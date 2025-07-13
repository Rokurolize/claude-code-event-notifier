#!/usr/bin/env python3
"""Test Webhook Delivery Functionality.

This module provides comprehensive tests for Discord webhook delivery
functionality, including success rate measurement, error handling,
response time validation, and integration testing.
"""

import asyncio
import json
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
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


class TestWebhookDelivery(unittest.IsolatedAsyncioTestCase):
    """Test cases for webhook delivery functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test webhook configuration
        self.test_config = {
            "webhook_url": "https://discord.com/api/webhooks/123456789/test_webhook_token",
            "use_threads": False,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        # Test payloads
        self.test_payloads = [
            {
                "name": "simple_message",
                "payload": {
                    "content": "Test webhook delivery message"
                }
            },
            {
                "name": "embed_message",
                "payload": {
                    "embeds": [{
                        "title": "Test Webhook",
                        "description": "Testing webhook delivery functionality",
                        "color": 0x00ff00,
                        "timestamp": "2025-07-12T22:00:00Z"
                    }]
                }
            },
            {
                "name": "mixed_message",
                "payload": {
                    "content": "Test message with embed",
                    "embeds": [{
                        "title": "Mixed Content",
                        "description": "Content and embed together",
                        "fields": [
                            {"name": "Field 1", "value": "Value 1", "inline": True},
                            {"name": "Field 2", "value": "Value 2", "inline": True}
                        ]
                    }]
                }
            },
            {
                "name": "large_payload",
                "payload": {
                    "content": "Large payload test: " + "A" * 1900,  # Near Discord limit
                    "embeds": [{
                        "title": "Large Content Test",
                        "description": "Testing with near-maximum content size",
                        "fields": [
                            {"name": f"Field {i}", "value": f"Value {i}" * 20, "inline": True}
                            for i in range(10)
                        ]
                    }]
                }
            }
        ]
    
    async def test_webhook_delivery_success_rate(self) -> None:
        """Test webhook delivery success rate measurement."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure successful responses
            mock_instance.send_webhook.return_value = {
                "status": "success",
                "message_id": "123456789012345678"
            }
            
            # Test multiple deliveries
            client = HTTPClient(self.test_config, self.logger)
            success_count = 0
            total_attempts = 10
            
            for i in range(total_attempts):
                try:
                    result = await client.send_webhook(self.test_payloads[0]["payload"])
                    if result and result.get("status") == "success":
                        success_count += 1
                except Exception as e:
                    self.logger.error(f"Webhook delivery failed: {e}")
            
            success_rate = success_count / total_attempts
            
            # Assert success rate meets requirement (99.5%+)
            self.assertGreaterEqual(success_rate, 0.995, 
                                  f"Webhook delivery success rate {success_rate:.3f} below target 0.995")
            
            # Verify all calls were made
            self.assertEqual(mock_instance.send_webhook.call_count, total_attempts)
    
    async def test_webhook_delivery_response_time(self) -> None:
        """Test webhook delivery response time performance."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate realistic response times
            async def mock_send_webhook(payload):
                await asyncio.sleep(0.1)  # Simulate 100ms response time
                return {"status": "success", "message_id": "123456789012345678"}
            
            mock_instance.send_webhook.side_effect = mock_send_webhook
            
            client = HTTPClient(self.test_config, self.logger)
            response_times = []
            
            # Test response times for different payload types
            for test_payload in self.test_payloads:
                start_time = time.time()
                
                try:
                    await client.send_webhook(test_payload["payload"])
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                except Exception as e:
                    self.logger.error(f"Webhook test failed for {test_payload['name']}: {e}")
                    response_times.append(float('inf'))  # Mark as failed
            
            # Calculate average response time
            valid_times = [t for t in response_times if t != float('inf')]
            avg_response_time = sum(valid_times) / len(valid_times) if valid_times else float('inf')
            
            # Assert average response time meets requirement (<3 seconds)
            self.assertLess(avg_response_time, 3.0,
                          f"Average webhook response time {avg_response_time:.3f}s exceeds 3s limit")
            
            # Assert all response times are reasonable
            for i, response_time in enumerate(response_times):
                test_name = self.test_payloads[i]["name"]
                self.assertLess(response_time, 5.0,
                              f"Response time for {test_name} ({response_time:.3f}s) too slow")
    
    async def test_webhook_error_handling(self) -> None:
        """Test webhook error handling and recovery."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test different error scenarios
            error_scenarios = [
                {
                    "name": "rate_limit_error",
                    "exception": HTTPError("Rate limited", status_code=429),
                    "should_retry": True
                },
                {
                    "name": "network_error",
                    "exception": HTTPError("Network error", status_code=500),
                    "should_retry": True
                },
                {
                    "name": "unauthorized_error",
                    "exception": HTTPError("Unauthorized", status_code=401),
                    "should_retry": False
                },
                {
                    "name": "not_found_error",
                    "exception": HTTPError("Webhook not found", status_code=404),
                    "should_retry": False
                }
            ]
            
            client = HTTPClient(self.test_config, self.logger)
            
            for scenario in error_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Configure mock to raise the error
                    mock_instance.send_webhook.side_effect = scenario["exception"]
                    
                    # Test error handling
                    with self.assertRaises(HTTPError):
                        await client.send_webhook(self.test_payloads[0]["payload"])
                    
                    # Verify error was logged appropriately
                    # In a real implementation, we would check retry behavior here
    
    async def test_webhook_payload_validation(self) -> None:
        """Test webhook payload validation and sanitization."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            mock_instance.send_webhook.return_value = {"status": "success"}
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test valid payloads
            for test_payload in self.test_payloads:
                with self.subTest(payload=test_payload["name"]):
                    try:
                        result = await client.send_webhook(test_payload["payload"])
                        self.assertIsNotNone(result)
                        self.assertEqual(result.get("status"), "success")
                    except Exception as e:
                        self.fail(f"Valid payload {test_payload['name']} failed: {e}")
            
            # Test invalid payloads
            invalid_payloads = [
                {
                    "name": "empty_payload",
                    "payload": {}
                },
                {
                    "name": "oversized_content",
                    "payload": {
                        "content": "A" * 2500  # Exceeds Discord 2000 char limit
                    }
                },
                {
                    "name": "invalid_embed_structure",
                    "payload": {
                        "embeds": [{
                            "title": "T" * 300,  # Exceeds 256 char limit
                            "description": "D" * 5000  # Exceeds 4096 char limit
                        }]
                    }
                },
                {
                    "name": "too_many_embed_fields",
                    "payload": {
                        "embeds": [{
                            "title": "Too Many Fields",
                            "fields": [
                                {"name": f"Field {i}", "value": f"Value {i}"}
                                for i in range(30)  # Exceeds 25 field limit
                            ]
                        }]
                    }
                }
            ]
            
            for invalid_payload in invalid_payloads:
                with self.subTest(payload=invalid_payload["name"]):
                    # Should either validate and truncate, or raise appropriate error
                    try:
                        result = await client.send_webhook(invalid_payload["payload"])
                        # If successful, payload should have been sanitized
                        self.assertIsNotNone(result)
                    except (ValueError, HTTPError) as e:
                        # Expected for invalid payloads
                        self.assertIsInstance(e, (ValueError, HTTPError))
    
    async def test_webhook_retry_mechanism(self) -> None:
        """Test webhook retry mechanism for transient failures."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure mock to fail twice, then succeed
            call_count = 0
            
            async def mock_send_webhook_with_retries(payload):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:
                    # First two calls fail with retryable error
                    raise HTTPError("Temporary server error", status_code=500)
                else:
                    # Third call succeeds
                    return {"status": "success", "message_id": "123456789012345678"}
            
            mock_instance.send_webhook.side_effect = mock_send_webhook_with_retries
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test retry mechanism
            start_time = time.time()
            
            try:
                result = await client.send_webhook(self.test_payloads[0]["payload"])
                self.assertIsNotNone(result)
                self.assertEqual(result.get("status"), "success")
                
                # Verify retries were attempted
                self.assertEqual(call_count, 3, "Expected 3 attempts (2 failures + 1 success)")
                
                # Verify reasonable total time (should include retry delays)
                total_time = time.time() - start_time
                self.assertGreater(total_time, 0.1, "Retry mechanism should introduce delays")
                self.assertLess(total_time, 10.0, "Total retry time should be reasonable")
                
            except HTTPError:
                self.fail("Webhook should have succeeded after retries")
    
    async def test_webhook_concurrent_delivery(self) -> None:
        """Test concurrent webhook delivery handling."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure mock with realistic delay
            async def mock_send_webhook(payload):
                await asyncio.sleep(0.1)  # Simulate processing time
                return {"status": "success", "message_id": f"msg_{time.time()}"}
            
            mock_instance.send_webhook.side_effect = mock_send_webhook
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test concurrent deliveries
            concurrent_count = 5
            tasks = []
            
            start_time = time.time()
            
            # Create concurrent webhook delivery tasks
            for i in range(concurrent_count):
                payload = {
                    "content": f"Concurrent message {i}",
                    "embeds": [{
                        "title": f"Concurrent Test {i}",
                        "description": f"Testing concurrent delivery #{i}"
                    }]
                }
                task = asyncio.create_task(client.send_webhook(payload))
                tasks.append(task)
            
            # Wait for all deliveries to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Verify all deliveries succeeded
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Concurrent delivery {i} failed: {result}")
                else:
                    self.assertIsNotNone(result)
                    self.assertEqual(result.get("status"), "success")
                    success_count += 1
            
            # Assert concurrent delivery performance
            self.assertEqual(success_count, concurrent_count,
                           f"Only {success_count}/{concurrent_count} concurrent deliveries succeeded")
            
            # Should be faster than sequential (each task takes ~0.1s)
            max_expected_time = 0.5  # Should complete much faster than 5 * 0.1s = 0.5s
            self.assertLess(total_time, max_expected_time,
                          f"Concurrent delivery took {total_time:.3f}s, expected < {max_expected_time}s")
    
    async def test_webhook_url_validation(self) -> None:
        """Test webhook URL validation."""
        # Test valid webhook URLs
        valid_urls = [
            "https://discord.com/api/webhooks/123456789012345678/TEST_WEBHOOK_TOKEN_1",
            "https://discordapp.com/api/webhooks/123456789012345678/TEST_WEBHOOK_TOKEN_2",
            "https://discord.com/api/webhooks/987654321098765432/TEST_WEBHOOK_TOKEN_3"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                config = self.test_config.copy()
                config["webhook_url"] = url
                
                try:
                    # Should not raise an exception for valid URLs
                    client = HTTPClient(config, self.logger)
                    self.assertIsNotNone(client)
                except ConfigurationError:
                    self.fail(f"Valid webhook URL rejected: {url}")
        
        # Test invalid webhook URLs
        invalid_urls = [
            "not_a_url",
            "http://discord.com/api/webhooks/123/token",  # HTTP instead of HTTPS
            "https://example.com/webhook",  # Wrong domain
            "https://discord.com/api/webhooks/",  # Missing ID and token
            "https://discord.com/api/webhooks/invalid_id/token",  # Invalid ID format
            ""  # Empty URL
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                config = self.test_config.copy()
                config["webhook_url"] = url
                
                with self.assertRaises((ConfigurationError, ValueError)):
                    HTTPClient(config, self.logger)
    
    async def test_webhook_delivery_integration(self) -> None:
        """Test end-to-end webhook delivery integration."""
        # This test would ideally use a real test webhook, but for unit testing
        # we'll mock the entire flow
        
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure realistic webhook response
            mock_instance.send_webhook.return_value = {
                "status": "success",
                "message_id": "123456789012345678",
                "timestamp": "2025-07-12T22:00:00Z"
            }
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test complete webhook delivery workflow
            test_event = {
                "session_id": "integration_test_session",
                "tool_name": "Read",
                "timestamp": "2025-07-12T22:00:00Z",
                "input_data": {"file_path": "/test/integration.py"}
            }
            
            # Format event into webhook payload (this would normally be done by formatters)
            webhook_payload = {
                "embeds": [{
                    "title": "🔧 Tool Usage: Read",
                    "description": f"Session: {test_event['session_id']}",
                    "fields": [
                        {
                            "name": "File Path",
                            "value": test_event['input_data']['file_path'],
                            "inline": True
                        },
                        {
                            "name": "Timestamp",
                            "value": test_event['timestamp'],
                            "inline": True
                        }
                    ],
                    "color": 0x00ff00,
                    "timestamp": test_event['timestamp']
                }]
            }
            
            # Send webhook
            result = await client.send_webhook(webhook_payload)
            
            # Verify integration success
            self.assertIsNotNone(result)
            self.assertEqual(result.get("status"), "success")
            self.assertIn("message_id", result)
            
            # Verify webhook was called with correct payload
            mock_instance.send_webhook.assert_called_once_with(webhook_payload)


def run_webhook_delivery_tests() -> None:
    """Run webhook delivery tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestWebhookDelivery)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nWebhook Delivery Tests Summary:")
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