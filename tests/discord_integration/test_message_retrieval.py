#!/usr/bin/env python3
"""Test Message Retrieval Functionality.

This module provides comprehensive tests for Discord message retrieval
functionality, including message fetching, parsing, filtering, pagination,
and content accuracy validation.
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
from src.core.http_client import HTTPClient
from src.exceptions import HTTPError, MessageRetrievalError


class TestMessageRetrieval(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord message retrieval functionality."""
    
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
        
        # Test message data
        self.test_messages = [
            {
                "id": "message_001",
                "type": 0,
                "content": "First test message",
                "channel_id": "123456789012345678",
                "author": {
                    "id": "user_001",
                    "username": "TestUser1",
                    "discriminator": "0001",
                    "avatar": "avatar_hash_1",
                    "bot": False
                },
                "timestamp": "2025-07-12T20:00:00.000Z",
                "edited_timestamp": None,
                "tts": False,
                "mention_everyone": False,
                "mentions": [],
                "mention_roles": [],
                "attachments": [],
                "embeds": [],
                "reactions": [],
                "pinned": False
            },
            {
                "id": "message_002",
                "type": 0,
                "content": "Second test message with embed",
                "channel_id": "123456789012345678",
                "author": {
                    "id": "bot_user_id",
                    "username": "Test Bot",
                    "discriminator": "0000",
                    "avatar": "bot_avatar_hash",
                    "bot": True
                },
                "timestamp": "2025-07-12T21:00:00.000Z",
                "edited_timestamp": None,
                "tts": False,
                "mention_everyone": False,
                "mentions": [],
                "mention_roles": [],
                "attachments": [],
                "embeds": [{
                    "type": "rich",
                    "title": "Test Embed",
                    "description": "This is a test embed",
                    "color": 0x00ff00,
                    "timestamp": "2025-07-12T21:00:00.000Z",
                    "fields": [
                        {"name": "Field 1", "value": "Value 1", "inline": True},
                        {"name": "Field 2", "value": "Value 2", "inline": False}
                    ]
                }],
                "reactions": [],
                "pinned": False
            },
            {
                "id": "message_003",
                "type": 0,
                "content": "Third message with attachment",
                "channel_id": "123456789012345678",
                "author": {
                    "id": "user_002",
                    "username": "TestUser2", 
                    "discriminator": "0002",
                    "avatar": "avatar_hash_2",
                    "bot": False
                },
                "timestamp": "2025-07-12T22:00:00.000Z",
                "edited_timestamp": "2025-07-12T22:05:00.000Z",
                "tts": False,
                "mention_everyone": False,
                "mentions": [],
                "mention_roles": [],
                "attachments": [{
                    "id": "attachment_001",
                    "filename": "test_file.txt",
                    "size": 1234,
                    "url": "https://cdn.discordapp.com/attachments/123/test_file.txt",
                    "proxy_url": "https://media.discordapp.net/attachments/123/test_file.txt",
                    "content_type": "text/plain"
                }],
                "embeds": [],
                "reactions": [{
                    "emoji": {"name": "✅", "id": None},
                    "count": 2,
                    "me": False
                }],
                "pinned": True
            }
        ]
        
        # Thread message data
        self.thread_messages = [
            {
                "id": "thread_msg_001",
                "type": 0,
                "content": "First thread message",
                "channel_id": "thread_987654321",
                "author": {
                    "id": "bot_user_id",
                    "username": "Test Bot",
                    "bot": True
                },
                "timestamp": "2025-07-12T22:10:00.000Z",
                "thread_metadata": {
                    "archived": False,
                    "auto_archive_duration": 1440,
                    "archive_timestamp": None
                }
            },
            {
                "id": "thread_msg_002",
                "type": 0,
                "content": "Second thread message",
                "channel_id": "thread_987654321",
                "author": {
                    "id": "user_001",
                    "username": "TestUser1",
                    "bot": False
                },
                "timestamp": "2025-07-12T22:15:00.000Z"
            }
        ]
    
    async def test_fetch_channel_messages_basic(self) -> None:
        """Test basic channel message retrieval."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure message retrieval response
            mock_instance.get_channel_messages.return_value = self.test_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test message retrieval
            messages = await client.get_channel_messages(self.test_config["channel_id"])
            
            # Verify retrieval results
            self.assertIsNotNone(messages)
            self.assertEqual(len(messages), 3)
            
            # Verify message structure
            for i, message in enumerate(messages):
                expected_message = self.test_messages[i]
                self.assertEqual(message["id"], expected_message["id"])
                self.assertEqual(message["content"], expected_message["content"])
                self.assertEqual(message["channel_id"], expected_message["channel_id"])
                self.assertIn("author", message)
                self.assertIn("timestamp", message)
            
            # Verify API call
            mock_instance.get_channel_messages.assert_called_once_with(
                self.test_config["channel_id"]
            )
    
    async def test_fetch_messages_with_limit(self) -> None:
        """Test message retrieval with limit parameter."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure limited response
            limited_messages = self.test_messages[:2]  # Only first 2 messages
            mock_instance.get_channel_messages.return_value = limited_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test with limit
            messages = await client.get_channel_messages(
                channel_id=self.test_config["channel_id"],
                limit=2
            )
            
            # Verify limited results
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["id"], "message_001")
            self.assertEqual(messages[1]["id"], "message_002")
            
            # Verify API call with limit
            mock_instance.get_channel_messages.assert_called_once_with(
                self.test_config["channel_id"], limit=2
            )
    
    async def test_fetch_messages_with_pagination(self) -> None:
        """Test message retrieval with pagination (before/after)."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure paginated responses
            first_page = self.test_messages[:2]
            second_page = [self.test_messages[2]]
            
            # Mock paginated calls
            call_count = 0
            async def mock_get_messages(channel_id, limit=None, before=None, after=None):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return first_page
                else:
                    return second_page
            
            mock_instance.get_channel_messages.side_effect = mock_get_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test first page
            first_messages = await client.get_channel_messages(
                channel_id=self.test_config["channel_id"],
                limit=2
            )
            
            # Test second page (after last message from first page)
            last_message_id = first_messages[-1]["id"]
            second_messages = await client.get_channel_messages(
                channel_id=self.test_config["channel_id"],
                after=last_message_id
            )
            
            # Verify pagination results
            self.assertEqual(len(first_messages), 2)
            self.assertEqual(len(second_messages), 1)
            self.assertEqual(second_messages[0]["id"], "message_003")
            
            # Verify both API calls were made
            self.assertEqual(mock_instance.get_channel_messages.call_count, 2)
    
    async def test_fetch_specific_message(self) -> None:
        """Test retrieval of a specific message by ID."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure specific message response
            target_message = self.test_messages[1]  # Second message
            mock_instance.get_message.return_value = target_message
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test specific message retrieval
            message = await client.get_message(
                channel_id=self.test_config["channel_id"],
                message_id="message_002"
            )
            
            # Verify specific message
            self.assertIsNotNone(message)
            self.assertEqual(message["id"], "message_002")
            self.assertEqual(message["content"], "Second test message with embed")
            self.assertTrue(message["author"]["bot"])
            self.assertEqual(len(message["embeds"]), 1)
            
            # Verify API call
            mock_instance.get_message.assert_called_once_with(
                self.test_config["channel_id"], "message_002"
            )
    
    async def test_fetch_thread_messages(self) -> None:
        """Test retrieval of messages from a thread."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure thread message response
            mock_instance.get_thread_messages.return_value = self.thread_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test thread message retrieval
            thread_id = "thread_987654321"
            messages = await client.get_thread_messages(thread_id)
            
            # Verify thread messages
            self.assertIsNotNone(messages)
            self.assertEqual(len(messages), 2)
            
            for message in messages:
                self.assertEqual(message["channel_id"], thread_id)
                self.assertIn("author", message)
                self.assertIn("timestamp", message)
            
            # Verify mix of bot and user messages
            bot_messages = [m for m in messages if m["author"]["bot"]]
            user_messages = [m for m in messages if not m["author"]["bot"]]
            
            self.assertEqual(len(bot_messages), 1)
            self.assertEqual(len(user_messages), 1)
            
            # Verify API call
            mock_instance.get_thread_messages.assert_called_once_with(thread_id)
    
    async def test_message_parsing_accuracy(self) -> None:
        """Test accuracy of message content parsing."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test complex message with various content types
            complex_message = {
                "id": "complex_msg_001",
                "type": 0,
                "content": "Complex message with @user mentions and #channel references",
                "channel_id": "123456789012345678",
                "author": {
                    "id": "user_003",
                    "username": "ComplexUser",
                    "discriminator": "0003",
                    "bot": False
                },
                "timestamp": "2025-07-12T22:30:00.000Z",
                "mentions": [{
                    "id": "mentioned_user_id",
                    "username": "MentionedUser",
                    "discriminator": "0004"
                }],
                "mention_channels": [{
                    "id": "mentioned_channel_id",
                    "name": "mentioned-channel",
                    "type": 0
                }],
                "embeds": [{
                    "type": "rich",
                    "title": "Complex Embed",
                    "description": "Embed with various fields",
                    "color": 0xff0000,
                    "fields": [
                        {"name": "URL Field", "value": "https://example.com", "inline": True},
                        {"name": "Code Field", "value": "`code snippet`", "inline": False},
                        {"name": "Markdown Field", "value": "**bold** and *italic*", "inline": True}
                    ],
                    "footer": {"text": "Footer text", "icon_url": "https://example.com/icon.png"},
                    "image": {"url": "https://example.com/image.png"},
                    "thumbnail": {"url": "https://example.com/thumb.png"}
                }],
                "reactions": [
                    {"emoji": {"name": "👍", "id": None}, "count": 5, "me": True},
                    {"emoji": {"name": "custom_emoji", "id": "custom_emoji_id"}, "count": 2, "me": False}
                ]
            }
            
            mock_instance.get_message.return_value = complex_message
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test parsing complex message
            message = await client.get_message(
                channel_id=self.test_config["channel_id"],
                message_id="complex_msg_001"
            )
            
            # Verify complex content parsing
            self.assertEqual(message["content"], complex_message["content"])
            self.assertEqual(len(message["mentions"]), 1)
            self.assertEqual(len(message["mention_channels"]), 1)
            self.assertEqual(len(message["embeds"]), 1)
            self.assertEqual(len(message["reactions"]), 2)
            
            # Verify embed parsing
            embed = message["embeds"][0]
            self.assertEqual(embed["title"], "Complex Embed")
            self.assertEqual(embed["color"], 0xff0000)
            self.assertEqual(len(embed["fields"]), 3)
            self.assertIn("footer", embed)
            self.assertIn("image", embed)
            self.assertIn("thumbnail", embed)
            
            # Verify reaction parsing
            reactions = message["reactions"]
            unicode_reaction = next(r for r in reactions if r["emoji"]["name"] == "👍")
            custom_reaction = next(r for r in reactions if r["emoji"]["name"] == "custom_emoji")
            
            self.assertIsNone(unicode_reaction["emoji"]["id"])
            self.assertIsNotNone(custom_reaction["emoji"]["id"])
            self.assertTrue(unicode_reaction["me"])
            self.assertFalse(custom_reaction["me"])
    
    async def test_message_filtering_by_author(self) -> None:
        """Test filtering messages by author."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            mock_instance.get_channel_messages.return_value = self.test_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Get all messages
            all_messages = await client.get_channel_messages(self.test_config["channel_id"])
            
            # Filter by bot messages
            bot_messages = [msg for msg in all_messages if msg["author"]["bot"]]
            user_messages = [msg for msg in all_messages if not msg["author"]["bot"]]
            
            # Verify filtering
            self.assertEqual(len(bot_messages), 1)
            self.assertEqual(len(user_messages), 2)
            
            # Verify bot message
            bot_message = bot_messages[0]
            self.assertEqual(bot_message["id"], "message_002")
            self.assertTrue(bot_message["author"]["bot"])
            
            # Verify user messages
            user_ids = {msg["author"]["id"] for msg in user_messages}
            self.assertEqual(user_ids, {"user_001", "user_002"})
    
    async def test_message_filtering_by_content(self) -> None:
        """Test filtering messages by content patterns."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            mock_instance.get_channel_messages.return_value = self.test_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Get all messages
            all_messages = await client.get_channel_messages(self.test_config["channel_id"])
            
            # Filter by content patterns
            embed_messages = [msg for msg in all_messages if "embed" in msg["content"].lower()]
            attachment_messages = [msg for msg in all_messages if "attachment" in msg["content"].lower()]
            test_messages = [msg for msg in all_messages if "test" in msg["content"].lower()]
            
            # Verify content filtering
            self.assertEqual(len(embed_messages), 1)
            self.assertEqual(embed_messages[0]["id"], "message_002")
            
            self.assertEqual(len(attachment_messages), 1)
            self.assertEqual(attachment_messages[0]["id"], "message_003")
            
            self.assertEqual(len(test_messages), 3)  # All contain "test"
    
    async def test_message_filtering_by_timestamp(self) -> None:
        """Test filtering messages by timestamp ranges."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            mock_instance.get_channel_messages.return_value = self.test_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Get all messages
            all_messages = await client.get_channel_messages(self.test_config["channel_id"])
            
            # Helper function to parse timestamps
            def parse_timestamp(timestamp_str: str) -> float:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return dt.timestamp()
            
            # Filter by timestamp (messages after 20:30 UTC)
            cutoff_time = parse_timestamp("2025-07-12T20:30:00.000Z")
            recent_messages = [
                msg for msg in all_messages 
                if parse_timestamp(msg["timestamp"]) > cutoff_time
            ]
            
            # Verify timestamp filtering
            self.assertEqual(len(recent_messages), 2)  # message_002 and message_003
            recent_ids = {msg["id"] for msg in recent_messages}
            self.assertEqual(recent_ids, {"message_002", "message_003"})
    
    async def test_message_retrieval_error_handling(self) -> None:
        """Test error handling in message retrieval."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test different error scenarios
            error_scenarios = [
                {
                    "name": "channel_not_found",
                    "error": HTTPError("Channel not found", status_code=404),
                    "method": "get_channel_messages"
                },
                {
                    "name": "insufficient_permissions",
                    "error": HTTPError("Missing access", status_code=403),
                    "method": "get_channel_messages"
                },
                {
                    "name": "message_not_found",
                    "error": HTTPError("Message not found", status_code=404),
                    "method": "get_message"
                },
                {
                    "name": "rate_limited",
                    "error": HTTPError("Rate limited", status_code=429),
                    "method": "get_thread_messages"
                }
            ]
            
            for scenario in error_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Configure error
                    if scenario["method"] == "get_channel_messages":
                        mock_instance.get_channel_messages.side_effect = scenario["error"]
                    elif scenario["method"] == "get_message":
                        mock_instance.get_message.side_effect = scenario["error"]
                    elif scenario["method"] == "get_thread_messages":
                        mock_instance.get_thread_messages.side_effect = scenario["error"]
                    
                    # Test error handling
                    with self.assertRaises(HTTPError) as context:
                        if scenario["method"] == "get_channel_messages":
                            await client.get_channel_messages("invalid_channel_id")
                        elif scenario["method"] == "get_message":
                            await client.get_message("channel_id", "invalid_message_id")
                        elif scenario["method"] == "get_thread_messages":
                            await client.get_thread_messages("invalid_thread_id")
                    
                    # Verify error details
                    error = context.exception
                    self.assertEqual(error.status_code, scenario["error"].status_code)
    
    async def test_message_retrieval_performance(self) -> None:
        """Test message retrieval performance with large datasets."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Generate large message dataset
            large_message_set = []
            for i in range(100):
                message = {
                    "id": f"perf_msg_{i:03d}",
                    "type": 0,
                    "content": f"Performance test message {i}",
                    "channel_id": "123456789012345678",
                    "author": {
                        "id": f"user_{i % 10}",  # 10 different users
                        "username": f"PerfUser{i % 10}",
                        "bot": i % 20 == 0  # Every 20th message from bot
                    },
                    "timestamp": f"2025-07-12T{20 + (i // 60):02d}:{i % 60:02d}:00.000Z"
                }
                large_message_set.append(message)
            
            # Configure performance response
            async def mock_get_messages(channel_id, limit=None, **kwargs):
                # Simulate processing time
                await asyncio.sleep(0.01)
                return large_message_set[:limit] if limit else large_message_set
            
            mock_instance.get_channel_messages.side_effect = mock_get_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test performance with different limits
            performance_tests = [
                {"limit": 10, "max_time": 0.1},
                {"limit": 50, "max_time": 0.2},
                {"limit": 100, "max_time": 0.3}
            ]
            
            for test in performance_tests:
                with self.subTest(limit=test["limit"]):
                    start_time = time.time()
                    
                    messages = await client.get_channel_messages(
                        channel_id=self.test_config["channel_id"],
                        limit=test["limit"]
                    )
                    
                    retrieval_time = time.time() - start_time
                    
                    # Verify performance
                    self.assertEqual(len(messages), test["limit"])
                    self.assertLess(retrieval_time, test["max_time"],
                                  f"Retrieval of {test['limit']} messages took {retrieval_time:.3f}s")
                    
                    # Log performance metrics
                    self.logger.info(
                        f"Message retrieval performance",
                        context={
                            "message_count": test["limit"],
                            "retrieval_time": retrieval_time,
                            "messages_per_second": test["limit"] / retrieval_time if retrieval_time > 0 else float('inf')
                        }
                    )
    
    async def test_concurrent_message_retrieval(self) -> None:
        """Test concurrent message retrieval operations."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure concurrent responses
            async def concurrent_get_messages(channel_id, **kwargs):
                # Simulate processing time
                await asyncio.sleep(0.1)
                # Return different messages based on channel ID
                channel_num = channel_id[-1]
                return [{
                    "id": f"concurrent_msg_{channel_num}",
                    "content": f"Message from channel {channel_num}",
                    "channel_id": channel_id,
                    "author": {"id": "user_001", "bot": False},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }]
            
            mock_instance.get_channel_messages.side_effect = concurrent_get_messages
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Create concurrent retrieval tasks
            channel_ids = [f"12345678901234567{i}" for i in range(5)]
            tasks = []
            
            for channel_id in channel_ids:
                task = asyncio.create_task(
                    client.get_channel_messages(channel_id)
                )
                tasks.append(task)
            
            # Execute concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Verify concurrent execution
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertEqual(len(successful_results), 5)
            
            # Should be faster than sequential (5 * 0.1s = 0.5s)
            self.assertLess(total_time, 0.3, f"Concurrent retrieval took {total_time:.3f}s")
            
            # Verify each result is unique
            channel_nums = set()
            for result in successful_results:
                messages = result
                self.assertEqual(len(messages), 1)
                message = messages[0]
                channel_num = message["channel_id"][-1]
                channel_nums.add(channel_num)
            
            self.assertEqual(len(channel_nums), 5)  # All unique channels
    
    async def test_message_content_validation(self) -> None:
        """Test validation of retrieved message content integrity."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test message with special characters and formatting
            special_message = {
                "id": "special_msg_001",
                "type": 0,
                "content": "Message with special chars: éñ🎯 and code `const x = 'test';` and **bold** text",
                "channel_id": "123456789012345678",
                "author": {"id": "user_001", "username": "TestUser", "bot": False},
                "timestamp": "2025-07-12T22:00:00.000Z",
                "embeds": [{
                    "description": "Embed with unicode: 世界 and emojis: 🌍🚀",
                    "fields": [
                        {"name": "Code Block", "value": "```python\nprint('hello')\n```"},
                        {"name": "URL", "value": "https://example.com/path?param=value&other=123"}
                    ]
                }]
            }
            
            mock_instance.get_message.return_value = special_message
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test content integrity
            message = await client.get_message(
                channel_id=self.test_config["channel_id"],
                message_id="special_msg_001"
            )
            
            # Verify content preservation
            self.assertEqual(message["content"], special_message["content"])
            
            # Verify special characters preserved
            self.assertIn("éñ🎯", message["content"])
            self.assertIn("`const x = 'test';`", message["content"])
            self.assertIn("**bold**", message["content"])
            
            # Verify embed content preservation
            embed = message["embeds"][0]
            self.assertIn("世界", embed["description"])
            self.assertIn("🌍🚀", embed["description"])
            
            # Verify code block and URL preservation
            code_field = next(f for f in embed["fields"] if f["name"] == "Code Block")
            url_field = next(f for f in embed["fields"] if f["name"] == "URL")
            
            self.assertIn("```python", code_field["value"])
            self.assertIn("print('hello')", code_field["value"])
            self.assertIn("https://example.com/path?param=value&other=123", url_field["value"])


def run_message_retrieval_tests() -> None:
    """Run message retrieval tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMessageRetrieval)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nMessage Retrieval Tests Summary:")
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