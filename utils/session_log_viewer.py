#!/usr/bin/env python3
"""Session log viewer for Claude Code Event Notifier.

This tool provides a command-line interface to view and analyze
session logs created by the Discord notifier.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class SessionLogViewer:
    """View and analyze Claude Code session logs."""

    def __init__(self):
        """Initialize the session log viewer."""
        self.base_dir = Path.home() / ".claude" / "hooks" / "session_logs"

    def list_projects(self) -> None:
        """List all projects with session logs."""
        projects_dir = self.base_dir / "projects"
        if not projects_dir.exists():
            print("No projects found. Session logging may not be enabled.")
            print("To enable: export DISCORD_ENABLE_SESSION_LOGGING=1")
            return

        print("\n📁 Projects with Session Logs:\n")

        for project_dir in sorted(projects_dir.iterdir()):
            if project_dir.is_dir():
                info_path = project_dir / "project_info.json"
                if info_path.exists():
                    with open(info_path) as f:
                        info = json.load(f)

                    print(f"🗂️  {info['project_name']}")
                    print(f"   Path: {info['project_path']}")
                    print(f"   ID: {project_dir.name}")

                    # Count sessions
                    sessions_path = project_dir / "sessions.json"
                    if sessions_path.exists():
                        with open(sessions_path) as f:
                            sessions = json.load(f)
                        active = sum(1 for s in sessions if s.get("status") == "active")
                        complete = sum(1 for s in sessions if s.get("status") == "complete")
                        print(f"   Sessions: {len(sessions)} total ({active} active, {complete} complete)")
                    print()

    def list_sessions(self, project_hash: Optional[str] = None) -> None:
        """List sessions, optionally filtered by project.

        Args:
            project_hash: Optional project hash to filter by
        """
        if project_hash:
            # List sessions for specific project
            sessions_path = self.base_dir / "projects" / project_hash / "sessions.json"
            if not sessions_path.exists():
                print(f"Project {project_hash} not found")
                return

            print(f"\n📊 Sessions for project {project_hash}:\n")

            with open(sessions_path) as f:
                sessions = json.load(f)

            # Show most recent sessions first
            for session in reversed(sessions[-20:]):  # Last 20 sessions
                status_icon = "🟢" if session.get("status") == "active" else "⚫"
                print(f"{status_icon} {session['session_id'][:8]}... - {session['start_time']}")
                if session.get("end_time"):
                    print(f"   Ended: {session['end_time']}")
        else:
            # List all recent sessions
            sessions_dir = self.base_dir / "sessions"
            if not sessions_dir.exists():
                print("No sessions found")
                return

            print("\n📊 Recent Sessions:\n")

            # Get all session directories sorted by modification time
            session_dirs = sorted(
                [d for d in sessions_dir.iterdir() if d.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True
            )[:20]  # Last 20 sessions

            for session_dir in session_dirs:
                metadata_path = session_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)

                    project_name = Path(metadata["project_path"]).name
                    print(f"📍 {session_dir.name[:8]}... - {project_name}")
                    print(f"   Started: {metadata['start_time']}")
                    print(f"   Events: {metadata.get('event_count', 0)}")
                    print()

    def show_session(self, session_id: str, verbose: bool = False) -> None:
        """Show detailed information about a session.

        Args:
            session_id: The session ID (can be partial)
            verbose: Whether to show verbose output
        """
        # Find full session ID from partial
        sessions_dir = self.base_dir / "sessions"
        matching_dirs = [d for d in sessions_dir.iterdir() if d.is_dir() and d.name.startswith(session_id)]

        if not matching_dirs:
            print(f"Session {session_id} not found")
            return

        if len(matching_dirs) > 1:
            print(f"Multiple sessions match '{session_id}':")
            for d in matching_dirs:
                print(f"  - {d.name}")
            print("\nPlease provide more characters to uniquely identify the session")
            return

        session_dir = matching_dirs[0]
        full_session_id = session_dir.name

        # Load metadata
        metadata_path = session_dir / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

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
            event_files = sorted(events_dir.glob("*.json"))

            if event_files:
                print("📜 Recent Events:")
                print("-" * 60)

                # Show last 10 events (or all if verbose)
                events_to_show = event_files if verbose else event_files[-10:]

                for event_file in events_to_show:
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

                if not verbose and len(event_files) > 10:
                    print(f"\n... and {len(event_files) - 10} more events")
                    print("Use --verbose to see all events")

        # Show subagent activity if any
        subagents_dir = session_dir / "subagents"
        if subagents_dir.exists() and any(subagents_dir.iterdir()):
            print("\n🤖 Subagent Activity:")
            print("-" * 60)

            for parent_dir in sorted(subagents_dir.iterdir())[:5]:
                if parent_dir.is_dir():
                    metadata_path = parent_dir / "metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path) as f:
                            sub_meta = json.load(f)
                        print(f"Parent Task: {parent_dir.name[:8]}...")
                        if sub_meta.get("prompt"):
                            prompt_preview = sub_meta["prompt"][:100]
                            if len(sub_meta["prompt"]) > 100:
                                prompt_preview += "..."
                            print(f"  Prompt: {prompt_preview}")

    def analyze_session(self, session_id: str) -> None:
        """Analyze a session and show statistics.

        Args:
            session_id: The session ID (can be partial)
        """
        # Find full session ID
        sessions_dir = self.base_dir / "sessions"
        matching_dirs = [d for d in sessions_dir.iterdir() if d.is_dir() and d.name.startswith(session_id)]

        if not matching_dirs:
            print(f"Session {session_id} not found")
            return

        session_dir = matching_dirs[0]

        print(f"\n📊 Session Analysis: {session_dir.name}\n")

        # Collect statistics
        tool_counts: dict[str, int] = {}
        error_count = 0
        total_duration_ms = 0
        file_operations: set[str] = set()

        events_dir = session_dir / "events"
        if events_dir.exists():
            for event_file in events_dir.glob("*.json"):
                with open(event_file) as f:
                    event = json.load(f)

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

        # Display statistics
        print("🔧 Tool Usage:")
        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool}: {count}")

        print(f"\n📁 Files Modified: {len(file_operations)}")
        if file_operations and len(file_operations) <= 10:
            for file_path in sorted(file_operations):
                print(f"  - {file_path}")

        print(f"\n⚠️  Errors: {error_count}")
        print(f"⏱️  Total Tool Duration: {total_duration_ms / 1000:.1f}s")

        # Success rate
        total_events = sum(tool_counts.values())
        if total_events > 0:
            success_rate = (total_events - error_count) / total_events * 100
            print(f"✅ Success Rate: {success_rate:.1f}%")


def main():
    """Main entry point for the session log viewer."""
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

    args = parser.parse_args()
    viewer = SessionLogViewer()

    # Execute requested action
    if args.list_projects:
        viewer.list_projects()
    elif args.list_sessions is not False:  # Can be True or a string
        if args.list_sessions is True:
            viewer.list_sessions()
        else:
            viewer.list_sessions(args.list_sessions)
    elif args.show_session:
        viewer.show_session(args.show_session, verbose=args.verbose)
    elif args.analyze:
        viewer.analyze_session(args.analyze)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
