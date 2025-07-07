# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Overview

A single-file Discord notifier for Claude Code hooks that sends event notifications when Claude Code performs actions. Zero dependencies, uses only Python standard library.

## Commands

```bash
# Install/configure the notifier in Claude Code
python3 configure_hooks.py

# Remove the notifier from Claude Code
python3 configure_hooks.py --remove

# Run integration tests (sends test messages to Discord)
python3 test.py

# Run unit tests (no network calls)
python3 -m unittest test_discord_notifier.py

# View debug logs (requires DISCORD_DEBUG=1)
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

## Architecture

### Core Implementation
- **src/discord_notifier.py** - Single-file implementation (~1160 lines)
  - `load_config()`: Loads Discord credentials with env vars overriding file config
  - `send_discord_message()`: Sends formatted embeds via webhook or bot API
  - `main()`: Reads event from stdin, formats and sends to Discord
  - Enhanced formatting functions with detailed JSON information:
    - `format_pre_tool_use()`: Shows command details, file paths, patterns, etc.
    - `format_post_tool_use()`: Includes execution results, output, errors
    - `format_notification()`: Displays all event data fields
    - `format_stop()`: Shows session details and transcript path
    - `format_subagent_stop()`: Includes task results and execution stats

### Hook Integration
The notifier integrates with Claude Code's hook system by modifying `~/.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "CLAUDE_HOOK_EVENT=PreToolUse python3 ~/.claude/hooks/discord_notifier.py"
      }],
      "matcher": ""
    }]
  }
}
```

### Event Flow
1. Claude Code triggers hook event → passes JSON data via stdin
2. discord_notifier.py reads event type from `CLAUDE_HOOK_EVENT` env var
3. Formats event data into Discord embed with color coding and emojis
4. Sends via webhook URL (simple) or bot API (requires channel ID)
5. Exits quickly (non-blocking) with graceful error handling

### Configuration Precedence
1. Environment variables (highest priority)
2. ~/.claude/hooks/.env.discord file
3. Built-in defaults

### Thread Support Configuration
The notifier supports creating separate Discord threads for each Claude Code session to improve organization:

```bash
# Environment variables for thread support
DISCORD_USE_THREADS=1              # Enable thread support (default: 0)
DISCORD_CHANNEL_TYPE=text          # Channel type: "text" or "forum" (default: "text")
DISCORD_THREAD_PREFIX=Session      # Thread name prefix (default: "Session")
```

**Thread Configuration in .env.discord:**
```bash
# Basic Discord setup
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN

# Thread support options
DISCORD_USE_THREADS=1
DISCORD_CHANNEL_TYPE=forum         # forum for forum channels, text for text channels
DISCORD_THREAD_PREFIX=Claude       # Custom prefix for thread names

# For bot API (required for text channel threads)
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

### User Mention Configuration
The notifier can mention a Discord user when Notification and Stop events are sent:

```bash
# Environment variable for user mentions
DISCORD_MENTION_USER_ID=123456789012345678  # Your Discord user ID
```

**Mention Configuration in .env.discord:**
```bash
# User mention for notifications
DISCORD_MENTION_USER_ID=123456789012345678  # Discord user ID to mention
```

**How to find your Discord User ID:**
1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click on your username in any channel
3. Select "Copy User ID"

**Note:** Mentions work for Notification and Stop events to avoid spam. The mention appears above the embed message.

**Thread Behavior:**
- **Text Channels**: Creates public threads using bot API (requires bot token + channel ID)
- **Forum Channels**: Creates forum posts using webhook URL (bot token not required)
- **Thread Names**: Format is `{THREAD_PREFIX} {session_id[:8]}` (e.g., "Session 1a2b3c4d")
- **Session Mapping**: Each unique session_id gets its own thread, cached for the session duration
- **Fallback**: If thread creation fails, messages fall back to the main channel

### Supported Events
- **PreToolUse** (blue): Before tool execution with detailed information
  - Shows tool name, session ID, timestamp
  - Tool-specific details (commands, file paths, patterns, URLs, etc.)
  - Full command text for Bash (up to 500 chars)
  - File operation details for Edit/Write/Read
- **PostToolUse** (green): After tool execution with results
  - Includes execution output (stdout/stderr for Bash)
  - File operation success/error status
  - Result summaries for search/list operations
  - Execution timestamp
- **Notification** (orange): System notifications with full event data
  - Message content and session details
  - Any additional event fields displayed
- **Stop** (gray): Session end events with details
  - Session ID and end timestamp
  - Transcript path if available
  - Session statistics (duration, tools used, etc.)
- **SubagentStop** (purple): Subagent completion with task results
  - Task description and completion time
  - Result summary (up to 400 chars)
  - Execution statistics

## Key Implementation Details

- Uses `urllib.request` for HTTP calls (no requests library needed)
- Atomic file writes in `configure_hooks.py` using tempfile + rename
- Debug logging to timestamped files when `DISCORD_DEBUG=1`
- Tool-specific emojis in `TOOL_EMOJIS` dict for visual distinction
- Webhook auth: Direct POST to webhook URL
- Bot auth: Requires bot token + channel ID with proper headers
- User-Agent header required: "ClaudeCodeDiscordNotifier/1.0" (prevents Discord 403 errors)
- Discord embed length limits enforced (4096 chars for description, 256 for title)

### Type Safety
- Comprehensive type annotations using TypedDict, Literal, Union types
- Config, DiscordEmbed, DiscordMessage types for structured data
- Tool-specific input types (BashToolInput, FileToolInput, etc.)
- EventType and ToolName literal types for compile-time safety
- ToolNames enum for consistent tool name references

### Code Organization
- Utility functions: `truncate_string()`, `format_file_path()`, `parse_env_file()`
- TruncationLimits class centralizes all character limits
- Tool-specific formatters for pre/post-use events
- Event formatter dispatch table for clean routing
- Specific exception handling instead of bare except clauses