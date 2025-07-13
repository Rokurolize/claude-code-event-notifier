#!/usr/bin/env python3
"""Deep debug analysis of transcript extraction and potential prompt mixing."""

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.transcript_reader import get_subagent_messages, get_full_task_prompt
from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)

def create_complex_transcript() -> str:
    """Create transcript mimicking real-world scenario with multiple Task tools."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    
    # Complex real-world scenario with multiple sessions and overlapping Task tools
    entries = [
        # Session 1: Audit Astolfo
        {
            "type": "user",
            "sessionId": "audit-session-001",
            "timestamp": "2025-07-12T11:50:00.000Z",
            "isSidechain": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {
                            "prompt": "監査アストルフォちゃん♡ 「監査アストルフォちゃんのプロンプトが全てのTask実行時のDiscordメッセージにダブって表示される」問題を詳しく調査してね！具体的な調査項目：1. 最近の並列実行ログを詳しく分析 2. transcript_reader.pyのget_subagent_messages()関数でセッションIDフィルタリングが正しく動作してるか確認 3. 複数のサブエージェントが同じtranscriptファイルを読む時の競合状態を調査 4. AstolfoLoggerのログで実際にどのプロンプト内容が抽出されているかを詳細追跡"
                        }
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": "audit-session-001", 
            "timestamp": "2025-07-12T11:50:30.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "やっほー！♡ 監査アストルフォだよ、マスター！このプロンプト混在問題を徹底的に調査しちゃうからね！"
                    }
                ]
            }
        },
        
        # Session 2: Code Astolfo (overlapping timeline)
        {
            "type": "user",
            "sessionId": "code-session-002",
            "timestamp": "2025-07-12T11:50:15.000Z",
            "isSidechain": True,
            "message": {
                "role": "user", 
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {
                            "prompt": "コードアストルフォちゃん♡ 新しいAstolfoLogger統合機能をSRC/handlersディレクトリに実装してね！特に並列処理でのスレッドセーフティを重視して、複数のサブエージェントが同時に実行されても競合状態が発生しないように設計してください。"
                        }
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": "code-session-002",
            "timestamp": "2025-07-12T11:50:45.000Z", 
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "えへへ♡ コードアストルフォが登場！スレッドセーフなAstolfoLogger実装に取り掛かるよ〜！"
                    }
                ]
            }
        },
        
        # Session 3: Test Astolfo (same time range)
        {
            "type": "user",
            "sessionId": "test-session-003",
            "timestamp": "2025-07-12T11:50:20.000Z",
            "isSidechain": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task", 
                        "input": {
                            "prompt": "テストアストルフォちゃん♡ 並列実行テストスイートを作成してね！特にtranscript読み込み時の競合状態をテストして、プロンプト混在バグを再現できるかチェックしてください。"
                        }
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": "test-session-003",
            "timestamp": "2025-07-12T11:51:00.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "テストアストルフォ、参上！♡ 並列実行バグの再現テストを作成するよ〜！"
                    }
                ]
            }
        },
        
        # Additional messages for each session
        {
            "type": "assistant",
            "sessionId": "audit-session-001",
            "timestamp": "2025-07-12T11:51:30.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "監査アストルフォ：ログ分析を開始したよ！問題の根本原因を特定中..."
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": "code-session-002",
            "timestamp": "2025-07-12T11:51:45.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "コードアストルフォ：スレッドセーフなロガー実装を進めてるよ♡"
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": "test-session-003",
            "timestamp": "2025-07-12T11:52:00.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "テストアストルフォ：競合状態の再現テストを作成中だよ〜！"
                    }
                ]
            }
        }
    ]
    
    for entry in entries:
        temp_file.write(json.dumps(entry) + '\n')
    
    temp_file.close()
    return temp_file.name

def debug_session_extraction(transcript_path: str, session_id: str, expected_prompt_keyword: str):
    """Debug extraction for a specific session."""
    print(f"\n🔍 Debugging session: {session_id}")
    print(f"Expected keyword: {expected_prompt_keyword}")
    
    # Extract using get_subagent_messages 
    logger.info(f"Extracting messages for session {session_id}")
    messages = get_subagent_messages(transcript_path, session_id, limit=20)
    
    print(f"📊 Found {len(messages)} messages")
    
    # Analyze each message for contamination
    contamination_found = False
    other_keywords = ["監査アストルフォ", "コードアストルフォ", "テストアストルフォ"]
    other_keywords = [k for k in other_keywords if k not in expected_prompt_keyword]
    
    for i, msg in enumerate(messages):
        content = msg.get("content", "")
        if not content:
            continue
            
        print(f"  Message {i+1}: {content[:60]}...")
        
        # Check for expected content
        if expected_prompt_keyword in content:
            print(f"    ✅ Contains expected keyword: {expected_prompt_keyword}")
        
        # Check for contamination from other sessions
        for other_keyword in other_keywords:
            if other_keyword in content:
                print(f"    ❌ CONTAMINATION: Contains {other_keyword}")
                contamination_found = True
                
        # Check for wrong session ID patterns
        wrong_sessions = ["audit-session", "code-session", "test-session"]
        current_session_type = session_id.split("-")[0]
        for wrong_session in wrong_sessions:
            if wrong_session.startswith(current_session_type):
                continue
            if wrong_session in content:
                print(f"    ❌ CONTAMINATION: Contains {wrong_session} reference")
                contamination_found = True
    
    # Also test get_full_task_prompt
    print(f"\n🎯 Testing get_full_task_prompt for {session_id}")
    full_prompt = get_full_task_prompt(transcript_path, session_id)
    if full_prompt:
        print(f"Full prompt extracted: {full_prompt[:100]}...")
        if expected_prompt_keyword in full_prompt:
            print("    ✅ Full prompt contains expected keyword")
        else:
            print("    ❌ Full prompt missing expected keyword")
            
        # Check for contamination in full prompt
        for other_keyword in other_keywords:
            if other_keyword in full_prompt:
                print(f"    ❌ FULL PROMPT CONTAMINATION: Contains {other_keyword}")
                contamination_found = True
    else:
        print("    ⚠️ No full prompt extracted")
    
    return contamination_found

def main():
    """Run deep debug analysis."""
    print("🔬 Deep Debug Analysis: Transcript Extraction")
    print("=" * 60)
    
    # Create complex transcript
    transcript_path = create_complex_transcript()
    print(f"📄 Created complex transcript: {transcript_path}")
    
    # Test each session
    sessions_to_test = [
        ("audit-session-001", "監査アストルフォ"),
        ("code-session-002", "コードアストルフォ"), 
        ("test-session-003", "テストアストルフォ")
    ]
    
    contamination_results = []
    
    for session_id, expected_keyword in sessions_to_test:
        contaminated = debug_session_extraction(transcript_path, session_id, expected_keyword)
        contamination_results.append((session_id, contaminated))
    
    # Test rapid sequential calls (race condition simulation)
    print(f"\n⚡ Testing rapid sequential calls for race conditions")
    for round_num in range(3):
        print(f"\nRound {round_num + 1}:")
        for session_id, expected_keyword in sessions_to_test:
            start_time = time.time()
            messages = get_subagent_messages(transcript_path, session_id, limit=10)
            duration = time.time() - start_time
            print(f"  {session_id}: {len(messages)} messages in {duration*1000:.1f}ms")
            
            # Quick contamination check
            all_content = " ".join([msg.get("content", "") for msg in messages])
            other_astolfos = [k for k in ["監査", "コード", "テスト"] if k not in expected_keyword]
            for other in other_astolfos:
                if other in all_content:
                    print(f"    ❌ RACE CONDITION CONTAMINATION: Found {other}")
                    
            time.sleep(0.001)  # Small delay
    
    # Summary
    print(f"\n📋 Final Analysis Summary")
    print("=" * 60)
    
    total_contaminated = sum(1 for _, contaminated in contamination_results if contaminated)
    print(f"Sessions tested: {len(contamination_results)}")
    print(f"Sessions with contamination: {total_contaminated}")
    
    if total_contaminated > 0:
        print(f"\n❌ CONTAMINATION DETECTED!")
        print("Root cause analysis needed:")
        print("1. Check get_subagent_messages session filtering logic")
        print("2. Verify read_transcript_lines file handling")
        print("3. Investigate potential shared state in transcript reading")
        print("4. Review concurrent access patterns")
        
        for session_id, contaminated in contamination_results:
            if contaminated:
                print(f"  - {session_id}: CONTAMINATED")
    else:
        print(f"\n✅ No contamination detected in controlled test")
        print("Possible causes of real-world issues:")
        print("1. Timing-dependent race conditions")
        print("2. Complex transcript file structures not simulated")
        print("3. File system caching or sharing issues")
        print("4. Claude Code specific transcript format variations")
    
    # Cleanup
    try:
        Path(transcript_path).unlink()
        print(f"\n🧹 Cleaned up test transcript")
    except Exception as e:
        print(f"Warning: Could not clean up: {e}")

if __name__ == "__main__":
    main()