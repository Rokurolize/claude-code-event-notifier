#!/usr/bin/env python3
"""Test channel routing functionality."""

import copy
import os
from pathlib import Path
import sys

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_channel_for_event, has_channel_routing, load_config
from event_types import Config


def test_channel_routing():
    """Test channel routing configuration and resolution."""
    print("🧪 Testing Channel Routing Functionality")
    print("=" * 50)

    # Test configuration with channel routing
    test_config = {
        "bot_token": "test_token",
        "channel_id": "default_channel",
        "channel_routing": {
            "enabled": True,
            "channels": {
                "tool_activity": "123456789",
                "completion": "234567890",
                "alerts": "345678901",
                "default": "999999999",
                "bash_commands": "456789012",
                "file_operations": "567890123",
                "ai_interactions": "678901234",
            },
            "event_routing": {
                "PreToolUse": "tool_activity",
                "PostToolUse": "tool_activity",
                "Stop": "completion",
                "SubagentStop": "completion",
                "Notification": "tool_activity",
            },
            "tool_routing": {
                "Bash": "bash_commands",
                "Read": "file_operations",
                "Edit": "file_operations",
                "Task": "ai_interactions",
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

    # Test 2: Event-based routing
    print("\n2. Testing event-based routing:")

    # PreToolUse -> tool_activity
    channel = get_channel_for_event("PreToolUse", None, test_config)
    assert channel == "123456789", f"Expected '123456789', got '{channel}'"
    print("   ✅ PreToolUse -> tool_activity channel")

    # Stop -> completion
    channel = get_channel_for_event("Stop", None, test_config)
    assert channel == "234567890"
    print("   ✅ Stop -> completion channel")

    # Test 3: Tool-specific routing (overrides event routing)
    print("\n3. Testing tool-specific routing:")

    # Bash tool -> bash_commands (overrides PreToolUse -> tool_activity)
    channel = get_channel_for_event("PreToolUse", "Bash", test_config)
    assert channel == "456789012"
    print("   ✅ Bash tool -> bash_commands channel")

    # Read tool -> file_operations
    channel = get_channel_for_event("PostToolUse", "Read", test_config)
    assert channel == "567890123"
    print("   ✅ Read tool -> file_operations channel")

    # Task tool -> ai_interactions
    channel = get_channel_for_event("PreToolUse", "Task", test_config)
    assert channel == "678901234"
    print("   ✅ Task tool -> ai_interactions channel")

    # Test 4: Fallback to default
    print("\n4. Testing fallback behavior:")

    # Unknown event -> default channel
    channel = get_channel_for_event("UnknownEvent", None, test_config)
    assert channel == "999999999"
    print("   ✅ Unknown event -> default channel")

    # Unknown tool -> event routing
    channel = get_channel_for_event("PreToolUse", "UnknownTool", test_config)
    assert channel == "123456789"  # Falls back to PreToolUse -> tool_activity
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

    # Set up test environment variables
    test_env = {
        "DISCORD_BOT_TOKEN": "test_token",
        "DISCORD_CHANNEL_ID": "default_channel",
        "DISCORD_CHANNEL_TOOL_ACTIVITY": "env_tool_activity",
        "DISCORD_CHANNEL_COMPLETION": "env_completion",
        "DISCORD_CHANNEL_BASH_COMMANDS": "env_bash",
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

        # Verify channel mappings
        routing = config["channel_routing"]
        channels = routing["channels"]

        assert channels["tool_activity"] == "env_tool_activity"
        assert channels["completion"] == "env_completion"
        assert channels["bash_commands"] == "env_bash"
        print("   ✅ Channel mappings loaded correctly")

        # Test routing resolution
        channel = get_channel_for_event("PreToolUse", "Bash", config)
        assert channel == "env_bash"
        print("   ✅ Tool routing works with env vars")

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
        print(f"\n✨ All tests completed successfully!")
    except Exception as e:
        import traceback

        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)
