# Claude Code Discord Notifier

Send Claude Code events to Discord. One file, no dependencies, simple setup.

## Requirements

- **Python 3.13 or higher** (required)
- **uv** (recommended) - Install from https://github.com/astral-sh/uv

## Quick Start

### 1. Install Python 3.13 (if not already installed)

```bash
# Option 1: Using uv (recommended)
uv python install 3.13

# Option 2: Download from Python.org
# Visit https://www.python.org/downloads/
```

### 2. Configure Claude Code Hooks

```bash
# Using uv (recommended - automatically uses Python 3.13)
uv run python configure_hooks.py

# Or if you have Python 3.13 in your PATH
python3.13 configure_hooks.py
```

### 3. Set Up Discord Credentials

```bash
cp .env.example ~/.claude/.env
# Edit the file with your Discord bot token and channel ID
```

### 4. Restart Claude Code

That's it! You'll now receive Discord notifications for Claude Code events.

## Configuration

Edit `~/.claude/.env`:

```bash
# Discord Bot Token (required)
DISCORD_BOT_TOKEN=your_bot_token_here
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
# Using uv (recommended)
uv run python configure_hooks.py --remove

# Or if you have Python 3.13 in your PATH
python3.13 configure_hooks.py --remove
```

## Troubleshooting

- **No notifications?** Check your Discord credentials in `~/.claude/.env`
- **Debug mode:** Set `DISCORD_DEBUG=1` in `~/.claude/.env`
- **Logs:** Check `~/.claude/hooks/logs/discord_notifier_*.log` when debug is enabled

## Troubleshooting Python Version

If you see an error about Python version:

```text
ERROR: This project requires Python 3.13 or higher.
Current Python version: 3.12.3
```

This means you're running with an older Python. Solutions:

1. **Use uv** (recommended): `uv run python configure_hooks.py`
2. **Install Python 3.13**: `uv python install 3.13`
3. **Check your Python**: `python3 --version` vs `uv run python --version`

## Architecture

- **Modular design:** Core implementation in `src/` directory with 4 focused modules
- **Comprehensive:** ~4,900 lines of Python code with advanced type safety
- **Zero dependencies:** Uses only Python 3.13+ standard library
- **Intelligent threading:** 4-tier thread management with persistent storage
- **Type-safe:** Comprehensive TypedDict definitions and runtime validation
- **Reliable:** Fails gracefully without blocking Claude Code
