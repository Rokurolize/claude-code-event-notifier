# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## AI Assistant Instructions

This project uses Claude Code for development assistance. The AI assistant should:

- Focus on code quality and type safety
- Use Python 3.13+ features appropriately
- Follow the project's architectural patterns
- Ensure comprehensive error handling
- Maintain detailed logging throughout the codebase

For operations that may generate large amounts of lint errors, use the Task tool to delegate to
sub-agents with clear, specific, and detailed instructions to avoid context window pressure.

## Overview

A comprehensive Discord notifier for Claude Code hooks that sends event notifications when
Claude Code performs actions. Zero dependencies, uses only Python 3.13+ standard library with
modern type annotations and intelligent thread management.

## Commands

```bash
# Install/configure the notifier in Claude Code (now references source directly)
python3 configure_hooks.py

# Remove the notifier from Claude Code
python3 configure_hooks.py --remove

# Run integration tests (sends test messages to Discord)
python3 test.py

# Run unit tests (no network calls)
python3 -m unittest test_discord_notifier.py

# Run all tests
python3 -m unittest discover -s . -p "test_*.py"

# Run single test method
python3 -m unittest test_discord_notifier.TestEventFiltering.test_parse_event_list_valid

# Run comprehensive type safety tests
python3 run_type_safety_tests.py

# Type checking and linting (requires Python 3.13+)
python3 -m mypy src/ configure_hooks.py
ruff check .
ruff format .

# Feature-specific tests
python3 test_mentions.py                      # User mention functionality
python3 test_error_handling.py                # Error handling scenarios
python3 test_config_type_safety.py            # Configuration type safety
python3 test_thread_persistence.py            # Thread storage and persistence
python3 test_intelligent_thread_management.py # Complete integration tests
python3 test_archived_thread_search.py        # Archived thread search functionality

# View debug logs (requires DISCORD_DEBUG=1)
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

## Architecture

### Core Implementation

- **src/discord_notifier.py** - Main implementation (~3200+ lines, Python 3.13+ syntax)

  - Uses Python 3.13 features: `TypeIs`, `ReadOnly` TypedDict, ExceptionGroup
  - Comprehensive event processing pipeline with type safety
  - HTTP client with Discord API support (webhook and bot)
  - **Intelligent Thread Management**: 4-tier lookup system
    1. In-memory cache (`SESSION_THREAD_CACHE`)
    2. SQLite persistent storage
    3. Discord API search (active + archived threads)
    4. New thread creation
  - **Archived Thread Search**: NEW - searches public/private archived threads
    - `list_public_archived_threads()`: Paginated search with before/limit params
    - `list_private_archived_threads()`: For accessible private archives
    - `search_all_threads()`: Comprehensive search across all thread states

- **src/thread_storage.py** - SQLite-based persistent thread storage

  - Zero-dependency SQLite implementation
  - Automatic cleanup of stale records
  - Thread validation and state tracking

- **src/type_guards.py** - Runtime type validation

  - TypeGuard functions for all data structures
  - Discord snowflake validation
  - Python 3.13 `TypeIs` functions for enhanced type narrowing

- **src/settings_types.py** - TypedDict definitions for Claude Code settings

### Hook Integration

**IMPORTANT**: As of latest update, hooks reference source files directly without copying:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "CLAUDE_HOOK_EVENT=PreToolUse python3 " +
                       "/home/ubuntu/claude_code_event_notifier/src/discord_notifier.py"
          }
        ],
        "matcher": ".*"
      }
    ]
  }
}
```

This allows real-time development - changes to source files are immediately reflected in hook execution.

### Event Processing Pipeline

1. Claude Code triggers hook → JSON via stdin
2. Event type from `CLAUDE_HOOK_EVENT` env var
3. Event filtering check (enabled/disabled lists)
4. Format to Discord embed with tool-specific details
5. Thread lookup/creation if enabled
6. Send via webhook or bot API
7. Exit 0 (non-blocking)

### Configuration System

- **Precedence**: Environment variables > .env.discord file > defaults
- **File location**: `~/.claude/hooks/.env.discord`
- **Validation**: Multi-tier validation with helpful error messages

### Thread Management Features

**Intelligent Thread Management with Archived Thread Search (ENHANCED)**:

- **4-Tier Thread Lookup System**:
  1. In-memory cache (`SESSION_THREAD_CACHE`)
  2. SQLite persistent storage
  3. Discord API search (active + archived threads) - **NEW**
  4. New thread creation
- **Archived Thread Search (NEW)**:
  - Searches public archived threads with pagination
  - Searches private archived threads (requires MANAGE_THREADS permission)
  - Automatically unarchives threads when reusing
  - Prevents duplicate thread creation across all thread states
- **Error Details (NEW)**:
  - Enhanced error reporting with Discord API response bodies
  - Shows specific error codes (e.g., 160006 for max active threads)

**Thread Configuration**:

```bash
DISCORD_USE_THREADS=1              # Enable threads
DISCORD_CHANNEL_TYPE=text          # "text" or "forum"
DISCORD_THREAD_PREFIX=Session      # Thread name prefix
DISCORD_THREAD_STORAGE_PATH=/path  # Custom DB location
DISCORD_THREAD_CLEANUP_DAYS=30     # Cleanup interval
```

### Supported Events

- **PreToolUse**: Tool execution start (blue)
- **PostToolUse**: Tool execution complete (green)
- **Notification**: System messages (orange)
- **Stop**: Session end (gray)
- **SubagentStop**: Subagent complete (purple)

Each event includes:

- Session ID and timestamp
- Tool-specific details and formatting
- Execution results and errors
- Optional user mentions

### Type Safety Architecture

```
BaseField
├── TimestampedField
│   └── SessionAware
│       └── BaseEventData
│           ├── PreToolUseEventData
│           ├── PostToolUseEventData
│           └── NotificationEventData
└── PathAware
    └── FileToolInputBase
```

### Testing Strategy

- **Unit tests**: Mocked, no network calls
- **Integration tests**: Real Discord API calls
- **Type safety tests**: Comprehensive validation
- **Feature tests**: Specific functionality

### Development Notes

**Python 3.13+ Required**:

- Modern type annotations (`X | Y` syntax)
- `TypeIs` for enhanced type narrowing
- `ReadOnly` TypedDict fields
- ExceptionGroup for error aggregation

**Direct Source Execution**:

- Hooks execute source files directly (no copying)
- Changes take effect immediately
- Restart Claude Code after running configure_hooks.py

**Error Handling**:

- Custom exception hierarchy
- Graceful degradation
- Non-blocking execution
- Comprehensive logging with DISCORD_DEBUG=1

**Discord API Limits**:

- Embed description: 4096 chars
- Embed title: 256 chars
- Field value: 1024 chars
- Automatic truncation with indicators

**Thread Creation Limits**:

- Discord enforces maximum active thread limits
- System falls back to main channel on errors
- 400 Bad Request often indicates limit reached

### Common Issues

**No notifications**: Check webhook URL or bot token in .env.discord

**Thread creation fails**: Usually permissions or Discord limits. Messages still send to main channel.

**Import errors in logs**: Relative imports when running standalone - doesn't affect functionality.

**Debug logging**: Set DISCORD_DEBUG=1 and check ~/.claude/hooks/logs/
