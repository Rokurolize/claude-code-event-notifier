# Claude Code Discord Notifier

Send Claude Code events to Discord. One file, no dependencies, simple setup.

## Quick Start

1. **Install:**

   ```bash
   python3 install.py
   ```

2. **Configure Discord:**

   ```bash
   cp ~/.claude/hooks/.env.discord.example ~/.claude/hooks/.env.discord
   # Edit the file with your Discord webhook URL or bot token
   ```

3. **Restart Claude Code**

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
- **PostToolUse** - After tool execution (green)
- **Notification** - System notifications (orange)
- **Stop** - Session ends (gray)
- **SubagentStop** - Subagent completes (purple)

## Uninstall

```bash
python3 install.py --uninstall
```

## Troubleshooting

- **No notifications?** Check your Discord credentials in `.env.discord`
- **Debug mode:** Set `DISCORD_DEBUG=1` in `.env.discord`
- **Logs:** Check `~/.claude/hooks/logs/discord_notifier_*.log` when debug is enabled

## Architecture

- **Single file:** `discord_notifier.py` (~240 lines)
- **No dependencies:** Uses only Python standard library
- **Fast:** Minimal overhead, exits quickly
- **Reliable:** Fails gracefully without blocking Claude Code
