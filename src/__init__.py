"""Claude Code Discord Notifier package."""

from src.utils.astolfo_logger import AstolfoLogger

__version__ = "0.1.0"

# Initialize package-level logger
logger = AstolfoLogger(__name__)
logger.info("Discord Notifier package initialized", {"version": __version__})
