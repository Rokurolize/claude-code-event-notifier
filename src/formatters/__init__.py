#!/usr/bin/env python3
"""Discord Notifier formatters package.

This package provides formatting functions for Discord notifications.
"""

from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)

try:
    from .base import (
        add_field,
        format_file_path,
        format_json_field,
        get_truncation_suffix,
        truncate_string,
    )
    from .event_formatters import (
        format_default,
        format_default_impl,
        format_event,
        format_notification,
        format_post_tool_use,
        format_pre_tool_use,
        format_stop,
        format_subagent_stop,
    )
    from .tool_formatters import (
        format_bash_post_use,
        format_bash_pre_use,
        format_file_operation_pre_use,
        format_read_operation_post_use,
        format_search_tool_pre_use,
        format_task_post_use,
        format_task_pre_use,
        format_unknown_tool_post_use,
        format_unknown_tool_pre_use,
        format_web_fetch_post_use,
        format_web_fetch_pre_use,
        format_write_operation_post_use,
    )

    logger.debug("Formatters module imports successful")
except ImportError as e:
    logger.exception("Failed to import formatter modules", {"error": str(e)})
    raise

__all__ = [
    "add_field",
    "format_bash_post_use",
    "format_bash_pre_use",
    "format_default",
    "format_default_impl",
    "format_event",
    "format_file_operation_pre_use",
    "format_file_path",
    "format_json_field",
    "format_notification",
    "format_post_tool_use",
    "format_pre_tool_use",
    "format_read_operation_post_use",
    "format_search_tool_pre_use",
    "format_stop",
    "format_subagent_stop",
    "format_task_post_use",
    "format_task_pre_use",
    "format_unknown_tool_post_use",
    "format_unknown_tool_pre_use",
    "format_web_fetch_post_use",
    "format_web_fetch_pre_use",
    "format_write_operation_post_use",
    "get_truncation_suffix",
    "truncate_string",
]
