# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Overview

A comprehensive Discord notifier for Claude Code hooks that sends event notifications when Claude Code performs actions. Zero dependencies, uses only Python 3.12+ standard library with modern type annotations.

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

# Run single test file
python3 -m unittest test_discord_notifier.TestEventFiltering.test_parse_event_list_valid

# Run comprehensive type safety tests
python3 run_type_safety_tests.py

# Type checking and linting (requires Python 3.12+)
python3 -m mypy src/ configure_hooks.py
ruff check .
ruff format .

# Feature-specific tests
python3 test_mentions.py                    # User mention functionality
python3 test_error_handling.py              # Error handling scenarios
python3 test_config_type_safety.py          # Configuration type safety

# Thread management tests
python3 test_thread_persistence.py          # Thread storage and persistence functionality
python3 test_intelligent_thread_management.py  # Complete integration tests (requires mocking)

# View debug logs (requires DISCORD_DEBUG=1)
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

## Architecture

### Core Implementation
- **src/discord_notifier.py** - Main implementation (~2200+ lines, Python 3.12+ syntax)
  - `load_config()`: Loads Discord credentials with env vars overriding file config
  - `send_discord_message()`: Sends formatted embeds via webhook or bot API
  - `main()`: Reads event from stdin, formats and sends to Discord
  - **Intelligent Thread Management**: 4-tier lookup system preventing duplicate threads
    - `get_or_create_thread()`: Smart thread discovery and creation with persistence
    - `validate_thread_exists()`: Thread validation and accessibility checking
    - `find_existing_thread_by_name()`: Discord API search for existing threads
    - `ensure_thread_is_usable()`: Automatic thread unarchiving and recovery
  - Enhanced formatting functions with detailed JSON information:
    - `format_pre_tool_use()`: Shows command details, file paths, patterns, etc.
    - `format_post_tool_use()`: Includes execution results, output, errors
    - `format_notification()`: Displays all event data fields
    - `format_stop()`: Shows session details and transcript path
    - `format_subagent_stop()`: Includes task results and execution stats
- **src/thread_storage.py** - SQLite-based persistent thread storage (~400+ lines)
  - `ThreadStorage`: Zero-dependency SQLite database for session-to-thread mappings
  - `ThreadRecord`: Type-safe thread data structure with metadata
  - Automatic cleanup, search operations, and statistics reporting
- **src/type_guards.py** - Enhanced with Discord snowflake validation
  - `is_valid_snowflake()`: Validates Discord ID format for thread and channel IDs

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

### Event Filtering Configuration
The notifier supports filtering events to only process specific types. This allows for focused notifications (e.g., only session completions) without modifying hook installation:

```bash
# Environment variables for event filtering
DISCORD_ENABLED_EVENTS=Stop,Notification    # Only process these events
DISCORD_DISABLED_EVENTS=PreToolUse         # Skip these events
```

**Event Filtering in .env.discord:**
```bash
# Option 1: Only send specific events (whitelist approach)
DISCORD_ENABLED_EVENTS=Stop,Notification

# Option 2: Skip specific events (blacklist approach)  
DISCORD_DISABLED_EVENTS=PreToolUse,PostToolUse

# Option 3: No filtering (default - process all events)
# Leave both variables unset or empty
```

**Filtering Logic:**
- **DISCORD_ENABLED_EVENTS** takes precedence if both are set
- **DISCORD_DISABLED_EVENTS** is used if enabled_events is not set
- **Default behavior**: Process all events if neither is configured
- **Invalid event names** are silently ignored (graceful degradation)

**Valid Event Types:**
- `PreToolUse`: Before tool execution
- `PostToolUse`: After tool execution  
- `Notification`: System notifications
- `Stop`: Session end events
- `SubagentStop`: Subagent completion events

**Common Use Cases:**
```bash
# Only session completion notifications
DISCORD_ENABLED_EVENTS=Stop,Notification

# Everything except verbose tool executions
DISCORD_DISABLED_EVENTS=PreToolUse,PostToolUse

# Only critical events
DISCORD_ENABLED_EVENTS=Stop,Notification
```

**Thread Behavior:**
- **Text Channels**: Creates public threads using bot API (requires bot token + channel ID)
- **Forum Channels**: Creates forum posts using webhook URL (bot token not required)
- **Thread Names**: Format is `{THREAD_PREFIX} {session_id[:8]}` (e.g., "Session 1a2b3c4d")
- **Session Mapping**: Each unique session_id gets its own thread, cached for the session duration
- **Fallback**: If thread creation fails, messages fall back to the main channel

### Intelligent Thread Management (Anti-Duplicate System)

The notifier features an advanced **Intelligent Thread Management System** that prevents duplicate thread creation by implementing a 4-tier lookup strategy to discover and reuse existing threads:

**Lookup Priority Sequence:**
1. **In-Memory Cache** (fastest) - Check `SESSION_THREAD_CACHE` for active sessions
2. **Persistent Storage** - Query SQLite database for stored session → thread mappings
3. **Discord API Search** - Search Discord for existing threads by name pattern
4. **New Thread Creation** - Create new thread only if none found

**Key Features:**
- **Zero Duplicate Threads**: Prevents creation of multiple threads with identical names
- **Cross-Restart Persistence**: Maintains thread relationships across bot restarts
- **Thread Recovery**: Automatically unarchives dormant threads to restore usability
- **Session Continuity**: Users can seamlessly continue conversations in existing threads
- **Graceful Degradation**: Falls back gracefully if any lookup tier fails

### Thread Storage Configuration

The persistent storage system uses SQLite for zero-dependency thread management:

```bash
# Environment variables for thread storage
DISCORD_THREAD_STORAGE_PATH=/custom/path/threads.db  # Custom database path (optional)
DISCORD_THREAD_CLEANUP_DAYS=30                       # Days to keep unused threads (default: 30)
```

**Storage Configuration in .env.discord:**
```bash
# Thread persistence options
DISCORD_THREAD_STORAGE_PATH=/home/user/.claude/hooks/custom_threads.db
DISCORD_THREAD_CLEANUP_DAYS=14    # Clean up threads unused for 14+ days
```

**Storage Details:**
- **Database Location**: Default: `~/.claude/hooks/threads.db`
- **Auto-Cleanup**: Removes stale thread records after specified days of inactivity
- **Thread Validation**: Verifies Discord threads still exist before reusing
- **State Management**: Tracks thread archived/locked status for intelligent recovery

### Thread Management API

The system provides several key functions for thread management:

- **`get_or_create_thread()`**: Main intelligent lookup function with 4-tier strategy
- **`validate_thread_exists()`**: Checks if a Discord thread ID is still valid and accessible
- **`find_existing_thread_by_name()`**: Searches Discord API for threads matching name patterns
- **`ensure_thread_is_usable()`**: Unarchives and unlocks threads to restore functionality

**Error Handling:**
- **ThreadManagementError**: Thread creation, validation, or state management failures
- **ThreadStorageError**: Persistent storage database errors with operation context
- **Graceful Recovery**: System continues functioning even if individual operations fail

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

- **Zero dependencies**: Uses only Python 3.12+ standard library (`urllib.request` for HTTP)
- **Atomic file operations**: `configure_hooks.py` uses tempfile + rename for settings.json safety
- **Debug logging**: Timestamped files when `DISCORD_DEBUG=1` set
- **Visual distinction**: Tool-specific emojis in `TOOL_EMOJIS` dict
- **Dual auth methods**: Webhook URL (simple) or bot token + channel ID (advanced features)
- **Discord API compliance**: User-Agent "ClaudeCodeDiscordNotifier/1.0" prevents 403 errors
- **Content limits**: Discord embed limits enforced (4096 chars description, 256 title)
- **Error resilience**: Graceful degradation without blocking Claude Code execution
- **Session thread caching**: Global `SESSION_THREAD_CACHE` dict maintains thread IDs per session

### Type Safety
- **Modern Python 3.12+ syntax**: Uses `X | Y` instead of `Union[X, Y]`, `list[T]` instead of `List[T]`
- **Comprehensive TypedDict hierarchies**: Config, DiscordEmbed, DiscordMessage types for structured data
- **Tool-specific input types**: BashToolInput, FileToolInput, etc. with strict validation
- **EventType and ToolName literals**: Compile-time safety with Literal types
- **Runtime type guards**: `src/type_guards.py` provides TypeGuard functions for runtime validation
- **Three-tier validation**: TypedDict definitions → Type guards → Runtime validation

### Code Organization
- Utility functions: `truncate_string()`, `format_file_path()`, `parse_env_file()`
- TruncationLimits class centralizes all character limits
- Tool-specific formatters for pre/post-use events
- Event formatter dispatch table for clean routing
- Specific exception handling instead of bare except clauses

### Module Structure
- **src/discord_notifier.py**: Main notifier implementation with event processing
- **src/settings_types.py**: TypedDict definitions for Claude Code settings.json structure
- **src/type_guards.py**: Runtime type validation and narrowing functions
- **configure_hooks.py**: Claude Code hook configuration management
- **run_type_safety_tests.py**: Comprehensive type safety test runner

### Architectural Patterns

**Event Processing Pipeline:**
1. **Input**: Claude Code hook → JSON via stdin → `CLAUDE_HOOK_EVENT` env var
2. **Validation**: `is_valid_event_type()` TypeGuard → event filtering logic
3. **Formatting**: Tool-specific formatters via dispatch table (`EVENT_FORMATTERS`)
4. **Delivery**: HTTP client with retry logic → Discord API (webhook/bot)
5. **Threading**: Optional session-based thread creation with caching

**Type System Hierarchy:**
```
BaseField (foundation)
  → TimestampedField (adds timestamp support)
    → SessionAware (adds session_id)
      → Specific event types (PreToolUseEventData, etc.)
```

**Configuration Loading Strategy:**
- **Layer 1**: Built-in defaults (webhook_url: None, debug: False, etc.)
- **Layer 2**: File config (`~/.claude/hooks/.env.discord`) parsed via `parse_env_file()`
- **Layer 3**: Environment variables (highest precedence, runtime override)
- **Validation**: `ConfigValidator` static methods ensure consistency

**Error Handling Patterns:**
- **Custom exception hierarchy**: `DiscordNotifierError` → `ConfigurationError`, `DiscordAPIError`, etc.
- **Graceful degradation**: Always exit 0 to avoid blocking Claude Code
- **Fallback chains**: Webhook failure → bot API → log error and continue
- **Type-safe error propagation**: Specific exception types with typed error data

### Development Workflow
- **Python 3.12+ Required**: Modern type annotation syntax (`str | None`, `list[int]`, etc.)
- **Strict type checking**: MyPy configuration with Python 3.12 target and strict mode
- **Comprehensive linting**: Ruff with 30+ rule categories and auto-formatting
- **Multi-tier testing**: Unit tests (mocked), integration tests (network calls), type safety tests
- **JSON handling**: Flexible typing for `json.loads()` operations while maintaining strict typing elsewhere
- **Error handling**: Custom exception hierarchy with specific error types
- **Type safety**: Comprehensive TypedDict hierarchies with runtime validation

### Critical Implementation Notes

**Hook Installation Process:**
- `configure_hooks.py` reads existing `~/.claude/settings.json`
- Creates atomic backup before modification using tempfile + rename pattern
- Adds hook entries to each event type (PreToolUse, PostToolUse, etc.)
- Each hook points to `discord_notifier.py` with appropriate `CLAUDE_HOOK_EVENT` value
- **IMPORTANT**: Changes require Claude Code restart to take effect

**Session Thread Management:**
- Global `SESSION_THREAD_CACHE: dict[str, str]` maps session_id → thread_id
- Thread creation is lazy (first event in session triggers creation)
- Text channels use bot API (`create_text_thread()`) - requires token + channel_id
- Forum channels use webhook (`create_forum_thread()`) - only needs webhook URL
- Cache persists for session duration, cleared on process restart

**Event Filtering Logic:**
```python
# Precedence: enabled_events > disabled_events > process_all
if config["enabled_events"]:  # Whitelist approach
    return event_type in config["enabled_events"]
elif config["disabled_events"]:  # Blacklist approach  
    return event_type not in config["disabled_events"]
else:  # Default: process all events
    return True
```

### Testing Structure
- **Unit tests**: `test_discord_notifier.py` (22 tests, mocked, no network calls)
- **Integration tests**: `test.py` (actual Discord messages sent)
- **Type safety suite**: `run_type_safety_tests.py` orchestrates all type checking
  - `test_config_type_safety.py`: Configuration loading and validation
  - `test_runtime_type_validation.py`: Runtime type checking scenarios  
  - `test_type_guards_validation.py`: TypeGuard function validation
- **Feature-specific tests**: 
  - `test_mentions.py`: User mention functionality
  - `test_error_handling.py`: Error scenarios and exception handling
  - `test_stop_mentions.py`: Session end mention behavior

**Test Execution Patterns:**
```bash
# Run all tests with coverage
python3 -m unittest discover -s . -p "test_*.py"

# Type safety validation (53+ tests across 3 suites)
python3 run_type_safety_tests.py

# Single test method
python3 -m unittest test_discord_notifier.TestEventFiltering.test_should_process_event_precedence
```