"""Type definitions for AstolfoLogger module."""

from typing import TypedDict, Union, Optional, Protocol, TypeVar, ParamSpec, Callable
from typing_extensions import TypeAlias, NotRequired

# JSON type definitions
JsonPrimitive: TypeAlias = Union[str, int, float, bool, None]
JsonValue: TypeAlias = Union[JsonPrimitive, dict[str, "JsonValue"], list["JsonValue"]]
JsonDict: TypeAlias = dict[str, JsonValue]

# Context types
ContextValue: TypeAlias = Union[str, int, float, bool, None, list[str]]
ContextDict: TypeAlias = dict[str, ContextValue]

# Error information
class ErrorDict(TypedDict):
    """Structured error information."""
    type: str
    message: str
    stack_trace: str

# Memory information
class MemoryDict(TypedDict):
    """Memory usage information."""
    rss_mb: int
    available_mb: int
    percent: float

# Performance metrics
class PerformanceDict(TypedDict):
    """Performance metrics."""
    duration_ms: float
    cpu_percent: NotRequired[float]
    memory_mb: NotRequired[float]

# Log entry structure
class LogDict(TypedDict, total=False):
    """Complete log entry structure."""
    timestamp: str
    level: str
    event: str
    session_id: str
    correlation_id: str
    context: ContextDict
    error: ErrorDict
    memory: MemoryDict
    performance: PerformanceDict
    tags: list[str]
    
# Function types
P = ParamSpec('P')
T = TypeVar('T')
LoggableFunc = Callable[P, T]

# Logger protocol
class LoggerProtocol(Protocol):
    """Protocol for logger implementations."""
    def debug(self, message: str, **kwargs: ContextValue) -> None: ...
    def info(self, message: str, **kwargs: ContextValue) -> None: ...
    def warning(self, message: str, **kwargs: ContextValue) -> None: ...
    def error(self, message: str, error: Optional[Exception] = None, **kwargs: ContextValue) -> None: ...
    def event(self, event_name: str, **context: ContextValue) -> None: ...

# Configuration types
class LogRotationConfig(TypedDict):
    """Log rotation configuration."""
    max_file_size_mb: int
    max_files: int
    compress_old_files: bool

class MemoryLogConfig(TypedDict):
    """Memory log configuration."""
    max_logs: int
    auto_save: bool
    save_interval_seconds: int

class AstolfoLoggerConfig(TypedDict, total=False):
    """Complete logger configuration."""
    debug_level: int
    log_file: str
    rotation: LogRotationConfig
    memory: MemoryLogConfig
    session_id: str