#!/usr/bin/env python3
"""Astolfo Logger - AI-optimized structured logging for Claude Code Discord Notifier.

This module provides structured logging specifically designed for AI debugging and
development by multiple Astolfo instances. Inspired by vibe-logger's philosophy.
"""

import json
import logging
import os
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, Union, Protocol, TypeVar, Callable, ParamSpec, cast, Any, Mapping, TYPE_CHECKING
from typing import get_type_hints

# Import type definitions
from src.utils.astolfo_logger_types import (
    JsonValue,
    JsonDict,
    ContextDict,
    ContextValue,
    ErrorDict,
    MemoryDict,
    PerformanceDict,
    LogDict,
    LoggableFunc,
    LoggerProtocol,
    P,
    T,
)


@dataclass
class AstolfoLog:
    """Structured log entry optimized for AI comprehension.
    
    Each log entry contains rich contextual information to help
    Astolfo instances understand what happened and why.
    """
    
    # Basic fields
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    level: str = "INFO"
    event: str = ""
    
    # Context fields
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    context: dict[str, ContextValue] = field(default_factory=dict)
    
    # Error information
    error: Optional[ErrorDict] = None
    
    # AI-specific fields
    ai_todo: Optional[str] = None
    human_note: Optional[str] = None
    astolfo_note: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[int] = None
    memory_usage: Optional[MemoryDict] = None
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        # Build dict from known fields
        data: dict[str, JsonValue] = {}
        
        # Add required fields
        data['timestamp'] = self.timestamp
        data['level'] = self.level
        data['event'] = self.event
        
        # Add optional fields if present
        if self.session_id is not None:
            data['session_id'] = self.session_id
        if self.correlation_id is not None:
            data['correlation_id'] = self.correlation_id
        if self.context:
            data['context'] = cast(JsonValue, self.context)
        if self.error is not None:
            data['error'] = cast(JsonValue, self.error)
        if self.ai_todo is not None:
            data['ai_todo'] = self.ai_todo
        if self.human_note is not None:
            data['human_note'] = self.human_note
        if self.astolfo_note is not None:
            data['astolfo_note'] = self.astolfo_note
        if self.duration_ms is not None:
            data['duration_ms'] = self.duration_ms
        if self.memory_usage is not None:
            data['memory_usage'] = cast(JsonValue, self.memory_usage)
            
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    
    def to_dict(self) -> LogDict:
        """Convert log entry to dictionary."""
        result: LogDict = {}
        
        # Explicitly handle each known field
        if self.timestamp is not None:
            result['timestamp'] = self.timestamp
        if self.level is not None:
            result['level'] = self.level
        if self.event:
            result['event'] = self.event
        if self.session_id is not None:
            result['session_id'] = self.session_id
        if self.correlation_id is not None:
            result['correlation_id'] = self.correlation_id
        if self.context:
            result['context'] = self.context
        if self.error is not None:
            result['error'] = self.error
        if self.memory_usage is not None:
            result['memory'] = self.memory_usage
        if self.duration_ms is not None:
            result['performance'] = PerformanceDict(duration_ms=float(self.duration_ms))
            
        return result


class AstolfoLogger:
    """Logger wrapper that provides structured logging for AI debugging."""
    
    def __init__(self, name: str, debug_level: int = 1):
        """Initialize the logger.
        
        Args:
            name: Logger name (usually __name__)
            debug_level: Debug verbosity level (1-3)
                1: Basic debug info
                2: API communication details
                3: All function inputs/outputs
        """
        self.logger = logging.getLogger(name)
        self.debug_level = debug_level
        self.session_id: Optional[str] = None
        self._start_times: dict[str, float] = {}
        
    def set_session_id(self, session_id: str) -> None:
        """Set the current session ID for all logs."""
        self.session_id = session_id
        
    def _create_log(
        self,
        level: str,
        event: str,
        **kwargs: Union[ContextValue, ContextDict, ErrorDict, MemoryDict]
    ) -> AstolfoLog:
        """Create a structured log entry."""
        # Initialize with defaults
        final_context: dict[str, ContextValue] = {}
        final_error: Optional[ErrorDict] = None
        final_ai_todo: Optional[str] = None
        final_human_note: Optional[str] = None
        final_astolfo_note: Optional[str] = None
        final_duration_ms: Optional[int] = None
        final_memory_usage: Optional[MemoryDict] = None
        final_correlation_id: Optional[str] = None
        
        # Process kwargs
        for key, value in kwargs.items():
            if key == 'correlation_id' and isinstance(value, str):
                final_correlation_id = value
            elif key == 'context' and isinstance(value, dict):
                # Verify it's a valid ContextDict
                if all(isinstance(k, str) and isinstance(v, (str, int, float, bool, list, type(None))) for k, v in value.items()):
                    final_context = cast(dict[str, ContextValue], value)
            elif key == 'error' and isinstance(value, dict):
                # Verify it's a valid ErrorDict
                if 'type' in value and 'message' in value and 'stack_trace' in value:
                    final_error = cast(ErrorDict, value)
            elif key == 'ai_todo' and isinstance(value, str):
                final_ai_todo = value
            elif key == 'human_note' and isinstance(value, str):
                final_human_note = value
            elif key == 'astolfo_note' and isinstance(value, str):
                final_astolfo_note = value
            elif key == 'duration_ms' and isinstance(value, int):
                final_duration_ms = value
            elif key == 'memory_usage' and isinstance(value, dict):
                # Verify it's a valid MemoryDict
                if 'rss_mb' in value and 'available_mb' in value and 'percent' in value:
                    final_memory_usage = cast(MemoryDict, value)
        
        # Build log entry
        log = AstolfoLog(
            level=level,
            event=event,
            session_id=self.session_id,
            correlation_id=final_correlation_id,
            context=final_context,
            error=final_error,
            ai_todo=final_ai_todo,
            human_note=final_human_note,
            astolfo_note=final_astolfo_note,
            duration_ms=final_duration_ms,
            memory_usage=final_memory_usage
        )
        return log
    
    def debug(self, *args: Union[str, int, float], **kwargs: Union[ContextValue, ContextDict, ErrorDict, MemoryDict]) -> None:
        """Log debug information.
        
        Supports both structured logging and standard logging format.
        """
        if self.debug_level >= 1:
            if len(args) == 1 and isinstance(args[0], str) and not kwargs:
                # Simple string message
                self.logger.debug(args[0])
            elif len(args) >= 2 and isinstance(args[0], str) and '%' in args[0]:
                # Printf-style formatting
                self.logger.debug(args[0], *args[1:])
            else:
                # Structured logging
                event = args[0] if args else "debug"
                log = self._create_log("DEBUG", str(event), **kwargs)
                self.logger.debug(log.to_json())
    
    def info(self, *args: Union[str, int, float], **kwargs: Union[ContextValue, ContextDict, ErrorDict, MemoryDict]) -> None:
        """Log information.
        
        Supports both structured logging and standard logging format.
        """
        if len(args) == 1 and isinstance(args[0], str) and not kwargs:
            # Simple string message
            self.logger.info(args[0])
        elif len(args) >= 2 and isinstance(args[0], str) and '%' in args[0]:
            # Printf-style formatting
            self.logger.info(args[0], *args[1:])
        else:
            # Structured logging
            event = args[0] if args else "info"
            log = self._create_log("INFO", str(event), **kwargs)
            self.logger.info(log.to_json())
    
    def warning(self, *args: Union[str, int, float], **kwargs: Union[ContextValue, ContextDict, ErrorDict, MemoryDict]) -> None:
        """Log warning.
        
        Supports both structured logging and standard logging format.
        """
        if len(args) == 1 and isinstance(args[0], str) and not kwargs:
            # Simple string message
            self.logger.warning(args[0])
        elif len(args) >= 2 and isinstance(args[0], str) and '%' in args[0]:
            # Printf-style formatting
            self.logger.warning(args[0], *args[1:])
        else:
            # Structured logging
            event = args[0] if args else "warning"
            log = self._create_log("WARNING", str(event), **kwargs)
            self.logger.warning(log.to_json())
    
    def error(self, *args: Union[str, int, float], exception: Optional[Exception] = None, **kwargs: Union[ContextValue, ContextDict, ErrorDict, MemoryDict]) -> None:
        """Log error with exception details.
        
        Supports both structured logging and standard logging format.
        """
        if len(args) == 1 and isinstance(args[0], str) and not kwargs and not exception:
            # Simple string message
            self.logger.error(args[0])
        elif len(args) >= 2 and isinstance(args[0], str) and '%' in args[0] and not exception:
            # Printf-style formatting
            self.logger.error(args[0], *args[1:])
        else:
            # Structured logging
            event = args[0] if args else "error"
            error_info: Optional[ErrorDict] = None
            if exception:
                error_info = ErrorDict(
                    type=type(exception).__name__,
                    message=str(exception),
                    stack_trace=traceback.format_exc()
                )
            
            # Filter out exception from kwargs if it was passed
            filtered_kwargs: dict[str, Union[ContextValue, ContextDict, ErrorDict, MemoryDict]] = {}
            for k, v in kwargs.items():
                if k != 'exception':
                    filtered_kwargs[k] = v
            
            if error_info:
                filtered_kwargs['error'] = error_info
                
            log = self._create_log("ERROR", str(event), **filtered_kwargs)
            self.logger.error(log.to_json())
    
    def exception(self, *args: Union[str, int, float], **kwargs: Union[ContextValue, ContextDict, ErrorDict, MemoryDict]) -> None:
        """Log exception with traceback.
        
        Supports both structured logging and standard logging format.
        """
        if len(args) == 1 and isinstance(args[0], str) and not kwargs:
            # Simple string message
            self.logger.exception(args[0])
        elif len(args) >= 2 and isinstance(args[0], str) and '%' in args[0]:
            # Printf-style formatting
            self.logger.exception(args[0], *args[1:])
        else:
            # Structured logging - capture current exception
            import sys
            exc_info = sys.exc_info()
            if exc_info[0]:
                exception = exc_info[1]
                event = args[0] if args else "exception"
                if isinstance(exception, Exception):
                    # Pass exception separately, not in kwargs
                    self.error(str(event), exception=exception)
                else:
                    # Handle non-Exception throwables
                    self.error(str(event))
            else:
                # No active exception, just log as error
                self.error(*args)
    
    def start_operation(self, operation_id: str) -> None:
        """Start timing an operation."""
        self._start_times[operation_id] = datetime.now(UTC).timestamp()
    
    def end_operation(self, operation_id: str) -> int:
        """End timing an operation and return duration in milliseconds."""
        if operation_id in self._start_times:
            duration_ms = int((datetime.now(UTC).timestamp() - self._start_times[operation_id]) * 1000)
            del self._start_times[operation_id]
            return duration_ms
        return 0
    
    def log_function_call(self, func_name: str, args: dict[str, JsonValue], level: int = 3) -> None:
        """Log function call with arguments (requires debug level 3)."""
        if self.debug_level >= level:
            context: ContextDict = {
                "function": func_name,
                "arguments": str(args)  # Convert to string for ContextValue compatibility
            }
            self.debug(
                f"{func_name}_called",
                context=context,
                ai_todo=f"Function {func_name} called with provided arguments"
            )
    
    def log_function_result(self, func_name: str, result: JsonValue, duration_ms: int, level: int = 3) -> None:
        """Log function result (requires debug level 3)."""
        if self.debug_level >= level:
            # Truncate large results
            result_preview: JsonValue
            if isinstance(result, str) and len(result) > 1000:
                result_preview = result[:1000] + "..."
            elif isinstance(result, (dict, list)) and len(str(result)) > 1000:
                result_preview = f"{type(result).__name__} with {len(result)} items"
            else:
                result_preview = result
                
            context: ContextDict = {
                "function": func_name,
                "result": str(result_preview),  # Convert to string for ContextValue compatibility
                "result_type": type(result).__name__
            }
            self.debug(
                f"{func_name}_completed",
                context=context,
                duration_ms=duration_ms,
                ai_todo=f"Function {func_name} completed successfully"
            )
    
    def log_api_request(self, method: str, url: str, headers: dict[str, str], body: Optional[JsonValue]) -> None:
        """Log API request details (requires debug level 2)."""
        if self.debug_level >= 2:
            # Hide sensitive headers
            safe_headers = {k: v if k.lower() != "authorization" else "***" for k, v in headers.items()}
            
            context: ContextDict = {
                "method": method,
                "url": url,
                "headers": str(safe_headers),  # Convert to string
                "body": str(body) if body else None,
                "body_size": len(json.dumps(body)) if body else 0
            }
            self.debug(
                "api_request",
                context=context,
                ai_todo="API request sent, response will follow"
            )
    
    def log_api_response(self, url: str, status: int, body: Optional[JsonValue], duration_ms: int) -> None:
        """Log API response details (requires debug level 2)."""
        if self.debug_level >= 2:
            body_str = str(body) if body else ""
            context: ContextDict = {
                "url": url,
                "status": status,
                "body": body_str if len(body_str) < 1000 else f"Large response ({len(body_str)} chars)",
                "success": 200 <= status < 300
            }
            self.debug(
                "api_response",
                context=context,
                duration_ms=duration_ms,
                ai_todo=f"API response received with status {status}"
            )
    
    def log_handover(self, completed_tasks: list[str], pending_tasks: list[str], notes: str) -> None:
        """Log handover information for the next Astolfo."""
        context: ContextDict = {
            "completed_tasks": ", ".join(completed_tasks),  # Convert list to string
            "pending_tasks": ", ".join(pending_tasks),  # Convert list to string
            "timestamp": datetime.now(UTC).isoformat()
        }
        self.info(
            "astolfo_handover",
            context=context,
            astolfo_note=notes,
            ai_todo="Review completed work and continue with pending tasks"
        )


def get_debug_level() -> int:
    """Get debug level from environment variable."""
    try:
        level = int(os.environ.get("DISCORD_DEBUG_LEVEL", "1"))
        return max(1, min(3, level))  # Clamp to 1-3
    except ValueError:
        return 1


def setup_astolfo_logger(name: str) -> AstolfoLogger:
    """Set up an Astolfo logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured AstolfoLogger instance
    """
    debug = os.environ.get("DISCORD_DEBUG", "0") == "1"
    debug_level = get_debug_level() if debug else 0
    
    # Configure underlying Python logger
    logger = logging.getLogger(name)
    
    if debug:
        log_dir = Path.home() / ".claude" / "hooks" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"discord_notifier_{datetime.now(UTC).strftime('%Y-%m-%d')}.log"
        
        # Set up handlers
        file_handler = logging.FileHandler(log_file, mode="a")
        console_handler = logging.StreamHandler()
        
        # Format for structured logs
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)
    else:
        # Production mode - only errors
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.handlers.clear()
        logger.addHandler(console_handler)
        logger.setLevel(logging.ERROR)
    
    return AstolfoLogger(name, debug_level)


# Example usage in decorators
def log_function_execution(logger: AstolfoLogger, level: int = 3) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to log function execution."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if logger.debug_level >= level:
                func_name = func.__name__
                
                # Create safe representations of arguments
                safe_args: list[str] = []
                for arg in args:
                    try:
                        safe_args.append(str(arg))
                    except Exception:
                        safe_args.append("<unprintable>")
                
                safe_kwargs: dict[str, str] = {}
                for k, v in kwargs.items():
                    try:
                        safe_kwargs[k] = str(v)
                    except Exception:
                        safe_kwargs[k] = "<unprintable>"
                
                # Log function call
                all_args: dict[str, JsonValue] = {
                    "args": cast(JsonValue, safe_args),
                    "kwargs": cast(JsonValue, safe_kwargs)
                }
                logger.log_function_call(func_name, all_args, level)
                
                # Time execution
                logger.start_operation(func_name)
                
                try:
                    result = func(*args, **kwargs)
                    duration_ms = logger.end_operation(func_name)
                    
                    # Create safe result representation
                    try:
                        if isinstance(result, (str, int, float, bool, type(None))):
                            safe_result: JsonValue = result
                        elif isinstance(result, (list, dict)):
                            safe_result = str(result)
                        else:
                            safe_result = f"<{type(result).__name__} object>"
                    except Exception:
                        safe_result = "<unprintable result>"
                    
                    logger.log_function_result(func_name, safe_result, duration_ms, level)
                    return result
                except Exception as e:
                    duration_ms = logger.end_operation(func_name)
                    context: ContextDict = {
                        "function": func_name, 
                        "args": str(all_args)
                    }
                    logger.error(
                        f"{func_name}_failed",
                        exception=e,
                        context=context,
                        duration_ms=duration_ms,
                        ai_todo=f"Function {func_name} failed with {type(e).__name__}. Check stack trace."
                    )
                    raise
            else:
                # If debug level is lower, just call the function
                return func(*args, **kwargs)
        
        return wrapper
    return decorator