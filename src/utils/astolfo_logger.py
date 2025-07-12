#!/usr/bin/env python3
"""Astolfo Logger - AI-optimized structured logging for Claude Code Discord Notifier.

This module provides structured logging specifically designed for AI debugging and
development by multiple Astolfo instances. Inspired by vibe-logger's philosophy.
"""

import json
import logging
import os
import traceback
import threading
import time
import gzip
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, Union, Protocol, TypeVar, Callable, ParamSpec, cast, Any, Mapping, TYPE_CHECKING
from typing import get_type_hints
from collections import deque

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
    LogRotationConfig,
    MemoryLogConfig,
    AstolfoLoggerConfig,
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
    """Logger wrapper that provides structured logging for AI debugging.
    
    Enhanced with log rotation, memory storage, and persistence features
    inspired by vibe-logger's architecture.
    """
    
    def __init__(self, name: str, debug_level: int = 1, config: Optional[AstolfoLoggerConfig] = None):
        """Initialize the logger.
        
        Args:
            name: Logger name (usually __name__)
            debug_level: Debug verbosity level (1-3)
                1: Basic debug info
                2: API communication details
                3: All function inputs/outputs
            config: Optional configuration override
        """
        self.logger = logging.getLogger(name)
        self.debug_level = debug_level
        self.session_id: Optional[str] = None
        self._start_times: dict[str, float] = {}
        
        # Memory log storage
        self._logs: deque[AstolfoLog] = deque(maxlen=1000)
        self._logs_lock = threading.Lock()
        
        # Log rotation settings
        self._rotation_config = LogRotationConfig(
            max_file_size_mb=10,
            max_files=5,
            compress_old_files=True
        )
        
        # Memory log settings
        self._memory_config = MemoryLogConfig(
            max_logs=1000,
            auto_save=True,
            save_interval_seconds=300  # 5 minutes
        )
        
        # Apply custom config if provided
        if config:
            if 'rotation' in config:
                self._rotation_config.update(config['rotation'])
            if 'memory' in config:
                self._memory_config.update(config['memory'])
            if 'session_id' in config:
                self.session_id = config['session_id']
                
        # Auto-save thread
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save = threading.Event()
        if self._memory_config['auto_save']:
            self._start_auto_save()
        
    def set_session_id(self, session_id: str) -> None:
        """Set the current session ID for all logs."""
        self.session_id = session_id
        
    def _start_auto_save(self) -> None:
        """Start the auto-save thread."""
        def auto_save_worker() -> None:
            while not self._stop_auto_save.is_set():
                self._stop_auto_save.wait(self._memory_config['save_interval_seconds'])
                if not self._stop_auto_save.is_set():
                    self.save_logs()
                    
        self._auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        self._auto_save_thread.start()
        
    def stop(self) -> None:
        """Stop the logger and save remaining logs."""
        self._stop_auto_save.set()
        if self._auto_save_thread:
            self._auto_save_thread.join(timeout=5)
        self.save_logs()
        
    def _rotate_log_file(self, log_file: Path) -> None:
        """Rotate log file if it exceeds max size."""
        if not log_file.exists():
            return
            
        file_size_mb = log_file.stat().st_size / (1024 * 1024)
        if file_size_mb < self._rotation_config['max_file_size_mb']:
            return
            
        # Find next available rotation number
        rotation_num = 1
        while True:
            rotated_file = log_file.with_suffix(f'.{rotation_num}.log')
            if self._rotation_config['compress_old_files']:
                rotated_file = rotated_file.with_suffix('.gz')
            if not rotated_file.exists():
                break
            rotation_num += 1
            
        # Rotate the file
        if self._rotation_config['compress_old_files']:
            with open(log_file, 'rb') as f_in:
                with gzip.open(rotated_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            log_file.unlink()
        else:
            log_file.rename(rotated_file)
            
        # Clean up old files
        self._cleanup_old_logs(log_file.parent, log_file.stem)
        
    def _cleanup_old_logs(self, log_dir: Path, base_name: str) -> None:
        """Remove old log files beyond max_files limit."""
        pattern = f"{base_name}.*.log*"
        # Create a proper function with type annotation
        def get_mtime(path: Path) -> float:
            return path.stat().st_mtime
        log_files = sorted(log_dir.glob(pattern), key=get_mtime, reverse=True)
        
        # Keep only max_files
        for old_file in log_files[self._rotation_config['max_files']:]:
            old_file.unlink()
            
    def add_log(self, log: AstolfoLog) -> None:
        """Add a log entry to memory storage."""
        with self._logs_lock:
            self._logs.append(log)
            
    def get_logs(self, limit: Optional[int] = None) -> list[AstolfoLog]:
        """Get logs from memory storage."""
        with self._logs_lock:
            logs = list(self._logs)
            if limit:
                return logs[-limit:]
            return logs
            
    def save_logs(self, file_path: Optional[Path] = None) -> None:
        """Save logs to file with rotation support."""
        if not file_path:
            log_dir = Path.home() / ".claude" / "hooks" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            file_path = log_dir / f"astolfo_logs_{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
            
        # Check rotation before writing
        self._rotate_log_file(file_path)
        
        # Write logs
        with self._logs_lock:
            logs_to_save = list(self._logs)
            
        if logs_to_save:
            with open(file_path, 'a') as f:
                for log in logs_to_save:
                    f.write(log.to_json() + '\n')
                    
    def load_logs(self, file_path: Path) -> list[AstolfoLog]:
        """Load logs from file."""
        logs: list[AstolfoLog] = []
        
        if not file_path.exists():
            return logs
            
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = cast(JsonDict, json.loads(line))
                        
                        # Extract values with proper typing
                        timestamp = str(data.get('timestamp', '')) if 'timestamp' in data else ''
                        level = str(data.get('level', 'INFO')) if 'level' in data else 'INFO'
                        event = str(data.get('event', '')) if 'event' in data else ''
                        session_id = str(data['session_id']) if 'session_id' in data and data['session_id'] is not None else None
                        correlation_id = str(data['correlation_id']) if 'correlation_id' in data and data['correlation_id'] is not None else None
                        
                        # Extract complex types
                        context_raw = data.get('context', {})
                        context = cast(dict[str, ContextValue], context_raw) if isinstance(context_raw, dict) else {}
                        
                        error_raw = data.get('error')
                        error = cast(ErrorDict, error_raw) if error_raw and isinstance(error_raw, dict) else None
                        
                        ai_todo = str(data['ai_todo']) if 'ai_todo' in data and data['ai_todo'] is not None else None
                        human_note = str(data['human_note']) if 'human_note' in data and data['human_note'] is not None else None
                        astolfo_note = str(data['astolfo_note']) if 'astolfo_note' in data and data['astolfo_note'] is not None else None
                        
                        duration_ms_raw = data.get('duration_ms')
                        duration_ms = int(duration_ms_raw) if duration_ms_raw is not None and isinstance(duration_ms_raw, (int, float)) else None
                        
                        memory_usage_raw = data.get('memory_usage')
                        memory_usage = cast(MemoryDict, memory_usage_raw) if memory_usage_raw and isinstance(memory_usage_raw, dict) else None
                        
                        log = AstolfoLog(
                            timestamp=timestamp,
                            level=level,
                            event=event,
                            session_id=session_id,
                            correlation_id=correlation_id,
                            context=context,
                            error=error,
                            ai_todo=ai_todo,
                            human_note=human_note,
                            astolfo_note=astolfo_note,
                            duration_ms=duration_ms,
                            memory_usage=memory_usage
                        )
                        logs.append(log)
        except Exception as e:
            self.logger.error(f"Failed to load logs from {file_path}: {e}")
            
        return logs
        
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
        
        # Add to memory storage
        self.add_log(log)
        
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


def setup_astolfo_logger(name: str, config: Optional[AstolfoLoggerConfig] = None) -> AstolfoLogger:
    """Set up an Astolfo logger instance.
    
    Args:
        name: Logger name (usually __name__)
        config: Optional configuration override
        
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
    
    # Create logger with enhanced features
    astolfo_logger = AstolfoLogger(name, debug_level, config)
    
    # Log startup info
    astolfo_logger.info(
        "astolfo_logger_initialized",
        context={
            "name": name,
            "debug_level": debug_level,
            "memory_logs": astolfo_logger._memory_config['max_logs'],
            "rotation_mb": astolfo_logger._rotation_config['max_file_size_mb']
        },
        human_note="AstolfoLogger initialized with vibelogger-inspired features",
        ai_todo="Monitor logs for performance and debugging insights"
    )
    
    return astolfo_logger


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