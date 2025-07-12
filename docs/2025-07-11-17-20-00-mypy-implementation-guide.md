# MyPy Error Fix Implementation Guide
Generated: 2025-07-11 17:20:00

## Quick Reference: Common Fixes

### 1. Explicit Any Not Allowed
```python
# ❌ Before
from typing import Any
def process(data: Any) -> Any:
    pass

# ✅ After - Option 1: Use specific types
def process(data: dict[str, str | int | float | bool]) -> dict[str, str | int | float | bool]:
    pass

# ✅ After - Option 2: Use TypeVar for generic functions
from typing import TypeVar
T = TypeVar('T')
def process(data: T) -> T:
    pass

# ✅ After - Option 3: If Any is truly needed
from typing import Any  # type: ignore[misc]
def process(data: Any) -> Any:  # type: ignore[explicit-any]
    pass
```

### 2. Missing Return Type Annotations
```python
# ❌ Before
def get_value(key: str):
    return config.get(key)

# ✅ After
def get_value(key: str) -> str | int | bool | None:
    return config.get(key)
```

### 3. TypedDict Key Access Errors
```python
# ❌ Before (validators.py line 320)
return "command" in tool_input and isinstance(tool_input["command"], str)

# ✅ After - Use type narrowing
if isinstance(tool_input, dict) and "command" in tool_input:
    return isinstance(tool_input["command"], str)
return False
```

### 4. Expression Contains Any
```python
# ❌ Before
metadata = thread_details.get("thread_metadata", {})

# ✅ After
metadata: dict[str, bool | str | int] = thread_details.get("thread_metadata", {})
```

## File-Specific Fixes

### 1. src/utils_helpers.py
```python
# Line 16 - Cannot assign to final name
# ❌ Before
TRUNCATION_SUFFIX = "..."

# ✅ After
TRUNCATION_SUFFIX: Final[str] = "..."  # Don't reassign elsewhere

# Line 108 - Explicit Any not allowed
# ❌ Before
def ensure_thread_is_usable(
    http_client: HTTPClient,
    thread_details: dict[str, Any],
    token: str
) -> bool:

# ✅ After
from typing import TypedDict

class ThreadDetails(TypedDict):
    id: str
    thread_metadata: dict[str, bool | str | int]

def ensure_thread_is_usable(
    http_client: HTTPClient,
    thread_details: ThreadDetails,
    token: str
) -> bool:
```

### 2. src/vibelogger/config.py
```python
# Lines 19, 30 - Missing return type annotations
# ❌ Before
@classmethod
def from_env(cls):
    ...

# ✅ After
@classmethod
def from_env(cls) -> "VibeLoggerConfig":
    ...

@classmethod
def default_file_config(cls, project_name: str = "vibe_project") -> dict[str, Any]:
    ...
```

### 3. src/type_guards.py
```python
# Line 437-440 - Dict entry incompatible types
# ❌ Before
validators: dict[str, Callable[[object], TypeIs[str | None]]] = {
    "debug": lambda v: isinstance(v, bool),
    "use_threads": lambda v: isinstance(v, bool),
}

# ✅ After - Create specific validators
def is_bool(value: object) -> TypeIs[bool]:
    return isinstance(value, bool)

def is_channel_type(value: object) -> TypeIs[str]:
    return isinstance(value, str) and value in ["text", "forum"]

validators = {
    "debug": is_bool,
    "use_threads": is_bool,
    "channel_type": is_channel_type,
}
```

### 4. src/utils/astolfo_logger.py
```python
# Replace all Any usage
# ❌ Before
@dataclass
class AstolfoLog:
    context: dict[str, Any] = field(default_factory=dict)
    error: Optional[dict[str, Any]] = None

# ✅ After
from typing import Union

JsonValue = Union[str, int, float, bool, None, dict[str, "JsonValue"], list["JsonValue"]]

@dataclass
class AstolfoLog:
    context: dict[str, JsonValue] = field(default_factory=dict)
    error: Optional[dict[str, JsonValue]] = None
```

### 5. src/core/http_client.py
```python
# Fix argument type mismatches
# ❌ Before
def post_webhook(self, webhook_url: str, message: dict) -> bool:

# ✅ After
from typing import TypedDict

class DiscordMessage(TypedDict, total=False):
    content: str
    embeds: list[dict[str, Any]]
    thread_name: NotRequired[str]

def post_webhook(self, webhook_url: str, message: DiscordMessage) -> bool:
```

### 6. src/handlers/discord_sender.py
```python
# Line 83 - Union type attribute access
# ❌ Before
message.get("content", "").replace(f"<@{ctx.config['mention_user_id']}>", "")

# ✅ After
content = message.get("content", "")
if content is not None:
    content = content.replace(f"<@{ctx.config['mention_user_id']}>", "")
```

## Type Alias Definitions to Add

Create a new file `src/type_aliases.py`:
```python
from typing import Union, TypeAlias

# Common JSON types
JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]

# Discord specific types
Snowflake: TypeAlias = str  # Discord IDs
EmbedField: TypeAlias = dict[str, str | bool]
DiscordEmbed: TypeAlias = dict[str, str | int | list[EmbedField] | dict[str, str]]

# Config types
ConfigValue: TypeAlias = str | int | bool | list[str]
```

## Systematic Fix Process

### Step 1: Create Type Infrastructure
1. Create `src/type_aliases.py` with common type definitions
2. Update `src/settings_types.py` with complete TypedDict definitions
3. Add missing fields to all TypedDict classes

### Step 2: Fix Core Modules (Bottom-up)
1. Fix `src/type_guards.py` - replace lambda validators with proper TypeIs functions
2. Fix `src/core/config_loader.py` - add return types
3. Fix `src/core/http_client.py` - use proper Discord types

### Step 3: Fix Dependent Modules
1. Fix handlers that use HTTPClient
2. Fix formatters that create Discord embeds
3. Fix utilities that process data

### Step 4: Fix Logger Modules
1. Replace all `Any` with `JsonValue` type alias
2. Add return type annotations to all methods
3. Fix method signature compatibility

## Validation Commands

After each fix, run:
```bash
# Check specific file
uv run --no-sync --python 3.13 python -m mypy src/path/to/file.py

# Check all files
uv run --no-sync --python 3.13 python -m mypy src/ --show-error-codes

# Run tests to ensure no breakage
uv run --no-sync --python 3.13 python -m unittest discover -s tests
```

## Emergency Escape Hatches

If a type is truly dynamic and cannot be typed:
```python
# Use type: ignore with specific error code
value: Any  # type: ignore[explicit-any]

# For entire function
def dynamic_function(data: Any) -> Any:  # type: ignore[explicit-any]
    pass

# For specific line
result = untypeable_operation()  # type: ignore[misc]
```

Always document WHY the type ignore is necessary.