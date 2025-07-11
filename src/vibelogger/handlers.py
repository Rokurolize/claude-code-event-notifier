"""
Standard logging integration handlers for VibeCoding Logger

This module provides handlers and adapters to integrate VibeCoding Logger
with Python's standard logging module, enabling seamless integration with
existing applications and third-party libraries.
"""

import logging
import traceback
from typing import Dict, Any, Optional

from .logger import VibeLogger, LogLevel


class VibeLoggingHandler(logging.Handler):
    """
    A logging handler that forwards standard logging records to VibeCoding Logger.
    
    This enables existing applications using standard logging to automatically
    benefit from VibeCoding Logger's AI-native features without code changes.
    
    Example:
        ```python
        import logging
        from vibelogger import create_file_logger, VibeLoggingHandler
        
        # Setup VibeCoding Logger
        vibe_logger = create_file_logger("my_app")
        handler = VibeLoggingHandler(vibe_logger)
        
        # Add to standard logging
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        
        # Use standard logging - automatically enhanced with VibeCoding features
        logger = logging.getLogger(__name__)
        logger.info("User login", extra={
            'operation': 'user_login',
            'context': {'user_id': '123'},
            'human_note': 'AI-TODO: Check for suspicious patterns'
        })
        ```
    """
    
    def __init__(self, vibe_logger: VibeLogger, extract_operation: bool = True):
        """
        Initialize the handler.
        
        Args:
            vibe_logger: The VibeCoding Logger instance to forward records to
            extract_operation: Whether to attempt extracting operation from logger name
        """
        super().__init__()
        self.vibe_logger = vibe_logger
        self.extract_operation = extract_operation
        
        # Mapping from standard logging levels to VibeCoding levels
        self.level_mapping = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.CRITICAL,
        }
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a logging record to VibeCoding Logger.
        
        Args:
            record: The standard logging record to process
        """
        try:
            # Extract VibeCoding-specific fields from record.extra
            # Debug: print record attributes
            # print(f"DEBUG: record.__dict__ = {record.__dict__}")
            
            operation = self._extract_operation(record)
            context = self._extract_context(record)
            human_note = getattr(record, 'human_note', None)
            ai_todo = getattr(record, 'ai_todo', None)
            
            # Get the appropriate VibeCoding log level
            vibe_level = self.level_mapping.get(record.levelno, LogLevel.INFO)
            
            # Format the message
            message = record.getMessage()
            
            # Add exception info if present
            if record.exc_info:
                import traceback
                exc_text = ''.join(traceback.format_exception(*record.exc_info))
                if exc_text:
                    message += f"\nException: {exc_text}"
            
            # Log to VibeCoding Logger
            if record.exc_info and hasattr(self.vibe_logger, 'log_exception'):
                # Use exception logging if available and we have exception info
                exc_type, exc_value, exc_traceback = record.exc_info
                if exc_value:
                    self.vibe_logger.log_exception(
                        operation=operation,
                        exception=exc_value,
                        context=context,
                        human_note=human_note,
                        ai_todo=ai_todo
                    )
                    return
            
            # Regular logging
            self.vibe_logger.log(
                level=vibe_level,
                operation=operation,
                message=message,
                context=context,
                human_note=human_note,
                ai_todo=ai_todo
            )
            
        except Exception:
            # Prevent logging errors from crashing the application
            self.handleError(record)
    
    def _extract_operation(self, record: logging.LogRecord) -> str:
        """Extract operation name from the logging record."""
        # Priority order: explicit operation > function name > logger name
        if hasattr(record, 'operation') and record.operation:
            return record.operation
        
        if self.extract_operation:
            # Try to extract from function name
            if hasattr(record, 'funcName') and record.funcName != '<module>':
                return record.funcName
            
            # Use logger name as fallback
            return record.name
        
        return record.name
    
    def _extract_context(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract context information from the logging record."""
        context = {}
        
        # Get explicit context
        if hasattr(record, 'context') and record.context:
            context.update(record.context)
        
        # Add standard logging fields to context
        context.update({
            'logger_name': record.name,
            'level_name': record.levelname,
            'filename': record.filename,
            'lineno': record.lineno,
            'thread_id': record.thread,
            'process_id': record.process,
        })
        
        # Add function name if available
        if hasattr(record, 'funcName'):
            context['function_name'] = record.funcName
        
        # Add any extra fields that aren't VibeCoding-specific or standard logging fields
        standard_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 
            'pathname', 'filename', 'module', 'exc_info', 
            'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread',
            'threadName', 'processName', 'process', 'message'
        }
        vibe_fields = {'operation', 'context', 'human_note', 'ai_todo'}
        
        for key, value in record.__dict__.items():
            if (key not in vibe_fields and 
                key not in standard_fields and
                not key.startswith('_') and 
                key not in context):
                context[key] = value
        
        return context


class VibeLoggerAdapter(logging.LoggerAdapter):
    """
    Enhanced LoggerAdapter with VibeCoding-specific methods.
    
    Provides convenience methods for VibeCoding-style logging while maintaining
    compatibility with standard logging.
    
    Example:
        ```python
        import logging
        from vibelogger.handlers import VibeLoggerAdapter
        
        logger = VibeLoggerAdapter(logging.getLogger(__name__), {})
        
        # VibeCoding-style logging
        logger.vibe_info(
            operation="fetch_user",
            message="Fetching user profile",
            context={'user_id': '123'},
            ai_todo="Check database performance"
        )
        
        # Standard logging still works
        logger.info("Regular log message")
        ```
    """
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        super().__init__(logger, extra)
    
    def process(self, msg, kwargs):
        """Process the logging call to add extra fields to the record."""
        # Call parent process first
        msg, kwargs = super().process(msg, kwargs)
        return msg, kwargs
    
    def vibe_log(self, level: int, operation: str, message: str,
                 context: Optional[Dict[str, Any]] = None,
                 human_note: Optional[str] = None,
                 ai_todo: Optional[str] = None,
                 **kwargs) -> None:
        """
        Log with VibeCoding-specific fields.
        
        Args:
            level: Logging level (logging.INFO, etc.)
            operation: Operation being performed
            message: Log message
            context: Additional context data
            human_note: Note for AI analysis
            ai_todo: Specific AI task
            **kwargs: Additional keyword arguments for logging
        """
        extra = kwargs.get('extra', {})
        extra.update({
            'operation': operation,
            'context': context or {},
            'human_note': human_note,
            'ai_todo': ai_todo
        })
        kwargs['extra'] = extra
        
        self.log(level, message, **kwargs)
    
    def vibe_debug(self, operation: str, message: str, **kwargs) -> None:
        """Log debug message with VibeCoding fields."""
        self.vibe_log(logging.DEBUG, operation, message, **kwargs)
    
    def vibe_info(self, operation: str, message: str, **kwargs) -> None:
        """Log info message with VibeCoding fields."""
        self.vibe_log(logging.INFO, operation, message, **kwargs)
    
    def vibe_warning(self, operation: str, message: str, **kwargs) -> None:
        """Log warning message with VibeCoding fields."""
        self.vibe_log(logging.WARNING, operation, message, **kwargs)
    
    def vibe_error(self, operation: str, message: str, **kwargs) -> None:
        """Log error message with VibeCoding fields."""
        self.vibe_log(logging.ERROR, operation, message, **kwargs)
    
    def vibe_critical(self, operation: str, message: str, **kwargs) -> None:
        """Log critical message with VibeCoding fields."""
        self.vibe_log(logging.CRITICAL, operation, message, **kwargs)
    
    def vibe_exception(self, operation: str, message: str,
                       context: Optional[Dict[str, Any]] = None,
                       human_note: Optional[str] = None,
                       ai_todo: Optional[str] = None) -> None:
        """
        Log an exception with VibeCoding fields.
        
        Args:
            operation: Operation that failed
            message: Error message
            context: Additional context
            human_note: Note for AI
            ai_todo: AI analysis request
        """
        self.vibe_log(
            logging.ERROR, operation, message,
            context=context, human_note=human_note, ai_todo=ai_todo,
            exc_info=True
        )


def setup_vibe_logging(vibe_logger: VibeLogger, 
                       logger_name: Optional[str] = None,
                       level: int = logging.INFO) -> VibeLoggerAdapter:
    """
    Convenience function to setup VibeCoding logging integration.
    
    Args:
        vibe_logger: VibeCoding Logger instance
        logger_name: Name of the logger (defaults to root logger)
        level: Logging level
    
    Returns:
        Configured VibeLoggerAdapter
    
    Example:
        ```python
        from vibelogger import create_file_logger
        from vibelogger.handlers import setup_vibe_logging
        
        vibe_logger = create_file_logger("my_app")
        logger = setup_vibe_logging(vibe_logger, __name__)
        
        logger.vibe_info("user_login", "User authenticated", 
                        context={'user_id': '123'})
        ```
    """
    # Get the logger
    std_logger = logging.getLogger(logger_name)
    std_logger.setLevel(level)
    
    # Add VibeCoding handler
    handler = VibeLoggingHandler(vibe_logger)
    std_logger.addHandler(handler)
    
    # Return enhanced adapter
    return VibeLoggerAdapter(std_logger, {})