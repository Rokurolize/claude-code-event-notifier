#!/usr/bin/env python3
"""Test script to check for potential shared state in AstolfoLogger."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.formatters.event_formatters import format_subagent_stop

def test_logger_state():
    """Test for potential shared state in AstolfoLogger."""
    print("Testing AstolfoLogger for potential shared state issues...")
    
    print("\n=== Test 1: Logger instance creation ===")
    
    # Create multiple logger instances
    logger_1 = AstolfoLogger("test_module_1")
    logger_2 = AstolfoLogger("test_module_2")
    logger_3 = AstolfoLogger("test_module_1")  # Same name as logger_1
    
    print(f"Logger 1 name: {logger_1.logger.name}")
    print(f"Logger 2 name: {logger_2.logger.name}")
    print(f"Logger 3 name: {logger_3.logger.name}")
    
    # Check if instances are the same
    print(f"Logger 1 is Logger 3 (same name): {logger_1 is logger_3}")
    print(f"Logger 1 is Logger 2 (different name): {logger_1 is logger_2}")
    
    print("\n=== Test 2: Session ID setting ===")
    
    # Set different session IDs
    logger_1.set_session_id("session-alpha")
    logger_2.set_session_id("session-beta")
    logger_3.set_session_id("session-gamma")
    
    print(f"Logger 1 session ID: {getattr(logger_1, 'session_id', 'None')}")
    print(f"Logger 2 session ID: {getattr(logger_2, 'session_id', 'None')}")
    print(f"Logger 3 session ID: {getattr(logger_3, 'session_id', 'None')}")
    
    # Check if session IDs leaked between instances
    if hasattr(logger_1, 'session_id') and hasattr(logger_3, 'session_id'):
        if logger_1.session_id == logger_3.session_id and logger_1 is not logger_3:
            print("❌ POTENTIAL ISSUE: Session IDs are shared between different instances")
        else:
            print("✅ Session IDs are properly isolated")
    
    print("\n=== Test 3: Logger state in formatters ===")
    
    # Test event data with different session IDs
    event_data_1 = {
        "session_id": "formatter-session-1",
        "subagent_id": "subagent-1",
        "result": "Result for session 1"
    }
    
    event_data_2 = {
        "session_id": "formatter-session-2", 
        "subagent_id": "subagent-2",
        "result": "Result for session 2"
    }
    
    # Format events (this will create internal loggers)
    embed_1 = format_subagent_stop(event_data_1, "session1")
    embed_2 = format_subagent_stop(event_data_2, "session2")
    
    print("✅ Formatter calls completed without errors")
    
    print("\n=== Test 4: Logger memory/state persistence ===")
    
    # Check if loggers have any persistent memory
    logger_test = AstolfoLogger("test_memory")
    
    # Add some data
    logger_test.info("Test message 1", {"data": "alpha"})
    
    # Create another logger with same name
    logger_test_2 = AstolfoLogger("test_memory")
    logger_test_2.info("Test message 2", {"data": "beta"})
    
    # Check if they share memory
    if hasattr(logger_test, '_memory') and hasattr(logger_test_2, '_memory'):
        if logger_test._memory is logger_test_2._memory:
            print("❌ POTENTIAL ISSUE: Loggers share memory storage")
        else:
            print("✅ Logger memory is properly isolated")
    else:
        print("✅ No shared memory attributes found")
    
    print("\n=== Test 5: Module-level logger state ===")
    
    # Import modules that use loggers to check for module-level state
    from src.formatters import event_formatters
    from src.utils import transcript_reader
    
    # Check if module-level loggers exist
    module_loggers = []
    for module in [event_formatters, transcript_reader]:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, AstolfoLogger):
                module_loggers.append((module.__name__, attr_name, attr))
    
    print(f"Found {len(module_loggers)} module-level loggers")
    for module_name, attr_name, logger in module_loggers:
        print(f"  {module_name}.{attr_name}: {logger.logger.name}")
    
    # Check if any have session IDs set
    contaminated_loggers = []
    for module_name, attr_name, logger in module_loggers:
        if hasattr(logger, 'session_id') and logger.session_id:
            contaminated_loggers.append((module_name, attr_name, logger.session_id))
    
    if contaminated_loggers:
        print("❌ POTENTIAL ISSUE: Module-level loggers have session IDs set:")
        for module_name, attr_name, session_id in contaminated_loggers:
            print(f"  {module_name}.{attr_name}: {session_id}")
    else:
        print("✅ No module-level loggers with session IDs found")

if __name__ == "__main__":
    test_logger_state()