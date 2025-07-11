"""
VibeCoding Logger - AI-Native Logging for LLM Agent Development

A specialized logging library designed for AI-driven development where LLMs need
rich, structured context to understand and debug code effectively.
"""

from .logger import (
    VibeLogger,
    LogLevel,
    LogEntry,
    EnvironmentInfo,
    create_logger,
    create_file_logger,
    create_env_logger
)
from .config import VibeLoggerConfig
from .handlers import (
    VibeLoggingHandler,
    VibeLoggerAdapter,
    setup_vibe_logging
)
from .formatters import (
    VibeJSONFormatter,
    VibeStructuredLogger,
    create_structured_logger
)

__version__ = "0.1.0"
__author__ = "VibeCoding Team"
__email__ = "info@vibecoding.com"
__description__ = "AI-Native Logging for LLM Agent Development"

__all__ = [
    # Core logger
    "VibeLogger",
    "LogLevel", 
    "LogEntry",
    "EnvironmentInfo",
    "VibeLoggerConfig",
    "create_logger",
    "create_file_logger",
    "create_env_logger",
    # Standard logging integration
    "VibeLoggingHandler",
    "VibeLoggerAdapter", 
    "setup_vibe_logging",
    # Formatters and structured logging
    "VibeJSONFormatter",
    "VibeStructuredLogger",
    "create_structured_logger"
]