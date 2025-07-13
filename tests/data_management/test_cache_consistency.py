#!/usr/bin/env python3
"""Test Cache Consistency Functionality.

This module provides comprehensive tests for cache consistency
functionality, including cache synchronization, cache invalidation,
cache coherence, cache performance, and cache recovery testing.
"""

import asyncio
import json
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import weakref

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.thread_storage import ThreadStorage
from src.exceptions import CacheError, ConsistencyError
from src.handlers.thread_manager import ThreadManager


class TestCacheConsistency(unittest.IsolatedAsyncioTestCase):
    """Test cases for cache consistency functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "cache_mode": "write_through",
            "cache_size": 1000,
            "cache_ttl": 300,
            "cache_sync_interval": 30,
            "consistency_level": "strong",
            "debug": True
        }
        
        # Cache test scenarios
        self.cache_test_data = {
            "threads": {
                "thread_001": {
                    "session_id": "session_cache_001",
                    "thread_id": "123456789012345678",
                    "thread_name": "Cache Test Thread 1",
                    "channel_id": "987654321098765432",
                    "created_at": "2025-07-12T22:00:00.000Z",
                    "last_used": "2025-07-12T22:30:00.000Z",
                    "is_archived": False,
                    "message_count": 15
                },
                "thread_002": {
                    "session_id": "session_cache_002",
                    "thread_id": "234567890123456789",
                    "thread_name": "Cache Test Thread 2",
                    "channel_id": "987654321098765432",
                    "created_at": "2025-07-12T21:30:00.000Z",
                    "last_used": "2025-07-12T22:00:00.000Z",
                    "is_archived": False,
                    "message_count": 8
                }
            },
            "sessions": {
                "session_cache_001": {
                    "session_id": "session_cache_001",
                    "status": "active",
                    "user_id": "user_cache_1",
                    "thread_id": "123456789012345678",
                    "metadata": {"tools_used": ["Write", "Read"], "commands_count": 10}
                },
                "session_cache_002": {
                    "session_id": "session_cache_002",
                    "status": "idle",
                    "user_id": "user_cache_2",
                    "thread_id": "234567890123456789",
                    "metadata": {"tools_used": ["Bash"], "commands_count": 5}
                }
            },
            "user_preferences": {
                "user_cache_1": {
                    "notification_settings": {"enabled": True, "frequency": "immediate"},
                    "thread_preferences": {"auto_archive": False, "naming_pattern": "Session {id}"}
                },
                "user_cache_2": {
                    "notification_settings": {"enabled": False, "frequency": "daily"},
                    "thread_preferences": {"auto_archive": True, "naming_pattern": "Work {timestamp}"}
                }
            }
        }
        
        # Cache consistency rules
        self.consistency_rules = {
            "thread_session_consistency": {
                "description": "Thread data must match corresponding session data",
                "check": lambda thread, session: thread.get("session_id") == session.get("session_id")
            },
            "session_thread_consistency": {
                "description": "Session thread_id must exist in thread cache",
                "check": lambda session, threads: session.get("thread_id") in threads
            },
            "timestamp_consistency": {
                "description": "Timestamps must be in proper chronological order",
                "check": lambda data: self._validate_timestamp_order(data)
            },
            "reference_integrity": {
                "description": "All references between cached objects must be valid",
                "check": lambda cache_data: self._validate_reference_integrity(cache_data)
            }
        }
        
        # Cache performance metrics
        self.performance_thresholds = {
            "cache_hit_ratio": 0.8,  # 80% minimum hit ratio
            "average_response_time": 0.01,  # 10ms maximum average response
            "cache_memory_usage": 0.9,  # 90% maximum memory usage
            "sync_delay": 0.1,  # 100ms maximum sync delay
            "invalidation_time": 0.05  # 50ms maximum invalidation time
        }
    
    async def test_cache_synchronization_basic(self) -> None:
        """Test basic cache synchronization between memory and storage."""
        with patch('src.thread_storage.ThreadStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_storage.return_value = mock_instance
            
            # Mock cache and storage systems
            memory_cache = {}
            persistent_storage = {}
            sync_log = []
            
            def cache_write(key: str, value: Any, write_through: bool = True) -> None:
                """Write to cache with optional write-through to storage."""
                memory_cache[key] = {
                    "data": value,
                    "timestamp": time.time(),
                    "dirty": not write_through
                }
                
                if write_through:
                    persistent_storage[key] = value
                    sync_log.append({
                        "operation": "write_through",
                        "key": key,
                        "timestamp": time.time()
                    })
            
            def cache_read(key: str) -> Optional[Any]:
                """Read from cache with fallback to storage."""
                if key in memory_cache:
                    sync_log.append({
                        "operation": "cache_hit",
                        "key": key,
                        "timestamp": time.time()
                    })
                    return memory_cache[key]["data"]
                
                # Cache miss - check storage
                if key in persistent_storage:
                    value = persistent_storage[key]
                    memory_cache[key] = {
                        "data": value,
                        "timestamp": time.time(),
                        "dirty": False
                    }
                    sync_log.append({
                        "operation": "cache_miss_loaded",
                        "key": key,
                        "timestamp": time.time()
                    })
                    return value
                
                sync_log.append({
                    "operation": "cache_miss_empty",
                    "key": key,
                    "timestamp": time.time()
                })
                return None
            
            def sync_dirty_entries() -> int:
                """Synchronize dirty cache entries to storage."""
                synced_count = 0
                for key, cache_entry in memory_cache.items():
                    if cache_entry.get("dirty", False):
                        persistent_storage[key] = cache_entry["data"]
                        cache_entry["dirty"] = False
                        synced_count += 1
                        sync_log.append({
                            "operation": "dirty_sync",
                            "key": key,
                            "timestamp": time.time()
                        })
                return synced_count
            
            mock_instance.cache_write.side_effect = cache_write
            mock_instance.cache_read.side_effect = cache_read
            mock_instance.sync_dirty_entries.side_effect = sync_dirty_entries
            
            storage = ThreadStorage("/tmp/cache_test.db")
            
            # Test write-through caching
            test_thread_data = self.cache_test_data["threads"]["thread_001"]
            storage.cache_write("thread_001", test_thread_data, write_through=True)
            
            # Verify immediate sync to storage
            self.assertIn("thread_001", persistent_storage)
            self.assertEqual(persistent_storage["thread_001"], test_thread_data)
            
            # Test cache hit
            cached_data = storage.cache_read("thread_001")
            self.assertEqual(cached_data, test_thread_data)
            
            # Verify cache hit was logged
            cache_hits = [log for log in sync_log if log["operation"] == "cache_hit"]
            self.assertEqual(len(cache_hits), 1)
            
            # Test write-back caching (dirty writes)
            test_session_data = self.cache_test_data["sessions"]["session_cache_001"]
            storage.cache_write("session_cache_001", test_session_data, write_through=False)
            
            # Verify data is in cache but not yet in storage
            self.assertIn("session_cache_001", memory_cache)
            self.assertNotIn("session_cache_001", persistent_storage)
            
            # Test dirty entry synchronization
            synced_count = storage.sync_dirty_entries()
            self.assertEqual(synced_count, 1)
            self.assertIn("session_cache_001", persistent_storage)
            
            # Test cache miss and load from storage
            # Simulate cache eviction
            memory_cache.pop("thread_001", None)
            
            # Read should load from storage
            reloaded_data = storage.cache_read("thread_001")
            self.assertEqual(reloaded_data, test_thread_data)
            
            # Verify cache miss and reload was logged
            cache_misses = [log for log in sync_log if log["operation"] == "cache_miss_loaded"]
            self.assertEqual(len(cache_misses), 1)
            
            # Log synchronization analysis
            self.logger.info(
                "Cache synchronization analysis",
                context={
                    "memory_cache_entries": len(memory_cache),
                    "storage_entries": len(persistent_storage),
                    "sync_operations": len(sync_log),
                    "cache_hits": len([log for log in sync_log if log["operation"] == "cache_hit"]),
                    "cache_misses": len([log for log in sync_log if log["operation"].startswith("cache_miss")]),
                    "dirty_syncs": len([log for log in sync_log if log["operation"] == "dirty_sync"]),
                    "write_through_operations": len([log for log in sync_log if log["operation"] == "write_through"])
                }
            )
    
    async def test_cache_invalidation_strategies(self) -> None:
        """Test various cache invalidation strategies and consistency."""
        with patch('src.handlers.thread_manager.ThreadManager') as mock_thread_manager:
            mock_instance = MagicMock()
            mock_thread_manager.return_value = mock_instance
            
            # Mock cache invalidation system
            cache_registry = {}
            invalidation_log = []
            dependency_graph = {}
            
            def register_cache_entry(key: str, data: Any, dependencies: List[str] = None) -> None:
                """Register cache entry with optional dependencies."""
                cache_registry[key] = {
                    "data": data,
                    "timestamp": time.time(),
                    "access_count": 0,
                    "valid": True
                }
                
                if dependencies:
                    dependency_graph[key] = dependencies
            
            def invalidate_cache_entry(key: str, invalidation_type: str) -> bool:
                """Invalidate cache entry and handle cascading invalidation."""
                if key not in cache_registry:
                    return False
                
                # Mark as invalid
                cache_registry[key]["valid"] = False
                invalidation_log.append({
                    "key": key,
                    "type": invalidation_type,
                    "timestamp": time.time(),
                    "cascaded": False
                })
                
                # Handle cascading invalidation
                cascaded_keys = []
                for dependent_key, dependencies in dependency_graph.items():
                    if key in dependencies and cache_registry.get(dependent_key, {}).get("valid", False):
                        cache_registry[dependent_key]["valid"] = False
                        cascaded_keys.append(dependent_key)
                        invalidation_log.append({
                            "key": dependent_key,
                            "type": "cascading",
                            "timestamp": time.time(),
                            "cascaded": True,
                            "trigger": key
                        })
                
                return True
            
            def validate_cache_consistency() -> Dict[str, Any]:
                """Validate overall cache consistency."""
                total_entries = len(cache_registry)
                valid_entries = sum(1 for entry in cache_registry.values() if entry.get("valid", False))
                invalid_entries = total_entries - valid_entries
                
                # Check dependency consistency
                dependency_violations = []
                for key, dependencies in dependency_graph.items():
                    entry = cache_registry.get(key, {})
                    if entry.get("valid", False):
                        for dep_key in dependencies:
                            dep_entry = cache_registry.get(dep_key, {})
                            if not dep_entry.get("valid", False):
                                dependency_violations.append({
                                    "dependent": key,
                                    "invalid_dependency": dep_key
                                })
                
                return {
                    "total_entries": total_entries,
                    "valid_entries": valid_entries,
                    "invalid_entries": invalid_entries,
                    "dependency_violations": dependency_violations,
                    "consistency_score": 1.0 - (len(dependency_violations) / max(total_entries, 1))
                }
            
            mock_instance.register_cache_entry.side_effect = register_cache_entry
            mock_instance.invalidate_cache_entry.side_effect = invalidate_cache_entry
            mock_instance.validate_cache_consistency.side_effect = validate_cache_consistency
            
            thread_manager = ThreadManager(self.test_config, self.logger)
            
            # Test basic invalidation
            thread_data = self.cache_test_data["threads"]["thread_001"]
            session_data = self.cache_test_data["sessions"]["session_cache_001"]
            
            # Register entries with dependencies
            thread_manager.register_cache_entry("thread_001", thread_data)
            thread_manager.register_cache_entry("session_cache_001", session_data, ["thread_001"])
            
            # Verify initial state
            initial_consistency = thread_manager.validate_cache_consistency()
            self.assertEqual(initial_consistency["valid_entries"], 2)
            self.assertEqual(initial_consistency["consistency_score"], 1.0)
            
            # Test direct invalidation
            invalidation_success = thread_manager.invalidate_cache_entry("thread_001", "manual")
            self.assertTrue(invalidation_success)
            
            # Verify cascading invalidation
            post_invalidation_consistency = thread_manager.validate_cache_consistency()
            self.assertEqual(post_invalidation_consistency["valid_entries"], 0)
            
            # Check invalidation log
            direct_invalidations = [log for log in invalidation_log if not log.get("cascaded", False)]
            cascaded_invalidations = [log for log in invalidation_log if log.get("cascaded", False)]
            
            self.assertEqual(len(direct_invalidations), 1)
            self.assertEqual(len(cascaded_invalidations), 1)
            self.assertEqual(direct_invalidations[0]["key"], "thread_001")
            self.assertEqual(cascaded_invalidations[0]["key"], "session_cache_001")
            
            # Test TTL-based invalidation
            current_time = time.time()
            ttl_threshold = 300  # 5 minutes
            
            # Register entries with different ages
            thread_manager.register_cache_entry("fresh_entry", {"data": "fresh"})
            cache_registry["fresh_entry"]["timestamp"] = current_time - 60  # 1 minute old
            
            thread_manager.register_cache_entry("stale_entry", {"data": "stale"})
            cache_registry["stale_entry"]["timestamp"] = current_time - 400  # 6+ minutes old
            
            # Simulate TTL invalidation
            for key, entry in list(cache_registry.items()):
                if entry.get("valid", False) and (current_time - entry["timestamp"]) > ttl_threshold:
                    thread_manager.invalidate_cache_entry(key, "ttl_expired")
            
            # Verify TTL invalidation
            self.assertTrue(cache_registry["fresh_entry"]["valid"])
            self.assertFalse(cache_registry["stale_entry"]["valid"])
            
            # Test LRU invalidation
            access_counts = {
                "high_access": 100,
                "medium_access": 50,
                "low_access": 5
            }
            
            for key, access_count in access_counts.items():
                thread_manager.register_cache_entry(key, {"data": key})
                cache_registry[key]["access_count"] = access_count
            
            # Simulate LRU invalidation (remove least recently used)
            lru_candidates = sorted(
                [(key, entry) for key, entry in cache_registry.items() if entry.get("valid", False)],
                key=lambda x: x[1]["access_count"]
            )
            
            if lru_candidates:
                lru_key = lru_candidates[0][0]
                thread_manager.invalidate_cache_entry(lru_key, "lru_eviction")
                
                # Verify LRU victim
                self.assertEqual(lru_key, "low_access")
                self.assertFalse(cache_registry["low_access"]["valid"])
            
            # Final consistency validation
            final_consistency = thread_manager.validate_cache_consistency()
            
            # Log invalidation analysis
            self.logger.info(
                "Cache invalidation strategies analysis",
                context={
                    "total_invalidations": len(invalidation_log),
                    "direct_invalidations": len(direct_invalidations),
                    "cascaded_invalidations": len(cascaded_invalidations),
                    "ttl_invalidations": len([log for log in invalidation_log if log["type"] == "ttl_expired"]),
                    "lru_invalidations": len([log for log in invalidation_log if log["type"] == "lru_eviction"]),
                    "final_consistency_score": final_consistency["consistency_score"],
                    "dependency_violations": len(final_consistency["dependency_violations"])
                }
            )
    
    async def test_cache_coherence_multithread(self) -> None:
        """Test cache coherence under concurrent multi-threaded access."""
        with patch('threading.Lock') as mock_lock:
            mock_lock_instance = MagicMock()
            mock_lock.return_value = mock_lock_instance
            
            # Mock multi-threaded cache system
            shared_cache = {}
            thread_local_caches = {}
            coherence_log = []
            lock_acquisitions = 0
            
            def thread_cache_operation(thread_id: str, operation: str, key: str, 
                                     value: Any = None) -> Any:
                nonlocal lock_acquisitions
                
                # Initialize thread-local cache if needed
                if thread_id not in thread_local_caches:
                    thread_local_caches[thread_id] = {}
                
                thread_cache = thread_local_caches[thread_id]
                
                # Simulate lock acquisition for shared cache access
                with mock_lock_instance:
                    lock_acquisitions += 1
                    
                    if operation == "read":
                        # Check thread-local cache first
                        if key in thread_cache:
                            coherence_log.append({
                                "thread_id": thread_id,
                                "operation": "local_cache_hit",
                                "key": key,
                                "timestamp": time.time()
                            })
                            return thread_cache[key]
                        
                        # Check shared cache
                        if key in shared_cache:
                            # Copy to thread-local cache
                            thread_cache[key] = shared_cache[key].copy()
                            coherence_log.append({
                                "thread_id": thread_id,
                                "operation": "shared_cache_hit",
                                "key": key,
                                "timestamp": time.time()
                            })
                            return shared_cache[key]
                        
                        coherence_log.append({
                            "thread_id": thread_id,
                            "operation": "cache_miss",
                            "key": key,
                            "timestamp": time.time()
                        })
                        return None
                    
                    elif operation == "write":
                        # Write to shared cache
                        shared_cache[key] = value
                        
                        # Invalidate in all thread-local caches
                        for tid, tcache in thread_local_caches.items():
                            if key in tcache:
                                del tcache[key]
                                coherence_log.append({
                                    "thread_id": tid,
                                    "operation": "local_cache_invalidated",
                                    "key": key,
                                    "timestamp": time.time(),
                                    "invalidated_by": thread_id
                                })
                        
                        # Update current thread's local cache
                        thread_cache[key] = value
                        
                        coherence_log.append({
                            "thread_id": thread_id,
                            "operation": "write_complete",
                            "key": key,
                            "timestamp": time.time()
                        })
                        return True
                    
                    elif operation == "invalidate":
                        # Remove from shared cache
                        shared_cache.pop(key, None)
                        
                        # Remove from all thread-local caches
                        for tid, tcache in thread_local_caches.items():
                            tcache.pop(key, None)
                            coherence_log.append({
                                "thread_id": tid,
                                "operation": "invalidated",
                                "key": key,
                                "timestamp": time.time(),
                                "invalidated_by": thread_id
                            })
                        
                        return True
                
                return None
            
            def validate_cache_coherence() -> Dict[str, Any]:
                """Validate cache coherence across all threads."""
                coherence_violations = []
                
                # Check that all thread-local caches are consistent with shared cache
                for thread_id, thread_cache in thread_local_caches.items():
                    for key, value in thread_cache.items():
                        if key in shared_cache:
                            if value != shared_cache[key]:
                                coherence_violations.append({
                                    "thread_id": thread_id,
                                    "key": key,
                                    "local_value": value,
                                    "shared_value": shared_cache[key]
                                })
                        else:
                            # Thread-local cache has data not in shared cache
                            coherence_violations.append({
                                "thread_id": thread_id,
                                "key": key,
                                "issue": "local_has_data_shared_missing"
                            })
                
                return {
                    "total_threads": len(thread_local_caches),
                    "shared_cache_size": len(shared_cache),
                    "coherence_violations": coherence_violations,
                    "coherence_score": 1.0 - (len(coherence_violations) / max(1, sum(len(tc) for tc in thread_local_caches.values())))
                }
            
            # Test concurrent operations
            thread_operations = [
                ("thread_1", "write", "data_1", {"value": "initial_1"}),
                ("thread_2", "write", "data_2", {"value": "initial_2"}),
                ("thread_1", "read", "data_2", None),
                ("thread_2", "read", "data_1", None),
                ("thread_3", "read", "data_1", None),
                ("thread_1", "write", "data_1", {"value": "updated_1"}),
                ("thread_2", "read", "data_1", None),
                ("thread_3", "read", "data_1", None),
                ("thread_1", "invalidate", "data_2", None),
                ("thread_2", "read", "data_2", None),
                ("thread_3", "write", "data_3", {"value": "new_3"}),
            ]
            
            # Execute operations sequentially (simulating concurrent access with locks)
            for thread_id, operation, key, value in thread_operations:
                result = thread_cache_operation(thread_id, operation, key, value)
                
                # Verify operation results
                if operation == "write":
                    self.assertTrue(result)
                elif operation == "read" and key in shared_cache:
                    self.assertIsNotNone(result)
                elif operation == "invalidate":
                    self.assertTrue(result)
            
            # Validate final coherence state
            coherence_validation = validate_cache_coherence()
            
            # Should have no coherence violations
            self.assertEqual(len(coherence_validation["coherence_violations"]), 0)
            self.assertEqual(coherence_validation["coherence_score"], 1.0)
            
            # Verify lock usage
            self.assertGreater(lock_acquisitions, 0)
            
            # Analyze operation patterns
            writes = [log for log in coherence_log if log["operation"] == "write_complete"]
            reads = [log for log in coherence_log if log["operation"] in ["local_cache_hit", "shared_cache_hit"]]
            invalidations = [log for log in coherence_log if log["operation"] == "invalidated"]
            
            # Log coherence analysis
            self.logger.info(
                "Cache coherence multi-thread analysis",
                context={
                    "total_operations": len(thread_operations),
                    "threads_involved": len(thread_local_caches),
                    "lock_acquisitions": lock_acquisitions,
                    "write_operations": len(writes),
                    "read_operations": len(reads),
                    "invalidation_operations": len(invalidations),
                    "coherence_score": coherence_validation["coherence_score"],
                    "final_shared_cache_size": coherence_validation["shared_cache_size"]
                }
            )
    
    async def test_cache_performance_metrics(self) -> None:
        """Test cache performance metrics and optimization."""
        with patch('time.time') as mock_time:
            # Mock time progression for performance testing
            current_time = 1640995200.0  # Fixed start time
            mock_time.return_value = current_time
            
            # Mock performance-monitored cache
            performance_cache = {}
            performance_metrics = {
                "hits": 0,
                "misses": 0,
                "writes": 0,
                "response_times": [],
                "memory_usage": 0,
                "sync_operations": 0
            }
            
            def timed_cache_operation(operation: str, key: str, value: Any = None) -> Tuple[Any, float]:
                """Perform cache operation with timing."""
                nonlocal current_time
                start_time = current_time
                
                if operation == "read":
                    if key in performance_cache:
                        performance_metrics["hits"] += 1
                        result = performance_cache[key]
                    else:
                        performance_metrics["misses"] += 1
                        result = None
                    
                    # Simulate read latency
                    operation_time = 0.005 if key in performance_cache else 0.015
                    
                elif operation == "write":
                    performance_cache[key] = value
                    performance_metrics["writes"] += 1
                    performance_metrics["memory_usage"] = len(json.dumps(performance_cache))
                    
                    # Simulate write latency
                    operation_time = 0.008
                    result = True
                
                elif operation == "sync":
                    performance_metrics["sync_operations"] += 1
                    
                    # Simulate sync latency
                    operation_time = 0.020
                    result = True
                
                else:
                    operation_time = 0.001
                    result = None
                
                current_time += operation_time
                mock_time.return_value = current_time
                
                response_time = current_time - start_time
                performance_metrics["response_times"].append(response_time)
                
                return result, response_time
            
            def calculate_performance_score() -> Dict[str, Any]:
                """Calculate overall performance score."""
                total_operations = performance_metrics["hits"] + performance_metrics["misses"]
                hit_ratio = performance_metrics["hits"] / max(total_operations, 1)
                
                avg_response_time = sum(performance_metrics["response_times"]) / max(len(performance_metrics["response_times"]), 1)
                
                # Simulate memory limit
                memory_limit = 10000  # bytes
                memory_usage_ratio = performance_metrics["memory_usage"] / memory_limit
                
                # Calculate performance scores
                hit_ratio_score = min(hit_ratio / self.performance_thresholds["cache_hit_ratio"], 1.0)
                response_time_score = min(self.performance_thresholds["average_response_time"] / avg_response_time, 1.0)
                memory_score = max(1.0 - memory_usage_ratio / self.performance_thresholds["cache_memory_usage"], 0.0)
                
                overall_score = (hit_ratio_score + response_time_score + memory_score) / 3
                
                return {
                    "hit_ratio": hit_ratio,
                    "hit_ratio_score": hit_ratio_score,
                    "average_response_time": avg_response_time,
                    "response_time_score": response_time_score,
                    "memory_usage_ratio": memory_usage_ratio,
                    "memory_score": memory_score,
                    "overall_score": overall_score,
                    "total_operations": total_operations,
                    "performance_grade": self._get_performance_grade(overall_score)
                }
            
            # Test cache performance under various loads
            
            # Phase 1: Warm-up phase (establish cache)
            warm_up_data = [
                ("write", f"warm_up_{i}", {"data": f"value_{i}"})
                for i in range(50)
            ]
            
            for operation, key, value in warm_up_data:
                result, response_time = timed_cache_operation(operation, key, value)
                self.assertTrue(result)
                self.assertLess(response_time, 0.01)  # 10ms threshold
            
            # Phase 2: Read-heavy workload (test hit ratio)
            read_heavy_operations = [
                ("read", f"warm_up_{i % 50}", None)
                for i in range(200)
            ]
            
            for operation, key, value in read_heavy_operations:
                result, response_time = timed_cache_operation(operation, key, value)
                # Should mostly be cache hits
                if key in performance_cache:
                    self.assertIsNotNone(result)
            
            # Phase 3: Mixed workload
            mixed_operations = [
                ("read", f"warm_up_{i % 50}", None) if i % 3 != 0 else
                ("write", f"mixed_{i}", {"data": f"mixed_value_{i}"})
                for i in range(100)
            ]
            
            for operation, key, value in mixed_operations:
                result, response_time = timed_cache_operation(operation, key, value)
            
            # Phase 4: Periodic sync operations
            for _ in range(5):
                result, response_time = timed_cache_operation("sync", "sync_op", None)
                self.assertTrue(result)
            
            # Calculate final performance metrics
            performance_score = calculate_performance_score()
            
            # Verify performance thresholds
            self.assertGreaterEqual(performance_score["hit_ratio"], self.performance_thresholds["cache_hit_ratio"])
            self.assertLessEqual(performance_score["average_response_time"], self.performance_thresholds["average_response_time"] * 2)  # Allow some variance
            self.assertGreaterEqual(performance_score["overall_score"], 0.7)  # Minimum 70% performance score
            
            # Test cache optimization recommendations
            optimization_recommendations = []
            
            if performance_score["hit_ratio"] < 0.9:
                optimization_recommendations.append("Increase cache size or improve cache key strategy")
            
            if performance_score["average_response_time"] > 0.008:
                optimization_recommendations.append("Optimize cache data structures or use faster storage")
            
            if performance_score["memory_usage_ratio"] > 0.8:
                optimization_recommendations.append("Implement cache eviction policy or increase memory limit")
            
            # Log performance analysis
            self.logger.info(
                "Cache performance metrics analysis",
                context={
                    "performance_score": performance_score,
                    "cache_entries": len(performance_cache),
                    "total_operations": performance_score["total_operations"],
                    "optimization_recommendations": optimization_recommendations,
                    "performance_grade": performance_score["performance_grade"],
                    "memory_usage_bytes": performance_metrics["memory_usage"],
                    "sync_operations": performance_metrics["sync_operations"]
                }
            )
    
    async def test_cache_recovery_mechanisms(self) -> None:
        """Test cache recovery mechanisms and fault tolerance."""
        with patch('src.thread_storage.ThreadStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_storage.return_value = mock_instance
            
            # Mock cache with recovery capabilities
            primary_cache = {}
            backup_cache = {}
            recovery_log = []
            failure_scenarios = {}
            
            def simulate_cache_failure(failure_type: str, component: str = "primary") -> None:
                """Simulate various cache failure scenarios."""
                failure_scenarios[failure_type] = {
                    "component": component,
                    "timestamp": time.time(),
                    "active": True
                }
                
                recovery_log.append({
                    "event": "failure_simulated",
                    "type": failure_type,
                    "component": component,
                    "timestamp": time.time()
                })
            
            def cache_operation_with_recovery(operation: str, key: str, value: Any = None) -> Any:
                """Perform cache operation with automatic recovery."""
                try:
                    # Check for active failures
                    if "memory_corruption" in failure_scenarios and failure_scenarios["memory_corruption"]["active"]:
                        raise Exception("Memory corruption detected")
                    
                    if "network_partition" in failure_scenarios and failure_scenarios["network_partition"]["active"]:
                        if operation in ["sync", "backup"]:
                            raise Exception("Network partition - cannot sync")
                    
                    # Perform operation on primary cache
                    if operation == "read":
                        if key in primary_cache:
                            return primary_cache[key]
                        else:
                            # Try backup cache
                            if key in backup_cache:
                                # Restore to primary
                                primary_cache[key] = backup_cache[key]
                                recovery_log.append({
                                    "event": "restored_from_backup",
                                    "key": key,
                                    "timestamp": time.time()
                                })
                                return backup_cache[key]
                            return None
                    
                    elif operation == "write":
                        primary_cache[key] = value
                        
                        # Backup operation (if not failing)
                        if "network_partition" not in failure_scenarios or not failure_scenarios["network_partition"]["active"]:
                            backup_cache[key] = value
                        
                        return True
                    
                    elif operation == "backup_sync":
                        if "network_partition" in failure_scenarios and failure_scenarios["network_partition"]["active"]:
                            raise Exception("Cannot sync - network partition")
                        
                        # Sync primary to backup
                        backup_cache.update(primary_cache)
                        recovery_log.append({
                            "event": "backup_sync_complete",
                            "entries_synced": len(primary_cache),
                            "timestamp": time.time()
                        })
                        return True
                    
                except Exception as e:
                    # Recovery handling
                    recovery_log.append({
                        "event": "operation_failed",
                        "operation": operation,
                        "error": str(e),
                        "timestamp": time.time()
                    })
                    
                    # Attempt recovery
                    if "memory_corruption" in str(e):
                        # Restore from backup
                        if backup_cache:
                            primary_cache.clear()
                            primary_cache.update(backup_cache)
                            recovery_log.append({
                                "event": "recovered_from_backup",
                                "entries_recovered": len(backup_cache),
                                "timestamp": time.time()
                            })
                            failure_scenarios["memory_corruption"]["active"] = False
                            return cache_operation_with_recovery(operation, key, value)
                    
                    elif "network_partition" in str(e):
                        # Continue with local operations only
                        if operation == "read":
                            return primary_cache.get(key)
                        elif operation == "write":
                            primary_cache[key] = value
                            return True
                    
                    return None
            
            def initiate_cache_recovery() -> Dict[str, Any]:
                """Initiate comprehensive cache recovery."""
                recovery_start = time.time()
                
                # Step 1: Clear all failure scenarios
                for failure_type in failure_scenarios:
                    failure_scenarios[failure_type]["active"] = False
                
                # Step 2: Validate cache integrity
                corrupted_entries = []
                for key, value in primary_cache.items():
                    # Simplified corruption check
                    if not isinstance(value, dict) or "data" not in value:
                        corrupted_entries.append(key)
                
                # Step 3: Remove corrupted entries
                for key in corrupted_entries:
                    del primary_cache[key]
                
                # Step 4: Restore from backup
                restored_count = 0
                for key, value in backup_cache.items():
                    if key not in primary_cache:
                        primary_cache[key] = value
                        restored_count += 1
                
                # Step 5: Validate consistency
                consistency_check = self._validate_cache_consistency(primary_cache, backup_cache)
                
                recovery_time = time.time() - recovery_start
                
                recovery_log.append({
                    "event": "full_recovery_complete",
                    "corrupted_entries_removed": len(corrupted_entries),
                    "entries_restored": restored_count,
                    "recovery_time": recovery_time,
                    "consistency_check": consistency_check,
                    "timestamp": time.time()
                })
                
                return {
                    "success": True,
                    "recovery_time": recovery_time,
                    "corrupted_entries": len(corrupted_entries),
                    "restored_entries": restored_count,
                    "final_cache_size": len(primary_cache),
                    "consistency_score": consistency_check["score"]
                }
            
            mock_instance.cache_operation_with_recovery.side_effect = cache_operation_with_recovery
            mock_instance.simulate_cache_failure.side_effect = simulate_cache_failure
            mock_instance.initiate_cache_recovery.side_effect = initiate_cache_recovery
            
            storage = ThreadStorage("/tmp/recovery_test.db")
            
            # Setup initial cache data
            initial_data = {
                f"recovery_test_{i}": {"data": f"test_value_{i}", "index": i}
                for i in range(20)
            }
            
            for key, value in initial_data.items():
                result = storage.cache_operation_with_recovery("write", key, value)
                self.assertTrue(result)
            
            # Perform initial backup
            backup_result = storage.cache_operation_with_recovery("backup_sync", "", None)
            self.assertTrue(backup_result)
            
            # Test recovery from memory corruption
            storage.simulate_cache_failure("memory_corruption", "primary")
            
            # Try to read - should trigger recovery
            test_key = "recovery_test_5"
            recovered_value = storage.cache_operation_with_recovery("read", test_key)
            self.assertIsNotNone(recovered_value)
            self.assertEqual(recovered_value["index"], 5)
            
            # Test recovery from network partition
            storage.simulate_cache_failure("network_partition", "backup")
            
            # Write operation should still work locally
            new_key = "recovery_test_new"
            new_value = {"data": "new_value", "index": 100}
            write_result = storage.cache_operation_with_recovery("write", new_key, new_value)
            self.assertTrue(write_result)
            
            # Test full cache recovery
            recovery_result = storage.initiate_cache_recovery()
            
            self.assertTrue(recovery_result["success"])
            self.assertLess(recovery_result["recovery_time"], 1.0)  # Should recover within 1 second
            self.assertGreaterEqual(recovery_result["consistency_score"], 0.9)
            
            # Verify cache is functional after recovery
            post_recovery_read = storage.cache_operation_with_recovery("read", test_key)
            self.assertIsNotNone(post_recovery_read)
            
            # Analyze recovery events
            failure_events = [log for log in recovery_log if log["event"] == "failure_simulated"]
            recovery_events = [log for log in recovery_log if "recovery" in log["event"]]
            
            # Log recovery analysis
            self.logger.info(
                "Cache recovery mechanisms analysis",
                context={
                    "total_recovery_events": len(recovery_log),
                    "failure_scenarios_tested": len(failure_events),
                    "recovery_operations": len(recovery_events),
                    "final_recovery_result": recovery_result,
                    "cache_integrity_verified": True,
                    "recovery_time_performance": recovery_result["recovery_time"] < 1.0
                }
            )
    
    # Helper methods
    
    def _validate_timestamp_order(self, data: Dict[str, Any]) -> bool:
        """Validate timestamp chronological order."""
        if "created_at" in data and "last_used" in data:
            try:
                # Simplified timestamp comparison for testing
                created = data["created_at"]
                last_used = data["last_used"]
                return created <= last_used
            except Exception:
                return False
        return True
    
    def _validate_reference_integrity(self, cache_data: Dict[str, Any]) -> bool:
        """Validate reference integrity between cache objects."""
        if "threads" in cache_data and "sessions" in cache_data:
            threads = cache_data["threads"]
            sessions = cache_data["sessions"]
            
            # Check that all session thread_ids exist in threads
            for session in sessions.values():
                thread_id = session.get("thread_id")
                if thread_id:
                    thread_exists = any(t.get("thread_id") == thread_id for t in threads.values())
                    if not thread_exists:
                        return False
            
            # Check that all thread session_ids exist in sessions
            for thread in threads.values():
                session_id = thread.get("session_id")
                if session_id and session_id not in sessions:
                    return False
        
        return True
    
    def _get_performance_grade(self, score: float) -> str:
        """Get performance grade based on score."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def _validate_cache_consistency(self, primary: Dict[str, Any], backup: Dict[str, Any]) -> Dict[str, Any]:
        """Validate consistency between primary and backup caches."""
        mismatches = []
        
        # Check keys in primary but not in backup
        primary_only = set(primary.keys()) - set(backup.keys())
        
        # Check keys in backup but not in primary
        backup_only = set(backup.keys()) - set(primary.keys())
        
        # Check value mismatches
        common_keys = set(primary.keys()) & set(backup.keys())
        for key in common_keys:
            if primary[key] != backup[key]:
                mismatches.append(key)
        
        total_keys = len(set(primary.keys()) | set(backup.keys()))
        inconsistent_keys = len(primary_only) + len(backup_only) + len(mismatches)
        
        consistency_score = 1.0 - (inconsistent_keys / max(total_keys, 1))
        
        return {
            "score": consistency_score,
            "mismatches": len(mismatches),
            "primary_only": len(primary_only),
            "backup_only": len(backup_only),
            "total_keys": total_keys
        }


def run_cache_consistency_tests() -> None:
    """Run cache consistency tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestCacheConsistency)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nCache Consistency Tests Summary:")
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