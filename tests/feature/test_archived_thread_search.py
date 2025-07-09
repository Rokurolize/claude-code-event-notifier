#!/usr/bin/env python3
"""Test archived thread search functionality in discord_notifier.py.

This test verifies that the Discord notifier can find threads in all states:
- Active threads
- Public archived threads
- Private archived threads

It also tests the deduplication functionality to prevent creating duplicate threads.
"""

from __future__ import annotations

import json
import logging
import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, Mock, patch

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from discord_notifier import (  # noqa: E402
    DiscordAPIError,
    HTTPClient,
    find_existing_thread_by_name,
    get_or_create_thread,
)

if TYPE_CHECKING:
    from discord_notifier import Config


class TestArchivedThreadSearch(unittest.TestCase):
    """Test cases for archived thread search functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = logging.getLogger("test")
        self.logger.setLevel(logging.DEBUG)

        # Mock config
        self.config: Config = {
            "webhook_url": "https://discord.com/api/webhooks/123/token",
            "bot_token": "test_bot_token",
            "channel_id": "123456789",
            "use_threads": True,
            "channel_type": "text",
            "thread_prefix": "Session",
            "thread_storage_path": None,
            "thread_cleanup_days": 30,
            "debug": False,
            "mention_user_id": None,
            "enabled_events": None,
            "disabled_events": None,
        }

        # Sample thread data
        self.active_thread = {
            "id": "111111111111111111",
            "name": "Session abcd1234",
            "type": 11,
            "thread_metadata": {"archived": False, "locked": False},
        }

        self.archived_thread = {
            "id": "222222222222222222",
            "name": "Session efgh5678",
            "type": 11,
            "thread_metadata": {
                "archived": True,
                "locked": False,
                "archive_timestamp": "2025-01-01T00:00:00.000000+00:00",
            },
        }

        self.private_archived_thread = {
            "id": "333333333333333333",
            "name": "Session ijkl9012",
            "type": 12,  # Private thread
            "thread_metadata": {
                "archived": True,
                "locked": False,
                "archive_timestamp": "2025-01-02T00:00:00.000000+00:00",
            },
        }

    def test_list_public_archived_threads(self) -> None:
        """Test listing public archived threads."""
        http_client = HTTPClient(self.logger)

        # Mock response with context manager support
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"threads": [self.archived_thread], "has_more": False}).encode()  # type: ignore[misc]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        with patch("urllib.request.urlopen", return_value=mock_response):
            threads, has_more = http_client.list_public_archived_threads(  # type: ignore[misc]
                str(self.config["channel_id"]), str(self.config["bot_token"])
            )

            assert len(threads) == 1  # type: ignore[misc]
            assert threads[0]["id"] == self.archived_thread["id"]  # type: ignore[misc]
            assert not has_more

    def test_list_private_archived_threads(self) -> None:
        """Test listing private archived threads."""
        http_client = HTTPClient(self.logger)

        # Mock response with context manager support
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({  # type: ignore[misc]
            "threads": [self.private_archived_thread],
            "has_more": False,
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        with patch("urllib.request.urlopen", return_value=mock_response):
            threads, has_more = http_client.list_private_archived_threads(  # type: ignore[misc]
                str(self.config["channel_id"]), str(self.config["bot_token"])
            )

            assert len(threads) == 1  # type: ignore[misc]
            assert threads[0]["id"] == self.private_archived_thread["id"]  # type: ignore[misc]
            assert not has_more

    def test_search_all_threads_comprehensive(self) -> None:
        """Test comprehensive thread search across all states."""
        http_client = HTTPClient(self.logger)

        # Mock the individual list methods
        with (
            patch.object(http_client, "list_active_threads", return_value=[self.active_thread]),
            patch.object(http_client, "list_public_archived_threads", return_value=([self.archived_thread], False)),
            patch.object(
                http_client, "list_private_archived_threads", return_value=([self.private_archived_thread], False)
            ),
        ):
            # Search for threads with "Session" in the name
            threads = http_client.search_all_threads(  # type: ignore[misc]
                str(self.config["channel_id"]), "Session", str(self.config["bot_token"])
            )

            # Should find all three threads
            assert len(threads) == 3  # type: ignore[misc]
            thread_ids = [t["id"] for t in threads]  # type: ignore[misc]
            assert self.active_thread["id"] in thread_ids  # type: ignore[misc]
            assert self.archived_thread["id"] in thread_ids  # type: ignore[misc]
            assert self.private_archived_thread["id"] in thread_ids  # type: ignore[misc]

    def test_search_all_threads_with_pagination(self) -> None:
        """Test thread search with pagination for archived threads."""
        http_client = HTTPClient(self.logger)

        # Create multiple pages of archived threads
        page1_threads = [
            {
                "id": f"4{i:017d}",
                "name": f"Session page1_{i}",
                "thread_metadata": {
                    "archived": True,
                    "archive_timestamp": f"2025-01-{10 - i:02d}T00:00:00.000000+00:00",
                },
            }
            for i in range(3)
        ]

        page2_threads = [
            {
                "id": f"5{i:017d}",
                "name": f"Session page2_{i}",
                "thread_metadata": {
                    "archived": True,
                    "archive_timestamp": f"2025-01-{5 - i:02d}T00:00:00.000000+00:00",
                },
            }
            for i in range(2)
        ]

        # Mock paginated responses
        call_count = 0

        def mock_list_public_archived(
            _channel_id: str,
            _token: str,
            before: str | None = None,  # noqa: ARG001
            limit: int = 100,  # noqa: ARG001
        ) -> tuple[list[dict[str, Any]], bool]:  # type: ignore[misc]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First page
                return page1_threads, True
            # Second page
            return page2_threads, False

        with (
            patch.object(http_client, "list_active_threads", return_value=[]),
            patch.object(http_client, "list_public_archived_threads", side_effect=mock_list_public_archived),
            patch.object(http_client, "list_private_archived_threads", return_value=([], False)),
        ):
            threads = http_client.search_all_threads(  # type: ignore[misc]
                str(self.config["channel_id"]), "Session", str(self.config["bot_token"])
            )

            # Should find all threads from both pages
            assert len(threads) == 5  # type: ignore[misc]
            assert call_count == 2  # Verify pagination happened

    def test_find_existing_thread_by_name_finds_archived(self) -> None:
        """Test that find_existing_thread_by_name finds archived threads."""
        http_client = HTTPClient(self.logger)

        # Mock search to return only an archived thread
        with patch.object(http_client, "search_all_threads", return_value=[self.archived_thread]):
            thread = find_existing_thread_by_name(  # type: ignore[misc]
                str(self.config["channel_id"]), "Session efgh5678", self.config, http_client, self.logger
            )

            assert thread is not None
            assert thread["id"] == self.archived_thread["id"]  # type: ignore[misc]
            assert thread["thread_metadata"]["archived"]  # type: ignore[misc]

    def test_find_existing_thread_exact_match_priority(self) -> None:
        """Test that exact name matches take priority over partial matches."""
        http_client = HTTPClient(self.logger)

        partial_match = {
            "id": "444444444444444444",
            "name": "Session abcd1234-extra",  # Partial match
            "thread_metadata": {"archived": False},
        }

        exact_match = {
            "id": "555555555555555555",
            "name": "Session abcd1234",  # Exact match
            "thread_metadata": {"archived": True},
        }

        # Return partial match first, then exact match
        with patch.object(http_client, "search_all_threads", return_value=[partial_match, exact_match]):
            thread = find_existing_thread_by_name(  # type: ignore[misc]
                str(self.config["channel_id"]), "Session abcd1234", self.config, http_client, self.logger
            )

            # Should return the exact match even though it's archived
            assert thread is not None
            assert thread["id"] == exact_match["id"]  # type: ignore[misc]

    @patch("discord_notifier.SESSION_THREAD_CACHE", {})
    def test_get_or_create_thread_finds_archived(self) -> None:
        """Test that get_or_create_thread finds and unarchives existing archived threads."""
        http_client = HTTPClient(self.logger)

        session_id = "efgh5678"

        # Mock finding an archived thread
        with (
            patch("discord_notifier.find_existing_thread_by_name", return_value=self.archived_thread),
            patch("discord_notifier.ensure_thread_is_usable", return_value=True),
            patch("thread_storage.ThreadStorage") as mock_storage,
        ):
            # Configure mock storage
            mock_storage_instance = MagicMock()
            mock_storage_instance.get_thread.return_value = None  # Not in storage yet
            mock_storage.return_value = mock_storage_instance

            thread_id = get_or_create_thread(session_id, self.config, http_client, self.logger)

            # Should find and return the existing archived thread
            assert thread_id == self.archived_thread["id"]

            # Verify storage was called to save the discovered thread
            mock_storage_instance.store_thread.assert_called_once()

    def test_error_handling_graceful_degradation(self) -> None:
        """Test that errors in archived thread search don't break the overall search."""
        http_client = HTTPClient(self.logger)

        # Mock active threads to work, archived threads to fail
        with (
            patch.object(http_client, "list_active_threads", return_value=[self.active_thread]),
            patch.object(http_client, "list_public_archived_threads", side_effect=DiscordAPIError("API Error")),
            patch.object(http_client, "list_private_archived_threads", side_effect=DiscordAPIError("Permission Error")),
        ):
            # Should still return active threads despite errors
            threads = http_client.search_all_threads(  # type: ignore[misc]
                str(self.config["channel_id"]), "Session", str(self.config["bot_token"])
            )

            assert len(threads) == 1  # type: ignore[misc]
            assert threads[0]["id"] == self.active_thread["id"]  # type: ignore[misc]


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    unittest.main()
