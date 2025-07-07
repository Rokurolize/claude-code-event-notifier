# JSON Type Checking Configuration Analysis

## Summary

This document analyzes the JSON handling patterns in the Claude Code Discord Notifier project and provides type checking configuration recommendations to improve type safety while maintaining functionality.

## Current JSON Usage Patterns

### 1. JSON Loading Operations (`json.loads()`)

The project uses `json.loads()` in several critical areas:

#### Main Event Processing (`src/discord_notifier.py:2292`)
```python
raw_input = sys.stdin.read()
event_data = json.loads(raw_input)  # Returns Any
```

#### Settings Configuration (`configure_hooks.py:140, 177`)
```python
settings_data = json.load(f)  # Returns Any
settings = cast(ClaudeSettings, settings_data)
```

#### Discord API Responses (`src/discord_notifier.py:1425, 1465`)
```python
response_data = json.loads(response.read().decode("utf-8"))  # Returns Any
```

### 2. JSON Serialization Operations (`json.dumps()`)

#### Configuration Writing
```python
json.dumps(settings, indent=2)  # Well-typed input
```

#### Discord API Calls
```python
json_data = json.dumps(data).encode("utf-8")  # Well-typed input
```

#### Debug Logging
```python
logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")
```

### 3. JSON Validation and Type Guards

#### JSON Serializability Check (`src/type_guards.py:656`)
```python
def is_json_serializable(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False
```

## Type Safety Challenges

### 1. `json.loads()` Return Type Problem

`json.loads()` always returns `Any`, which breaks type safety:

```python
# Current pattern - loses type information
event_data = json.loads(raw_input)  # Type: Any
session_id = event_data.get("session_id", "")  # Mypy warning
```

### 2. Dynamic Event Data Access

Event data structures vary by event type, requiring flexible access:

```python
# Different event types have different fields
if event_type == "PreToolUse":
    tool_name = event_data.get("tool_name")  # String expected
elif event_type == "PostToolUse":
    output = event_data.get("output")  # Could be string or dict
```

### 3. Discord API Response Handling

Discord API responses are parsed as JSON but have known structures:

```python
response_data = json.loads(response.read().decode("utf-8"))
thread_id = response_data.get("id")  # Should be string
```

## Recommended Type Checking Configuration

### 1. MyPy Configuration (`mypy.ini`)

**Key Settings for JSON Handling:**
- `disallow_any_expr = False` - Allow `Any` in expressions (needed for `json.loads()`)
- `disallow_any_explicit = False` - Allow explicit `Any` annotations
- `strict_optional = True` - Maintain strict optional checking
- `warn_return_any = True` - Warn when functions return `Any`

**Module-Specific Overrides:**
- More lenient settings for JSON-heavy modules
- Strict settings for type definition modules
- Relaxed settings for test modules

### 2. Ruff Configuration (`pyproject.toml`)

**Type Checking Rules:**
- `TCH` - flake8-type-checking (imports in TYPE_CHECKING blocks)
- `ANN` - flake8-annotations (type annotations)
- `PYI` - flake8-pyi (stub file conventions)

**JSON-Specific Ignores:**
- Allow `Any` types in JSON parsing functions
- Allow complex formatting functions
- Maintain strict checking elsewhere

## Implementation Improvements

### 1. Enhanced Type Guards

```python
def is_event_data(value: Any) -> TypeGuard[dict[str, Any]]:
    """Type guard for event data structures."""
    return (
        isinstance(value, dict) and
        "session_id" in value and
        isinstance(value["session_id"], str)
    )
```

### 2. Structured JSON Parsing

```python
def parse_event_data(raw_input: str) -> dict[str, Any]:
    """Parse and validate event data from JSON."""
    try:
        data = json.loads(raw_input)
        if not isinstance(data, dict):
            raise ValueError("Event data must be a dictionary")
        return data
    except json.JSONDecodeError as e:
        raise EventProcessingError(f"Invalid JSON: {e}") from e
```

### 3. Response Type Validation

```python
def parse_discord_response(response_text: str) -> dict[str, Any]:
    """Parse Discord API response with validation."""
    try:
        data = json.loads(response_text)
        if not isinstance(data, dict):
            raise DiscordAPIError("Invalid response format")
        return data
    except json.JSONDecodeError as e:
        raise DiscordAPIError(f"Invalid JSON response: {e}") from e
```

## Benefits of This Configuration

### 1. Balanced Type Safety
- Maintains strict typing where possible
- Allows necessary flexibility for JSON operations
- Catches type errors in non-JSON code

### 2. Clear Error Reporting
- Specific warnings for JSON-related type issues
- Context-aware error messages
- Traceback information for debugging

### 3. Development Workflow
- Fast type checking with appropriate strictness
- Clear distinction between JSON and non-JSON code
- Useful warnings without excessive noise

## Migration Strategy

### 1. Immediate Steps
1. Add `pyproject.toml` with mypy and ruff configuration
2. Run `mypy` to identify current type issues
3. Address critical type safety problems

### 2. Gradual Improvements
1. Add type guards for JSON parsing functions
2. Implement structured response parsing
3. Add validation for critical JSON operations

### 3. Long-term Goals
1. Consider JSON schema validation for critical data
2. Implement proper TypedDict validation
3. Add runtime type checking for external data

## Conclusion

The provided configuration balances type safety with practical JSON handling needs. It allows the necessary flexibility for `json.loads()` operations while maintaining strict type checking for the rest of the codebase. This approach catches real type errors without creating excessive maintenance overhead.

The configuration is designed to:
- Allow `Any` types where JSON parsing requires them
- Maintain strict checking for business logic
- Provide clear error messages and context
- Support incremental adoption of better type safety practices

This setup enables the project to benefit from static type checking while working effectively with dynamic JSON data structures that are inherent to the Discord API and Claude Code event system.