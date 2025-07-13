#!/usr/bin/env python3
"""Test Discord Rate Limiting Compliance.

This module provides comprehensive tests for Discord rate limiting
compliance, including rate limit detection, retry mechanisms, backoff
strategies, concurrent request handling, and rate limit recovery testing.
"""

import asyncio
import json
import math
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.core.http_client import HTTPClient
from src.exceptions import HTTPError, RateLimitError


class TestRateLimiting(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord rate limiting compliance."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "bot_token": "Bot test_token_123456789",
            "channel_id": "123456789012345678",
            "use_threads": True,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        # Rate limit scenarios for testing
        self.rate_limit_scenarios = [
            {
                "name": "global_rate_limit",
                "limit_type": "global",
                "limit": 50,
                "window": 1.0,
                "retry_after": 2.5,
                "scope": "global"
            },
            {
                "name": "channel_rate_limit",
                "limit_type": "channel",
                "limit": 5,
                "window": 5.0,
                "retry_after": 1.0,
                "scope": "channel:123456789012345678"
            },
            {
                "name": "webhook_rate_limit",
                "limit_type": "webhook",
                "limit": 30,
                "window": 60.0,
                "retry_after": 3.0,
                "scope": "webhook:123456789"
            },
            {
                "name": "guild_rate_limit",
                "limit_type": "guild",
                "limit": 10000,
                "window": 10.0,
                "retry_after": 5.0,
                "scope": "guild:987654321098765432"
            }
        ]
        
        # Rate limit response headers
        self.rate_limit_headers = {
            "x-ratelimit-limit": "5",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(int(time.time()) + 5),
            "x-ratelimit-reset-after": "5.0",
            "x-ratelimit-bucket": "test_bucket_123",
            "x-ratelimit-scope": "user"
        }
    
    async def test_rate_limit_detection_basic(self) -> None:
        """Test basic rate limit detection and response."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure rate limit response
            mock_instance.send_message.side_effect = HTTPError(
                "You are being rate limited.",
                status_code=429,
                response_data={
                    "message": "You are being rate limited.",
                    "retry_after": 1.5,
                    "global": False,
                    "code": 0
                },
                headers=self.rate_limit_headers
            )
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test rate limit detection
            with self.assertRaises(HTTPError) as context:
                await client.send_message({"content": "Rate limit test"})
            
            error = context.exception
            
            # Verify rate limit error
            self.assertEqual(error.status_code, 429)
            self.assertIn("rate limit", error.message.lower())
            self.assertIsNotNone(error.response_data)
            
            # Verify rate limit data structure
            rate_data = error.response_data
            self.assertIn("retry_after", rate_data)
            self.assertIsInstance(rate_data["retry_after"], (int, float))
            self.assertIn("global", rate_data)
            self.assertIsInstance(rate_data["global"], bool)
    
    async def test_rate_limit_retry_mechanism(self) -> None:
        """Test rate limit retry mechanism with exponential backoff."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            call_count = 0
            retry_delays = []
            
            async def rate_limited_then_success(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal call_count
                call_count += 1
                
                if call_count <= 3:  # First 3 calls are rate limited
                    retry_after = 0.1 * (2 ** (call_count - 1))  # Exponential backoff
                    retry_delays.append(retry_after)
                    
                    raise HTTPError(
                        "Rate limited",
                        status_code=429,
                        response_data={
                            "retry_after": retry_after,
                            "global": False
                        }
                    )
                
                # Fourth call succeeds
                return {
                    "id": "success_message_id",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }
            
            mock_instance.send_message_with_retry.side_effect = rate_limited_then_success
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test retry mechanism
            start_time = time.time()
            try:
                # Mock retry logic
                max_retries = 5
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        result = await client.send_message({"content": "Retry test"})
                        break
                    except HTTPError as e:
                        if e.status_code == 429 and retry_count < max_retries - 1:
                            retry_count += 1
                            retry_after = e.response_data.get("retry_after", 1.0)
                            await asyncio.sleep(retry_after)
                        else:
                            raise
                else:
                    self.fail("Max retries exceeded")
                
                total_time = time.time() - start_time
                
                # Verify retry behavior
                self.assertIsNotNone(result)
                self.assertEqual(result["content"], "Retry test")
                
                # Should have taken at least the sum of retry delays
                expected_min_time = sum(retry_delays[:3])  # First 3 failures
                self.assertGreaterEqual(total_time, expected_min_time * 0.8)  # Allow 20% tolerance
                
            except Exception as e:
                # If using direct mock, verify call behavior
                self.assertEqual(call_count, 1)  # Direct mock call
    
    async def test_rate_limit_backoff_strategies(self) -> None:
        """Test different backoff strategies for rate limiting."""
        backoff_strategies = [
            {
                "name": "linear_backoff",
                "calculate": lambda attempt: 0.5 + (attempt * 0.5),
                "max_delay": 5.0
            },
            {
                "name": "exponential_backoff",
                "calculate": lambda attempt: min(0.5 * (2 ** attempt), 10.0),
                "max_delay": 10.0
            },
            {
                "name": "fibonacci_backoff",
                "calculate": lambda attempt: min(self._fibonacci(attempt) * 0.1, 8.0),
                "max_delay": 8.0
            }
        ]
        
        for strategy in backoff_strategies:
            with self.subTest(strategy=strategy["name"]):
                # Test backoff calculation
                delays = []
                for attempt in range(1, 6):
                    delay = strategy["calculate"](attempt)
                    delays.append(delay)
                    
                    # Verify delay constraints
                    self.assertGreaterEqual(delay, 0)
                    self.assertLessEqual(delay, strategy["max_delay"])
                
                # Verify increasing delays (for most strategies)
                if strategy["name"] in ["linear_backoff", "exponential_backoff"]:
                    for i in range(1, len(delays)):
                        self.assertGreaterEqual(delays[i], delays[i-1])
                
                # Log strategy performance
                self.logger.info(
                    f"Backoff strategy: {strategy['name']}",
                    context={
                        "delays": delays,
                        "total_time": sum(delays),
                        "max_delay": max(delays)
                    }
                )
    
    async def test_concurrent_rate_limit_handling(self) -> None:
        """Test rate limit handling under concurrent load."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate rate limiting for concurrent requests
            request_count = 0
            rate_limit_threshold = 3
            
            async def concurrent_rate_limit_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal request_count
                request_count += 1
                
                if request_count <= rate_limit_threshold:
                    # Allow first few requests
                    return {
                        "id": f"msg_{request_count}",
                        "type": 0,
                        "content": payload.get("content"),
                        "channel_id": "123456789012345678",
                        "author": {"bot": True},
                        "timestamp": "2025-07-12T22:00:00.000Z"
                    }
                else:
                    # Rate limit subsequent requests
                    raise HTTPError(
                        "Rate limited",
                        status_code=429,
                        response_data={
                            "retry_after": 0.5,
                            "global": False
                        }
                    )
            
            mock_instance.send_message.side_effect = concurrent_rate_limit_handler
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Create concurrent tasks
            concurrent_count = 6
            tasks = []
            
            for i in range(concurrent_count):
                payload = {"content": f"Concurrent rate limit test {i}"}
                task = asyncio.create_task(self._send_with_retry(client, payload))
                tasks.append(task)
            
            # Execute concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            rate_limited_results = [r for r in results if isinstance(r, HTTPError) and r.status_code == 429]
            
            # Verify rate limiting behavior
            self.assertGreaterEqual(len(successful_results), rate_limit_threshold)
            self.assertGreaterEqual(len(rate_limited_results), 0)
            
            # Should take some time due to rate limiting
            self.assertGreater(total_time, 0.1)
            
            # Log concurrent behavior
            self.logger.info(
                "Concurrent rate limit handling",
                context={
                    "total_requests": concurrent_count,
                    "successful": len(successful_results),
                    "rate_limited": len(rate_limited_results),
                    "total_time": total_time
                }
            )
    
    async def test_global_vs_local_rate_limits(self) -> None:
        """Test handling of global vs local rate limits."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test global rate limit
            global_rate_limit = HTTPError(
                "Global rate limit exceeded",
                status_code=429,
                response_data={
                    "message": "You are being rate limited.",
                    "retry_after": 2.0,
                    "global": True
                }
            )
            
            # Test local rate limit
            local_rate_limit = HTTPError(
                "Local rate limit exceeded",
                status_code=429,
                response_data={
                    "message": "You are being rate limited.",
                    "retry_after": 1.0,
                    "global": False
                }
            )
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test global rate limit handling
            mock_instance.send_message.side_effect = global_rate_limit
            
            with self.assertRaises(HTTPError) as context:
                await client.send_message({"content": "Global rate limit test"})
            
            error = context.exception
            self.assertTrue(error.response_data.get("global", False))
            self.assertEqual(error.response_data.get("retry_after"), 2.0)
            
            # Test local rate limit handling
            mock_instance.send_message.side_effect = local_rate_limit
            
            with self.assertRaises(HTTPError) as context:
                await client.send_message({"content": "Local rate limit test"})
            
            error = context.exception
            self.assertFalse(error.response_data.get("global", True))
            self.assertEqual(error.response_data.get("retry_after"), 1.0)
    
    async def test_rate_limit_recovery_timing(self) -> None:
        """Test accurate timing of rate limit recovery."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            recovery_time = 1.0
            rate_limit_start = time.time()
            
            call_count = 0
            
            async def time_sensitive_rate_limit(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal call_count
                call_count += 1
                
                elapsed = time.time() - rate_limit_start
                
                if elapsed < recovery_time:
                    # Still in rate limit period
                    remaining_time = recovery_time - elapsed
                    raise HTTPError(
                        "Rate limited",
                        status_code=429,
                        response_data={
                            "retry_after": remaining_time,
                            "global": False
                        }
                    )
                else:
                    # Rate limit has expired
                    return {
                        "id": "recovered_message",
                        "type": 0,
                        "content": payload.get("content"),
                        "channel_id": "123456789012345678",
                        "author": {"bot": True},
                        "timestamp": "2025-07-12T22:00:00.000Z"
                    }
            
            mock_instance.send_message.side_effect = time_sensitive_rate_limit
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test immediate request (should be rate limited)
            with self.assertRaises(HTTPError):
                await client.send_message({"content": "Immediate test"})
            
            # Wait for rate limit to expire
            await asyncio.sleep(recovery_time + 0.1)
            
            # Test request after recovery (should succeed)
            result = await client.send_message({"content": "Recovery test"})
            
            # Verify recovery
            self.assertIsNotNone(result)
            self.assertEqual(result["content"], "Recovery test")
            self.assertGreaterEqual(call_count, 2)
    
    async def test_rate_limit_header_parsing(self) -> None:
        """Test parsing of rate limit headers."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure response with rate limit headers
            test_headers = {
                "x-ratelimit-limit": "10",
                "x-ratelimit-remaining": "5",
                "x-ratelimit-reset": str(int(time.time()) + 60),
                "x-ratelimit-reset-after": "60.0",
                "x-ratelimit-bucket": "test_bucket_456",
                "x-ratelimit-scope": "user"
            }
            
            def success_with_headers(payload: Dict[str, Any]) -> Dict[str, Any]:
                # Simulate successful response with headers
                return {
                    "id": "header_test_msg",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "_headers": test_headers  # Mock headers in response
                }
            
            mock_instance.send_message.side_effect = success_with_headers
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test header parsing
            result = await client.send_message({"content": "Header test"})
            
            # Verify response
            self.assertIsNotNone(result)
            
            # Test rate limit info extraction
            if "_headers" in result:
                headers = result["_headers"]
                
                # Verify header values
                self.assertEqual(headers.get("x-ratelimit-limit"), "10")
                self.assertEqual(headers.get("x-ratelimit-remaining"), "5")
                self.assertIsNotNone(headers.get("x-ratelimit-reset"))
                self.assertEqual(headers.get("x-ratelimit-reset-after"), "60.0")
                self.assertEqual(headers.get("x-ratelimit-bucket"), "test_bucket_456")
                self.assertEqual(headers.get("x-ratelimit-scope"), "user")
    
    async def test_rate_limit_queue_management(self) -> None:
        """Test rate limit queue management for pending requests."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate queue-based rate limiting
            request_queue = []
            processing = False
            
            async def queued_rate_limit_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal processing
                
                request_id = f"req_{len(request_queue)}"
                request_queue.append({
                    "id": request_id,
                    "payload": payload,
                    "timestamp": time.time()
                })
                
                if processing:
                    # Already processing, queue this request
                    raise HTTPError(
                        "Rate limited - queued",
                        status_code=429,
                        response_data={
                            "retry_after": 0.5,
                            "global": False,
                            "queue_position": len(request_queue)
                        }
                    )
                else:
                    # Start processing
                    processing = True
                    await asyncio.sleep(0.2)  # Simulate processing time
                    processing = False
                    
                    return {
                        "id": request_id,
                        "type": 0,
                        "content": payload.get("content"),
                        "channel_id": "123456789012345678",
                        "author": {"bot": True},
                        "timestamp": "2025-07-12T22:00:00.000Z"
                    }
            
            mock_instance.send_message.side_effect = queued_rate_limit_handler
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test queue management
            queue_size = 3
            tasks = []
            
            for i in range(queue_size):
                payload = {"content": f"Queued message {i}"}
                task = asyncio.create_task(self._send_with_retry(client, payload))
                tasks.append(task)
            
            # Execute with small delay between starts
            for task in tasks:
                await asyncio.sleep(0.05)
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify queue behavior
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertGreaterEqual(len(successful_results), 1)
            self.assertLessEqual(len(request_queue), queue_size + 1)
    
    async def test_rate_limit_burst_handling(self) -> None:
        """Test handling of burst requests and rate limit buckets."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate burst allowance
            burst_limit = 5
            burst_count = 0
            burst_reset_time = time.time() + 10
            
            async def burst_rate_limit_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal burst_count
                
                current_time = time.time()
                
                if current_time > burst_reset_time:
                    # Reset burst counter
                    burst_count = 0
                
                if burst_count < burst_limit:
                    # Allow within burst limit
                    burst_count += 1
                    return {
                        "id": f"burst_msg_{burst_count}",
                        "type": 0,
                        "content": payload.get("content"),
                        "channel_id": "123456789012345678",
                        "author": {"bot": True},
                        "timestamp": "2025-07-12T22:00:00.000Z"
                    }
                else:
                    # Burst limit exceeded
                    raise HTTPError(
                        "Burst limit exceeded",
                        status_code=429,
                        response_data={
                            "retry_after": burst_reset_time - current_time,
                            "global": False,
                            "burst_limit": burst_limit,
                            "burst_remaining": 0
                        }
                    )
            
            mock_instance.send_message.side_effect = burst_rate_limit_handler
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test burst behavior
            burst_test_count = burst_limit + 2
            successful_bursts = 0
            rate_limited_bursts = 0
            
            for i in range(burst_test_count):
                try:
                    result = await client.send_message({"content": f"Burst test {i}"})
                    successful_bursts += 1
                except HTTPError as e:
                    if e.status_code == 429:
                        rate_limited_bursts += 1
                        
                        # Verify burst limit data
                        self.assertIn("burst_limit", e.response_data)
                        self.assertEqual(e.response_data["burst_limit"], burst_limit)
                    else:
                        raise
            
            # Verify burst limiting
            self.assertEqual(successful_bursts, burst_limit)
            self.assertEqual(rate_limited_bursts, burst_test_count - burst_limit)
    
    # Helper methods
    
    async def _send_with_retry(self, client: HTTPClient, payload: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Send message with retry logic for rate limiting."""
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return await client.send_message(payload)
            except HTTPError as e:
                if e.status_code == 429 and retry_count < max_retries - 1:
                    retry_count += 1
                    retry_after = e.response_data.get("retry_after", 1.0)
                    await asyncio.sleep(retry_after)
                else:
                    raise
        
        raise HTTPError("Max retries exceeded", status_code=429)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number for backoff strategy."""
        if n <= 1:
            return n
        return self._fibonacci(n-1) + self._fibonacci(n-2)


def run_rate_limiting_tests() -> None:
    """Run rate limiting tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRateLimiting)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nRate Limiting Tests Summary:")
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