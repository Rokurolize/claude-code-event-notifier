# Discord Mention Enhancement - Test Plan

## Change Summary
Added user mentions to Stop events in addition to the existing Notification event mentions.

## Code Changes

### 1. Updated `src/discord_notifier.py` (lines 1286-1294)
- Modified the mention logic to include both `EventTypes.NOTIFICATION.value` and `EventTypes.STOP.value`
- Added conditional message text:
  - Notification events: Use the event's message
  - Stop events: Use "Session ended"

### 2. Updated `CLAUDE.md` documentation
- Changed "Notification events" to "Notification and Stop events" in user mention configuration
- Updated the note to reflect that mentions work for both event types

## Test Cases

### Test 1: Stop Event with Mention
1. Configure `DISCORD_MENTION_USER_ID` in `.env.discord`
2. Run a Claude Code session that triggers a Stop event
3. **Expected**: Discord message should include `<@USER_ID> Session ended` above the embed

### Test 2: Stop Event without Mention
1. Remove or comment out `DISCORD_MENTION_USER_ID` configuration
2. Run a Claude Code session that triggers a Stop event
3. **Expected**: Discord message should only contain the embed, no mention

### Test 3: Notification Event (Regression Test)
1. Configure `DISCORD_MENTION_USER_ID` in `.env.discord`
2. Trigger a Notification event
3. **Expected**: Discord message should include mention with notification message (existing behavior)

## Configuration Example
```bash
# In ~/.claude/hooks/.env.discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK
DISCORD_MENTION_USER_ID=123456789012345678  # Your Discord user ID
```