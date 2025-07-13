#!/usr/bin/env python3
"""Test to see how contamination warnings appear in Discord messages."""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop

def create_contaminated_transcript() -> str:
    """Create transcript with contamination scenario."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    
    entries = [
        # Audit session task (the contaminating prompt)
        {
            "type": "user",
            "sessionId": "audit-session-999",
            "timestamp": "2025-07-12T11:50:00.000Z", 
            "isSidechain": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {
                            "prompt": "監査アストルフォちゃん♡ 「監査アストルフォちゃんのプロンプトが全てのTask実行時のDiscordメッセージにダブって表示される」問題を詳しく調査してね！具体的な調査項目：1. 最近の並列実行ログを詳しく分析 2. transcript_reader.pyのget_subagent_messages()関数でセッションIDフィルタリングが正しく動作してるか確認 3. 複数のサブエージェントが同じtranscriptファイルを読む時の競合状態を調査"
                        }
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": "audit-session-999",
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
        {
            "type": "assistant",
            "sessionId": "audit-session-999",
            "timestamp": "2025-07-12T11:51:00.000Z",
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
        }
    ]
    
    for entry in entries:
        temp_file.write(json.dumps(entry) + '\n')
    
    temp_file.close()
    return temp_file.name

def test_contamination_display():
    """Test how contamination warnings appear in Discord embeds."""
    print("🎭 Testing Contamination Display in Discord Messages")
    print("=" * 60)
    
    transcript_path = create_contaminated_transcript()
    
    # Test case: Implementation Astolfo with wrong session ID
    event_data = {
        "subagent_id": "implementation-astolfo", 
        "result": "Discord notification feature implementation completed successfully!",
        "session_id": "audit-session-999",  # Wrong session ID!
        "transcript_path": transcript_path,
        "duration_seconds": 45,
        "tools_used": 8
    }
    
    print("📋 Event Data:")
    print(f"   Subagent ID: {event_data['subagent_id']}")
    print(f"   Session ID: {event_data['session_id']} (WRONG!)")
    print(f"   Expected: Should be implementation-session-xxx")
    print(f"   Result: {event_data['result']}")
    print()
    
    # Format the embed
    embed = format_subagent_stop(event_data, "impl-123")
    
    print("📬 Generated Discord Embed:")
    print("=" * 40)
    print(f"**Title:** {embed.get('title', '')}")
    print()
    print(f"**Description:**")
    description = embed.get('description', '')
    for line in description.split('\n'):
        print(f"  {line}")
    print()
    
    # Show fields
    fields = embed.get('fields', [])
    if fields:
        print(f"**Fields:** ({len(fields)} total)")
        for i, field in enumerate(fields):
            field_name = field.get('name', f'Field {i+1}')
            field_value = field.get('value', '')
            print(f"  📄 **{field_name}:**")
            
            # Show if contamination was detected
            if "⚠️ [CONTAMINATION DETECTED:" in field_value:
                print(f"     🚨 CONTAMINATION WARNING VISIBLE!")
                
            # Show preview of content
            lines = field_value.split('\n')
            for line in lines[:3]:  # Show first 3 lines
                print(f"     {line}")
            if len(lines) > 3:
                print(f"     ... ({len(lines)-3} more lines)")
            print()
    else:
        print("**Fields:** None")
    
    print("📊 Analysis:")
    print("=" * 40)
    
    contamination_visible = any("⚠️ [CONTAMINATION DETECTED:" in field.get('value', '') for field in fields)
    audit_content_present = any("監査アストルフォ" in field.get('value', '') for field in fields)
    
    if contamination_visible:
        print("✅ Contamination warnings are VISIBLE in Discord message")
        print("✅ Users will see the warning labels")
    else:
        print("❌ Contamination warnings are NOT visible")
    
    if audit_content_present:
        print("⚠️ Audit Astolfo content is still present in the message")
        print("   (But now it's clearly marked as contamination)")
    else:
        print("✅ No audit content detected")
    
    print()
    print("🎯 User Experience:")
    print("=" * 40)
    print("Before fix: Users would see audit astolfo prompts in implementation")
    print("             messages with no indication that something was wrong.")
    print()
    print("After fix:  Users still see the mixed content, BUT:")
    print("           - Clear warning labels identify the contamination")
    print("           - Detailed error logs are generated for debugging")
    print("           - Empty session IDs are handled gracefully")
    print("           - Developers can track down the root cause")
    
    # Cleanup
    Path(transcript_path).unlink()

if __name__ == "__main__":
    test_contamination_display()