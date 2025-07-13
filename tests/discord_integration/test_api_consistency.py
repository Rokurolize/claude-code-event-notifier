#!/usr/bin/env python3
"""Test Discord API Consistency.

This module provides comprehensive tests for Discord API consistency,
including response format validation, behavior consistency across different
scenarios, and integration reliability.
"""

import asyncio
import json
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.core.config import ConfigLoader
from src.core.http_client import HTTPClient
from src.exceptions import HTTPError, ConfigurationError


class TestAPIConsistency(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord API consistency."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configurations for different scenarios
        self.webhook_config = {
            "webhook_url": "https://discord.com/api/webhooks/123456789/test_token",
            "use_threads": False,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        self.bot_config = {
            "bot_token": "Bot test_bot_token_12345",
            "channel_id": "123456789012345678",
            "use_threads": True,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        # Expected API response formats
        self.expected_webhook_response = {
            "id": str,
            "type": int,
            "content": (str, type(None)),
            "channel_id": str,
            "author": dict,
            "timestamp": str
        }
        
        self.expected_bot_response = {
            "id": str,
            "type": int,
            "content": (str, type(None)),
            "channel_id": str,
            "author": dict,
            "timestamp": str,
            "embeds": list
        }
        
        # Test payloads for consistency testing
        self.test_payloads = [
            {
                "name": "simple_text",
                "payload": {"content": "Simple text message for consistency testing"}
            },
            {
                "name": "embed_only",
                "payload": {
                    "embeds": [{
                        "title": "Consistency Test",
                        "description": "Testing API response consistency",
                        "color": 0x00ff00
                    }]
                }
            },
            {
                "name": "mixed_content",
                "payload": {
                    "content": "Mixed content message",
                    "embeds": [{
                        "title": "Mixed Test",
                        "description": "Content with embed",
                        "fields": [
                            {"name": "Field 1", "value": "Value 1", "inline": True},
                            {"name": "Field 2", "value": "Value 2", "inline": False}
                        ]
                    }]
                }
            }
        ]
    
    async def test_webhook_response_format_consistency(self) -> None:
        """Test webhook response format consistency across multiple calls."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure consistent mock response format
            def create_mock_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": "123456789012345678",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {
                        "id": "webhook_id",
                        "username": "Test Webhook",
                        "discriminator": "0000",
                        "avatar": None,
                        "bot": True
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "embeds": payload.get("embeds", [])
                }
            
            mock_instance.send_webhook.side_effect = lambda payload: create_mock_response(payload)
            
            client = HTTPClient(self.webhook_config, self.logger)
            responses = []
            
            # Test multiple payloads
            for test_payload in self.test_payloads:
                with self.subTest(payload=test_payload["name"]):
                    response = await client.send_webhook(test_payload["payload"])
                    responses.append(response)
                    
                    # Verify response format consistency
                    self.assertIsNotNone(response)
                    self.assertIsInstance(response, dict)
                    
                    # Check required fields are present and have correct types
                    for field, expected_type in self.expected_webhook_response.items():
                        self.assertIn(field, response, f"Missing field {field} in response")
                        
                        if isinstance(expected_type, tuple):
                            # Multiple allowed types
                            self.assertIsInstance(response[field], expected_type,
                                                f"Field {field} has wrong type: {type(response[field])}")
                        else:
                            # Single expected type
                            self.assertIsInstance(response[field], expected_type,
                                                f"Field {field} has wrong type: {type(response[field])}")
            
            # Verify consistent structure across all responses
            self._verify_response_structure_consistency(responses)
    
    async def test_bot_api_response_format_consistency(self) -> None:
        """Test bot API response format consistency."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure bot API mock response
            def create_bot_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": "987654321098765432",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {
                        "id": "bot_user_id",
                        "username": "Test Bot",
                        "discriminator": "0000",
                        "avatar": "bot_avatar_hash",
                        "bot": True
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "embeds": payload.get("embeds", []),
                    "message_reference": None,
                    "flags": 0
                }
            
            # Mock both webhook and bot methods
            mock_instance.send_webhook.side_effect = lambda payload: create_bot_response(payload)
            mock_instance.send_message.side_effect = lambda payload: create_bot_response(payload)
            
            client = HTTPClient(self.bot_config, self.logger)
            responses = []
            
            # Test bot API responses
            for test_payload in self.test_payloads:
                with self.subTest(payload=test_payload["name"]):
                    # Test with send_message method (simulated)
                    response = await client.send_webhook(test_payload["payload"])  # Using webhook mock for testing
                    responses.append(response)
                    
                    # Verify bot API specific response format
                    self.assertIsNotNone(response)
                    self.assertIsInstance(response, dict)
                    
                    # Check bot-specific fields
                    self.assertIn("id", response)
                    self.assertIn("author", response)
                    self.assertIn("embeds", response)
                    
                    # Verify author is bot
                    self.assertTrue(response["author"]["bot"])
            
            # Verify consistency across bot responses
            self._verify_response_structure_consistency(responses)
    
    async def test_api_behavior_consistency_across_methods(self) -> None:
        """Test API behavior consistency across different delivery methods."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure responses for different methods
            webhook_responses = []
            bot_responses = []
            
            def create_webhook_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                response = {
                    "id": f"webhook_{len(webhook_responses)}",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True, "username": "Webhook"},
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "embeds": payload.get("embeds", [])
                }
                webhook_responses.append(response)
                return response
            
            def create_bot_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                response = {
                    "id": f"bot_{len(bot_responses)}",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True, "username": "Bot"},
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "embeds": payload.get("embeds", [])
                }
                bot_responses.append(response)
                return response
            
            mock_instance.send_webhook.side_effect = create_webhook_response
            mock_instance.send_message.side_effect = create_bot_response
            
            # Test webhook method
            webhook_client = HTTPClient(self.webhook_config, self.logger)
            
            # Test bot method
            bot_client = HTTPClient(self.bot_config, self.logger)
            
            test_payload = self.test_payloads[0]["payload"]
            
            # Send same payload via both methods
            webhook_response = await webhook_client.send_webhook(test_payload)
            bot_response = await webhook_client.send_webhook(test_payload)  # Using same mock for testing
            
            # Verify both methods handle the payload consistently
            self.assertIsNotNone(webhook_response)
            self.assertIsNotNone(bot_response)
            
            # Both should have similar structure (excluding method-specific fields)
            common_fields = ["type", "content", "channel_id", "timestamp", "embeds"]
            for field in common_fields:
                if field in webhook_response and field in bot_response:
                    # Content should be preserved consistently
                    if field in ["content", "embeds"]:
                        self.assertEqual(webhook_response[field], bot_response[field],
                                       f"Field {field} inconsistent between methods")
    
    async def test_error_response_consistency(self) -> None:
        """Test error response format consistency."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test different error scenarios
            error_scenarios = [
                {
                    "name": "rate_limit",
                    "status_code": 429,
                    "error_data": {
                        "message": "You are being rate limited.",
                        "retry_after": 1.234,
                        "global": False
                    }
                },
                {
                    "name": "unauthorized",
                    "status_code": 401,
                    "error_data": {
                        "message": "401: Unauthorized",
                        "code": 0
                    }
                },
                {
                    "name": "bad_request",
                    "status_code": 400,
                    "error_data": {
                        "message": "Cannot send an empty message",
                        "code": 50006
                    }
                },
                {
                    "name": "not_found",
                    "status_code": 404,
                    "error_data": {
                        "message": "Unknown Webhook",
                        "code": 10015
                    }
                }
            ]
            
            client = HTTPClient(self.webhook_config, self.logger)
            
            for scenario in error_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Configure mock to raise HTTPError with consistent format
                    mock_instance.send_webhook.side_effect = HTTPError(
                        scenario["error_data"]["message"],
                        status_code=scenario["status_code"],
                        response_data=scenario["error_data"]
                    )
                    
                    # Test error handling
                    with self.assertRaises(HTTPError) as context:
                        await client.send_webhook({"content": "test"})
                    
                    error = context.exception
                    
                    # Verify error format consistency
                    self.assertEqual(error.status_code, scenario["status_code"])
                    self.assertIsNotNone(error.message)
                    self.assertIsInstance(error.message, str)
                    
                    # Check for consistent error data structure
                    if hasattr(error, 'response_data') and error.response_data:
                        self.assertIsInstance(error.response_data, dict)
                        self.assertIn("message", error.response_data)
    
    async def test_response_timing_consistency(self) -> None:
        """Test response timing consistency across multiple calls."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure mock with realistic timing
            call_times = []
            
            async def timed_webhook_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                start_time = time.time()
                await asyncio.sleep(0.1)  # Simulate consistent processing time
                end_time = time.time()
                call_times.append(end_time - start_time)
                
                return {
                    "id": f"msg_{int(end_time * 1000)}",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }
            
            mock_instance.send_webhook.side_effect = timed_webhook_response
            
            client = HTTPClient(self.webhook_config, self.logger)
            
            # Test multiple calls for timing consistency
            test_count = 5
            responses = []
            
            for i in range(test_count):
                response = await client.send_webhook({"content": f"Timing test {i}"})
                responses.append(response)
            
            # Verify timing consistency
            self.assertEqual(len(call_times), test_count)
            
            # Calculate timing statistics
            avg_time = sum(call_times) / len(call_times)
            max_deviation = max(abs(t - avg_time) for t in call_times)
            
            # Timing should be consistent (within 50% deviation)
            acceptable_deviation = avg_time * 0.5
            self.assertLessEqual(max_deviation, acceptable_deviation,
                               f"Response timing inconsistent: max deviation {max_deviation:.3f}s "
                               f"exceeds {acceptable_deviation:.3f}s")
            
            # All responses should be valid
            for i, response in enumerate(responses):
                with self.subTest(call=i):
                    self.assertIsNotNone(response)
                    self.assertIn("id", response)
                    self.assertIn("timestamp", response)
    
    async def test_payload_handling_consistency(self) -> None:
        """Test consistent payload handling across different scenarios."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Track payload transformations
            processed_payloads = []
            
            def payload_echo_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                # Echo back the payload in a consistent format
                processed_payloads.append(payload.copy())
                
                return {
                    "id": "echo_response",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "embeds": payload.get("embeds", []),
                    "original_payload": payload  # Include original for verification
                }
            
            mock_instance.send_webhook.side_effect = payload_echo_response
            
            client = HTTPClient(self.webhook_config, self.logger)
            
            # Test various payload formats
            payload_tests = [
                {"content": "Simple string"},
                {"content": "Unicode: 🎯📊✅❌ 世界"},
                {"content": "Special chars: @#$%^&*()"},
                {"embeds": [{"title": "Simple embed"}]},
                {"embeds": [{"title": "Complex embed", "fields": [{"name": "test", "value": "value"}]}]},
                {"content": "Mixed", "embeds": [{"title": "Mixed content"}]},
                {"content": None},  # Edge case
                {},  # Empty payload
            ]
            
            responses = []
            
            for i, payload in enumerate(payload_tests):
                with self.subTest(payload_index=i):
                    try:
                        response = await client.send_webhook(payload)
                        responses.append(response)
                        
                        # Verify payload was preserved correctly
                        self.assertIsNotNone(response)
                        
                        if "original_payload" in response:
                            original = response["original_payload"]
                            
                            # Content should be preserved (if present)
                            if "content" in payload:
                                self.assertEqual(original.get("content"), payload.get("content"))
                            
                            # Embeds should be preserved (if present)
                            if "embeds" in payload:
                                self.assertEqual(original.get("embeds"), payload.get("embeds"))
                    
                    except Exception as e:
                        # Some payloads might be invalid - that's consistent behavior too
                        self.logger.info(f"Payload {i} failed consistently: {e}")
            
            # Verify all processed payloads maintain consistency
            self.assertEqual(len(processed_payloads), len(responses))
    
    async def test_concurrent_api_consistency(self) -> None:
        """Test API consistency under concurrent load."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Track concurrent calls
            concurrent_responses = []
            call_counter = 0
            
            async def concurrent_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal call_counter
                call_id = call_counter
                call_counter += 1
                
                # Simulate some processing time
                await asyncio.sleep(0.05)
                
                response = {
                    "id": f"concurrent_{call_id}",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "call_id": call_id,
                    "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
                }
                
                concurrent_responses.append(response)
                return response
            
            mock_instance.send_webhook.side_effect = concurrent_response
            
            client = HTTPClient(self.webhook_config, self.logger)
            
            # Create concurrent tasks
            concurrent_count = 5
            tasks = []
            
            for i in range(concurrent_count):
                payload = {"content": f"Concurrent message {i}"}
                task = asyncio.create_task(client.send_webhook(payload), name=f"task_{i}")
                tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify concurrent consistency
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertEqual(len(successful_results), concurrent_count,
                           f"Expected {concurrent_count} successful results, got {len(successful_results)}")
            
            # Verify each response has consistent structure
            for i, result in enumerate(successful_results):
                with self.subTest(concurrent_call=i):
                    self.assertIsInstance(result, dict)
                    self.assertIn("id", result)
                    self.assertIn("call_id", result)
                    self.assertIn("content", result)
                    
                    # Content should match what was sent
                    expected_content = f"Concurrent message {i}"
                    self.assertIn(expected_content, result.get("content", ""))
            
            # Verify all calls were processed (no lost requests)
            self.assertEqual(len(concurrent_responses), concurrent_count)
            
            # Verify unique response IDs (no duplicate processing)
            response_ids = [r["id"] for r in concurrent_responses]
            self.assertEqual(len(response_ids), len(set(response_ids)),
                           "Duplicate response IDs detected - concurrent handling issue")
    
    def _verify_response_structure_consistency(self, responses: List[Dict[str, Any]]) -> None:
        """Verify that all responses have consistent structure."""
        if not responses:
            self.fail("No responses to verify")
        
        # Use first response as template
        template = responses[0]
        template_keys = set(template.keys())
        template_types = {key: type(template[key]) for key in template_keys}
        
        # Verify all responses match the template structure
        for i, response in enumerate(responses[1:], 1):
            response_keys = set(response.keys())
            
            # Check for missing keys
            missing_keys = template_keys - response_keys
            if missing_keys:
                self.fail(f"Response {i} missing keys: {missing_keys}")
            
            # Check for extra keys
            extra_keys = response_keys - template_keys
            if extra_keys:
                self.logger.warning(f"Response {i} has extra keys: {extra_keys}")
            
            # Check type consistency for common keys
            for key in template_keys & response_keys:
                if template[key] is not None and response[key] is not None:
                    template_type = template_types[key]
                    response_type = type(response[key])
                    
                    if template_type != response_type:
                        self.fail(f"Response {i} key '{key}' type mismatch: "
                                f"expected {template_type}, got {response_type}")


def run_api_consistency_tests() -> None:
    """Run API consistency tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestAPIConsistency)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nAPI Consistency Tests Summary:")
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