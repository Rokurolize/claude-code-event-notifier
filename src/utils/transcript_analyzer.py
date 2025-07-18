#!/usr/bin/env python3
"""
Transcript File Analyzer for Subagent Content Extraction

This module provides functionality to extract subagent responses from Claude Code transcript files.
Since Claude Code Hook SubagentStop events don't include conversation content,
this module analyzes the transcript file to extract actual subagent responses.

Author: Astolfo (Discord Event Notifier Team)
Date: 2025-07-16
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, TypedDict
from datetime import datetime


class SubagentResponse(TypedDict):
    """Subagent response extracted from transcript."""
    subagent_id: str
    conversation_log: str
    response_content: str
    task_description: str
    duration_seconds: float
    tools_used: int
    timestamp: str
    prompt: str


class TranscriptAnalyzer:
    """Analyze Claude Code transcript files to extract subagent information."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def extract_subagent_responses(self, transcript_path: str) -> List[SubagentResponse]:
        """Extract all subagent responses from transcript file.
        
        Args:
            transcript_path: Path to the transcript .jsonl file
            
        Returns:
            List of SubagentResponse objects containing extracted information
        """
        try:
            transcript_file = Path(transcript_path)
            if not transcript_file.exists():
                self.logger.warning(f"Transcript file not found: {transcript_path}")
                return []
                
            responses = []
            current_tasks = {}  # Track ongoing tasks by tool_use_id
            
            with open(transcript_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                        
                    try:
                        entry = json.loads(line)
                        
                        # Track task starts (tool_use with Task)
                        if self._is_task_start(entry):
                            task_info = self._extract_task_info(entry)
                            if task_info:
                                current_tasks[task_info['tool_use_id']] = task_info
                                
                        # Track subagent responses (isSidechain=true with assistant response)
                        elif self._is_subagent_response(entry):
                            response_info = self._extract_response_info(entry)
                            if response_info:
                                # Try to match with corresponding task
                                matching_task = self._find_matching_task(
                                    response_info, current_tasks
                                )
                                
                                if matching_task:
                                    combined_response = self._combine_task_and_response(
                                        matching_task, response_info
                                    )
                                    responses.append(combined_response)
                                    
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Invalid JSON at line {line_num}: {e}")
                        continue
                    except Exception as e:
                        self.logger.warning(f"Error processing line {line_num}: {e}")
                        continue
                        
            self.logger.info(f"Extracted {len(responses)} subagent responses from {transcript_path}")
            return responses
            
        except Exception as e:
            self.logger.error(f"Error reading transcript file {transcript_path}: {e}")
            return []
    
    def _is_task_start(self, entry: dict) -> bool:
        """Check if entry represents a Task tool invocation."""
        message = entry.get('message', {})
        if not isinstance(message, dict):
            return False
            
        content = message.get('content', [])
        if not isinstance(content, list):
            return False
            
        for item in content:
            if (isinstance(item, dict) and 
                item.get('type') == 'tool_use' and 
                item.get('name') == 'Task'):
                return True
        return False
    
    def _extract_task_info(self, entry: dict) -> Optional[Dict]:
        """Extract task information from tool_use entry."""
        message = entry.get('message', {})
        content = message.get('content', [])
        
        for item in content:
            if (isinstance(item, dict) and 
                item.get('type') == 'tool_use' and 
                item.get('name') == 'Task'):
                
                tool_input = item.get('input', {})
                return {
                    'tool_use_id': item.get('id'),
                    'description': tool_input.get('description', ''),
                    'prompt': tool_input.get('prompt', ''),
                    'timestamp': entry.get('timestamp', ''),
                    'session_id': entry.get('sessionId', '')
                }
        return None
    
    def _is_subagent_response(self, entry: dict) -> bool:
        """Check if entry is a subagent response (isSidechain=true with assistant content)."""
        return (entry.get('isSidechain') is True and 
                entry.get('type') == 'assistant' and
                entry.get('message', {}).get('role') == 'assistant')
    
    def _extract_response_info(self, entry: dict) -> Optional[Dict]:
        """Extract response information from subagent entry."""
        message = entry.get('message', {})
        content = message.get('content', [])
        
        response_text = ""
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                response_text += item.get('text', '')
        
        if not response_text:
            return None
            
        return {
            'response_content': response_text,
            'timestamp': entry.get('timestamp', ''),
            'session_id': entry.get('sessionId', ''),
            'message_id': message.get('id', ''),
            'uuid': entry.get('uuid', '')
        }
    
    def _find_matching_task(self, response_info: Dict, current_tasks: Dict) -> Optional[Dict]:
        """Find the task that corresponds to this response."""
        # Simple matching strategy: return the most recent task for the same session
        # This could be improved with more sophisticated matching logic
        matching_tasks = [
            task for task in current_tasks.values()
            if task['session_id'] == response_info['session_id']
        ]
        
        if not matching_tasks:
            return None
            
        # Return the most recent task
        return max(matching_tasks, key=lambda x: x.get('timestamp', ''))
    
    def _combine_task_and_response(self, task_info: Dict, response_info: Dict) -> SubagentResponse:
        """Combine task and response information into SubagentResponse."""
        # Calculate duration
        task_time = datetime.fromisoformat(task_info['timestamp'].replace('Z', '+00:00'))
        response_time = datetime.fromisoformat(response_info['timestamp'].replace('Z', '+00:00'))
        duration = (response_time - task_time).total_seconds()
        
        # Generate subagent ID
        subagent_id = f"subagent_{response_info['uuid'][:8]}"
        
        return SubagentResponse(
            subagent_id=subagent_id,
            conversation_log=f"User: {task_info['prompt']}\nAssistant: {response_info['response_content']}",
            response_content=response_info['response_content'],
            task_description=task_info['description'],
            duration_seconds=duration,
            tools_used=0,  # Would need more analysis to determine actual tool usage
            timestamp=response_info['timestamp'],
            prompt=task_info['prompt']
        )
    
    def get_latest_subagent_response(self, transcript_path: str) -> Optional[SubagentResponse]:
        """Get the most recent subagent response from transcript."""
        responses = self.extract_subagent_responses(transcript_path)
        if not responses:
            return None
            
        # Return the most recent response
        return max(responses, key=lambda x: x['timestamp'])
    
    def get_subagent_responses_in_timeframe(
        self, 
        transcript_path: str, 
        start_time: datetime,
        end_time: datetime
    ) -> List[SubagentResponse]:
        """Get subagent responses within a specific timeframe."""
        responses = self.extract_subagent_responses(transcript_path)
        
        filtered_responses = []
        for response in responses:
            try:
                response_time = datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00'))
                if start_time <= response_time <= end_time:
                    filtered_responses.append(response)
            except ValueError:
                continue
                
        return filtered_responses


def analyze_transcript_file(transcript_path: str) -> List[SubagentResponse]:
    """Convenience function to analyze transcript file."""
    analyzer = TranscriptAnalyzer()
    return analyzer.extract_subagent_responses(transcript_path)


# Example usage for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python transcript_analyzer.py <transcript_path>")
        sys.exit(1)
        
    transcript_path = sys.argv[1]
    responses = analyze_transcript_file(transcript_path)
    
    print(f"Found {len(responses)} subagent responses:")
    for i, response in enumerate(responses, 1):
        print(f"\n{i}. {response['subagent_id']}")
        print(f"   Task: {response['task_description']}")
        print(f"   Response: {response['response_content'][:100]}...")
        print(f"   Duration: {response['duration_seconds']:.2f}s")