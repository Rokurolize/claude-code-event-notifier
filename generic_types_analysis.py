#!/usr/bin/env python3
"""
Analysis of Generic types and TypeVar usage for Discord Notifier.

This file demonstrates how to use Generic types and TypeVar to create more
reusable type definitions for nested structures in the Discord notifier.
"""

from typing import (
    Any,
    TypedDict,
    Literal,
    TypeGuard,
    Protocol,
    Final,
    cast,
    NotRequired,
    Generic,
    TypeVar,
    Type,
    Union,
    Optional,
    Callable,
    Dict,
    List,
)
from collections.abc import Callable as CallableABC
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# =============================================================================
# Generic Type Variables
# =============================================================================

# Type variables for creating generic structures
T = TypeVar('T')  # General type variable
TInput = TypeVar('TInput', bound='ToolInputProtocol')  # Tool input constraint
TResponse = TypeVar('TResponse')  # Tool response type
TEventData = TypeVar('TEventData', bound='BaseEventData')  # Event data constraint
TConfig = TypeVar('TConfig', bound='ConfigProtocol')  # Configuration constraint
TMessage = TypeVar('TMessage', bound='MessageProtocol')  # Message constraint

# Constraint type variables for specific domains
ToolNameT = TypeVar('ToolNameT', bound=str)  # Tool name constraint
EventTypeT = TypeVar('EventTypeT', bound=str)  # Event type constraint
ResponseDataT = TypeVar('ResponseDataT', bound=Union[str, dict, list])  # Response data constraint

# =============================================================================
# Base Protocols for Generic Constraints
# =============================================================================

class ToolInputProtocol(Protocol):
    """Protocol for tool input structures."""
    pass

class ConfigProtocol(Protocol):
    """Protocol for configuration structures."""
    webhook_url: Optional[str]
    bot_token: Optional[str]
    channel_id: Optional[str]
    debug: bool

class MessageProtocol(Protocol):
    """Protocol for message structures."""
    pass

class BaseEventData(TypedDict):
    """Base event data structure."""
    session_id: str
    transcript_path: str
    hook_event_name: str

# =============================================================================
# Generic Tool Input/Response Structures
# =============================================================================

class GenericToolInput(TypedDict, Generic[T]):
    """Generic tool input structure with type parameter."""
    tool_specific_data: T
    
    # Common fields that all tools might have
    description: NotRequired[str]
    timeout: NotRequired[int]

class GenericToolResponse(TypedDict, Generic[T]):
    """Generic tool response structure with type parameter."""
    success: bool
    data: T
    error: Optional[str]
    timestamp: str

# Specific tool input data types
class BashInputData(TypedDict):
    """Bash-specific input data."""
    command: str
    working_directory: NotRequired[str]

class FileInputData(TypedDict):
    """File operation input data."""
    file_path: str
    old_string: NotRequired[str]
    new_string: NotRequired[str]
    edits: NotRequired[List[Dict[str, Any]]]
    offset: NotRequired[Optional[int]]
    limit: NotRequired[Optional[int]]

class SearchInputData(TypedDict):
    """Search tool input data."""
    pattern: str
    path: NotRequired[str]
    include: NotRequired[str]

class WebInputData(TypedDict):
    """Web fetch input data."""
    url: str
    prompt: str

# Specific tool response data types
class BashOutputData(TypedDict):
    """Bash command output data."""
    stdout: str
    stderr: str
    return_code: int
    interrupted: bool

class FileOutputData(TypedDict):
    """File operation output data."""
    file_path: str
    lines_affected: NotRequired[int]
    content_length: NotRequired[int]

class SearchOutputData(TypedDict):
    """Search operation output data."""
    matches: List[str]
    total_count: int

class WebOutputData(TypedDict):
    """Web fetch output data."""
    content: str
    content_type: str
    status_code: int

# Type aliases for specific tool types
BashToolInput = GenericToolInput[BashInputData]
FileToolInput = GenericToolInput[FileInputData]
SearchToolInput = GenericToolInput[SearchInputData]
WebToolInput = GenericToolInput[WebInputData]

BashToolResponse = GenericToolResponse[BashOutputData]
FileToolResponse = GenericToolResponse[FileOutputData]
SearchToolResponse = GenericToolResponse[SearchOutputData]
WebToolResponse = GenericToolResponse[WebOutputData]

# =============================================================================
# Generic Event Data Structures
# =============================================================================

class GenericEventData(BaseEventData, Generic[TInput, TResponse]):
    """Generic event data structure with tool input/response types."""
    tool_name: str
    tool_input: TInput
    tool_response: NotRequired[TResponse]
    execution_time: NotRequired[float]
    metadata: NotRequired[Dict[str, Any]]

# Specific event data types
PreToolUseEventData = GenericEventData[TInput, None]
PostToolUseEventData = GenericEventData[TInput, TResponse]

# =============================================================================
# Generic Message Structures
# =============================================================================

class GenericDiscordMessage(TypedDict, Generic[T]):
    """Generic Discord message structure."""
    content: NotRequired[str]
    embeds: List[T]
    attachments: NotRequired[List[Dict[str, Any]]]
    flags: NotRequired[int]

class GenericDiscordEmbed(TypedDict, Generic[T]):
    """Generic Discord embed structure."""
    title: NotRequired[str]
    description: NotRequired[str]
    color: NotRequired[int]
    timestamp: NotRequired[str]
    footer: NotRequired[Dict[str, str]]
    fields: NotRequired[List[T]]

class EmbedField(TypedDict):
    """Discord embed field structure."""
    name: str
    value: str
    inline: NotRequired[bool]

# Type aliases for specific message types
StandardDiscordEmbed = GenericDiscordEmbed[EmbedField]
StandardDiscordMessage = GenericDiscordMessage[StandardDiscordEmbed]

# =============================================================================
# Generic Formatter Protocol
# =============================================================================

class GenericFormatter(Protocol, Generic[TEventData, TMessage]):
    """Generic formatter protocol."""
    
    def format(self, event_data: TEventData, session_id: str) -> TMessage:
        """Format event data into message."""
        ...

class EventFormatter(GenericFormatter[TEventData, StandardDiscordMessage]):
    """Base event formatter class."""
    
    def format(self, event_data: TEventData, session_id: str) -> StandardDiscordMessage:
        """Format event data into Discord message."""
        # Implementation would be here
        pass

# =============================================================================
# Generic Registry Pattern
# =============================================================================

class GenericRegistry(Generic[T]):
    """Generic registry for managing type-safe collections."""
    
    def __init__(self) -> None:
        self._items: Dict[str, T] = {}
    
    def register(self, key: str, item: T) -> None:
        """Register an item with a key."""
        self._items[key] = item
    
    def get(self, key: str) -> Optional[T]:
        """Get an item by key."""
        return self._items.get(key)
    
    def get_all(self) -> Dict[str, T]:
        """Get all registered items."""
        return self._items.copy()

# Specific registry types
FormatterRegistry = GenericRegistry[GenericFormatter[Any, StandardDiscordMessage]]
ConfigRegistry = GenericRegistry[ConfigProtocol]

# =============================================================================
# Generic HTTP Client Pattern
# =============================================================================

class GenericHTTPResponse(TypedDict, Generic[T]):
    """Generic HTTP response structure."""
    status_code: int
    headers: Dict[str, str]
    data: T
    success: bool

class GenericHTTPClient(Generic[TConfig]):
    """Generic HTTP client with configuration type."""
    
    def __init__(self, config: TConfig) -> None:
        self.config = config
    
    def post(self, url: str, data: T, headers: Optional[Dict[str, str]] = None) -> GenericHTTPResponse[T]:
        """Generic POST method."""
        # Implementation would be here
        pass

# =============================================================================
# Generic Validation Pattern
# =============================================================================

class GenericValidator(Generic[T]):
    """Generic validator for type-safe validation."""
    
    def __init__(self, validator_func: Callable[[T], bool]) -> None:
        self.validator_func = validator_func
    
    def validate(self, item: T) -> bool:
        """Validate an item."""
        return self.validator_func(item)
    
    def validate_all(self, items: List[T]) -> List[bool]:
        """Validate multiple items."""
        return [self.validate(item) for item in items]

# Type guards with generics
def is_tool_input_type(obj: Any, input_type: Type[TInput]) -> TypeGuard[TInput]:
    """Generic type guard for tool input types."""
    # Implementation would check if obj matches the input_type structure
    return isinstance(obj, dict) and hasattr(input_type, '__annotations__')

def is_event_data_type(obj: Any, event_type: Type[TEventData]) -> TypeGuard[TEventData]:
    """Generic type guard for event data types."""
    # Implementation would check if obj matches the event_type structure
    return isinstance(obj, dict) and 'session_id' in obj

# =============================================================================
# Generic Factory Pattern
# =============================================================================

class GenericFactory(Generic[T]):
    """Generic factory for creating instances."""
    
    def __init__(self, creator_func: Callable[..., T]) -> None:
        self.creator_func = creator_func
    
    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance using the creator function."""
        return self.creator_func(*args, **kwargs)

# =============================================================================
# Generic Builder Pattern
# =============================================================================

class GenericBuilder(Generic[T]):
    """Generic builder pattern for constructing complex objects."""
    
    def __init__(self, target_type: Type[T]) -> None:
        self.target_type = target_type
        self._data: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any) -> 'GenericBuilder[T]':
        """Set a field value."""
        self._data[key] = value
        return self
    
    def build(self) -> T:
        """Build the target object."""
        # This would need actual implementation based on target_type
        return cast(T, self._data)

# Message builder example
class MessageBuilder(GenericBuilder[StandardDiscordMessage]):
    """Builder for Discord messages."""
    
    def add_embed(self, embed: StandardDiscordEmbed) -> 'MessageBuilder':
        """Add an embed to the message."""
        if 'embeds' not in self._data:
            self._data['embeds'] = []
        self._data['embeds'].append(embed)
        return self
    
    def set_content(self, content: str) -> 'MessageBuilder':
        """Set message content."""
        self._data['content'] = content
        return self

# =============================================================================
# Generic Processing Pipeline
# =============================================================================

class GenericProcessor(Generic[T]):
    """Generic processor for transformation pipelines."""
    
    def process(self, input_data: T) -> T:
        """Process the input data."""
        return input_data

class ProcessorChain(Generic[T]):
    """Chain of processors for pipeline processing."""
    
    def __init__(self) -> None:
        self.processors: List[GenericProcessor[T]] = []
    
    def add_processor(self, processor: GenericProcessor[T]) -> 'ProcessorChain[T]':
        """Add a processor to the chain."""
        self.processors.append(processor)
        return self
    
    def process(self, input_data: T) -> T:
        """Process data through the entire chain."""
        result = input_data
        for processor in self.processors:
            result = processor.process(result)
        return result

# =============================================================================
# Example Usage and Benefits
# =============================================================================

def example_usage():
    """Example demonstrating the benefits of generic types."""
    
    # Type-safe tool input creation
    bash_input: BashToolInput = {
        'tool_specific_data': {'command': 'ls -la'},
        'description': 'List directory contents'
    }
    
    # Type-safe event data
    event_data: PreToolUseEventData[BashToolInput] = {
        'session_id': 'abc123',
        'transcript_path': '/path/to/transcript',
        'hook_event_name': 'PreToolUse',
        'tool_name': 'Bash',
        'tool_input': bash_input
    }
    
    # Type-safe registry
    formatter_registry = FormatterRegistry()
    bash_formatter = EventFormatter()
    formatter_registry.register('bash', bash_formatter)
    
    # Type-safe builder
    message_builder = MessageBuilder(StandardDiscordMessage)
    embed: StandardDiscordEmbed = {
        'title': 'Test Embed',
        'description': 'This is a test'
    }
    message = message_builder.add_embed(embed).set_content('Hello!').build()
    
    # Type-safe validation
    validator = GenericValidator(lambda x: isinstance(x, dict) and 'command' in x)
    is_valid = validator.validate(bash_input['tool_specific_data'])
    
    return {
        'bash_input': bash_input,
        'event_data': event_data,
        'message': message,
        'is_valid': is_valid
    }

# =============================================================================
# Benefits Summary
# =============================================================================

"""
Benefits of using Generic types and TypeVar:

1. **Type Safety**: Compile-time type checking prevents runtime errors
2. **Reusability**: Generic structures can be reused with different types
3. **Maintainability**: Changes to base types propagate to all derived types
4. **Documentation**: Generic constraints serve as documentation
5. **IDE Support**: Better autocomplete and refactoring support
6. **Extensibility**: Easy to add new tool types without duplicating code
7. **Consistency**: Enforces consistent patterns across the codebase
8. **Testing**: Easier to create type-safe mocks and test data

Specific improvements for the Discord notifier:

1. **Tool Input/Response Uniformity**: All tools follow the same pattern
2. **Event Data Consistency**: All events have the same base structure
3. **Message Building**: Type-safe message construction
4. **Formatter Registry**: Type-safe formatter management
5. **HTTP Client**: Generic response handling
6. **Validation**: Reusable validation patterns
7. **Factory Pattern**: Type-safe object creation
8. **Builder Pattern**: Fluent API for complex objects
"""

if __name__ == "__main__":
    result = example_usage()
    print("Generic types example completed successfully!")
    print(f"Result keys: {list(result.keys())}")