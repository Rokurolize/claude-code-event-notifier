# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Environment
**Critical**: This project requires Python 3.13+ and uses uv for dependency management.

```bash
# Development environment setup
uv install --dev  # Install all dev dependencies (mypy, ruff, pytest, etc.)

# Setup hooks (NEW - use architecture-specific scripts)
uv run python setup_guide.py        # Interactive setup guide (recommended)
uv run python setup_simple.py       # Setup simple architecture directly
uv run python setup_full.py         # Setup full architecture directly

# Remove hooks
uv run python setup_simple.py --remove  # Remove simple architecture hooks
uv run python setup_full.py --remove    # Remove full architecture hooks

# Testing
uv run python -m pytest tests/unit/        # Run unit tests
uv run python -m pytest tests/integration/ # Run integration tests
uv run python -m pytest --cov=src         # Run with coverage
uv run python -m pytest -x                # Stop on first failure

# Code Quality
uv run ruff check .                        # Lint code
uv run ruff format .                       # Format code
uv run mypy src/                          # Type checking

# Pre-PR Checklist
uv run ruff check src/simple/              # Essential lint checks only
uv run python -m pytest tests/unit/ -x     # Unit tests (stop on first failure)
git diff --check                           # Check for whitespace errors

# Debug Discord connectivity
uv run python tools/discord_api/discord_api_test_runner.py --quick
uv run python utils/check_discord_access.py
```

### Architecture-Specific Commands

```bash
# Simple Architecture (main implementation)
uv run python src/simple/main.py < test_event.json  # Test event processing
uv run python configure_hooks_simple.py             # Configure simple hooks

# Simple architecture-specific testing
cd src/simple && uv run python test_channel_routing.py  # Test channel routing
cd src/simple && uv run python test_all_events.py       # Test all event types

# Full Architecture (legacy)
uv run python src/main.py < test_event.json         # Test full architecture
```

## Core Architecture

This project implements a **dual architecture system** for Discord notifications:

### Simple Architecture (Primary - 900 lines)
- **Location**: `src/simple/`
- **Design**: Pure Python 3.13+, zero dependencies, fail-silent
- **Entry Point**: `src/simple/main.py`
- **Key Principle**: Never block Claude Code execution

```text
Claude Code Hook → JSON Event → Simple Dispatcher → Discord Message
```

**Core Files**:
- `main.py` - Event dispatcher and entry point
- `handlers.py` - Event processing logic for all Claude Code events
- `config.py` - Configuration management with channel routing constants
- `discord_client.py` - Discord API client (webhook & bot API support)
- `event_types.py` - TypedDict definitions for all data structures
- `utils.py` - Shared utilities (sanitization, markdown escaping)
- `task_tracker.py` - Task session management for threading features
- `task_storage_improved.py` - Persistent JSON storage with file locking
- `transcript_reader.py` - Subagent conversation extraction for summaries
- `debug_logger.py` - Debug data logging with automatic cleanup

### Full Architecture (Legacy - 8000+ lines)
- **Location**: `src/core/`, `src/handlers/`, `src/formatters/`
- **Design**: Modular with advanced features
- **Entry Point**: `src/main.py`

### Hook Integration
The system integrates with Claude Code via hooks defined in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",  // Optional: filter by tool name (regex supported)
        "hooks": [
          {
            "type": "command",
            "command": "uv run --python 3.13 --no-project python /path/to/src/simple/main.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",  // Regex pattern for multiple tools
        "hooks": [
          {
            "type": "command",
            "command": "uv run --python 3.13 --no-project python /path/to/src/simple/main.py"
          }
        ]
      }
    ],
    "Notification": [  // Events without tool filtering
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --python 3.13 --no-project python /path/to/src/simple/main.py"
          }
        ]
      }
    ],
    "Stop": [  // Session completion event
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --python 3.13 --no-project python /path/to/src/simple/main.py"
          }
        ]
      }
    ]
  }
}
```

**Important Notes**:
- For tool-specific events (PreToolUse/PostToolUse), use `matcher` to filter by tool name
- For non-tool events (Notification/Stop/SubagentStop), omit the `matcher` field
- `matcher` supports regex patterns (e.g., `"Edit|Write"`, `"Notebook.*"`)
- Empty string `""` or omitted `matcher` matches all tools
- `"matcher": "*"` is invalid syntax

## Key Design Patterns

### 1. Fail-Silent Pattern
All code must gracefully handle errors without blocking Claude Code:

```python
try:
    # Discord notification logic
except Exception:
    # Never log errors or raise exceptions
    pass
sys.exit(0)  # Always exit successfully
```

### 2. Pure Python 3.13+ Types
Uses modern type annotations exclusively:

```python
# Use this
def function(data: dict[str, Any]) -> str | None:

# Not this  
def function(data: Dict[str, Any]) -> Optional[str]:
```

### 3. Configuration Priority
1. Environment variables (highest)
2. `~/.claude/.env` file
3. Default values (lowest)

### 4. Event Processing Flow
1. Read JSON from stdin
2. Parse event type from `hook_event_name`
3. Apply filtering (events/tools)
4. Route to appropriate handler
5. Send to Discord (webhook or bot API)

## Configuration Management

### Primary Config File
`~/.claude/.env` - Main configuration for Discord credentials and behavior

### Key Settings
```bash
# Authentication (choose one)
DISCORD_BOT_TOKEN=your_bot_token         # Bot API (recommended)
DISCORD_WEBHOOK_URL=your_webhook_url     # Webhook (simpler)
DISCORD_CHANNEL_ID=your_channel_id       # Required for bot API

# Event Control (granular)
DISCORD_EVENT_PRETOOLUSE=1               # Tool execution start
DISCORD_EVENT_POSTTOOLUSE=1              # Tool execution end
DISCORD_EVENT_NOTIFICATION=1             # System notifications
DISCORD_EVENT_STOP=0                     # Session end
DISCORD_EVENT_SUBAGENT_STOP=1            # Subagent completion

# Tool Filtering
DISCORD_TOOL_READ=0                      # Disable Read tool notifications
DISCORD_TOOL_TASK=1                      # Enable Task tool notifications

# Advanced Features
DISCORD_THREAD_FOR_TASK=1                # Create threads for Task execution
DISCORD_DEBUG=1                          # Enable debug logging

# Channel Routing (new)
DISCORD_CHANNEL_TOOL_ACTIVITY=123456789   # Channel for tool executions
DISCORD_CHANNEL_COMPLETION=987654321      # Channel for completions
DISCORD_CHANNEL_DEFAULT=555555555         # Fallback channel
```

### Channel Routing Feature
The system supports routing notifications to different Discord channels based on event type and tool:

```bash
# Phase 1: Basic channel separation
DISCORD_CHANNEL_TOOL_ACTIVITY=...    # PreToolUse/PostToolUse events
DISCORD_CHANNEL_COMPLETION=...       # Stop/SubagentStop events  
DISCORD_CHANNEL_ALERTS=...           # Errors and warnings
DISCORD_CHANNEL_DEFAULT=...          # Fallback for unmatched events

# Phase 2: Tool-specific routing (overrides event routing)
DISCORD_CHANNEL_BASH_COMMANDS=...    # Bash tool notifications
DISCORD_CHANNEL_FILE_OPERATIONS=...  # Read/Edit/Write notifications
DISCORD_CHANNEL_SEARCH_GREP=...      # Grep/Glob/LS notifications
DISCORD_CHANNEL_AI_INTERACTIONS=...  # Task/WebFetch/TodoWrite
```

## Threading System

The project implements **persistent task tracking** for complex Task tool executions:

### Components
- `TaskTracker` - Session-based task management
- `TaskStorage` - Persistent JSON storage with file locking
- `TranscriptReader` - Extract subagent conversations
- Thread creation for long-running tasks

### Storage Location
- `~/.claude/hooks/task_tracking/tasks.json` - Persistent task data
- `~/.claude/hooks/logs/` - Debug and operation logs

## Testing Strategy

### Test Structure
```text
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Discord API integration
└── feature/        # Specific feature validation
```

### Running Tests
```bash
# Quick unit tests
uv run python -m pytest tests/unit/ -x

# Full test suite with coverage
uv run python -m pytest --cov=src --cov-fail-under=85

# Integration tests (requires Discord credentials)
uv run python -m pytest tests/integration/ -m integration

# Test channel routing specifically
cd src/simple && uv run python test_channel_routing.py
```

## Debugging

### Debug Mode
Set `DISCORD_DEBUG=1` to enable comprehensive logging:

```bash
# Logs location
~/.claude/hooks/logs/simple_notifier_*.log

# Debug data with improved filename format (includes tool names)
# For tool-related events (PreToolUse/PostToolUse):
~/.claude/hooks/debug/{timestamp}_{event}_{tool}_raw_input.json
~/.claude/hooks/debug/{timestamp}_{event}_{tool}_formatted_output.json

# For other events (Stop, Notification, SubagentStop):
~/.claude/hooks/debug/{timestamp}_{event}_raw_input.json
~/.claude/hooks/debug/{timestamp}_{event}_formatted_output.json

# Examples:
# - 20250722_143025_123_PreToolUse_Bash_raw_input.json
# - 20250722_143027_456_PostToolUse_Read_formatted_output.json
# - 20250722_143030_789_Stop_raw_input.json
```

### Common Issues
- **No notifications**: Check credentials in `~/.claude/.env`
- **Import errors**: Ensure Python 3.13+ with `uv run python --version`
- **Hook not firing**: Verify `~/.claude/settings.json` hook configuration

## Security Considerations

### Input Sanitization
All user input is sanitized to prevent log injection attacks:

```python
from utils import sanitize_log_input
safe_input = sanitize_log_input(user_input)  # Removes \n\r characters
```

### Path Validation
File operations validate paths to prevent directory traversal:

```python
# Allowed directories only
allowed_dirs = [(Path.home() / ".claude").resolve(strict=True)]
if not any(os.path.commonpath([file_path, allowed_dir]) == str(allowed_dir) for allowed_dir in allowed_dirs):
    return None
```

### Discord Content Escaping
Discord markdown is escaped to prevent formatting exploits:

```python
from utils import escape_discord_markdown
safe_content = escape_discord_markdown(user_content)
```

### Comprehensive Log Sanitization
All logger calls that include user or API-controlled data use sanitization:

```python
# Exception handling example
logger.error(f"Discord API error: {sanitize_log_input(str(e.code))} - {sanitize_log_input(str(e.reason))}")

# Thread name sanitization example
safe_description = sanitize_log_input(description[:50]).replace('\n', ' ').replace('\r', ' ')
```

## Code Quality Standards

### Type Safety
- **mypy**: Ultra-strict configuration targeting Python 3.13+
- **ruff**: Comprehensive linting with 30+ rule categories
- **pytest**: 85%+ test coverage requirement

### Python Version
- **Minimum**: Python 3.13+
- **Target**: Python 3.14 (pyproject.toml configured for latest features)
- **Features**: Uses `ReadOnly`, `TypeIs`, modern union syntax (`str | None`)

### Import Organization
1. Standard library imports
2. Third-party imports (none in simple architecture)
3. Local imports

Always use absolute imports from project root, except within the `src/simple/` package which uses relative imports for simplicity.