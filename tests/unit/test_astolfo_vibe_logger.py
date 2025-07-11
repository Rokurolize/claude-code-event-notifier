#!/usr/bin/env python3
"""Unit tests for AstolfoVibeLogger."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.utils.astolfo_vibe_logger import (
    APIRequestLog,
    APIResponseLog,
    AstolfoVibeLogger,
    LogLevel,
)
from src.vibelogger.config import VibeLoggerConfig


class TestAstolfoVibeLogger(unittest.TestCase):
    """Test cases for AstolfoVibeLogger."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"
        
        # Create config
        self.config = VibeLoggerConfig(
            log_level="DEBUG",
            log_file=str(self.log_file),
            auto_save=True,
            max_file_size_mb=1,
            create_dirs=True,
            keep_logs_in_memory=True,
            max_memory_logs=100
        )
        
        # Create logger
        self.logger = AstolfoVibeLogger(config=self.config, session_id="test-session")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_basic_logging(self):
        """Test basic logging functionality."""
        self.logger.log(
            level=LogLevel.INFO,
            event="test_event",
            context={"key": "value"},
            ai_todo="Test action",
            astolfo_note="テストだよ！♡"
        )
        
        # Check log file exists
        self.assertTrue(self.log_file.exists())
        
        # Read and verify log content
        with open(self.log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            # Print log data for debugging
            print(f"Log data: {json.dumps(log_data, indent=2)}")
            
            self.assertEqual(log_data["operation"], "test_event")
            self.assertEqual(log_data["level"], "INFO")
            self.assertEqual(log_data["context"]["key"], "value")
            self.assertEqual(log_data["context"]["session_id"], "test-session")
            self.assertEqual(log_data["ai_todo"], "Test action")
            # astolfo_note might be in human_note field
            self.assertEqual(log_data.get("human_note"), "テストだよ！♡")
    
    def test_api_request_logging(self):
        """Test API request logging."""
        request = APIRequestLog(
            method="POST",
            url="https://discord.com/api/webhooks/123",
            headers={"Content-Type": "application/json"},
            body={"content": "Hello"}
        )
        
        with patch.dict(os.environ, {"DISCORD_DEBUG_LEVEL": "3"}):
            logger = AstolfoVibeLogger(config=self.config)
            logger.log_api_request(request)
        
        # Verify log content
        with open(self.log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            self.assertEqual(log_data["operation"], "api_request")
            self.assertEqual(log_data["context"]["method"], "POST")
            self.assertEqual(log_data["context"]["url"], "https://discord.com/api/webhooks/123")
            self.assertIsNotNone(log_data["context"]["headers"])
            self.assertIsNotNone(log_data["context"]["body"])
    
    def test_api_response_logging(self):
        """Test API response logging."""
        response = APIResponseLog(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"success": True},
            duration_ms=123.45
        )
        
        with patch.dict(os.environ, {"DISCORD_DEBUG_LEVEL": "2"}):
            logger = AstolfoVibeLogger(config=self.config)
            logger.log_api_response(response)
        
        # Verify log content
        with open(self.log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            self.assertEqual(log_data["operation"], "api_response")
            self.assertEqual(log_data["context"]["status_code"], 200)
            self.assertEqual(log_data["context"]["duration_ms"], 123.45)
    
    def test_function_call_decorator(self):
        """Test function call logging decorator."""
        # Create logger with debug level 3
        with patch.dict(os.environ, {"DISCORD_DEBUG_LEVEL": "3"}):
            logger = AstolfoVibeLogger(config=self.config, session_id="test-session")
            
            @logger.log_function_call
            def test_function(x: int, y: int) -> int:
                return x + y
            
            result = test_function(2, 3)
            self.assertEqual(result, 5)
        
        # Check logs
        with open(self.log_file, 'r') as f:
            logs = [json.loads(line) for line in f.readlines()]
            
            # Should have at least start and success logs
            self.assertGreaterEqual(len(logs), 2)
            
            # Check start log
            start_log = next(l for l in logs if l["operation"] == "function_call_start")
            self.assertEqual(start_log["context"]["function"], "test_function")
            
            # Check success log
            success_log = next(l for l in logs if l["operation"] == "function_call_success")
            self.assertEqual(success_log["context"]["function"], "test_function")
            self.assertIn("duration_ms", success_log["context"])
    
    def test_truncation_logging(self):
        """Test truncation logging functionality."""
        self.logger.log_truncation(
            field_name="prompt",
            original_length=5000,
            truncated_length=2000,
            limit_used=2000,
            source_location="test_file.py"
        )
        
        # Verify log content
        with open(self.log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            self.assertEqual(log_data["operation"], "text_truncation")
            self.assertEqual(log_data["context"]["field"], "prompt")
            self.assertEqual(log_data["context"]["original_length"], 5000)
            self.assertEqual(log_data["context"]["truncated_length"], 2000)
            self.assertTrue(log_data["context"]["truncated"])
            self.assertIn("切り詰められちゃった", log_data.get("human_note", ""))
    
    def test_data_transformation_logging(self):
        """Test data transformation logging."""
        original = "A" * 1000
        truncated = "A" * 200 + "..."
        
        with patch.dict(os.environ, {"DISCORD_DEBUG_LEVEL": "3"}):
            logger = AstolfoVibeLogger(config=self.config)
            logger.log_data_transformation(
                operation="truncate_string",
                before=original,
                after=truncated,
                details={"limit": 200}
            )
        
        # Verify log content
        with open(self.log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            self.assertEqual(log_data["operation"], "data_transformation")
            self.assertEqual(log_data["context"]["operation"], "truncate_string")
            self.assertEqual(log_data["context"]["before_length"], 1000)
            self.assertEqual(log_data["context"]["after_length"], 203)
            self.assertEqual(log_data["context"]["limit"], 200)
    
    def test_compatibility_methods(self):
        """Test compatibility methods for standard logging interface."""
        self.logger.debug("Debug message", extra_data="test")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        
        # Read all logs
        with open(self.log_file, 'r') as f:
            logs = [json.loads(line) for line in f.readlines()]
        
        # Verify each log level
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0]["level"], "DEBUG")
        self.assertEqual(logs[1]["level"], "INFO")
        self.assertEqual(logs[2]["level"], "WARNING")
        self.assertEqual(logs[3]["level"], "ERROR")
    
    def test_module_import_logging(self):
        """Test module import logging."""
        with patch.dict(os.environ, {"DISCORD_DEBUG_LEVEL": "3"}):
            logger = AstolfoVibeLogger(config=self.config)
            logger.log_module_import(
                module_name="src.formatters.event_formatters",
                from_path="/home/ubuntu/claude_code_event_notifier/src/formatters/event_formatters.py"
            )
        
        # Verify log content
        with open(self.log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            self.assertEqual(log_data["operation"], "module_import")
            self.assertEqual(log_data["context"]["module"], "src.formatters.event_formatters")
            self.assertIn("from_path", log_data["context"])
    
    def test_config_value_logging(self):
        """Test configuration value logging."""
        with patch.dict(os.environ, {"DISCORD_DEBUG_LEVEL": "2"}):
            logger = AstolfoVibeLogger(config=self.config)
            logger.log_config_value(
                key="PROMPT_PREVIEW",
                value=2000,
                source="src.core.constants"
            )
        
        # Verify log content
        with open(self.log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            self.assertEqual(log_data["operation"], "config_value_used")
            self.assertEqual(log_data["context"]["key"], "PROMPT_PREVIEW")
            self.assertEqual(log_data["context"]["value"], 2000)
            self.assertEqual(log_data["context"]["source"], "src.core.constants")


if __name__ == "__main__":
    unittest.main()