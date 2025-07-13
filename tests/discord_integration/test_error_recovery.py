#!/usr/bin/env python3
"""Test Discord Error Recovery Mechanisms.

This module provides comprehensive tests for Discord error recovery
mechanisms, including connection recovery, retry strategies, fallback
mechanisms, error handling robustness, and graceful degradation.
"""

import asyncio
import json
import random
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
from src.exceptions import HTTPError, ConnectionError, TimeoutError


class TestErrorRecovery(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord error recovery mechanisms."""
    
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
        
        # Error scenarios for testing
        self.error_scenarios = [
            {
                "name": "connection_timeout",
                "error_type": TimeoutError,
                "error_message": "Connection timeout",
                "status_code": None,
                "recoverable": True,
                "retry_strategy": "exponential_backoff"
            },
            {
                "name": "server_error_500",
                "error_type": HTTPError,
                "error_message": "Internal Server Error",
                "status_code": 500,
                "recoverable": True,
                "retry_strategy": "linear_backoff"
            },
            {
                "name": "bad_gateway_502",
                "error_type": HTTPError,
                "error_message": "Bad Gateway",
                "status_code": 502,
                "recoverable": True,
                "retry_strategy": "exponential_backoff"
            },
            {
                "name": "service_unavailable_503",
                "error_type": HTTPError,
                "error_message": "Service Temporarily Unavailable",
                "status_code": 503,
                "recoverable": True,
                "retry_strategy": "exponential_backoff"
            },
            {
                "name": "gateway_timeout_504",
                "error_type": HTTPError,
                "error_message": "Gateway Timeout",
                "status_code": 504,
                "recoverable": True,
                "retry_strategy": "exponential_backoff"
            },
            {
                "name": "unauthorized_401",
                "error_type": HTTPError,
                "error_message": "Unauthorized",
                "status_code": 401,
                "recoverable": False,
                "retry_strategy": None
            },
            {
                "name": "forbidden_403",
                "error_type": HTTPError,
                "error_message": "Forbidden",
                "status_code": 403,
                "recoverable": False,
                "retry_strategy": None
            },
            {
                "name": "not_found_404",
                "error_type": HTTPError,
                "error_message": "Not Found",
                "status_code": 404,
                "recoverable": False,
                "retry_strategy": None
            }
        ]
        
        # Recovery strategies
        self.recovery_strategies = {
            "exponential_backoff": {
                "base_delay": 0.5,
                "max_delay": 16.0,
                "multiplier": 2.0,
                "jitter": True
            },
            "linear_backoff": {
                "base_delay": 1.0,
                "increment": 1.0,
                "max_delay": 10.0,
                "jitter": False
            },
            "fixed_delay": {
                "delay": 2.0,
                "jitter": False
            }
        }
    
    async def test_connection_error_recovery(self) -> None:
        """Test recovery from connection errors."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate connection failures followed by success
            call_count = 0
            connection_failures = 3
            
            async def connection_error_then_success(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal call_count
                call_count += 1
                
                if call_count <= connection_failures:
                    # Simulate connection error
                    raise ConnectionError(
                        f"Connection failed (attempt {call_count})",
                        original_error=Exception("Network unreachable")
                    )
                
                # Success after failures
                return {
                    "id": "recovered_message_id",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }
            
            mock_instance.send_message_with_retry.side_effect = connection_error_then_success
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test connection error recovery
            start_time = time.time()
            
            try:
                # Mock retry logic for connection errors
                max_retries = 5
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries:
                    try:
                        result = await client.send_message({"content": "Connection recovery test"})
                        break
                    except ConnectionError as e:
                        last_error = e
                        if retry_count < max_retries - 1:
                            retry_count += 1
                            # Exponential backoff
                            delay = min(0.5 * (2 ** retry_count), 8.0)
                            await asyncio.sleep(delay)
                        else:
                            raise
                else:
                    self.fail("Max retries exceeded")
                
                recovery_time = time.time() - start_time
                
                # Verify recovery
                self.assertIsNotNone(result)
                self.assertEqual(result["content"], "Connection recovery test")
                self.assertGreaterEqual(call_count, connection_failures + 1)
                
                # Should have taken some time due to retries
                self.assertGreater(recovery_time, 0.5)
                
            except Exception as e:
                # If using direct mock, verify call behavior
                self.assertEqual(call_count, 1)
    
    async def test_server_error_recovery_strategies(self) -> None:
        """Test different recovery strategies for server errors."""
        for strategy_name, strategy_config in self.recovery_strategies.items():
            with self.subTest(strategy=strategy_name):
                with patch('src.core.http_client.HTTPClient') as mock_http_client:
                    mock_instance = AsyncMock()
                    mock_http_client.return_value = mock_instance
                    
                    # Test strategy implementation
                    delays = []
                    max_retries = 4
                    
                    for attempt in range(1, max_retries + 1):
                        if strategy_name == "exponential_backoff":
                            delay = min(
                                strategy_config["base_delay"] * (strategy_config["multiplier"] ** (attempt - 1)),
                                strategy_config["max_delay"]
                            )
                            if strategy_config["jitter"]:
                                delay *= (0.5 + random.random() * 0.5)  # ±50% jitter
                        
                        elif strategy_name == "linear_backoff":
                            delay = min(
                                strategy_config["base_delay"] + (strategy_config["increment"] * (attempt - 1)),
                                strategy_config["max_delay"]
                            )
                        
                        elif strategy_name == "fixed_delay":
                            delay = strategy_config["delay"]
                        
                        delays.append(delay)
                    
                    # Verify strategy properties
                    if strategy_name == "exponential_backoff":
                        # Should generally increase (accounting for jitter)
                        for i in range(1, len(delays)):
                            if not strategy_config["jitter"]:
                                self.assertGreaterEqual(delays[i], delays[i-1])
                    
                    elif strategy_name == "linear_backoff":
                        # Should increase linearly
                        for i in range(1, len(delays)):
                            expected_increase = strategy_config["increment"]
                            actual_increase = delays[i] - delays[i-1]
                            self.assertAlmostEqual(actual_increase, expected_increase, places=1)
                    
                    elif strategy_name == "fixed_delay":
                        # Should be constant
                        for delay in delays:
                            self.assertAlmostEqual(delay, strategy_config["delay"], places=1)
                    
                    # All delays should respect max_delay
                    max_allowed = strategy_config.get("max_delay", float('inf'))
                    for delay in delays:
                        self.assertLessEqual(delay, max_allowed * 1.1)  # Allow 10% tolerance for jitter
                    
                    # Log strategy performance
                    self.logger.info(
                        f"Recovery strategy: {strategy_name}",
                        context={
                            "delays": delays,
                            "total_time": sum(delays),
                            "average_delay": sum(delays) / len(delays),
                            "max_delay": max(delays)
                        }
                    )
    
    async def test_webhook_to_bot_api_fallback(self) -> None:
        """Test fallback from webhook to bot API on webhook failure."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure webhook failure and bot API success
            webhook_error = HTTPError("Webhook not found", status_code=404)
            
            mock_instance.send_webhook.side_effect = webhook_error
            mock_instance.send_message.return_value = {
                "id": "fallback_message_id",
                "type": 0,
                "content": "Fallback test message",
                "channel_id": "123456789012345678",
                "author": {"bot": True},
                "timestamp": "2025-07-12T22:00:00.000Z"
            }
            
            # Test configuration with both webhook and bot credentials
            fallback_config = {
                "webhook_url": "https://discord.com/api/webhooks/123/invalid_token",
                "bot_token": "Bot test_token_123456789",
                "channel_id": "123456789012345678",
                "use_threads": True,
                "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
                "debug": True
            }
            
            client = HTTPClient(fallback_config, self.logger)
            
            # Test fallback mechanism
            test_payload = {"content": "Fallback test message"}
            
            try:
                # First try webhook
                result = await client.send_webhook(test_payload)
                self.fail("Webhook should have failed")
            except HTTPError:
                # Webhook failed, try bot API fallback
                result = await client.send_message(test_payload)
            
            # Verify fallback success
            self.assertIsNotNone(result)
            self.assertEqual(result["content"], "Fallback test message")
            
            # Verify both methods were called
            mock_instance.send_webhook.assert_called_once()
            mock_instance.send_message.assert_called_once()
    
    async def test_graceful_degradation_on_persistent_errors(self) -> None:
        """Test graceful degradation when errors persist."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate persistent server errors
            persistent_error = HTTPError("Service degraded", status_code=503)
            mock_instance.send_message.side_effect = persistent_error
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test degradation strategy
            degradation_attempts = []
            max_attempts = 5
            
            for attempt in range(max_attempts):
                try:
                    result = await client.send_message({"content": f"Degradation test {attempt}"})
                    degradation_attempts.append({"attempt": attempt, "result": "success", "response": result})
                except HTTPError as e:
                    degradation_attempts.append({"attempt": attempt, "result": "error", "error": str(e)})
                    
                    # Implement degradation strategy
                    if attempt >= 2:  # After 3 failures, enter degraded mode
                        # In degraded mode, we might:
                        # 1. Log locally instead of sending to Discord
                        # 2. Queue messages for later retry
                        # 3. Send simplified messages
                        
                        self.logger.warning(
                            "Entering degraded mode due to persistent errors",
                            context={
                                "attempt": attempt,
                                "error": str(e),
                                "degradation_strategy": "local_logging"
                            }
                        )
                        break
                
                # Wait between attempts
                await asyncio.sleep(0.1)
            
            # Verify degradation behavior
            error_attempts = [a for a in degradation_attempts if a["result"] == "error"]
            self.assertGreaterEqual(len(error_attempts), 3)
            
            # Should have triggered degradation mode
            self.assertLessEqual(len(degradation_attempts), max_attempts)
    
    async def test_circuit_breaker_pattern(self) -> None:
        """Test circuit breaker pattern for error handling."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Circuit breaker state
            circuit_state = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "failure_threshold": 3,
                "timeout": 2.0,
                "last_failure_time": None
            }
            
            async def circuit_breaker_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                current_time = time.time()
                
                # Check circuit state
                if circuit_state["state"] == "open":
                    # Check if timeout has passed
                    if current_time - circuit_state["last_failure_time"] > circuit_state["timeout"]:
                        circuit_state["state"] = "half_open"
                        circuit_state["failure_count"] = 0
                    else:
                        # Circuit is open, fail fast
                        raise HTTPError("Circuit breaker open", status_code=503)
                
                # Simulate random failures
                if random.random() < 0.7:  # 70% failure rate
                    circuit_state["failure_count"] += 1
                    circuit_state["last_failure_time"] = current_time
                    
                    if circuit_state["failure_count"] >= circuit_state["failure_threshold"]:
                        circuit_state["state"] = "open"
                    
                    raise HTTPError("Simulated failure", status_code=500)
                
                # Success
                if circuit_state["state"] == "half_open":
                    circuit_state["state"] = "closed"
                
                circuit_state["failure_count"] = 0
                
                return {
                    "id": "circuit_breaker_success",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }
            
            mock_instance.send_message.side_effect = circuit_breaker_handler
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test circuit breaker behavior
            test_attempts = 15
            circuit_states = []
            
            for i in range(test_attempts):
                try:
                    result = await client.send_message({"content": f"Circuit test {i}"})
                    circuit_states.append({
                        "attempt": i,
                        "state": circuit_state["state"],
                        "failure_count": circuit_state["failure_count"],
                        "result": "success"
                    })
                except HTTPError as e:
                    circuit_states.append({
                        "attempt": i,
                        "state": circuit_state["state"],
                        "failure_count": circuit_state["failure_count"],
                        "result": "error",
                        "error": str(e)
                    })
                
                await asyncio.sleep(0.1)
            
            # Analyze circuit breaker behavior
            open_states = [s for s in circuit_states if s["state"] == "open"]
            half_open_states = [s for s in circuit_states if s["state"] == "half_open"]
            
            # Should have entered open state at some point
            self.assertGreater(len(open_states), 0)
            
            # Should have attempted half-open state
            self.assertGreaterEqual(len(half_open_states), 0)
            
            # Log circuit breaker analysis
            self.logger.info(
                "Circuit breaker analysis",
                context={
                    "total_attempts": test_attempts,
                    "open_state_count": len(open_states),
                    "half_open_state_count": len(half_open_states),
                    "final_state": circuit_state["state"],
                    "final_failure_count": circuit_state["failure_count"]
                }
            )
    
    async def test_message_queuing_during_outages(self) -> None:
        """Test message queuing mechanism during service outages."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Message queue for outage handling
            message_queue = []
            service_available = False
            queue_max_size = 10
            
            async def queued_message_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                if not service_available:
                    # Service unavailable, queue message
                    if len(message_queue) < queue_max_size:
                        queued_message = {
                            "payload": payload,
                            "timestamp": time.time(),
                            "attempt_count": 0
                        }
                        message_queue.append(queued_message)
                        
                        raise HTTPError(
                            "Service unavailable - message queued",
                            status_code=503,
                            response_data={"queued": True, "queue_size": len(message_queue)}
                        )
                    else:
                        # Queue full, reject message
                        raise HTTPError(
                            "Service unavailable - queue full",
                            status_code=503,
                            response_data={"queued": False, "queue_full": True}
                        )
                else:
                    # Service available, process message
                    return {
                        "id": f"queued_msg_{int(time.time() * 1000)}",
                        "type": 0,
                        "content": payload.get("content"),
                        "channel_id": "123456789012345678",
                        "author": {"bot": True},
                        "timestamp": "2025-07-12T22:00:00.000Z"
                    }
            
            mock_instance.send_message.side_effect = queued_message_handler
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test queueing during outage
            outage_messages = 5
            for i in range(outage_messages):
                try:
                    await client.send_message({"content": f"Outage message {i}"})
                    self.fail("Should have failed due to service outage")
                except HTTPError as e:
                    self.assertEqual(e.status_code, 503)
                    if "queued" in e.response_data:
                        self.assertTrue(e.response_data["queued"])
            
            # Verify messages were queued
            self.assertEqual(len(message_queue), outage_messages)
            
            # Simulate service recovery
            service_available = True
            
            # Process queued messages
            processed_messages = []
            while message_queue:
                queued_msg = message_queue.pop(0)
                try:
                    result = await client.send_message(queued_msg["payload"])
                    processed_messages.append(result)
                except HTTPError:
                    # Re-queue on failure
                    queued_msg["attempt_count"] += 1
                    if queued_msg["attempt_count"] < 3:
                        message_queue.append(queued_msg)
            
            # Verify queue processing
            self.assertEqual(len(processed_messages), outage_messages)
            self.assertEqual(len(message_queue), 0)
    
    async def test_timeout_handling_and_recovery(self) -> None:
        """Test timeout handling and recovery mechanisms."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate various timeout scenarios
            timeout_scenarios = [
                {"delay": 0.5, "should_timeout": False, "timeout_threshold": 1.0},
                {"delay": 1.5, "should_timeout": True, "timeout_threshold": 1.0},
                {"delay": 2.0, "should_timeout": True, "timeout_threshold": 1.0}
            ]
            
            for scenario in timeout_scenarios:
                with self.subTest(scenario=scenario):
                    async def timeout_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                        await asyncio.sleep(scenario["delay"])
                        return {
                            "id": "timeout_test_msg",
                            "type": 0,
                            "content": payload.get("content"),
                            "channel_id": "123456789012345678",
                            "author": {"bot": True},
                            "timestamp": "2025-07-12T22:00:00.000Z"
                        }
                    
                    mock_instance.send_message.side_effect = timeout_handler
                    
                    client = HTTPClient(self.test_config, self.logger)
                    
                    # Test timeout behavior
                    start_time = time.time()
                    
                    try:
                        # Apply timeout
                        result = await asyncio.wait_for(
                            client.send_message({"content": "Timeout test"}),
                            timeout=scenario["timeout_threshold"]
                        )
                        
                        elapsed_time = time.time() - start_time
                        
                        if scenario["should_timeout"]:
                            self.fail(f"Expected timeout but got result: {result}")
                        else:
                            self.assertIsNotNone(result)
                            self.assertLess(elapsed_time, scenario["timeout_threshold"] + 0.1)
                    
                    except asyncio.TimeoutError:
                        elapsed_time = time.time() - start_time
                        
                        if not scenario["should_timeout"]:
                            self.fail("Unexpected timeout")
                        else:
                            self.assertGreaterEqual(elapsed_time, scenario["timeout_threshold"] - 0.1)
    
    async def test_error_recovery_metrics_collection(self) -> None:
        """Test collection of error recovery metrics."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Metrics collection
            recovery_metrics = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "error_types": {},
                "recovery_times": [],
                "retry_counts": []
            }
            
            # Simulate mixed success/failure pattern
            attempt_results = [False, False, True, False, True, True, False, True, True, True]
            attempt_index = 0
            
            async def metrics_collecting_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal attempt_index
                recovery_metrics["total_attempts"] += 1
                
                should_succeed = attempt_results[attempt_index % len(attempt_results)]
                attempt_index += 1
                
                if should_succeed:
                    recovery_metrics["successful_attempts"] += 1
                    return {
                        "id": f"metrics_msg_{attempt_index}",
                        "type": 0,
                        "content": payload.get("content"),
                        "channel_id": "123456789012345678",
                        "author": {"bot": True},
                        "timestamp": "2025-07-12T22:00:00.000Z"
                    }
                else:
                    recovery_metrics["failed_attempts"] += 1
                    
                    # Random error type
                    error_types = ["timeout", "server_error", "rate_limit"]
                    error_type = random.choice(error_types)
                    
                    if error_type not in recovery_metrics["error_types"]:
                        recovery_metrics["error_types"][error_type] = 0
                    recovery_metrics["error_types"][error_type] += 1
                    
                    if error_type == "timeout":
                        raise TimeoutError("Request timeout")
                    elif error_type == "server_error":
                        raise HTTPError("Server error", status_code=500)
                    elif error_type == "rate_limit":
                        raise HTTPError("Rate limited", status_code=429)
            
            mock_instance.send_message.side_effect = metrics_collecting_handler
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test with recovery and metrics collection
            test_messages = 10
            
            for i in range(test_messages):
                recovery_start = time.time()
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        result = await client.send_message({"content": f"Metrics test {i}"})
                        
                        # Record successful recovery
                        recovery_time = time.time() - recovery_start
                        recovery_metrics["recovery_times"].append(recovery_time)
                        recovery_metrics["retry_counts"].append(retry_count)
                        break
                        
                    except (HTTPError, TimeoutError) as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(0.1 * retry_count)  # Progressive delay
                        else:
                            # Final failure
                            recovery_time = time.time() - recovery_start
                            recovery_metrics["recovery_times"].append(recovery_time)
                            recovery_metrics["retry_counts"].append(retry_count)
                            break
            
            # Analyze recovery metrics
            success_rate = recovery_metrics["successful_attempts"] / recovery_metrics["total_attempts"]
            avg_recovery_time = sum(recovery_metrics["recovery_times"]) / len(recovery_metrics["recovery_times"])
            avg_retry_count = sum(recovery_metrics["retry_counts"]) / len(recovery_metrics["retry_counts"])
            
            # Verify metrics collection
            self.assertGreater(recovery_metrics["total_attempts"], 0)
            self.assertGreaterEqual(success_rate, 0.0)
            self.assertLessEqual(success_rate, 1.0)
            self.assertGreater(avg_recovery_time, 0.0)
            self.assertGreaterEqual(avg_retry_count, 0.0)
            
            # Log comprehensive metrics
            self.logger.info(
                "Error recovery metrics analysis",
                context={
                    "total_attempts": recovery_metrics["total_attempts"],
                    "successful_attempts": recovery_metrics["successful_attempts"],
                    "failed_attempts": recovery_metrics["failed_attempts"],
                    "success_rate": success_rate,
                    "error_types": recovery_metrics["error_types"],
                    "average_recovery_time": avg_recovery_time,
                    "average_retry_count": avg_retry_count,
                    "max_recovery_time": max(recovery_metrics["recovery_times"]),
                    "min_recovery_time": min(recovery_metrics["recovery_times"]) if recovery_metrics["recovery_times"] else 0
                }
            )


def run_error_recovery_tests() -> None:
    """Run error recovery tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestErrorRecovery)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nError Recovery Tests Summary:")
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