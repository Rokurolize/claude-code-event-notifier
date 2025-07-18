#!/usr/bin/env python3
"""HTTP client for Discord API interactions.

This module provides a robust HTTP client for communicating with Discord's API,
supporting bot authentication methods.
"""

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import TypedDict, cast

from .constants import DEFAULT_TIMEOUT, DISCORD_API_BASE, USER_AGENT
from .exceptions import DiscordAPIError


# Type definitions for Discord API structures
class BaseField(TypedDict):
    """Base field structure for common properties."""


class TimestampedField(BaseField):
    """Fields that include timestamps."""

    timestamp: str | None


# Discord API response types
class DiscordChannel(TypedDict, total=False):
    """Discord channel response structure."""

    id: str
    type: int
    name: str
    parent_id: str | None
    position: int
    topic: str | None
    nsfw: bool
    last_message_id: str | None


class DiscordThread(TypedDict, total=False):
    """Discord thread response structure."""

    id: str
    type: int
    name: str
    parent_id: str
    owner_id: str
    message_count: int
    member_count: int
    archived: bool
    auto_archive_duration: int
    archive_timestamp: str
    locked: bool
    invitable: bool
    create_timestamp: str | None


class DiscordFooter(TypedDict):
    """Discord footer structure."""

    text: str


class DiscordFieldBase(TypedDict):
    """Base Discord field structure."""

    name: str
    value: str


class DiscordField(DiscordFieldBase):
    """Discord field with optional inline support."""

    inline: bool | None


class DiscordEmbedBase(TypedDict):
    """Base Discord embed structure."""

    title: str | None
    description: str | None
    color: int | None


class DiscordEmbed(DiscordEmbedBase, TimestampedField):
    """Complete Discord embed structure."""

    footer: DiscordFooter | None
    fields: list[DiscordField] | None


class DiscordMessageBase(TypedDict):
    """Base Discord message structure."""

    embeds: list[DiscordEmbed] | None


class DiscordMessage(DiscordMessageBase):
    """Discord message with optional content."""

    content: str | None


class DiscordThreadMessage(DiscordMessageBase):
    """Discord message with thread support."""

    thread_name: str | None


class DiscordMessageResponse(TypedDict):
    """Discord message response with ID."""

    id: str
    timestamp: str
    author: dict[str, str]
    content: str | None
    embeds: list[DiscordEmbed] | None


class HTTPClient:
    """HTTP client for Discord API calls.

    This client provides methods for various Discord API operations including:
    - Sending messages via bot API
    - Managing threads (create, archive, unarchive)
    - Listing and searching threads

    All methods include proper error handling and retry logic.
    """

    def __init__(self, logger: logging.Logger, timeout: int = DEFAULT_TIMEOUT):
        """Initialize HTTP client.

        Args:
            logger: Logger instance for debugging
            timeout: Request timeout in seconds
        """
        self.logger = logger
        self.timeout = timeout
        self.headers_base = {"User-Agent": USER_AGENT}

    def post_bot_api(self, url: str, data: DiscordMessage, token: str) -> bool:
        """Send message via Discord bot API.

        Args:
            url: Discord API endpoint URL
            data: Message data to send
            token: Bot authentication token

        Returns:
            True if successful, False otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
            "Authorization": f"Bot {token}",
        }

        return self._make_request(url, data, headers, "Bot API", lambda s: 200 <= s < 300)

    def post_bot_api_with_id(self, url: str, data: DiscordMessage, token: str) -> DiscordMessageResponse | None:
        """Send message via Discord bot API and return message ID.

        Args:
            url: Discord API endpoint URL
            data: Message data to send
            token: Bot authentication token

        Returns:
            Message response with ID if successful, None otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
            "Authorization": f"Bot {token}",
        }

        return self._make_request_with_response(url, data, headers, "Bot API", 200)

    def _make_request(
        self,
        url: str,
        data: DiscordMessage | DiscordThreadMessage | dict[str, str | int | bool],
        headers: dict[str, str],
        api_name: str,
        success_check: int | Callable[[int], bool],
    ) -> bool:
        """Make HTTP request with error handling.

        Args:
            url: Request URL
            data: Data to send
            headers: HTTP headers
            api_name: Name for logging
            success_check: Status code or callable to check success

        Returns:
            True if successful, False otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers=headers)  # noqa: S310

            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("%s response: %s", api_name, status)

                if callable(success_check):
                    return bool(success_check(status))
                return bool(status == success_check)

        except urllib.error.HTTPError as e:
            self.logger.exception("%s HTTP error %s: %s", api_name, e.code, e.reason)
            raise DiscordAPIError(f"{api_name} failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("%s URL error: %s", api_name, e.reason)
            raise DiscordAPIError(f"{api_name} connection failed: {e.reason}") from e

    def _make_request_with_response(
        self,
        url: str,
        data: DiscordMessage | DiscordThreadMessage | dict[str, str | int | bool],
        headers: dict[str, str],
        api_name: str,
        success_status: int,
    ) -> DiscordMessageResponse | None:
        """Make HTTP request and return response data.

        Args:
            url: Request URL
            data: Data to send
            headers: HTTP headers
            api_name: Name for logging
            success_status: Expected success status code

        Returns:
            Discord message response if successful, None otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers=headers)  # noqa: S310

            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("%s response: %s", api_name, status)

                if status == success_status:
                    # Read response data
                    response_data = response.read().decode("utf-8")
                    if response_data:
                        message_data = json.loads(response_data)
                        return cast(DiscordMessageResponse, {
                            "id": message_data.get("id", ""),
                            "timestamp": message_data.get("timestamp", ""),
                            "author": message_data.get("author", {}),
                            "content": message_data.get("content"),
                            "embeds": message_data.get("embeds"),
                        })
                    else:
                        self.logger.warning("%s success but no response data", api_name)
                        return None
                else:
                    self.logger.warning("%s unexpected status: %s", api_name, status)
                    return None

        except urllib.error.HTTPError as e:
            self.logger.exception("%s HTTP error %s: %s", api_name, e.code, e.reason)
            raise DiscordAPIError(f"{api_name} failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("%s URL error: %s", api_name, e.reason)
            raise DiscordAPIError(f"{api_name} connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during HTTP operations
            self.logger.exception("%s unexpected error: %s", api_name, type(e).__name__)
            raise DiscordAPIError(f"{api_name} unexpected error: {e}") from e

    def create_text_thread(self, channel_id: str, name: str, token: str) -> str | None:
        """Create new text channel thread via Discord bot API.

        Args:
            channel_id: Parent channel ID
            name: Thread name
            token: Bot authentication token

        Returns:
            Thread ID if successful, None otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/threads"
        data = {"name": name, "type": 11}  # 11 = public thread
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
            "Authorization": f"Bot {token}",
        }

        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers=headers)  # noqa: S310

            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("Text Thread Creation response: %s", status)

                if 200 <= status < 300:
                    # Parse response to get thread_id
                    response_data = json.loads(response.read().decode("utf-8"))
                    return cast("str | None", response_data.get("id"))  # thread_id
                return None

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
                self.logger.exception("Text Thread Creation HTTP error %s: %s, body: %s", e.code, e.reason, error_body)
            except (OSError, UnicodeDecodeError):
                self.logger.exception("Text Thread Creation HTTP error %s: %s", e.code, e.reason)
            raise DiscordAPIError(f"Text thread creation failed: {e.code} {e.reason}, details: {error_body}") from e
        except urllib.error.URLError as e:
            self.logger.exception("Text Thread Creation URL error: %s", e.reason)
            raise DiscordAPIError(f"Text thread creation connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during text thread creation
            self.logger.exception("Text Thread Creation unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"Text thread creation unexpected error: {e}") from e

    def get_channel_info(self, channel_id: str, token: str) -> DiscordChannel | None:
        """Get channel information via Discord bot API.

        Args:
            channel_id: Discord channel ID (snowflake)
            token: Discord bot token

        Returns:
            Channel object from Discord API if found, None otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        url = f"{DISCORD_API_BASE}/channels/{channel_id}"
        headers = {
            **self.headers_base,
            "Authorization": f"Bot {token}",
        }

        try:
            req = urllib.request.Request(url, headers=headers)  # noqa: S310
            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("Get Channel Info response: %s", status)

                if 200 <= status < 300:
                    response_data = json.loads(response.read().decode("utf-8"))
                    return cast("DiscordChannel", response_data)
                return None

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Channel not found
                self.logger.debug("Channel not found: %s", channel_id)
                return None
            self.logger.exception("Get Channel Info HTTP error %s: %s", e.code, e.reason)
            raise DiscordAPIError(f"Get channel info failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("Get Channel Info URL error: %s", e.reason)
            raise DiscordAPIError(f"Get channel info connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during channel info retrieval
            self.logger.exception("Get Channel Info unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"Get channel info unexpected error: {e}") from e

    def list_active_threads(self, channel_id: str, token: str) -> list[DiscordThread]:
        """List active threads in a channel via Discord bot API.

        Args:
            channel_id: Discord channel ID (snowflake)
            token: Discord bot token

        Returns:
            List of thread objects from Discord API

        Raises:
            DiscordAPIError: On API communication errors
        """
        # Step 1: Get guild_id from channel
        channel_info = self.get_channel_info(channel_id, token)
        if not channel_info:
            self.logger.error("Could not get channel info for %s", channel_id)
            return []

        guild_id = channel_info.get("guild_id")
        if not guild_id:
            self.logger.error("No guild_id found for channel %s", channel_id)
            return []

        # Step 2: Use correct endpoint with guild_id
        url = f"{DISCORD_API_BASE}/guilds/{guild_id}/threads/active"
        headers = {
            **self.headers_base,
            "Authorization": f"Bot {token}",
        }

        try:
            req = urllib.request.Request(url, headers=headers)  # noqa: S310

            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("List Active Threads response: %s", status)

                if 200 <= status < 300:
                    response_data = json.loads(response.read().decode("utf-8"))
                    # Filter threads to only include those from our channel
                    all_threads = response_data.get("threads", [])
                    channel_threads = [t for t in all_threads if t.get("parent_id") == channel_id]
                    return cast("list[DiscordThread]", channel_threads)
                return []

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
                self.logger.exception("List Active Threads HTTP error %s: %s, body: %s", e.code, e.reason, error_body)
            except (OSError, UnicodeDecodeError):
                self.logger.exception("List Active Threads HTTP error %s: %s", e.code, e.reason)
            if e.code == 404:
                # Guild not found or no access - return empty list
                return []
            raise DiscordAPIError(f"List active threads failed: {e.code} {e.reason}, details: {error_body}") from e
        except urllib.error.URLError as e:
            self.logger.exception("List Active Threads URL error: %s", e.reason)
            raise DiscordAPIError(f"List active threads connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during active thread listing
            self.logger.exception("List Active Threads unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"List active threads unexpected error: {e}") from e

    def get_thread_details(self, thread_id: str, token: str) -> DiscordThread | None:
        """Get details of a specific thread via Discord bot API.

        Args:
            thread_id: Discord thread ID (snowflake)
            token: Discord bot token

        Returns:
            Thread object from Discord API if found, None otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        url = f"{DISCORD_API_BASE}/channels/{thread_id}"
        headers = {
            **self.headers_base,
            "Authorization": f"Bot {token}",
        }

        try:
            req = urllib.request.Request(url, headers=headers)  # noqa: S310

            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("Get Thread Details response: %s", status)

                if 200 <= status < 300:
                    response_data = json.loads(response.read().decode("utf-8"))
                    return cast("DiscordThread", response_data)
                return None

        except urllib.error.HTTPError as e:
            self.logger.debug("Get Thread Details HTTP error %s: %s", e.code, e.reason)
            if e.code == 404:
                # Thread not found - return None
                return None
            raise DiscordAPIError(f"Get thread details failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("Get Thread Details URL error: %s", e.reason)
            raise DiscordAPIError(f"Get thread details connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during thread detail retrieval
            self.logger.exception("Get Thread Details unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"Get thread details unexpected error: {e}") from e

    def unarchive_thread(self, thread_id: str, token: str) -> bool:
        """Unarchive a thread via Discord bot API.

        Args:
            thread_id: Discord thread ID (snowflake)
            token: Discord bot token

        Returns:
            True if successful, False otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        url = f"{DISCORD_API_BASE}/channels/{thread_id}"
        data = {"archived": False}
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
            "Authorization": f"Bot {token}",
        }

        try:
            json_data = json.dumps(data).encode("utf-8")

            # Create a custom request class to override the HTTP method
            class PatchRequest(urllib.request.Request):
                def get_method(self) -> str:
                    return "PATCH"

            req = PatchRequest(url, data=json_data, headers=headers)

            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("Unarchive Thread response: %s", status)

                return bool(200 <= status < 300)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Thread not found
                self.logger.debug("Thread not found for unarchive: %s", thread_id)
                return False
            self.logger.exception("Unarchive Thread HTTP error %s: %s", e.code, e.reason)
            raise DiscordAPIError(f"Unarchive thread failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("Unarchive Thread URL error: %s", e.reason)
            raise DiscordAPIError(f"Unarchive thread connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during thread unarchiving
            self.logger.exception("Unarchive Thread unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"Unarchive thread unexpected error: {e}") from e

    def archive_thread(self, thread_id: str, token: str, locked: bool = False) -> bool:
        """Archive/close a thread via Discord bot API.

        Args:
            thread_id: Discord thread ID (snowflake)
            token: Discord bot token
            locked: Whether to lock the thread (prevents non-moderators from unarchiving)

        Returns:
            True if successful, False otherwise

        Raises:
            DiscordAPIError: On API communication errors
        """
        url = f"{DISCORD_API_BASE}/channels/{thread_id}"
        data = {"archived": True}
        if locked:
            data["locked"] = True
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
            "Authorization": f"Bot {token}",
        }

        try:
            json_data = json.dumps(data).encode("utf-8")

            # Create a custom request class to override the HTTP method
            class PatchRequest(urllib.request.Request):
                def get_method(self) -> str:
                    return "PATCH"

            req = PatchRequest(url, data=json_data, headers=headers)

            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("Archive Thread response: %s", status)

                return bool(200 <= status < 300)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Thread not found
                self.logger.debug("Thread not found for archive: %s", thread_id)
                return False
            self.logger.exception("Archive Thread HTTP error %s: %s", e.code, e.reason)
            raise DiscordAPIError(f"Archive thread failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("Archive Thread URL error: %s", e.reason)
            raise DiscordAPIError(f"Archive thread connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during thread archiving
            self.logger.exception("Archive Thread unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"Archive thread unexpected error: {e}") from e

    def list_public_archived_threads(
        self, channel_id: str, token: str, before: str | None = None, limit: int = 100
    ) -> tuple[list[DiscordThread], bool]:
        """List public archived threads in a channel.

        Args:
            channel_id: Discord channel ID
            token: Discord bot token
            before: Get threads before this timestamp (snowflake)
            limit: Maximum number of threads to return (max 100)

        Returns:
            Tuple of (list of thread objects, has_more flag)

        Raises:
            DiscordAPIError: On API communication errors
        """
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/threads/archived/public"
        params = []
        if before:
            params.append(f"before={before}")
        params.append(f"limit={min(limit, 100)}")
        if params:
            url += "?" + "&".join(params)

        headers = {
            **self.headers_base,
            "Authorization": f"Bot {token}",
        }

        try:
            req = urllib.request.Request(url, headers=headers)  # noqa: S310
            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("List Public Archived Threads response: %s", status)

                if 200 <= status < 300:
                    response_data = json.loads(response.read().decode("utf-8"))
                    threads = response_data.get("threads", [])
                    has_more = response_data.get("has_more", False)
                    return threads, has_more
                return [], False

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.logger.debug("Channel not found for listing archived threads: %s", channel_id)
                return [], False
            self.logger.exception("List Public Archived Threads HTTP error %s: %s", e.code, e.reason)
            raise DiscordAPIError(f"List public archived threads failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("List Public Archived Threads URL error: %s", e.reason)
            raise DiscordAPIError(f"List public archived threads connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during public archived thread listing
            self.logger.exception("List Public Archived Threads unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"List public archived threads unexpected error: {e}") from e

    def list_private_archived_threads(
        self, channel_id: str, token: str, before: str | None = None, limit: int = 100
    ) -> tuple[list[DiscordThread], bool]:
        """List private archived threads in a channel (requires MANAGE_THREADS permission).

        Args:
            channel_id: Discord channel ID
            token: Discord bot token
            before: Get threads before this timestamp (snowflake)
            limit: Maximum number of threads to return (max 100)

        Returns:
            Tuple of (list of thread objects, has_more flag)

        Raises:
            DiscordAPIError: On API communication errors
        """
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/threads/archived/private"
        params = []
        if before:
            params.append(f"before={before}")
        params.append(f"limit={min(limit, 100)}")
        if params:
            url += "?" + "&".join(params)

        headers = {
            **self.headers_base,
            "Authorization": f"Bot {token}",
        }

        try:
            req = urllib.request.Request(url, headers=headers)  # noqa: S310
            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                status = response.status
                self.logger.debug("List Private Archived Threads response: %s", status)

                if 200 <= status < 300:
                    response_data = json.loads(response.read().decode("utf-8"))
                    threads = response_data.get("threads", [])
                    has_more = response_data.get("has_more", False)
                    return threads, has_more
                return [], False

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.logger.debug("Channel not found for listing private archived threads: %s", channel_id)
                return [], False
            self.logger.exception("List Private Archived Threads HTTP error %s: %s", e.code, e.reason)
            raise DiscordAPIError(f"List private archived threads failed: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            self.logger.exception("List Private Archived Threads URL error: %s", e.reason)
            raise DiscordAPIError(f"List private archived threads connection failed: {e.reason}") from e
        except Exception as e:
            # Catch any other unexpected errors during private archived thread listing
            self.logger.exception("List Private Archived Threads unexpected error: %s", type(e).__name__)
            raise DiscordAPIError(f"List private archived threads unexpected error: {e}") from e

    def search_threads_by_name(self, channel_id: str, thread_name: str, token: str) -> list[DiscordThread]:
        """Search for threads by name in a channel (active and archived).

        Args:
            channel_id: Discord channel ID
            thread_name: Thread name to search for
            token: Discord bot token

        Returns:
            List of thread objects that match the name pattern

        Raises:
            DiscordAPIError: On API communication errors
        """
        matching_threads: list[DiscordThread] = []
        search_name = thread_name.lower()

        # Search active threads
        try:
            active_threads = self.list_active_threads(channel_id, token)
            matching_threads.extend(
                thread for thread in active_threads if search_name in thread.get("name", "").lower()
            )
        except DiscordAPIError:
            self.logger.debug("Could not search active threads for %s", channel_id)

        # Search public archived threads
        try:
            archived_threads, _ = self.list_public_archived_threads(channel_id, token)
            matching_threads.extend(
                thread for thread in archived_threads if search_name in thread.get("name", "").lower()
            )
        except DiscordAPIError:
            self.logger.debug("Could not search public archived threads for %s", channel_id)

        # Search private archived threads
        try:
            private_archived_threads, _ = self.list_private_archived_threads(channel_id, token)
            matching_threads.extend(
                thread for thread in private_archived_threads if search_name in thread.get("name", "").lower()
            )
        except DiscordAPIError:
            self.logger.debug("Could not search private archived threads for %s", channel_id)

        return matching_threads
