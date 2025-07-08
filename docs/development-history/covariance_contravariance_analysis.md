# Covariance/Contravariance Analysis: Claude Code Event Notifier

## Executive Summary

The Claude Code Event Notifier codebase exhibits several significant covariance and contravariance issues that are preventing the type checker from properly inferring types. These issues primarily stem from inappropriate use of TypedDict inheritance, complex union types, and violations of variance principles in generic type parameters.

## Key Findings

### 1. **Critical TypedDict Variance Violation**

**Location**: `src/settings_types.py:73-75`

**Issue**: The `ToolHookConfig` class attempts to override an optional field as required, which violates TypedDict contravariance rules.

```python
class HookConfig(TypedDict, total=False):
    hooks: list[HookEntry]
    matcher: str  # Optional field

class ToolHookConfig(HookConfig):
    matcher: str  # ERROR: Cannot make optional field required
```

**Root Cause**: TypedDict inheritance requires that field requirements can only become more permissive (contravariant), not more restrictive. A field cannot change from optional to required in a subclass.

**Impact**: Type checker error: `TypedDict item "matcher" cannot be redefined as Required`

### 2. **Complex Union Type Covariance Issues**

**Location**: `src/discord_notifier.py:232-252`

**Issue**: The union types create covariance problems when combined with inheritance chains.

```python
ToolInput = (
    BashToolInput
    | FileToolInput  
    | SearchToolInput
    | TaskToolInput
    | WebToolInput
    | dict[str, Any]  # This breaks type specificity
)

EventData = (
    PreToolUseEventData
    | PostToolUseEventData
    | NotificationEventData
    | StopEventData
    | SubagentStopEventData
    | dict[str, Any]  # Generic fallback causes covariance issues
)
```

**Root Cause**: The generic `dict[str, Any]` fallback makes union types too broad, preventing the type checker from narrowing to specific types.

### 3. **Function Parameter Contravariance Problems**

**Location**: `src/type_guards.py:917-932`

**Issue**: Generic type guard functions with overly complex return types.

```python
def get_type_guard(type_name: str) -> TypeGuard[Any] | None:
    return TYPE_GUARDS.get(type_name)
```

**Root Cause**: The function signature is too generic, and the complex union return type prevents proper type inference.

### 4. **Event Data Inheritance Chain Issues**

**Location**: `src/discord_notifier.py:193-229`

**Issue**: Multiple inheritance levels create covariance problems.

```python
class PreToolUseEventData(BaseEventData):
    tool_name: str
    tool_input: dict[str, Any]

class PostToolUseEventData(PreToolUseEventData):  # Inheritance chain
    tool_response: str | dict[str, Any] | list[Any]
```

**Root Cause**: Deep inheritance chains with varying field requirements create variance conflicts when used in union types.

## Detailed Analysis

### Variance Principles Being Violated

1. **Contravariance in Function Parameters**
   - Function parameters should be contravariant (accept more general types)
   - Current implementation uses overly specific parameters that can't be widened

2. **Covariance in Return Types**
   - Return types should be covariant (can be narrowed to more specific types)
   - Current union return types are too broad to be narrowed effectively

3. **TypedDict Field Variance**
   - TypedDict fields follow contravariant rules for requirements
   - Optional fields cannot become required in subclasses

### Type Inference Failures

The type checker reports multiple "unknown" and "partially unknown" types:

```
Type of "hook_config" is unknown
Type of "event_type" is unknown
Type of "get" is partially unknown
Return type is unknown
```

These indicate that the type checker cannot resolve the complex variance relationships.

## Root Cause Analysis

### 1. **Structural vs Nominal Typing Conflicts**

The codebase mixes structural typing (TypedDict) with nominal typing patterns, creating variance mismatches.

### 2. **Over-Complex Type Hierarchies**

Deep inheritance chains with changing field requirements violate type system constraints.

### 3. **Generic Type Misuse**

Using `dict[str, Any]` as a fallback breaks type specificity and creates covariance issues.

### 4. **Inadequate Type Guards**

Missing or incorrect type guards fail to properly narrow union types.

## Specific Diagnostic Patterns

### Pattern 1: Unknown Type Propagation
```
Type of "hook_config" is unknown
Type of "event_type" is unknown
```

### Pattern 2: Overload Resolution Failures
```
Type of "get" is partially unknown
Type of "get" is "Overload[...]" 
```

### Pattern 3: Generic Type Parameter Issues
```
Variable not allowed in type expression
Return type is unknown
```

## Impact Assessment

### Type Safety Risks
- Dictionary access without proper type guards
- Potential `KeyError` exceptions on optional TypedDict fields
- Incorrect type assumptions in event handling

### Development Experience Issues
- No IntelliSense/autocomplete in IDEs
- Missing type checking during development
- Harder to catch type-related bugs

### Maintenance Challenges
- Difficult to refactor safely
- Type changes propagate unpredictably
- Complex debugging of type-related issues

## Recommended Solutions

### 1. **Fix TypedDict Inheritance**

Replace inheritance with composition for TypedDict with different field requirements:

```python
# Instead of inheritance
class HookConfig(TypedDict, total=False):
    hooks: list[HookEntry]
    matcher: str

# Use composition
class BaseHookConfig(TypedDict):
    hooks: list[HookEntry]

class ToolHookConfig(BaseHookConfig):
    matcher: str  # Required for tool events

class NonToolHookConfig(BaseHookConfig):
    pass  # No matcher field
```

### 2. **Implement Discriminated Unions**

Replace broad unions with discriminated unions:

```python
class EventData(TypedDict):
    event_type: Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]
    data: PreToolUseEventData | PostToolUseEventData | NotificationEventData | StopEventData | SubagentStopEventData
```

### 3. **Add Comprehensive Type Guards**

Implement proper type guards for all union types:

```python
def is_pre_tool_use_event(data: dict[str, Any]) -> TypeGuard[PreToolUseEventData]:
    return (
        isinstance(data.get("hook_event_name"), str) and
        data["hook_event_name"] == "PreToolUse" and
        "tool_name" in data and
        "tool_input" in data
    )
```

### 4. **Use Protocol Classes for Variance Control**

Replace inheritance with Protocol classes for better variance control:

```python
class EventFormatterProtocol(Protocol):
    def format(self, event_data: dict[str, Any], session_id: str) -> DiscordEmbed: ...
```

### 5. **Simplify Generic Type Usage**

Remove overly broad generic fallbacks and use specific type narrowing:

```python
# Instead of broad union with dict[str, Any]
ToolInput = BashToolInput | FileToolInput | SearchToolInput | TaskToolInput | WebToolInput

# Use proper type narrowing with type guards
def narrow_tool_input(tool_name: str, tool_input: dict[str, Any]) -> ToolInput:
    if tool_name == "Bash":
        return cast(BashToolInput, tool_input)
    # ... handle other cases
```

## Priority Actions

1. **Immediate**: Fix the TypedDict inheritance issue in `settings_types.py`
2. **High**: Implement discriminated unions for EventData
3. **Medium**: Add comprehensive type guards for all union types
4. **Low**: Refactor to use Protocol classes where appropriate

## Expected Outcomes

After implementing these fixes:
- Type checker will properly infer types throughout the codebase
- IDE support will improve with better autocomplete and error detection
- Runtime type safety will increase
- Code maintainability will improve significantly

## Technical Details

### Variance Rules Refresher

- **Covariance**: Type parameters can be narrowed (subtypes allowed)
- **Contravariance**: Type parameters can be widened (supertypes allowed)
- **Invariance**: Type parameters must match exactly

### TypedDict Constraints

- Fields marked as required cannot become optional in subclasses
- Fields marked as optional can become required, but only through explicit redefinition
- Field types must maintain their variance properties

### Union Type Best Practices

- Use discriminated unions where possible
- Implement proper type guards for runtime narrowing
- Avoid overly broad fallback types like `dict[str, Any]`