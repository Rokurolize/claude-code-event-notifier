# Error Handling Type Improvements Analysis

## Overview

This document analyzes how error handling affects types in the Discord notifier codebase and provides recommendations for improving type safety in try/except blocks.

## Key Issues Found

### 1. Bare `except` clauses
**Location**: `configure_hooks.py:54`
**Issue**: Bare `except:` clauses catch all exceptions without type information
**Fix**: Use specific exception types or `except Exception as e:` with type annotation

### 2. Generic Exception Handling
**Location**: Multiple locations in `discord_notifier.py`
**Issue**: Catching `Exception` without leveraging type information for better error handling
**Fix**: Use Union types for expected exceptions and type narrowing

### 3. Missing Type Annotations in Exception Variables
**Issue**: Exception variables not always typed, making error handling less precise
**Fix**: Add explicit type annotations for exception variables

## Recommended Improvements

### 1. Enhanced Exception Type Definitions

```python
from typing import Union, TypeAlias
import urllib.error
import json

# Define specific exception types for better type checking
NetworkError: TypeAlias = Union[urllib.error.HTTPError, urllib.error.URLError]
ConfigError: TypeAlias = Union[ConfigurationError, json.JSONDecodeError]
ValidationError: TypeAlias = Union[TypeError, ValueError]
```

### 2. Improved Error Handling Patterns

```python
# Instead of bare except:
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {type(e).__name__}: {e}")
    handle_error(e)

# Type-narrowed exception handling
try:
    network_operation()
except urllib.error.HTTPError as e:
    # e is now typed as HTTPError
    logger.error(f"HTTP error {e.code}: {e.reason}")
    return False
except urllib.error.URLError as e:
    # e is now typed as URLError  
    logger.error(f"URL error: {e.reason}")
    return False
except Exception as e:
    # Generic fallback with type information
    logger.error(f"Unexpected error: {type(e).__name__}: {e}")
    return False
```

### 3. Type-Safe Error Recovery

```python
def safe_json_load(data: str) -> dict[str, Any] | None:
    """Load JSON with type-safe error handling."""
    try:
        result = json.loads(data)
        if not isinstance(result, dict):
            logger.warning(f"Expected dict, got {type(result).__name__}")
            return None
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error at line {e.lineno}: {e.msg}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading JSON: {type(e).__name__}: {e}")
        return None
```

### 4. Context Manager Error Handling

```python
from contextlib import contextmanager
from typing import Generator, TypeVar

T = TypeVar('T')

@contextmanager
def safe_file_operation(filepath: Path) -> Generator[Path, None, None]:
    """Context manager for safe file operations with cleanup."""
    temp_path: Path | None = None
    try:
        temp_path = filepath.with_suffix('.tmp')
        yield temp_path
        # Atomic rename on success
        temp_path.rename(filepath)
    except (OSError, IOError) as e:
        logger.error(f"File operation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in file operation: {type(e).__name__}: {e}")
        raise
    finally:
        # Clean up temp file if it exists
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
```

### 5. Result Types for Error Handling

```python
from typing import Generic, TypeVar, Union
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Result(Generic[T, E]):
    """Result type for operations that can fail."""
    success: bool
    value: T | None = None
    error: E | None = None
    
    @classmethod
    def ok(cls, value: T) -> 'Result[T, E]':
        return cls(success=True, value=value)
    
    @classmethod
    def err(cls, error: E) -> 'Result[T, E]':
        return cls(success=False, error=error)

def safe_discord_send(message: DiscordMessage, config: Config) -> Result[bool, DiscordAPIError]:
    """Send Discord message with Result type for error handling."""
    try:
        success = send_to_discord(message, config, logger, http_client)
        return Result.ok(success)
    except DiscordAPIError as e:
        return Result.err(e)
    except Exception as e:
        # Convert unexpected errors to our domain error
        api_error = DiscordAPIError(f"Unexpected error: {e}")
        return Result.err(api_error)
```

## Implementation Status

### Fixed Issues
1. ✅ Replaced bare `except:` with `except Exception as e:` in `configure_hooks.py`
2. ✅ Added missing import for `ClaudeSettings` type
3. ✅ Improved type annotations in exception handling

### Recommended Future Improvements
1. 🔄 Add Union types for expected exception combinations
2. 🔄 Implement Result types for operations that can fail
3. 🔄 Add context managers for resource cleanup
4. 🔄 Create specific exception type aliases
5. 🔄 Add type narrowing in exception handlers

## Type Safety Benefits

### Before
```python
try:
    operation()
except:  # No type information
    cleanup()
    raise
```

### After
```python
try:
    operation()
except (ConfigurationError, ValidationError) as e:
    # e is typed as Union[ConfigurationError, ValidationError]
    logger.error(f"Configuration error: {e}")
    cleanup()
    raise e
except Exception as e:
    # e is typed as Exception
    logger.error(f"Unexpected error: {type(e).__name__}: {e}")
    cleanup()
    raise e
```

## Testing Implications

Error handling improvements should be accompanied by tests that verify:
1. Correct exception types are raised
2. Type narrowing works as expected
3. Error recovery mechanisms function properly
4. Resource cleanup occurs in all scenarios

## Conclusion

The codebase demonstrates good error handling practices overall, with comprehensive custom exception types and appropriate use of specific exception catching. The main improvements focus on:

1. Eliminating bare `except` clauses
2. Adding type annotations to exception variables
3. Using Union types for expected exception combinations
4. Implementing Result types for better error propagation
5. Adding context managers for resource safety

These improvements enhance type safety while maintaining the existing robust error handling patterns.