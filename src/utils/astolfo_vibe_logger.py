#!/usr/bin/env python3
"""AstolfoVibeLogger - Enhanced vibe-logger for Discord Notifier.

This module extends vibe-logger with Discord-specific features and
enhanced debugging capabilities for easier problem investigation.
"""

import functools
import json
import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, TypeVar, Union, Optional
from enum import Enum

# Import vibe-logger components
from src.vibelogger.logger import VibeLogger, LogLevel as VibeLogLevel
from src.vibelogger.config import VibeLoggerConfig


F = TypeVar("F", bound=Callable[..., Any])


class LogLevel(Enum):
    """Log levels for AstolfoVibeLogger."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class APIRequestLog:
    """Structure for API request logging."""
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: Optional[Union[str, dict]] = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class APIResponseLog:
    """Structure for API response logging."""
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: Optional[Union[str, dict]] = None
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AstolfoVibeLogger(VibeLogger):
    """Enhanced vibe-logger with Discord-specific features."""
    
    def __init__(self, config: Optional[VibeLoggerConfig] = None, session_id: Optional[str] = None):
        """Initialize AstolfoVibeLogger.
        
        Args:
            config: Optional vibe-logger configuration
            session_id: Optional session ID for correlation
        """
        super().__init__(config)
        self.session_id = session_id
        self.debug_level = self._get_debug_level()
        
        # Add custom fields to logs
        self._custom_fields = {
            "session_id": session_id,
            "debug_level": self.debug_level,
            "astolfo_version": "2.0.0"
        }
    
    def _get_debug_level(self) -> int:
        """Get debug level from environment."""
        try:
            return int(os.environ.get("DISCORD_DEBUG_LEVEL", "1"))
        except ValueError:
            return 1
    
    def log(
        self,
        level: Union[str, LogLevel],
        event: str,
        context: Optional[dict[str, Any]] = None,
        error: Optional[Union[Exception, dict[str, Any]]] = None,
        ai_todo: Optional[str] = None,
        astolfo_note: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Enhanced log method with Discord-specific fields.
        
        Args:
            level: Log level
            event: Event name
            context: Additional context
            error: Error information
            ai_todo: AI action suggestion
            astolfo_note: Astolfo's personal note
            **kwargs: Additional fields
        """
        # Prepare enhanced context
        enhanced_context = self._custom_fields.copy()
        if context:
            enhanced_context.update(context)
        
        # Add custom fields
        if astolfo_note:
            kwargs["astolfo_note"] = astolfo_note
        
        # Convert level to string if enum
        if isinstance(level, LogLevel):
            level = level.value
        
        # Handle error separately
        if error:
            if isinstance(error, Exception):
                # Log as exception
                super().log_exception(
                    operation=event,
                    exception=error,
                    context=enhanced_context,
                    human_note=kwargs.get("human_note"),
                    ai_todo=ai_todo
                )
                return
            else:
                # Add error info to context
                enhanced_context["error"] = error
        
        # Convert our LogLevel to vibe-logger's LogLevel
        if isinstance(level, LogLevel):
            vibe_level = VibeLogLevel[level.value]
        else:
            vibe_level = VibeLogLevel[level]
        
        # Call parent log method
        super().log(
            level=vibe_level,
            operation=event,
            message=ai_todo or f"Event: {event}",
            context=enhanced_context,
            human_note=kwargs.get("human_note") or astolfo_note,
            ai_todo=ai_todo
        )
    
    def log_api_request(self, request: APIRequestLog) -> None:
        """Log API request details.
        
        Args:
            request: API request information
        """
        if self.debug_level >= 2:
            self.log(
                level=LogLevel.DEBUG,
                event="api_request",
                context={
                    "method": request.method,
                    "url": request.url,
                    "headers": request.headers if self.debug_level >= 3 else None,
                    "body": request.body if self.debug_level >= 3 else None,
                },
                ai_todo="API request sent to Discord"
            )
    
    def log_api_response(self, response: APIResponseLog) -> None:
        """Log API response details.
        
        Args:
            response: API response information
        """
        if self.debug_level >= 2:
            self.log(
                level=LogLevel.DEBUG,
                event="api_response",
                context={
                    "status_code": response.status_code,
                    "duration_ms": response.duration_ms,
                    "headers": response.headers if self.debug_level >= 3 else None,
                    "body": response.body if self.debug_level >= 3 else None,
                },
                ai_todo=f"API response received: {response.status_code}"
            )
    
    def log_function_call(self, func: F) -> F:
        """Decorator to log function calls with arguments and results.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            func_name = func.__name__
            
            # Log function entry
            if self.debug_level >= 3:
                self.log(
                    level=LogLevel.DEBUG,
                    event=f"function_call_start",
                    context={
                        "function": func_name,
                        "args": repr(args)[:500] if args else None,
                        "kwargs": repr(kwargs)[:500] if kwargs else None,
                    },
                    ai_todo=f"Executing {func_name}"
                )
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log function success
                if self.debug_level >= 3:
                    self.log(
                        level=LogLevel.DEBUG,
                        event=f"function_call_success",
                        context={
                            "function": func_name,
                            "duration_ms": duration_ms,
                            "result": repr(result)[:500] if result else None,
                        },
                        ai_todo=f"Completed {func_name}"
                    )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log function error
                self.log(
                    level=LogLevel.ERROR,
                    event=f"function_call_error",
                    context={
                        "function": func_name,
                        "duration_ms": duration_ms,
                    },
                    error=e,
                    ai_todo=f"Error in {func_name}: {str(e)}"
                )
                raise
        
        return wrapper  # type: ignore
    
    def log_module_import(self, module_name: str, from_path: Optional[str] = None) -> None:
        """Log module import for tracking which implementation is used.
        
        Args:
            module_name: Name of imported module
            from_path: Path it was imported from
        """
        if self.debug_level >= 3:
            self.log(
                level=LogLevel.DEBUG,
                event="module_import",
                context={
                    "module": module_name,
                    "from_path": from_path,
                    "caller": traceback.extract_stack()[-3].filename if len(traceback.extract_stack()) > 2 else None
                },
                ai_todo=f"Module {module_name} imported"
            )
    
    def log_config_value(self, key: str, value: Any, source: str) -> None:
        """Log configuration value usage for debugging.
        
        Args:
            key: Configuration key
            value: Configuration value
            source: Where the value came from
        """
        if self.debug_level >= 2:
            self.log(
                level=LogLevel.DEBUG,
                event="config_value_used",
                context={
                    "key": key,
                    "value": value,
                    "source": source,
                },
                ai_todo=f"Config {key}={value} from {source}"
            )
    
    def log_data_transformation(
        self, 
        operation: str, 
        before: Any, 
        after: Any,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        """Log data transformation for debugging truncation issues.
        
        Args:
            operation: Name of the operation
            before: Data before transformation
            after: Data after transformation
            details: Additional details
        """
        if self.debug_level >= 3:
            context = {
                "operation": operation,
                "before_length": len(str(before)) if before else 0,
                "after_length": len(str(after)) if after else 0,
                "before_preview": str(before)[:200] if before else None,
                "after_preview": str(after)[:200] if after else None,
            }
            if details:
                context.update(details)
            
            self.log(
                level=LogLevel.DEBUG,
                event="data_transformation",
                context=context,
                ai_todo=f"Data transformed by {operation}"
            )
    
    def log_truncation(
        self,
        field_name: str,
        original_length: int,
        truncated_length: int,
        limit_used: int,
        source_location: Optional[str] = None
    ) -> None:
        """Log text truncation operations for debugging.
        
        Args:
            field_name: Name of the field being truncated
            original_length: Original text length
            truncated_length: Length after truncation
            limit_used: The limit that was applied
            source_location: Where in code this happened
        """
        self.log(
            level=LogLevel.INFO,
            event="text_truncation",
            context={
                "field": field_name,
                "original_length": original_length,
                "truncated_length": truncated_length,
                "limit_used": limit_used,
                "source_location": source_location or traceback.extract_stack()[-2].filename,
                "truncated": original_length > truncated_length,
            },
            ai_todo=f"Text truncated: {field_name} from {original_length} to {truncated_length} chars",
            astolfo_note=f"マスター、{field_name}が切り詰められちゃった！" if original_length > truncated_length else None
        )
    
    # Compatibility methods for smooth transition
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Debug level logging (compatibility method)."""
        self.log(LogLevel.DEBUG, msg, context=kwargs)
    
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Info level logging (compatibility method)."""
        self.log(LogLevel.INFO, msg, context=kwargs)
    
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Warning level logging (compatibility method)."""
        self.log(LogLevel.WARNING, msg, context=kwargs)
    
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Error level logging (compatibility method)."""
        self.log(LogLevel.ERROR, msg, context=kwargs)
    
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Exception logging (compatibility method)."""
        import sys
        exc_info = sys.exc_info()
        if exc_info[0]:
            self.log(LogLevel.ERROR, msg, error=exc_info[1], context=kwargs)
        else:
            self.error(msg, *args, **kwargs)


# Export main components
__all__ = [
    "AstolfoVibeLogger",
    "LogLevel",
    "APIRequestLog",
    "APIResponseLog",
]