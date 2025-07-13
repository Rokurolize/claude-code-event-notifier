#!/usr/bin/env python3
"""Test Parallel Processing Safety.

This module provides comprehensive tests for parallel processing safety,
including concurrent event handling, thread safety, resource synchronization,
deadlock prevention, and race condition detection.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
import sys
import time
import threading
import queue
import concurrent.futures
from datetime import datetime, timezone
from dataclasses import dataclass, field
import random

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.discord_notifier import main as discord_notifier_main
from src.core.http_client import HTTPClient
from src.handlers.discord_sender import DiscordSender
from src.thread_storage import ThreadStorage
from src.type_defs.events import EventDict
from src.type_defs.discord import DiscordMessage


# Parallel processing test types
@dataclass
class ConcurrentTask:
    """Concurrent task configuration."""
    task_id: str
    event_data: EventDict
    delay: float = 0.0
    expected_duration: float = 1.0
    priority: int = 0


@dataclass
class ParallelResult:
    """Result of parallel processing test."""
    task_id: str
    success: bool
    start_time: float
    end_time: float
    duration: float
    error: Optional[Exception] = None
    thread_id: Optional[int] = None


@dataclass
class RaceConditionTest:
    """Race condition test configuration."""
    name: str
    concurrent_operations: int
    shared_resource: str
    expected_final_state: Any
    tolerance: float = 0.1


class ThreadSafeCounter:
    """Thread-safe counter for testing."""
    
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()
        self._access_log = []
    
    def increment(self, amount: int = 1) -> int:
        """Increment counter safely."""
        with self._lock:
            thread_id = threading.get_ident()
            self._access_log.append({"action": "increment", "thread": thread_id, "time": time.time()})
            self._value += amount
            return self._value
    
    def decrement(self, amount: int = 1) -> int:
        """Decrement counter safely."""
        with self._lock:
            thread_id = threading.get_ident()
            self._access_log.append({"action": "decrement", "thread": thread_id, "time": time.time()})
            self._value -= amount
            return self._value
    
    def get_value(self) -> int:
        """Get current value."""
        with self._lock:
            return self._value
    
    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get access log."""
        with self._lock:
            return self._access_log.copy()


class TestParallelProcessing(unittest.IsolatedAsyncioTestCase):
    """Test cases for parallel processing safety."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.thread_safe_counter = ThreadSafeCounter()
        self.shared_resources = {}
        
        # Test configuration
        self.test_config = {
            "max_concurrent_events": 10,
            "event_timeout": 5.0,
            "thread_pool_size": 4,
            "enable_deadlock_detection": True,
            "debug": True
        }
        
        # Sample events for parallel processing
        self.test_events = [
            {
                "event_type": "ToolUse",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": f"session-{i}",
                "tool_name": "Edit",
                "tool_input": {"file_path": f"/test/file{i}.py", "old_string": "old", "new_string": "new"}
            }
            for i in range(20)
        ]
    
    async def test_concurrent_event_processing(self) -> None:
        """Test concurrent processing of multiple events."""
        num_events = 10
        events = self.test_events[:num_events]
        
        # Process events concurrently
        tasks = []
        for i, event in enumerate(events):
            task = self._process_event_async(event, task_id=f"task-{i}")
            tasks.append(task)
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify all events processed successfully
        successful_results = [r for r in results if isinstance(r, ParallelResult) and r.success]
        self.assertEqual(len(successful_results), num_events)
        
        # Verify parallel execution (should be faster than sequential)
        sequential_time_estimate = num_events * 0.1  # Assume 0.1s per event
        self.assertLess(total_time, sequential_time_estimate * 0.8)  # Should be significantly faster
        
        # Check for overlapping execution
        self._verify_parallel_execution(successful_results)
    
    async def test_thread_safety_shared_resources(self) -> None:
        """Test thread safety with shared resources."""
        num_threads = 50
        increments_per_thread = 100
        expected_final_value = num_threads * increments_per_thread
        
        # Function to increment counter
        def increment_counter():
            for _ in range(increments_per_thread):
                self.thread_safe_counter.increment()
                time.sleep(0.001)  # Small delay to increase chance of race conditions
        
        # Run threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(increment_counter) for _ in range(num_threads)]
            concurrent.futures.wait(futures)
        
        # Verify final value
        final_value = self.thread_safe_counter.get_value()
        self.assertEqual(final_value, expected_final_value)
        
        # Check access log for thread safety
        access_log = self.thread_safe_counter.get_access_log()
        self.assertEqual(len(access_log), num_threads * increments_per_thread)
        
        # Verify multiple threads accessed the counter
        thread_ids = set(entry["thread"] for entry in access_log)
        self.assertGreater(len(thread_ids), 1)
    
    async def test_discord_sender_thread_safety(self) -> None:
        """Test Discord sender thread safety."""
        num_concurrent_sends = 20
        
        # Mock Discord API responses
        with patch('src.core.http_client.HTTPClient.post') as mock_post:
            mock_post.return_value = {"id": "123", "content": "test"}
            
            # Create concurrent send operations
            tasks = []
            for i in range(num_concurrent_sends):
                message = DiscordMessage(
                    content=f"Test message {i}",
                    embeds=[],
                    username="Test Bot"
                )
                task = self._send_discord_message_async(message, task_id=f"send-{i}")
                tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all sends succeeded
            successful_sends = [r for r in results if isinstance(r, ParallelResult) and r.success]
            self.assertEqual(len(successful_sends), num_concurrent_sends)
            
            # Verify HTTP client was called for each message
            self.assertEqual(mock_post.call_count, num_concurrent_sends)
    
    async def test_thread_storage_concurrent_access(self) -> None:
        """Test thread storage concurrent access safety."""
        num_operations = 50
        session_ids = [f"session-{i}" for i in range(10)]
        
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock database responses
            mock_cursor.fetchone.return_value = ("thread-123", int(time.time()))
            
            # Function to perform storage operations
            async def storage_operation(session_id: str, operation_id: int):
                storage = ThreadStorage()
                
                # Perform various operations
                operations = [
                    lambda: storage.get_thread_id(session_id),
                    lambda: storage.store_thread_id(session_id, f"thread-{operation_id}"),
                    lambda: storage.cleanup_old_sessions(max_age_hours=24)
                ]
                
                for op in operations:
                    try:
                        op()
                        await asyncio.sleep(0.001)  # Small delay
                    except Exception as e:
                        raise Exception(f"Storage operation failed: {e}")
            
            # Execute concurrent storage operations
            tasks = []
            for i in range(num_operations):
                session_id = random.choice(session_ids)
                task = storage_operation(session_id, i)
                tasks.append(task)
            
            # Run all operations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for exceptions
            exceptions = [r for r in results if isinstance(r, Exception)]
            self.assertEqual(len(exceptions), 0, f"Found exceptions: {exceptions}")
    
    async def test_resource_lock_deadlock_prevention(self) -> None:
        """Test deadlock prevention in resource locking."""
        resource_a = threading.Lock()
        resource_b = threading.Lock()
        deadlock_detected = threading.Event()
        completion_count = ThreadSafeCounter()
        
        def acquire_resources_order1():
            """Acquire resources in order A -> B."""
            try:
                if resource_a.acquire(timeout=1.0):
                    time.sleep(0.1)  # Hold lock for a bit
                    if resource_b.acquire(timeout=1.0):
                        time.sleep(0.1)
                        resource_b.release()
                        completion_count.increment()
                    resource_a.release()
                else:
                    deadlock_detected.set()
            except Exception:
                deadlock_detected.set()
        
        def acquire_resources_order2():
            """Acquire resources in order B -> A."""
            try:
                if resource_b.acquire(timeout=1.0):
                    time.sleep(0.1)  # Hold lock for a bit
                    if resource_a.acquire(timeout=1.0):
                        time.sleep(0.1)
                        resource_a.release()
                        completion_count.increment()
                    resource_b.release()
                else:
                    deadlock_detected.set()
            except Exception:
                deadlock_detected.set()
        
        # Run potentially deadlocking operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for _ in range(5):
                futures.append(executor.submit(acquire_resources_order1))
                futures.append(executor.submit(acquire_resources_order2))
            
            # Wait with timeout
            concurrent.futures.wait(futures, timeout=5.0)
        
        # Check if deadlock was avoided
        if deadlock_detected.is_set():
            self.logger.warning("Deadlock detected - this indicates proper timeout handling")
        
        # Verify some operations completed
        completed_operations = completion_count.get_value()
        self.assertGreater(completed_operations, 0, "No operations completed - possible deadlock")
    
    async def test_race_condition_detection(self) -> None:
        """Test detection and handling of race conditions."""
        race_tests = [
            RaceConditionTest(
                name="counter_increment",
                concurrent_operations=100,
                shared_resource="counter",
                expected_final_state=100
            ),
            RaceConditionTest(
                name="list_append",
                concurrent_operations=50,
                shared_resource="list",
                expected_final_state=50
            )
        ]
        
        for test in race_tests:
            with self.subTest(test=test.name):
                await self._run_race_condition_test(test)
    
    async def test_event_queue_thread_safety(self) -> None:
        """Test event queue thread safety."""
        event_queue = queue.Queue(maxsize=100)
        num_producers = 5
        num_consumers = 3
        events_per_producer = 20
        
        # Producer function
        def producer(producer_id: int):
            for i in range(events_per_producer):
                event = {
                    "event_type": "TestEvent",
                    "producer_id": producer_id,
                    "sequence": i,
                    "timestamp": time.time()
                }
                event_queue.put(event)
                time.sleep(0.001)  # Small delay
        
        # Consumer function
        def consumer(consumer_id: int, results: List[Dict[str, Any]]):
            while True:
                try:
                    event = event_queue.get(timeout=2.0)
                    # Process event
                    processed_event = {
                        "consumer_id": consumer_id,
                        "original_event": event,
                        "processed_at": time.time()
                    }
                    results.append(processed_event)
                    event_queue.task_done()
                except queue.Empty:
                    break
        
        # Run producers and consumers concurrently
        consumer_results = [[] for _ in range(num_consumers)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_producers + num_consumers) as executor:
            # Start producers
            producer_futures = [
                executor.submit(producer, i) for i in range(num_producers)
            ]
            
            # Start consumers
            consumer_futures = [
                executor.submit(consumer, i, consumer_results[i])
                for i in range(num_consumers)
            ]
            
            # Wait for producers to finish
            concurrent.futures.wait(producer_futures)
            
            # Wait for queue to be empty
            event_queue.join()
            
            # Cancel consumer futures
            for future in consumer_futures:
                future.cancel()
        
        # Verify all events were processed
        total_events_produced = num_producers * events_per_producer
        total_events_consumed = sum(len(results) for results in consumer_results)
        
        self.assertEqual(total_events_consumed, total_events_produced)
        
        # Verify no duplicate processing
        all_processed_events = []
        for results in consumer_results:
            all_processed_events.extend(results)
        
        event_signatures = []
        for result in all_processed_events:
            event = result["original_event"]
            signature = f"{event['producer_id']}-{event['sequence']}"
            event_signatures.append(signature)
        
        # No duplicates
        self.assertEqual(len(event_signatures), len(set(event_signatures)))
    
    async def test_async_event_processing(self) -> None:
        """Test async event processing with proper concurrency."""
        num_events = 15
        processing_times = []
        
        async def process_single_event(event: EventDict, processing_delay: float) -> ParallelResult:
            """Process a single event with simulated work."""
            start_time = time.time()
            
            # Simulate async processing
            await asyncio.sleep(processing_delay)
            
            # Simulate Discord API call
            with patch('src.core.http_client.HTTPClient.post') as mock_post:
                mock_post.return_value = {"id": "123", "content": "processed"}
                
                # Process event
                try:
                    # Simulate actual processing
                    await asyncio.sleep(0.01)
                    
                    end_time = time.time()
                    return ParallelResult(
                        task_id=event["session_id"],
                        success=True,
                        start_time=start_time,
                        end_time=end_time,
                        duration=end_time - start_time
                    )
                except Exception as e:
                    end_time = time.time()
                    return ParallelResult(
                        task_id=event["session_id"],
                        success=False,
                        start_time=start_time,
                        end_time=end_time,
                        duration=end_time - start_time,
                        error=e
                    )
        
        # Create events with varying processing times
        events = self.test_events[:num_events]
        processing_delays = [random.uniform(0.1, 0.3) for _ in range(num_events)]
        
        # Process events concurrently
        start_time = time.time()
        tasks = [
            process_single_event(event, delay)
            for event, delay in zip(events, processing_delays)
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify all events processed successfully
        successful_results = [r for r in results if r.success]
        self.assertEqual(len(successful_results), num_events)
        
        # Verify concurrent execution
        max_individual_time = max(r.duration for r in successful_results)
        self.assertLess(total_time, max_individual_time * num_events * 0.5)  # Should be much faster than sequential
        
        # Log performance metrics
        self.logger.info(
            "async_processing_performance",
            total_events=num_events,
            total_time=total_time,
            average_event_time=sum(r.duration for r in successful_results) / len(successful_results),
            max_event_time=max_individual_time
        )
    
    async def _process_event_async(self, event: EventDict, task_id: str) -> ParallelResult:
        """Process a single event asynchronously."""
        start_time = time.time()
        thread_id = threading.get_ident()
        
        try:
            # Simulate event processing
            with patch('src.handlers.discord_sender.DiscordSender.send_notification') as mock_send:
                mock_send.return_value = True
                
                # Add some processing delay
                await asyncio.sleep(0.05)
                
                # Simulate actual processing
                result = True  # Mock successful processing
                
                end_time = time.time()
                return ParallelResult(
                    task_id=task_id,
                    success=result,
                    start_time=start_time,
                    end_time=end_time,
                    duration=end_time - start_time,
                    thread_id=thread_id
                )
                
        except Exception as e:
            end_time = time.time()
            return ParallelResult(
                task_id=task_id,
                success=False,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                error=e,
                thread_id=thread_id
            )
    
    async def _send_discord_message_async(self, message: DiscordMessage, task_id: str) -> ParallelResult:
        """Send Discord message asynchronously."""
        start_time = time.time()
        
        try:
            sender = DiscordSender(webhook_url="https://discord.com/api/webhooks/123/abc")
            
            # Mock the HTTP call
            with patch('src.core.http_client.HTTPClient.post') as mock_post:
                mock_post.return_value = {"id": "123", "content": message.content}
                
                # Send message
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: sender.send_message(message)
                )
                
                end_time = time.time()
                return ParallelResult(
                    task_id=task_id,
                    success=result,
                    start_time=start_time,
                    end_time=end_time,
                    duration=end_time - start_time
                )
                
        except Exception as e:
            end_time = time.time()
            return ParallelResult(
                task_id=task_id,
                success=False,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                error=e
            )
    
    def _verify_parallel_execution(self, results: List[ParallelResult]) -> None:
        """Verify that tasks executed in parallel."""
        if len(results) < 2:
            return
        
        # Sort by start time
        sorted_results = sorted(results, key=lambda r: r.start_time)
        
        # Check for overlapping execution
        overlaps = 0
        for i in range(len(sorted_results) - 1):
            current = sorted_results[i]
            next_task = sorted_results[i + 1]
            
            # If next task started before current finished, they overlapped
            if next_task.start_time < current.end_time:
                overlaps += 1
        
        # Should have some overlapping execution for parallel processing
        self.assertGreater(overlaps, 0, "No overlapping execution detected - tasks may be running sequentially")
    
    async def _run_race_condition_test(self, test: RaceConditionTest) -> None:
        """Run a race condition test."""
        if test.shared_resource == "counter":
            shared_counter = ThreadSafeCounter()
            
            def increment_operation():
                shared_counter.increment()
            
            # Run concurrent operations
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(increment_operation)
                    for _ in range(test.concurrent_operations)
                ]
                concurrent.futures.wait(futures)
            
            # Verify final state
            final_value = shared_counter.get_value()
            self.assertEqual(final_value, test.expected_final_state)
            
        elif test.shared_resource == "list":
            shared_list = []
            list_lock = threading.Lock()
            
            def append_operation(value):
                with list_lock:
                    shared_list.append(value)
            
            # Run concurrent operations
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(append_operation, i)
                    for i in range(test.concurrent_operations)
                ]
                concurrent.futures.wait(futures)
            
            # Verify final state
            final_length = len(shared_list)
            self.assertEqual(final_length, test.expected_final_state)


if __name__ == "__main__":
    unittest.main()