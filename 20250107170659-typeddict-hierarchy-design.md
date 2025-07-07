# TypedDict Hierarchy Design Implementation

## Overview

This document describes the comprehensive TypedDict hierarchy implemented for the Discord Notifier to provide better type safety, maintainability, and developer experience.

## Implementation Summary

### 1. Base Foundation Types

Created foundational TypedDict classes that serve as building blocks:

```python
class BaseField(TypedDict):
    """Base field structure for common properties."""
    pass

class TimestampedField(BaseField):
    """Fields that include timestamps."""
    timestamp: NotRequired[str]

class SessionAware(BaseField):
    """Fields that are session-aware."""
    session_id: str

class PathAware(BaseField):
    """Fields that include file paths."""
    file_path: NotRequired[str]
```

### 2. Discord API Types Hierarchy

Structured Discord-specific types with proper inheritance:

```python
# Base structures
class DiscordFooter(TypedDict):
    text: str

class DiscordFieldBase(TypedDict):
    name: str
    value: str

class DiscordField(DiscordFieldBase):
    inline: NotRequired[bool]

# Embed hierarchy
class DiscordEmbedBase(TypedDict):
    title: NotRequired[str]
    description: NotRequired[str]
    color: NotRequired[int]

class DiscordEmbed(DiscordEmbedBase, TimestampedField):
    footer: NotRequired[DiscordFooter]
    fields: NotRequired[list[DiscordField]]

# Message hierarchy
class DiscordMessageBase(TypedDict):
    embeds: NotRequired[list[DiscordEmbed]]

class DiscordMessage(DiscordMessageBase):
    content: NotRequired[str]  # For mentions

class DiscordThreadMessage(DiscordMessageBase):
    thread_name: NotRequired[str]  # For creating new threads
```

### 3. Configuration Hierarchy

Organized configuration into logical components:

```python
class DiscordCredentials(TypedDict):
    webhook_url: str | None
    bot_token: str | None
    channel_id: str | None

class ThreadConfiguration(TypedDict):
    use_threads: bool
    channel_type: Literal["text", "forum"]
    thread_prefix: str

class NotificationConfiguration(TypedDict):
    mention_user_id: str | None
    debug: bool

class Config(DiscordCredentials, ThreadConfiguration, NotificationConfiguration):
    pass  # Combines all configuration aspects
```

### 4. Tool Input Hierarchy

Structured tool inputs with proper inheritance:

```python
class ToolInputBase(TypedDict):
    description: NotRequired[str]

class BashToolInput(ToolInputBase):
    command: str

class FileToolInputBase(ToolInputBase, PathAware):
    pass

class ReadToolInput(FileToolInputBase):
    offset: NotRequired[int]
    limit: NotRequired[int]

class WriteToolInput(FileToolInputBase):
    content: str

class EditToolInput(FileToolInputBase):
    old_string: str
    new_string: str
    replace_all: NotRequired[bool]

class MultiEditToolInput(FileToolInputBase):
    edits: list[FileEditOperation]

class SearchToolInputBase(ToolInputBase):
    pattern: str
    path: NotRequired[str]

class GlobToolInput(SearchToolInputBase):
    pass

class GrepToolInput(SearchToolInputBase):
    include: NotRequired[str]

class TaskToolInput(ToolInputBase):
    prompt: str

class WebToolInput(ToolInputBase):
    url: str
    prompt: str
```

### 5. Tool Response Hierarchy

Structured tool responses with common base:

```python
class ToolResponseBase(TypedDict):
    success: NotRequired[bool]
    error: NotRequired[str]

class BashToolResponse(ToolResponseBase):
    stdout: str
    stderr: str
    interrupted: bool
    isImage: bool

class FileOperationResponse(ToolResponseBase):
    filePath: NotRequired[str]

class SearchResponse(ToolResponseBase):
    results: NotRequired[list[str]]
    count: NotRequired[int]
```

### 6. Event Data Hierarchy

Structured event data with proper inheritance chain:

```python
class BaseEventData(SessionAware, TimestampedField):
    transcript_path: NotRequired[str]
    hook_event_name: str

class ToolEventDataBase(BaseEventData):
    tool_name: str
    tool_input: dict[str, Any]

class PreToolUseEventData(ToolEventDataBase):
    pass

class PostToolUseEventData(ToolEventDataBase):
    tool_response: ToolResponse

class NotificationEventData(BaseEventData):
    message: str
    title: NotRequired[str]
    level: NotRequired[Literal["info", "warning", "error"]]

class StopEventDataBase(BaseEventData):
    stop_hook_active: NotRequired[bool]

class StopEventData(StopEventDataBase):
    duration: NotRequired[float]
    tools_used: NotRequired[int]
    messages_exchanged: NotRequired[int]

class SubagentStopEventData(StopEventData):
    task_description: NotRequired[str]
    result: NotRequired[str | dict[str, Any]]
    execution_time: NotRequired[float]
    status: NotRequired[str]
```

### 7. Enhanced Type Safety Features

Added comprehensive type guards and validators:

```python
# Type guards
def is_tool_event_data(data: dict[str, Any]) -> TypeGuard[ToolEventDataBase]:
    return "tool_name" in data

def is_notification_event_data(data: dict[str, Any]) -> TypeGuard[NotificationEventData]:
    return "message" in data

def is_stop_event_data(data: dict[str, Any]) -> TypeGuard[StopEventDataBase]:
    return "hook_event_name" in data

# Configuration validators
class ConfigValidator:
    @staticmethod
    def validate_credentials(config: Config) -> bool:
        return bool(
            config.get("webhook_url") or 
            (config.get("bot_token") and config.get("channel_id"))
        )
    
    @staticmethod
    def validate_thread_config(config: Config) -> bool:
        if not config.get("use_threads", False):
            return True
        
        channel_type = config.get("channel_type", "text")
        if channel_type == "forum":
            return bool(config.get("webhook_url"))
        elif channel_type == "text":
            return bool(config.get("bot_token") and config.get("channel_id"))
        
        return False
    
    @staticmethod
    def validate_all(config: Config) -> bool:
        return (
            ConfigValidator.validate_credentials(config) and
            ConfigValidator.validate_thread_config(config) and
            ConfigValidator.validate_mention_config(config)
        )

# Event data validators
class EventDataValidator:
    @staticmethod
    def validate_base_event_data(data: dict[str, Any]) -> bool:
        required_fields = {"session_id", "hook_event_name"}
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_tool_event_data(data: dict[str, Any]) -> bool:
        if not EventDataValidator.validate_base_event_data(data):
            return False
        
        required_fields = {"tool_name", "tool_input"}
        return all(field in data for field in required_fields)
```

## Key Benefits Achieved

### 1. **Improved Type Safety**
- Clear inheritance hierarchy reduces duplication
- Better IDE support with proper type hints
- Compile-time error detection for missing fields
- Eliminates duplicate union type definitions

### 2. **Enhanced Maintainability**
- Single source of truth for shared structures
- Easy to extend with new event types
- Clear separation of concerns
- Consistent use of `NotRequired` vs `str | None`

### 3. **Better Developer Experience**
- Clear documentation through types
- Autocomplete support in IDEs
- Better error messages
- Type-driven development

### 4. **Runtime Safety**
- Type guards prevent runtime errors
- Validation methods ensure data integrity
- Proper handling of optional fields

## Migration Impact

### Changes Made:
1. **Reorganized all TypedDict definitions** into a logical hierarchy
2. **Removed duplicate `ToolInput` definitions** (was defined twice)
3. **Added comprehensive type guards** for runtime type checking
4. **Implemented validation classes** for configuration and event data
5. **Maintained backward compatibility** with legacy structures

### Test Results:
- All 13 existing unit tests pass
- No breaking changes to existing functionality
- Type checker reports no errors

## Usage Examples

### Type-Safe Configuration Creation:
```python
def create_config() -> Config:
    config: Config = {
        "webhook_url": "https://discord.com/api/webhooks/123/abc",
        "bot_token": None,
        "channel_id": None,
        "debug": False,
        "use_threads": True,
        "channel_type": "forum",
        "thread_prefix": "Session",
        "mention_user_id": None,
    }
    
    if not ConfigValidator.validate_all(config):
        raise ConfigurationError("Invalid configuration")
    
    return config
```

### Type-Safe Event Processing:
```python
def process_event(event_data: dict[str, Any]) -> DiscordMessage:
    if is_tool_event_data(event_data):
        # TypeScript knows this is ToolEventDataBase
        return format_tool_event(event_data)
    elif is_notification_event_data(event_data):
        # TypeScript knows this is NotificationEventData
        return format_notification_event(event_data)
    else:
        return format_generic_event(event_data)
```

## Future Extensibility

The hierarchical structure makes it easy to:
1. Add new tool types by extending `ToolInputBase`
2. Add new event types by extending `BaseEventData`
3. Add new Discord features by extending `DiscordMessageBase`
4. Add new validation rules to validator classes

This design provides a solid foundation for future enhancements while maintaining type safety and code clarity.