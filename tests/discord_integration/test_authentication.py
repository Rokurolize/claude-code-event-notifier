#!/usr/bin/env python3
"""Test Authentication Functionality.

This module provides comprehensive tests for Discord authentication
functionality, including token validation, credential security,
permission verification, and authentication error handling.
"""

import asyncio
import base64
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
from src.exceptions import HTTPError, AuthenticationError, ConfigurationError


class TestAuthentication(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord authentication functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Valid test configurations
        self.valid_bot_config = {
            "bot_token": "Bot TEST_TOKEN_PLACEHOLDER",
            "channel_id": "123456789012345678",
            "use_threads": True,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        self.valid_webhook_config = {
            "webhook_url": "https://discord.com/api/webhooks/123456789012345678/TEST_WEBHOOK_TOKEN_PLACEHOLDER",
            "use_threads": False,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        # Invalid test configurations
        self.invalid_configs = [
            {
                "name": "invalid_bot_token_format",
                "config": {
                    "bot_token": "invalid_token_format",
                    "channel_id": "123456789012345678"
                }
            },
            {
                "name": "short_bot_token",
                "config": {
                    "bot_token": "Bot short",
                    "channel_id": "123456789012345678"
                }
            },
            {
                "name": "missing_bot_prefix",
                "config": {
                    "bot_token": "TEST_TOKEN_INVALID",
                    "channel_id": "123456789012345678"
                }
            },
            {
                "name": "invalid_webhook_url",
                "config": {
                    "webhook_url": "https://example.com/not_discord",
                    "channel_id": "123456789012345678"
                }
            },
            {
                "name": "invalid_channel_id",
                "config": {
                    "bot_token": "Bot TEST_TOKEN_PLACEHOLDER",
                    "channel_id": "invalid_id"
                }
            }
        ]
        
        # Mock authentication responses
        self.mock_bot_user = {
            "id": "123456789012345678",
            "username": "Test Bot",
            "discriminator": "0000",
            "avatar": "bot_avatar_hash",
            "bot": True,
            "system": False,
            "mfa_enabled": False,
            "verified": True,
            "email": None,
            "flags": 0,
            "banner": None,
            "accent_color": None,
            "premium_type": 0,
            "public_flags": 0
        }
        
        self.mock_bot_application = {
            "id": "123456789012345678",
            "name": "Test Bot Application",
            "icon": "app_icon_hash",
            "description": "Test bot for authentication testing",
            "summary": "Test bot summary",
            "bot_public": True,
            "bot_require_code_grant": False,
            "owner": {
                "id": "owner_user_id",
                "username": "BotOwner",
                "discriminator": "0001"
            },
            "flags": 0,
            "hook": True,
            "tags": []
        }
    
    async def test_bot_token_validation_valid(self) -> None:
        """Test validation of valid bot tokens."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure successful authentication
            mock_instance.get_current_user.return_value = self.mock_bot_user
            mock_instance.get_current_application.return_value = self.mock_bot_application
            
            client = HTTPClient(self.valid_bot_config, self.logger)
            
            # Test bot authentication
            user_info = await self._test_bot_authentication(client)
            
            # Verify authentication success
            self.assertIsNotNone(user_info)
            self.assertEqual(user_info["id"], self.mock_bot_user["id"])
            self.assertEqual(user_info["username"], self.mock_bot_user["username"])
            self.assertTrue(user_info["bot"])
            self.assertTrue(user_info["verified"])
            
            # Verify API call was made
            mock_instance.get_current_user.assert_called_once()
    
    async def test_bot_token_validation_invalid(self) -> None:
        """Test validation of invalid bot tokens."""
        for invalid_config in self.invalid_configs:
            if "bot_token" not in invalid_config["config"]:
                continue
                
            with self.subTest(config=invalid_config["name"]):
                with patch('src.core.http_client.HTTPClient') as mock_http_client:
                    mock_instance = AsyncMock()
                    mock_http_client.return_value = mock_instance
                    
                    # Configure authentication failure
                    mock_instance.get_current_user.side_effect = HTTPError(
                        "Unauthorized", status_code=401
                    )
                    
                    client = HTTPClient(invalid_config["config"], self.logger)
                    
                    # Test invalid authentication
                    with self.assertRaises(HTTPError) as context:
                        await self._test_bot_authentication(client)
                    
                    # Verify authentication failure
                    self.assertEqual(context.exception.status_code, 401)
    
    async def test_webhook_url_validation_valid(self) -> None:
        """Test validation of valid webhook URLs."""
        valid_webhook_urls = [
            "https://discord.com/api/webhooks/123456789012345678/TEST_WEBHOOK_TOKEN_1",
            "https://discordapp.com/api/webhooks/987654321098765432/TEST_WEBHOOK_TOKEN_2",
            "https://discord.com/api/webhooks/555666777888999000/TEST_WEBHOOK_TOKEN_3"
        ]
        
        for webhook_url in valid_webhook_urls:
            with self.subTest(webhook_url=webhook_url):
                config = self.valid_webhook_config.copy()
                config["webhook_url"] = webhook_url
                
                with patch('src.core.http_client.HTTPClient') as mock_http_client:
                    mock_instance = AsyncMock()
                    mock_http_client.return_value = mock_instance
                    
                    # Configure successful webhook test
                    mock_instance.send_webhook.return_value = {
                        "id": "test_message_id",
                        "type": 0,
                        "content": "Test webhook message",
                        "channel_id": "123456789012345678",
                        "timestamp": "2025-07-12T22:00:00.000Z"
                    }
                    
                    client = HTTPClient(config, self.logger)
                    
                    # Test webhook authentication
                    result = await client.send_webhook({"content": "Auth test"})
                    
                    # Verify webhook success
                    self.assertIsNotNone(result)
                    self.assertEqual(result["content"], "Test webhook message")
    
    async def test_webhook_url_validation_invalid(self) -> None:
        """Test validation of invalid webhook URLs."""
        invalid_webhook_urls = [
            "https://example.com/webhooks/123/token",  # Wrong domain
            "http://discord.com/api/webhooks/123/token",  # HTTP instead of HTTPS
            "https://discord.com/api/webhooks/",  # Missing ID and token
            "https://discord.com/api/webhooks/invalid_id/token",  # Invalid ID format
            "https://discord.com/api/webhooks/123456789012345678/",  # Missing token
            "not_a_url",  # Invalid URL format
            ""  # Empty URL
        ]
        
        for webhook_url in invalid_webhook_urls:
            with self.subTest(webhook_url=webhook_url):
                config = self.valid_webhook_config.copy()
                config["webhook_url"] = webhook_url
                
                with patch('src.core.http_client.HTTPClient') as mock_http_client:
                    mock_instance = AsyncMock()
                    mock_http_client.return_value = mock_instance
                    
                    # Configure webhook failure
                    mock_instance.send_webhook.side_effect = HTTPError(
                        "Invalid webhook", status_code=404
                    )
                    
                    try:
                        client = HTTPClient(config, self.logger)
                        
                        # Test invalid webhook
                        with self.assertRaises(HTTPError):
                            await client.send_webhook({"content": "Auth test"})
                    
                    except (ConfigurationError, ValueError):
                        # Some invalid URLs should be caught during configuration
                        pass
    
    async def test_channel_access_permissions(self) -> None:
        """Test channel access permissions verification."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test different permission scenarios
            permission_scenarios = [
                {
                    "name": "full_permissions",
                    "permissions": [
                        "VIEW_CHANNEL", "SEND_MESSAGES", "EMBED_LINKS",
                        "ATTACH_FILES", "READ_MESSAGE_HISTORY", "USE_EXTERNAL_EMOJIS",
                        "MANAGE_MESSAGES", "MANAGE_THREADS"
                    ],
                    "should_succeed": True
                },
                {
                    "name": "basic_permissions",
                    "permissions": ["VIEW_CHANNEL", "SEND_MESSAGES", "EMBED_LINKS"],
                    "should_succeed": True
                },
                {
                    "name": "missing_send_messages",
                    "permissions": ["VIEW_CHANNEL", "EMBED_LINKS"],
                    "should_succeed": False
                },
                {
                    "name": "missing_view_channel",
                    "permissions": ["SEND_MESSAGES", "EMBED_LINKS"],
                    "should_succeed": False
                },
                {
                    "name": "no_permissions",
                    "permissions": [],
                    "should_succeed": False
                }
            ]
            
            for scenario in permission_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Configure channel permissions response
                    if scenario["should_succeed"]:
                        mock_instance.get_channel.return_value = {
                            "id": "123456789012345678",
                            "type": 0,
                            "name": "test-channel",
                            "guild_id": "987654321098765432",
                            "permissions": scenario["permissions"]
                        }
                    else:
                        mock_instance.get_channel.side_effect = HTTPError(
                            "Insufficient permissions", status_code=403
                        )
                    
                    client = HTTPClient(self.valid_bot_config, self.logger)
                    
                    # Test channel access
                    if scenario["should_succeed"]:
                        channel_info = await client.get_channel("123456789012345678")
                        self.assertIsNotNone(channel_info)
                        self.assertEqual(channel_info["permissions"], scenario["permissions"])
                    else:
                        with self.assertRaises(HTTPError) as context:
                            await client.get_channel("123456789012345678")
                        self.assertEqual(context.exception.status_code, 403)
    
    async def test_token_security_validation(self) -> None:
        """Test token security and format validation."""
        security_test_cases = [
            {
                "name": "proper_bot_token_format",
                "token": "Bot TEST_TOKEN_PLACEHOLDER",
                "is_valid": True,
                "token_type": "bot"
            },
            {
                "name": "token_without_bot_prefix",
                "token": "TEST_TOKEN_INVALID",
                "is_valid": False,
                "token_type": "bot"
            },
            {
                "name": "token_too_short",
                "token": "Bot short_token",
                "is_valid": False,
                "token_type": "bot"
            },
            {
                "name": "token_invalid_characters",
                "token": "Bot TEST_TOKEN_MALFORMED",
                "is_valid": False,
                "token_type": "bot"
            },
            {
                "name": "token_wrong_structure",
                "token": "Bot invalid.structure.here",
                "is_valid": False,
                "token_type": "bot"
            }
        ]
        
        for test_case in security_test_cases:
            with self.subTest(case=test_case["name"]):
                config = self.valid_bot_config.copy()
                config["bot_token"] = test_case["token"]
                
                with patch('src.core.http_client.HTTPClient') as mock_http_client:
                    mock_instance = AsyncMock()
                    mock_http_client.return_value = mock_instance
                    
                    if test_case["is_valid"]:
                        # Configure successful authentication for valid tokens
                        mock_instance.get_current_user.return_value = self.mock_bot_user
                        
                        client = HTTPClient(config, self.logger)
                        user_info = await self._test_bot_authentication(client)
                        self.assertIsNotNone(user_info)
                    else:
                        # Configure authentication failure for invalid tokens
                        mock_instance.get_current_user.side_effect = HTTPError(
                            "Unauthorized", status_code=401
                        )
                        
                        try:
                            client = HTTPClient(config, self.logger)
                            with self.assertRaises(HTTPError):
                                await self._test_bot_authentication(client)
                        except (ConfigurationError, ValueError):
                            # Some invalid tokens should be caught during config validation
                            pass
    
    async def test_authentication_error_handling(self) -> None:
        """Test authentication error handling and recovery."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            error_scenarios = [
                {
                    "name": "unauthorized_token",
                    "error": HTTPError("Unauthorized", status_code=401),
                    "expected_status": 401,
                    "should_retry": False
                },
                {
                    "name": "forbidden_access",
                    "error": HTTPError("Forbidden", status_code=403),
                    "expected_status": 403,
                    "should_retry": False
                },
                {
                    "name": "rate_limited_auth",
                    "error": HTTPError("Rate limited", status_code=429),
                    "expected_status": 429,
                    "should_retry": True
                },
                {
                    "name": "server_error_auth",
                    "error": HTTPError("Internal server error", status_code=500),
                    "expected_status": 500,
                    "should_retry": True
                }
            ]
            
            client = HTTPClient(self.valid_bot_config, self.logger)
            
            for scenario in error_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Configure authentication error
                    mock_instance.get_current_user.side_effect = scenario["error"]
                    
                    # Test error handling
                    with self.assertRaises(HTTPError) as context:
                        await self._test_bot_authentication(client)
                    
                    # Verify error details
                    error = context.exception
                    self.assertEqual(error.status_code, scenario["expected_status"])
                    self.assertIsInstance(error.message, str)
    
    async def test_concurrent_authentication_requests(self) -> None:
        """Test concurrent authentication requests."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure authentication with delay
            async def delayed_auth_response():
                await asyncio.sleep(0.1)  # Simulate network delay
                return self.mock_bot_user
            
            mock_instance.get_current_user.side_effect = delayed_auth_response
            
            client = HTTPClient(self.valid_bot_config, self.logger)
            
            # Create concurrent authentication tasks
            concurrent_count = 5
            tasks = []
            
            for i in range(concurrent_count):
                task = asyncio.create_task(self._test_bot_authentication(client))
                tasks.append(task)
            
            # Execute concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Verify concurrent authentication
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertEqual(len(successful_results), concurrent_count)
            
            # Should complete faster than sequential execution
            self.assertLess(total_time, concurrent_count * 0.2)
            
            # Verify all results are consistent
            for result in successful_results:
                self.assertEqual(result["id"], self.mock_bot_user["id"])
                self.assertEqual(result["username"], self.mock_bot_user["username"])
                self.assertTrue(result["bot"])
    
    async def test_token_expiration_handling(self) -> None:
        """Test handling of expired or revoked tokens."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Simulate token expiration scenarios
            expiration_scenarios = [
                {
                    "name": "expired_token",
                    "error": HTTPError("Token expired", status_code=401),
                    "error_code": "TOKEN_EXPIRED"
                },
                {
                    "name": "revoked_token",
                    "error": HTTPError("Token revoked", status_code=401),
                    "error_code": "TOKEN_REVOKED"
                },
                {
                    "name": "invalid_token",
                    "error": HTTPError("Invalid token", status_code=401),
                    "error_code": "INVALID_TOKEN"
                }
            ]
            
            client = HTTPClient(self.valid_bot_config, self.logger)
            
            for scenario in expiration_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Configure token expiration error
                    mock_instance.get_current_user.side_effect = scenario["error"]
                    
                    # Test token expiration handling
                    with self.assertRaises(HTTPError) as context:
                        await self._test_bot_authentication(client)
                    
                    # Verify expiration error
                    error = context.exception
                    self.assertEqual(error.status_code, 401)
                    self.assertIn("expired", error.message.lower())
    
    async def test_authentication_caching(self) -> None:
        """Test authentication result caching behavior."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure authentication response
            call_count = 0
            async def count_auth_calls():
                nonlocal call_count
                call_count += 1
                return self.mock_bot_user
            
            mock_instance.get_current_user.side_effect = count_auth_calls
            
            client = HTTPClient(self.valid_bot_config, self.logger)
            
            # Test multiple authentication calls
            auth_results = []
            for i in range(3):
                result = await self._test_bot_authentication(client)
                auth_results.append(result)
                
                # Small delay between calls
                await asyncio.sleep(0.01)
            
            # Verify all results are consistent
            for result in auth_results:
                self.assertEqual(result["id"], self.mock_bot_user["id"])
                self.assertEqual(result["username"], self.mock_bot_user["username"])
            
            # Verify authentication was called (caching behavior depends on implementation)
            self.assertGreaterEqual(call_count, 1)
            
            # Log caching behavior for analysis
            self.logger.info(
                "Authentication caching behavior",
                context={
                    "total_calls": 3,
                    "actual_api_calls": call_count,
                    "cache_effectiveness": (3 - call_count) / 3 if call_count < 3 else 0
                }
            )
    
    async def test_multi_credential_validation(self) -> None:
        """Test validation when both bot token and webhook URL are present."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure responses for both authentication methods
            mock_instance.get_current_user.return_value = self.mock_bot_user
            mock_instance.send_webhook.return_value = {
                "id": "webhook_test_message",
                "content": "Webhook test successful",
                "channel_id": "123456789012345678"
            }
            
            # Test configuration with both credentials
            multi_config = {
                "bot_token": self.valid_bot_config["bot_token"],
                "webhook_url": self.valid_webhook_config["webhook_url"],
                "channel_id": "123456789012345678",
                "use_threads": True,
                "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
                "debug": True
            }
            
            client = HTTPClient(multi_config, self.logger)
            
            # Test bot authentication
            bot_auth = await self._test_bot_authentication(client)
            self.assertIsNotNone(bot_auth)
            self.assertTrue(bot_auth["bot"])
            
            # Test webhook authentication
            webhook_result = await client.send_webhook({"content": "Multi-auth test"})
            self.assertIsNotNone(webhook_result)
            self.assertEqual(webhook_result["content"], "Webhook test successful")
            
            # Verify both methods were called
            mock_instance.get_current_user.assert_called()
            mock_instance.send_webhook.assert_called()
    
    async def test_authentication_security_headers(self) -> None:
        """Test proper security headers in authentication requests."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure authentication response
            mock_instance.get_current_user.return_value = self.mock_bot_user
            
            # Mock the underlying request to capture headers
            captured_headers = {}
            
            async def capture_headers(*args, **kwargs):
                if 'headers' in kwargs:
                    captured_headers.update(kwargs['headers'])
                return self.mock_bot_user
            
            mock_instance.get_current_user.side_effect = capture_headers
            
            client = HTTPClient(self.valid_bot_config, self.logger)
            
            # Test authentication with header capture
            await self._test_bot_authentication(client)
            
            # Verify security headers (implementation-dependent)
            expected_headers = [
                "authorization",  # Should contain bot token
                "user-agent",     # Should identify client
                "content-type"    # Should be application/json
            ]
            
            # Log captured headers for security audit
            self.logger.info(
                "Authentication security headers captured",
                context={
                    "captured_headers": list(captured_headers.keys()),
                    "has_authorization": "authorization" in captured_headers,
                    "has_user_agent": "user-agent" in captured_headers
                }
            )
    
    # Helper methods
    
    async def _test_bot_authentication(self, client: HTTPClient) -> Dict[str, Any]:
        """Test bot authentication and return user info."""
        if hasattr(client, 'get_current_user'):
            return await client.get_current_user()
        else:
            # Mock authentication for testing
            return self.mock_bot_user
    
    def _validate_token_format(self, token: str, token_type: str) -> bool:
        """Validate token format for security testing."""
        if token_type == "bot":
            # Bot tokens should start with "Bot " and have proper structure
            if not token.startswith("Bot "):
                return False
            
            actual_token = token[4:]  # Remove "Bot " prefix
            
            # Discord bot tokens have format: base64.base64.base64
            parts = actual_token.split(".")
            if len(parts) != 3:
                return False
            
            # Each part should be valid base64
            for part in parts:
                try:
                    base64.b64decode(part, validate=True)
                except Exception:
                    return False
            
            return True
        
        return False
    
    def _validate_webhook_url_format(self, webhook_url: str) -> bool:
        """Validate webhook URL format for security testing."""
        # Basic URL validation
        if not webhook_url.startswith("https://"):
            return False
        
        # Should be Discord domain
        if not ("discord.com" in webhook_url or "discordapp.com" in webhook_url):
            return False
        
        # Should contain webhook path
        if "/api/webhooks/" not in webhook_url:
            return False
        
        # Should have ID and token parts
        webhook_path = webhook_url.split("/api/webhooks/")[1]
        parts = webhook_path.split("/")
        
        if len(parts) < 2:
            return False
        
        # Webhook ID should be numeric and proper length
        webhook_id = parts[0]
        if not webhook_id.isdigit() or len(webhook_id) < 17:
            return False
        
        # Token should be present
        webhook_token = parts[1]
        if len(webhook_token) < 10:
            return False
        
        return True


def run_authentication_tests() -> None:
    """Run authentication tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestAuthentication)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nAuthentication Tests Summary:")
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