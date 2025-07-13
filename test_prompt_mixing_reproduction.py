#!/usr/bin/env python3
"""Advanced test to reproduce the actual prompt mixing issue.

This test specifically targets the conditions that could cause
the "audit astolfo prompt appearing in all messages" problem.
"""

import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop
from src.utils.transcript_reader import get_subagent_messages
from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)

def create_realistic_transcript(base_session: str, audit_session: str) -> str:
    """Create a realistic transcript with overlapping sessions."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    
    # Realistic Claude Code transcript entries
    entries = [
        # Main session task
        {
            "type": "user",
            "sessionId": base_session,
            "timestamp": "2025-07-12T11:50:00.000Z",
            "isSidechain": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {
                            "prompt": "実装アストルフォちゃん♡ 新しいDiscord通知機能を実装してね！特にスレッド管理機能を重視して設計してください。"
                        }
                    }
                ]
            }
        },
        
        # Audit session task (THIS IS THE PROBLEM PROMPT)
        {
            "type": "user", 
            "sessionId": audit_session,
            "timestamp": "2025-07-12T11:50:10.000Z",
            "isSidechain": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {
                            "prompt": "監査アストルフォちゃん♡ 「監査アストルフォちゃんのプロンプトが全てのTask実行時のDiscordメッセージにダブって表示される」問題を詳しく調査してね！具体的な調査項目：1. 最近の並列実行ログを詳しく分析 2. transcript_reader.pyのget_subagent_messages()関数でセッションIDフィルタリングが正しく動作してるか確認"
                        }
                    }
                ]
            }
        },
        
        # Main session response
        {
            "type": "assistant",
            "sessionId": base_session,
            "timestamp": "2025-07-12T11:50:20.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "実装アストルフォ：Discord通知機能の実装を開始します！"
                    }
                ]
            }
        },
        
        # Audit session response
        {
            "type": "assistant",
            "sessionId": audit_session,
            "timestamp": "2025-07-12T11:50:30.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "監査アストルフォ：プロンプト混在問題の調査を開始します！"
                    }
                ]
            }
        },
        
        # More entries to simulate realistic conditions
        {
            "type": "assistant",
            "sessionId": base_session,
            "timestamp": "2025-07-12T11:51:00.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "実装アストルフォ：スレッド管理機能の設計を完了しました。"
                    }
                ]
            }
        }
    ]
    
    for entry in entries:
        temp_file.write(json.dumps(entry) + '\n')
    
    temp_file.close()
    return temp_file.name

def test_session_id_edge_cases():
    """Test various session ID edge cases that could cause mixing."""
    print("🧪 Testing Session ID Edge Cases")
    print("=" * 50)
    
    transcript_path = create_realistic_transcript("main-session-123", "audit-session-456")
    
    # Test 1: Empty session ID
    print("\n1. Testing empty session ID:")
    try:
        messages_empty = get_subagent_messages(transcript_path, "", limit=10)
        print(f"   Messages with empty session ID: {len(messages_empty)}")
        if messages_empty:
            print("   ❌ CRITICAL: Empty session ID returned messages!")
            for i, msg in enumerate(messages_empty):
                content = msg.get("content", "")[:60]
                print(f"     Message {i+1}: {content}...")
        else:
            print("   ✅ Empty session ID correctly returned no messages")
    except Exception as e:
        print(f"   ⚠️ Exception with empty session ID: {e}")
    
    # Test 2: Non-existent session ID
    print("\n2. Testing non-existent session ID:")
    messages_nonexistent = get_subagent_messages(transcript_path, "non-existent-session", limit=10)
    print(f"   Messages with non-existent session: {len(messages_nonexistent)}")
    
    # Test 3: Partial session ID match
    print("\n3. Testing partial session ID match:")
    messages_partial = get_subagent_messages(transcript_path, "main-session", limit=10)
    print(f"   Messages with partial session ID: {len(messages_partial)}")
    
    # Test 4: Case sensitivity
    print("\n4. Testing case sensitivity:")
    messages_case = get_subagent_messages(transcript_path, "MAIN-SESSION-123", limit=10)
    print(f"   Messages with different case: {len(messages_case)}")
    
    # Cleanup
    Path(transcript_path).unlink()

def test_formatter_with_problematic_data():
    """Test the formatter with conditions that could cause mixing."""
    print("\n🎭 Testing Formatter with Problematic Event Data")
    print("=" * 50)
    
    transcript_path = create_realistic_transcript("impl-session-999", "audit-session-777")
    
    # Test cases that could cause the mixing issue
    test_cases = [
        {
            "name": "Empty session_id in event_data",
            "event_data": {
                "subagent_id": "impl-astolfo",
                "result": "Implementation completed",
                "session_id": "",  # Empty session ID!
                "transcript_path": transcript_path
            },
            "display_session": "impl-999"
        },
        {
            "name": "Missing session_id in event_data", 
            "event_data": {
                "subagent_id": "impl-astolfo",
                "result": "Implementation completed",
                # session_id missing!
                "transcript_path": transcript_path
            },
            "display_session": "impl-999"
        },
        {
            "name": "Wrong session_id in event_data",
            "event_data": {
                "subagent_id": "impl-astolfo", 
                "result": "Implementation completed",
                "session_id": "audit-session-777",  # Wrong session!
                "transcript_path": transcript_path
            },
            "display_session": "impl-999"
        },
        {
            "name": "None session_id in event_data",
            "event_data": {
                "subagent_id": "impl-astolfo",
                "result": "Implementation completed", 
                "session_id": None,  # None session ID!
                "transcript_path": transcript_path
            },
            "display_session": "impl-999"
        }
    ]
    
    contamination_detected = False
    
    for test_case in test_cases:
        print(f"\n📋 Test: {test_case['name']}")
        
        try:
            embed = format_subagent_stop(test_case["event_data"], test_case["display_session"])
            
            # Check for contamination
            description = embed.get("description", "")
            fields = embed.get("fields", [])
            
            # Look for audit astolfo content in implementation astolfo result
            audit_keywords = ["監査アストルフォ", "監査", "プロンプト混在問題", "調査"]
            
            contamination_found = False
            
            if any(keyword in description for keyword in audit_keywords):
                print(f"   ❌ CONTAMINATION in description: Found audit content")
                contamination_found = True
                contamination_detected = True
                
            for field in fields:
                field_value = field.get("value", "")
                if any(keyword in field_value for keyword in audit_keywords):
                    print(f"   ❌ CONTAMINATION in field '{field.get('name', '')}': Found audit content")
                    contamination_found = True
                    contamination_detected = True
            
            if not contamination_found:
                print(f"   ✅ No contamination detected")
                
            # Debug info
            print(f"   📊 Description length: {len(description)}")
            print(f"   📊 Fields count: {len(fields)}")
            
        except Exception as e:
            print(f"   ⚠️ Exception in formatter: {e}")
    
    # Cleanup
    Path(transcript_path).unlink()
    
    return contamination_detected

def test_concurrent_access():
    """Test concurrent access to the same transcript file."""
    print("\n🏃‍♀️🏃‍♂️ Testing Concurrent Access")
    print("=" * 50)
    
    transcript_path = create_realistic_transcript("concurrent-session-1", "concurrent-session-2")
    
    results = {}
    errors = []
    
    def worker(session_id: str, worker_id: int):
        """Worker function for concurrent access test."""
        try:
            for i in range(5):
                messages = get_subagent_messages(transcript_path, session_id, limit=10)
                
                # Check for cross-contamination
                for msg in messages:
                    content = msg.get("content", "")
                    if session_id == "concurrent-session-1" and "concurrent-session-2" in content:
                        errors.append(f"Worker {worker_id}: Session 1 contaminated with session 2 content")
                    elif session_id == "concurrent-session-2" and "concurrent-session-1" in content:
                        errors.append(f"Worker {worker_id}: Session 2 contaminated with session 1 content")
                
                results[f"{session_id}-{worker_id}-{i}"] = len(messages)
                time.sleep(0.001)  # Small delay to increase concurrency chances
                
        except Exception as e:
            errors.append(f"Worker {worker_id} error: {e}")
    
    # Start multiple workers
    threads = []
    for i in range(4):
        session = "concurrent-session-1" if i % 2 == 0 else "concurrent-session-2"
        thread = threading.Thread(target=worker, args=(session, i))
        threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    print(f"   📊 Total operations: {len(results)}")
    print(f"   📊 Errors detected: {len(errors)}")
    
    if errors:
        print("   ❌ CONCURRENT ACCESS ISSUES:")
        for error in errors:
            print(f"     - {error}")
    else:
        print("   ✅ No concurrent access issues detected")
    
    # Cleanup
    Path(transcript_path).unlink()
    
    return len(errors) > 0

def main():
    """Run all reproduction tests."""
    print("🔬 Advanced Prompt Mixing Reproduction Test")
    print("=" * 60)
    print("Targeting the specific issue:")
    print("\"監査アストルフォちゃんのプロンプトが全てのTask実行時のDiscordメッセージにダブって表示される\"")
    print()
    
    # Run all tests
    test_session_id_edge_cases()
    
    contamination_detected = test_formatter_with_problematic_data()
    
    concurrent_issues = test_concurrent_access()
    
    # Final summary
    print("\n📋 FINAL TEST SUMMARY")
    print("=" * 60)
    
    if contamination_detected:
        print("❌ PROMPT MIXING REPRODUCED!")
        print("   The formatter is vulnerable to session ID issues")
        print("   Recommendation: Implement immediate session ID validation")
    else:
        print("✅ No contamination reproduced in formatter tests")
    
    if concurrent_issues:
        print("❌ CONCURRENT ACCESS ISSUES DETECTED!")
        print("   File locking may not be sufficient for all cases")
    else:
        print("✅ Concurrent access appears stable")
    
    # Next steps
    print(f"\n🎯 NEXT STEPS:")
    if contamination_detected or concurrent_issues:
        print("1. Implement session ID validation in get_subagent_messages()")
        print("2. Add contamination detection alerts in format_subagent_stop()")
        print("3. Enhance logging for session ID debugging")
        print("4. Test with actual Claude Code environment")
    else:
        print("1. Test with actual Claude Code transcript files")
        print("2. Monitor production logs for session ID anomalies") 
        print("3. Consider memory-based contamination sources")
        print("4. Review AstolfoLogger state management")

if __name__ == "__main__":
    main()