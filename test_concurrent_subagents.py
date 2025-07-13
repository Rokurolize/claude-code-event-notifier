#!/usr/bin/env python3
"""Test concurrent SubagentStop processing with real transcript data."""

import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.formatters.event_formatters import format_subagent_stop
from src.utils.transcript_reader import get_subagent_messages
from src.utils.astolfo_logger import AstolfoLogger

class ConcurrentSubagentTest:
    """Test concurrent subagent processing."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.results: Dict[str, dict] = {}
        self.lock = threading.Lock()
        
    def create_realistic_transcript(self, session_id: str, subagent_id: str) -> str:
        """Create a realistic transcript file with subagent messages."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        
        # Realistic subagent messages
        messages = [
            {
                "timestamp": "2025-07-12T11:45:00.000Z",
                "type": "user",
                "session_id": session_id,
                "role": "user",
                "content": [{"type": "text", "text": f"Starting {subagent_id} - implement logging feature"}]
            },
            {
                "timestamp": "2025-07-12T11:45:05.000Z", 
                "type": "assistant",
                "session_id": session_id,
                "role": "assistant",
                "content": [{"type": "text", "text": f"I'll implement the logging feature for {subagent_id}. Let me start by analyzing the requirements."}]
            },
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
                            "description": f"Implement AstolfoLogger integration for {subagent_id}",
                            "prompt": f"Create structured logging system with JSON output for {subagent_id} component"
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
                        "tool_use_id": "task_123",
                        "content": "Task completed successfully"
                    }
                ]
            }
        ]
        
        for msg in messages:
            json.dump(msg, temp_file)
            temp_file.write('\n')
            
        temp_file.close()
        return temp_file.name
        
    def process_subagent(self, subagent_data: dict) -> None:
        """Process a single subagent event."""
        subagent_id = subagent_data["subagent_id"]
        session_id = subagent_data["session_id"]
        
        try:
            self.logger.info(f"Processing {subagent_id}", subagent_id=subagent_id)
            
            # Create realistic transcript
            transcript_path = self.create_realistic_transcript(session_id, subagent_id)
            subagent_data["transcript_path"] = transcript_path
            
            # Small delay to simulate processing time
            time.sleep(0.1)
            
            # Format the event
            embed = format_subagent_stop(subagent_data, session_id[:8])
            
            # Get subagent messages
            messages = get_subagent_messages(transcript_path, session_id, limit=10)
            
            # Store results safely
            with self.lock:
                self.results[subagent_id] = {
                    "success": True,
                    "embed": embed,
                    "messages": messages,
                    "session_id": session_id,
                    "timestamp": time.time()
                }
                
            self.logger.info(f"Completed {subagent_id}", 
                           subagent_id=subagent_id,
                           messages_found=len(messages))
                           
        except Exception as e:
            with self.lock:
                self.results[subagent_id] = {
                    "success": False,
                    "error": str(e),
                    "session_id": session_id,
                    "timestamp": time.time()
                }
            self.logger.error(f"Failed {subagent_id}", 
                            subagent_id=subagent_id,
                            error=str(e))
    
    def run_concurrent_test(self, num_subagents: int = 5) -> None:
        """Run concurrent subagent processing test."""
        print(f"🚀 Testing {num_subagents} concurrent subagents")
        print("=" * 50)
        
        # Create test data
        subagent_events = []
        for i in range(num_subagents):
            subagent_events.append({
                "session_id": f"session-{1000 + i:04d}",
                "subagent_id": f"subagent-{chr(65 + i)}-{i:03d}",
                "result": f"Completed task #{i+1}: implemented feature {chr(65 + i)}",
                "duration_seconds": 20 + (i * 5),
                "tools_used": 3 + i,
            })
            
        # Create threads
        threads = []
        start_time = time.time()
        
        for event in subagent_events:
            thread = threading.Thread(
                target=self.process_subagent,
                args=(event,),
                name=f"SubagentThread-{event['subagent_id']}"
            )
            threads.append(thread)
            
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        end_time = time.time()
        
        # Analyze results
        self.analyze_concurrent_results(end_time - start_time)
        
    def analyze_concurrent_results(self, duration: float) -> None:
        """Analyze the results of concurrent processing."""
        print(f"\n📊 Analysis (completed in {duration:.2f}s)")
        print("-" * 30)
        
        successful = sum(1 for r in self.results.values() if r["success"])
        failed = len(self.results) - successful
        
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        
        if failed > 0:
            print("\n🔍 Failures:")
            for subagent_id, result in self.results.items():
                if not result["success"]:
                    print(f"   {subagent_id}: {result['error']}")
        
        # Check for data isolation
        print("\n🔒 Data Isolation Check:")
        contamination_found = False
        
        for subagent_id, result in self.results.items():
            if not result["success"]:
                continue
                
            embed = result["embed"]
            description = embed.get("description", "")
            
            # Check if this subagent's data appears in others
            for other_id, other_result in self.results.items():
                if subagent_id == other_id or not other_result["success"]:
                    continue
                    
                other_desc = other_result["embed"].get("description", "")
                
                if subagent_id in other_desc:
                    print(f"   ❌ {subagent_id} found in {other_id}")
                    contamination_found = True
                    
        if not contamination_found:
            print("   ✅ All subagents properly isolated")
            
        # Performance metrics
        print("\n⚡ Performance Metrics:")
        timestamps = [r["timestamp"] for r in self.results.values()]
        if timestamps:
            time_spread = max(timestamps) - min(timestamps)
            print(f"   Processing spread: {time_spread:.2f}s")
            print(f"   Throughput: {len(self.results)/duration:.1f} subagents/sec")
            
        # Content verification
        print("\n📋 Content Verification:")
        for subagent_id, result in self.results.items():
            if result["success"]:
                embed = result["embed"]
                title = embed.get("title", "")
                description = embed.get("description", "")
                
                print(f"   {subagent_id}:")
                print(f"     Title: {title}")
                print(f"     Has correct ID: {'✅' if subagent_id in description else '❌'}")
                print(f"     Description length: {len(description)} chars")
                print(f"     Messages found: {len(result.get('messages', []))}")

def main():
    """Run concurrent subagent tests."""
    print("🤖 Concurrent SubagentStop Test Suite")
    print("====================================")
    
    tester = ConcurrentSubagentTest()
    
    # Test with different numbers of concurrent subagents
    for num_subagents in [3, 5, 8]:
        print(f"\n🧪 Test Round: {num_subagents} subagents")
        tester.results.clear()  # Reset for each test
        tester.run_concurrent_test(num_subagents)
        time.sleep(1)  # Brief pause between rounds

if __name__ == "__main__":
    main()