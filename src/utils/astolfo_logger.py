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
from typing import Any, Optional, Union


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
    context: dict[str, Any] = field(default_factory=dict)
    
    # Error information
    error: Optional[dict[str, Any]] = None
    
    # AI-specific fields
    ai_todo: Optional[str] = None
    human_note: Optional[str] = None
    astolfo_note: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[int] = None
    memory_usage: Optional[dict[str, int]] = None
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        # Filter out None values for cleaner output
        data = {k: v for k, v in self.__dict__.items() if v is not None}
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert log entry to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


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
        **kwargs: Any
    ) -> AstolfoLog:
        """Create a structured log entry."""
        log = AstolfoLog(
            level=level,
            event=event,
            session_id=self.session_id,
            **kwargs
        )
        return log
    
    def debug(self, *args: Any, **kwargs: Any) -> None:
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
    
    def info(self, *args: Any, **kwargs: Any) -> None:
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
    
    def warning(self, *args: Any, **kwargs: Any) -> None:
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
    
    def error(self, *args: Any, exception: Optional[Exception] = None, **kwargs: Any) -> None:
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
            error_info = None
            if exception:
                error_info = {
                    "type": type(exception).__name__,
                    "message": str(exception),
                    "stack_trace": traceback.format_exc()
                }
            
            log = self._create_log("ERROR", str(event), error=error_info, **kwargs)
            self.logger.error(log.to_json())
    
    def exception(self, *args: Any, **kwargs: Any) -> None:
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
                self.error(str(event), exception=exception, **kwargs)
            else:
                # No active exception, just log as error
                self.error(*args, **kwargs)
    
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
    
    def log_function_call(self, func_name: str, args: dict[str, Any], level: int = 3) -> None:
        """Log function call with arguments (requires debug level 3)."""
        if self.debug_level >= level:
            self.debug(
                f"{func_name}_called",
                context={
                    "function": func_name,
                    "arguments": args
                },
                ai_todo=f"Function {func_name} called with provided arguments"
            )
    
    def log_function_result(self, func_name: str, result: Any, duration_ms: int, level: int = 3) -> None:
        """Log function result (requires debug level 3)."""
        if self.debug_level >= level:
            # Truncate large results
            if isinstance(result, str) and len(result) > 1000:
                result_preview = result[:1000] + "..."
            elif isinstance(result, (dict, list)) and len(str(result)) > 1000:
                result_preview = f"{type(result).__name__} with {len(result)} items"
            else:
                result_preview = result
                
            self.debug(
                f"{func_name}_completed",
                context={
                    "function": func_name,
                    "result": result_preview,
                    "result_type": type(result).__name__
                },
                duration_ms=duration_ms,
                ai_todo=f"Function {func_name} completed successfully"
            )
    
    def log_api_request(self, method: str, url: str, headers: dict[str, str], body: Any) -> None:
        """Log API request details (requires debug level 2)."""
        if self.debug_level >= 2:
            # Hide sensitive headers
            safe_headers = {k: v if k.lower() != "authorization" else "***" for k, v in headers.items()}
            
            self.debug(
                "api_request",
                context={
                    "method": method,
                    "url": url,
                    "headers": safe_headers,
                    "body": body,
                    "body_size": len(json.dumps(body)) if body else 0
                },
                ai_todo="API request sent, response will follow"
            )
    
    def log_api_response(self, url: str, status: int, body: Any, duration_ms: int) -> None:
        """Log API response details (requires debug level 2)."""
        if self.debug_level >= 2:
            self.debug(
                "api_response",
                context={
                    "url": url,
                    "status": status,
                    "body": body if len(str(body)) < 1000 else f"Large response ({len(str(body))} chars)",
                    "success": 200 <= status < 300
                },
                duration_ms=duration_ms,
                ai_todo=f"API response received with status {status}"
            )
    
    def log_handover(self, completed_tasks: list[str], pending_tasks: list[str], notes: str) -> None:
        """Log handover information for the next Astolfo."""
        self.info(
            "astolfo_handover",
            context={
                "completed_tasks": completed_tasks,
                "pending_tasks": pending_tasks,
                "timestamp": datetime.now(UTC).isoformat()
            },
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
def log_function_execution(logger: AstolfoLogger, level: int = 3):
    """Decorator to log function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if logger.debug_level >= level:
                func_name = func.__name__
                
                # Log function call
                all_args = {"args": args, "kwargs": kwargs}
                logger.log_function_call(func_name, all_args, level)
                
                # Time execution
                logger.start_operation(func_name)
                
                try:
                    result = func(*args, **kwargs)
                    duration_ms = logger.end_operation(func_name)
                    logger.log_function_result(func_name, result, duration_ms, level)
                    return result
                except Exception as e:
                    duration_ms = logger.end_operation(func_name)
                    logger.error(
                        f"{func_name}_failed",
                        exception=e,
                        context={"function": func_name, "args": all_args},
                        duration_ms=duration_ms,
                        ai_todo=f"Function {func_name} failed with {type(e).__name__}. Check stack trace."
                    )
                    raise
        
        return wrapper
    return decorator