# MyPy Error Fix Plan
Generated: 2025-07-11 17:15:00

## Executive Summary

Total mypy errors: ~1,180 errors across 25 files

### Top Error Categories:
1. **Expression type contains "Any"** (~344 errors) - 29%
2. **Explicit "Any" is not allowed** (53 errors) - 4.5%
3. **Missing return type annotations** (20 errors) - 1.7%
4. **Missing type annotations** (14 errors) - 1.2%
5. **TypedDict key errors** (~40 errors) - 3.4%
6. **Incompatible types** (~30 errors) - 2.5%

### Most Affected Files:
1. `src/utils/astolfo_logger.py` - 157 errors
2. `src/vibelogger/formatters.py` - 137 errors
3. `src/utils/astolfo_vibe_logger.py` - 109 errors
4. `src/vibelogger/logger.py` - 95 errors
5. `src/vibelogger/handlers.py` - 78 errors

## Fix Strategy

### Phase 1: Foundation Fixes (Priority: HIGH)
Fix the core modules that other modules depend on:

#### 1.1 Fix Type Guards Module
**File**: `src/type_guards.py` (61 errors)
- Add proper return type annotations for all TypeGuard functions
- Replace `Any` with specific types
- Fix TypedDict key validation logic

#### 1.2 Fix Core Config Loader
**File**: `src/core/config_loader.py` (8 errors)
- Add return type annotations
- Replace `Any` with proper config types
- Fix type compatibility issues

#### 1.3 Fix Settings Types
**File**: `src/settings_types.py` (if exists)
- Ensure all TypedDict definitions are complete
- Add missing keys that are being accessed

### Phase 2: HTTP Client and Core Modules (Priority: HIGH)
#### 2.1 Fix HTTP Client
**File**: `src/core/http_client.py` (76 errors)
- Add proper type annotations for all methods
- Replace `Any` with specific Discord API types
- Fix argument type mismatches

#### 2.2 Fix Thread Storage
**File**: `src/thread_storage.py` (48 errors)
- Add return type annotations
- Replace `Any` with specific types for database results
- Fix SQL query result typing

### Phase 3: Logger Modules (Priority: MEDIUM)
These have the most errors but are less critical:

#### 3.1 Fix AstolfoLogger
**File**: `src/utils/astolfo_logger.py` (157 errors)
- Replace all `Any` usage with specific types
- Add return type annotations
- Fix the logging method signatures

#### 3.2 Fix VibeLogger Components
**Files**: 
- `src/vibelogger/logger.py` (95 errors)
- `src/vibelogger/formatters.py` (137 errors)
- `src/vibelogger/handlers.py` (78 errors)
- Add proper type annotations throughout
- Replace `Any` with specific types
- Fix method signature compatibility

### Phase 4: Handlers and Formatters (Priority: MEDIUM)
#### 4.1 Fix Discord Sender
**File**: `src/handlers/discord_sender.py` (26 errors)
- Fix argument type mismatches with HTTPClient
- Add proper type annotations for Discord message structures

#### 4.2 Fix Event Formatters
**File**: `src/formatters/event_formatters.py` (36 errors)
- Add return type annotations
- Fix embed field type issues

### Phase 5: Utilities (Priority: LOW)
#### 5.1 Fix Utils Helpers
**File**: `src/utils_helpers.py` (12 errors)
- Fix final variable assignment
- Add type annotations for metadata

#### 5.2 Fix Validators
**File**: `src/validators.py` (53 errors)
- Fix TypedDict key access issues
- Add proper type guards

## Common Fixes Across All Files

### 1. Replace `Any` Usage
```python
# Before
def process_data(data: Any) -> Any:
    return data.get("key")

# After
def process_data(data: dict[str, str | int | float]) -> str | int | float | None:
    return data.get("key")
```

### 2. Add Return Type Annotations
```python
# Before
def get_config(key: str):
    return CONFIG.get(key)

# After
def get_config(key: str) -> str | int | bool | None:
    return CONFIG.get(key)
```

### 3. Fix TypedDict Key Access
```python
# Before
if "command" in tool_input:  # tool_input might be wrong type

# After
if isinstance(tool_input, dict) and "command" in tool_input:
    # Or use proper type guard
```

### 4. Fix Method Signatures
```python
# Before
def log(self, message: str, **kwargs):
    pass

# After
def log(self, message: str, *, level: str = "info", **kwargs: str | int | float | bool) -> None:
    pass
```

### 5. Fix Import Types
```python
# Add at top of files
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any  # Only for type hints where absolutely necessary
```

## Implementation Order

1. **Week 1**: Phase 1 (Foundation) + Phase 2 (Core Modules)
   - Fix type guards and config first
   - Then fix HTTP client and thread storage

2. **Week 2**: Phase 3 (Logger Modules)
   - Start with astolfo_logger.py
   - Then fix vibelogger components

3. **Week 3**: Phase 4 (Handlers) + Phase 5 (Utilities)
   - Fix remaining handlers and formatters
   - Clean up utility modules

## Verification Steps

After each phase:
1. Run `mypy` on fixed files
2. Run unit tests to ensure no functionality broken
3. Check that dependent modules still work

## Success Metrics

- Total error count reduced from ~1,180 to 0
- All functions have proper return type annotations
- No `Any` usage except where absolutely necessary (with `# type: ignore` comments)
- All TypedDict accesses are type-safe

## Notes

- Some errors might be interconnected - fixing core modules may resolve errors in dependent modules
- Consider creating type alias definitions for commonly used complex types
- Document any legitimate uses of `Any` with comments explaining why it's necessary