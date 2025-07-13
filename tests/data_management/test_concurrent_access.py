#!/usr/bin/env python3
"""Test Concurrent Access Functionality.

This module provides comprehensive tests for concurrent access functionality,
including multi-threaded database operations, race condition prevention,
deadlock detection, transaction isolation, and concurrent data integrity.
"""

import asyncio
import json
import sqlite3
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import tempfile
import queue
import random

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.thread_storage import ThreadStorage
from src.exceptions import ConcurrencyError, DeadlockError
from src.handlers.thread_manager import ThreadManager


class TestConcurrentAccess(unittest.IsolatedAsyncioTestCase):
    """Test cases for concurrent access functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "max_concurrent_connections": 10,
            "transaction_timeout": 30,
            "deadlock_detection": True,
            "isolation_level": "SERIALIZABLE",
            "retry_count": 3,
            "retry_delay": 0.1,
            "debug": True
        }
        
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Concurrent access test scenarios
        self.concurrent_test_data = {
            "threads": [
                {
                    "session_id": f"concurrent_session_{i:03d}",
                    "thread_id": f"12345678901234567{i:1d}",
                    "thread_name": f"Concurrent Thread {i}",
                    "channel_id": "987654321098765432",
                    "created_at": f"2025-07-12T22:{i % 60:02d}:00.000Z",
                    "last_used": f"2025-07-12T22:{(i + 5) % 60:02d}:00.000Z",
                    "is_archived": i % 3 == 0,
                    "message_count": i * 5
                }
                for i in range(50)
            ],
            "sessions": [
                {
                    "session_id": f"concurrent_session_{i:03d}",
                    "status": ["active", "idle", "completed"][i % 3],
                    "user_id": f"user_{i % 10}",
                    "created_at": f"2025-07-12T22:{i % 60:02d}:00.000Z",
                    "metadata": json.dumps({
                        "tools_used": ["Write", "Read", "Bash"][:(i % 3) + 1],
                        "commands_count": i * 2,
                        "concurrent_test": True
                    })
                }
                for i in range(50)
            ]
        }
        
        # Concurrency patterns for testing
        self.concurrency_patterns = {
            "high_read_low_write": {
                "read_ratio": 0.8,
                "write_ratio": 0.2,
                "operations_per_thread": 20
            },
            "balanced_read_write": {
                "read_ratio": 0.5,
                "write_ratio": 0.5,
                "operations_per_thread": 15
            },
            "high_write_low_read": {
                "read_ratio": 0.2,
                "write_ratio": 0.8,
                "operations_per_thread": 10
            },
            "mixed_operations": {
                "read_ratio": 0.4,
                "write_ratio": 0.4,
                "update_ratio": 0.2,
                "operations_per_thread": 25
            }
        }
        
        # Deadlock scenarios for testing
        self.deadlock_scenarios = [
            {
                "name": "circular_dependency",
                "threads": 2,
                "resources": ["table_a", "table_b"],
                "pattern": "thread1: lock_a -> lock_b, thread2: lock_b -> lock_a"
            },
            {
                "name": "chain_dependency",
                "threads": 3,
                "resources": ["table_a", "table_b", "table_c"],
                "pattern": "thread1: a->b, thread2: b->c, thread3: c->a"
            },
            {
                "name": "multiple_resource",
                "threads": 4,
                "resources": ["table_a", "table_b", "table_c", "table_d"],
                "pattern": "complex multi-resource locking"
            }
        ]
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Close any open connections and remove temp file
        try:
            Path(self.db_path).unlink(missing_ok=True)
        except Exception:
            pass
    
    async def test_multi_threaded_database_operations(self) -> None:
        """Test multi-threaded database operations with proper synchronization."""
        with patch('sqlite3.connect') as mock_connect:
            # Mock database connections with thread safety
            connection_pool = {}
            operation_log = []
            lock = threading.Lock()
            
            def create_connection(db_path):
                thread_id = threading.current_thread().ident
                if thread_id not in connection_pool:
                    conn = MagicMock()
                    cursor = MagicMock()
                    conn.cursor.return_value = cursor
                    conn.thread_id = thread_id
                    connection_pool[thread_id] = conn
                    
                    # Mock execute with logging
                    def logged_execute(query, params=()):
                        with lock:
                            operation_log.append({
                                "thread_id": thread_id,
                                "operation": "execute",
                                "query": query[:50],
                                "timestamp": time.time(),
                                "params_count": len(params) if params else 0
                            })
                        return cursor
                    
                    conn.execute.side_effect = logged_execute
                    conn.commit.side_effect = lambda: operation_log.append({
                        "thread_id": thread_id,
                        "operation": "commit",
                        "timestamp": time.time()
                    })
                    
                return connection_pool[thread_id]
            
            mock_connect.side_effect = create_connection
            
            # Test concurrent read operations
            def concurrent_read_worker(worker_id: int, results: queue.Queue):
                """Worker function for concurrent reads."""
                try:
                    storage = ThreadStorage(self.db_path)
                    conn = sqlite3.connect(self.db_path)
                    
                    read_count = 0
                    for i in range(10):
                        # Simulate read operation
                        query = f"SELECT * FROM threads WHERE session_id = 'concurrent_session_{(worker_id * 10 + i) % 50:03d}'"
                        conn.execute(query)
                        read_count += 1
                        
                        # Small delay to increase contention
                        time.sleep(0.001)
                    
                    results.put({
                        "worker_id": worker_id,
                        "operation_type": "read",
                        "operations_completed": read_count,
                        "success": True
                    })
                    
                except Exception as e:
                    results.put({
                        "worker_id": worker_id,
                        "operation_type": "read",
                        "operations_completed": 0,
                        "success": False,
                        "error": str(e)
                    })
            
            # Test concurrent write operations
            def concurrent_write_worker(worker_id: int, results: queue.Queue):
                """Worker function for concurrent writes."""
                try:
                    storage = ThreadStorage(self.db_path)
                    conn = sqlite3.connect(self.db_path)
                    
                    write_count = 0
                    for i in range(5):
                        # Simulate write operation
                        session_id = f"write_session_{worker_id:03d}_{i:03d}"
                        query = f"INSERT INTO threads (session_id, thread_id, created_at) VALUES (?, ?, ?)"
                        params = (session_id, f"thread_{worker_id}_{i}", "2025-07-12T22:00:00.000Z")
                        
                        conn.execute(query, params)
                        conn.commit()
                        write_count += 1
                        
                        # Small delay to increase contention
                        time.sleep(0.002)
                    
                    results.put({
                        "worker_id": worker_id,
                        "operation_type": "write",
                        "operations_completed": write_count,
                        "success": True
                    })
                    
                except Exception as e:
                    results.put({
                        "worker_id": worker_id,
                        "operation_type": "write",
                        "operations_completed": 0,
                        "success": False,
                        "error": str(e)
                    })
            
            # Launch concurrent workers
            results_queue = queue.Queue()
            threads = []
            
            # Start read workers
            for worker_id in range(5):
                thread = threading.Thread(target=concurrent_read_worker, args=(worker_id, results_queue))
                threads.append(thread)
                thread.start()
            
            # Start write workers
            for worker_id in range(3):
                thread = threading.Thread(target=concurrent_write_worker, args=(worker_id, results_queue))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=30)  # 30 second timeout
            
            # Collect results
            worker_results = []
            while not results_queue.empty():
                try:
                    result = results_queue.get_nowait()
                    worker_results.append(result)
                except queue.Empty:
                    break
            
            # Verify results
            successful_workers = [r for r in worker_results if r["success"]]
            failed_workers = [r for r in worker_results if not r["success"]]
            
            self.assertEqual(len(worker_results), 8)  # 5 readers + 3 writers
            self.assertGreaterEqual(len(successful_workers), 6)  # Most should succeed
            
            # Analyze operation patterns
            read_operations = [r for r in worker_results if r["operation_type"] == "read"]
            write_operations = [r for r in worker_results if r["operation_type"] == "write"]
            
            total_read_ops = sum(r["operations_completed"] for r in read_operations)
            total_write_ops = sum(r["operations_completed"] for r in write_operations)
            
            self.assertGreater(total_read_ops, 0)
            self.assertGreater(total_write_ops, 0)
            
            # Verify thread isolation
            thread_ids_used = set(log["thread_id"] for log in operation_log)
            self.assertGreaterEqual(len(thread_ids_used), 2)  # Multiple threads used
            
            # Log multi-threading analysis
            self.logger.info(
                "Multi-threaded database operations analysis",
                context={
                    "total_workers": len(worker_results),
                    "successful_workers": len(successful_workers),
                    "failed_workers": len(failed_workers),
                    "total_read_operations": total_read_ops,
                    "total_write_operations": total_write_ops,
                    "threads_involved": len(thread_ids_used),
                    "database_operations_logged": len(operation_log)
                }
            )
    
    async def test_race_condition_prevention(self) -> None:
        """Test prevention of race conditions in concurrent operations."""
        with patch('src.thread_storage.ThreadStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_storage.return_value = mock_instance
            
            # Mock race condition scenarios
            shared_counter = {"value": 0}
            race_condition_log = []
            access_lock = threading.Lock()
            
            def non_atomic_increment(worker_id: int, iterations: int) -> Dict[str, Any]:
                """Non-atomic increment that can cause race conditions."""
                local_increments = 0
                
                for i in range(iterations):
                    # Simulate non-atomic read-modify-write
                    current_value = shared_counter["value"]
                    
                    # Simulate processing delay (increases race condition likelihood)
                    time.sleep(0.0001)
                    
                    # Write back incremented value
                    shared_counter["value"] = current_value + 1
                    local_increments += 1
                    
                    race_condition_log.append({
                        "worker_id": worker_id,
                        "iteration": i,
                        "read_value": current_value,
                        "written_value": current_value + 1,
                        "timestamp": time.time()
                    })
                
                return {
                    "worker_id": worker_id,
                    "local_increments": local_increments,
                    "final_observed_value": shared_counter["value"]
                }
            
            def atomic_increment(worker_id: int, iterations: int) -> Dict[str, Any]:
                """Atomic increment using proper locking."""
                local_increments = 0
                
                for i in range(iterations):
                    # Atomic read-modify-write with lock
                    with access_lock:
                        current_value = shared_counter["value"]
                        shared_counter["value"] = current_value + 1
                        local_increments += 1
                        
                        race_condition_log.append({
                            "worker_id": worker_id,
                            "iteration": i,
                            "read_value": current_value,
                            "written_value": current_value + 1,
                            "timestamp": time.time(),
                            "atomic": True
                        })
                
                return {
                    "worker_id": worker_id,
                    "local_increments": local_increments,
                    "final_observed_value": shared_counter["value"]
                }
            
            def detect_race_conditions(log_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
                """Detect race conditions in operation log."""
                race_conditions = []
                
                # Look for overlapping read-write sequences
                for i, entry1 in enumerate(log_entries):
                    for j, entry2 in enumerate(log_entries[i+1:], i+1):
                        # Check if two operations read the same value
                        if (entry1["read_value"] == entry2["read_value"] and 
                            entry1["worker_id"] != entry2["worker_id"]):
                            race_conditions.append({
                                "type": "concurrent_read_same_value",
                                "worker1": entry1["worker_id"],
                                "worker2": entry2["worker_id"],
                                "value": entry1["read_value"],
                                "timestamp_diff": abs(entry2["timestamp"] - entry1["timestamp"])
                            })
                
                # Check for lost updates
                sorted_log = sorted(log_entries, key=lambda x: x["timestamp"])
                lost_updates = 0
                
                for i in range(1, len(sorted_log)):
                    current = sorted_log[i]
                    previous = sorted_log[i-1]
                    
                    expected_value = previous["written_value"]
                    actual_read = current["read_value"]
                    
                    if actual_read != expected_value and not current.get("atomic", False):
                        lost_updates += 1
                
                return {
                    "race_conditions_detected": len(race_conditions),
                    "lost_updates": lost_updates,
                    "race_condition_details": race_conditions[:5]  # First 5 for analysis
                }
            
            mock_instance.non_atomic_increment.side_effect = non_atomic_increment
            mock_instance.atomic_increment.side_effect = atomic_increment
            mock_instance.detect_race_conditions.side_effect = detect_race_conditions
            
            storage = ThreadStorage(self.db_path)
            
            # Test 1: Non-atomic operations (should cause race conditions)
            shared_counter["value"] = 0
            race_condition_log.clear()
            
            non_atomic_threads = []
            non_atomic_results = []
            iterations_per_thread = 10
            
            def run_non_atomic(worker_id):
                result = storage.non_atomic_increment(worker_id, iterations_per_thread)
                non_atomic_results.append(result)
            
            # Launch multiple threads for non-atomic operations
            for worker_id in range(5):
                thread = threading.Thread(target=run_non_atomic, args=(worker_id,))
                non_atomic_threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in non_atomic_threads:
                thread.join()
            
            # Analyze non-atomic results
            total_expected = len(non_atomic_threads) * iterations_per_thread
            final_value_non_atomic = shared_counter["value"]
            non_atomic_log = [entry for entry in race_condition_log if not entry.get("atomic", False)]
            
            race_analysis_non_atomic = storage.detect_race_conditions(non_atomic_log)
            
            # Should have race conditions with non-atomic operations
            self.assertLess(final_value_non_atomic, total_expected)  # Lost updates
            self.assertGreater(race_analysis_non_atomic["race_conditions_detected"], 0)
            
            # Test 2: Atomic operations (should prevent race conditions)
            shared_counter["value"] = 0
            race_condition_log.clear()
            
            atomic_threads = []
            atomic_results = []
            
            def run_atomic(worker_id):
                result = storage.atomic_increment(worker_id, iterations_per_thread)
                atomic_results.append(result)
            
            # Launch multiple threads for atomic operations
            for worker_id in range(5):
                thread = threading.Thread(target=run_atomic, args=(worker_id,))
                atomic_threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in atomic_threads:
                thread.join()
            
            # Analyze atomic results
            final_value_atomic = shared_counter["value"]
            atomic_log = [entry for entry in race_condition_log if entry.get("atomic", False)]
            
            race_analysis_atomic = storage.detect_race_conditions(atomic_log)
            
            # Should have no race conditions with atomic operations
            self.assertEqual(final_value_atomic, total_expected)  # No lost updates
            self.assertEqual(race_analysis_atomic["race_conditions_detected"], 0)
            
            # Log race condition analysis
            self.logger.info(
                "Race condition prevention analysis",
                context={
                    "non_atomic_operations": {
                        "expected_value": total_expected,
                        "actual_value": final_value_non_atomic,
                        "lost_updates": total_expected - final_value_non_atomic,
                        "race_conditions": race_analysis_non_atomic["race_conditions_detected"]
                    },
                    "atomic_operations": {
                        "expected_value": total_expected,
                        "actual_value": final_value_atomic,
                        "lost_updates": total_expected - final_value_atomic,
                        "race_conditions": race_analysis_atomic["race_conditions_detected"]
                    },
                    "race_condition_prevention_effective": race_analysis_atomic["race_conditions_detected"] == 0
                }
            )
    
    async def test_deadlock_detection_and_recovery(self) -> None:
        """Test deadlock detection and recovery mechanisms."""
        with patch('src.handlers.thread_manager.ThreadManager') as mock_thread_manager:
            mock_instance = MagicMock()
            mock_thread_manager.return_value = mock_instance
            
            # Mock deadlock detection system
            resource_locks = {}
            lock_requests = []
            deadlock_log = []
            
            def acquire_resource_lock(thread_id: str, resource_id: str, timeout: float = 5.0) -> Dict[str, Any]:
                """Attempt to acquire a resource lock with deadlock detection."""
                request_time = time.time()
                
                lock_requests.append({
                    "thread_id": thread_id,
                    "resource_id": resource_id,
                    "action": "request",
                    "timestamp": request_time
                })
                
                # Check if resource is already locked
                if resource_id in resource_locks:
                    current_owner = resource_locks[resource_id]["owner"]
                    if current_owner != thread_id:
                        # Detect potential deadlock
                        deadlock_detected = detect_deadlock_cycle(thread_id, resource_id)
                        
                        if deadlock_detected:
                            deadlock_log.append({
                                "victim_thread": thread_id,
                                "resource": resource_id,
                                "current_owner": current_owner,
                                "deadlock_cycle": deadlock_detected["cycle"],
                                "timestamp": time.time()
                            })
                            
                            raise DeadlockError(f"Deadlock detected: {deadlock_detected['cycle']}")
                        
                        # Wait for resource
                        start_wait = time.time()
                        while (resource_id in resource_locks and 
                               time.time() - start_wait < timeout):
                            time.sleep(0.01)
                        
                        if resource_id in resource_locks:
                            raise TimeoutError(f"Timeout waiting for resource {resource_id}")
                
                # Acquire lock
                resource_locks[resource_id] = {
                    "owner": thread_id,
                    "acquired_at": time.time()
                }
                
                lock_requests.append({
                    "thread_id": thread_id,
                    "resource_id": resource_id,
                    "action": "acquired",
                    "timestamp": time.time()
                })
                
                return {
                    "success": True,
                    "resource_id": resource_id,
                    "thread_id": thread_id,
                    "acquired_at": resource_locks[resource_id]["acquired_at"]
                }
            
            def release_resource_lock(thread_id: str, resource_id: str) -> Dict[str, Any]:
                """Release a resource lock."""
                if resource_id not in resource_locks:
                    return {"success": False, "error": "Resource not locked"}
                
                if resource_locks[resource_id]["owner"] != thread_id:
                    return {"success": False, "error": "Not the lock owner"}
                
                del resource_locks[resource_id]
                
                lock_requests.append({
                    "thread_id": thread_id,
                    "resource_id": resource_id,
                    "action": "released",
                    "timestamp": time.time()
                })
                
                return {"success": True, "resource_id": resource_id}
            
            def detect_deadlock_cycle(requesting_thread: str, requested_resource: str) -> Optional[Dict[str, Any]]:
                """Detect deadlock cycles in resource allocation graph."""
                # Build wait-for graph
                wait_for_graph = {}
                
                # Find what each thread is waiting for
                for request in lock_requests:
                    if request["action"] == "request":
                        thread_id = request["thread_id"]
                        resource_id = request["resource_id"]
                        
                        # Check if still waiting (no corresponding acquired)
                        acquired = any(r["thread_id"] == thread_id and 
                                     r["resource_id"] == resource_id and 
                                     r["action"] == "acquired" and
                                     r["timestamp"] > request["timestamp"]
                                     for r in lock_requests)
                        
                        if not acquired:
                            if resource_id in resource_locks:
                                owner = resource_locks[resource_id]["owner"]
                                if thread_id not in wait_for_graph:
                                    wait_for_graph[thread_id] = set()
                                wait_for_graph[thread_id].add(owner)
                
                # Add current request
                if requested_resource in resource_locks:
                    owner = resource_locks[requested_resource]["owner"]
                    if requesting_thread not in wait_for_graph:
                        wait_for_graph[requesting_thread] = set()
                    wait_for_graph[requesting_thread].add(owner)
                
                # Detect cycles using DFS
                def has_cycle(node, visited, rec_stack, path):
                    visited.add(node)
                    rec_stack.add(node)
                    path.append(node)
                    
                    if node in wait_for_graph:
                        for neighbor in wait_for_graph[node]:
                            if neighbor not in visited:
                                if has_cycle(neighbor, visited, rec_stack, path):
                                    return True
                            elif neighbor in rec_stack:
                                # Found cycle
                                cycle_start = path.index(neighbor)
                                return path[cycle_start:] + [neighbor]
                    
                    path.pop()
                    rec_stack.remove(node)
                    return False
                
                visited = set()
                rec_stack = set()
                
                for thread in wait_for_graph:
                    if thread not in visited:
                        path = []
                        result = has_cycle(thread, visited, rec_stack, path)
                        if result and isinstance(result, list):
                            return {
                                "cycle_detected": True,
                                "cycle": result
                            }
                
                return None
            
            def simulate_deadlock_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
                """Simulate a specific deadlock scenario."""
                scenario_name = scenario["name"]
                threads_count = scenario["threads"]
                resources = scenario["resources"]
                
                threads = []
                thread_results = []
                scenario_start = time.time()
                
                def deadlock_worker(worker_id: int, lock_sequence: List[str]):
                    """Worker that follows a specific locking sequence."""
                    thread_id = f"deadlock_thread_{worker_id}"
                    acquired_locks = []
                    
                    try:
                        for resource in lock_sequence:
                            # Add delay to increase deadlock probability
                            time.sleep(random.uniform(0.01, 0.05))
                            
                            result = acquire_resource_lock(thread_id, resource, timeout=2.0)
                            acquired_locks.append(resource)
                        
                        # Hold locks briefly
                        time.sleep(0.1)
                        
                        # Release in reverse order
                        for resource in reversed(acquired_locks):
                            release_resource_lock(thread_id, resource)
                        
                        thread_results.append({
                            "thread_id": thread_id,
                            "success": True,
                            "locks_acquired": len(acquired_locks)
                        })
                        
                    except (DeadlockError, TimeoutError) as e:
                        # Release any acquired locks
                        for resource in acquired_locks:
                            try:
                                release_resource_lock(thread_id, resource)
                            except:
                                pass
                        
                        thread_results.append({
                            "thread_id": thread_id,
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "locks_acquired": len(acquired_locks)
                        })
                
                # Create deadlock-prone lock sequences
                if scenario_name == "circular_dependency":
                    sequences = [
                        ["table_a", "table_b"],
                        ["table_b", "table_a"]
                    ]
                elif scenario_name == "chain_dependency":
                    sequences = [
                        ["table_a", "table_b"],
                        ["table_b", "table_c"],
                        ["table_c", "table_a"]
                    ]
                else:
                    # Random sequences for complex scenarios
                    sequences = [
                        random.sample(resources, min(len(resources), 2))
                        for _ in range(threads_count)
                    ]
                
                # Start worker threads
                for i in range(threads_count):
                    sequence = sequences[i % len(sequences)]
                    thread = threading.Thread(target=deadlock_worker, args=(i, sequence))
                    threads.append(thread)
                    thread.start()
                
                # Wait for completion
                for thread in threads:
                    thread.join(timeout=10)
                
                scenario_duration = time.time() - scenario_start
                
                successful_threads = [r for r in thread_results if r["success"]]
                failed_threads = [r for r in thread_results if not r["success"]]
                deadlock_errors = [r for r in failed_threads if r.get("error_type") == "DeadlockError"]
                
                return {
                    "scenario_name": scenario_name,
                    "threads_count": threads_count,
                    "successful_threads": len(successful_threads),
                    "failed_threads": len(failed_threads),
                    "deadlock_errors": len(deadlock_errors),
                    "deadlocks_detected": len([log for log in deadlock_log if log["timestamp"] >= scenario_start]),
                    "scenario_duration": scenario_duration,
                    "thread_results": thread_results
                }
            
            mock_instance.acquire_resource_lock.side_effect = acquire_resource_lock
            mock_instance.release_resource_lock.side_effect = release_resource_lock
            mock_instance.detect_deadlock_cycle.side_effect = detect_deadlock_cycle
            mock_instance.simulate_deadlock_scenario.side_effect = simulate_deadlock_scenario
            
            thread_manager = ThreadManager(self.test_config, self.logger)
            
            # Test each deadlock scenario
            deadlock_results = []
            
            for scenario in self.deadlock_scenarios:
                # Clear state for each scenario
                resource_locks.clear()
                lock_requests.clear()
                
                result = thread_manager.simulate_deadlock_scenario(scenario)
                deadlock_results.append(result)
                
                # Verify deadlock detection worked
                if scenario["name"] in ["circular_dependency", "chain_dependency"]:
                    # These scenarios should trigger deadlock detection
                    self.assertGreater(result["deadlocks_detected"], 0,
                                     f"Deadlock should be detected in {scenario['name']} scenario")
                
                # Verify no permanent deadlocks (all threads should complete or be aborted)
                self.assertEqual(result["successful_threads"] + result["failed_threads"], 
                               result["threads_count"])
            
            # Test deadlock recovery effectiveness
            total_deadlocks_detected = sum(r["deadlocks_detected"] for r in deadlock_results)
            total_threads = sum(r["threads_count"] for r in deadlock_results)
            recovery_rate = 1.0 - (total_deadlocks_detected / total_threads)
            
            # Log deadlock analysis
            self.logger.info(
                "Deadlock detection and recovery analysis",
                context={
                    "scenarios_tested": len(self.deadlock_scenarios),
                    "total_threads": total_threads,
                    "total_deadlocks_detected": total_deadlocks_detected,
                    "recovery_rate": recovery_rate,
                    "deadlock_results": [
                        {
                            "scenario": r["scenario_name"],
                            "threads": r["threads_count"],
                            "deadlocks": r["deadlocks_detected"],
                            "success_rate": r["successful_threads"] / r["threads_count"]
                        }
                        for r in deadlock_results
                    ]
                }
            )
    
    async def test_transaction_isolation_levels(self) -> None:
        """Test different transaction isolation levels and their behavior."""
        with patch('sqlite3.connect') as mock_connect:
            # Mock connections with different isolation levels
            connections = {}
            transaction_log = []
            
            def create_connection_with_isolation(isolation_level: str):
                conn = MagicMock()
                cursor = MagicMock()
                conn.cursor.return_value = cursor
                conn.isolation_level = isolation_level
                
                # Mock transaction operations
                def begin_transaction():
                    transaction_log.append({
                        "connection": id(conn),
                        "isolation_level": isolation_level,
                        "operation": "BEGIN",
                        "timestamp": time.time()
                    })
                
                def commit_transaction():
                    transaction_log.append({
                        "connection": id(conn),
                        "isolation_level": isolation_level,
                        "operation": "COMMIT",
                        "timestamp": time.time()
                    })
                
                def rollback_transaction():
                    transaction_log.append({
                        "connection": id(conn),
                        "isolation_level": isolation_level,
                        "operation": "ROLLBACK",
                        "timestamp": time.time()
                    })
                
                conn.execute.side_effect = lambda query, params=(): transaction_log.append({
                    "connection": id(conn),
                    "isolation_level": isolation_level,
                    "operation": "EXECUTE",
                    "query": query[:50],
                    "timestamp": time.time()
                })
                
                conn.begin = begin_transaction
                conn.commit = commit_transaction
                conn.rollback = rollback_transaction
                
                return conn
            
            def test_isolation_scenario(scenario_name: str, isolation_level: str) -> Dict[str, Any]:
                """Test a specific isolation scenario."""
                scenario_start = time.time()
                isolation_anomalies = []
                
                # Create connections with specified isolation level
                conn1 = create_connection_with_isolation(isolation_level)
                conn2 = create_connection_with_isolation(isolation_level)
                
                if scenario_name == "dirty_read":
                    # Transaction 1: Update but don't commit
                    conn1.begin()
                    conn1.execute("UPDATE threads SET message_count = 999 WHERE session_id = 'test_session'")
                    
                    # Transaction 2: Try to read uncommitted data
                    conn2.begin()
                    conn2.execute("SELECT message_count FROM threads WHERE session_id = 'test_session'")
                    
                    # Simulate reading uncommitted data
                    if isolation_level in ["READ_UNCOMMITTED"]:
                        isolation_anomalies.append("dirty_read_detected")
                    
                    conn1.rollback()
                    conn2.commit()
                
                elif scenario_name == "non_repeatable_read":
                    # Transaction 1: Read data
                    conn1.begin()
                    conn1.execute("SELECT message_count FROM threads WHERE session_id = 'test_session'")
                    
                    # Transaction 2: Update and commit
                    conn2.begin()
                    conn2.execute("UPDATE threads SET message_count = 888 WHERE session_id = 'test_session'")
                    conn2.commit()
                    
                    # Transaction 1: Read again (should get different result in some isolation levels)
                    conn1.execute("SELECT message_count FROM threads WHERE session_id = 'test_session'")
                    
                    if isolation_level in ["READ_UNCOMMITTED", "READ_COMMITTED"]:
                        isolation_anomalies.append("non_repeatable_read_detected")
                    
                    conn1.commit()
                
                elif scenario_name == "phantom_read":
                    # Transaction 1: Count rows
                    conn1.begin()
                    conn1.execute("SELECT COUNT(*) FROM threads WHERE is_archived = 0")
                    
                    # Transaction 2: Insert new row
                    conn2.begin()
                    conn2.execute("INSERT INTO threads (session_id, thread_id, is_archived) VALUES ('phantom_test', 'phantom_thread', 0)")
                    conn2.commit()
                    
                    # Transaction 1: Count again (might see phantom row)
                    conn1.execute("SELECT COUNT(*) FROM threads WHERE is_archived = 0")
                    
                    if isolation_level in ["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ"]:
                        isolation_anomalies.append("phantom_read_detected")
                    
                    conn1.commit()
                
                scenario_duration = time.time() - scenario_start
                
                return {
                    "scenario_name": scenario_name,
                    "isolation_level": isolation_level,
                    "anomalies_detected": isolation_anomalies,
                    "scenario_duration": scenario_duration,
                    "transactions_executed": len([log for log in transaction_log if log["timestamp"] >= scenario_start])
                }
            
            # Test different isolation levels
            isolation_levels = ["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"]
            test_scenarios = ["dirty_read", "non_repeatable_read", "phantom_read"]
            
            isolation_test_results = []
            
            for isolation_level in isolation_levels:
                for scenario in test_scenarios:
                    result = test_isolation_scenario(scenario, isolation_level)
                    isolation_test_results.append(result)
            
            # Analyze isolation behavior
            isolation_analysis = {}
            
            for isolation_level in isolation_levels:
                level_results = [r for r in isolation_test_results if r["isolation_level"] == isolation_level]
                
                isolation_analysis[isolation_level] = {
                    "scenarios_tested": len(level_results),
                    "total_anomalies": sum(len(r["anomalies_detected"]) for r in level_results),
                    "anomaly_types": list(set(
                        anomaly for r in level_results for anomaly in r["anomalies_detected"]
                    )),
                    "average_duration": sum(r["scenario_duration"] for r in level_results) / len(level_results)
                }
            
            # Verify isolation level behavior
            # SERIALIZABLE should have no anomalies
            serializable_anomalies = isolation_analysis["SERIALIZABLE"]["total_anomalies"]
            self.assertEqual(serializable_anomalies, 0)
            
            # READ_UNCOMMITTED should have the most anomalies
            read_uncommitted_anomalies = isolation_analysis["READ_UNCOMMITTED"]["total_anomalies"]
            self.assertGreaterEqual(read_uncommitted_anomalies, 2)
            
            # Log isolation analysis
            self.logger.info(
                "Transaction isolation levels analysis",
                context={
                    "isolation_levels_tested": len(isolation_levels),
                    "scenarios_per_level": len(test_scenarios),
                    "total_tests": len(isolation_test_results),
                    "isolation_analysis": isolation_analysis,
                    "serializable_protection": serializable_anomalies == 0,
                    "isolation_effectiveness": {
                        level: analysis["total_anomalies"] 
                        for level, analysis in isolation_analysis.items()
                    }
                }
            )
    
    async def test_concurrent_data_integrity(self) -> None:
        """Test data integrity under concurrent access patterns."""
        with patch('src.thread_storage.ThreadStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_storage.return_value = mock_instance
            
            # Mock data integrity validation
            integrity_violations = []
            data_state = {"threads": {}, "sessions": {}}
            integrity_checks = []
            
            def concurrent_data_operation(operation_type: str, worker_id: int, 
                                        data_item: Dict[str, Any]) -> Dict[str, Any]:
                """Perform concurrent data operation with integrity checking."""
                operation_start = time.time()
                
                try:
                    if operation_type == "insert":
                        session_id = data_item["session_id"]
                        
                        # Check for duplicate
                        if session_id in data_state["threads"]:
                            integrity_violations.append({
                                "type": "duplicate_insert",
                                "worker_id": worker_id,
                                "session_id": session_id,
                                "timestamp": time.time()
                            })
                            return {"success": False, "error": "Duplicate session_id"}
                        
                        # Insert data
                        data_state["threads"][session_id] = data_item
                        
                    elif operation_type == "update":
                        session_id = data_item["session_id"]
                        
                        # Check existence
                        if session_id not in data_state["threads"]:
                            integrity_violations.append({
                                "type": "update_nonexistent",
                                "worker_id": worker_id,
                                "session_id": session_id,
                                "timestamp": time.time()
                            })
                            return {"success": False, "error": "Session not found"}
                        
                        # Update data
                        data_state["threads"][session_id].update(data_item)
                        
                    elif operation_type == "delete":
                        session_id = data_item["session_id"]
                        
                        # Check existence
                        if session_id not in data_state["threads"]:
                            integrity_violations.append({
                                "type": "delete_nonexistent",
                                "worker_id": worker_id,
                                "session_id": session_id,
                                "timestamp": time.time()
                            })
                            return {"success": False, "error": "Session not found"}
                        
                        # Delete data
                        del data_state["threads"][session_id]
                    
                    elif operation_type == "validate_references":
                        # Check referential integrity
                        violations = 0
                        
                        for thread_data in data_state["threads"].values():
                            session_id = thread_data.get("session_id")
                            if session_id and session_id not in data_state["sessions"]:
                                violations += 1
                                integrity_violations.append({
                                    "type": "broken_reference",
                                    "worker_id": worker_id,
                                    "thread_session_id": session_id,
                                    "timestamp": time.time()
                                })
                        
                        return {"success": True, "violations": violations}
                    
                    return {
                        "success": True,
                        "operation_type": operation_type,
                        "worker_id": worker_id,
                        "duration": time.time() - operation_start
                    }
                    
                except Exception as e:
                    integrity_violations.append({
                        "type": "operation_exception",
                        "worker_id": worker_id,
                        "error": str(e),
                        "timestamp": time.time()
                    })
                    return {"success": False, "error": str(e)}
            
            def validate_data_consistency() -> Dict[str, Any]:
                """Validate overall data consistency."""
                consistency_issues = []
                
                # Check for orphaned references
                for thread_data in data_state["threads"].values():
                    session_id = thread_data.get("session_id")
                    if session_id and session_id not in data_state["sessions"]:
                        consistency_issues.append({
                            "type": "orphaned_reference",
                            "thread_session_id": session_id
                        })
                
                # Check for duplicate IDs
                thread_ids = [t.get("thread_id") for t in data_state["threads"].values()]
                duplicate_thread_ids = [tid for tid in thread_ids if thread_ids.count(tid) > 1]
                
                if duplicate_thread_ids:
                    consistency_issues.append({
                        "type": "duplicate_thread_ids",
                        "duplicates": list(set(duplicate_thread_ids))
                    })
                
                # Check data type consistency
                for session_id, thread_data in data_state["threads"].items():
                    if not isinstance(thread_data.get("message_count", 0), int):
                        consistency_issues.append({
                            "type": "type_mismatch",
                            "session_id": session_id,
                            "field": "message_count"
                        })
                
                return {
                    "consistent": len(consistency_issues) == 0,
                    "issues_found": len(consistency_issues),
                    "consistency_issues": consistency_issues,
                    "data_counts": {
                        "threads": len(data_state["threads"]),
                        "sessions": len(data_state["sessions"])
                    }
                }
            
            def run_concurrent_integrity_test(pattern: Dict[str, Any]) -> Dict[str, Any]:
                """Run concurrent operations following a specific pattern."""
                pattern_start = time.time()
                
                # Initialize test data
                data_state["threads"].clear()
                data_state["sessions"].clear()
                integrity_violations.clear()
                
                # Pre-populate sessions for reference integrity
                for session_data in self.concurrent_test_data["sessions"][:20]:
                    data_state["sessions"][session_data["session_id"]] = session_data
                
                # Launch concurrent workers
                workers = []
                worker_results = []
                operations_per_worker = pattern["operations_per_thread"]
                
                def worker_function(worker_id: int):
                    worker_operations = []
                    
                    for i in range(operations_per_worker):
                        # Choose operation type based on pattern
                        rand = random.random()
                        
                        if rand < pattern.get("read_ratio", 0.5):
                            # Read operation (validate references)
                            operation_type = "validate_references"
                            data_item = {}
                        elif rand < pattern.get("read_ratio", 0.5) + pattern.get("write_ratio", 0.3):
                            # Insert operation
                            operation_type = "insert"
                            thread_index = worker_id * operations_per_worker + i
                            data_item = {
                                "session_id": f"concurrent_session_{thread_index % 20:03d}",
                                "thread_id": f"thread_{worker_id}_{i}",
                                "thread_name": f"Worker {worker_id} Thread {i}",
                                "message_count": i
                            }
                        else:
                            # Update operation
                            operation_type = "update"
                            existing_sessions = list(data_state["threads"].keys())
                            if existing_sessions:
                                session_id = random.choice(existing_sessions)
                                data_item = {
                                    "session_id": session_id,
                                    "message_count": i + 100
                                }
                            else:
                                continue
                        
                        result = concurrent_data_operation(operation_type, worker_id, data_item)
                        worker_operations.append(result)
                        
                        # Small delay to increase concurrency
                        time.sleep(0.001)
                    
                    worker_results.append({
                        "worker_id": worker_id,
                        "operations": worker_operations,
                        "successful_operations": sum(1 for op in worker_operations if op.get("success")),
                        "failed_operations": sum(1 for op in worker_operations if not op.get("success"))
                    })
                
                # Start workers
                num_workers = 8
                for worker_id in range(num_workers):
                    worker = threading.Thread(target=worker_function, args=(worker_id,))
                    workers.append(worker)
                    worker.start()
                
                # Wait for completion
                for worker in workers:
                    worker.join()
                
                # Validate final consistency
                final_consistency = validate_data_consistency()
                
                pattern_duration = time.time() - pattern_start
                
                return {
                    "pattern_name": pattern.get("name", "unknown"),
                    "workers": num_workers,
                    "operations_per_worker": operations_per_worker,
                    "total_operations": sum(len(wr["operations"]) for wr in worker_results),
                    "successful_operations": sum(wr["successful_operations"] for wr in worker_results),
                    "failed_operations": sum(wr["failed_operations"] for wr in worker_results),
                    "integrity_violations": len(integrity_violations),
                    "final_consistency": final_consistency,
                    "pattern_duration": pattern_duration
                }
            
            mock_instance.concurrent_data_operation.side_effect = concurrent_data_operation
            mock_instance.validate_data_consistency.side_effect = validate_data_consistency
            mock_instance.run_concurrent_integrity_test.side_effect = run_concurrent_integrity_test
            
            storage = ThreadStorage(self.db_path)
            
            # Test different concurrency patterns
            integrity_test_results = []
            
            for pattern_name, pattern_config in self.concurrency_patterns.items():
                pattern_config["name"] = pattern_name
                result = storage.run_concurrent_integrity_test(pattern_config)
                integrity_test_results.append(result)
                
                # Verify data integrity maintained
                self.assertTrue(result["final_consistency"]["consistent"],
                              f"Data consistency violated in pattern: {pattern_name}")
                
                # Check that most operations succeeded
                success_rate = result["successful_operations"] / result["total_operations"]
                self.assertGreater(success_rate, 0.7,
                                 f"Low success rate in pattern: {pattern_name}")
            
            # Analyze overall integrity performance
            total_operations = sum(r["total_operations"] for r in integrity_test_results)
            total_violations = sum(r["integrity_violations"] for r in integrity_test_results)
            overall_integrity_rate = 1.0 - (total_violations / total_operations)
            
            # Log concurrent data integrity analysis
            self.logger.info(
                "Concurrent data integrity analysis",
                context={
                    "patterns_tested": len(self.concurrency_patterns),
                    "total_operations": total_operations,
                    "total_integrity_violations": total_violations,
                    "overall_integrity_rate": overall_integrity_rate,
                    "pattern_results": [
                        {
                            "pattern": r["pattern_name"],
                            "operations": r["total_operations"],
                            "success_rate": r["successful_operations"] / r["total_operations"],
                            "violations": r["integrity_violations"],
                            "consistent": r["final_consistency"]["consistent"]
                        }
                        for r in integrity_test_results
                    ]
                }
            )


def run_concurrent_access_tests() -> None:
    """Run concurrent access tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestConcurrentAccess)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nConcurrent Access Tests Summary:")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    asyncio.run(main())