# Formatter Registry Mypy Fix

## Date: 2025-07-12
## Author: Assistant

## Problem

The `src/formatters/registry.py` file was using explicit `Any` types which are not allowed in mypy strict mode. The main issues were:

1. Using `Callable[[Any, str], DiscordEmbed]` for formatter functions
2. Type mismatches between different formatter functions that accept specific event types
3. Lambda expressions with implicit Any types

## Solution

### 1. Introduced a Protocol for Type Safety

Created an `EventFormatter` protocol that defines the interface for all formatter functions:

```python
class EventFormatter(Protocol):
    """Protocol for event formatter functions."""
    
    def __call__(self, event_data: EventData, session_id: str) -> DiscordEmbed:
        """Format event data into Discord embed."""
        ...
```

### 2. Used EventData Union Type

Imported and used the `EventData` union type which encompasses all possible event data types:

```python
EventData = (
    PreToolUseEventData
    | PostToolUseEventData
    | NotificationEventData
    | StopEventData
    | SubagentStopEventData
    | dict[str, str | int | float | bool]
)
```

### 3. Created Helper Function for Default Formatter

Replaced the lambda with a proper function to avoid Any type inference:

```python
def _create_default_formatter(event_type: str) -> EventFormatter:
    """Create a default formatter for unknown event types."""
    def formatter(event_data: EventData, session_id: str) -> DiscordEmbed:
        data_dict = cast(dict[str, str | int | float | bool], event_data)
        return cast(DiscordEmbed, format_default(data_dict, session_id))
    
    return formatter
```

### 4. Updated Registry Implementation

Changed the registry to use the Protocol type:

```python
class FormatterRegistry:
    def __init__(self) -> None:
        self._formatters: dict[str, EventFormatter] = {
            # formatter mappings with casts
        }
    
    def get_formatter(self, event_type: str) -> EventFormatter:
        if event_type in self._formatters:
            return self._formatters[event_type]
        return _create_default_formatter(event_type)
    
    def register(self, event_type: str, formatter: EventFormatter) -> None:
        self._formatters[event_type] = formatter
```

## Results

- ✅ All mypy errors in `registry.py` resolved
- ✅ No explicit Any types used
- ✅ Type safety maintained through Protocol pattern
- ✅ Functionality preserved and tested

## Technical Details

The Protocol pattern allows us to define a common interface for all formatters while still allowing each formatter to accept its specific event type (covariance). This works because:

1. All specific event types are part of the EventData union
2. The Protocol defines the broadest acceptable interface
3. Individual formatters can be more specific in their actual implementation
4. Type casting is used safely where needed to bridge between general and specific types

This approach maintains both type safety and flexibility in the formatter system.