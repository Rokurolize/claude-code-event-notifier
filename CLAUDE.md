# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this simple Discord notifier.

## Overview

This is a single-file Discord notifier for Claude Code hooks. It sends event notifications to Discord when Claude Code performs actions like using tools or ending sessions.

## Setup

```bash
# Configure Claude Code hooks
python configure_hooks.py

# Set up Discord credentials
cp ~/.claude/hooks/.env.discord.example ~/.claude/hooks/.env.discord
# Edit ~/.claude/hooks/.env.discord with your Discord webhook URL or bot token
```

## Testing

```bash
# Run the test script to verify Discord integration
python test.py

# View debug logs (when DISCORD_DEBUG=1)
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

## Project Structure

- `src/discord_notifier.py` - The single-file Discord notifier script
- `configure_hooks.py` - Installs the notifier into Claude Code's hooks system
- `test.py` - Test script to verify the Discord integration works
- `README.md` - User documentation

## How It Works

1. Claude Code triggers a hook event (PreToolUse, PostToolUse, Notification, Stop, SubagentStop)
2. The event data is passed via stdin to `discord_notifier.py`
3. The script formats the event into a Discord embed message and sends it
4. Errors are logged when debug mode is enabled (DISCORD_DEBUG=1)

## Key Features

- **No dependencies** - Uses only Python standard library
- **Simple setup** - Just copy one file and update settings.json
- **Flexible auth** - Supports Discord webhooks (recommended) or bot tokens
- **Graceful failures** - Won't interrupt Claude Code if Discord is unavailable