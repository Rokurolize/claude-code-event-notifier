#!/usr/bin/env python3
"""Test Claude Code Hooks Integration.

This module provides comprehensive tests for Claude Code hooks integration,
including hook configuration, event reception, stdin/stdout handling,
environment variable processing, and non-blocking execution.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
import sys
import os
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
import signal
import threading
import time

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.discord_notifier import main as discord_notifier_main
from src.type_defs.events import EventDict, ToolUseEvent
from src.type_defs.tools import ToolResult, EditToolInput, WriteToolInput
import configure_hooks


# Hook test types
class HookConfig(TypedDict):
    """Hook configuration structure."""
    event: str
    command: str
    cwd: Optional[str]
    env: Optional[Dict[str, str]]


class HookTestResult(TypedDict):
    """Result of hook test execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timed_out: bool


class TestHookIntegration(unittest.IsolatedAsyncioTestCase):
    """Test cases for Claude Code hooks integration."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.temp_dir = tempfile.mkdtemp()
        self.hooks_dir = Path(self.temp_dir) / ".claude" / "hooks"
        self.hooks_dir.mkdir(parents=True)
        
        # Test configuration
        self.test_config = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "enabled_events": ["ToolUse", "Error", "Stop"],
            "disabled_events": ["Response"],
            "debug": True
        }
        
        # Sample events
        self.sample_events = {
            "ToolUse": {
                "event_type": "ToolUse",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-123",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/test/file.py",
                    "old_string": "old",
                    "new_string": "new"
                },
                "tool_result": {
                    "success": True,
                    "output": "File edited successfully"
                }
            },
            "Error": {
                "event_type": "Error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-123",
                "error_type": "ValidationError",
                "error_message": "Invalid input",
                "stack_trace": "Traceback..."
            },
            "Stop": {
                "event_type": "Stop",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "test-session-123",
                "reason": "User requested stop"
            }
        }
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_hook_configuration(self) -> None:
        """Test hook configuration and installation."""
        # Create mock settings.json
        settings_path = self.hooks_dir.parent / "settings.json"
        settings = {
            "hooks": []
        }
        settings_path.write_text(json.dumps(settings, indent=2))
        
        # Test hook installation
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            with patch.dict(os.environ, {
                "DISCORD_WEBHOOK_URL": self.test_config["webhook_url"]
            }):
                # Mock sys.argv for configure_hooks
                with patch.object(sys, 'argv', ['configure_hooks.py']):
                    # Run configure_hooks
                    configure_hooks.main()
        
        # Verify hooks were added
        updated_settings = json.loads(settings_path.read_text())
        self.assertIn("hooks", updated_settings)
        self.assertGreater(len(updated_settings["hooks"]), 0)
        
        # Verify hook structure
        for hook in updated_settings["hooks"]:
            self.assertIn("event", hook)
            self.assertIn("command", hook)
            self.assertIn(hook["event"], ["ToolUse", "Error", "Response", "Stop", "Start"])
    
    async def test_stdin_event_processing(self) -> None:
        """Test processing events from stdin."""
        for event_type, event_data in self.sample_events.items():
            with self.subTest(event_type=event_type):
                # Prepare stdin input
                stdin_data = json.dumps(event_data)
                
                # Mock stdin and environment
                with patch('sys.stdin.read', return_value=stdin_data):
                    with patch.dict(os.environ, {
                        "CLAUDE_HOOK_EVENT": event_type,
                        "DISCORD_WEBHOOK_URL": self.test_config["webhook_url"]
                    }):
                        # Mock Discord sender
                        with patch('src.handlers.discord_sender.DiscordSender.send_notification') as mock_send:
                            mock_send.return_value = True
                            
                            # Run notifier
                            result = await discord_notifier_main()
                            
                            # Verify notification was sent
                            self.assertEqual(result, 0)
                            mock_send.assert_called_once()
    
    async def test_environment_variable_handling(self) -> None:
        """Test environment variable processing."""
        env_vars = {
            "CLAUDE_HOOK_EVENT": "ToolUse",
            "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/456/def",
            "DISCORD_USE_THREADS": "true",
            "DISCORD_ENABLED_EVENTS": "ToolUse,Error",
            "DISCORD_DISABLED_EVENTS": "Response",
            "DISCORD_DEBUG": "1"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Import config after setting env vars
            from src.core.config import ConfigManager
            config = ConfigManager().load_config()
            
            # Verify config loaded from env
            self.assertEqual(config["DISCORD_WEBHOOK_URL"], env_vars["DISCORD_WEBHOOK_URL"])
            self.assertTrue(config["DISCORD_USE_THREADS"])
            self.assertIn("ToolUse", config["DISCORD_ENABLED_EVENTS"])
            self.assertIn("Error", config["DISCORD_ENABLED_EVENTS"])
            self.assertIn("Response", config["DISCORD_DISABLED_EVENTS"])
            self.assertTrue(config["DISCORD_DEBUG"])
    
    async def test_non_blocking_execution(self) -> None:
        """Test non-blocking hook execution."""
        # Create a slow hook script
        slow_hook = self.hooks_dir / "slow_hook.py"
        slow_hook.write_text("""
import time
import sys
# Simulate slow processing
time.sleep(2)
print("Slow hook completed")
sys.exit(0)
""")
        slow_hook.chmod(0o755)
        
        # Test with timeout
        start_time = time.time()
        
        proc = subprocess.Popen(
            [sys.executable, str(slow_hook)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Should not block
        try:
            stdout, stderr = proc.communicate(timeout=0.1)
            self.fail("Hook should have timed out")
        except subprocess.TimeoutExpired:
            # Expected behavior - hook runs in background
            elapsed = time.time() - start_time
            self.assertLess(elapsed, 0.5)  # Should timeout quickly
            
            # Clean up
            proc.terminate()
            proc.wait()
    
    async def test_event_filtering(self) -> None:
        """Test event filtering based on configuration."""
        test_cases = [
            # Enabled event
            {
                "event_type": "ToolUse",
                "enabled_events": ["ToolUse", "Error"],
                "disabled_events": [],
                "should_process": True
            },
            # Disabled event
            {
                "event_type": "Response",
                "enabled_events": [],
                "disabled_events": ["Response"],
                "should_process": False
            },
            # Not in enabled list
            {
                "event_type": "Stop",
                "enabled_events": ["ToolUse"],
                "disabled_events": [],
                "should_process": False
            },
            # All events enabled
            {
                "event_type": "Error",
                "enabled_events": [],
                "disabled_events": [],
                "should_process": True
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                with patch.dict(os.environ, {
                    "CLAUDE_HOOK_EVENT": test_case["event_type"],
                    "DISCORD_WEBHOOK_URL": self.test_config["webhook_url"],
                    "DISCORD_ENABLED_EVENTS": ",".join(test_case["enabled_events"]),
                    "DISCORD_DISABLED_EVENTS": ",".join(test_case["disabled_events"])
                }):
                    # Mock Discord sender
                    with patch('src.handlers.discord_sender.DiscordSender.send_notification') as mock_send:
                        mock_send.return_value = True
                        
                        # Prepare event data
                        event_data = self.sample_events.get(
                            test_case["event_type"],
                            {"event_type": test_case["event_type"]}
                        )
                        
                        with patch('sys.stdin.read', return_value=json.dumps(event_data)):
                            # Run notifier
                            result = await discord_notifier_main()
                            
                            # Verify filtering
                            if test_case["should_process"]:
                                mock_send.assert_called()
                            else:
                                mock_send.assert_not_called()
                            
                            # Should always exit 0
                            self.assertEqual(result, 0)
    
    async def test_error_handling_non_blocking(self) -> None:
        """Test that errors don't block Claude Code."""
        error_scenarios = [
            # Invalid JSON input
            {
                "stdin": "invalid json {",
                "event": "ToolUse"
            },
            # Missing required fields
            {
                "stdin": json.dumps({}),
                "event": "ToolUse"
            },
            # Network error
            {
                "stdin": json.dumps(self.sample_events["ToolUse"]),
                "event": "ToolUse",
                "network_error": True
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(scenario=scenario):
                with patch.dict(os.environ, {
                    "CLAUDE_HOOK_EVENT": scenario["event"],
                    "DISCORD_WEBHOOK_URL": self.test_config["webhook_url"]
                }):
                    with patch('sys.stdin.read', return_value=scenario["stdin"]):
                        if scenario.get("network_error"):
                            # Mock network error
                            with patch('src.core.http_client.HTTPClient.post') as mock_post:
                                mock_post.side_effect = Exception("Network error")
                                
                                # Should still exit 0
                                result = await discord_notifier_main()
                                self.assertEqual(result, 0)
                        else:
                            # Should handle gracefully
                            result = await discord_notifier_main()
                            self.assertEqual(result, 0)
    
    async def test_concurrent_hook_execution(self) -> None:
        """Test concurrent hook executions."""
        num_hooks = 5
        results = []
        
        async def run_hook(event_data: Dict[str, Any]) -> int:
            """Run a single hook."""
            with patch('sys.stdin.read', return_value=json.dumps(event_data)):
                with patch.dict(os.environ, {
                    "CLAUDE_HOOK_EVENT": event_data["event_type"],
                    "DISCORD_WEBHOOK_URL": self.test_config["webhook_url"]
                }):
                    with patch('src.handlers.discord_sender.DiscordSender.send_notification') as mock_send:
                        mock_send.return_value = True
                        return await discord_notifier_main()
        
        # Run multiple hooks concurrently
        tasks = []
        for i in range(num_hooks):
            event_data = self.sample_events["ToolUse"].copy()
            event_data["session_id"] = f"session-{i}"
            tasks.append(run_hook(event_data))
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        self.assertEqual(len(results), num_hooks)
        self.assertTrue(all(r == 0 for r in results))
    
    async def test_hook_removal(self) -> None:
        """Test hook removal functionality."""
        # Create mock settings with hooks
        settings_path = self.hooks_dir.parent / "settings.json"
        settings = {
            "hooks": [
                {
                    "event": "ToolUse",
                    "command": "python /path/to/notifier.py"
                },
                {
                    "event": "Error",
                    "command": "python /path/to/notifier.py"
                }
            ]
        }
        settings_path.write_text(json.dumps(settings, indent=2))
        
        # Test hook removal
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            with patch.object(sys, 'argv', ['configure_hooks.py', '--remove']):
                # Run configure_hooks with remove flag
                configure_hooks.main()
        
        # Verify hooks were removed
        updated_settings = json.loads(settings_path.read_text())
        
        # Should have no Discord notifier hooks
        discord_hooks = [
            h for h in updated_settings.get("hooks", [])
            if "discord_notifier" in h.get("command", "")
        ]
        self.assertEqual(len(discord_hooks), 0)
    
    async def test_hook_command_execution(self) -> None:
        """Test actual hook command execution."""
        # Create test hook script
        test_hook = self.hooks_dir / "test_hook.py"
        test_hook.write_text(f"""
import sys
import json
import os

# Read event from stdin
event_data = json.loads(sys.stdin.read())

# Write to test file to verify execution
output_file = "{self.temp_dir}/hook_output.json"
with open(output_file, "w") as f:
    json.dump({{
        "event": os.environ.get("CLAUDE_HOOK_EVENT"),
        "data": event_data,
        "pid": os.getpid()
    }}, f)

# Always exit 0
sys.exit(0)
""")
        test_hook.chmod(0o755)
        
        # Execute hook
        event_data = self.sample_events["ToolUse"]
        proc = subprocess.Popen(
            [sys.executable, str(test_hook)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                **os.environ,
                "CLAUDE_HOOK_EVENT": "ToolUse"
            },
            text=True
        )
        
        stdout, stderr = proc.communicate(input=json.dumps(event_data))
        
        # Verify execution
        self.assertEqual(proc.returncode, 0)
        
        # Check output file
        output_file = Path(self.temp_dir) / "hook_output.json"
        self.assertTrue(output_file.exists())
        
        output_data = json.loads(output_file.read_text())
        self.assertEqual(output_data["event"], "ToolUse")
        self.assertEqual(output_data["data"]["session_id"], event_data["session_id"])
    
    async def test_signal_handling(self) -> None:
        """Test signal handling for graceful shutdown."""
        # Create hook that handles signals
        signal_hook = self.hooks_dir / "signal_hook.py"
        signal_hook.write_text(f"""
import signal
import sys
import time
import json

shutdown = False

def signal_handler(signum, frame):
    global shutdown
    shutdown = True
    with open("{self.temp_dir}/signal_received.txt", "w") as f:
        f.write(str(signum))
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Read event data
event_data = json.loads(sys.stdin.read())

# Simulate processing
while not shutdown:
    time.sleep(0.1)
""")
        signal_hook.chmod(0o755)
        
        # Start hook process
        proc = subprocess.Popen(
            [sys.executable, str(signal_hook)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send event data
        proc.stdin.write(json.dumps(self.sample_events["ToolUse"]))
        proc.stdin.close()
        
        # Give it time to start
        time.sleep(0.5)
        
        # Send SIGTERM
        proc.terminate()
        proc.wait(timeout=2)
        
        # Verify signal was handled
        signal_file = Path(self.temp_dir) / "signal_received.txt"
        self.assertTrue(signal_file.exists())
        
        # Should have received SIGTERM (15)
        signal_num = int(signal_file.read_text())
        self.assertEqual(signal_num, signal.SIGTERM)
    
    def _execute_hook(self, command: str, event_data: Dict[str, Any], 
                     env: Optional[Dict[str, str]] = None) -> HookTestResult:
        """Execute a hook command and return results."""
        start_time = time.time()
        
        # Prepare environment
        hook_env = os.environ.copy()
        if env:
            hook_env.update(env)
        
        # Execute hook
        proc = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=hook_env,
            text=True
        )
        
        try:
            stdout, stderr = proc.communicate(
                input=json.dumps(event_data),
                timeout=5.0
            )
            
            return HookTestResult(
                success=proc.returncode == 0,
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                execution_time=time.time() - start_time,
                timed_out=False
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            return HookTestResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Hook execution timed out",
                execution_time=time.time() - start_time,
                timed_out=True
            )


if __name__ == "__main__":
    unittest.main()