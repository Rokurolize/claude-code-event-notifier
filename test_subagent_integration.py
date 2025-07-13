#!/usr/bin/env python3
"""Integration test for SubagentStop events - simulates end-to-end workflow."""

import json
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.discord_notifier import main as discord_main
from src.formatters.event_formatters import format_subagent_stop
from src.utils.transcript_reader import get_subagent_messages
from src.utils.astolfo_logger import AstolfoLogger

# Test data
TEST_EVENTS = [
    {
        "session_id": "test-subagent-12345678",
        "subagent_id": "subagent-alpha-001",
        "result": "Task completed successfully. Added new logging functionality with AstolfoLogger integration.",
        "duration_seconds": 45,
        "tools_used": 8,
        "transcript_path": "/tmp/test_transcript.jsonl"
    },
    {
        "session_id": "test-subagent-87654321",
        "subagent_id": "subagent-beta-002",
        "result": "Successfully implemented Discord notification improvements with enhanced formatting.",
        "duration_seconds": 23,
        "tools_used": 4,
        "transcript_path": "/tmp/test_transcript_2.jsonl"
    }
]

def test_subagent_formatter():
    """Test the SubagentStop formatter directly."""
    logger = AstolfoLogger(__name__)
    
    print("🧪 Testing SubagentStop Formatter")
    print("=" * 50)
    
    for i, event_data in enumerate(TEST_EVENTS, 1):
        session_id = str(event_data["session_id"])[:8]
        
        print(f"\n📋 Test Case {i}: {event_data['subagent_id']}")
        print(f"   Session: {session_id}")
        print(f"   Result: {event_data['result'][:50]}...")
        
        try:
            # Test the formatter
            embed = format_subagent_stop(event_data, session_id)
            
            print("✅ Formatter succeeded")
            print(f"   Title: {embed.get('title', 'No title')}")
            
            description = embed.get('description', '')
            if description:
                print(f"   Description length: {len(description)} chars")
                
                # Check for proper subagent ID isolation
                correct_id = event_data["subagent_id"]
                other_ids = [e["subagent_id"] for e in TEST_EVENTS if e != event_data]
                
                if correct_id in description:
                    print(f"   ✅ Contains correct subagent ID: {correct_id}")
                else:
                    print(f"   ❌ Missing correct subagent ID: {correct_id}")
                
                # Check for cross-contamination
                contaminated = False
                for other_id in other_ids:
                    if other_id in description:
                        print(f"   ❌ CONTAMINATION: Found other subagent ID: {other_id}")
                        contaminated = True
                
                if not contaminated:
                    print("   ✅ No cross-contamination detected")
            
            # Check for fields
            fields = embed.get('fields', [])
            if fields:
                print(f"   Fields: {len(fields)} items")
                for j, field in enumerate(fields[:3]):  # Show first 3 fields
                    field_name = field.get('name', 'Unknown')
                    field_value = field.get('value', '')[:30]
                    print(f"     {j+1}. {field_name}: {field_value}...")
            
            logger.info(
                "SubagentStop formatter test completed",
                test_case=i,
                subagent_id=event_data["subagent_id"],
                session_id=session_id,
                success=True
            )
            
        except Exception as e:
            print(f"   ❌ Formatter failed: {e}")
            logger.error(
                "SubagentStop formatter test failed",
                test_case=i,
                subagent_id=event_data["subagent_id"],
                error=str(e)
            )

def test_transcript_reading():
    """Test transcript reading functionality."""
    print("\n\n🔍 Testing Transcript Reading")
    print("=" * 50)
    
    # Create test transcript files
    test_transcripts = [
        {
            "path": "/tmp/test_transcript.jsonl",
            "session_id": "test-subagent-12345678",
            "messages": [
                {"timestamp": "2025-07-12T11:45:00Z", "type": "user", "role": "user", "content": "Test message 1"},
                {"timestamp": "2025-07-12T11:45:30Z", "type": "assistant", "role": "assistant", "content": "Test response 1"}
            ]
        },
        {
            "path": "/tmp/test_transcript_2.jsonl",
            "session_id": "test-subagent-87654321", 
            "messages": [
                {"timestamp": "2025-07-12T11:46:00Z", "type": "user", "role": "user", "content": "Test message 2"},
                {"timestamp": "2025-07-12T11:46:30Z", "type": "assistant", "role": "assistant", "content": "Test response 2"}
            ]
        }
    ]
    
    for transcript in test_transcripts:
        path = transcript["path"]
        session_id = transcript["session_id"]
        
        print(f"\n📄 Creating test transcript: {path}")
        
        try:
            with open(path, 'w') as f:
                for msg in transcript["messages"]:
                    json.dump({
                        "timestamp": msg["timestamp"],
                        "type": msg["type"],
                        "session_id": session_id,
                        "role": msg["role"],
                        "content": [{"type": "text", "text": msg["content"]}]
                    }, f)
                    f.write('\n')
            
            print(f"   ✅ Created with {len(transcript['messages'])} messages")
            
            # Test reading
            messages = get_subagent_messages(path, session_id, limit=10)
            print(f"   📖 Read {len(messages)} subagent messages")
            
            for i, msg in enumerate(messages[:2]):  # Show first 2
                content = msg.get("content", "")[:30]
                print(f"     {i+1}. {content}...")
                
        except Exception as e:
            print(f"   ❌ Failed to create/read transcript: {e}")

def test_parallel_processing():
    """Test multiple SubagentStop events in parallel."""
    print("\n\n🚀 Testing Parallel Processing Simulation")
    print("=" * 50)
    
    print("Simulating rapid-fire SubagentStop events...")
    
    results = []
    for i, event_data in enumerate(TEST_EVENTS):
        session_id = str(event_data["session_id"])[:8]
        
        try:
            embed = format_subagent_stop(event_data, session_id)
            results.append({
                "event": event_data,
                "embed": embed,
                "success": True
            })
            print(f"   ✅ Event {i+1} processed successfully")
        except Exception as e:
            results.append({
                "event": event_data,
                "embed": None,
                "success": False,
                "error": str(e)
            })
            print(f"   ❌ Event {i+1} failed: {e}")
    
    # Cross-check for contamination
    print("\n🔍 Cross-contamination analysis:")
    for i, result1 in enumerate(results):
        if not result1["success"]:
            continue
            
        embed1 = result1["embed"]
        desc1 = embed1.get("description", "")
        id1 = result1["event"]["subagent_id"]
        
        for j, result2 in enumerate(results):
            if i == j or not result2["success"]:
                continue
                
            id2 = result2["event"]["subagent_id"]
            
            if id2 in desc1:
                print(f"   ❌ Event {i+1} contains data from Event {j+1}")
            else:
                print(f"   ✅ Event {i+1} isolated from Event {j+1}")

def main():
    """Run all integration tests."""
    print("🤖 SubagentStop Integration Test Suite")
    print("=====================================")
    
    # Test 1: Direct formatter testing
    test_subagent_formatter()
    
    # Test 2: Transcript reading
    test_transcript_reading()
    
    # Test 3: Parallel processing simulation
    test_parallel_processing()
    
    print("\n\n🏁 Integration tests completed!")
    print("Check the output above for any issues.")

if __name__ == "__main__":
    main()