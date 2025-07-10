#!/usr/bin/env python3
"""Unit tests for transcript reader functionality."""

import json
import tempfile
import unittest
from pathlib import Path

from src.utils.transcript_reader import (
    get_full_task_prompt,
    get_subagent_messages,
    read_transcript_lines,
)


class TestTranscriptReader(unittest.TestCase):
    """Test cases for transcript reader functions."""
    
    def setUp(self) -> None:
        """Set up test data."""
        self.session_id = "test-session-123"
        
        # Create sample transcript data
        self.transcript_data = [
            {
                "sessionId": self.session_id,
                "type": "user",
                "message": {"role": "user", "content": "Test user message"},
                "isSidechain": False,
                "timestamp": "2025-01-10T10:00:00Z"
            },
            {
                "sessionId": self.session_id,
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {
                                "description": "Test task",
                                "prompt": "This is a very long prompt that should not be truncated. " * 50
                            }
                        }
                    ]
                },
                "isSidechain": False,
                "timestamp": "2025-01-10T10:01:00Z"
            },
            {
                "sessionId": self.session_id,
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Subagent message 1"}]
                },
                "isSidechain": True,
                "timestamp": "2025-01-10T10:02:00Z"
            },
            {
                "sessionId": self.session_id,
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Subagent message 2"}]
                },
                "isSidechain": True,
                "timestamp": "2025-01-10T10:03:00Z"
            }
        ]
        
    def test_read_transcript_lines(self) -> None:
        """Test reading lines from transcript file."""
        # Create temporary transcript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for data in self.transcript_data:
                f.write(json.dumps(data) + '\n')
            temp_path = f.name
            
        try:
            # Test reading lines
            lines = read_transcript_lines(temp_path, max_lines=10)
            self.assertEqual(len(lines), len(self.transcript_data))
            
            # Verify first line
            self.assertEqual(lines[0]["sessionId"], self.session_id)
            self.assertEqual(lines[0]["type"], "user")
            
        finally:
            Path(temp_path).unlink()
            
    def test_get_full_task_prompt(self) -> None:
        """Test extracting full Task prompt."""
        # Create temporary transcript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for data in self.transcript_data:
                f.write(json.dumps(data) + '\n')
            temp_path = f.name
            
        try:
            # Test getting Task prompt
            prompt = get_full_task_prompt(temp_path, self.session_id)
            self.assertIsNotNone(prompt)
            self.assertIn("This is a very long prompt", prompt)
            self.assertGreater(len(prompt), 200)  # Should be much longer than truncation limit
            
            # Test with wrong session ID
            prompt = get_full_task_prompt(temp_path, "wrong-session")
            self.assertIsNone(prompt)
            
        finally:
            Path(temp_path).unlink()
            
    def test_get_subagent_messages(self) -> None:
        """Test extracting subagent messages."""
        # Create temporary transcript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for data in self.transcript_data:
                f.write(json.dumps(data) + '\n')
            temp_path = f.name
            
        try:
            # Test getting subagent messages
            messages = get_subagent_messages(temp_path, self.session_id)
            self.assertEqual(len(messages), 2)
            
            # Verify message content
            self.assertEqual(messages[0]["content"], "Subagent message 1")
            self.assertEqual(messages[1]["content"], "Subagent message 2")
            
            # Verify metadata
            self.assertEqual(messages[0]["role"], "assistant")
            self.assertIn("timestamp", messages[0])
            
        finally:
            Path(temp_path).unlink()
            
    def test_nonexistent_file(self) -> None:
        """Test handling of nonexistent file."""
        lines = read_transcript_lines("/nonexistent/file.jsonl")
        self.assertEqual(lines, [])
        
        prompt = get_full_task_prompt("/nonexistent/file.jsonl", self.session_id)
        self.assertIsNone(prompt)
        
        messages = get_subagent_messages("/nonexistent/file.jsonl", self.session_id)
        self.assertEqual(messages, [])
        
    def test_malformed_json(self) -> None:
        """Test handling of malformed JSON."""
        # Create file with malformed JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json\n')
            f.write('{"another": "valid"}\n')
            temp_path = f.name
            
        try:
            lines = read_transcript_lines(temp_path)
            # Should skip invalid line
            self.assertEqual(len(lines), 2)
            
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    unittest.main()