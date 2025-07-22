#!/usr/bin/env python3
"""Debug data logger for Discord Event Notifier.

Saves raw input and formatted output for debugging purposes.
Only active when DISCORD_DEBUG is enabled.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def save_debug_data(
    raw_input: str, formatted_output: dict[str, Any] | None, event_type: str, tool_name: str | None = None
) -> None:
    """Save raw input and formatted output data for debugging.

    Args:
        raw_input: Raw JSON string from stdin
        formatted_output: Formatted Discord message dict
        event_type: Type of event being processed
        tool_name: Optional tool name for PreToolUse/PostToolUse events
    """
    try:
        # Create debug directory
        debug_dir = Path.home() / ".claude" / "hooks" / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")[:-3]  # microseconds to milliseconds

        # Generate filename with optional tool name
        if tool_name and event_type in ["PreToolUse", "PostToolUse"]:
            # Include tool name for tool-related events
            filename_base = f"{timestamp}_{event_type}_{tool_name}"
        else:
            # Use original format for other events
            filename_base = f"{timestamp}_{event_type}"

        # Save raw input
        raw_file = debug_dir / f"{filename_base}_raw_input.json"
        raw_data = json.loads(raw_input) if isinstance(raw_input, str) else raw_input
        masked_raw = mask_sensitive_data(raw_data)
        raw_file.write_text(json.dumps(masked_raw, indent=2))

        # Save formatted output if present
        if formatted_output:
            output_file = debug_dir / f"{filename_base}_formatted_output.json"
            masked_output = mask_sensitive_data(formatted_output)
            output_file.write_text(json.dumps(masked_output, indent=2))

        # Cleanup old files on every save (lightweight operation)
        cleanup_old_files(debug_dir)

    except Exception:
        # Never let debug logging break the main flow
        pass


def mask_sensitive_data(data: Any) -> Any:
    """Recursively mask sensitive information in data structures.

    Args:
        data: Data to mask (dict, list, or primitive)

    Returns:
        Data with sensitive information masked
    """
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            # Keys that might contain sensitive data
            if any(sensitive in key.lower() for sensitive in ["token", "webhook", "password", "secret", "key", "auth"]):
                # Keep the structure but mask the value
                if isinstance(value, str) and len(value) > 8:
                    masked[key] = value[:4] + "***MASKED***" + value[-4:]
                else:
                    masked[key] = "***MASKED***"
            else:
                masked[key] = mask_sensitive_data(value)
        return masked
    if isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    if isinstance(data, str):
        # Mask Discord tokens in strings (they have a specific pattern)
        # Discord bot tokens: <user_id>.<timestamp>.<hmac>
        token_pattern = r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{27,}\b"
        if re.search(token_pattern, data):
            return re.sub(token_pattern, "***DISCORD_TOKEN_MASKED***", data)

        # Mask webhook URLs
        webhook_pattern = r"https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+"
        if re.search(webhook_pattern, data):
            return re.sub(webhook_pattern, "***WEBHOOK_URL_MASKED***", data)

        return data
    return data


def cleanup_old_files(debug_dir: Path, days: int = 7) -> None:
    """Remove debug files older than specified days.

    Args:
        debug_dir: Directory containing debug files
        days: Number of days to keep files (default: 7)
    """
    try:
        cutoff_time = datetime.now(UTC) - timedelta(days=days)

        for file in debug_dir.glob("*_raw_input.json"):
            # Extract timestamp from filename
            try:
                # Filename can be either:
                # - {timestamp}_{event_type}_raw_input
                # - {timestamp}_{event_type}_{tool_name}_raw_input
                parts = file.stem.split("_")
                if len(parts) >= 2:
                    timestamp_str = parts[0] + parts[1]
                    file_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S").replace(tzinfo=UTC)

                if file_time < cutoff_time:
                    file.unlink()
                    # Also remove corresponding output file if it exists
                    output_file = file.parent / file.name.replace("_raw_input.json", "_formatted_output.json")
                    if output_file.exists():
                        output_file.unlink()
            except (ValueError, IndexError):
                # Skip files with unexpected naming
                continue

    except Exception:
        # Never let cleanup break the main flow
        pass
