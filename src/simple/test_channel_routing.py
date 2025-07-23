#!/usr/bin/env python3
"""Test channel routing functionality."""

import copy
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_channel_for_event, has_channel_routing, load_config


def test_channel_routing():
    """Test channel routing configuration and resolution."""
    print("🧪 Testing Channel Routing Functionality")
    print("=" * 50)

    # Test configuration with official event-based channel routing
    test_config = {
        "bot_token": "test_token",
        "channel_id": "default_channel",
        "channel_routing": {
            "enabled": True,
            "channels": {
                "pretooluse": "123456789",
                "posttooluse": "234567890",
                "notification": "345678901",
                "stop": "456789012",
                "subagentstop": "567890123",
                "default": "999999999",
            },
            "event_routing": {
                "PreToolUse": "pretooluse",
                "PostToolUse": "posttooluse",
                "Notification": "notification",
                "Stop": "stop",
                "SubagentStop": "subagentstop",
            },
            "tool_routing": {
                # No tool routing for now - events go directly to their channels
            },
        },
    }

    # Test 1: has_channel_routing
    print("1. Testing has_channel_routing():")
    assert has_channel_routing(test_config) == True
    print("   ✅ Detects enabled routing correctly")

    # Test with disabled routing
    disabled_config = copy.deepcopy(test_config)
    disabled_config["channel_routing"]["enabled"] = False
    assert has_channel_routing(disabled_config) == False
    print("   ✅ Detects disabled routing correctly")

    # Test 2: Official event-based routing
    print("\n2. Testing official event-based routing:")

    # PreToolUse -> pretooluse channel
    channel = get_channel_for_event("PreToolUse", None, test_config)
    assert channel == "123456789", f"Expected '123456789', got '{channel}'"
    print("   ✅ PreToolUse -> pretooluse channel")

    # Notification -> notification channel
    channel = get_channel_for_event("Notification", None, test_config)
    assert channel == "345678901"
    print("   ✅ Notification -> notification channel")

    # SubagentStop -> subagentstop channel
    channel = get_channel_for_event("SubagentStop", None, test_config)
    assert channel == "567890123"
    print("   ✅ SubagentStop -> subagentstop channel")

    # Test 3: Tool name does not override (simplified routing)
    print("\n3. Testing event routing with tools:")

    # Tools go through their event channels (no tool-specific overrides)
    channel = get_channel_for_event("PreToolUse", "Bash", test_config)
    assert channel == "123456789"  # Still goes to pretooluse channel
    print("   ✅ Bash tool -> pretooluse channel")

    # Read tool also goes to posttooluse for PostToolUse
    channel = get_channel_for_event("PostToolUse", "Read", test_config)
    assert channel == "234567890"  # posttooluse channel
    print("   ✅ Read tool -> posttooluse channel")

    # Task tool goes to pretooluse for PreToolUse
    channel = get_channel_for_event("PreToolUse", "Task", test_config)
    assert channel == "123456789"  # pretooluse channel
    print("   ✅ Task tool -> pretooluse channel")

    # Test 4: Fallback to default
    print("\n4. Testing fallback behavior:")

    # Unknown event -> default channel
    channel = get_channel_for_event("UnknownEvent", None, test_config)
    assert channel == "999999999"
    print("   ✅ Unknown event -> default channel")

    # Unknown tool -> event routing (still goes to proper event channel)
    channel = get_channel_for_event("PreToolUse", "UnknownTool", test_config)
    assert channel == "123456789"  # Falls back to PreToolUse -> pretooluse
    print("   ✅ Unknown tool -> event routing fallback")

    # Test 5: No routing configuration
    print("\n5. Testing disabled routing:")

    no_routing_config = {"bot_token": "test", "channel_id": "default"}
    channel = get_channel_for_event("PreToolUse", "Bash", no_routing_config)
    assert channel is None
    print("   ✅ No routing returns None")

    print("\n" + "=" * 50)
    print("🎉 All channel routing tests passed!")


def test_environment_variable_loading():
    """Test loading channel routing from environment variables."""
    print("\n🧪 Testing Environment Variable Loading")
    print("=" * 50)

    # Set up test environment variables for official event structure
    test_env = {
        "DISCORD_BOT_TOKEN": "test_token",
        "DISCORD_CHANNEL_ID": "default_channel",
        "DISCORD_CHANNEL_PRETOOLUSE": "env_pretooluse",
        "DISCORD_CHANNEL_NOTIFICATION": "env_notification",
        "DISCORD_CHANNEL_SUBAGENTSTOP": "env_subagentstop",
        "DISCORD_CHANNEL_DEFAULT": "env_default",
    }

    # Backup original environment
    original_env = {}
    for key in test_env:
        original_env[key] = os.environ.get(key)
        os.environ[key] = test_env[key]

    try:
        # Load config with environment variables
        config = load_config()

        # Verify routing was enabled
        assert has_channel_routing(config)
        print("   ✅ Routing enabled from environment variables")

        # Verify channel mappings for official events
        routing = config["channel_routing"]
        channels = routing["channels"]

        assert channels["pretooluse"] == "env_pretooluse"
        assert channels["notification"] == "env_notification"
        assert channels["subagentstop"] == "env_subagentstop"
        assert channels["default"] == "env_default"
        print("   ✅ Channel mappings loaded correctly")

        # Test routing resolution with official events
        pretooluse_channel = get_channel_for_event("PreToolUse", None, config)
        notification_channel = get_channel_for_event("Notification", None, config)
        subagentstop_channel = get_channel_for_event("SubagentStop", None, config)

        assert pretooluse_channel == "env_pretooluse"
        assert notification_channel == "env_notification"
        assert subagentstop_channel == "env_subagentstop"
        print("   ✅ Official event routing works with env vars")

        print("\n🎉 Environment variable loading tests passed!")

    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    try:
        test_channel_routing()
        test_environment_variable_loading()
        print("\n✨ All tests completed successfully!")
    except Exception as e:
        import traceback

        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)
