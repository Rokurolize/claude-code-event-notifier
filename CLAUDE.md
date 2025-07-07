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
- **src/discord_notifier.py** - Single-file implementation (~240 lines)
  - `load_config()`: Loads Discord credentials with env vars overriding file config
  - `send_discord_message()`: Sends formatted embeds via webhook or bot API
  - `main()`: Reads event from stdin, formats and sends to Discord

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
- **PreToolUse** (blue): Before tool execution, includes tool name and input
- **PostToolUse** (green): After tool execution, includes execution time
- **Notification** (orange): System notifications with messages
- **Stop** (gray): Session end events
- **SubagentStop** (purple): Subagent completion with results

## Key Implementation Details

- Uses `urllib.request` for HTTP calls (no requests library needed)
- Atomic file writes in `configure_hooks.py` using tempfile + rename
- Debug logging to timestamped files when `DISCORD_DEBUG=1`
- Tool-specific emojis in `TOOL_EMOJIS` dict for visual distinction
- Webhook auth: Direct POST to webhook URL
- Bot auth: Requires bot token + channel ID with proper headers