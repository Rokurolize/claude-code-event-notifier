# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Installation and Setup
```bash
# Install the project in development mode
pip install -e .

# Run the automated hook installer
python src/hook_installer.py

# Configure Discord credentials
cp config/.env.discord.example ~/.claude/hooks/.env.discord
# Edit ~/.claude/hooks/.env.discord with your Discord webhook URL or bot token
```

### Testing
```bash
# Run individual test files
python tests/test_discord_hooks.py
python tests/test_webhook_simple.py
python tests/test_updated_logger.py

# With pytest (if installed)
pip install pytest
pytest tests/
```

### Debugging and Utilities
```bash
# Check hook installation status
python scripts/check_hooks_status.py

# Test Discord integration
python scripts/demo_discord_hooks.py

# Debug Discord hooks
python scripts/debug_discord_hooks.py

# View debug logs (when DISCORD_DEBUG=1)
tail -f ~/.claude/hooks/logs/discord_notifications.log
```

### Code Quality (Optional Development Dependencies)
```bash
# Install development dependencies
pip install black flake8 mypy pytest

# Format code
black src/ tests/ scripts/

# Run linting
flake8 src/ tests/ scripts/

# Type checking
mypy src/ tests/ scripts/
```

## High-Level Architecture

This project integrates Claude Code's hooks system with Discord notifications. It follows an event-driven architecture with clear separation of concerns:

### Core Components

1. **Event Handler** (`src/event_notifier.py`): 
   - Entry point that receives Claude Code hook events via environment variables
   - Routes events to the message formatter and Discord sender
   - Handles logging and error recovery

2. **Message Formatter** (`src/message_formatter.py`):
   - Converts Claude Code events into Discord-compatible embed messages
   - Provides color coding and structured formatting for different event types
   - Handles complex event data structures with graceful fallbacks

3. **Discord Communication** (`src/discord_sender.py`):
   - Supports both webhook (preferred) and bot token authentication
   - Implements retry logic and error handling for Discord API
   - Manages asynchronous communication with Discord servers

4. **Hook Installer** (`src/hook_installer.py`):
   - Automated setup utility that configures Claude Code's settings.json
   - Creates necessary directories and copies required files
   - Validates existing configurations before modification

### Event Flow

1. Claude Code triggers a hook event (PreToolUse, PostToolUse, Notification, Stop, SubagentStop)
2. The event data is passed via stdin to `event_notifier.py`
3. Event data is parsed and formatted into Discord embeds by `message_formatter.py`
4. `discord_sender.py` delivers the formatted message to Discord
5. Errors are logged to `~/.claude/hooks/logs/discord_notifications.log` when debug mode is enabled

### Key Design Decisions

- **No External Dependencies**: Uses only Python standard library for maximum compatibility
- **Modular Architecture**: Each component has a single responsibility for easy testing and maintenance
- **Flexible Authentication**: Supports both webhooks (simpler) and bot tokens (more features)
- **Comprehensive Error Handling**: Fails gracefully without disrupting Claude Code operations
- **Debug Mode**: Detailed logging available via DISCORD_DEBUG environment variable

### Configuration Storage

- Discord credentials: `~/.claude/hooks/.env.discord`
- Claude Code hooks: `~/.claude/settings.json`
- Log files: `~/.claude/hooks/logs/`
- Script installation: `~/.claude/hooks/`

This architecture ensures reliable event delivery while maintaining clean separation between Claude Code's operation and Discord notification system.