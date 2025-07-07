# Type Checking Guide

This project uses MyPy and Ruff for type checking and linting, with specific configurations for JSON handling.

## Quick Start

```bash
# Install type checking tools (when available)
pip install mypy ruff

# Run type checking
mypy src/
mypy configure_hooks.py

# Run linting
ruff check .
ruff format .

# Run custom JSON validation
python3 validate_json_types.py
```

## Configuration Files

- `pyproject.toml` - Modern Python project configuration with MyPy and Ruff settings
- `mypy.ini` - MyPy-specific configuration with JSON handling rules
- `validate_json_types.py` - Custom validation script for JSON type patterns

## Key Features

### JSON Handling
- Allows `Any` types for `json.loads()` operations
- Maintains strict typing for business logic
- Module-specific rules for different components

### Type Safety
- Strict optional checking
- Warning for functions returning `Any`
- Comprehensive type annotations

### Development
- Clear error messages with context
- Incremental adoption support
- Balanced strictness levels

## Module-Specific Rules

| Module | Strictness | JSON Handling | Notes |
|--------|------------|---------------|-------|
| `src/discord_notifier.py` | Medium | Flexible | Main application logic |
| `src/type_guards.py` | Low | Flexible | Type guard functions |
| `src/settings_types.py` | High | Strict | Type definitions |
| `configure_hooks.py` | Medium | Flexible | Configuration script |
| `test_*.py` | Low | Flexible | Test modules |

## Current Status

Based on `validate_json_types.py`:
- ✅ 3 `json.loads()` calls identified (expected)
- ✅ 8 `json.dumps()` calls (properly typed)
- ✅ 0 problematic `Any` annotations
- ✅ Configuration files present

## Best Practices

1. **Use type annotations** for all functions
2. **Validate JSON data** when possible
3. **Use TypeGuards** for runtime type checking
4. **Cast with care** - prefer validation over casting
5. **Test type safety** with the validation script

## Troubleshooting

### Common Issues
- `json.loads()` returns `Any` - This is expected and configured
- Missing type annotations - Add them incrementally
- Strict mode errors - Check module-specific overrides

### Getting Help
- Check `20250107174000-type-checking-configuration-summary.md` for detailed analysis
- Run `validate_json_types.py` for current status
- Review `pyproject.toml` for configuration details