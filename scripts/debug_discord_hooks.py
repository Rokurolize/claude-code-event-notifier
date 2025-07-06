#!/usr/bin/env python3
"""Debug Discord hooks configuration"""

import os
import json
import urllib.request
from pathlib import Path

# Load environment
env_file = Path(".env.test")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

token = os.environ.get("DISCORD_TOKEN", "Not set")
channel_id = os.environ.get("DISCORD_CHANNEL_ID", "Not set")

print("Discord Configuration Debug")
print("=" * 30)
print(f"Token: {token[:20]}..." if token != "Not set" else "Token: Not set")
print(f"Channel ID: {channel_id}")
print()

# Test bot info
if token != "Not set":
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {token}"},
        )
        with urllib.request.urlopen(req) as response:
            bot_info = json.loads(response.read())
            print(
                f"✅ Bot authenticated: {bot_info['username']}#{bot_info['discriminator']}"
            )
    except Exception as e:
        print(f"❌ Bot authentication failed: {e}")

# Test channel access
if token != "Not set" and channel_id != "Not set":
    try:
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{channel_id}",
            headers={"Authorization": f"Bot {token}"},
        )
        with urllib.request.urlopen(req) as response:
            channel_info = json.loads(response.read())
            print(
                f"✅ Channel accessible: {channel_info.get('name', 'Unknown')} (type: {channel_info.get('type', 'Unknown')})"
            )
    except urllib.error.HTTPError as e:
        print(f"❌ Channel access failed: {e}")
        print("   Possible issues:")
        print("   - Bot not in the server")
        print("   - Bot lacks View Channel permission")
        print("   - Channel ID is incorrect")
    except Exception as e:
        print(f"❌ Channel check failed: {e}")

print()
print("Hook Configuration:")
hooks_file = Path.home() / ".claude" / "hooks.json"
if hooks_file.exists():
    print(f"✅ hooks.json exists at {hooks_file}")
    with open(hooks_file) as f:
        hooks = json.load(f)
        discord_hooks = 0
        for event, configs in hooks.get("hooks", {}).items():
            for config in configs:
                for hook in config.get("hooks", []):
                    if "discord_event_logger.py" in hook.get("command", ""):
                        discord_hooks += 1
        print(f"✅ Found {discord_hooks} Discord hook configurations")
else:
    print(f"❌ hooks.json not found at {hooks_file}")

print()
print("Testing message send...")
test_message = {
    "content": "Test message from debug script",
    "embeds": [{"title": "Debug Test", "color": 0x00FF00}],
}
if token != "Not set" and channel_id != "Not set":
    try:
        data = json.dumps(test_message).encode("utf-8")
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            data=data,
            headers={
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req) as response:
            print("✅ Test message sent successfully!")
    except urllib.error.HTTPError as e:
        print(f"❌ Message send failed: HTTP {e.code}")
        if e.code == 403:
            print("   Bot lacks Send Messages permission in this channel")
        elif e.code == 404:
            print("   Channel not found")
    except Exception as e:
        print(f"❌ Message send failed: {e}")
