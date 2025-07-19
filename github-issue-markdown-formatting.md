# 🐛 Discord notifications incorrectly format text containing double underscores

## Description
Discord notifications from the simple architecture implementation are experiencing markdown formatting issues when messages contain double underscores (`__`). This affects messages like merge commit descriptions that include command-line flags such as `--no-project`.

## Current Behavior
When a notification contains text like:
```
feat: ✏️ Simple architecture achieving 93% code reduction
- Add environment isolation with --no-project flag
```

Discord interprets `__` as the start of underline formatting, causing the message to display incorrectly.

## Expected Behavior
The text should display exactly as written, without any unintended markdown formatting.

## Root Cause Analysis
The issue occurs because:
1. Discord uses markdown syntax where `__text__` creates underlined text
2. The current implementation in `src/simple/handlers.py` only escapes HTML characters for specific fields (using `html.escape()`)
3. General text content is not escaped for Discord markdown special characters

## Impact
- Visual formatting issues in Discord notifications
- Potential confusion when reading technical content with command-line flags
- Affects any message containing markdown special characters (`*`, `_`, `` ` ``, `~`, `|`, etc.)

## Reproduction Steps
1. Configure Discord notifications using the simple architecture
2. Trigger an event that includes text with double underscores or double dashes
3. Observe the incorrectly formatted message in Discord

## Proposed Fix
Add a Discord markdown escape function in `src/simple/handlers.py`:

```python
def escape_discord_markdown(text: str) -> str:
    """Escape Discord markdown special characters."""
    # Escape backslashes first to avoid double-escaping
    text = text.replace("\\", "\\\\")
    # Escape other markdown characters
    for char in "*_`~|>#-=[]()":
        text = text.replace(char, f"\\{char}")
    return text
```

Then apply this escaping to user-provided content before sending to Discord.

## Affected Files
- `src/simple/handlers.py` - Main location where text formatting occurs
- Potentially `src/simple/discord_client.py` if a centralized approach is preferred

## Priority
Medium - This is a visual issue that affects readability but doesn't break functionality

## Labels
- bug
- simple-architecture
- discord
- formatting