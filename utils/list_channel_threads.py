#!/usr/bin/env python3
"""チャンネル内のスレッド一覧を表示."""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import TypedDict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.astolfo_logger import AstolfoLogger


class ThreadInfo(TypedDict):
    """Discord thread information."""

    id: str
    name: str
    parent_id: str | None


# Discord設定
TOKEN = os.getenv("DISCORD_TOKEN", "")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")

# Initialize logger
logger = AstolfoLogger(__name__)


def list_active_threads() -> None:
    """アクティブなスレッドを一覧表示."""
    logger.debug("Starting thread listing", channel_id=CHANNEL_ID)
    try:
        url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/threads/archived/public?limit=100"
        headers = {"Authorization": f"Bot {TOKEN}"}

        request = urllib.request.Request(url, headers=headers)  # noqa: S310
        logger.debug("Sending request to Discord API", url=url)
        with urllib.request.urlopen(request) as response:  # type: ignore[misc] # noqa: S310
            response_data: bytes = response.read()  # type: ignore[misc]
            text: str = response_data.decode()
            data: dict[str, list[dict[str, str]]] = json.loads(text)
            threads: list[dict[str, str]] = data.get("threads", [])
            logger.info("Successfully retrieved threads", thread_count=len(threads))

            print(f"Found {len(threads)} archived threads in channel {CHANNEL_ID}:")
            for thread in threads:
                print(f"  - {thread['name']} (ID: {thread['id']})")

    except urllib.error.HTTPError as e:
        logger.exception("HTTP error occurred", code=e.code, reason=e.reason)
        print(f"Error: HTTP {e.code} - {e.reason}")
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.exception("Request or JSON parsing error", error=str(e))
        print(f"Error: {e}")


def main() -> None:
    """メイン関数."""
    logger.debug("CLI tool started", channel_id=CHANNEL_ID)
    print(f"Listing threads in channel: {CHANNEL_ID}")
    print("-" * 50)
    list_active_threads()
    logger.debug("CLI tool completed")


if __name__ == "__main__":
    main()
