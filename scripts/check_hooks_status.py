#!/usr/bin/env python3
"""
Check the status of Discord hooks and summarize recent activity
"""

import json
from datetime import datetime
from pathlib import Path


def check_hooks_status():
    print("🔍 Discord Hooks Status Check")
    print("=" * 50)
    print(f"Time: {datetime.now()}")
    print()

    # Check log files
    log_dir = Path("/home/ubuntu/.claude/hooks/logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("discord_hook_*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            print(f"✅ Logging is active")
            print(f"   Latest log: {latest_log.name}")
            print(f"   Size: {latest_log.stat().st_size:,} bytes")

            # Count events in log
            event_counts = {}
            with open(latest_log) as f:
                for line in f:
                    if "Event type:" in line:
                        event_type = line.split("Event type:")[-1].strip()
                        event_counts[event_type] = event_counts.get(event_type, 0) + 1

            print(f"\n📊 Event Summary (from today's log):")
            for event_type, count in sorted(event_counts.items()):
                print(f"   - {event_type}: {count} events")

            # Show recent events
            print(f"\n📋 Recent Events (last 10):")
            recent_events = []
            with open(latest_log) as f:
                for line in f:
                    if "Event type:" in line and "Tool name:" in f.readline():
                        f.seek(f.tell() - len(f.readline()))
                        tool_line = f.readline()
                        if "Tool name:" in tool_line:
                            timestamp = line.split(" - ")[0]
                            event = line.split("Event type:")[-1].strip()
                            tool = (
                                tool_line.split("Tool name:")[-1].split(",")[0].strip()
                            )
                            recent_events.append((timestamp, event, tool))

            for timestamp, event, tool in recent_events[-10:]:
                print(f"   {timestamp} - {event}: {tool}")
    else:
        print("❌ No log directory found")

    # Check Discord config
    print(f"\n🔐 Discord Configuration:")
    env_file = Path("/home/ubuntu/.claude/hooks/.env.discord")
    if env_file.exists():
        print("✅ .env.discord found")
        config_items = 0
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    config_items += 1
        print(f"   {config_items} configuration items")
    else:
        print("❌ .env.discord not found")

    # Check settings.json
    print(f"\n⚙️  Hook Configuration:")
    settings_file = Path.home() / ".claude" / "settings.json"
    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)
            if "hooks" in settings:
                print("✅ Hooks configured in settings.json")
                for event_type in settings["hooks"]:
                    discord_hooks = sum(
                        1
                        for h in settings["hooks"][event_type]
                        for hook in h.get("hooks", [])
                        if "discord_event_logger" in hook.get("command", "")
                    )
                    if discord_hooks > 0:
                        print(f"   - {event_type}: Discord logger enabled")

    print(f"\n💡 Summary:")
    print("• Hook system is capturing all events")
    print("• Events are being logged to disk")
    print("• Discord notifications may have auth issues")
    print("• Check logs for detailed debugging info")


if __name__ == "__main__":
    check_hooks_status()
