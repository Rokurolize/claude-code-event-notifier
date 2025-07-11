#!/usr/bin/env python3
"""Test module imports for utilities.

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


class TestUtilsImports(unittest.TestCase):
    """Test that utility functions can be imported correctly."""
    
    def test_truncate_string_importable(self):
        """truncate_string関数をutils_helpers.pyからインポートできることを確認"""
        try:
            from src.utils_helpers import truncate_string
            # 関数が存在し、呼び出し可能なことを確認
            self.assertTrue(callable(truncate_string))
            # 基本的な動作確認
            result = truncate_string("Hello world!", 10)
            self.assertEqual(result, "Hello w...")
        except ImportError as e:
            self.fail(f"Failed to import truncate_string: {e}")
    
    def test_format_file_path_importable(self):
        """format_file_path関数をutils_helpers.pyからインポートできることを確認"""
        try:
            from src.utils_helpers import format_file_path
            # 関数が存在し、呼び出し可能なことを確認
            self.assertTrue(callable(format_file_path))
            # 基本的な動作確認
            result = format_file_path("/home/user/file.txt")
            self.assertIsInstance(result, str)
        except ImportError as e:
            self.fail(f"Failed to import format_file_path: {e}")
    
    def test_thread_management_importable(self):
        """ensure_thread_is_usable関数をutils_helpers.pyからインポートできることを確認"""
        try:
            from src.utils_helpers import ensure_thread_is_usable
            # 関数が存在し、呼び出し可能なことを確認
            self.assertTrue(callable(ensure_thread_is_usable))
        except ImportError as e:
            self.fail(f"Failed to import ensure_thread_is_usable: {e}")
    
    def test_session_thread_cache_accessible(self):
        """SESSION_THREAD_CACHEがutils_helpers.pyからアクセスできることを確認"""
        try:
            from src.utils_helpers import SESSION_THREAD_CACHE
            # 辞書であることを確認
            self.assertIsInstance(SESSION_THREAD_CACHE, dict)
        except ImportError as e:
            self.fail(f"Failed to import SESSION_THREAD_CACHE: {e}")


if __name__ == "__main__":
    unittest.main()