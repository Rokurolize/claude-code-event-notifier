# Claude Code Discord Notifier

Send Claude Code events to Discord. One file, no dependencies, simple setup.

## Quick Start

### 1. Configure Claude Code Hooks

```bash
python3 configure_hooks.py
```

### 2. Set Up Discord Credentials

```bash
cp .env.example ~/.claude/.env
# Edit the file with your Discord webhook URL or bot token
```

### 3. Restart Claude Code

That's it! You'll now receive Discord notifications for Claude Code events.

## Configuration

Edit `~/.claude/.env`:

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
- **PostToolUse** - After tool execution (green)
- **Notification** - System notifications (orange)
- **Stop** - Session ends (gray)
- **SubagentStop** - Subagent completes (purple)

## Removal

To remove the Discord notifier from Claude Code:

```bash
python3 configure_hooks.py --remove
```

## Troubleshooting

- **No notifications?** Check your Discord credentials in `~/.claude/.env`
- **Debug mode:** Set `DISCORD_DEBUG=1` in `~/.claude/.env`
- **Logs:** Check `~/.claude/hooks/logs/discord_notifier_*.log` when debug is enabled

## Architecture

- **Modular design:** Core implementation in `src/` directory with 4 focused modules
- **Comprehensive:** ~4,900 lines of Python code with advanced type safety
- **Zero dependencies:** Uses only Python 3.13+ standard library
- **Intelligent threading:** 4-tier thread management with persistent storage
- **Type-safe:** Comprehensive TypedDict definitions and runtime validation
- **Reliable:** Fails gracefully without blocking Claude Code
