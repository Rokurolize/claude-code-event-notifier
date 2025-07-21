#!/usr/bin/env python3
"""Simple transcript reader for extracting subagent conversations.

Minimal implementation to read Claude Code transcript files and extract
subagent task execution details.
"""

import json
import logging
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)


def read_subagent_messages(transcript_path: str, event_timestamp: str | None = None) -> dict | None:
    """Extract subagent task and response from transcript file.
    
    Args:
        transcript_path: Path to the transcript .jsonl file
        event_timestamp: Optional timestamp to match specific task-response pair
        
    Returns:
        Dict with task info and response, or None if not found
    """
    logger.debug(f"read_subagent_messages called with path: {transcript_path}, event_timestamp: {event_timestamp}")
    
    # Validate transcript path is within expected directories
    try:
        transcript_file = Path(transcript_path).resolve()
        allowed_dirs = [
            Path.home() / ".claude",
            Path("/tmp"),  # Some systems may use tmp
        ]
        if not any(transcript_file.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs):
            logger.error(f"Transcript path outside allowed directories: {transcript_path}")
            return None
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return None
    
    try:
        if not transcript_file.exists():
            logger.debug(f"Transcript file does not exist: {transcript_path}")
            return None
        
        file_size = transcript_file.stat().st_size
        logger.debug(f"Transcript file exists, size: {file_size} bytes")
            
        # Read file in reverse to find most recent task/response pair
        lines = []
        with transcript_file.open('r', encoding='utf-8') as f:
            lines = f.readlines()
        
        logger.debug(f"Read {len(lines)} lines from transcript file")
        
        # Track all task-response pairs found
        task_response_pairs = []
        current_tasks = {}  # Map tool_id to task info
        lines_processed = 0
        json_errors = 0
        
        # Search from end to beginning for efficiency
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line:
                continue
            
            lines_processed += 1
                
            try:
                entry = json.loads(line)
                
                # Found subagent response
                if (entry.get('isSidechain') is True and 
                    entry.get('type') == 'assistant'):
                    
                    message = entry.get('message', {})
                    content = message.get('content', [])
                    response_text = ""
                    
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            response_text += item.get('text', '')
                    
                    if response_text:
                        response_info = {
                            'content': response_text,
                            'timestamp': entry.get('timestamp', '')
                        }
                        
                        # For simple tasks, match the most recent task
                        if current_tasks:
                            # Get the most recently added task (last in dict)
                            task_id = list(current_tasks.keys())[-1]
                            task_info = current_tasks[task_id]
                            task_response_pairs.append({
                                'task': task_info,
                                'response': response_info
                            })
                            logger.debug(f"Matched task-response pair: {task_info['description']}")
                            # Remove matched task to avoid duplicate matching
                            del current_tasks[task_id]
                        else:
                            logger.debug(f"Found response without any pending tasks")
                
                # Found task invocation
                else:
                    message = entry.get('message', {})
                    content = message.get('content', [])
                    if isinstance(content, list):
                        for item in content:
                            if (isinstance(item, dict) and 
                                item.get('type') == 'tool_use' and 
                                item.get('name') == 'Task'):
                                
                                tool_id = item.get('id')
                                tool_input = item.get('input', {})
                                task_info = {
                                    'description': tool_input.get('description', 'Unknown Task'),
                                    'prompt': tool_input.get('prompt', ''),
                                    'timestamp': entry.get('timestamp', ''),
                                    'tool_id': tool_id
                                }
                                
                                if tool_id:
                                    current_tasks[tool_id] = task_info
                                    logger.debug(f"Found Task invocation: {task_info['description']} (tool_id: {tool_id})")
                    
            except json.JSONDecodeError as e:
                json_errors += 1
                if json_errors <= 3:  # Log first few errors only
                    logger.debug(f"JSON decode error at line {i+1}: {e}")
                continue
        
        logger.debug(f"Processed {lines_processed} lines, found {len(task_response_pairs)} task-response pairs")
        
        # Return the most recent task-response pair
        if task_response_pairs:
            # If multiple pairs found, log them
            if len(task_response_pairs) > 1:
                logger.debug(f"Multiple task-response pairs found:")
                for idx, pair in enumerate(task_response_pairs):
                    logger.debug(f"  {idx+1}. {pair['task']['description']}")
            
            # Return the most recent one (last in list since we read backwards)
            most_recent = task_response_pairs[-1]
            logger.debug(f"Returning most recent task-response pair: {most_recent['task']['description']}")
            return most_recent
        else:
            logger.debug(f"No complete task-response pairs found")
        
        return None
        
    except (IOError, OSError) as e:
        logger.exception("Unexpected error reading transcript")
        return None


def format_for_discord(subagent_data: dict) -> str:
    """Format subagent data for Discord message.
    
    Args:
        subagent_data: Dict with task and response info
        
    Returns:
        Formatted markdown string for Discord
    """
    if not subagent_data:
        return "No subagent data available"
        
    task = subagent_data.get('task', {})
    response = subagent_data.get('response', {})
    
    # Calculate duration if timestamps available
    duration = "Unknown"
    if task.get('timestamp') and response.get('timestamp'):
        try:
            from datetime import datetime
            task_time = datetime.fromisoformat(task['timestamp'].replace('Z', '+00:00'))
            response_time = datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00'))
            duration_seconds = (response_time - task_time).total_seconds()
            duration = f"{duration_seconds:.1f}s"
        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to calculate duration: {e}")
    
    # Format message with Discord markdown
    message = f"""## Task Execution Summary

**Description**: {task.get('description', 'Unknown')}
**Duration**: {duration}

### User Prompt
```
{task.get('prompt', 'No prompt available')[:1000]}
```

### Assistant Response
{response.get('content', 'No response available')[:2000]}
"""
    
    return message