"""
VibeCoding Logger - AI-Native Logging for LLM Agent Development

CONCEPT:
This logger is designed specifically for VibeCoding (AI-driven development) where
LLMs need rich, structured context to understand and debug code effectively.
Unlike traditional human-readable logs, this creates "AI briefing packages" with
comprehensive context, correlation tracking, and embedded human annotations.

KEY FEATURES:
- Structured JSON format optimized for LLM consumption
- Rich context including function arguments, stack traces, environment info
- Correlation IDs to track request flows across operations
- Human annotation fields (human_note, ai_todo) for AI instructions
- Automatic file saving with timestamp-based naming
- Log rotation to prevent large files

BASIC USAGE:
```python
from vibe_logger import create_file_logger

# Create logger with auto-save to timestamped file
logger = create_file_logger("my_project")

# Log with rich context
logger.info(
    operation="fetchUserProfile",
    message="Starting user profile fetch",
    context={"user_id": "123", "source": "api_endpoint"},
    human_note="AI-TODO: Check if user exists before fetching profile"
)

# Log exceptions with full context
try:
    result = risky_operation()
except Exception as e:
    logger.log_exception(
        operation="fetchUserProfile",
        exception=e,
        context={"user_id": "123"},
        ai_todo="Suggest proper error handling for this case"
    )

# Get logs formatted for AI analysis
ai_context = logger.get_logs_for_ai()
```

ADVANCED USAGE:
```python
# Custom configuration
from .config import VibeLoggerConfig
config = VibeLoggerConfig(
    log_file="./logs/custom.log",
    max_file_size_mb=50,
    auto_save=True
)
logger = create_logger(config=config)

# Environment-based configuration
logger = create_env_logger()  # Uses VIBE_* environment variables
```

AI INTEGRATION:
The logger creates structured data that LLMs can immediately understand:
- timestamp: ISO format for precise timing
- correlation_id: Links related operations
- operation: What the code was trying to do
- context: Function arguments, variables, state
- environment: Runtime info for reproduction
- human_note: Natural language instructions for AI
- ai_todo: Specific analysis requests

This enables LLMs to quickly diagnose issues and suggest precise fixes.
"""

import json
import uuid
import traceback
import inspect
import platform
import sys
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
from .config import VibeLoggerConfig


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class EnvironmentInfo:
    python_version: str
    os: str
    platform: str
    architecture: str
    
    @classmethod
    def collect(cls):
        return cls(
            python_version=sys.version,
            os=platform.system(),
            platform=platform.platform(),
            architecture=platform.machine()
        )


@dataclass
class LogEntry:
    timestamp: str
    level: str
    correlation_id: str
    operation: str
    message: str
    context: Dict[str, Any]
    environment: EnvironmentInfo
    source: Optional[str] = None
    stack_trace: Optional[str] = None
    human_note: Optional[str] = None
    ai_todo: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, ensure_ascii=False)


class VibeLogger:
    def __init__(
        self, 
        config: Optional[VibeLoggerConfig] = None,
        correlation_id: Optional[str] = None,
        log_file: Optional[str] = None,
        auto_save: bool = True,
        create_dirs: bool = True
    ):
        if config:
            self.config = config
        else:
            self.config = VibeLoggerConfig(
                correlation_id=correlation_id,
                log_file=log_file,
                auto_save=auto_save,
                create_dirs=create_dirs,
                max_file_size_mb=10,
                keep_logs_in_memory=True,
                max_memory_logs=1000
            )
        
        # Ensure correlation_id is a non-empty string
        if self.config.correlation_id and str(self.config.correlation_id).strip():
            self.correlation_id = str(self.config.correlation_id)
        else:
            self.correlation_id = str(uuid.uuid4())
        self.environment = EnvironmentInfo.collect()
        self.logs: List[LogEntry] = []
        self.log_file = self.config.log_file
        self.auto_save = self.config.auto_save
        self._file_lock = threading.Lock()
        self._logs_lock = threading.Lock()
        
        if self.log_file and self.config.create_dirs:
            try:
                Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                # If we can't create directories, log to memory only
                # This handles: disk full, read-only filesystem, permission denied, etc.
                self.auto_save = False
    
    def _get_caller_info(self) -> str:
        """Get caller information by finding the first frame outside this logger file."""
        logger_filename = inspect.getsourcefile(self.__class__)
        frame = inspect.currentframe()
        try:
            current_frame = frame
            while current_frame:
                if current_frame.f_code.co_filename != logger_filename:
                    filename = current_frame.f_code.co_filename
                    line_number = current_frame.f_lineno
                    function_name = current_frame.f_code.co_name
                    # Get just the filename, not the full path
                    short_filename = filename.split('/')[-1] if '/' in filename else filename.split('\\')[-1]
                    return f"{short_filename}:{line_number} in {function_name}()"
                current_frame = current_frame.f_back
            return "Unknown source"
        finally:
            del frame
    
    def _create_log_entry(
        self,
        level: LogLevel,
        operation: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        human_note: Optional[str] = None,
        ai_todo: Optional[str] = None,
        include_stack: bool = False
    ) -> LogEntry:
        return LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            correlation_id=self.correlation_id,
            operation=operation,
            message=message,
            context=context or {},
            environment=self.environment,
            source=self._get_caller_info(),
            stack_trace=traceback.format_stack() if include_stack else None,
            human_note=human_note,
            ai_todo=ai_todo
        )
    
    def _process_entry(self, entry: LogEntry) -> None:
        """Process log entry: add to memory and save to file based on configuration."""
        with self._logs_lock:
            if getattr(self.config, 'keep_logs_in_memory', True):
                self.logs.append(entry)
                max_logs = getattr(self.config, 'max_memory_logs', 1000)
                if len(self.logs) > max_logs:
                    self.logs.pop(0)
        
        if self.auto_save and self.log_file:
            self._save_to_file(entry)
    
    def log(
        self,
        level: LogLevel,
        operation: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        human_note: Optional[str] = None,
        ai_todo: Optional[str] = None
    ) -> LogEntry:
        entry = self._create_log_entry(
            level=level,
            operation=operation,
            message=message,
            context=context,
            human_note=human_note,
            ai_todo=ai_todo,
            include_stack=level in [LogLevel.ERROR, LogLevel.CRITICAL]
        )
        
        self._process_entry(entry)
        return entry
    
    def debug(self, operation: str, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.DEBUG, operation, message, **kwargs)
    
    def info(self, operation: str, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.INFO, operation, message, **kwargs)
    
    def warning(self, operation: str, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.WARNING, operation, message, **kwargs)
    
    def error(self, operation: str, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.ERROR, operation, message, **kwargs)
    
    def critical(self, operation: str, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.CRITICAL, operation, message, **kwargs)
    
    def log_exception(
        self,
        operation: str,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        human_note: Optional[str] = None,
        ai_todo: Optional[str] = None
    ) -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=LogLevel.ERROR.value,
            correlation_id=self.correlation_id,
            operation=operation,
            message=f"{type(exception).__name__}: {str(exception)}",
            context=context or {},
            environment=self.environment,
            source=self._get_caller_info(),
            stack_trace=traceback.format_exc(),
            human_note=human_note,
            ai_todo=ai_todo
        )
        
        self._process_entry(entry)
        return entry
    
    def get_logs_json(self) -> str:
        with self._logs_lock:
            return json.dumps([asdict(log) for log in self.logs], indent=2, default=str, ensure_ascii=False)
    
    def get_logs_for_ai(self, operation_filter: Optional[str] = None) -> str:
        with self._logs_lock:
            filtered_logs = self.logs
            if operation_filter:
                filtered_logs = [log for log in self.logs if operation_filter in log.operation]
            
            return json.dumps([asdict(log) for log in filtered_logs], indent=2, default=str, ensure_ascii=False)
    
    def _save_to_file(self, entry: LogEntry):
        with self._file_lock:
            try:
                self._rotate_log_if_needed()
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(entry.to_json() + '\n')
            except Exception as e:
                print(f"Failed to save log to file: {e}")
    
    def _rotate_log_if_needed(self, max_size_mb: Optional[int] = None):
        if not self.log_file or not Path(self.log_file).exists():
            return
        
        max_size = max_size_mb or getattr(self.config, 'max_file_size_mb', 10)
        file_size_mb = Path(self.log_file).stat().st_size / (1024 * 1024)
        if file_size_mb > max_size:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_file = f"{self.log_file}.{timestamp}"
            Path(self.log_file).rename(rotated_file)
    
    def save_all_logs(self, file_path: Optional[str] = None):
        target_file = file_path or self.log_file
        if not target_file:
            raise ValueError("No log file specified")
        
        Path(target_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_file, 'w', encoding='utf-8') as f:
            for log in self.logs:
                f.write(log.to_json() + '\n')
    
    def load_logs_from_file(self, file_path: str):
        """Load logs from file with robust error handling for corrupted data."""
        if not Path(file_path).exists():
            return
        
        loaded_count = 0
        error_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                    
                try:
                    log_data = json.loads(line)
                    
                    # Use get() for safe dictionary access with defaults
                    env_data = log_data.get('environment', {})
                    if env_data:
                        try:
                            env = EnvironmentInfo(**env_data)
                            log_data['environment'] = env
                        except TypeError as e:
                            print(f"Warning: Invalid environment data on line {line_num}, using defaults: {e}")
                            log_data['environment'] = EnvironmentInfo.collect()
                    else:
                        log_data['environment'] = EnvironmentInfo.collect()
                    
                    # Validate required fields
                    required_fields = ['timestamp', 'level', 'correlation_id', 'operation', 'message']
                    missing_fields = [field for field in required_fields if field not in log_data]
                    if missing_fields:
                        print(f"Warning: Missing required fields on line {line_num}: {missing_fields}, skipping entry")
                        error_count += 1
                        continue
                    
                    entry = LogEntry(**log_data)
                    self.logs.append(entry)
                    loaded_count += 1
                    
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping corrupted JSON on line {line_num}: {e}")
                    error_count += 1
                except TypeError as e:
                    print(f"Warning: Failed to create LogEntry on line {line_num} due to missing/invalid fields: {e}")
                    error_count += 1
                except Exception as e:
                    print(f"Warning: Unexpected error parsing line {line_num}: {e}")
                    error_count += 1
        
        if error_count > 0:
            print(f"Loaded {loaded_count} log entries with {error_count} errors from {file_path}")
        else:
            print(f"Successfully loaded {loaded_count} log entries from {file_path}")
    
    def clear_logs(self):
        with self._logs_lock:
            self.logs.clear()


def create_logger(
    config: Optional[VibeLoggerConfig] = None,
    correlation_id: Optional[str] = None,
    log_file: Optional[str] = None,
    auto_save: bool = True
) -> VibeLogger:
    return VibeLogger(config, correlation_id, log_file, auto_save)


def create_file_logger(project_name: str = "vibe_project") -> VibeLogger:
    config = VibeLoggerConfig.default_file_config(project_name)
    return VibeLogger(config)


def create_env_logger() -> VibeLogger:
    config = VibeLoggerConfig.from_env()
    return VibeLogger(config)