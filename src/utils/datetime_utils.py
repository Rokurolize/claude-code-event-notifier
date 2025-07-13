#!/usr/bin/env python3
"""DateTime utilities for Discord Notifier with timezone support.

This module provides timezone-aware datetime functions that separate:
- User-facing displays (JST by default, configurable)
- System internal logs (UTC for consistency)
"""

import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)


def get_user_timezone() -> str:
    """Get user-configured timezone from environment variable.
    
    Returns:
        Timezone string (default: "Asia/Tokyo" for JST)
    """
    timezone = os.getenv("DISCORD_TIMEZONE", "Asia/Tokyo")
    logger.debug(
        "User timezone configured",
        context={"timezone": timezone, "source": "environment"}
    )
    return timezone


def get_user_datetime() -> datetime:
    """Get current datetime in user-configured timezone.
    
    Returns:
        Timezone-aware datetime for user display
    """
    user_tz = get_user_timezone()
    try:
        tz = ZoneInfo(user_tz)
        user_time = datetime.now(tz)
        logger.debug(
            "User datetime generated",
            context={
                "timezone": user_tz,
                "timestamp": user_time.isoformat(),
                "utc_offset": user_time.strftime("%z")
            }
        )
        return user_time
    except Exception as e:
        logger.warning(
            "Failed to get user timezone, falling back to JST",
            context={"requested_timezone": user_tz},
            exception=e
        )
        # Fallback to JST
        return datetime.now(ZoneInfo("Asia/Tokyo"))


def get_system_datetime() -> datetime:
    """Get current datetime in UTC for system internal use.
    
    Returns:
        UTC datetime for system consistency
    """
    return datetime.now(UTC)


def format_user_datetime(dt: datetime | None = None) -> str:
    """Format datetime for user display in user timezone.
    
    Args:
        dt: DateTime to format (default: current user time)
        
    Returns:
        ISO format string in user timezone
    """
    if dt is None:
        dt = get_user_datetime()
    
    # Convert to user timezone if necessary
    user_tz = get_user_timezone()
    if dt.tzinfo is None or dt.tzinfo != ZoneInfo(user_tz):
        try:
            dt = dt.astimezone(ZoneInfo(user_tz))
        except Exception as e:
            logger.warning(
                "Failed to convert to user timezone",
                context={"original_tz": str(dt.tzinfo), "target_tz": user_tz},
                exception=e
            )
    
    formatted = dt.isoformat()
    logger.debug(
        "User datetime formatted",
        context={
            "formatted": formatted,
            "timezone": user_tz,
            "original_dt": str(dt)
        }
    )
    return formatted


def format_system_datetime(dt: datetime | None = None) -> str:
    """Format datetime for system internal use in UTC.
    
    Args:
        dt: DateTime to format (default: current UTC time)
        
    Returns:
        ISO format string in UTC
    """
    if dt is None:
        dt = get_system_datetime()
    
    # Convert to UTC if necessary
    if dt.tzinfo != UTC:
        dt = dt.astimezone(UTC)
    
    return dt.isoformat()


def format_user_display_time(dt: datetime | None = None) -> str:
    """Format datetime for human-readable display.
    
    Args:
        dt: DateTime to format (default: current user time)
        
    Returns:
        Human-readable time string (e.g., "2025-07-12 20:30:45 JST")
    """
    if dt is None:
        dt = get_user_datetime()
    
    user_tz = get_user_timezone()
    try:
        if dt.tzinfo != ZoneInfo(user_tz):
            dt = dt.astimezone(ZoneInfo(user_tz))
        
        # Format: YYYY-MM-DD HH:MM:SS TZ
        display_time = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        
        logger.debug(
            "User display time formatted",
            context={
                "display_time": display_time,
                "timezone": user_tz
            }
        )
        return display_time
    except Exception as e:
        logger.warning(
            "Failed to format display time",
            context={"datetime": str(dt), "timezone": user_tz},
            exception=e
        )
        # Fallback to ISO format
        return dt.isoformat()


# Convenience functions for specific use cases
def get_discord_embed_timestamp() -> str:
    """Get timestamp for Discord embed (user timezone).
    
    Returns:
        ISO format timestamp for Discord embed
    """
    return format_user_datetime()


def get_log_timestamp() -> str:
    """Get timestamp for internal logging (UTC).
    
    Returns:
        ISO format timestamp for internal logs
    """
    return format_system_datetime()


def get_completed_at_display() -> str:
    """Get human-readable completion time for Discord display.
    
    Returns:
        Human-readable completion time string
    """
    return format_user_display_time()