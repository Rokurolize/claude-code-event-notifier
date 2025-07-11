# Discord Notifier Dependency Analysis

## Overview

This document analyzes the import dependencies in `/home/ubuntu/claude_code_event_notifier/src/discord_notifier.py` to guide safe module splitting.

## Import Structure

### External Module Imports (with fallbacks)

1. **ThreadStorage**
   - Primary: `from src.thread_storage import ThreadStorage`
   - Fallback: `from thread_storage import ThreadStorage`
   - If unavailable: Creates dummy ThreadStorage class
   - Used by: Thread management functions

2. **AstolfoLogger**
   - Primary: `from src.utils.astolfo_logger import setup_astolfo_logger, AstolfoLogger`
   - Fallback: `from utils.astolfo_logger import setup_astolfo_logger, AstolfoLogger`
   - If unavailable: Sets `ASTOLFO_LOGGER_AVAILABLE = False`
   - Used by: Logging setup

3. **HTTPClient** (REQUIRED)
   - Primary: `from src.core.http_client import HTTPClient`
   - Fallback: `from core.http_client import HTTPClient`
   - If unavailable: Raises ImportError (critical dependency)
   - Used by: All Discord API communication

4. **SessionLogger**
   - Primary: `from src.utils.session_logger import SessionLogger`
   - No fallback
   - If unavailable: Sets `SESSION_LOGGER_AVAILABLE = False`
   - Used by: Event persistence

5. **Formatters Base**
   - Primary: `from src.formatters.base import ...`
   - Fallback: `from formatters.base import ...`
   - If unavailable: Defines functions locally
   - Functions imported:
     - `truncate_string`
     - `format_file_path`
     - `get_truncation_suffix`
     - `add_field`
     - `format_json_field`

6. **Tool Formatters**
   - Primary: `from src.formatters.tool_formatters import ...`
   - Fallback: `from formatters.tool_formatters import ...`
   - If unavailable: Sets `TOOL_FORMATTERS_AVAILABLE = False`
   - Many format functions imported for different tools

## Type Dependencies

### Type Hierarchy

```
BaseField (base TypedDict)
├── TimestampedField extends BaseField
│   └── SessionAware extends BaseField
│       └── BaseEventData extends SessionAware, TimestampedField
│           ├── ToolEventDataBase extends BaseEventData
│           │   ├── PreToolUseEventData
│           │   └── PostToolUseEventData
│           ├── NotificationEventData extends BaseEventData
│           └── StopEventDataBase extends BaseEventData
│               └── StopEventData
│                   └── SubagentStopEventData
└── PathAware extends BaseField

DiscordFooter (TypedDict)
DiscordFieldBase (TypedDict)
└── DiscordField extends DiscordFieldBase

DiscordEmbedBase (TypedDict)
└── DiscordEmbed extends DiscordEmbedBase, TimestampedField

DiscordMessageBase (TypedDict)
├── DiscordMessage extends DiscordMessageBase
└── DiscordThreadMessage extends DiscordMessageBase

Config (multiple inheritance from TypedDict components)
├── DiscordCredentials
├── ThreadConfiguration
├── NotificationConfiguration
└── EventFilterConfiguration
```

### Tool Input Types

```
ToolInputBase (base TypedDict)
├── BashToolInput
├── FileToolInputBase extends ToolInputBase, PathAware
│   ├── ReadToolInput
│   ├── WriteToolInput
│   ├── EditToolInput
│   └── MultiEditToolInput
├── ListToolInput extends ToolInputBase, PathAware
├── SearchToolInputBase extends ToolInputBase
│   ├── GlobToolInput
│   └── GrepToolInput
├── TaskToolInput
└── WebToolInput
```

## Function Dependencies

### Core Function Call Graph

```
main()
├── setup_logging()
├── ConfigLoader.load_config()
├── format_event()
│   └── FormatterRegistry.get_formatter()
│       └── format_pre_tool_use/format_post_tool_use/etc.
├── send_to_discord()
│   ├── _send_stop_or_notification_event()
│   │   └── get_or_create_thread()
│   │       ├── _check_cached_thread()
│   │       ├── _check_persistent_storage()
│   │       ├── _search_discord_for_thread()
│   │       └── _create_new_thread()
│   └── _send_to_thread()
│       └── _split_embed_if_needed()
│           └── _send_single_message()
```

### Key Function Groups

1. **Type Guards** (standalone, no dependencies)
   - `is_tool_event_data()`
   - `is_notification_event_data()`
   - `is_stop_event_data()`
   - `is_bash_tool_input()`
   - `is_file_tool_input()`
   - `is_search_tool_input()`
   - `is_valid_event_type()`
   - `is_bash_tool()`
   - `is_file_tool()`
   - `is_search_tool()`
   - `is_list_tool()`

2. **Validation Classes** (depend on types only)
   - `ConfigValidator`
   - `EventDataValidator`
   - `ToolInputValidator`

3. **Utility Functions** (mostly standalone)
   - `parse_env_file()`
   - `parse_event_list()`
   - `should_process_event()`

4. **Thread Management** (interdependent)
   - `get_or_create_thread()` - main entry point
   - `validate_thread_exists()`
   - `find_existing_thread_by_name()`
   - `ensure_thread_is_usable()`
   - Helper functions: `_check_cached_thread()`, `_check_persistent_storage()`, etc.

5. **Formatting Functions** (depend on types)
   - `format_event()` - dispatcher
   - `format_pre_tool_use()`
   - `format_post_tool_use()`
   - `format_notification()`
   - `format_stop()`
   - `format_subagent_stop()`
   - `format_default()`

6. **Discord Communication** (depend on HTTPClient)
   - `send_to_discord()` - main entry point
   - `_send_stop_or_notification_event()`
   - `_send_to_thread()`
   - `_send_to_regular_channel()`
   - `_split_embed_if_needed()`
   - `_send_single_message()`

## Global Variables

- `SESSION_THREAD_CACHE: dict[str, str]` - Used by thread management
- Constants (EVENT_COLORS, TOOL_EMOJIS, ENV_*, etc.) - Used throughout

## Circular Import Risks

### Low Risk
- Type definitions (TypedDict) - no runtime dependencies
- Type guards - pure functions
- Constants and enums - no dependencies

### Medium Risk
- Formatting functions that might import utility functions
- Thread management functions that use global cache

### High Risk
- None identified - the code already handles import failures gracefully

## Recommended Module Split Order

1. **Phase 1: Constants and Types** (no dependencies)
   - Move all TypedDict definitions
   - Move Enums (EventTypes, ToolNames)
   - Move constants (COLORS, EMOJIS, ENV_*, LIMITS)
   - Move type guards

2. **Phase 2: Validators** (depend only on types)
   - ConfigValidator
   - EventDataValidator
   - ToolInputValidator

3. **Phase 3: Utilities** (minimal dependencies)
   - parse_env_file()
   - parse_event_list()
   - should_process_event()
   - Formatting utilities (if not already in formatters.base)

4. **Phase 4: Core Components** (depend on types and utilities)
   - ConfigLoader
   - FormatterRegistry
   - Event formatting functions

5. **Phase 5: Discord Operations** (depend on HTTPClient and types)
   - Thread management functions
   - Message sending functions

6. **Phase 6: Main Entry Point**
   - main() function
   - Command-line handling

## Special Considerations

1. **Import Fallbacks**: The code already handles missing imports gracefully. Maintain this pattern when splitting.

2. **Global State**: `SESSION_THREAD_CACHE` is used by thread management. Consider making it part of a class or module state.

3. **HTTPClient Dependency**: This is a critical dependency. Any module that sends Discord messages needs access to it.

4. **Logging**: Setup happens early in main(). Consider where logger configuration should live.

5. **Type Annotations**: Many functions use complex type annotations. Ensure all necessary types are imported in each new module.

## Conclusion

The code is well-structured for splitting. The main challenges are:
1. Maintaining the import fallback patterns
2. Handling the global thread cache
3. Ensuring all type dependencies are satisfied

Start with extracting types and constants as they have no dependencies, then work up through the dependency chain.