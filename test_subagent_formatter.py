#!/usr/bin/env python3
"""Test script to reproduce potential data mixing in SubagentStop formatter."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop
from src.formatters.registry import FormatterRegistry

def test_subagent_formatter():
    """Test SubagentStop formatter with different session IDs."""
    print("Testing SubagentStop formatter for potential data mixing...")
    
    # Create test event data for different "sessions"
    event_data_1 = {
        "session_id": "session-12345",
        "subagent_id": "subagent-1",
        "result": "Task 1 completed: This is the result for session 1",
        "duration_seconds": 45.2,
        "tools_used": 3,
        "transcript_path": "/tmp/nonexistent_transcript_1.jsonl"
    }
    
    event_data_2 = {
        "session_id": "session-67890",
        "subagent_id": "subagent-2", 
        "result": "Task 2 completed: This is the result for session 2 with different content",
        "duration_seconds": 32.1,
        "tools_used": 5,
        "transcript_path": "/tmp/nonexistent_transcript_2.jsonl"
    }
    
    # Test with FormatterRegistry
    registry = FormatterRegistry()
    formatter = registry.get_formatter("SubagentStop")
    
    print("\n=== Test 1: Direct formatter calls ===")
    
    # Format first event
    embed_1 = format_subagent_stop(event_data_1, "12345")
    print(f"Event 1 title: {embed_1.get('title', 'No title')}")
    print(f"Event 1 description preview: {str(embed_1.get('description', ''))[:200]}...")
    
    # Format second event
    embed_2 = format_subagent_stop(event_data_2, "67890") 
    print(f"Event 2 title: {embed_2.get('title', 'No title')}")
    print(f"Event 2 description preview: {str(embed_2.get('description', ''))[:200]}...")
    
    print("\n=== Test 2: Registry formatter calls ===")
    
    # Use registry formatter
    embed_3 = formatter(event_data_1, "12345")
    embed_4 = formatter(event_data_2, "67890")
    
    print(f"Registry Event 1 title: {embed_3.get('title', 'No title')}")
    print(f"Registry Event 1 description preview: {str(embed_3.get('description', ''))[:200]}...")
    print(f"Registry Event 2 title: {embed_4.get('title', 'No title')}")
    print(f"Registry Event 2 description preview: {str(embed_4.get('description', ''))[:200]}...")
    
    print("\n=== Test 3: Check for data leakage ===")
    
    # Check if any content from event 1 appears in event 2 results
    desc_1 = str(embed_1.get('description', ''))
    desc_2 = str(embed_2.get('description', ''))
    desc_3 = str(embed_3.get('description', ''))
    desc_4 = str(embed_4.get('description', ''))
    
    # Look for session ID mixing
    if "session-12345" in desc_2 or "session-12345" in desc_4:
        print("❌ POTENTIAL ISSUE: Session ID from event 1 found in event 2 results")
    else:
        print("✅ No session ID cross-contamination detected")
        
    # Look for result content mixing  
    if "Task 1 completed" in desc_2 or "Task 1 completed" in desc_4:
        print("❌ POTENTIAL ISSUE: Result content from event 1 found in event 2 results")
    elif "Task 2 completed" in desc_1 or "Task 2 completed" in desc_3:
        print("❌ POTENTIAL ISSUE: Result content from event 2 found in event 1 results")
    else:
        print("✅ No result content cross-contamination detected")
        
    # Look for subagent ID mixing
    if "subagent-1" in desc_2 or "subagent-1" in desc_4:
        print("❌ POTENTIAL ISSUE: Subagent ID from event 1 found in event 2 results")
    elif "subagent-2" in desc_1 or "subagent-2" in desc_3:
        print("❌ POTENTIAL ISSUE: Subagent ID from event 2 found in event 1 results")
    else:
        print("✅ No subagent ID cross-contamination detected")

    print("\n=== Test 4: Formatter instance reuse ===")
    
    # Test if the same formatter function instance has any issues
    same_formatter = registry.get_formatter("SubagentStop")
    is_same_instance = formatter is same_formatter
    print(f"Formatter instance reuse: {is_same_instance}")
    
    if is_same_instance:
        print("✅ Formatter is properly reused from registry (no new instances)")
    else:
        print("⚠️  New formatter instance created - check registry implementation")

if __name__ == "__main__":
    test_subagent_formatter()