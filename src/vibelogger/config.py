from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import os


@dataclass
class VibeLoggerConfig:
    log_file: Optional[str] = None
    auto_save: bool = True
    max_file_size_mb: int = 10
    create_dirs: bool = True
    log_level: str = "INFO"
    correlation_id: Optional[str] = None
    keep_logs_in_memory: bool = True
    max_memory_logs: int = 1000
    
    @classmethod
    def from_env(cls):
        return cls(
            log_file=os.getenv("VIBE_LOG_FILE"),
            auto_save=os.getenv("VIBE_AUTO_SAVE", "true").lower() == "true",
            max_file_size_mb=int(os.getenv("VIBE_MAX_FILE_SIZE_MB", "10")),
            create_dirs=os.getenv("VIBE_CREATE_DIRS", "true").lower() == "true",
            log_level=os.getenv("VIBE_LOG_LEVEL", "INFO"),
            correlation_id=os.getenv("VIBE_CORRELATION_ID")
        )
    
    @classmethod
    def default_file_config(cls, project_name: str = "vibe_project"):
        from datetime import datetime
        # Use project folder instead of home directory for better Claude Code access
        log_dir = Path("./logs") / project_name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"vibe_{timestamp}.log"
        
        return cls(
            log_file=str(log_file),
            auto_save=True,
            max_file_size_mb=10,
            create_dirs=True,
            log_level="INFO"
        )