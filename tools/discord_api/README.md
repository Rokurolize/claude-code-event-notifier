# Discord API Tools

Unified collection of Discord API testing, validation, and analysis tools.

## 🎯 Overview

This directory contains all Discord API development and testing utilities, organized for easy discovery and maintenance.

## 📁 Tool Structure

```
tools/discord_api/
├── discord_api_basic_checker.py      # Basic access & permissions checker
├── discord_api_advanced_validator.py # Advanced validation & statistics
├── discord_api_message_fetcher.py    # Message fetching & analysis
├── discord_api_test_runner.py        # Comprehensive test suite
└── shared/                           # Common libraries
    ├── __init__.py                   # Package exports
    ├── config.py                     # Configuration utilities
    └── utils.py                      # API utilities
```

## 🔧 Tools Description

### 1. Basic Checker (`discord_api_basic_checker.py`)
Simple tool for verifying Discord API access and permissions.

**Usage:**
```bash
python discord_api_basic_checker.py [--channel-id CHANNEL_ID] [--thread-id THREAD_ID]
```

**Features:**
- Bot authentication check
- Channel access verification
- Thread access testing
- Archived threads listing
- Comprehensive permissions analysis

### 2. Advanced Validator (`discord_api_advanced_validator.py`)
Comprehensive validation tool with statistics and repeated verification.

**Usage:**
```bash
python discord_api_advanced_validator.py [--channel-id CHANNEL_ID] [--iterations 3] [--delay 2] [--limit 50]
```

**Features:**
- Message retrieval and analysis
- Discord Notifier message detection
- Repeated verification for reliability testing
- Health analysis and statistics
- Real-time monitoring capabilities

### 3. Message Fetcher (`discord_api_message_fetcher.py`)
Tool for fetching and analyzing specific Discord messages.

**Usage:**
```bash
# Using channel and message IDs
python discord_api_message_fetcher.py --channel-id CHANNEL_ID --message-id MESSAGE_ID

# Using Discord URL
python discord_api_message_fetcher.py --url "https://discord.com/channels/guild/channel/message"

# Focus on Discord Notifier messages
python discord_api_message_fetcher.py --url URL --analyze-notifier
```

**Features:**
- Message structure analysis
- Embed content examination
- Discord Notifier message detection
- JSON export for detailed analysis
- URL parsing for convenience

### 4. Test Runner (`discord_api_test_runner.py`)
Comprehensive test suite for full Discord API functionality verification.

**Usage:**
```bash
python discord_api_test_runner.py [--channel-id CHANNEL_ID] [--quick]
```

**Features:**
- Configuration validation
- Authentication testing
- Permission verification
- Message retrieval testing
- Event simulation testing
- Rate limiting behavior analysis
- Comprehensive reporting

## ⚙️ Configuration

All tools use unified configuration from:

1. **Environment variables:**
   - `DISCORD_BOT_TOKEN` - Discord bot token
   - `DISCORD_CHANNEL_ID` - Target channel ID

2. **Config file:** `~/.claude/.env`
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_CHANNEL_ID=your_channel_id_here
   ```

## 🔍 Quick Discovery

**Find all Discord API tools:**
```bash
find . -name "*discord_api*.py"
# or
ls **/discord_api*.py
```

**Search pattern:** `**/discord_api*.py`

## 📋 Common Use Cases

### Quick Health Check
```bash
python discord_api_basic_checker.py
```

### Comprehensive Analysis
```bash
python discord_api_advanced_validator.py --iterations 5
```

### Message Investigation
```bash
python discord_api_message_fetcher.py --url "DISCORD_MESSAGE_URL" --analyze-notifier
```

### Full Test Suite
```bash
python discord_api_test_runner.py
```

## 🛠️ Development

### Shared Libraries

All tools use common libraries from the `shared/` directory:

- **`config.py`** - Unified configuration loading
- **`utils.py`** - Common API request utilities
- **`__init__.py`** - Package exports

### Adding New Tools

1. Create `discord_api_your_tool.py` in this directory
2. Import from `shared` for common functionality
3. Follow the existing CLI argument patterns
4. Update this README

### Error Handling

All tools implement:
- Graceful error handling
- Detailed error messages with Discord API error codes
- Non-blocking execution (won't crash Claude Code)
- Appropriate exit codes for scripting

## 🔗 Integration

These tools integrate with the main Discord Event Notifier system:

- **Configuration**: Shares config with main notifier
- **Event Testing**: Can simulate events through simple architecture
- **Message Analysis**: Can analyze notifier-generated messages
- **Health Monitoring**: Validates notifier functionality

## 📈 Migration Notes

This directory consolidates and improves upon previous scattered tools:

- **Migrated from:** `utils/check_discord_access.py`
- **Migrated from:** `src/utils/discord_api_validator.py`  
- **Migrated from:** `fetch_specific_message.py`
- **Consolidated:** Various test scripts into unified test runner

**Old files are preserved until migration is fully verified.**