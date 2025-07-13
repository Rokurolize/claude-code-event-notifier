#!/usr/bin/env python3
"""Test for the EXACT prompt mixing issue that the audit Astolfo found."""

import json
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop
from src.utils.transcript_reader import get_subagent_messages

def create_mixed_transcript() -> str:
    """Create a transcript with multiple sessions to simulate real conditions."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    
    # Create entries for multiple sessions with Task tool prompts
    sessions = [
        {
            "sessionId": "audit-astolfo-session-001",
            "prompt": "監査アストルフォちゃん♡ このシステムの並列実行ログを調査して、プロンプト混在が起きてる理由を特定してね！詳細なレポートを作成して、根本原因を解明してください。"
        },
        {
            "sessionId": "code-astolfo-session-002", 
            "prompt": "コードアストルフォちゃん♡ 新しいログシステムを実装して、バグを修正してね！AstolfoLoggerの拡張機能も追加してください。"
        },
        {
            "sessionId": "test-astolfo-session-003",
            "prompt": "テストアストルフォちゃん♡ 全てのユニットテストを実行して、カバレッジレポートを生成してね！"
        }
    ]
    
    for i, session in enumerate(sessions):
        # Each session has multiple entries including Task tool calls
        entries = [
            # User message with Task tool
            {
                "type": "user",
                "sessionId": session["sessionId"],
                "timestamp": f"2025-07-12T12:0{i}:00.000Z",
                "isSidechain": True,
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {
                                "prompt": session["prompt"]
                            }
                        }
                    ]
                }
            },
            # Assistant response
            {
                "type": "assistant", 
                "sessionId": session["sessionId"],
                "timestamp": f"2025-07-12T12:0{i}:30.000Z",
                "isSidechain": True,
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Session {session['sessionId']}: Working on the task..."
                        }
                    ]
                }
            },
            # Additional messages
            {
                "type": "assistant",
                "sessionId": session["sessionId"], 
                "timestamp": f"2025-07-12T12:0{i}:45.000Z",
                "isSidechain": True,
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Session {session['sessionId']}: Progress update - halfway done!"
                        }
                    ]
                }
            }
        ]
        
        for entry in entries:
            temp_file.write(json.dumps(entry) + '\n')
    
    temp_file.close()
    return temp_file.name

def test_concurrent_formatting(transcript_path: str, session_data: list, results: list, thread_id: int):
    """Test concurrent SubagentStop formatting."""
    print(f"Thread {thread_id}: Starting concurrent test")
    
    for i, session in enumerate(session_data):
        try:
            event_data = {
                "session_id": session["sessionId"], 
                "subagent_id": f"subagent-{thread_id}-{i}",
                "result": f"Thread {thread_id} Session {i} completed",
                "transcript_path": transcript_path
            }
            
            # Format the embed
            embed = format_subagent_stop(event_data, session["sessionId"][:8])
            
            # Check for contamination
            description = embed.get("description", "")
            fields = embed.get("fields", [])
            
            # Look for other sessions' content
            contamination_found = []
            all_content = description + " " + " ".join([f["value"] for f in fields])
            
            for other_session in session_data:
                if other_session != session:
                    # Check if other session's prompt appears in this embed
                    if other_session["sessionId"] in all_content:
                        contamination_found.append(f"SessionID: {other_session['sessionId']}")
                    
                    # Check for prompt mixing
                    other_prompt_keywords = other_session["prompt"][:30]  # First 30 chars
                    if other_prompt_keywords in all_content:
                        contamination_found.append(f"Prompt: {other_prompt_keywords}")
            
            result = {
                "thread_id": thread_id,
                "session": session["sessionId"],
                "iteration": i,
                "embed_title": embed.get("title", ""),
                "description_length": len(description),
                "fields_count": len(fields),
                "contamination": contamination_found,
                "success": True,
                "timestamp": time.time()
            }
            
            if contamination_found:
                print(f"Thread {thread_id}: ❌ CONTAMINATION FOUND in session {session['sessionId']}")
                print(f"   Contaminated with: {contamination_found}")
            else:
                print(f"Thread {thread_id}: ✅ Session {session['sessionId']} clean")
                
            results.append(result)
            
            # Small delay to increase chance of race conditions
            time.sleep(0.01)
            
        except Exception as e:
            results.append({
                "thread_id": thread_id,
                "session": session["sessionId"], 
                "iteration": i,
                "success": False,
                "error": str(e),
                "timestamp": time.time()
            })
            print(f"Thread {thread_id}: ❌ Error in session {session['sessionId']}: {e}")

def main():
    """Run the concurrent prompt mixing test."""
    print("🔍 Concurrent Prompt Mixing Detection Test")
    print("=" * 60)
    
    # Create test transcript with multiple sessions
    transcript_path = create_mixed_transcript()
    print(f"📄 Created test transcript: {transcript_path}")
    
    # Session data
    sessions = [
        {
            "sessionId": "audit-astolfo-session-001",
            "prompt": "監査アストルフォちゃん♡ このシステムの並列実行ログを調査..."
        },
        {
            "sessionId": "code-astolfo-session-002",
            "prompt": "コードアストルフォちゃん♡ 新しいログシステムを実装..."
        },
        {
            "sessionId": "test-astolfo-session-003", 
            "prompt": "テストアストルフォちゃん♡ 全てのユニットテストを実行..."
        }
    ]
    
    print(f"📋 Testing {len(sessions)} concurrent sessions")
    
    # Test 1: Sequential access (control test)
    print("\n🔵 Test 1: Sequential Access (Control)")
    results_sequential = []
    for i, session in enumerate(sessions):
        test_concurrent_formatting(transcript_path, [session], results_sequential, i)
    
    print(f"Sequential test completed: {len(results_sequential)} results")
    
    # Test 2: Concurrent access 
    print("\n🔴 Test 2: Concurrent Access (Race Conditions)")
    results_concurrent = []
    threads = []
    
    # Start multiple threads accessing the same transcript simultaneously
    for i in range(3):
        thread = threading.Thread(
            target=test_concurrent_formatting,
            args=(transcript_path, sessions, results_concurrent, i)
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"Concurrent test completed: {len(results_concurrent)} results")
    
    # Test 3: Rapid alternating access
    print("\n🟡 Test 3: Rapid Alternating Access")
    results_rapid = []
    for round_num in range(5):
        print(f"Round {round_num + 1}:")
        for i, session in enumerate(sessions):
            test_concurrent_formatting(transcript_path, [session], results_rapid, f"rapid-{round_num}")
            time.sleep(0.001)  # Very small delay
    
    print(f"Rapid test completed: {len(results_rapid)} results")
    
    # Analysis
    print("\n📊 Analysis Summary")
    print("=" * 60)
    
    all_results = results_sequential + results_concurrent + results_rapid
    total_tests = len(all_results)
    contaminated_tests = len([r for r in all_results if r.get("contamination")])
    
    print(f"Total tests run: {total_tests}")
    print(f"Tests with contamination: {contaminated_tests}")
    print(f"Contamination rate: {(contaminated_tests/total_tests)*100:.1f}%")
    
    if contaminated_tests > 0:
        print("\n❌ CONTAMINATION DETECTED!")
        print("Detailed contamination report:")
        for r in all_results:
            if r.get("contamination"):
                print(f"  Thread {r['thread_id']}, Session {r['session']}: {r['contamination']}")
    else:
        print("\n✅ No contamination detected in any test")
    
    # Cleanup
    try:
        Path(transcript_path).unlink()
        print(f"\n🧹 Cleaned up test transcript: {transcript_path}")
    except Exception as e:
        print(f"Warning: Could not clean up transcript: {e}")

if __name__ == "__main__":
    main()