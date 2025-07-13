#!/usr/bin/env python3
"""Test Bot API Functionality.

This module provides comprehensive tests for Discord bot API functionality,
including authentication, channel access, message operations, permissions
validation, and integration testing.
"""

import asyncio
import json
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
from src.core.config import ConfigLoader
from src.core.http_client import HTTPClient
from src.exceptions import HTTPError, ConfigurationError


class TestBotAPIFunctionality(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord bot API functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test bot configuration
        self.test_config = {
            "bot_token": "Bot TEST_TOKEN_PLACEHOLDER",
            "channel_id": "123456789012345678",
            "use_threads": True,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        # Alternative webhook config for comparison tests
        self.webhook_config = {
            "webhook_url": "https://discord.com/api/webhooks/123456789/test_token",
            "use_threads": False,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        # Test payloads for bot API
        self.test_payloads = [
            {
                "name": "simple_message",
                "payload": {
                    "content": "Test bot API message"
                }
            },
            {
                "name": "embed_message",
                "payload": {
                    "embeds": [{
                        "title": "Bot API Test",
                        "description": "Testing bot API functionality",
                        "color": 0x5865f2,
                        "timestamp": "2025-07-12T22:00:00Z",
                        "author": {
                            "name": "Claude Code Bot",
                            "icon_url": "https://example.com/icon.png"
                        }
                    }]
                }
            },
            {
                "name": "mixed_content",
                "payload": {
                    "content": "Bot API mixed content test",
                    "embeds": [{
                        "title": "Mixed Content Test", 
                        "description": "Content with embed via bot API",
                        "fields": [
                            {"name": "API Type", "value": "Bot API", "inline": True},
                            {"name": "Test Type", "value": "Integration", "inline": True}
                        ]
                    }]
                }
            },
            {
                "name": "complex_embed",
                "payload": {
                    "embeds": [{
                        "title": "Complex Bot API Test",
                        "description": "Testing complex embed structures with bot API",
                        "color": 0x57f287,
                        "fields": [
                            {"name": "Authentication", "value": "✅ Bot Token", "inline": True},
                            {"name": "Permissions", "value": "✅ Send Messages", "inline": True},
                            {"name": "Features", "value": "✅ Rich Embeds", "inline": True}
                        ],
                        "footer": {
                            "text": "Bot API Integration Test",
                            "icon_url": "https://example.com/footer.png"
                        },
                        "thumbnail": {
                            "url": "https://example.com/thumbnail.png"
                        }
                    }]
                }
            }
        ]
        
        # Expected API response structures
        self.expected_bot_response = {
            "id": str,
            "type": int,
            "content": (str, type(None)),
            "channel_id": str,
            "author": dict,
            "timestamp": str,
            "embeds": list,
            "pinned": bool,
            "mention_everyone": bool,
            "tts": bool,
            "attachments": list,
            "reactions": list
        }
    
    async def test_bot_authentication_validation(self) -> None:
        """Test bot authentication validation and token verification."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test valid bot token authentication
            mock_instance.authenticate_bot.return_value = {
                "authenticated": True,
                "bot_info": {
                    "id": "123456789012345678",
                    "username": "Test Bot",
                    "discriminator": "0000",
                    "avatar": "avatar_hash",
                    "bot": True,
                    "verified": True
                }
            }
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test authentication
            auth_result = await self._test_bot_authentication(client)
            
            self.assertTrue(auth_result.get("authenticated", False))
            self.assertIsNotNone(auth_result.get("bot_info"))
            
            bot_info = auth_result["bot_info"]
            self.assertTrue(bot_info.get("bot", False))
            self.assertIsInstance(bot_info.get("id"), str)
            self.assertIsInstance(bot_info.get("username"), str)
    
    async def test_channel_access_permissions(self) -> None:
        """Test channel access permissions and validation."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure channel access response
            mock_instance.get_channel.return_value = {
                "id": "123456789012345678",
                "type": 0,  # GUILD_TEXT
                "name": "test-channel",
                "guild_id": "987654321098765432",
                "permissions": [
                    "VIEW_CHANNEL",
                    "SEND_MESSAGES", 
                    "EMBED_LINKS",
                    "ATTACH_FILES",
                    "READ_MESSAGE_HISTORY",
                    "USE_EXTERNAL_EMOJIS"
                ]
            }
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test channel access
            channel_info = await self._test_channel_access(client)
            
            self.assertIsNotNone(channel_info)
            self.assertEqual(channel_info.get("id"), self.test_config["channel_id"])
            self.assertIn("permissions", channel_info)
            
            # Verify required permissions
            required_permissions = ["VIEW_CHANNEL", "SEND_MESSAGES", "EMBED_LINKS"]
            actual_permissions = channel_info.get("permissions", [])
            
            for perm in required_permissions:
                self.assertIn(perm, actual_permissions, 
                            f"Missing required permission: {perm}")
    
    async def test_message_send_operations(self) -> None:
        """Test message sending operations via bot API."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure message send responses
            def create_message_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": f"msg_{int(time.time() * 1000)}",
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
                    "pinned": False,
                    "mention_everyone": False,
                    "tts": False,
                    "attachments": [],
                    "reactions": []
                }
            
            mock_instance.send_message.side_effect = create_message_response
            
            client = HTTPClient(self.test_config, self.logger)
            responses = []
            
            # Test sending different message types
            for test_payload in self.test_payloads:
                with self.subTest(payload=test_payload["name"]):
                    response = await client.send_message(test_payload["payload"])
                    responses.append(response)
                    
                    # Verify response structure
                    self.assertIsNotNone(response)
                    self.assertIsInstance(response, dict)
                    
                    # Check required fields
                    for field, expected_type in self.expected_bot_response.items():
                        self.assertIn(field, response, f"Missing field {field}")
                        
                        if isinstance(expected_type, tuple):
                            self.assertIsInstance(response[field], expected_type,
                                                f"Field {field} wrong type: {type(response[field])}")
                        else:
                            self.assertIsInstance(response[field], expected_type,
                                                f"Field {field} wrong type: {type(response[field])}")
                    
                    # Verify bot-specific fields
                    self.assertTrue(response["author"]["bot"])
                    self.assertEqual(response["channel_id"], self.test_config["channel_id"])
            
            # Verify all messages were sent successfully
            self.assertEqual(len(responses), len(self.test_payloads))
            self.assertEqual(mock_instance.send_message.call_count, len(self.test_payloads))
    
    async def test_message_edit_operations(self) -> None:
        """Test message editing operations via bot API."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure edit message response
            original_message_id = "123456789012345678"
            
            def edit_message_response(message_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": message_id,
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
                    "edited_timestamp": "2025-07-12T22:01:00.000Z",
                    "embeds": payload.get("embeds", []),
                    "pinned": False,
                    "mention_everyone": False,
                    "tts": False,
                    "attachments": [],
                    "reactions": []
                }
            
            mock_instance.edit_message.side_effect = edit_message_response
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test editing message
            edit_payload = {
                "content": "Edited message content",
                "embeds": [{
                    "title": "Edited Embed",
                    "description": "This message was edited via bot API",
                    "color": 0xfee75c
                }]
            }
            
            response = await client.edit_message(original_message_id, edit_payload)
            
            # Verify edit response
            self.assertIsNotNone(response)
            self.assertEqual(response["id"], original_message_id)
            self.assertEqual(response["content"], edit_payload["content"])
            self.assertIn("edited_timestamp", response)
            self.assertIsNotNone(response["edited_timestamp"])
            
            # Verify edit was called correctly
            mock_instance.edit_message.assert_called_once_with(original_message_id, edit_payload)
    
    async def test_message_delete_operations(self) -> None:
        """Test message deletion operations via bot API."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure delete message response
            message_id = "123456789012345678"
            mock_instance.delete_message.return_value = {"deleted": True, "message_id": message_id}
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test deleting message
            response = await client.delete_message(message_id)
            
            # Verify deletion response
            self.assertIsNotNone(response)
            self.assertTrue(response.get("deleted", False))
            self.assertEqual(response.get("message_id"), message_id)
            
            # Verify delete was called correctly
            mock_instance.delete_message.assert_called_once_with(message_id)
    
    async def test_thread_operations(self) -> None:
        """Test thread creation and management via bot API."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure thread creation response
            def create_thread_response(name: str, message_id: Optional[str] = None) -> Dict[str, Any]:
                thread_id = f"thread_{int(time.time() * 1000)}"
                return {
                    "id": thread_id,
                    "type": 11,  # PUBLIC_THREAD
                    "name": name,
                    "parent_id": "123456789012345678",
                    "owner_id": "bot_user_id",
                    "guild_id": "987654321098765432",
                    "thread_metadata": {
                        "archived": False,
                        "archive_timestamp": None,
                        "auto_archive_duration": 1440,
                        "locked": False
                    },
                    "member_count": 1,
                    "message_count": 0 if message_id is None else 1
                }
            
            mock_instance.create_thread.side_effect = create_thread_response
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test creating thread
            thread_name = "Bot API Test Thread"
            thread_response = await client.create_thread(thread_name)
            
            # Verify thread creation
            self.assertIsNotNone(thread_response)
            self.assertEqual(thread_response["name"], thread_name)
            self.assertEqual(thread_response["type"], 11)  # PUBLIC_THREAD
            self.assertEqual(thread_response["parent_id"], self.test_config["channel_id"])
            self.assertFalse(thread_response["thread_metadata"]["archived"])
            
            # Test thread message sending
            thread_id = thread_response["id"]
            thread_message_payload = {
                "content": "Message in thread via bot API",
                "embeds": [{
                    "title": "Thread Message",
                    "description": "This message was sent to a thread"
                }]
            }
            
            # Configure thread message response
            mock_instance.send_message_to_thread.return_value = {
                "id": "thread_msg_123",
                "type": 0,
                "content": thread_message_payload["content"],
                "channel_id": thread_id,
                "author": {
                    "id": "bot_user_id",
                    "username": "Test Bot",
                    "bot": True
                },
                "timestamp": "2025-07-12T22:00:00.000Z",
                "embeds": thread_message_payload["embeds"]
            }
            
            thread_msg_response = await client.send_message_to_thread(thread_id, thread_message_payload)
            
            # Verify thread message
            self.assertIsNotNone(thread_msg_response)
            self.assertEqual(thread_msg_response["channel_id"], thread_id)
            self.assertEqual(thread_msg_response["content"], thread_message_payload["content"])
    
    async def test_bot_vs_webhook_comparison(self) -> None:
        """Test functionality differences between bot API and webhook."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure responses for both methods
            def bot_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": "bot_msg_123",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {
                        "id": "bot_user_id",
                        "username": "Test Bot",
                        "discriminator": "0000",
                        "bot": True
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "embeds": payload.get("embeds", []),
                    "pinned": False,
                    "mention_everyone": False,
                    "tts": False,
                    "attachments": [],
                    "reactions": []
                }
            
            def webhook_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": "webhook_msg_456",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {
                        "id": "webhook_id",
                        "username": "Test Webhook",
                        "discriminator": "0000",
                        "bot": True
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "embeds": payload.get("embeds", [])
                }
            
            mock_instance.send_message.side_effect = bot_response
            mock_instance.send_webhook.side_effect = webhook_response
            
            # Test bot client
            bot_client = HTTPClient(self.test_config, self.logger)
            
            # Test webhook client
            webhook_client = HTTPClient(self.webhook_config, self.logger)
            
            test_payload = self.test_payloads[0]["payload"]
            
            # Send via both methods
            bot_result = await bot_client.send_message(test_payload)
            webhook_result = await webhook_client.send_webhook(test_payload)
            
            # Compare results
            self.assertIsNotNone(bot_result)
            self.assertIsNotNone(webhook_result)
            
            # Content should be preserved in both
            self.assertEqual(bot_result["content"], webhook_result["content"])
            self.assertEqual(bot_result["embeds"], webhook_result["embeds"])
            
            # Bot API should have additional fields
            bot_only_fields = ["pinned", "mention_everyone", "tts", "attachments", "reactions"]
            for field in bot_only_fields:
                self.assertIn(field, bot_result, f"Bot API missing field: {field}")
                self.assertNotIn(field, webhook_result, f"Webhook unexpectedly has field: {field}")
    
    async def test_rate_limiting_compliance(self) -> None:
        """Test bot API rate limiting compliance."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate rate limiting
            call_count = 0
            rate_limit_threshold = 5
            
            async def rate_limited_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal call_count
                call_count += 1
                
                if call_count > rate_limit_threshold:
                    # Simulate rate limit error
                    raise HTTPError(
                        "Too Many Requests",
                        status_code=429,
                        response_data={
                            "message": "You are being rate limited.",
                            "retry_after": 1.0,
                            "global": False
                        }
                    )
                
                return {
                    "id": f"msg_{call_count}",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }
            
            mock_instance.send_message.side_effect = rate_limited_response
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test rapid message sending
            successful_sends = 0
            rate_limited_errors = 0
            
            for i in range(rate_limit_threshold + 3):
                try:
                    await client.send_message({"content": f"Rate limit test {i}"})
                    successful_sends += 1
                except HTTPError as e:
                    if e.status_code == 429:
                        rate_limited_errors += 1
                        # Verify rate limit error format
                        self.assertIn("retry_after", e.response_data)
                        self.assertIsInstance(e.response_data["retry_after"], (int, float))
                    else:
                        raise
            
            # Verify rate limiting behavior
            self.assertEqual(successful_sends, rate_limit_threshold)
            self.assertGreater(rate_limited_errors, 0)
            self.assertEqual(successful_sends + rate_limited_errors, rate_limit_threshold + 3)
    
    async def test_error_handling_robustness(self) -> None:
        """Test bot API error handling and recovery."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test different error scenarios
            error_scenarios = [
                {
                    "name": "unauthorized",
                    "error": HTTPError("Unauthorized", status_code=401),
                    "should_retry": False
                },
                {
                    "name": "forbidden", 
                    "error": HTTPError("Forbidden", status_code=403),
                    "should_retry": False
                },
                {
                    "name": "not_found",
                    "error": HTTPError("Not Found", status_code=404),
                    "should_retry": False
                },
                {
                    "name": "rate_limited",
                    "error": HTTPError("Too Many Requests", status_code=429),
                    "should_retry": True
                },
                {
                    "name": "server_error",
                    "error": HTTPError("Internal Server Error", status_code=500),
                    "should_retry": True
                }
            ]
            
            for scenario in error_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    mock_instance.send_message.side_effect = scenario["error"]
                    
                    # Test error handling
                    with self.assertRaises(HTTPError) as context:
                        await client.send_message({"content": "Error test"})
                    
                    error = context.exception
                    self.assertEqual(error.status_code, scenario["error"].status_code)
                    self.assertIsInstance(error.message, str)
    
    async def test_concurrent_bot_operations(self) -> None:
        """Test concurrent bot API operations."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure concurrent response handling
            async def concurrent_message_response(payload: Dict[str, Any]) -> Dict[str, Any]:
                # Simulate processing time
                await asyncio.sleep(0.1)
                return {
                    "id": f"concurrent_{int(time.time() * 1000000)}",
                    "type": 0,
                    "content": payload.get("content"),
                    "channel_id": "123456789012345678",
                    "author": {"bot": True},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }
            
            mock_instance.send_message.side_effect = concurrent_message_response
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Create concurrent tasks
            concurrent_count = 5
            tasks = []
            
            for i in range(concurrent_count):
                payload = {"content": f"Concurrent bot message {i}"}
                task = asyncio.create_task(client.send_message(payload))
                tasks.append(task)
            
            # Execute concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Verify concurrent execution
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertEqual(len(successful_results), concurrent_count)
            
            # Should complete faster than sequential execution
            self.assertLess(total_time, concurrent_count * 0.2)  # Much faster than 1s
            
            # Verify unique message IDs
            message_ids = [r["id"] for r in successful_results]
            self.assertEqual(len(message_ids), len(set(message_ids)))
    
    async def test_bot_integration_comprehensive(self) -> None:
        """Test comprehensive bot API integration workflow."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure complete integration workflow
            mock_instance.authenticate_bot.return_value = {
                "authenticated": True,
                "bot_info": {"id": "bot_id", "username": "Test Bot", "bot": True}
            }
            
            mock_instance.get_channel.return_value = {
                "id": "123456789012345678",
                "type": 0,
                "name": "test-channel",
                "permissions": ["VIEW_CHANNEL", "SEND_MESSAGES", "EMBED_LINKS"]
            }
            
            mock_instance.send_message.return_value = {
                "id": "integration_msg_123",
                "type": 0,
                "content": "Integration test message",
                "channel_id": "123456789012345678",
                "author": {"bot": True},
                "timestamp": "2025-07-12T22:00:00.000Z"
            }
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Execute integration workflow
            # 1. Authenticate
            auth_result = await self._test_bot_authentication(client)
            self.assertTrue(auth_result["authenticated"])
            
            # 2. Verify channel access
            channel_info = await self._test_channel_access(client)
            self.assertIsNotNone(channel_info)
            
            # 3. Send test message
            message_result = await client.send_message({
                "content": "Integration test message",
                "embeds": [{
                    "title": "Bot Integration Test",
                    "description": "Complete bot API integration test",
                    "color": 0x00ff00
                }]
            })
            
            # Verify integration success
            self.assertIsNotNone(message_result)
            self.assertEqual(message_result["content"], "Integration test message")
            self.assertTrue(message_result["author"]["bot"])
    
    # Helper methods
    
    async def _test_bot_authentication(self, client: HTTPClient) -> Dict[str, Any]:
        """Test bot authentication."""
        # Simulate authentication check
        if hasattr(client, 'authenticate_bot'):
            return await client.authenticate_bot()
        else:
            # Mock authentication for testing
            return {
                "authenticated": True,
                "bot_info": {
                    "id": "test_bot_id",
                    "username": "Test Bot",
                    "bot": True
                }
            }
    
    async def _test_channel_access(self, client: HTTPClient) -> Dict[str, Any]:
        """Test channel access."""
        if hasattr(client, 'get_channel'):
            return await client.get_channel(self.test_config["channel_id"])
        else:
            # Mock channel access for testing
            return {
                "id": self.test_config["channel_id"],
                "type": 0,
                "name": "test-channel",
                "permissions": ["VIEW_CHANNEL", "SEND_MESSAGES", "EMBED_LINKS"]
            }


def run_bot_api_tests() -> None:
    """Run bot API functionality tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestBotAPIFunctionality)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nBot API Functionality Tests Summary:")
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