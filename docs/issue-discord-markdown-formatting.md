# Issue: Discord Markdown Formatting Incorrectly Processing Double Underscores

## Summary
Discord notifications are incorrectly formatting messages that contain double underscores (`__`), interpreting them as markdown underline syntax. This affects messages like commit descriptions that contain flags such as `--no-project`.

## Problem Description
When a Discord notification is sent with text containing `__` (double underscores), Discord's markdown parser interprets this as underline formatting. For example, a message containing:
```
Add environment isolation with --no-project flag
```

Discord may interpret the `__` in `--no-project` as the start of underlined text, causing formatting issues in the displayed message.

## Current Behavior
- The simple architecture implementation in `src/simple/handlers.py` uses `html.escape()` for some fields (file paths, commands, errors)
- However, general text content in descriptions and messages is not escaped for Discord markdown
- This causes visual formatting issues when messages contain markdown special characters

## Root Cause
Discord uses a variant of markdown for message formatting where:
- `*text*` or `_text_` = italic
- `**text**` = bold  
- `__text__` = underline
- `` `text` `` = inline code
- And other markdown syntax

The current implementation doesn't escape these special characters in all text fields.

## Affected Areas
1. Tool descriptions in `format_tool_input()` and `format_tool_response()`
2. General message content in notification handlers
3. Any user-provided text that might contain markdown special characters

## Proposed Solution

### Option 1: Escape All Markdown Characters (Recommended)
Create a utility function to escape Discord markdown characters:

```python
def escape_discord_markdown(text: str) -> str:
    """Escape Discord markdown special characters."""
    # Order matters - escape backslashes first
    text = text.replace("\\", "\\\\")
    text = text.replace("*", "\\*")
    text = text.replace("_", "\\_")
    text = text.replace("`", "\\`")
    text = text.replace("~", "\\~")
    text = text.replace("|", "\\|")
    text = text.replace(">", "\\>")
    text = text.replace("#", "\\#")
    text = text.replace("-", "\\-")
    text = text.replace("=", "\\=")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("(", "\\(")
    text = text.replace(")", "\\)")
    return text
```

Then apply this function to all user-provided text before sending to Discord.

### Option 2: Use Code Blocks for Technical Content
Wrap technical content (like command flags) in inline code blocks:
```python
# Instead of: Add environment isolation with --no-project flag
# Use: Add environment isolation with `--no-project` flag
```

### Option 3: Replace Problematic Characters
Replace double underscores with a safe alternative:
```python
text = text.replace("__", "\\_\\_")
```

## Implementation Notes

1. The escaping should be applied in the handlers before creating the Discord message
2. Be careful not to double-escape already escaped content
3. Consider which fields need escaping (descriptions, titles, field values)
4. Test with various markdown characters to ensure proper display

## Test Cases
Test messages containing:
- `--no-project` (double dash)
- `__init__.py` (double underscore)
- `**kwargs` (double asterisk)
- `~/path/to/file` (tilde)
- `command > output.txt` (greater than)
- Mixed markdown: `Use --flag with __file__ and **options**`

## References
- Discord Markdown Documentation: https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline
- Discord Developer Docs on Message Formatting: https://discord.com/developers/docs/reference#message-formatting