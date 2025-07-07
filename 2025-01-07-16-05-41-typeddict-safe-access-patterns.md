# TypedDict Safe Access Patterns for test_discord_notifier.py

## Problem

Lines 123 and 155 in `test_discord_notifier.py` access the `embeds` field on a `DiscordMessage` TypedDict using bracket notation:

```python
# Line 123
self.assertIn("embeds", result)
embed = result["embeds"][0]  # TypedDict access error

# Line 155
self.assertIn("embeds", result)
embed = result["embeds"][0]  # TypedDict access error
```

The issue is that `DiscordMessage` is defined with `total=False`, making all fields optional:

```python
class DiscordMessage(TypedDict, total=False):
    """Discord message structure."""
    embeds: list[DiscordEmbed]
    content: str  # Optional content for mentions
```

## Solution: Safe Access Patterns

### Option 1: Use `.get()` method with type assertion

```python
# Line 123-124 replacement
self.assertIn("embeds", result)
embeds = result.get("embeds")
self.assertIsNotNone(embeds)
assert embeds is not None  # Type narrowing for mypy
embed = embeds[0]

# Line 155-156 replacement
self.assertIn("embeds", result)
embeds = result.get("embeds")
self.assertIsNotNone(embeds)
assert embeds is not None  # Type narrowing for mypy
embed = embeds[0]
```

### Option 2: Use type guard after assertion

```python
# Add this helper function to the test file
def has_embeds(msg: discord_notifier.DiscordMessage) -> TypeGuard[dict[str, Any]]:
    """Type guard to check if message has embeds."""
    return "embeds" in msg and isinstance(msg.get("embeds"), list)

# Then use it in tests:
self.assertTrue(has_embeds(result))
if has_embeds(result):
    embed = result["embeds"][0]  # Now safe
```

### Option 3: Cast after assertion (simpler but less safe)

```python
from typing import cast

# Line 123-124 replacement
self.assertIn("embeds", result)
embed = cast(list[discord_notifier.DiscordEmbed], result["embeds"])[0]

# Line 155-156 replacement
self.assertIn("embeds", result)
embed = cast(list[discord_notifier.DiscordEmbed], result["embeds"])[0]
```

### Option 4: Update test to use type: ignore (least preferred)

```python
# Line 124
embed = result["embeds"][0]  # type: ignore[typeddict-item]

# Line 156
embed = result["embeds"][0]  # type: ignore[typeddict-item]
```

## Recommended Solution

I recommend **Option 1** as it provides the best balance of type safety and clarity. Here's the complete fix for both occurrences:

```python
# Fix for test_format_event_with_unknown_type (lines 123-124)
self.assertIn("embeds", result)
embeds = result.get("embeds")
self.assertIsNotNone(embeds)
assert embeds is not None  # Type narrowing for mypy
embed = embeds[0]

# Fix for test_format_notification_with_mention (lines 155-156)
self.assertIn("embeds", result)
embeds = result.get("embeds")
self.assertIsNotNone(embeds)
assert embeds is not None  # Type narrowing for mypy
embed = embeds[0]
```

This approach:
1. Uses the safe `.get()` method which returns `None` if the key doesn't exist
2. Asserts that embeds is not None for the test
3. Uses `assert embeds is not None` to narrow the type for mypy
4. Provides clear test failure messages if embeds is missing

## Alternative: Update DiscordMessage Definition

If `format_event` always returns a message with embeds (which it does based on line 1287), you could also consider making `embeds` a required field:

```python
class DiscordMessageWithEmbeds(TypedDict):
    """Discord message that always has embeds."""
    embeds: list[DiscordEmbed]

class DiscordMessage(DiscordMessageWithEmbeds, total=False):
    """Discord message with optional content."""
    content: str
```

However, this would require changes to the main code and might break other uses of `DiscordMessage`.