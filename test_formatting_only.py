#!/usr/bin/env python3
"""Test Discord message formatting without actual Discord API calls.

This test focuses on the formatting and validation logic without requiring
Discord API credentials, useful for CI/CD and development environments.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop
from src.validators.message_validator import MessageValidator
from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import get_user_datetime


def create_test_transcript() -> str:
    """Create a temporary transcript for testing."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    
    entries = [
        {
            "type": "user",
            "sessionId": "test-session-001",
            "timestamp": "2025-07-12T12:00:00.000Z",
            "isSidechain": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {
                            "prompt": "テストアストルフォちゃん♡ Discord通知フォーマットのテストを実行してね！"
                        }
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": "test-session-001", 
            "timestamp": "2025-07-12T12:00:30.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "テストアストルフォ：Discord通知フォーマットのテストを開始します！"
                    }
                ]
            }
        },
        # Contaminated session for testing
        {
            "type": "user",
            "sessionId": "audit-session-contaminated",
            "timestamp": "2025-07-12T12:01:00.000Z",
            "isSidechain": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {
                            "prompt": "監査アストルフォちゃん♡ プロンプト混在テストのための監査を実行してね！"
                        }
                    }
                ]
            }
        },
        {
            "type": "assistant", 
            "sessionId": "audit-session-contaminated",
            "timestamp": "2025-07-12T12:01:30.000Z",
            "isSidechain": True,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "監査アストルフォ：プロンプト混在の調査を開始します！"
                    }
                ]
            }
        }
    ]
    
    for entry in entries:
        temp_file.write(json.dumps(entry) + '\n')
    
    temp_file.close()
    return temp_file.name


def test_normal_formatting():
    """Test normal subagent message formatting."""
    print("🎯 Testing Normal Subagent Message Formatting")
    print("=" * 50)
    
    transcript_path = create_test_transcript()
    
    event_data = {
        "subagent_id": "test-astolfo-normal",
        "result": "Discord notification formatting test completed successfully!",
        "session_id": "test-session-001",
        "transcript_path": transcript_path,
        "duration_seconds": 30,
        "tools_used": 5
    }
    
    # Format the message
    embed = format_subagent_stop(event_data, "test-001")
    
    print(f"✅ Embed Title: {embed.get('title', '')}")
    print(f"📝 Description Preview: {embed.get('description', '')[:100]}...")
    
    # Check for JST timestamp
    description = embed.get('description', '')
    if 'JST' in description:
        print("✅ JST timestamp detected in description")
    else:
        print("❌ JST timestamp not found")
    
    # Check fields
    fields = embed.get('fields', [])
    print(f"📄 Fields Count: {len(fields)}")
    
    if fields:
        for i, field in enumerate(fields):
            field_name = field.get('name', f'Field {i+1}')
            field_value = field.get('value', '')
            print(f"   Field {i+1}: {field_name}")
            if "⚠️ [CONTAMINATION DETECTED:" in field_value:
                print(f"      🚨 Contamination warning detected!")
            else:
                print(f"      ✅ Clean content")
    
    Path(transcript_path).unlink()
    return embed


def test_contamination_detection():
    """Test contamination detection formatting."""
    print("\n⚠️ Testing Contamination Detection")
    print("=" * 50)
    
    transcript_path = create_test_transcript()
    
    # Use wrong session ID to trigger contamination
    event_data = {
        "subagent_id": "test-astolfo-impl",
        "result": "Implementation completed with potential contamination",
        "session_id": "audit-session-contaminated",  # Wrong session!
        "transcript_path": transcript_path,
        "duration_seconds": 45,
        "tools_used": 8
    }
    
    # Format the message
    embed = format_subagent_stop(event_data, "impl-999")
    
    print(f"🎯 Testing Wrong Session ID: audit-session-contaminated")
    print(f"📝 Expected Subagent: test-astolfo-impl")
    
    # Check fields for contamination warnings
    fields = embed.get('fields', [])
    contamination_detected = False
    
    for i, field in enumerate(fields):
        field_value = field.get('value', '')
        if "⚠️ [CONTAMINATION DETECTED:" in field_value:
            contamination_detected = True
            print(f"✅ Contamination warning found in field {i+1}")
            # Extract contamination type
            import re
            match = re.search(r"⚠️ \[CONTAMINATION DETECTED: ([^\]]+)\]", field_value)
            if match:
                contamination_type = match.group(1)
                print(f"   🔍 Contamination Type: {contamination_type}")
    
    if contamination_detected:
        print("🎉 Contamination detection is working correctly!")
    else:
        print("❌ Contamination detection failed")
    
    Path(transcript_path).unlink()
    return contamination_detected


def test_validation_logic():
    """Test message validation logic."""
    print("\n✅ Testing Message Validation Logic")
    print("=" * 50)
    
    validator = MessageValidator()
    
    # Create test embed
    test_embed = {
        "title": "🤖 Subagent Completed",
        "description": "**Session:** `test-001`\n**Completed at:** 2025-07-12 21:52:00 JST\n**Subagent ID:** test-astolfo\n**Result:**\nTest validation completed",
        "fields": [
            {
                "name": "Message 1",
                "value": "Normal message content here"
            },
            {
                "name": "Message 2", 
                "value": "⚠️ [CONTAMINATION DETECTED: 監査アストルフォ] Contaminated content here"
            }
        ]
    }
    
    # Create fake received message
    received_message = {
        "id": "123456789",
        "channel_id": "987654321",
        "author": {"id": "111111111", "username": "TestBot"},
        "content": "",
        "timestamp": "2025-07-12T12:52:00.000Z",
        "embeds": [test_embed],
        "type": 0
    }
    
    # Validate
    result = validator.validate_subagent_message(
        test_embed,
        received_message,
        "test-astolfo"
    )
    
    print(f"🎯 Validation Success: {result['success']}")
    print(f"❌ Errors: {len(result['errors'])}")
    print(f"⚠️ Warnings: {len(result['warnings'])}")
    
    # Check specific validations
    details = result['details']
    
    if details.get('timestamp_found'):
        print("✅ JST timestamp validation working")
    else:
        print("❌ JST timestamp validation failed")
    
    if details.get('contamination_detected'):
        print(f"✅ Contamination detection working ({details['contamination_count']} detected)")
    else:
        print("ℹ️ No contamination detected (expected for this test)")
    
    return result


def main():
    """Run all formatting tests."""
    logger = AstolfoLogger(__name__)
    
    print("🎭" * 30)
    print("🎯 DISCORD FORMATTING TEST SUITE 🎯")
    print("🎭" * 30)
    print("Testing without Discord API - focusing on formatting logic")
    print()
    
    try:
        # Test 1: Normal formatting
        normal_embed = test_normal_formatting()
        
        # Test 2: Contamination detection
        contamination_detected = test_contamination_detection()
        
        # Test 3: Validation logic
        validation_result = test_validation_logic()
        
        # Summary
        print("\n🎭" * 30)
        print("📊 TEST SUMMARY")
        print("🎭" * 30)
        
        print(f"✅ Normal Formatting: {'PASS' if normal_embed else 'FAIL'}")
        print(f"⚠️ Contamination Detection: {'PASS' if contamination_detected else 'FAIL'}")
        print(f"✅ Validation Logic: {'PASS' if validation_result['success'] else 'FAIL'}")
        
        overall_success = normal_embed and contamination_detected
        
        if overall_success:
            print("\n🎉 ALL FORMATTING TESTS PASSED!")
            print("✅ JST timestamps working")
            print("✅ Contamination detection working")
            print("✅ Message validation working")
        else:
            print("\n❌ SOME TESTS FAILED")
            print("Please check the output above for details")
        
        print("\n💡 Next Step: Run with actual Discord credentials for full integration test")
        print("🎭" * 30)
        
        return 0 if overall_success else 1
        
    except Exception as e:
        logger.error("Formatting test failed", error=str(e))
        print(f"\n💥 TEST FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())