# MyPy Type Error Fixes for discord_notifier.py

## Date: 2025-07-11
## File: src/discord_notifier.py

### Summary

Fixed all 22 mypy type errors in `src/discord_notifier.py` while maintaining full functionality and test compatibility.

### Issues Fixed

1. **Import Conflicts (2 errors)**
   - Removed duplicate imports of `validate_thread_exists` from `src.validators`
   - Removed duplicate import of `ensure_thread_is_usable` from `src.utils_helpers`
   - Kept only the imports from `src.core.thread_manager` which have the correct signatures

2. **Logger Type Incompatibility (5 errors)**
   - Changed `setup_logging` return type to `Union[logging.Logger, AstolfoLogger]`
   - Added logic to extract the internal `logging.Logger` from `AstolfoLogger` when passing to `send_to_discord`
   - Fixed logger type cast for `send_to_discord` function call

3. **Event Data Type Mismatches (3 errors)**
   - Added type casting for event data when calling formatters
   - Used `typing_cast` to convert between different but compatible TypedDict definitions
   - Added specific handling for each event type (PreToolUse, PostToolUse, Notification, Stop, SubagentStop)

4. **None Type Handling (4 errors)**
   - Added checks for `embed["title"]` and `embed["description"]` being None before calculating length
   - Ensured truncate_string is only called with non-None values

5. **DiscordEmbed Type Mismatch (1 error)**
   - Cast the embed from `src.core.http_client.DiscordEmbed` to `src.type_defs.discord.DiscordEmbed`
   - These are structurally identical types from different modules

6. **Truthy Function Checks (4 errors)**
   - Removed redundant `AstolfoLogger and` checks before `isinstance(logger, AstolfoLogger)`
   - The class itself is always truthy, so the check was unnecessary

7. **Unreachable Code (3 errors)**
   - Fixed by updating the logger type system to properly handle Union types

### Code Changes

#### 1. Import Fixes
```python
# Removed from validators import:
# validate_thread_exists,

# Removed from utils_helpers import:
# ensure_thread_is_usable,
```

#### 2. Logger Type Handling
```python
def setup_logging(debug: bool) -> Union[logging.Logger, AstolfoLogger]:
    # Return type now supports both logger types

# When calling send_to_discord:
if isinstance(logger, AstolfoLogger):
    logger_for_send = logger.logger  # Use the internal logger
else:
    logger_for_send = logger
success = send_to_discord(message, config, logger_for_send, http_client, session_id, event_type)
```

#### 3. Event Data Type Casting
```python
# Cast to the expected type for the formatter
from typing import cast as typing_cast
if event_type in ["PreToolUse", "PostToolUse"]:
    from src.formatters.event_formatters import ToolEventData as FormatterToolEventData
    embed = formatter(typing_cast(FormatterToolEventData, event_data), session_id)
elif event_type == "Notification":
    from src.formatters.event_formatters import NotificationEventData as FormatterNotificationEventData
    embed = formatter(typing_cast(FormatterNotificationEventData, event_data), session_id)
# ... etc for other event types
```

#### 4. None Type Safety
```python
# Added None checks before length calculations
if "title" in embed and embed["title"] and len(embed["title"]) > DiscordLimits.MAX_TITLE_LENGTH:
    embed["title"] = truncate_string(embed["title"], DiscordLimits.MAX_TITLE_LENGTH)
```

### Testing

- All unit tests pass (22 tests)
- Basic smoke test passes
- No runtime errors introduced
- Full backward compatibility maintained

### Notes

1. The type system has multiple parallel TypedDict definitions in different modules which are structurally identical but treated as different types by mypy
2. AstolfoLogger wraps a standard logging.Logger but is not a subclass, requiring special handling
3. The event formatter system uses duck typing but mypy requires explicit casts for type safety
4. Future refactoring could consolidate the duplicate type definitions to avoid these casting requirements