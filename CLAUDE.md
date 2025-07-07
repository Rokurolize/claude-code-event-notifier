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
- **src/discord_notifier.py** - Single-file implementation (~780 lines)
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