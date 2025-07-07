#!/usr/bin/env python3
"""
Improved Generic Types Implementation for Discord Notifier.

This file demonstrates practical implementations of Generic types and TypeVar 
that can be directly integrated into the Discord notifier codebase.
"""

from typing import (
    Any,
    TypedDict,
    TypeGuard,
    Protocol,
    NotRequired,
    Generic,
    TypeVar,
    runtime_checkable,
    Callable,
    Mapping,
    Sequence,
)
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

# =============================================================================
# Type Variables with Proper Constraints
# =============================================================================

# Generic type variables
T = TypeVar('T')
TConfig = TypeVar('TConfig', bound='BaseConfig')
TInput = TypeVar('TInput', bound='BaseToolInput')
TResponse = TypeVar('TResponse')
TEventData = TypeVar('TEventData', bound='BaseEventData')

# Constrained type variables for specific domains
ToolNameT = TypeVar('ToolNameT', bound=str)
EventTypeT = TypeVar('EventTypeT', bound=str)

# Covariant/Contravariant type variables for protocols
T_co = TypeVar('T_co', covariant=True)  # Output type (covariant)
T_contra = TypeVar('T_contra', contravariant=True)  # Input type (contravariant)

# =============================================================================
# Base Protocol Definitions
# =============================================================================

@runtime_checkable
class BaseConfig(Protocol):
    """Base configuration protocol."""
    webhook_url: str | None
    bot_token: str | None
    channel_id: str | None
    debug: bool

@runtime_checkable
class BaseToolInput(Protocol):
    """Base tool input protocol."""
    pass

@runtime_checkable
class BaseEventData(Protocol):
    """Base event data protocol."""
    session_id: str
    transcript_path: str
    hook_event_name: str

# =============================================================================
# Generic Result/Response Pattern
# =============================================================================

class Result(Generic[T], TypedDict):
    """Generic result structure for operations."""
    success: bool
    data: T
    error: str | None
    metadata: dict[str, Any] | None

class AsyncResult(Generic[T], TypedDict):
    """Generic async result structure."""
    success: bool
    data: T
    error: str | None
    execution_time: float
    timestamp: str

# =============================================================================
# Generic Tool System
# =============================================================================

class BaseToolInputType(TypedDict):
    """Base tool input type."""
    description: NotRequired[str]
    timeout: NotRequired[int]

class GenericToolInput(BaseToolInputType, Generic[T]):
    """Generic tool input with specific data."""
    tool_data: T

class GenericToolResponse(Generic[T]):
    """Generic tool response."""
    
    def __init__(self, success: bool, data: T, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error

# Tool-specific input types
class BashToolData(TypedDict):
    """Bash tool specific data."""
    command: str
    working_directory: NotRequired[str]
    environment: NotRequired[dict[str, str]]

class FileToolData(TypedDict):
    """File tool specific data."""
    file_path: str
    operation: str  # 'read', 'write', 'edit'
    content: NotRequired[str]
    old_string: NotRequired[str]
    new_string: NotRequired[str]

class SearchToolData(TypedDict):
    """Search tool specific data."""
    pattern: str
    path: NotRequired[str]
    include_filter: NotRequired[str]
    exclude_filter: NotRequired[str]

# Type aliases for specific tools
BashInput = GenericToolInput[BashToolData]
FileInput = GenericToolInput[FileToolData]
SearchInput = GenericToolInput[SearchToolData]

# =============================================================================
# Generic Event System
# =============================================================================

class GenericEventData(Generic[TInput, TResponse]):
    """Generic event data structure."""
    
    def __init__(
        self,
        session_id: str,
        transcript_path: str,
        hook_event_name: str,
        tool_name: str,
        tool_input: TInput,
        tool_response: TResponse | None = None,
        metadata: dict[str, Any] | None = None
    ):
        self.session_id = session_id
        self.transcript_path = transcript_path
        self.hook_event_name = hook_event_name
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_response = tool_response
        self.metadata = metadata or {}

# Event type aliases
PreToolUseEvent = GenericEventData[TInput, None]
PostToolUseEvent = GenericEventData[TInput, TResponse]

# =============================================================================
# Generic Formatter System
# =============================================================================

class FormatterProtocol(Protocol[T_contra, T_co]):
    """Protocol for formatters with proper variance."""
    
    def format(self, input_data: T_contra) -> T_co:
        """Format input data to output format."""
        ...

class GenericFormatter(Generic[TEventData, T]):
    """Generic formatter base class."""
    
    def __init__(self, format_func: Callable[[TEventData, str], T]):
        self._format_func = format_func
    
    def format(self, event_data: TEventData, session_id: str) -> T:
        """Format event data."""
        return self._format_func(event_data, session_id)

# =============================================================================
# Generic Registry Pattern
# =============================================================================

class TypedRegistry(Generic[T]):
    """Type-safe registry for managing collections."""
    
    def __init__(self) -> None:
        self._items: dict[str, T] = {}
    
    def register(self, key: str, item: T) -> None:
        """Register an item."""
        self._items[key] = item
    
    def get(self, key: str) -> T | None:
        """Get an item by key."""
        return self._items.get(key)
    
    def get_all(self) -> dict[str, T]:
        """Get all items."""
        return self._items.copy()
    
    def has(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._items
    
    def remove(self, key: str) -> bool:
        """Remove an item."""
        if key in self._items:
            del self._items[key]
            return True
        return False

# =============================================================================
# Generic Builder Pattern
# =============================================================================

class GenericBuilder(Generic[T], ABC):
    """Abstract generic builder."""
    
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
    
    @abstractmethod
    def build(self) -> T:
        """Build the target object."""
        ...
    
    def set_field(self, key: str, value: Any) -> 'GenericBuilder[T]':
        """Set a field value."""
        self._data[key] = value
        return self

# =============================================================================
# Generic Validation System
# =============================================================================

class ValidationResult(Generic[T]):
    """Generic validation result."""
    
    def __init__(self, is_valid: bool, data: T, errors: list[str] | None = None):
        self.is_valid = is_valid
        self.data = data
        self.errors = errors or []

class GenericValidator(Generic[T]):
    """Generic validator."""
    
    def __init__(self, validation_rules: list[Callable[[T], bool]]):
        self.validation_rules = validation_rules
    
    def validate(self, item: T) -> ValidationResult[T]:
        """Validate an item."""
        errors = []
        for rule in self.validation_rules:
            try:
                if not rule(item):
                    errors.append(f"Validation rule failed for {type(item).__name__}")
            except Exception as e:
                errors.append(f"Validation error: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            data=item,
            errors=errors
        )

# =============================================================================
# Generic Processing Pipeline
# =============================================================================

class ProcessorProtocol(Protocol[T]):
    """Protocol for data processors."""
    
    def process(self, data: T) -> T:
        """Process data."""
        ...

class GenericProcessor(Generic[T]):
    """Generic data processor."""
    
    def __init__(self, process_func: Callable[[T], T]):
        self._process_func = process_func
    
    def process(self, data: T) -> T:
        """Process data using the provided function."""
        return self._process_func(data)

class ProcessingPipeline(Generic[T]):
    """Generic processing pipeline."""
    
    def __init__(self) -> None:
        self.processors: list[ProcessorProtocol[T]] = []
    
    def add_processor(self, processor: ProcessorProtocol[T]) -> 'ProcessingPipeline[T]':
        """Add a processor to the pipeline."""
        self.processors.append(processor)
        return self
    
    def process(self, data: T) -> T:
        """Process data through all processors."""
        result = data
        for processor in self.processors:
            result = processor.process(result)
        return result

# =============================================================================
# Generic HTTP Client
# =============================================================================

class HTTPRequest(Generic[T]):
    """Generic HTTP request."""
    
    def __init__(self, url: str, method: str, data: T, headers: dict[str, str] | None = None):
        self.url = url
        self.method = method
        self.data = data
        self.headers = headers or {}

class HTTPResponse(Generic[T]):
    """Generic HTTP response."""
    
    def __init__(self, status_code: int, data: T, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.data = data
        self.headers = headers or {}
        self.success = 200 <= status_code < 300

class GenericHTTPClient(Generic[TConfig]):
    """Generic HTTP client with typed configuration."""
    
    def __init__(self, config: TConfig):
        self.config = config
    
    def send_request(self, request: HTTPRequest[T]) -> HTTPResponse[T]:
        """Send a request (mock implementation)."""
        # In a real implementation, this would make the actual HTTP request
        return HTTPResponse(200, request.data)

# =============================================================================
# Practical Discord Notifier Types
# =============================================================================

class DiscordEmbedField(TypedDict):
    """Discord embed field."""
    name: str
    value: str
    inline: NotRequired[bool]

class DiscordEmbed(TypedDict):
    """Discord embed structure."""
    title: NotRequired[str]
    description: NotRequired[str]
    color: NotRequired[int]
    timestamp: NotRequired[str]
    footer: NotRequired[dict[str, str]]
    fields: NotRequired[list[DiscordEmbedField]]

class DiscordMessage(TypedDict):
    """Discord message structure."""
    content: NotRequired[str]
    embeds: NotRequired[list[DiscordEmbed]]

# Generic Discord message types
DiscordMessageBuilder = GenericBuilder[DiscordMessage]
DiscordMessageValidator = GenericValidator[DiscordMessage]
DiscordMessageProcessor = GenericProcessor[DiscordMessage]

# =============================================================================
# Type Guards and Runtime Checks
# =============================================================================

def is_valid_tool_input(obj: Any, expected_type: type[TInput]) -> TypeGuard[TInput]:
    """Type guard for tool input validation."""
    if not isinstance(obj, dict):
        return False
    
    # Check for required fields based on the expected type
    required_fields = getattr(expected_type, '__required_keys__', set())
    return all(field in obj for field in required_fields)

def is_valid_event_data(obj: Any) -> TypeGuard[BaseEventData]:
    """Type guard for event data validation."""
    return (
        isinstance(obj, dict) and 
        'session_id' in obj and 
        'transcript_path' in obj and 
        'hook_event_name' in obj
    )

# =============================================================================
# Factory Pattern with Generics
# =============================================================================

class GenericFactory(Generic[T]):
    """Generic factory for creating typed objects."""
    
    def __init__(self, creator: Callable[..., T]):
        self._creator = creator
    
    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance."""
        return self._creator(*args, **kwargs)

# =============================================================================
# Practical Usage Examples
# =============================================================================

class DiscordNotifierConfig(TypedDict):
    """Discord notifier configuration."""
    webhook_url: str | None
    bot_token: str | None
    channel_id: str | None
    debug: bool
    use_threads: bool
    channel_type: str
    thread_prefix: str
    mention_user_id: str | None

class DiscordNotifierTypes:
    """Type aliases for Discord notifier."""
    
    # Configuration types
    Config = DiscordNotifierConfig
    ConfigRegistry = TypedRegistry[Config]
    ConfigValidator = GenericValidator[Config]
    
    # Tool types
    BashTool = GenericToolInput[BashToolData]
    FileTool = GenericToolInput[FileToolData]
    SearchTool = GenericToolInput[SearchToolData]
    
    # Event types
    PreToolEvent = GenericEventData[BaseToolInput, None]
    PostToolEvent = GenericEventData[BaseToolInput, Any]
    
    # Formatter types
    EventFormatter = GenericFormatter[GenericEventData[Any, Any], DiscordMessage]
    FormatterRegistry = TypedRegistry[EventFormatter]
    
    # HTTP client types
    HTTPClient = GenericHTTPClient[Config]
    
    # Processing types
    MessageProcessor = GenericProcessor[DiscordMessage]
    MessagePipeline = ProcessingPipeline[DiscordMessage]

# =============================================================================
# Example Integration Function
# =============================================================================

def create_typed_discord_notifier():
    """Example of creating a typed Discord notifier system."""
    
    # Create typed configuration
    config: DiscordNotifierConfig = {
        'webhook_url': 'https://discord.com/api/webhooks/...',
        'bot_token': None,
        'channel_id': None,
        'debug': False,
        'use_threads': False,
        'channel_type': 'text',
        'thread_prefix': 'Session',
        'mention_user_id': None
    }
    
    # Create typed registries
    config_registry = TypedRegistry[DiscordNotifierConfig]()
    formatter_registry = TypedRegistry[GenericFormatter[Any, DiscordMessage]]()
    
    # Create typed validators
    config_validator = GenericValidator[DiscordNotifierConfig]([
        lambda cfg: cfg['webhook_url'] is not None or (cfg['bot_token'] is not None and cfg['channel_id'] is not None),
        lambda cfg: cfg['channel_type'] in ['text', 'forum']
    ])
    
    # Create typed HTTP client
    http_client = GenericHTTPClient(config)
    
    # Create typed processors
    message_processor = GenericProcessor[DiscordMessage](
        lambda msg: {**msg, 'content': msg.get('content', '') + ' [Processed]'}
    )
    
    # Create processing pipeline
    pipeline = ProcessingPipeline[DiscordMessage]()
    pipeline.add_processor(message_processor)
    
    return {
        'config': config,
        'config_registry': config_registry,
        'formatter_registry': formatter_registry,
        'config_validator': config_validator,
        'http_client': http_client,
        'pipeline': pipeline
    }

# =============================================================================
# Benefits Documentation
# =============================================================================

"""
Benefits of this Generic Types Implementation:

1. **Type Safety**: 
   - Compile-time type checking prevents runtime errors
   - IDE provides better autocomplete and error detection
   - Refactoring becomes safer and more reliable

2. **Reusability**:
   - Generic structures can be reused with different types
   - Common patterns (Registry, Builder, Validator) work with any type
   - Reduces code duplication across different tool types

3. **Maintainability**:
   - Changes to base types propagate automatically
   - Consistent patterns make code easier to understand
   - Generic constraints serve as documentation

4. **Extensibility**:
   - Easy to add new tool types without duplicating code
   - New event types can be added with minimal changes
   - Formatters can be created for any event type

5. **Testing**:
   - Type-safe mocks and test data
   - Generic test utilities can be reused
   - Better coverage through type-driven testing

6. **Performance**:
   - Runtime type checking only when needed
   - Generic constraints are compile-time only
   - No performance overhead in production

Specific Improvements for Discord Notifier:

1. **Tool System**: All tools follow the same generic pattern
2. **Event Handling**: Consistent event data structures with type parameters
3. **Message Building**: Type-safe Discord message construction
4. **Configuration**: Typed configuration with validation
5. **HTTP Client**: Generic request/response handling
6. **Processing Pipeline**: Composable message processing
7. **Registry Pattern**: Type-safe component registration
8. **Validation**: Reusable validation patterns with proper error handling
"""

if __name__ == "__main__":
    # Example usage
    notifier_components = create_typed_discord_notifier()
    
    # Validate configuration
    config = notifier_components['config']
    validator = notifier_components['config_validator']
    validation_result = validator.validate(config)
    
    print(f"Configuration valid: {validation_result.is_valid}")
    if not validation_result.is_valid:
        print(f"Validation errors: {validation_result.errors}")
    
    # Test message processing
    test_message: DiscordMessage = {
        'content': 'Hello, World!',
        'embeds': [{
            'title': 'Test Embed',
            'description': 'This is a test embed'
        }]
    }
    
    pipeline = notifier_components['pipeline']
    processed_message = pipeline.process(test_message)
    
    print(f"Original message: {test_message}")
    print(f"Processed message: {processed_message}")
    print("\nGeneric types implementation completed successfully!")