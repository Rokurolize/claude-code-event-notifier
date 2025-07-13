#!/usr/bin/env python3
"""Timestamp accuracy test suite for Discord notifications.

This test suite specifically validates that all timestamp generation
functions produce correct JST timestamps in real-time scenarios.
"""

import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.formatters.event_formatters import (
    format_notification,
    format_post_tool_use,
    format_pre_tool_use,
    format_stop,
    format_subagent_stop
)
from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import get_user_datetime


class TimestampAccuracyTests(unittest.TestCase):
    """Test suite for timestamp accuracy across all event formatters."""
    
    def setUp(self):
        """Set up test environment."""
        self.logger = AstolfoLogger(__name__)
        
        # Create temporary transcript for tests requiring it
        self.temp_transcript = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        self.temp_transcript.write('{"type":"test","sessionId":"test-001","timestamp":"2025-07-12T13:00:00.000Z"}\n')
        self.temp_transcript.close()
        
        # Test data templates
        self.test_session_id = "test-001"
        self.test_subagent_data = {
            "subagent_id": "test-astolfo",
            "result": "Test completed",
            "session_id": "test-session-001",
            "transcript_path": self.temp_transcript.name,
            "duration_seconds": 30,
            "tools_used": 5
        }
        self.test_tool_data = {
            "tool_name": "TestTool",
            "input": {"test": "data"}
        }
        self.test_stop_data = {
            "session_id": "test-session-001"
        }
        self.test_notification_data = {
            "message": "Test notification",
            "session_id": "test-session-001"
        }
    
    def tearDown(self):
        """Clean up test environment."""
        Path(self.temp_transcript.name).unlink(missing_ok=True)
    
    def extract_timestamp_from_embed(self, embed: dict, field_name: str) -> str:
        """Extract timestamp from embed description or fields.
        
        Args:
            embed: Discord embed dictionary
            field_name: Field name to search for (e.g., "Completed at", "Time")
            
        Returns:
            Extracted timestamp string
        """
        description = embed.get("description", "")
        
        # Search in description
        pattern = rf"\*\*{re.escape(field_name)}:\*\* (.+)"
        match = re.search(pattern, description)
        if match:
            return match.group(1).strip()
        
        # Search in fields
        for field in embed.get("fields", []):
            if field.get("name") == field_name:
                return field.get("value", "").strip()
        
        raise ValueError(f"Timestamp field '{field_name}' not found in embed")
    
    def assert_timestamp_is_recent_jst(self, timestamp_str: str, tolerance_minutes: int = 2):
        """Assert that timestamp is recent and in JST format.
        
        Args:
            timestamp_str: Timestamp string to validate
            tolerance_minutes: Allowed difference from current time
        """
        # Check JST suffix
        self.assertTrue(
            timestamp_str.endswith(" JST"),
            f"Timestamp should end with ' JST': {timestamp_str}"
        )
        
        # Parse timestamp (remove JST suffix)
        time_part = timestamp_str.replace(" JST", "")
        try:
            parsed_time = datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            self.fail(f"Failed to parse timestamp '{time_part}': {e}")
        
        # Check if timestamp is recent
        current_time = get_user_datetime().replace(tzinfo=None)
        time_diff = abs((current_time - parsed_time).total_seconds())
        
        max_diff = tolerance_minutes * 60
        self.assertLessEqual(
            time_diff, 
            max_diff,
            f"Timestamp {timestamp_str} is {time_diff:.0f}s old, max allowed: {max_diff}s"
        )
    
    def test_pre_tool_use_timestamp(self):
        """Test PreToolUse event timestamp accuracy."""
        before_time = get_user_datetime()
        
        embed = format_pre_tool_use(self.test_tool_data, self.test_session_id)
        
        after_time = get_user_datetime()
        
        # Extract timestamp
        timestamp = self.extract_timestamp_from_embed(embed, "Time")
        
        # Validate JST format and recency
        self.assert_timestamp_is_recent_jst(timestamp)
        
        self.logger.info(
            "PreToolUse timestamp test passed",
            context={
                "timestamp": timestamp,
                "before_time": before_time.isoformat(),
                "after_time": after_time.isoformat()
            }
        )
    
    def test_post_tool_use_timestamp(self):
        """Test PostToolUse event timestamp accuracy."""
        before_time = get_user_datetime()
        
        # Mock tool response
        tool_response = {
            "tool_name": "TestTool",
            "success": True,
            "output": "Test completed successfully"
        }
        
        embed = format_post_tool_use(tool_response, self.test_session_id)
        
        after_time = get_user_datetime()
        
        # Extract timestamp
        timestamp = self.extract_timestamp_from_embed(embed, "Completed at")
        
        # Validate JST format and recency
        self.assert_timestamp_is_recent_jst(timestamp)
        
        self.logger.info(
            "PostToolUse timestamp test passed",
            context={
                "timestamp": timestamp,
                "before_time": before_time.isoformat(),
                "after_time": after_time.isoformat()
            }
        )
    
    def test_stop_event_timestamp(self):
        """Test Stop event timestamp accuracy."""
        before_time = get_user_datetime()
        
        embed = format_stop(self.test_stop_data, self.test_session_id)
        
        after_time = get_user_datetime()
        
        # Extract timestamp
        timestamp = self.extract_timestamp_from_embed(embed, "Ended at")
        
        # Validate JST format and recency
        self.assert_timestamp_is_recent_jst(timestamp)
        
        self.logger.info(
            "Stop event timestamp test passed",
            context={
                "timestamp": timestamp,
                "before_time": before_time.isoformat(),
                "after_time": after_time.isoformat()
            }
        )
    
    def test_notification_timestamp(self):
        """Test Notification event timestamp accuracy."""
        before_time = get_user_datetime()
        
        embed = format_notification(self.test_notification_data, self.test_session_id)
        
        after_time = get_user_datetime()
        
        # Extract timestamp
        timestamp = self.extract_timestamp_from_embed(embed, "Time")
        
        # Validate JST format and recency
        self.assert_timestamp_is_recent_jst(timestamp)
        
        self.logger.info(
            "Notification timestamp test passed",
            context={
                "timestamp": timestamp,
                "before_time": before_time.isoformat(),
                "after_time": after_time.isoformat()
            }
        )
    
    def test_subagent_stop_timestamp(self):
        """Test SubagentStop event timestamp accuracy."""
        before_time = get_user_datetime()
        
        embed = format_subagent_stop(self.test_subagent_data, self.test_session_id)
        
        after_time = get_user_datetime()
        
        # Extract timestamp
        timestamp = self.extract_timestamp_from_embed(embed, "Completed at")
        
        # Validate JST format and recency
        self.assert_timestamp_is_recent_jst(timestamp)
        
        self.logger.info(
            "SubagentStop timestamp test passed",
            context={
                "timestamp": timestamp,
                "before_time": before_time.isoformat(),
                "after_time": after_time.isoformat()
            }
        )
    
    def test_all_events_have_consistent_timezone(self):
        """Test that all event types use consistent JST timezone."""
        events_and_timestamps = []
        
        # Generate all event types
        test_cases = [
            ("PreToolUse", format_pre_tool_use(self.test_tool_data, self.test_session_id), "Time"),
            ("PostToolUse", format_post_tool_use({"tool_name": "Test", "success": True}, self.test_session_id), "Completed at"),
            ("Stop", format_stop(self.test_stop_data, self.test_session_id), "Ended at"),
            ("Notification", format_notification(self.test_notification_data, self.test_session_id), "Time"),
            ("SubagentStop", format_subagent_stop(self.test_subagent_data, self.test_session_id), "Completed at")
        ]
        
        for event_type, embed, field_name in test_cases:
            timestamp = self.extract_timestamp_from_embed(embed, field_name)
            events_and_timestamps.append((event_type, timestamp))
            
            # Each timestamp should be JST
            self.assertTrue(
                timestamp.endswith(" JST"),
                f"{event_type} timestamp should end with ' JST': {timestamp}"
            )
        
        # All timestamps should be within a few seconds of each other
        # (since they were generated in quick succession)
        parsed_times = []
        for event_type, timestamp in events_and_timestamps:
            time_part = timestamp.replace(" JST", "")
            parsed_time = datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S")
            parsed_times.append((event_type, parsed_time))
        
        # Check that all times are within 30 seconds of each other
        min_time = min(time for _, time in parsed_times)
        max_time = max(time for _, time in parsed_times)
        time_spread = (max_time - min_time).total_seconds()
        
        self.assertLessEqual(
            time_spread, 
            30,
            f"Event timestamps spread too far apart: {time_spread:.2f}s. "
            f"Events: {[(event, time.strftime('%H:%M:%S')) for event, time in parsed_times]}"
        )
        
        self.logger.info(
            "All events have consistent JST timezone",
            context={
                "events_tested": len(test_cases),
                "time_spread_seconds": time_spread,
                "timestamps": {event: timestamp for event, timestamp in events_and_timestamps}
            }
        )
    
    def test_timezone_persistence_across_calls(self):
        """Test that timezone setting persists across multiple formatter calls."""
        timestamps = []
        
        # Make multiple calls in quick succession
        for i in range(5):
            embed = format_notification(
                {"message": f"Test {i}", "session_id": "test"},
                f"test-{i}"
            )
            timestamp = self.extract_timestamp_from_embed(embed, "Time")
            timestamps.append(timestamp)
        
        # All should be JST
        for i, timestamp in enumerate(timestamps):
            self.assertTrue(
                timestamp.endswith(" JST"),
                f"Call {i} timestamp should be JST: {timestamp}"
            )
        
        self.logger.info(
            "Timezone persistence test passed",
            context={
                "calls_made": len(timestamps),
                "all_jst": all(ts.endswith(" JST") for ts in timestamps),
                "sample_timestamps": timestamps[:3]
            }
        )


class UTCLeakDetectionTests(unittest.TestCase):
    """Test suite for detecting UTC timestamp leaks in codebase."""
    
    def setUp(self):
        """Set up test environment."""
        self.logger = AstolfoLogger(__name__)
        self.src_path = Path(__file__).parent.parent.parent / "src"
    
    def test_no_utc_in_formatters(self):
        """Test that formatter files don't contain UTC timestamp generation."""
        formatter_files = list(self.src_path.glob("formatters/*.py"))
        
        utc_patterns = [
            r"datetime\.now\(UTC\)",
            r"datetime\.utcnow\(\)",
            r"\.strftime.*UTC",
            r"timezone\.utc"
        ]
        
        violations = []
        
        for file_path in formatter_files:
            content = file_path.read_text()
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in utc_patterns:
                    if re.search(pattern, line):
                        violations.append(f"{file_path.name}:{line_num}: {line.strip()}")
        
        self.assertEqual(
            len(violations), 
            0,
            f"Found UTC timestamp patterns in formatters:\n" + "\n".join(violations)
        )
        
        self.logger.info(
            "No UTC patterns found in formatters",
            context={
                "files_checked": len(formatter_files),
                "patterns_checked": len(utc_patterns)
            }
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)