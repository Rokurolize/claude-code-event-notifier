"""
Structured logging utilities and formatters for VibeCoding Logger

This module provides utilities for structured logging, custom formatters,
and integration helpers for various logging scenarios.
"""

import json
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

from .logger import VibeLogger, LogEntry


class VibeJSONFormatter(logging.Formatter):
    """
    A JSON formatter that outputs VibeCoding-compatible structured logs.
    
    This formatter converts standard logging records into JSON format
    similar to VibeCoding Logger's native format, enabling consistent
    log analysis across different logging approaches.
    
    Example:
        ```python
        import logging
        from vibelogger.formatters import VibeJSONFormatter
        
        handler = logging.StreamHandler()
        handler.setFormatter(VibeJSONFormatter())
        
        logger = logging.getLogger(__name__)
        logger.addHandler(handler)
        logger.info("User login", extra={'operation': 'user_login'})
        ```
    """
    
    def __init__(self, 
                 include_extra: bool = True,
                 include_env: bool = False,
                 correlation_id: Optional[str] = None):
        """
        Initialize the JSON formatter.
        
        Args:
            include_extra: Include extra fields from log record
            include_env: Include environment information
            correlation_id: Default correlation ID for logs
        """
        super().__init__()
        self.include_extra = include_extra
        self.include_env = include_env
        self.correlation_id = correlation_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Base log structure
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'correlation_id': getattr(record, 'correlation_id', self.correlation_id),
            'operation': getattr(record, 'operation', record.name),
            'message': record.getMessage(),
            'source': f"{record.filename}:{record.lineno} in {record.funcName}()"
        }
        
        # Add context if available
        context = getattr(record, 'context', {})
        if not context and self.include_extra:
            # Extract extra fields as context
            context = self._extract_extra_fields(record)
        
        log_data['context'] = context
        
        # Add VibeCoding-specific fields
        if hasattr(record, 'human_note'):
            log_data['human_note'] = record.human_note
        
        if hasattr(record, 'ai_todo'):
            log_data['ai_todo'] = record.ai_todo
        
        # Add exception info if present
        if record.exc_info:
            log_data['stack_trace'] = self.formatException(record.exc_info)
        
        # Add environment info if requested
        if self.include_env:
            from .logger import EnvironmentInfo
            log_data['environment'] = EnvironmentInfo.collect().__dict__
        
        return json.dumps(log_data, default=str, ensure_ascii=False)
    
    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from log record as context."""
        # Standard fields to exclude
        standard_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
            'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'message',
            'operation', 'context', 'human_note', 'ai_todo', 'correlation_id'
        }
        
        context = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith('_'):
                context[key] = value
        
        return context


class VibeStructuredLogger:
    """
    A utility class for structured logging with VibeCoding enhancements.
    
    This class provides methods to create structured log entries that are
    optimized for AI analysis while maintaining compatibility with standard
    logging practices.
    
    Example:
        ```python
        from vibelogger.formatters import VibeStructuredLogger
        
        struct_logger = VibeStructuredLogger("user_service")
        
        # Structured logging with automatic context
        with struct_logger.operation_context("user_registration"):
            struct_logger.info("Starting user registration",
                             user_data={'email': 'user@example.com'})
            
            try:
                register_user()
                struct_logger.success("User registered successfully")
            except Exception as e:
                struct_logger.failure("Registration failed", error=str(e))
        ```
    """
    
    def __init__(self, service_name: str, vibe_logger: Optional[VibeLogger] = None):
        """
        Initialize structured logger.
        
        Args:
            service_name: Name of the service/component
            vibe_logger: Optional VibeCoding Logger instance
        """
        self.service_name = service_name
        self.vibe_logger = vibe_logger
        self._operation_stack = []
        self._context_stack = []
    
    def operation_context(self, operation: str, **context):
        """
        Context manager for operation-scoped logging.
        
        Args:
            operation: Operation name
            **context: Additional context for the operation
        
        Returns:
            Context manager
        """
        return OperationContext(self, operation, context)
    
    def add_context(self, **context):
        """Add context that persists across log calls."""
        if self._context_stack:
            self._context_stack[-1].update(context)
        else:
            self._context_stack.append(context.copy())
    
    def _get_current_context(self) -> Dict[str, Any]:
        """Get the current accumulated context."""
        context = {'service': self.service_name}
        for ctx in self._context_stack:
            context.update(ctx)
        return context
    
    def _get_current_operation(self) -> str:
        """Get the current operation name."""
        return self._operation_stack[-1] if self._operation_stack else self.service_name
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method."""
        operation = self._get_current_operation()
        context = self._get_current_context()
        
        # Merge any additional context
        if 'context' in kwargs:
            context.update(kwargs.pop('context'))
        
        # Add any extra kwargs to context
        for key, value in kwargs.items():
            if key not in {'human_note', 'ai_todo'}:
                context[key] = value
        
        if self.vibe_logger:
            # Use VibeCoding Logger
            from .logger import LogLevel
            level_map = {
                'DEBUG': LogLevel.DEBUG,
                'INFO': LogLevel.INFO,
                'WARNING': LogLevel.WARNING,
                'ERROR': LogLevel.ERROR,
                'CRITICAL': LogLevel.CRITICAL
            }
            
            self.vibe_logger.log(
                level=level_map[level],
                operation=operation,
                message=message,
                context=context,
                human_note=kwargs.get('human_note'),
                ai_todo=kwargs.get('ai_todo')
            )
        else:
            # Use standard logging
            logger = logging.getLogger(self.service_name)
            getattr(logger, level.lower())(message, extra={
                'operation': operation,
                'context': context,
                'human_note': kwargs.get('human_note'),
                'ai_todo': kwargs.get('ai_todo')
            })
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log('CRITICAL', message, **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message (info level with success indicator)."""
        kwargs['status'] = 'success'
        self._log('INFO', message, **kwargs)
    
    def failure(self, message: str, **kwargs):
        """Log failure message (error level with failure indicator)."""
        kwargs['status'] = 'failure'
        self._log('ERROR', message, **kwargs)
    
    def metric(self, metric_name: str, value: Union[int, float], unit: str = '', **kwargs):
        """Log a metric value."""
        kwargs.update({
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit,
            'log_type': 'metric'
        })
        self._log('INFO', f"Metric: {metric_name} = {value} {unit}", **kwargs)
    
    def performance(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics."""
        kwargs.update({
            'duration_ms': duration_ms,
            'log_type': 'performance'
        })
        self._log('INFO', f"Performance: {operation} took {duration_ms:.2f}ms", **kwargs)


class OperationContext:
    """Context manager for operation-scoped logging."""
    
    def __init__(self, struct_logger: VibeStructuredLogger, operation: str, context: Dict[str, Any]):
        self.struct_logger = struct_logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.struct_logger._operation_stack.append(self.operation)
        self.struct_logger._context_stack.append(self.context.copy())
        self.start_time = datetime.now()
        
        self.struct_logger.info(f"Started operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds() * 1000
            
            if exc_type is None:
                self.struct_logger.success(
                    f"Completed operation: {self.operation}",
                    duration_ms=duration
                )
            else:
                self.struct_logger.failure(
                    f"Failed operation: {self.operation}",
                    duration_ms=duration,
                    error_type=exc_type.__name__,
                    error_message=str(exc_val),
                    ai_todo=f"Analyze why {self.operation} failed with {exc_type.__name__}"
                )
        
        # Clean up stacks
        if self.struct_logger._operation_stack:
            self.struct_logger._operation_stack.pop()
        if self.struct_logger._context_stack:
            self.struct_logger._context_stack.pop()


def create_structured_logger(service_name: str, 
                            vibe_logger: Optional[VibeLogger] = None) -> VibeStructuredLogger:
    """
    Factory function to create a structured logger.
    
    Args:
        service_name: Name of the service/component
        vibe_logger: Optional VibeCoding Logger instance
    
    Returns:
        Configured VibeStructuredLogger
    """
    return VibeStructuredLogger(service_name, vibe_logger)