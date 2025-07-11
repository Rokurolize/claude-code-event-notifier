# Phase 4 Extraction Plan: discord_notifier.py Analysis

## File Overview
- **Total Lines**: 2,386
- **Status**: Heavily integrated monolithic file requiring careful extraction

## Major Components and Line Counts

### 1. Imports and Type Definitions (Lines 1-401)
- **Lines**: 401
- **Content**: 
  - Python version check
  - Module imports with fallback handling
  - Type definitions (now mostly imported from other modules)
  - Constants and enums
- **Extraction Strategy**: Already mostly extracted to separate modules

### 2. Utility Functions (Lines 402-749)
- **Lines**: 348
- **Key Functions**:
  - `parse_env_file()` - Environment file parsing (lines 482-538)
  - `parse_event_list()` - Event list parsing (lines 540-578)
  - `should_process_event()` - Event filtering logic (lines 580-622)
  - `truncate_string()` - String truncation (fallback if import fails)
  - `format_file_path()` - File path formatting (fallback if import fails)
  - `get_truncation_suffix()` - Truncation suffix (fallback if import fails)
  - `add_field()` - Discord field addition (fallback if import fails)
  - `format_json_field()` - JSON field formatting (fallback if import fails)
- **Extraction Strategy**: Move to `src/utils/discord_utils.py` or enhance existing utils

### 3. Thread Management Functions (Lines 750-1192)
- **Lines**: 443
- **Key Functions**:
  - `validate_thread_exists()` - Thread validation
  - `_find_best_matching_thread()` - Thread matching logic
  - `_search_threads_with_error_handling()` - Thread search with error handling
  - `find_existing_thread_by_name()` - Find thread by name
  - `_check_thread_state()` - Check if thread is archived/locked
  - `_try_unarchive_thread()` - Unarchive thread
  - `_check_cached_thread()` - Check in-memory cache
  - `_check_persistent_storage()` - Check SQLite storage
  - `_store_thread_in_storage()` - Store thread in SQLite
  - `_search_discord_for_thread()` - Search Discord API
  - `_handle_forum_channel_thread()` - Forum channel handling
  - `_create_text_channel_thread()` - Text channel thread creation
  - `_create_new_thread()` - Generic thread creation
  - `get_or_create_thread()` - Main thread management function
- **Extraction Strategy**: Already partially moved to `thread_manager.py`, complete the migration

### 4. ConfigLoader Class (Lines 1194-1305)
- **Lines**: 112
- **Methods**:
  - `_get_default_config()` - Default configuration
  - `_load_from_env()` - Load from environment
  - `_validate_config()` - Configuration validation
  - `load()` - Main loading method
- **Extraction Strategy**: Move to `src/core/config.py` (enhance existing module)

### 5. Logging Setup (Lines 1307-1342)
- **Lines**: 36
- **Function**: `setup_logging()` - Configure logging
- **Extraction Strategy**: Move to `src/utils/logging_utils.py`

### 6. Event Formatters (Lines 1495-1819)
- **Lines**: 325
- **Key Functions**:
  - `format_pre_tool_use()` - Pre-tool use formatting
  - `format_read_operation_post_use()` - Read operation formatting
  - `format_task_post_use()` - Task formatting
  - `format_web_fetch_post_use()` - Web fetch formatting
  - `format_post_tool_use()` - Post-tool use formatting
  - `format_notification()` - Notification formatting
  - `format_stop()` - Stop event formatting
  - `format_subagent_stop()` - Subagent stop formatting
  - `format_default_impl()` - Default formatting implementation
  - `format_default()` - Default formatting wrapper
- **Extraction Strategy**: Already partially in `event_formatters.py`, complete migration

### 7. FormatterRegistry Class (Lines 1821-1844)
- **Lines**: 24
- **Methods**:
  - `__init__()` - Initialize registry
  - `get_formatter()` - Get formatter for event type
  - `register()` - Register new formatter
- **Extraction Strategy**: Move to `src/formatters/registry.py`

### 8. Event Processing Functions (Lines 1845-1895)
- **Lines**: 51
- **Function**: `format_event()` - Main event formatting dispatcher
- **Extraction Strategy**: Move to `src/handlers/event_processor.py`

### 9. Message Sending Functions (Lines 1896-2189)
- **Lines**: 294
- **Key Functions**:
  - `_send_stop_or_notification_event()` - Special event handling
  - `_send_to_thread()` - Send to thread
  - `_send_to_regular_channel()` - Send to regular channel
  - `send_to_discord()` - Main sending function
  - `_split_embed_if_needed()` - Split large embeds
  - `_send_single_message()` - Send single message
- **Extraction Strategy**: Already partially in `discord_sender.py`, complete migration

### 10. Main Function (Lines 2197-2386)
- **Lines**: 190
- **Function**: `main()` - Entry point and orchestration
- **Extraction Strategy**: Keep in discord_notifier.py but simplify by using extracted modules

## Extraction Priority

1. **High Priority** (Most independent, easiest to extract):
   - ConfigLoader → `src/core/config.py`
   - FormatterRegistry → `src/formatters/registry.py`
   - Logging setup → `src/utils/logging_utils.py`
   - Utility functions → `src/utils/discord_utils.py`

2. **Medium Priority** (Some dependencies):
   - Event formatters → Complete migration to `event_formatters.py`
   - Event processing → `src/handlers/event_processor.py`

3. **Low Priority** (Heavy dependencies):
   - Thread management → Complete migration to `thread_manager.py`
   - Message sending → Complete migration to `discord_sender.py`

4. **Final Step**:
   - Refactor main() to use all extracted modules
   - Remove duplicated code
   - Update imports

## Risks and Considerations

1. **Import Dependencies**: Many modules have circular import risks
2. **Global State**: SESSION_THREAD_CACHE and loggers need careful handling
3. **Fallback Logic**: Many functions have fallback implementations if imports fail
4. **Type Definitions**: Already mostly extracted but need to ensure consistency
5. **Testing**: Each extraction needs comprehensive testing

## Recommended Approach

1. Start with high-priority, independent components
2. Create comprehensive tests before extraction
3. Extract one component at a time
4. Run full test suite after each extraction
5. Update imports incrementally
6. Keep fallback logic until all extractions are complete

## Success Metrics

- [ ] File reduced from 2,386 lines to < 500 lines
- [ ] All tests passing after each extraction
- [ ] No circular imports
- [ ] Clear module boundaries
- [ ] Improved maintainability and testability