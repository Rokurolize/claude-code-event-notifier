# Claude Code Event Notifier

A Python module that sends Claude Code hook events to Discord for real-time monitoring and notifications.

## Overview

The Claude Code Event Notifier integrates with Claude Code's hooks system to capture and forward events to Discord channels. This allows teams to monitor Claude Code's activities, tool usage, and session lifecycle in real-time through Discord notifications.

## Features

- **Real-time Notifications**: Sends Claude Code events to Discord as they happen
- **Rich Embed Messages**: Formats events with color-coded embeds for easy visibility
- **Multiple Event Types**: Supports PreToolUse, PostToolUse, Notification, Stop, and SubagentStop events
- **Flexible Authentication**: Works with both Discord webhooks (recommended) and bot tokens
- **Detailed Logging**: Comprehensive debug logging for troubleshooting
- **Clean Architecture**: Modular design with separated concerns for easy maintenance

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/your-username/claude-code-event-notifier.git
cd claude-code-event-notifier
```

2. Install the module:
```bash
pip install -e .
```

3. Run the hook installer:
```bash
python src/hook_installer.py
```

### Manual Installation

If you prefer manual setup:

1. Copy the notifier script to Claude's hooks directory:
```bash
cp src/event_notifier.py ~/.claude/hooks/claude_event_notifier.py
cp src/message_formatter.py ~/.claude/hooks/
cp src/discord_sender.py ~/.claude/hooks/
```

2. Make the script executable:
```bash
chmod +x ~/.claude/hooks/claude_event_notifier.py
```

3. Configure Claude Code's settings.json (see Configuration section)

## Configuration

### Discord Setup

Create a `.env.discord` file in `~/.claude/hooks/` with your Discord credentials:

```bash
# Option 1: Discord Webhook (Recommended)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Option 2: Discord Bot
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here

# Optional: Enable debug logging
DISCORD_DEBUG=1
```

### Claude Code Hooks Configuration

The installer automatically configures your `~/.claude/settings.json`. For manual configuration, add:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "CLAUDE_HOOK_EVENT=PreToolUse python3 ~/.claude/hooks/claude_event_notifier.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "CLAUDE_HOOK_EVENT=PostToolUse python3 ~/.claude/hooks/claude_event_notifier.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "CLAUDE_HOOK_EVENT=Notification python3 ~/.claude/hooks/claude_event_notifier.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "CLAUDE_HOOK_EVENT=Stop python3 ~/.claude/hooks/claude_event_notifier.py"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "CLAUDE_HOOK_EVENT=SubagentStop python3 ~/.claude/hooks/claude_event_notifier.py"
          }
        ]
      }
    ]
  }
}
```

## Usage

Once installed and configured, Claude Code will automatically send notifications to your Discord channel for:

- **PreToolUse**: Before any tool is executed
- **PostToolUse**: After tool execution completes
- **Notification**: System notifications
- **Stop**: When a Claude session ends
- **SubagentStop**: When a subagent completes

### Notification Format

Each notification includes:
- Event type and timestamp
- Tool name and description (for tool events)
- Execution details and results
- Color-coded embeds for quick identification

## Development

### Project Structure

```
claude_code_event_notifier/
├── src/
│   ├── __init__.py
│   ├── event_notifier.py      # Main entry point
│   ├── message_formatter.py   # Discord message formatting
│   ├── discord_sender.py      # Discord API communication
│   └── hook_installer.py      # Installation utility
├── tests/                      # Test files
├── scripts/                    # Utility scripts
├── config/
│   └── .env.discord.example   # Example configuration
├── setup.py
├── requirements.txt
└── README.md
```

### Testing

Run tests from the project root:

```bash
python tests/test_discord_hooks.py
python tests/test_webhook_simple.py
```

### Debug Mode

Enable debug logging by setting `DISCORD_DEBUG=1` in your `.env.discord` file. Logs are written to:
- `/home/ubuntu/.claude/hooks/logs/discord_notifications.log`

## Troubleshooting

### Common Issues

1. **No notifications appearing**
   - Check Discord credentials in `.env.discord`
   - Verify webhook URL or bot token is valid
   - Enable debug mode and check logs
   - Ensure Claude Code has been restarted after configuration

2. **403 Forbidden errors**
   - Webhook URL may be expired - create a new one
   - Bot token may lack permissions - check Discord bot settings

3. **Hooks not triggering**
   - Verify `settings.json` is properly formatted
   - Use empty string `""` for matcher, not `"*"`
   - Check file permissions on hook scripts

### Log Locations

- Debug logs: `~/.claude/hooks/logs/discord_notifications.log`
- Claude Code logs: Check Claude's standard output

## Security Considerations

- Store Discord credentials in `~/.claude/hooks/.env.discord` with 600 permissions
- Never commit `.env.discord` files to version control
- Use webhook URLs when possible (more secure than bot tokens)
- Regularly rotate credentials

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow the existing code style
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built for the Claude Code community to enhance visibility and collaboration through Discord integrations.