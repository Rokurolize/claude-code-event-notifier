#!/usr/bin/env python3
"""Test script to check for potential transcript reading data mixing."""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop
from src.utils.transcript_reader import get_subagent_messages

def create_test_transcript(session_id: str, messages: list[str]) -> str:
    """Create a test transcript file with specified messages."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    
    for i, msg in enumerate(messages):
        # Create transcript entry
        entry = {
            "type": "assistant",
            "sessionId": session_id,
            "timestamp": f"2025-07-12T11:30:{i:02d}.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": msg
                    }
                ]
            }
        }
        temp_file.write(json.dumps(entry) + '\n')
    
    temp_file.close()
    return temp_file.name

def test_transcript_reading():
    """Test for potential transcript reading data mixing."""
    print("Testing transcript reading for potential data mixing...")
    
    # Create test transcripts with unique content
    transcript_1_path = create_test_transcript(
        "session-12345",
        [
            "Session 1 message A: Working on task Alpha",
            "Session 1 message B: Processing data for Alpha",
            "Session 1 message C: Completed Alpha task successfully"
        ]
    )
    
    transcript_2_path = create_test_transcript(
        "session-67890", 
        [
            "Session 2 message X: Starting task Beta",
            "Session 2 message Y: Beta analysis in progress",
            "Session 2 message Z: Beta task finished with results"
        ]
    )
    
    print(f"Created test transcripts:")
    print(f"  Transcript 1: {transcript_1_path}")
    print(f"  Transcript 2: {transcript_2_path}")
    
    try:
        print("\n=== Test 1: Direct transcript reading ===")
        
        # Read messages from each transcript
        messages_1 = get_subagent_messages(transcript_1_path, "session-12345", limit=10)
        messages_2 = get_subagent_messages(transcript_2_path, "session-67890", limit=10)
        
        print(f"Transcript 1 messages count: {len(messages_1)}")
        for i, msg in enumerate(messages_1):
            print(f"  {i+1}: {msg.get('content', 'No content')[:50]}...")
            
        print(f"Transcript 2 messages count: {len(messages_2)}")
        for i, msg in enumerate(messages_2):
            print(f"  {i+1}: {msg.get('content', 'No content')[:50]}...")
        
        # Check for cross-contamination in direct reading
        print("\n=== Check 1: Direct reading contamination ===")
        session_1_content = [msg.get('content', '') for msg in messages_1]
        session_2_content = [msg.get('content', '') for msg in messages_2]
        
        # Check if session 1 content appears in session 2 results
        contamination_found = False
        for content_1 in session_1_content:
            if any("Alpha" in content_2 for content_2 in session_2_content):
                print("❌ ISSUE: Session 1 content found in session 2 results")
                contamination_found = True
                break
                
        for content_2 in session_2_content:
            if any("Beta" in content_1 for content_1 in session_1_content):
                print("❌ ISSUE: Session 2 content found in session 1 results")
                contamination_found = True
                break
                
        if not contamination_found:
            print("✅ No direct reading contamination detected")
        
        print("\n=== Test 2: Formatter integration ===")
        
        # Test with formatter integration
        event_data_1 = {
            "session_id": "session-12345",
            "subagent_id": "subagent-alpha",
            "result": "Alpha task result",
            "transcript_path": transcript_1_path
        }
        
        event_data_2 = {
            "session_id": "session-67890", 
            "subagent_id": "subagent-beta",
            "result": "Beta task result",
            "transcript_path": transcript_2_path
        }
        
        # Format embeds
        embed_1 = format_subagent_stop(event_data_1, "12345")
        embed_2 = format_subagent_stop(event_data_2, "67890")
        
        desc_1 = str(embed_1.get('description', ''))
        desc_2 = str(embed_2.get('description', ''))
        
        print(f"Embed 1 description length: {len(desc_1)}")
        print(f"Embed 2 description length: {len(desc_2)}")
        
        # Check fields for cross-contamination
        fields_1 = embed_1.get('fields', [])
        fields_2 = embed_2.get('fields', [])
        
        print(f"Embed 1 fields count: {len(fields_1)}")
        print(f"Embed 2 fields count: {len(fields_2)}")
        
        print("\n=== Check 2: Formatter contamination ===")
        
        # Look for Alpha content in Beta embed
        alpha_in_beta = False
        beta_in_alpha = False
        
        if "Alpha" in desc_2:
            print("❌ ISSUE: Alpha content found in Beta embed description")
            alpha_in_beta = True
            
        if "Beta" in desc_1:
            print("❌ ISSUE: Beta content found in Alpha embed description")
            beta_in_alpha = True
            
        # Check fields
        for field in fields_2:
            field_value = field.get('value', '')
            if "Alpha" in field_value:
                print("❌ ISSUE: Alpha content found in Beta embed fields")
                alpha_in_beta = True
                
        for field in fields_1:
            field_value = field.get('value', '')
            if "Beta" in field_value:
                print("❌ ISSUE: Beta content found in Alpha embed fields")
                beta_in_alpha = True
                
        if not alpha_in_beta and not beta_in_alpha:
            print("✅ No formatter contamination detected")
            
        print("\n=== Test 3: Multiple calls with same session IDs ===")
        
        # Test repeated calls with same session IDs
        embed_1_repeat = format_subagent_stop(event_data_1, "12345")
        embed_2_repeat = format_subagent_stop(event_data_2, "67890")
        
        # Check if results are consistent
        consistent_1 = embed_1.get('description') == embed_1_repeat.get('description')
        consistent_2 = embed_2.get('description') == embed_2_repeat.get('description')
        
        print(f"Embed 1 consistent: {consistent_1}")
        print(f"Embed 2 consistent: {consistent_2}")
        
        if consistent_1 and consistent_2:
            print("✅ Repeated calls produce consistent results")
        else:
            print("❌ ISSUE: Repeated calls produce different results")
            
        print("\n=== Test 4: Rapid alternating calls ===")
        
        # Rapidly alternate between the two events to test for race conditions
        for i in range(5):
            if i % 2 == 0:
                embed_alt = format_subagent_stop(event_data_1, "12345")
                if "Beta" in str(embed_alt.get('description', '')):
                    print(f"❌ ISSUE: Beta content in Alpha embed on iteration {i}")
            else:
                embed_alt = format_subagent_stop(event_data_2, "67890")
                if "Alpha" in str(embed_alt.get('description', '')):
                    print(f"❌ ISSUE: Alpha content in Beta embed on iteration {i}")
                    
        print("✅ Rapid alternating calls completed")
        
    finally:
        # Clean up temp files
        try:
            Path(transcript_1_path).unlink()
            Path(transcript_2_path).unlink()
            print(f"\nCleaned up temporary files")
        except Exception as e:
            print(f"Warning: Could not clean up temp files: {e}")

if __name__ == "__main__":
    test_transcript_reading()