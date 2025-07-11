#!/usr/bin/env python3
"""Test module imports for validators.

Following Kent Beck's TDD approach:
1. Write failing tests (Red)
2. Make them pass with minimal code (Green)
3. Refactor while keeping tests green
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestValidatorImports(unittest.TestCase):
    """Test that validators can be imported correctly."""
    
    def test_config_validator_importable(self):
        """ConfigValidatorをvalidators.pyからインポートできることを確認"""
        try:
            from src.validators import ConfigValidator
            # クラスが存在することを確認
            self.assertTrue(hasattr(ConfigValidator, 'validate_credentials'))
            self.assertTrue(hasattr(ConfigValidator, 'validate_thread_config'))
            self.assertTrue(hasattr(ConfigValidator, 'validate_mention_config'))
            self.assertTrue(hasattr(ConfigValidator, 'validate_all'))
        except ImportError as e:
            self.fail(f"Failed to import ConfigValidator: {e}")
    
    def test_event_data_validator_importable(self):
        """EventDataValidatorをvalidators.pyからインポートできることを確認"""
        try:
            from src.validators import EventDataValidator
            # クラスが存在することを確認
            self.assertTrue(hasattr(EventDataValidator, 'validate_base_event_data'))
            self.assertTrue(hasattr(EventDataValidator, 'validate_tool_event_data'))
            self.assertTrue(hasattr(EventDataValidator, 'validate_notification_event_data'))
            self.assertTrue(hasattr(EventDataValidator, 'validate_stop_event_data'))
        except ImportError as e:
            self.fail(f"Failed to import EventDataValidator: {e}")
    
    def test_tool_input_validator_importable(self):
        """ToolInputValidatorをvalidators.pyからインポートできることを確認"""
        try:
            from src.validators import ToolInputValidator
            # クラスが存在することを確認
            self.assertTrue(hasattr(ToolInputValidator, 'validate_bash_input'))
            self.assertTrue(hasattr(ToolInputValidator, 'validate_file_input'))
            self.assertTrue(hasattr(ToolInputValidator, 'validate_search_input'))
            self.assertTrue(hasattr(ToolInputValidator, 'validate_web_input'))
        except ImportError as e:
            self.fail(f"Failed to import ToolInputValidator: {e}")
    
    def test_type_guards_importable(self):
        """TypeGuard関数をvalidators.pyからインポートできることを確認"""
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
        except ImportError as e:
            self.fail(f"Failed to import type guards: {e}")
    
    def test_validate_thread_exists_importable(self):
        """validate_thread_exists関数をvalidators.pyからインポートできることを確認"""
        try:
            from src.validators import validate_thread_exists
            # 関数が存在することを確認
            self.assertTrue(callable(validate_thread_exists))
        except ImportError as e:
            self.fail(f"Failed to import validate_thread_exists: {e}")


if __name__ == "__main__":
    unittest.main()