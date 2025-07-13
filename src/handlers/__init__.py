"""Discord event handlers and thread management."""

from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)

try:
    from .discord_sender import DiscordContext, send_to_discord
    from .event_registry import FormatterRegistry
    from .thread_manager import SESSION_THREAD_CACHE, get_or_create_thread

    logger.debug("Handlers module imports successful")
except ImportError as e:
    logger.exception("Failed to import handler modules", {"error": str(e)})
    raise

__all__ = [
    "SESSION_THREAD_CACHE",
    "DiscordContext",
    "FormatterRegistry",
    "get_or_create_thread",
    "send_to_discord",
]
