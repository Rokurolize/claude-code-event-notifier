#!/usr/bin/env python3
"""Test SubagentStop with mixed tool usage patterns."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop
from src.utils.transcript_reader import get_subagent_messages, get_full_task_prompt
from src.utils.astolfo_logger import AstolfoLogger

class MixedToolTest:
    """Test subagent events with various tool combinations."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        
    def create_complex_transcript(self, session_id: str, tool_mix: str) -> str:
        """Create transcript with different tool usage patterns."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        
        base_messages = [
            {
                "timestamp": "2025-07-12T11:45:00.000Z",
                "type": "user",
                "session_id": session_id,
                "role": "user",
                "content": [{"type": "text", "text": f"Execute complex task with {tool_mix} tools"}]
            }
        ]
        
        # Add tool-specific messages based on mix type
        if "task" in tool_mix.lower():
            base_messages.extend([
                {
                    "timestamp": "2025-07-12T11:45:10.000Z",
                    "type": "tool_use",
                    "session_id": session_id,
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {
                                "description": "Implement advanced feature with Task tool",
                                "prompt": "Create a comprehensive solution that handles edge cases and provides robust error handling. The implementation should be modular and follow best practices for maintainability."
                            }
                        }
                    ]
                },
                {
                    "timestamp": "2025-07-12T11:45:15.000Z",
                    "type": "tool_result",
                    "session_id": session_id,
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "task_456",
                            "content": "Task completed with advanced implementation"
                        }
                    ]
                }
            ])
            
        if "webfetch" in tool_mix.lower():
            base_messages.extend([
                {
                    "timestamp": "2025-07-12T11:45:20.000Z",
                    "type": "tool_use",
                    "session_id": session_id,
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "WebFetch",
                            "input": {
                                "url": "https://api.example.com/data",
                                "prompt": "Extract configuration data for integration"
                            }
                        }
                    ]
                },
                {
                    "timestamp": "2025-07-12T11:45:25.000Z",
                    "type": "tool_result",
                    "session_id": session_id,
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "webfetch_789",
                            "content": "Configuration data retrieved successfully"
                        }
                    ]
                }
            ])
            
        if "bash" in tool_mix.lower():
            base_messages.extend([
                {
                    "timestamp": "2025-07-12T11:45:30.000Z",
                    "type": "tool_use",
                    "session_id": session_id,
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {
                                "command": "python -m pytest tests/ -v",
                                "description": "Run comprehensive test suite"
                            }
                        }
                    ]
                },
                {
                    "timestamp": "2025-07-12T11:45:35.000Z",
                    "type": "tool_result",
                    "session_id": session_id,
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "bash_101",
                            "content": "All tests passed successfully"
                        }
                    ]
                }
            ])
            
        if "edit" in tool_mix.lower():
            base_messages.extend([
                {
                    "timestamp": "2025-07-12T11:45:40.000Z",
                    "type": "tool_use",
                    "session_id": session_id,
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {
                                "file_path": "/project/src/main.py",
                                "old_string": "def old_function():",
                                "new_string": "def new_improved_function():"
                            }
                        }
                    ]
                },
                {
                    "timestamp": "2025-07-12T11:45:45.000Z",
                    "type": "tool_result",
                    "session_id": session_id,
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "edit_202",
                            "content": "File edited successfully"
                        }
                    ]
                }
            ])
            
        # Add final assistant response
        base_messages.append({
            "timestamp": "2025-07-12T11:45:50.000Z",
            "type": "assistant",
            "session_id": session_id,
            "role": "assistant",
            "content": [{"type": "text", "text": f"Completed complex workflow using {tool_mix} tools successfully."}]
        })
        
        # Write all messages
        for msg in base_messages:
            json.dump(msg, temp_file)
            temp_file.write('\n')
            
        temp_file.close()
        return temp_file.name
        
    def test_tool_combinations(self) -> None:
        """Test various tool combinations in subagent workflows."""
        print("🔧 Testing Mixed Tool Patterns")
        print("=" * 50)
        
        tool_combinations = [
            ("Task-Only", "task"),
            ("Task+WebFetch", "task+webfetch"),
            ("Task+Bash", "task+bash"),
            ("Task+Edit", "task+edit"),
            ("All-Tools", "task+webfetch+bash+edit"),
            ("WebFetch+Bash", "webfetch+bash"),
        ]
        
        results = {}
        
        for combo_name, tool_mix in tool_combinations:
            print(f"\n📋 Testing: {combo_name}")
            print(f"   Tools: {tool_mix}")
            
            session_id = f"mixed-session-{hash(combo_name) % 10000:04d}"
            subagent_id = f"subagent-{combo_name.lower().replace('-', '_')}"
            
            try:
                # Create transcript with tool mix
                transcript_path = self.create_complex_transcript(session_id, tool_mix)
                
                # Create subagent event data
                event_data = {
                    "session_id": session_id,
                    "subagent_id": subagent_id,
                    "result": f"Successfully completed workflow using {combo_name} pattern",
                    "duration_seconds": len(tool_mix.split("+")) * 15,  # More tools = longer time
                    "tools_used": len(tool_mix.split("+")),
                    "transcript_path": transcript_path
                }
                
                # Format the event
                embed = format_subagent_stop(event_data, session_id[:8])
                
                # Get subagent messages
                messages = get_subagent_messages(transcript_path, session_id, limit=20)
                
                # Test Task prompt extraction if Task tool is used
                task_prompt = None
                if "task" in tool_mix:
                    task_prompt = get_full_task_prompt(transcript_path, session_id)
                
                results[combo_name] = {
                    "success": True,
                    "embed": embed,
                    "messages": messages,
                    "task_prompt": task_prompt,
                    "tools_used": len(tool_mix.split("+")),
                    "session_id": session_id,
                    "subagent_id": subagent_id
                }
                
                print(f"   ✅ Success")
                print(f"   📄 Messages found: {len(messages)}")
                print(f"   📋 Task prompt: {'Found' if task_prompt else 'None'}")
                print(f"   📝 Description length: {len(embed.get('description', ''))}")
                
                # Check for fields in embed
                fields = embed.get('fields', [])
                if fields:
                    print(f"   🔧 Embed fields: {len(fields)}")
                    for i, field in enumerate(fields[:2]):  # Show first 2
                        field_name = field.get('name', '')
                        print(f"      {i+1}. {field_name}")
                
            except Exception as e:
                results[combo_name] = {
                    "success": False,
                    "error": str(e),
                    "session_id": session_id,
                    "subagent_id": subagent_id
                }
                print(f"   ❌ Failed: {e}")
                
        self.analyze_mixed_tool_results(results)
        
    def analyze_mixed_tool_results(self, results: Dict[str, dict]) -> None:
        """Analyze results from mixed tool testing."""
        print(f"\n\n📊 Mixed Tool Analysis")
        print("=" * 30)
        
        successful = sum(1 for r in results.values() if r["success"])
        total = len(results)
        
        print(f"Success rate: {successful}/{total} ({successful/total*100:.1f}%)")
        
        if successful < total:
            print("\n❌ Failures:")
            for name, result in results.items():
                if not result["success"]:
                    print(f"   {name}: {result['error']}")
        
        # Analyze successful cases
        print("\n✅ Successful Cases:")
        for name, result in results.items():
            if result["success"]:
                embed = result["embed"]
                desc = embed.get("description", "")
                
                print(f"\n   {name}:")
                print(f"     Subagent ID present: {'✅' if result['subagent_id'] in desc else '❌'}")
                print(f"     Session ID present: {'✅' if result['session_id'][:8] in desc else '❌'}")
                print(f"     Messages extracted: {len(result['messages'])}")
                
                if result['task_prompt']:
                    print(f"     Task prompt extracted: ✅ ({len(result['task_prompt'])} chars)")
                else:
                    print(f"     Task prompt extracted: ⏸️  (not applicable or not found)")
                    
                # Check for tool-specific content
                tools_mentioned = []
                for tool in ['Task', 'WebFetch', 'Bash', 'Edit']:
                    if tool.lower() in desc.lower():
                        tools_mentioned.append(tool)
                        
                if tools_mentioned:
                    print(f"     Tools mentioned: {', '.join(tools_mentioned)}")
                    
        # Cross-contamination check
        print("\n🔒 Cross-contamination Check:")
        contamination = False
        
        for name1, result1 in results.items():
            if not result1["success"]:
                continue
                
            desc1 = result1["embed"].get("description", "")
            
            for name2, result2 in results.items():
                if name1 == name2 or not result2["success"]:
                    continue
                    
                # Check if result1's data appears in result2
                if result1["subagent_id"] in result2["embed"].get("description", ""):
                    print(f"   ❌ {name1} data found in {name2}")
                    contamination = True
                    
        if not contamination:
            print("   ✅ All test cases properly isolated")
            
        # Performance analysis
        print("\n⚡ Performance Patterns:")
        by_tool_count = {}
        for name, result in results.items():
            if result["success"]:
                tool_count = result["tools_used"]
                if tool_count not in by_tool_count:
                    by_tool_count[tool_count] = []
                by_tool_count[tool_count].append({
                    "name": name,
                    "desc_length": len(result["embed"].get("description", "")),
                    "message_count": len(result["messages"])
                })
                
        for tool_count in sorted(by_tool_count.keys()):
            cases = by_tool_count[tool_count]
            avg_desc = sum(c["desc_length"] for c in cases) / len(cases)
            avg_msgs = sum(c["message_count"] for c in cases) / len(cases)
            print(f"   {tool_count} tools: {avg_desc:.0f} chars desc, {avg_msgs:.1f} messages avg")

def main():
    """Run mixed tool pattern tests."""
    print("🔧 Mixed Tool Pattern Test Suite")
    print("================================")
    
    tester = MixedToolTest()
    tester.test_tool_combinations()
    
    print("\n🏁 Mixed tool tests completed!")

if __name__ == "__main__":
    main()