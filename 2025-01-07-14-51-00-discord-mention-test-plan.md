# Discord Mention Feature Test Plan

## Overview
This test plan validates that Windows Discord notifications properly display both the user mention and the notification message when a user is mentioned in a Notification event.

## Feature Description
- **Previous behavior**: Windows notifications only showed "@username"
- **New behavior**: Windows notifications show "@username {message content}"
- **Implementation**: Modified `format_event()` in `discord_notifier.py` to include message after mention

## Prerequisites

### 1. Discord Configuration
Ensure one of the following is configured:
- `~/.claude/hooks/.env.discord` file with Discord credentials
- Environment variables set for Discord

### 2. User ID Configuration
```bash
# Required for mention testing
export DISCORD_MENTION_USER_ID=YOUR_DISCORD_USER_ID
```

To find your Discord User ID:
1. Enable Developer Mode in Discord: Settings → Advanced → Developer Mode
2. Right-click on your username in any channel
3. Select "Copy User ID"

### 3. Debug Mode (Optional)
```bash
export DISCORD_DEBUG=1  # Enable debug logging
```

## Test Execution

### Method 1: Comprehensive Test Script
```bash
# Run all notification tests including mention variants
python3 test.py
```

This includes:
- Standard notification with mention
- Short message ("Quick test")
- Long message with emojis (build status)
- Message with special characters
- Empty message (tests default behavior)

### Method 2: Mention-Specific Test Script
```bash
# Set your Discord user ID
export DISCORD_MENTION_USER_ID=123456789012345678

# Run mention-specific tests
python3 test_mentions.py
```

This script tests:
1. Standard notification with mention
2. Short messages
3. Long messages with emojis
4. Messages with Discord formatting
5. Empty/missing messages
6. Multi-line messages
7. Notifications without mention configuration

### Method 3: Manual Testing
```bash
# Create a test event file
cat > test_notification.json << 'EOF'
{
  "session_id": "manual-test-123",
  "message": "This is a manual test of the mention feature"
}
EOF

# Send the notification
export CLAUDE_HOOK_EVENT=Notification
export DISCORD_MENTION_USER_ID=YOUR_USER_ID
python3 src/discord_notifier.py < test_notification.json
```

## Verification Steps

### 1. Windows Desktop Notification
- [ ] Notification popup appears on Windows
- [ ] Popup shows: "@YourUsername {message}"
- [ ] Click on notification opens Discord to the correct message

### 2. Discord Application
- [ ] Message appears in configured channel/thread
- [ ] Content field shows: `<@USER_ID> {message}`
- [ ] Embed still contains full formatted message
- [ ] User receives mention notification (red badge)

### 3. Mobile Discord App
- [ ] Push notification shows mention and message preview
- [ ] Notification is actionable (tap to open)

### 4. Edge Cases
- [ ] Very long messages display correctly (no truncation in content)
- [ ] Special characters are properly escaped
- [ ] Unicode/emoji display correctly
- [ ] Multi-line messages maintain formatting

## Expected Results

### With Mention Configuration
```json
{
  "content": "<@123456789012345678> Test notification message",
  "embeds": [{
    "title": "📢 Notification",
    "description": "**Message:** Test notification message\n...",
    "color": 16753920
  }]
}
```

### Without Mention Configuration
```json
{
  "embeds": [{
    "title": "📢 Notification", 
    "description": "**Message:** Test notification message\n...",
    "color": 16753920
  }]
}
```

## Troubleshooting

### No Windows Notification
1. Check Discord notification settings
2. Ensure Discord is running
3. Verify Windows notification settings
4. Check Discord focus state

### Mention Not Working
1. Verify `DISCORD_MENTION_USER_ID` is set correctly
2. Ensure it's a Notification event (not other event types)
3. Check debug logs: `~/.claude/hooks/logs/discord_notifier_*.log`

### Message Not Appearing
1. Check for JSON encoding issues
2. Verify message field exists in event data
3. Test with simple ASCII message first

## Rollback Plan
If issues occur, revert commit `3f0e59b`:
```bash
git revert 3f0e59b
```

## Success Criteria
- [x] Unit tests pass (`test_format_notification_with_mention`)
- [ ] Windows notifications show full "@user message" format
- [ ] No regression in non-mention notifications
- [ ] All test cases in `test_mentions.py` pass
- [ ] User feedback confirms improved visibility