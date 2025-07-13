#!/usr/bin/env python3
"""Test module imports for validators.

Following Kent Beck's TDD approach:
1. Write failing tests (Red)
2. Make them pass with minimal code (Green)
3. Refactor while keeping tests green
"""

import sys
import unittest
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)


class TestValidatorImports(unittest.TestCase):
    """Test that validators can be imported correctly."""
    
    def test_config_validator_importable(self):
        """ConfigValidatorをvalidators.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing ConfigValidator import", {"test_method": "test_config_validator_importable"})
        
        try:
            from src.validators import ConfigValidator
            # クラスが存在することを確認
            self.assertTrue(hasattr(ConfigValidator, 'validate_credentials'))
            self.assertTrue(hasattr(ConfigValidator, 'validate_thread_config'))
            self.assertTrue(hasattr(ConfigValidator, 'validate_mention_config'))
            self.assertTrue(hasattr(ConfigValidator, 'validate_all'))
            
            logger.info("ConfigValidator import test passed", {
                "duration": time.time() - start_time,
                "methods_validated": ["validate_credentials", "validate_thread_config", "validate_mention_config", "validate_all"]
            })
        except ImportError as e:
            logger.error("ConfigValidator import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import ConfigValidator: {e}")
    
    def test_event_data_validator_importable(self):
        """EventDataValidatorをvalidators.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing EventDataValidator import", {"test_method": "test_event_data_validator_importable"})
        
        try:
            from src.validators import EventDataValidator
            # クラスが存在することを確認
            self.assertTrue(hasattr(EventDataValidator, 'validate_base_event_data'))
            self.assertTrue(hasattr(EventDataValidator, 'validate_tool_event_data'))
            self.assertTrue(hasattr(EventDataValidator, 'validate_notification_event_data'))
            self.assertTrue(hasattr(EventDataValidator, 'validate_stop_event_data'))
            
            logger.info("EventDataValidator import test passed", {
                "duration": time.time() - start_time,
                "methods_validated": ["validate_base_event_data", "validate_tool_event_data", "validate_notification_event_data", "validate_stop_event_data"]
            })
        except ImportError as e:
            logger.error("EventDataValidator import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import EventDataValidator: {e}")
    
    def test_tool_input_validator_importable(self):
        """ToolInputValidatorをvalidators.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing ToolInputValidator import", {"test_method": "test_tool_input_validator_importable"})
        
        try:
            from src.validators import ToolInputValidator
            # クラスが存在することを確認
            self.assertTrue(hasattr(ToolInputValidator, 'validate_bash_input'))
            self.assertTrue(hasattr(ToolInputValidator, 'validate_file_input'))
            self.assertTrue(hasattr(ToolInputValidator, 'validate_search_input'))
            self.assertTrue(hasattr(ToolInputValidator, 'validate_web_input'))
            
            logger.info("ToolInputValidator import test passed", {
                "duration": time.time() - start_time,
                "methods_validated": ["validate_bash_input", "validate_file_input", "validate_search_input", "validate_web_input"]
            })
        except ImportError as e:
            logger.error("ToolInputValidator import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import ToolInputValidator: {e}")
    
    def test_type_guards_importable(self):
        """TypeGuard関数をvalidators.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing type guards import", {"test_method": "test_type_guards_importable"})
        
        try:
            from src.validators import (
                is_tool_event_data, is_notification_event_data,
                is_stop_event_data, is_bash_tool_input,
                is_file_tool_input, is_search_tool_input,
                is_valid_event_type, is_bash_tool,
                is_file_tool, is_search_tool, is_list_tool
            )
            # 関数が存在することを確認
            self.assertTrue(callable(is_tool_event_data))
            self.assertTrue(callable(is_valid_event_type))
            
            logger.info("Type guards import test passed", {
                "duration": time.time() - start_time,
                "guards_tested": ["is_tool_event_data", "is_valid_event_type", "is_bash_tool_input", "is_file_tool_input"]
            })
        except ImportError as e:
            logger.error("Type guards import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import type guards: {e}")
    
    def test_validate_thread_exists_importable(self):
        """validate_thread_exists関数をvalidators.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing validate_thread_exists import", {"test_method": "test_validate_thread_exists_importable"})
        
        try:
            from src.validators import validate_thread_exists
            # 関数が存在することを確認
            self.assertTrue(callable(validate_thread_exists))
            
            logger.info("validate_thread_exists import test passed", {
                "duration": time.time() - start_time,
                "function_validated": "validate_thread_exists"
            })
        except ImportError as e:
            logger.error("validate_thread_exists import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import validate_thread_exists: {e}")


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting validators integration test suite", {"test_file": __file__})
    
    try:
        print("=== Validators Integration Tests ===")
        unittest.main()
        logger.info("Validators test suite completed successfully", {
            "duration": time.time() - start_time
        })
    except Exception as e:
        logger.error("Validators test suite failed", {
            "error": str(e),
            "duration": time.time() - start_time
        })
        raise