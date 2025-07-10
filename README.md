# Claude Code Discord Notifier

Send Claude Code events to Discord with real-time notifications, thread organization, and full Task prompt visibility. Zero external dependencies, uses only Python 3.13+ standard library.

## Quick Start

### 1. Configure Claude Code Hooks

```bash
# Use uv to ensure Python 3.13+ is used
uv run --no-sync --python 3.13 python configure_hooks.py

# Or if you have Python 3.13+ installed:
# python3.13 configure_hooks.py
```

### 2. Set Up Discord Credentials

```bash
cp ~/.claude/hooks/.env.discord.example ~/.claude/hooks/.env.discord
# Edit the file with your Discord webhook URL or bot token
```

### 3. Restart Claude Code

That's it! You'll now receive Discord notifications for Claude Code events.

## Configuration

Edit `~/.claude/hooks/.env.discord`:

```bash
# Option 1: Webhook (recommended - easier)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN

# Option 2: Bot Token (more features)
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here

# Optional: Enable debug logging
DISCORD_DEBUG=1
```

## Events Tracked

- **PreToolUse** - Before any tool executes (blue)
  - Shows full Task prompts from transcript files (not truncated!)
- **PostToolUse** - After tool execution (green)
- **Notification** - System notifications (orange)
- **Stop** - Session ends (gray)
- **SubagentStop** - Subagent completes (purple)
  - Includes subagent message history

## Removal

To remove the Discord notifier from Claude Code:

```bash
uv run --no-sync --python 3.13 python configure_hooks.py --remove
```

## Troubleshooting

- **No notifications?** Check your Discord credentials in `.env.discord`
- **Debug mode:** Set `DISCORD_DEBUG=1` in `.env.discord`
- **Logs:** Check `~/.claude/hooks/logs/discord_notifier_*.log` when debug is enabled

## Architecture

- **Modular design:** 21 Python files organized in `src/` directory with focused modules
- **Comprehensive:** ~9,600 lines of Python code with advanced type safety
- **Zero dependencies:** Uses only Python 3.13+ standard library
- **Intelligent threading:** 4-tier thread management with SQLite persistent storage
- **Type-safe:** Comprehensive TypedDict definitions and runtime validation
- **Transcript integration:** Reads Claude Code transcript files for complete context
- **Reliable:** Fails gracefully without blocking Claude Code

## Features

- **Full Task Prompts:** No more truncated prompts - see the complete Task tool input
- **Thread Organization:** Automatically groups messages by session in Discord threads
- **Subagent Monitoring:** Track what subagents are doing with message history
- **Flexible Configuration:** Use webhooks (simple) or bot tokens (advanced features)
- **Event Filtering:** Enable/disable specific events via configuration
- **Debug Logging:** Comprehensive logging for troubleshooting
## Advanced Configuration

### Event Filtering

Control which events are sent to Discord:

```bash
# Only send specific events
DISCORD_ENABLED_EVENTS=PreToolUse,PostToolUse,SubagentStop

# Or disable specific events
DISCORD_DISABLED_EVENTS=Notification,Stop
```

### Thread Management

Configure thread behavior:

```bash
# Enable/disable threading (default: true)
DISCORD_USE_THREADS=true

# Custom thread prefix
DISCORD_THREAD_PREFIX=Claude Session

# Thread cleanup after days (default: 30)
DISCORD_THREAD_CLEANUP_DAYS=7
```

### Mention Users

Get notified with @mentions:

```bash
# Your Discord user ID
DISCORD_MENTION_USER_ID=123456789012345678
```

## Requirements

- Python 3.13 or higher (required for TypeIs and ReadOnly features)
- Claude Code CLI
- Discord webhook URL or bot token
- Optional: [uv](https://github.com/astral-sh/uv) for automatic Python version management

## License

MIT
