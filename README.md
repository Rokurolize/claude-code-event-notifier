# Claude Code Discord Notifier

![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/Rokurolize/claude-code-event-notifier?utm_source=oss&utm_medium=github&utm_campaign=Rokurolize%2Fclaude-code-event-notifier&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

Send Claude Code events to Discord. Pure Python 3.13+, zero dependencies, simple setup.

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

### Advanced Configuration

```bash
# Event Control (granular)
DISCORD_EVENT_PRETOOLUSE=1      # Tool execution start
DISCORD_EVENT_POSTTOOLUSE=1     # Tool execution end
DISCORD_EVENT_NOTIFICATION=1    # System notifications
DISCORD_EVENT_STOP=0            # Session end
DISCORD_EVENT_SUBAGENT_STOP=1   # Subagent completion

# Tool Filtering
DISCORD_TOOL_READ=0             # Disable Read tool notifications
DISCORD_TOOL_EDIT=1             # Enable Edit tool notifications
DISCORD_TOOL_BASH=1             # Enable Bash tool notifications
DISCORD_TOOL_TASK=1             # Enable Task tool notifications

# Advanced Features
DISCORD_THREAD_FOR_TASK=1       # Create threads for Task execution
```

### Channel Routing (NEW)

Route notifications to different Discord channels based on event type:

```bash
# Basic channel separation
DISCORD_CHANNEL_TOOL_ACTIVITY=123456789   # PreToolUse/PostToolUse events
DISCORD_CHANNEL_COMPLETION=987654321      # Stop/SubagentStop events  
DISCORD_CHANNEL_ALERTS=456789123          # Errors and warnings
DISCORD_CHANNEL_DEFAULT=555555555         # Fallback channel

# Tool-specific routing (overrides event routing)
DISCORD_CHANNEL_BASH_COMMANDS=111111111   # Bash tool notifications
DISCORD_CHANNEL_FILE_OPERATIONS=222222222 # Read/Edit/Write notifications
DISCORD_CHANNEL_SEARCH_GREP=333333333     # Grep/Glob/LS notifications
DISCORD_CHANNEL_AI_INTERACTIONS=444444444 # Task/WebFetch/TodoWrite
```

## Events Tracked

- **PreToolUse** - Before any tool executes (blue)
- **PostToolUse** - After tool execution (green)
- **Notification** - System notifications (orange)
- **Stop** - Session ends (gray)
- **SubagentStop** - Subagent completes (purple)

## Testing Your Setup

```bash
# Validate end-to-end setup
uv run python configure_hooks.py --validate-end-to-end

# Test Discord connectivity
uv run python utils/check_discord_access.py

# Test with a sample event
uv run python src/simple/main.py < test_event.json
```

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
- **Logs:** Check `~/.claude/hooks/logs/simple_notifier_*.log` when debug is enabled
- **Verify bot permissions:** Ensure your bot has "Send Messages" permission in the Discord channel

## Debugging

When `DISCORD_DEBUG=1` is set, the notifier saves raw input/output data for debugging:

```text
~/.claude/hooks/debug/
# For tool-related events (PreToolUse/PostToolUse):
├── {timestamp}_{event_type}_{tool_name}_raw_input.json      # Raw hook input data
├── {timestamp}_{event_type}_{tool_name}_formatted_output.json  # Discord message data

# For other events (Stop, Notification, SubagentStop):
├── {timestamp}_{event_type}_raw_input.json      # Raw hook input data
└── {timestamp}_{event_type}_formatted_output.json  # Discord message data
```

Examples:
- `20250722_143025_123_PreToolUse_Bash_raw_input.json` - Bash tool execution start
- `20250722_143027_456_PostToolUse_Read_formatted_output.json` - Read tool completion
- `20250722_143030_789_Stop_raw_input.json` - Session end event

Features:
- **Automatic cleanup**: Files older than 7 days are deleted automatically
- **Privacy protection**: Tokens and sensitive data are masked with `***MASKED***`
- **Easy analysis**: JSON format for easy inspection and debugging

Example usage:
```bash
# Enable debug mode
echo "DISCORD_DEBUG=1" >> ~/.claude/.env

# View recent debug files
ls -la ~/.claude/hooks/debug/

# Inspect a specific event
cat ~/.claude/hooks/debug/*_PreToolUse_raw_input.json | jq

# Find all Bash tool executions
ls ~/.claude/hooks/debug/*_Bash_*.json

# View Read tool events
cat ~/.claude/hooks/debug/*_Read_*.json | jq '.tool_name'
```

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

The project uses a **Simple Architecture** (900 lines) that prioritizes reliability:

- **Zero dependencies:** Uses only Python 3.13+ standard library
- **Fail-silent design:** Never blocks Claude Code execution
- **Type-safe:** Modern Python 3.13+ type annotations throughout
- **Secure:** Input sanitization, path validation, and markdown escaping
- **Thread support:** Automatic thread creation for Task tool executions
- **Channel routing:** Route notifications to different Discord channels

For detailed architecture information, see [CLAUDE.md](CLAUDE.md).

## Contributing

This project welcomes contributions! Please ensure:
- Python 3.13+ compatibility
- Zero external dependencies in the simple architecture
- All code passes `uv run ruff check` and `uv run ruff format`
- Tests pass with `uv run python -m pytest tests/unit/`

## License

MIT License - see [LICENSE](LICENSE) file for details.