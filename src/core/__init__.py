"""Core components for the Discord notifier."""

from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)

try:
    from .config import Config, ConfigLoader, ConfigValidator
    from .constants import (
        DEFAULT_TIMEOUT,
        DISCORD_API_BASE,
        USER_AGENT,
        DiscordColors,
        DiscordLimits,
        EventTypes,
        ToolNames,
    )
    from .exceptions import (
        ConfigurationError,
        DiscordAPIError,
        DiscordNotifierError,
        EventProcessingError,
        InvalidEventTypeError,
        ThreadManagementError,
        ThreadStorageError,
    )
    from .http_client import HTTPClient

    logger.debug("Core module imports successful")
except ImportError as e:
    logger.exception("Failed to import core modules", {"error": str(e)})
    raise

__all__ = [
    "DEFAULT_TIMEOUT",
    "DISCORD_API_BASE",
    "USER_AGENT",
    "Config",
    "ConfigLoader",
    "ConfigValidator",
    "ConfigurationError",
    "DiscordAPIError",
    "DiscordColors",
    "DiscordLimits",
    "DiscordNotifierError",
    "EventProcessingError",
    "EventTypes",
    "HTTPClient",
    "InvalidEventTypeError",
    "ThreadManagementError",
    "ThreadStorageError",
    "ToolNames",
]
