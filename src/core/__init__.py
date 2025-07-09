"""Core components for the Discord notifier."""

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
