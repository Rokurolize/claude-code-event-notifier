#!/usr/bin/env python3
"""Path utility functions for Discord Notifier.

This module provides utility functions for path manipulation and extraction,
specifically for converting Claude Code internal paths to user-friendly paths.
"""

import re
from typing import Optional


def extract_working_directory_from_transcript_path(transcript_path: str) -> Optional[str]:
    """Extract working directory from Claude Code transcript path.
    
    Claude Code stores transcripts in internal paths like:
    `/home/ubuntu/.claude/projects/-home-ubuntu-workbench-projects-project-name/`
    
    This function converts them to actual working directories:
    `/home/ubuntu/workbench/projects/project-name/`
    
    Args:
        transcript_path: Path to transcript file from Claude Code
        
    Returns:
        Working directory path that user can cd into, or None if conversion fails
        
    Examples:
        >>> path = "/home/ubuntu/.claude/projects/-home-ubuntu-workbench-projects-claude-code-event-notifier-bugfix/session.jsonl"
        >>> extract_working_directory_from_transcript_path(path)
        '/home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix'
    """
    if not transcript_path:
        return None
        
    # Pattern to match Claude Code internal project paths
    # Format: /home/ubuntu/.claude/projects/-home-ubuntu-workbench-projects-PROJECT_NAME/
    pattern = r'/home/ubuntu/\.claude/projects/-home-ubuntu-workbench-projects-([^/]+)/'
    
    match = re.search(pattern, transcript_path)
    if not match:
        return None
        
    project_name = match.group(1)
    
    # Convert to actual working directory
    working_dir = f"/home/ubuntu/workbench/projects/{project_name}"
    
    return working_dir


def get_project_name_from_path(path: str) -> Optional[str]:
    """Extract project name from any path.
    
    Args:
        path: File or directory path
        
    Returns:
        Project name extracted from path, or None if not found
        
    Examples:
        >>> get_project_name_from_path("/home/ubuntu/workbench/projects/my-project/file.py")
        'my-project'
        >>> get_project_name_from_path("/home/ubuntu/.claude/projects/-home-ubuntu-workbench-projects-my-project/")
        'my-project'
    """
    if not path:
        return None
        
    # Try to extract from actual working directory
    workbench_match = re.search(r'/home/ubuntu/workbench/projects/([^/]+)', path)
    if workbench_match:
        return workbench_match.group(1)
        
    # Try to extract from Claude Code internal path
    claude_match = re.search(r'/home/ubuntu/\.claude/projects/-home-ubuntu-workbench-projects-([^/]+)', path)
    if claude_match:
        return claude_match.group(1)
        
    return None


def format_cd_command(working_dir: str) -> str:
    """Format a ready-to-use cd command.
    
    Args:
        working_dir: Working directory path
        
    Returns:
        Ready-to-use cd command string
        
    Examples:
        >>> format_cd_command("/home/ubuntu/workbench/projects/my-project")
        'cd /home/ubuntu/workbench/projects/my-project'
    """
    return f"cd {working_dir}"