#!/usr/bin/env python3
"""ThreadStorage Management Utility for Discord Notifier.

This utility provides advanced ThreadStorage management capabilities
including statistics, cleanup, and thread discovery functions.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.thread_storage import ThreadStorage, ThreadStats, ThreadStatsError, ThreadRecord
    from src.core.config import ConfigLoader
    from src.core.constants import DEFAULT_THREAD_CLEANUP_DAYS
    THREAD_STORAGE_AVAILABLE = True
except ImportError:
    THREAD_STORAGE_AVAILABLE = False


class ThreadStorageManager:
    """Advanced ThreadStorage management interface.
    
    Provides high-level operations for managing thread storage including
    statistics, cleanup, search, and health monitoring.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ThreadStorage manager.
        
        Args:
            config: Optional configuration dictionary. If None, loads from ConfigLoader.
        """
        if not THREAD_STORAGE_AVAILABLE:
            raise RuntimeError("ThreadStorage is not available")
        
        self.config = config or ConfigLoader.load()
        
        # Initialize ThreadStorage with configuration
        storage_path = None
        if self.config.get("thread_storage_path"):
            storage_path = Path(self.config["thread_storage_path"])
        
        cleanup_days = self.config.get("thread_cleanup_days", DEFAULT_THREAD_CLEANUP_DAYS)
        self.storage = ThreadStorage(db_path=storage_path, cleanup_days=cleanup_days)
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics.
        
        Returns:
            Dictionary with storage statistics and metadata
        """
        stats = self.storage.get_stats()
        
        if "error" in stats:
            return {
                "status": "error",
                "error": stats["error"],
                "db_path": stats["db_path"],
                "timestamp": datetime.now(UTC).isoformat()
            }
        
        return {
            "status": "success",
            "total_threads": stats["total_threads"],
            "archived_threads": stats["archived_threads"],
            "active_threads": stats["active_threads"],
            "oldest_thread": stats["oldest_thread"],
            "most_recent_use": stats["most_recent_use"],
            "db_path": stats["db_path"],
            "cleanup_days": stats["cleanup_days"],
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    def cleanup_stale_threads(self) -> Dict[str, Any]:
        """Clean up stale threads and return results.
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            removed_count = self.storage.cleanup_stale_threads()
            return {
                "status": "success",
                "removed_count": removed_count,
                "message": f"Removed {removed_count} stale thread mappings",
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def find_threads_by_channel(self, channel_id: str) -> Dict[str, Any]:
        """Find all threads in a specific channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Dictionary with thread list and metadata
        """
        try:
            threads = self.storage.find_threads_by_channel(channel_id)
            thread_data = []
            
            for thread in threads:
                thread_data.append({
                    "session_id": thread.session_id,
                    "thread_id": thread.thread_id,
                    "channel_id": thread.channel_id,
                    "thread_name": thread.thread_name,
                    "created_at": thread.created_at.isoformat(),
                    "last_used": thread.last_used.isoformat(),
                    "is_archived": thread.is_archived
                })
            
            return {
                "status": "success",
                "channel_id": channel_id,
                "thread_count": len(threads),
                "threads": thread_data,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "channel_id": channel_id,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def find_thread_by_name(self, channel_id: str, thread_name: str) -> Dict[str, Any]:
        """Find a specific thread by name.
        
        Args:
            channel_id: Discord channel ID
            thread_name: Thread name to search for
            
        Returns:
            Dictionary with thread information or None if not found
        """
        try:
            thread = self.storage.find_thread_by_name(channel_id, thread_name)
            
            if thread:
                return {
                    "status": "success",
                    "found": True,
                    "thread": {
                        "session_id": thread.session_id,
                        "thread_id": thread.thread_id,
                        "channel_id": thread.channel_id,
                        "thread_name": thread.thread_name,
                        "created_at": thread.created_at.isoformat(),
                        "last_used": thread.last_used.isoformat(),
                        "is_archived": thread.is_archived
                    },
                    "timestamp": datetime.now(UTC).isoformat()
                }
            else:
                return {
                    "status": "success",
                    "found": False,
                    "channel_id": channel_id,
                    "thread_name": thread_name,
                    "timestamp": datetime.now(UTC).isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "channel_id": channel_id,
                "thread_name": thread_name,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def get_thread_by_session(self, session_id: str) -> Dict[str, Any]:
        """Get thread information for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with thread information or None if not found
        """
        try:
            thread = self.storage.get_thread(session_id)
            
            if thread:
                return {
                    "status": "success",
                    "found": True,
                    "thread": {
                        "session_id": thread.session_id,
                        "thread_id": thread.thread_id,
                        "channel_id": thread.channel_id,
                        "thread_name": thread.thread_name,
                        "created_at": thread.created_at.isoformat(),
                        "last_used": thread.last_used.isoformat(),
                        "is_archived": thread.is_archived
                    },
                    "timestamp": datetime.now(UTC).isoformat()
                }
            else:
                return {
                    "status": "success",
                    "found": False,
                    "session_id": session_id,
                    "timestamp": datetime.now(UTC).isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def update_thread_status(self, session_id: str, is_archived: bool) -> Dict[str, Any]:
        """Update thread archived status.
        
        Args:
            session_id: Session identifier
            is_archived: New archived status
            
        Returns:
            Dictionary with update results
        """
        try:
            success = self.storage.update_thread_status(session_id, is_archived)
            
            return {
                "status": "success" if success else "not_found",
                "updated": success,
                "session_id": session_id,
                "is_archived": is_archived,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def remove_thread(self, session_id: str) -> Dict[str, Any]:
        """Remove a thread from storage.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with removal results
        """
        try:
            success = self.storage.remove_thread(session_id)
            
            return {
                "status": "success" if success else "not_found",
                "removed": success,
                "session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report for ThreadStorage.
        
        Returns:
            Dictionary with health report including recommendations
        """
        try:
            stats = self.get_storage_statistics()
            
            if stats["status"] == "error":
                return {
                    "status": "unhealthy",
                    "issues": ["Database access error"],
                    "recommendations": ["Check database file permissions", "Verify storage path exists"],
                    "stats": stats,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            
            issues = []
            recommendations = []
            
            # Check for high thread count
            if stats["total_threads"] > 1000:
                issues.append("High thread count may impact performance")
                recommendations.append("Consider running cleanup to remove stale threads")
            
            # Check for high archive ratio
            if stats["total_threads"] > 0:
                archive_ratio = stats["archived_threads"] / stats["total_threads"]
                if archive_ratio > 0.8:
                    issues.append("High percentage of archived threads")
                    recommendations.append("Consider cleanup or archive management")
            
            # Check for old threads
            if stats["oldest_thread"]:
                try:
                    oldest_date = datetime.fromisoformat(stats["oldest_thread"])
                    days_old = (datetime.now(UTC) - oldest_date).days
                    if days_old > stats["cleanup_days"] * 2:
                        issues.append(f"Oldest thread is {days_old} days old")
                        recommendations.append("Run cleanup to remove very old threads")
                except (ValueError, TypeError):
                    pass
            
            health_status = "healthy" if not issues else "issues_detected"
            
            return {
                "status": health_status,
                "issues": issues,
                "recommendations": recommendations,
                "stats": stats,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def close(self):
        """Close the ThreadStorage connection."""
        self.storage.close()


def main():
    """CLI interface for ThreadStorage management."""
    if not THREAD_STORAGE_AVAILABLE:
        print("Error: ThreadStorage is not available")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python thread_storage_manager.py <command> [args...]")
        print("Commands:")
        print("  stats           - Show storage statistics")
        print("  cleanup         - Clean up stale threads")
        print("  health          - Show health report")
        print("  find-channel <channel_id> - Find threads in channel")
        print("  find-name <channel_id> <thread_name> - Find thread by name")
        print("  get-session <session_id> - Get thread for session")
        print("  archive <session_id> - Archive thread")
        print("  unarchive <session_id> - Unarchive thread")
        print("  remove <session_id> - Remove thread")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = ThreadStorageManager()
    
    try:
        if command == "stats":
            result = manager.get_storage_statistics()
        elif command == "cleanup":
            result = manager.cleanup_stale_threads()
        elif command == "health":
            result = manager.get_health_report()
        elif command == "find-channel":
            if len(sys.argv) < 3:
                print("Usage: find-channel <channel_id>")
                sys.exit(1)
            result = manager.find_threads_by_channel(sys.argv[2])
        elif command == "find-name":
            if len(sys.argv) < 4:
                print("Usage: find-name <channel_id> <thread_name>")
                sys.exit(1)
            result = manager.find_thread_by_name(sys.argv[2], sys.argv[3])
        elif command == "get-session":
            if len(sys.argv) < 3:
                print("Usage: get-session <session_id>")
                sys.exit(1)
            result = manager.get_thread_by_session(sys.argv[2])
        elif command == "archive":
            if len(sys.argv) < 3:
                print("Usage: archive <session_id>")
                sys.exit(1)
            result = manager.update_thread_status(sys.argv[2], True)
        elif command == "unarchive":
            if len(sys.argv) < 3:
                print("Usage: unarchive <session_id>")
                sys.exit(1)
            result = manager.update_thread_status(sys.argv[2], False)
        elif command == "remove":
            if len(sys.argv) < 3:
                print("Usage: remove <session_id>")
                sys.exit(1)
            result = manager.remove_thread(sys.argv[2])
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
        
        print(json.dumps(result, indent=2))
    
    finally:
        manager.close()


if __name__ == "__main__":
    main()