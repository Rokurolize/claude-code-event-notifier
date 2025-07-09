# Fix G004 Logging F-String Errors

## Date: 2025-01-09 23:33:00

## Summary

Fixed all G004 errors in the codebase by converting f-strings in logging statements to lazy % formatting.

## Changes Made

### Files Modified

1. **src/thread_storage.py**
   - Fixed 14 logging statements
   - Converted all `self._logger.xxx(f"...")` to `self._logger.xxx("...", args)`

2. **src/discord_notifier.py**
   - Fixed 78 logging statements
   - Converted both `logger.xxx(f"...")` and `self.logger.xxx(f"...")` patterns
   - Handled various complexity levels including multiple format arguments

3. **examples/discord_notifier_refactor_example.py**
   - Fixed 4 logging statements
   - Converted all `self.logger.xxx(f"...")` to `self.logger.xxx("...", args)`

### Conversion Pattern

The conversion followed these patterns:

```python
# Single argument
# OLD: logger.debug(f"Message {variable}")
# NEW: logger.debug("Message %s", variable)

# Multiple arguments
# OLD: logger.info(f"Count: {count}, Name: {name}")
# NEW: logger.info("Count: %s, Name: %s", count, name)

# Complex expressions
# OLD: logger.error(f"Error {type(e).__name__}: {e}")
# NEW: logger.error("Error %s: %s", type(e).__name__, e)
```

### Benefits

1. **Performance**: String formatting only happens when the log level is enabled
2. **Best Practice**: Follows Python logging best practices
3. **Lint Compliance**: Eliminates all G004 errors from ruff linting

### Verification

All Python source files in `src/` and `examples/` directories have been checked and no G004 errors remain.