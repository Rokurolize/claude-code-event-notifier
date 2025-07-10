# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Overview

Discord notifier for Claude Code hooks. Sends real-time notifications when Claude Code performs actions (file operations, command execution, etc.). Zero dependencies, uses only Python 3.13+ standard library.

## Commands

```bash
# Install/configure the notifier in Claude Code
python3 configure_hooks.py

# Remove the notifier from Claude Code
python3 configure_hooks.py --remove

# Run all tests
python3 -m unittest discover -s tests -p "test_*.py"

# Run specific test categories
python3 -m unittest discover -s tests/unit -p "test_*.py"      # Unit tests only
python3 -m unittest discover -s tests/feature -p "test_*.py"    # Feature tests
python3 -m unittest discover -s tests/integration -p "test_*.py" # Integration tests

# Run single test file
python3 -m unittest tests/unit/test_discord_notifier.py

# Type checking and linting
python3 -m mypy src/ configure_hooks.py
ruff check src/ configure_hooks.py utils/
ruff format src/ configure_hooks.py utils/

# View debug logs (requires DISCORD_DEBUG=1)
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

## Architecture

### Core Structure

The project is organized into focused modules:

```
src/
├── discord_notifier.py    # Main entry point and event processing
├── thread_storage.py       # SQLite-based thread persistence
├── type_guards.py          # Runtime type validation with TypeGuard/TypeIs
└── settings_types.py       # TypedDict definitions for Claude Code settings

src/core/
├── config.py              # Configuration loading and validation
└── http_client.py         # Discord API client implementation

src/handlers/
├── discord_sender.py      # Message sending logic
├── event_registry.py      # Event type registration and dispatch
└── thread_manager.py      # Thread lookup and management

src/formatters/
├── base.py                # Base formatter protocol
├── event_formatters.py    # Event-specific formatters
└── tool_formatters.py     # Tool-specific formatters
```

### Event Processing Flow

1. **Hook Trigger**: Claude Code executes a tool and triggers the configured hook
2. **Event Reception**: `discord_notifier.py` receives JSON event data via stdin
3. **Event Parsing**: Event type determined from `CLAUDE_HOOK_EVENT` environment variable
4. **Filtering**: Check if event type is enabled/disabled in configuration
5. **Formatting**: Event-specific formatter creates Discord embed with appropriate details
6. **Thread Management**: If threads enabled, perform 4-tier lookup:
   - Check in-memory cache (`SESSION_THREAD_CACHE`)
   - Check SQLite storage (`thread_storage.py`)
   - Search Discord API for existing threads
   - Create new thread if needed
7. **Sending**: Use webhook or bot API to send formatted message
8. **Non-blocking Exit**: Always exit 0 to avoid blocking Claude Code

### Key Design Patterns

**Type Safety Throughout**:
- All data structures defined as TypedDict
- Runtime validation with TypeGuard functions
- Python 3.13+ type features (`TypeIs`, union types)

**Modular HTTP Client**:
- Separate methods for webhook vs bot API
- Built-in retry logic with exponential backoff
- Comprehensive error handling with custom exceptions

**Smart Thread Management**:
- Persistent storage prevents thread duplication
- Automatic thread unarchiving when reused
- Graceful fallback to main channel on errors

**Event-Specific Formatting**:
- Each event type has dedicated formatter
- Tool-specific details extracted and displayed
- Automatic truncation for Discord limits

### Configuration

Configuration follows a precedence hierarchy:
1. Environment variables (highest priority)
2. `.env.discord` file in `~/.claude/hooks/`
3. Default values (lowest priority)

Key configuration options:
- `DISCORD_WEBHOOK_URL` or `DISCORD_TOKEN` + `DISCORD_CHANNEL_ID`
- `DISCORD_USE_THREADS` - Enable thread organization
- `DISCORD_ENABLED_EVENTS` / `DISCORD_DISABLED_EVENTS` - Event filtering
- `DISCORD_DEBUG` - Enable detailed logging

### Hook Integration

Hooks are configured to execute source files directly:
- No copying of files to hooks directory
- Changes to source code take effect immediately
- Must restart Claude Code after running `configure_hooks.py`