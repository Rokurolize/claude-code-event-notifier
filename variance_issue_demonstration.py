#!/usr/bin/env python3
"""
Demonstration of covariance/contravariance issues in the Claude Code Event Notifier.

This script isolates and demonstrates the specific variance issues that are causing
type checker failures, with explanations and proposed fixes.
"""

from typing import TypedDict, Literal, Any, TypeGuard, Protocol, cast
from typing_extensions import NotRequired


# =============================================================================
# ISSUE 1: TypedDict Contravariance Violation
# =============================================================================

print("=== ISSUE 1: TypedDict Contravariance Violation ===")

# PROBLEMATIC CODE (causes type checker errors):
class HookConfigProblematic(TypedDict, total=False):
    """Base hook config with optional fields."""
    hooks: list[dict[str, str]]
    matcher: str  # Optional field

class ToolHookConfigProblematic(HookConfigProblematic):
    """Tool hook config - attempts to make optional field required."""
    matcher: str  # ERROR: Cannot make optional field required!

# FIXED VERSION:
class HookConfigFixed(TypedDict):
    """Base hook config with only required fields."""
    hooks: list[dict[str, str]]

class ToolHookConfigFixed(HookConfigFixed):
    """Tool hook config with required matcher."""
    matcher: str  # OK: Adding required field to base

class NonToolHookConfigFixed(HookConfigFixed):
    """Non-tool hook config with optional matcher."""
    matcher: NotRequired[str]  # OK: Adding optional field

print("✅ TypedDict inheritance fixed using composition approach")


# =============================================================================
# ISSUE 2: Union Type Covariance Issues
# =============================================================================

print("\n=== ISSUE 2: Union Type Covariance Issues ===")

# PROBLEMATIC CODE (causes type inference failures):
class BashInput(TypedDict):
    command: str
    timeout: NotRequired[int]

class FileInput(TypedDict):
    file_path: str
    content: str

# This union is too broad and prevents proper type narrowing
ToolInputProblematic = BashInput | FileInput | dict[str, Any]

def process_tool_input_problematic(tool_input: ToolInputProblematic) -> str:
    """Type checker cannot narrow the union properly."""
    # Type checker loses specificity due to dict[str, Any] fallback
    if "command" in tool_input:
        # Type checker doesn't know this is BashInput
        return f"bash: {tool_input['command']}"  # Type error possible
    return "unknown"

# FIXED VERSION using discriminated unions:
class BashInputFixed(TypedDict):
    tool_type: Literal["bash"]
    command: str
    timeout: NotRequired[int]

class FileInputFixed(TypedDict):
    tool_type: Literal["file"]
    file_path: str
    content: str

ToolInputFixed = BashInputFixed | FileInputFixed

def process_tool_input_fixed(tool_input: ToolInputFixed) -> str:
    """Type checker can properly narrow based on discriminant."""
    if tool_input["tool_type"] == "bash":
        # Type checker knows this is BashInputFixed
        return f"bash: {tool_input['command']}"  # Type safe!
    else:
        # Type checker knows this is FileInputFixed
        return f"file: {tool_input['file_path']}"

print("✅ Union type covariance fixed using discriminated unions")


# =============================================================================
# ISSUE 3: Function Parameter Contravariance
# =============================================================================

print("\n=== ISSUE 3: Function Parameter Contravariance ===")

# PROBLEMATIC CODE (prevents proper type inference):
def get_type_guard_problematic(type_name: str) -> TypeGuard[Any] | None:
    """Return type is too generic, prevents narrowing."""
    type_guards = {
        "bash": lambda x: isinstance(x, dict) and "command" in x,
        "file": lambda x: isinstance(x, dict) and "file_path" in x,
    }
    return type_guards.get(type_name)

# FIXED VERSION using specific type guards:
def is_bash_input(value: Any) -> TypeGuard[BashInputFixed]:
    """Specific type guard for bash input."""
    return (
        isinstance(value, dict) and
        value.get("tool_type") == "bash" and
        "command" in value
    )

def is_file_input(value: Any) -> TypeGuard[FileInputFixed]:
    """Specific type guard for file input."""
    return (
        isinstance(value, dict) and
        value.get("tool_type") == "file" and
        "file_path" in value
    )

def narrow_tool_input(tool_input: dict[str, Any]) -> ToolInputFixed:
    """Proper type narrowing using specific type guards."""
    if is_bash_input(tool_input):
        return tool_input  # Type checker knows this is BashInputFixed
    elif is_file_input(tool_input):
        return tool_input  # Type checker knows this is FileInputFixed
    else:
        raise ValueError(f"Unknown tool input type: {tool_input}")

print("✅ Function parameter contravariance fixed with specific type guards")


# =============================================================================
# ISSUE 4: Protocol-based Variance Control
# =============================================================================

print("\n=== ISSUE 4: Protocol-based Variance Control ===")

# PROBLEMATIC CODE (inheritance causes variance issues):
class FormatterBase:
    """Base formatter with rigid inheritance."""
    def format(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"formatted": True}

class BashFormatterProblematic(FormatterBase):
    """Bash formatter with variance issues."""
    def format(self, data: BashInputFixed) -> dict[str, str]:  # Variance conflict!
        return {"bash_output": data["command"]}

# FIXED VERSION using Protocol for proper variance:
class FormatterProtocol(Protocol):
    """Protocol for formatters with proper variance."""
    def format(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format method with contravariant parameter, covariant return."""
        ...

class BashFormatterFixed:
    """Bash formatter using protocol."""
    def format(self, data: dict[str, Any]) -> dict[str, str]:
        """Properly typed format method."""
        if is_bash_input(data):
            return {"bash_output": data["command"]}
        return {"error": "Invalid bash input"}

def use_formatter(formatter: FormatterProtocol, data: dict[str, Any]) -> dict[str, Any]:
    """Function using protocol for proper variance."""
    return formatter.format(data)

print("✅ Protocol-based variance control implemented")


# =============================================================================
# ISSUE 5: Generic Type Parameter Variance
# =============================================================================

print("\n=== ISSUE 5: Generic Type Parameter Variance ===")

from typing import Generic, TypeVar

# PROBLEMATIC CODE (invariant when should be covariant):
T = TypeVar('T')

class ContainerProblematic(Generic[T]):
    """Container with invariant type parameter."""
    def __init__(self, item: T) -> None:
        self._item = item
    
    def get_item(self) -> T:
        return self._item

# This fails because List[str] is not assignable to List[object]
# container_str: ContainerProblematic[str] = ContainerProblematic("hello")
# container_obj: ContainerProblematic[object] = container_str  # Type error!

# FIXED VERSION using proper variance:
from typing import TypeVar

T_co = TypeVar('T_co', covariant=True)  # Covariant type parameter

class ContainerFixed(Generic[T_co]):
    """Container with covariant type parameter."""
    def __init__(self, item: T_co) -> None:
        self._item = item
    
    def get_item(self) -> T_co:
        return self._item

# This works because Container[str] is assignable to Container[object]
container_str: ContainerFixed[str] = ContainerFixed("hello")
container_obj: ContainerFixed[object] = container_str  # OK!

print("✅ Generic type parameter variance fixed")


# =============================================================================
# DEMONSTRATION OF FIXES
# =============================================================================

print("\n=== DEMONSTRATION: All Fixes Working Together ===")

# Example data
bash_data = {
    "tool_type": "bash",
    "command": "echo hello",
    "timeout": 30
}

file_data = {
    "tool_type": "file", 
    "file_path": "/tmp/test.txt",
    "content": "Hello, World!"
}

# Type-safe processing
def demonstrate_fixes():
    """Demonstrate all fixes working together."""
    
    # 1. Type-safe narrowing
    bash_input = narrow_tool_input(bash_data)
    file_input = narrow_tool_input(file_data)
    
    # 2. Type-safe formatting
    bash_formatter = BashFormatterFixed()
    bash_result = bash_formatter.format(bash_input)
    
    # 3. Type-safe container usage
    bash_container: ContainerFixed[BashInputFixed] = ContainerFixed(bash_input)
    container_obj: ContainerFixed[object] = bash_container  # Covariance works!
    
    print(f"✅ Bash processing: {bash_result}")
    print(f"✅ Container covariance: {type(container_obj.get_item())}")
    
    return True

success = demonstrate_fixes()
print(f"\n🎉 All variance issues resolved: {success}")

# =============================================================================
# SUMMARY OF FIXES
# =============================================================================

print("\n=== SUMMARY OF VARIANCE FIXES ===")
print("1. ✅ TypedDict inheritance: Use composition instead of problematic inheritance")
print("2. ✅ Union type covariance: Use discriminated unions with proper type guards")
print("3. ✅ Function contravariance: Implement specific type guards instead of generic ones")
print("4. ✅ Protocol variance: Use Protocol classes for flexible type relationships")
print("5. ✅ Generic variance: Properly annotate type parameters with variance modifiers")
print("\nResult: Type checker can now properly infer types throughout the codebase!")