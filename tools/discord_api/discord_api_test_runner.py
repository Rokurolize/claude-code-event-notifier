#!/usr/bin/env python3
"""Discord API comprehensive test runner.

Unified test suite for Discord API functionality including access tests,
message validation, event simulation, and comprehensive analysis.
Combines functionality from multiple test scripts into one tool.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from shared import (
    get_discord_bot_token,
    get_discord_channel_id,
    validate_discord_config,
    make_discord_request,
    print_api_response,
)


class TestResult:
    """Container for test results."""
    
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.error_message: Optional[str] = None
        self.details: dict[str, Any] = {}
    
    def set_success(self, details: Optional[dict[str, Any]] = None) -> None:
        """Mark test as successful."""
        self.success = True
        self.error_message = None
        if details:
            self.details.update(details)
    
    def set_failure(self, error: str, details: Optional[dict[str, Any]] = None) -> None:
        """Mark test as failed."""
        self.success = False
        self.error_message = error
        if details:
            self.details.update(details)
    
    def __str__(self) -> str:
        status = "✅ PASS" if self.success else "❌ FAIL"
        result = f"{status} {self.name}"
        if self.error_message:
            result += f" - {self.error_message}"
        return result


class DiscordAPITestSuite:
    """Comprehensive Discord API test suite."""
    
    def __init__(self, channel_id: Optional[str] = None, quick_mode: bool = False):
        self.channel_id = channel_id or get_discord_channel_id()
        self.quick_mode = quick_mode
        self.results: list[TestResult] = []
        self.start_time = time.time()
    
    def add_result(self, result: TestResult) -> None:
        """Add test result to suite."""
        self.results.append(result)
        print(f"   {result}")
    
    def test_configuration(self) -> TestResult:
        """Test Discord configuration validity."""
        result = TestResult("Configuration Validation")
        
        is_valid, message = validate_discord_config()
        if is_valid:
            result.set_success({"message": message})
        else:
            result.set_failure(message)
        
        return result
    
    def test_bot_authentication(self) -> TestResult:
        """Test bot authentication with Discord API."""
        result = TestResult("Bot Authentication")
        
        url = "https://discord.com/api/v10/users/@me"
        success, data, error = make_discord_request(url)
        
        if success and data:
            result.set_success({
                "bot_id": data.get("id"),
                "bot_username": data.get("username"),
                "verified": data.get("verified", False),
            })
        else:
            result.set_failure(error or "Authentication failed")
        
        return result
    
    def test_channel_access(self) -> TestResult:
        """Test access to target channel."""
        result = TestResult("Channel Access")
        
        if not self.channel_id:
            result.set_failure("No channel ID configured")
            return result
        
        url = f"https://discord.com/api/v10/channels/{self.channel_id}"
        success, data, error = make_discord_request(url)
        
        if success and data:
            result.set_success({
                "channel_name": data.get("name"),
                "channel_type": data.get("type"),
                "guild_id": data.get("guild_id"),
            })
        else:
            result.set_failure(error or "Channel access failed")
        
        return result
    
    def test_message_retrieval(self) -> TestResult:
        """Test message retrieval from channel."""
        result = TestResult("Message Retrieval")
        
        if not self.channel_id:
            result.set_failure("No channel ID configured")
            return result
        
        url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages?limit=10"
        success, data, error = make_discord_request(url)
        
        if success and data and isinstance(data, list):
            # Count Discord Notifier messages
            notifier_count = 0
            for msg in data:
                embeds = msg.get("embeds", [])
                for embed in embeds:
                    footer = embed.get("footer", {}).get("text", "")
                    if "Discord Notifier" in footer:
                        notifier_count += 1
                        break
            
            result.set_success({
                "message_count": len(data),
                "notifier_messages": notifier_count,
                "has_notifier_messages": notifier_count > 0,
            })
        else:
            result.set_failure(error or "Message retrieval failed")
        
        return result
    
    def test_permissions(self) -> TestResult:
        """Test bot permissions in the channel."""
        result = TestResult("Permission Check")
        
        if not self.channel_id:
            result.set_failure("No channel ID configured")
            return result
        
        # Test various permission-dependent endpoints
        permissions_tests = [
            ("view_channel", f"https://discord.com/api/v10/channels/{self.channel_id}"),
            ("read_message_history", f"https://discord.com/api/v10/channels/{self.channel_id}/messages?limit=1"),
            ("view_archived_threads", f"https://discord.com/api/v10/channels/{self.channel_id}/threads/archived/public"),
        ]
        
        passed_permissions = []
        failed_permissions = []
        
        for perm_name, url in permissions_tests:
            success, _, error = make_discord_request(url)
            if success:
                passed_permissions.append(perm_name)
            else:
                failed_permissions.append((perm_name, error))
        
        if len(passed_permissions) >= 2:  # At least basic permissions work
            result.set_success({
                "passed_permissions": passed_permissions,
                "failed_permissions": failed_permissions,
            })
        else:
            result.set_failure(f"Insufficient permissions: {failed_permissions}")
        
        return result
    
    def test_event_simulation(self) -> TestResult:
        """Test event simulation using the simple architecture."""
        result = TestResult("Event Simulation")
        
        # Find the simple architecture main script
        main_script = Path("src/simple/main.py")
        if not main_script.exists():
            result.set_failure("Simple architecture main.py not found")
            return result
        
        # Test event data
        test_event = {
            "session_id": "test-api-runner",
            "hook_event_name": "Notification",
            "message": "🧪 Discord API Test Runner verification message",
        }
        
        try:
            # Run the script with test data
            process = subprocess.run(
                ["uv", "run", "--python", "3.13", "python", str(main_script)],
                input=json.dumps(test_event),
                text=True,
                capture_output=True,
                timeout=30,
            )
            
            if process.returncode == 0:
                result.set_success({
                    "exit_code": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                })
            else:
                result.set_failure(f"Script failed with exit code {process.returncode}: {process.stderr}")
        
        except subprocess.TimeoutExpired:
            result.set_failure("Script execution timed out")
        except Exception as e:
            result.set_failure(f"Script execution error: {e}")
        
        return result
    
    def test_rate_limiting(self) -> TestResult:
        """Test API rate limiting behavior."""
        result = TestResult("Rate Limiting")
        
        if not self.channel_id:
            result.set_failure("No channel ID configured")
            return result
        
        url = f"https://discord.com/api/v10/channels/{self.channel_id}"
        
        # Make several rapid requests
        responses = []
        for i in range(5):
            start_time = time.time()
            success, data, error = make_discord_request(url)
            end_time = time.time()
            
            responses.append({
                "success": success,
                "response_time": end_time - start_time,
                "error": error,
            })
            
            time.sleep(0.1)  # Small delay between requests
        
        successful_requests = sum(1 for r in responses if r["success"])
        avg_response_time = sum(r["response_time"] for r in responses) / len(responses)
        
        if successful_requests >= 4:  # Allow for some potential rate limiting
            result.set_success({
                "successful_requests": successful_requests,
                "total_requests": len(responses),
                "avg_response_time": f"{avg_response_time:.3f}s",
            })
        else:
            result.set_failure(f"Too many failed requests: {successful_requests}/{len(responses)}")
        
        return result
    
    def run_all_tests(self) -> None:
        """Run all tests in the suite."""
        print("🚀 Discord API Comprehensive Test Suite")
        print("=" * 70)
        print(f"Target Channel: {self.channel_id or 'Not configured'}")
        print(f"Test Mode: {'Quick (essential tests only)' if self.quick_mode else 'Full'}")
        print(f"Test Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Define test sequence
        tests = [
            self.test_configuration,
            self.test_bot_authentication,
            self.test_channel_access,
            self.test_message_retrieval,
            self.test_permissions,
        ]
        
        # Add optional tests if not in quick mode
        if not self.quick_mode:
            tests.extend([
                self.test_event_simulation,
                self.test_rate_limiting,
            ])
        
        # Run each test
        for i, test_func in enumerate(tests, 1):
            print(f"🧪 Running Test {i}/{len(tests)}: {test_func.__name__.replace('test_', '').replace('_', ' ').title()}")
            
            try:
                result = test_func()
                self.add_result(result)
            except Exception as e:
                error_result = TestResult(test_func.__name__)
                error_result.set_failure(f"Test execution error: {e}")
                self.add_result(error_result)
            
            print()
    
    def print_summary(self) -> None:
        """Print test summary and statistics."""
        end_time = time.time()
        duration = end_time - self.start_time
        
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        success_rate = passed / total if total > 0 else 0
        
        print("📊 Test Summary")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1%}")
        print(f"Execution Time: {duration:.2f}s")
        print()
        
        # Show failed tests
        failed_tests = [r for r in self.results if not r.success]
        if failed_tests:
            print("❌ Failed Tests:")
            for test in failed_tests:
                print(f"   {test.name}: {test.error_message}")
            print()
        
        # Overall status
        if success_rate >= 0.9:
            print("✅ Overall Status: EXCELLENT - Discord API is fully functional")
        elif success_rate >= 0.7:
            print("⚠️  Overall Status: GOOD - Minor issues detected")
        elif success_rate >= 0.5:
            print("⚠️  Overall Status: PARTIAL - Significant issues detected")
        else:
            print("❌ Overall Status: POOR - Major issues detected")
    
    def get_exit_code(self) -> int:
        """Get appropriate exit code based on test results."""
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        success_rate = passed / total if total > 0 else 0
        
        if success_rate >= 0.9:
            return 0  # Excellent
        elif success_rate >= 0.7:
            return 1  # Good but with warnings
        else:
            return 2  # Issues detected


def main() -> None:
    """Main entry point for test runner."""
    import argparse
    
    description = """Discord API comprehensive test runner

Executes a complete test suite to verify Discord API functionality including
authentication, permissions, message operations, and integration with the
Simple Notifier system."""
    
    epilog = """Tests performed (7 total):
  1. Configuration validation
     - Verifies bot token and channel ID are properly configured
     
  2. Bot authentication
     - Tests Discord API authentication
     - Retrieves bot user information
     
  3. Channel access permissions
     - Verifies access to target channel
     - Retrieves channel metadata
     
  4. Message retrieval
     - Tests ability to fetch recent messages
     - Counts Discord/Simple Notifier messages
     
  5. Permission verification
     - Tests various permission-dependent endpoints
     - Identifies missing permissions
     
  6. Event simulation (skipped in --quick mode)
     - Tests Simple Notifier integration
     - Simulates notification event
     
  7. Rate limiting behavior (skipped in --quick mode)
     - Tests API rate limit handling
     - Measures response times

Examples:
  # Run all tests on default channel
  %(prog)s
  
  # Test specific channel
  %(prog)s --channel-id 1391964875600822366
  
  # Quick test (essential tests only - 1-5)
  %(prog)s --quick
  
  # Quick test on specific channel
  %(prog)s --channel-id 1391964875600822366 --quick

Configuration:
  Bot token and channel ID can be set via:
  - Environment: DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
  - Config file: ~/.claude/.env

--quick mode:
  Runs only essential tests (1-5), skipping:
  - Event simulation test (requires Simple Notifier setup)
  - Rate limiting test (takes extra time)
  
  Use --quick for rapid connectivity verification.

Output:
  - Individual test results with pass/fail status
  - Detailed error messages for failures
  - Overall summary with success rate
  - Exit code based on results

Exit codes:
  0 - Excellent (≥90%% tests passed)
  1 - Good but with warnings (≥70%% passed)
  2 - Issues detected (<70%% passed)
  3 - Interrupted by user
  4 - Test suite error
"""
    
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--channel-id",
        help="Discord channel ID to test. If not specified, uses DISCORD_CHANNEL_ID from config"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only essential tests (1-5), skip event simulation and rate limiting tests"
    )
    
    args = parser.parse_args()
    
    # Create and run test suite
    suite = DiscordAPITestSuite(channel_id=args.channel_id, quick_mode=args.quick)
    
    try:
        suite.run_all_tests()
        suite.print_summary()
        
        print()
        print("🎯 Test suite completed!")
        
        sys.exit(suite.get_exit_code())
    
    except KeyboardInterrupt:
        print("\n⚠️  Test suite interrupted by user")
        sys.exit(3)
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        sys.exit(4)


if __name__ == "__main__":
    main()