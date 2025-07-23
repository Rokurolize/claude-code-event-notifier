#!/usr/bin/env python3
"""Clean up old log and debug files for Claude Code Event Notifier."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_files(directory: Path, pattern: str, days_to_keep: int = 7) -> int:
    """Remove files older than specified days."""
    if not directory.exists():
        return 0
    
    count = 0
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    for file in directory.glob(pattern):
        if file.is_file():
            file_date = datetime.fromtimestamp(file.stat().st_mtime)
            if file_date < cutoff_date:
                try:
                    file.unlink()
                    count += 1
                except Exception as e:
                    print(f"Failed to remove {file}: {e}", file=sys.stderr)
    
    return count

def main():
    """Main cleanup function."""
    hooks_dir = Path.home() / ".claude" / "hooks"
    
    # Clean up old logs (keep last 7 days)
    log_count = cleanup_old_files(hooks_dir / "logs", "*.log", days_to_keep=7)
    
    # Clean up debug files (keep last 3 days)
    debug_count = cleanup_old_files(hooks_dir / "debug", "*.json", days_to_keep=3)
    
    print(f"🧹 Cleanup complete:")
    print(f"   - Removed {log_count} old log files")
    print(f"   - Removed {debug_count} debug files")
    
    # Show current status
    logs_dir = hooks_dir / "logs"
    debug_dir = hooks_dir / "debug"
    
    if logs_dir.exists():
        current_logs = len(list(logs_dir.glob("*.log")))
        print(f"   - Current log files: {current_logs}")
    
    if debug_dir.exists():
        current_debug = len(list(debug_dir.glob("*.json")))
        print(f"   - Current debug files: {current_debug}")

if __name__ == "__main__":
    main()