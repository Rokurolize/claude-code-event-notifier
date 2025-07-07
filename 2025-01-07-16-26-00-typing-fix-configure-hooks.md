# Fixed Typing Issue in configure_hooks.py

## Problem
The `hooks_list.append(hook_config)` call at line 194 (now line 202) had a partially unknown type because the type system couldn't infer the type of `settings["hooks"][event]`.

## Solution
Added proper type definitions to ensure type safety:

1. **Added `ClaudeSettings` TypedDict** (lines 34-36):
   ```python
   class ClaudeSettings(TypedDict, total=False):
       """Claude Code settings structure."""
       hooks: dict[str, list[HookConfig]]
   ```

2. **Updated main function to use typed settings** (lines 160-165):
   ```python
   settings_data = json.load(f)
   # Type cast to ensure proper typing
   settings = cast(ClaudeSettings, settings_data)
   ```

3. **Removed unnecessary type cast** (line 202):
   ```python
   # Before: settings["hooks"][event].append(cast(Any, hook_config))
   # After: settings["hooks"][event].append(hook_config)
   ```

4. **Updated filter_hooks return type** (line 90):
   ```python
   def filter_hooks(event_hooks: Any) -> list[HookConfig]:
   ```

5. **Applied same typing to removal section** (lines 126-129)

## Benefits
- Proper type checking for the entire settings structure
- No more type errors or unknown method warnings
- Cleaner code without unnecessary casts
- Better IDE support and autocomplete

## Testing
- Code compiles without syntax errors
- All unit tests pass (13 tests)
- Type safety is now enforced throughout the configuration process