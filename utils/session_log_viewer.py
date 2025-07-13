#!/usr/bin/env python3
"""Session log viewer for Claude Code Event Notifier.

This tool provides a command-line interface to view and analyze
session logs created by the Discord notifier.
"""

import argparse
import builtins
import contextlib
import json

# Simplified logging setup for CLI tool
import logging
import os
import sys
import time
from pathlib import Path


def setup_minimal_logger(name: str):
    """Create a minimal logger instance for CLI usage."""
    logger = logging.getLogger(name)

    # Simple console handler for errors only
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)

    return SimpleLogger(logger)

class SimpleLogger:
    """Simplified logger for CLI tool usage."""
    def __init__(self, logger):
        self.logger = logger

    def debug(self, event: str, **kwargs) -> None:
        # In production, we can enable this via DISCORD_DEBUG environment variable
        if os.environ.get("DISCORD_DEBUG", "0") == "1":
            context = kwargs.get("context", {})
            ai_todo = kwargs.get("ai_todo", "")
            print(f"DEBUG: {event} | Context: {context} | AI Todo: {ai_todo}")

    def info(self, event: str, **kwargs) -> None:
        # Performance information for large operations
        duration_ms = kwargs.get("duration_ms")
        if duration_ms and duration_ms > 1000:  # Log if operation takes > 1 second
            print(f"INFO: {event} completed in {duration_ms}ms")

    def warning(self, event: str, **kwargs) -> None:
        if "exception" in kwargs:
            self.logger.warning(f"{event}: {kwargs.get('exception', '')}")
        else:
            self.logger.warning(event)

    def error(self, event: str, **kwargs) -> None:
        if "exception" in kwargs:
            self.logger.error(f"{event}: {kwargs.get('exception', '')}")
        else:
            self.logger.error(event)

    def stop(self):
        pass  # No cleanup needed


class SessionLogViewer:
    """View and analyze Claude Code session logs."""

    def __init__(self):
        """Initialize the session log viewer."""
        self.base_dir = Path.home() / ".claude" / "hooks" / "session_logs"

        # Initialize simple logger for internal debugging
        self.logger = setup_minimal_logger(__name__)
        self.logger.info(
            "session_log_viewer_initialized",
            context={"base_dir": str(self.base_dir)},
            ai_todo="Session log viewer ready for operation"
        )

    def list_projects(self) -> None:
        """List all projects with session logs."""
        projects_dir = self.base_dir / "projects"

        print("📁 プロジェクト一覧を取得しています...")
        self.logger.debug(
            "list_projects_started",
            context={"projects_dir": str(projects_dir)}
        )

        if not projects_dir.exists():
            print("No projects found. Session logging may not be enabled.")
            print("To enable: export DISCORD_ENABLE_SESSION_LOGGING=1")
            self.logger.warning(
                "no_projects_directory",
                context={"path": str(projects_dir)},
                ai_todo="Projects directory missing - session logging not enabled"
            )
            return

        print("\n📁 Projects with Session Logs:\n")

        start_time = time.time()
        project_count = 0

        try:
            for project_dir in sorted(projects_dir.iterdir()):
                if project_dir.is_dir():
                    project_count += 1
                    info_path = project_dir / "project_info.json"

                    if info_path.exists():
                        try:
                            with open(info_path) as f:
                                info = json.load(f)

                            print(f"🗂️  {info['project_name']}")
                            print(f"   Path: {info['project_path']}")
                            print(f"   ID: {project_dir.name}")

                            # Count sessions
                            sessions_path = project_dir / "sessions.json"
                            if sessions_path.exists():
                                try:
                                    with open(sessions_path) as f:
                                        sessions = json.load(f)
                                    active = sum(1 for s in sessions if s.get("status") == "active")
                                    complete = sum(1 for s in sessions if s.get("status") == "complete")
                                    print(f"   Sessions: {len(sessions)} total ({active} active, {complete} complete)")

                                    self.logger.debug(
                                        "project_sessions_counted",
                                        context={
                                            "project": info["project_name"],
                                            "total_sessions": len(sessions),
                                            "active_sessions": active,
                                            "complete_sessions": complete
                                        }
                                    )
                                except (json.JSONDecodeError, FileNotFoundError) as e:
                                    print("   Sessions: Error reading sessions file")
                                    self.logger.exception(
                                        "sessions_file_error",
                                        exception=e,
                                        context={"sessions_path": str(sessions_path)},
                                        ai_todo="Fix corrupted sessions.json file"
                                    )
                            print()
                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            print("   Error: Could not read project info")
                            self.logger.exception(
                                "project_info_error",
                                exception=e,
                                context={"info_path": str(info_path)},
                                ai_todo="Fix corrupted project_info.json file"
                            )

            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.info(
                "list_projects_completed",
                context={"project_count": project_count},
                duration_ms=duration_ms,
                ai_todo=f"Listed {project_count} projects in {duration_ms}ms"
            )

        except Exception as e:
            self.logger.exception(
                "list_projects_failed",
                exception=e,
                context={"projects_dir": str(projects_dir)},
                ai_todo="Check file system permissions and directory structure"
            )

    def list_sessions(self, project_hash: str | None = None) -> None:
        """List sessions, optionally filtered by project.

        Args:
            project_hash: Optional project hash to filter by
        """
        start_time = time.time()

        if project_hash:
            print(f"📊 プロジェクト {project_hash} のセッション一覧を取得しています...")

            # List sessions for specific project
            sessions_path = self.base_dir / "projects" / project_hash / "sessions.json"

            self.logger.debug(
                "list_project_sessions_started",
                context={"project_hash": project_hash, "sessions_path": str(sessions_path)}
            )

            if not sessions_path.exists():
                print(f"Project {project_hash} not found")
                self.logger.warning(
                    "project_sessions_not_found",
                    context={"project_hash": project_hash, "path": str(sessions_path)},
                    ai_todo="Check if project hash is correct or session logging is enabled"
                )
                return

            print(f"\n📊 Sessions for project {project_hash}:\n")

            try:
                with open(sessions_path) as f:
                    sessions = json.load(f)

                # Show most recent sessions first
                for session in reversed(sessions[-20:]):  # Last 20 sessions
                    status_icon = "🟢" if session.get("status") == "active" else "⚫"
                    print(f"{status_icon} {session['session_id'][:8]}... - {session['start_time']}")
                    if session.get("end_time"):
                        print(f"   Ended: {session['end_time']}")

                self.logger.debug(
                    "project_sessions_listed",
                    context={"project_hash": project_hash, "session_count": len(sessions)}
                )

            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error reading sessions file: {e}")
                self.logger.exception(
                    "sessions_file_read_error",
                    exception=e,
                    context={"sessions_path": str(sessions_path)},
                    ai_todo="Fix corrupted or missing sessions.json file"
                )
        else:
            print("📊 最新セッション一覧を取得しています...")

            # List all recent sessions
            sessions_dir = self.base_dir / "sessions"

            self.logger.debug(
                "list_all_sessions_started",
                context={"sessions_dir": str(sessions_dir)}
            )

            if not sessions_dir.exists():
                print("No sessions found")
                self.logger.warning(
                    "sessions_directory_not_found",
                    context={"sessions_dir": str(sessions_dir)},
                    ai_todo="Check if session logging is enabled"
                )
                return

            print("\n📊 Recent Sessions:\n")

            try:
                # Get all session directories sorted by modification time
                session_dirs = sorted(
                    [d for d in sessions_dir.iterdir() if d.is_dir()],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )[:20]  # Last 20 sessions

                self.logger.debug(
                    "session_directories_found",
                    context={"total_sessions": len(session_dirs)}
                )

                for session_dir in session_dirs:
                    metadata_path = session_dir / "metadata.json"
                    if metadata_path.exists():
                        try:
                            with open(metadata_path) as f:
                                metadata = json.load(f)

                            project_name = Path(metadata["project_path"]).name
                            print(f"📍 {session_dir.name[:8]}... - {project_name}")
                            print(f"   Started: {metadata['start_time']}")
                            print(f"   Events: {metadata.get('event_count', 0)}")
                            print()
                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            print(f"   Error reading metadata for {session_dir.name[:8]}...")
                            self.logger.exception(
                                "metadata_read_error",
                                exception=e,
                                context={"metadata_path": str(metadata_path)},
                                ai_todo="Fix corrupted metadata.json file"
                            )
            except Exception as e:
                print(f"Error accessing sessions directory: {e}")
                self.logger.exception(
                    "sessions_directory_access_error",
                    exception=e,
                    context={"sessions_dir": str(sessions_dir)},
                    ai_todo="Check file system permissions"
                )

        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.info(
            "list_sessions_completed",
            context={"project_hash": project_hash},
            duration_ms=duration_ms,
            ai_todo=f"Session listing completed in {duration_ms}ms"
        )

    def show_session(self, session_id: str, verbose: bool = False) -> None:
        """Show detailed information about a session.

        Args:
            session_id: The session ID (can be partial)
            verbose: Whether to show verbose output
        """
        start_time = time.time()
        print(f"🔍 セッション {session_id} の詳細を取得しています...")

        self.logger.debug(
            "show_session_started",
            context={"session_id": session_id, "verbose": verbose}
        )

        # Find full session ID from partial
        sessions_dir = self.base_dir / "sessions"

        try:
            matching_dirs = [d for d in sessions_dir.iterdir() if d.is_dir() and d.name.startswith(session_id)]
        except Exception as e:
            print(f"Error accessing sessions directory: {e}")
            self.logger.exception(
                "sessions_directory_access_error",
                exception=e,
                context={"sessions_dir": str(sessions_dir)},
                ai_todo="Check file system permissions"
            )
            return

        if not matching_dirs:
            print(f"Session {session_id} not found")
            self.logger.warning(
                "session_not_found",
                context={"session_id": session_id},
                ai_todo="Check if session ID is correct"
            )
            return

        if len(matching_dirs) > 1:
            print(f"Multiple sessions match '{session_id}':")
            for d in matching_dirs:
                print(f"  - {d.name}")
            print("\nPlease provide more characters to uniquely identify the session")
            self.logger.warning(
                "ambiguous_session_id",
                context={"session_id": session_id, "matches": len(matching_dirs)},
                ai_todo="User needs to provide more specific session ID"
            )
            return

        session_dir = matching_dirs[0]
        full_session_id = session_dir.name

        self.logger.debug(
            "session_found",
            context={"full_session_id": full_session_id, "session_dir": str(session_dir)}
        )

        # Load metadata
        metadata_path = session_dir / "metadata.json"
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading session metadata: {e}")
            self.logger.exception(
                "metadata_load_error",
                exception=e,
                context={"metadata_path": str(metadata_path)},
                ai_todo="Fix corrupted or missing metadata.json file"
            )
            return

        print(f"\n🔍 Session Details: {full_session_id}\n")
        print(f"📁 Project: {metadata['project_path']}")
        print(f"🕐 Started: {metadata['start_time']}")
        if metadata.get("last_updated"):
            print(f"🕑 Last Updated: {metadata['last_updated']}")
        print(f"📊 Total Events: {metadata.get('event_count', 0)}")
        print()

        # Show recent events
        events_dir = session_dir / "events"
        if events_dir.exists():
            try:
                event_files = sorted(events_dir.glob("*.json"))

                self.logger.debug(
                    "events_directory_scanned",
                    context={"event_count": len(event_files), "events_dir": str(events_dir)}
                )

                if event_files:
                    print("📜 Recent Events:")
                    print("-" * 60)

                    # Show last 10 events (or all if verbose)
                    events_to_show = event_files if verbose else event_files[-10:]

                    # Performance logging for large files
                    if len(event_files) > 100:
                        self.logger.info(
                            "large_session_processing",
                            context={"total_events": len(event_files), "showing": len(events_to_show)},
                            ai_todo="Processing large session - may take longer"
                        )

                    for event_file in events_to_show:
                        try:
                            with open(event_file) as f:
                                event = json.load(f)

                            timestamp = event.get("timestamp", "Unknown")
                            event_type = event.get("event_type", "Unknown")
                            tool_name = event.get("tool_name", "N/A")

                            # Format based on event type
                            if event_type in ["PreToolUse", "PostToolUse"]:
                                print(f"{event['sequence']:06d} | {timestamp} | {event_type:<15} | {tool_name}")

                                # Show additional details for specific tools
                                if tool_name == "Bash" and event.get("tool_input", {}).get("command"):
                                    cmd = event["tool_input"]["command"]
                                    if len(cmd) > 50:
                                        cmd = cmd[:47] + "..."
                                    print(f"         Command: {cmd}")
                                elif tool_name == "Task" and event.get("tool_input", {}).get("description"):
                                    desc = event["tool_input"]["description"]
                                    print(f"         Task: {desc}")
                            else:
                                print(f"{event['sequence']:06d} | {timestamp} | {event_type}")
                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            print(f"         Error reading event {event_file.name}")
                            self.logger.exception(
                                "event_file_read_error",
                                exception=e,
                                context={"event_file": str(event_file)},
                                ai_todo="Fix corrupted event file"
                            )

                    if not verbose and len(event_files) > 10:
                        print(f"\n... and {len(event_files) - 10} more events")
                        print("Use --verbose to see all events")

            except Exception as e:
                print(f"Error processing events directory: {e}")
                self.logger.exception(
                    "events_processing_error",
                    exception=e,
                    context={"events_dir": str(events_dir)},
                    ai_todo="Check events directory permissions and structure"
                )

        # Show subagent activity if any
        subagents_dir = session_dir / "subagents"
        if subagents_dir.exists():
            try:
                subagent_dirs = list(subagents_dir.iterdir())
                if subagent_dirs:
                    print("\n🤖 Subagent Activity:")
                    print("-" * 60)

                    for parent_dir in sorted(subagent_dirs)[:5]:
                        if parent_dir.is_dir():
                            metadata_path = parent_dir / "metadata.json"
                            if metadata_path.exists():
                                try:
                                    with open(metadata_path) as f:
                                        sub_meta = json.load(f)
                                    print(f"Parent Task: {parent_dir.name[:8]}...")
                                    if sub_meta.get("prompt"):
                                        prompt_preview = sub_meta["prompt"][:100]
                                        if len(sub_meta["prompt"]) > 100:
                                            prompt_preview += "..."
                                        print(f"  Prompt: {prompt_preview}")
                                except (json.JSONDecodeError, FileNotFoundError) as e:
                                    print("  Error reading subagent metadata")
                                    self.logger.exception(
                                        "subagent_metadata_error",
                                        exception=e,
                                        context={"metadata_path": str(metadata_path)},
                                        ai_todo="Fix corrupted subagent metadata"
                                    )

                    self.logger.debug(
                        "subagent_activity_shown",
                        context={"subagent_count": len(subagent_dirs)}
                    )
            except Exception as e:
                print(f"Error processing subagents directory: {e}")
                self.logger.exception(
                    "subagents_processing_error",
                    exception=e,
                    context={"subagents_dir": str(subagents_dir)},
                    ai_todo="Check subagents directory permissions"
                )

        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.info(
            "show_session_completed",
            context={"session_id": session_id, "full_session_id": full_session_id},
            duration_ms=duration_ms,
            ai_todo=f"Session details displayed in {duration_ms}ms"
        )

    def analyze_session(self, session_id: str) -> None:
        """Analyze a session and show statistics.

        Args:
            session_id: The session ID (can be partial)
        """
        start_time = time.time()
        print(f"📊 セッション {session_id} を分析しています...")

        self.logger.debug(
            "analyze_session_started",
            context={"session_id": session_id}
        )

        # Find full session ID
        sessions_dir = self.base_dir / "sessions"

        try:
            matching_dirs = [d for d in sessions_dir.iterdir() if d.is_dir() and d.name.startswith(session_id)]
        except Exception as e:
            print(f"Error accessing sessions directory: {e}")
            self.logger.exception(
                "sessions_access_error_in_analyze",
                exception=e,
                context={"sessions_dir": str(sessions_dir)},
                ai_todo="Check file system permissions"
            )
            return

        if not matching_dirs:
            print(f"Session {session_id} not found")
            self.logger.warning(
                "session_not_found_in_analyze",
                context={"session_id": session_id},
                ai_todo="Check if session ID is correct"
            )
            return

        session_dir = matching_dirs[0]
        full_session_id = session_dir.name

        print(f"\n📊 Session Analysis: {full_session_id}\n")

        self.logger.debug(
            "session_found_for_analysis",
            context={"full_session_id": full_session_id}
        )

        # Collect statistics
        tool_counts: dict[str, int] = {}
        error_count = 0
        total_duration_ms = 0
        file_operations: set[str] = set()
        events_processed = 0

        events_dir = session_dir / "events"
        if events_dir.exists():
            try:
                event_files = list(events_dir.glob("*.json"))

                # Performance logging for large sessions
                if len(event_files) > 500:
                    self.logger.info(
                        "large_session_analysis",
                        context={"event_count": len(event_files)},
                        ai_todo="Analyzing large session - this may take a while"
                    )

                for event_file in event_files:
                    try:
                        with open(event_file) as f:
                            event = json.load(f)

                        events_processed += 1

                        # Count tool usage
                        if tool_name := event.get("tool_name"):
                            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

                        # Count errors
                        if event.get("error") or event.get("exit_code", 0) != 0:
                            error_count += 1

                        # Track file operations
                        if tool_name in ["Read", "Write", "Edit", "MultiEdit"]:
                            if file_path := event.get("tool_input", {}).get("file_path"):
                                file_operations.add(file_path)

                        # Sum durations
                        if duration := event.get("duration_ms"):
                            total_duration_ms += duration

                    except (json.JSONDecodeError, FileNotFoundError) as e:
                        self.logger.exception(
                            "event_analysis_error",
                            exception=e,
                            context={"event_file": str(event_file)},
                            ai_todo="Skip corrupted event file in analysis"
                        )

                self.logger.debug(
                    "events_analyzed",
                    context={
                        "events_processed": events_processed,
                        "tool_types": len(tool_counts),
                        "files_modified": len(file_operations),
                        "errors_found": error_count
                    }
                )

            except Exception as e:
                print(f"Error analyzing events: {e}")
                self.logger.exception(
                    "events_analysis_error",
                    exception=e,
                    context={"events_dir": str(events_dir)},
                    ai_todo="Check events directory structure and permissions"
                )
                return

        # Display statistics
        print("🔧 Tool Usage:")
        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool}: {count}")

        print(f"\n📁 Files Modified: {len(file_operations)}")
        if file_operations and len(file_operations) <= 10:
            for file_path in sorted(file_operations):
                print(f"  - {file_path}")
        elif len(file_operations) > 10:
            for file_path in sorted(list(file_operations)[:10]):
                print(f"  - {file_path}")
            print(f"  ... and {len(file_operations) - 10} more files")

        print(f"\n⚠️  Errors: {error_count}")
        print(f"⏱️  Total Tool Duration: {total_duration_ms / 1000:.1f}s")

        # Success rate
        total_events = sum(tool_counts.values())
        if total_events > 0:
            success_rate = (total_events - error_count) / total_events * 100
            print(f"✅ Success Rate: {success_rate:.1f}%")

        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.info(
            "analyze_session_completed",
            context={
                "session_id": session_id,
                "full_session_id": full_session_id,
                "events_processed": events_processed,
                "tool_types": len(tool_counts),
                "files_modified": len(file_operations),
                "error_count": error_count,
                "success_rate": success_rate if total_events > 0 else 0
            },
            duration_ms=duration_ms,
            ai_todo=f"Session analysis completed in {duration_ms}ms"
        )


def main():
    """Main entry point for the session log viewer."""
    # Initialize global logger for main function
    main_logger = setup_minimal_logger("session_log_viewer.main")

    start_time = time.time()
    main_logger.info(
        "session_log_viewer_started",
        context={"args": " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "no_args"},
        ai_todo="CLI session log viewer starting up"
    )

    parser = argparse.ArgumentParser(
        description="View and analyze Claude Code session logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --list-projects              # List all projects
  %(prog)s --list-sessions              # List recent sessions
  %(prog)s --list-sessions abc123       # List sessions for project abc123
  %(prog)s --show-session 8963fa2a      # Show session details
  %(prog)s --analyze 8963fa2a           # Analyze session statistics
""",
    )

    parser.add_argument("--list-projects", action="store_true", help="List all projects with session logs")
    parser.add_argument(
        "--list-sessions",
        nargs="?",
        const=True,
        metavar="PROJECT_HASH",
        help="List sessions (optionally for a specific project)",
    )
    parser.add_argument("--show-session", metavar="SESSION_ID", help="Show detailed information about a session")
    parser.add_argument("--analyze", metavar="SESSION_ID", help="Analyze a session and show statistics")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    try:
        args = parser.parse_args()
        viewer = SessionLogViewer()

        # Execute requested action
        if args.list_projects:
            main_logger.debug("executing_list_projects", context={"command": "list_projects"})
            viewer.list_projects()
        elif args.list_sessions is not False:  # Can be True or a string
            if args.list_sessions is True:
                main_logger.debug("executing_list_all_sessions", context={"command": "list_sessions"})
                viewer.list_sessions()
            else:
                main_logger.debug(
                    "executing_list_project_sessions",
                    context={"command": "list_sessions", "project_hash": args.list_sessions}
                )
                viewer.list_sessions(args.list_sessions)
        elif args.show_session:
            main_logger.debug(
                "executing_show_session",
                context={"command": "show_session", "session_id": args.show_session, "verbose": args.verbose}
            )
            viewer.show_session(args.show_session, verbose=args.verbose)
        elif args.analyze:
            main_logger.debug(
                "executing_analyze_session",
                context={"command": "analyze", "session_id": args.analyze}
            )
            viewer.analyze_session(args.analyze)
        else:
            main_logger.debug("showing_help", context={"command": "help"})
            parser.print_help()

        duration_ms = int((time.time() - start_time) * 1000)
        main_logger.info(
            "session_log_viewer_completed",
            context={"total_duration_ms": duration_ms},
            ai_todo=f"CLI operation completed successfully in {duration_ms}ms"
        )

    except KeyboardInterrupt:
        print("\n💫 中断されました...")
        main_logger.warning(
            "session_log_viewer_interrupted",
            context={"signal": "KeyboardInterrupt"},
            ai_todo="User interrupted the CLI operation"
        )
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        main_logger.exception(
            "session_log_viewer_error",
            exception=e,
            ai_todo="Unexpected error in main function - needs investigation"
        )
        sys.exit(1)
    finally:
        # Ensure logger cleanup
        with contextlib.suppress(builtins.BaseException):
            main_logger.stop()


if __name__ == "__main__":
    main()
