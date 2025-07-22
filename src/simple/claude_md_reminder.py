#!/usr/bin/env python3
"""CLAUDE.md update reminder for Discord Event Notifier.

This script sends a Discord notification to remind about updating CLAUDE.md
when significant changes occur in the project.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from discord_client import send_to_discord
from event_types import Config, DiscordMessage


def check_if_update_needed() -> str | None:
    """Check if CLAUDE.md needs updating based on recent changes."""
    # Check for significant files that might indicate need for update
    significant_files = [
        "INSTRUCTIONS.md",
        "README.md", 
        "configure_hooks.py",
        "configure_hooks_simple.py",
        "src/simple/main.py",
        "src/main.py"
    ]
    
    project_root = Path(__file__).parent.parent.parent
    claude_md = project_root / "CLAUDE.md"
    
    if not claude_md.exists():
        return "CLAUDE.md not found!"
    
    try:
        # Get CLAUDE.md modification time
        claude_md_mtime = claude_md.stat().st_mtime
    except (IOError, OSError) as e:
        return f"Error accessing CLAUDE.md: {e}"
    
    # Check if any significant files were modified after CLAUDE.md
    newer_files = []
    for file_path in significant_files:
        full_path = project_root / file_path
        try:
            if full_path.exists():
                if full_path.stat().st_mtime > claude_md_mtime:
                    newer_files.append(file_path)
        except (IOError, OSError):
            # Skip files we can't access
            continue
    
    if newer_files:
        return f"Files modified after CLAUDE.md: {', '.join(newer_files)}"
    
    return None


def send_reminder(reason: str, config: Config) -> None:
    """Send a reminder notification to Discord."""
    message: DiscordMessage = {
        "embeds": [{
            "title": "📝 CLAUDE.md Update Reminder",
            "description": (
                "重要な変更が検出されました。CLAUDE.mdの更新を検討してください。\n\n"
                f"**理由**: {reason}\n\n"
                "**更新すべき内容**:\n"
                "- アーキテクチャの変更\n"
                "- 解決したエラーと教訓\n"
                "- 新機能や重要な設計決定\n\n"
                "```bash\n"
                "# タイムスタンプ取得\n"
                "date +\"%Y-%m-%d-%H-%M-%S\"\n"
                "```"
            ),
            "color": 0xFFD700,  # Gold
            "footer": {
                "text": "CLAUDE.md Auto-Update Reminder | " + 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }]
    }
    
    send_to_discord(message, config)


def main() -> None:
    """Check and send reminder if needed."""
    config = load_config()
    if not config:
        return
    
    reason = check_if_update_needed()
    if reason:
        send_reminder(reason, config)
        print(f"📨 Reminder sent: {reason}")
    else:
        print("✅ CLAUDE.md appears to be up to date")


if __name__ == "__main__":
    main()