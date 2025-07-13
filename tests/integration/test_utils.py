#!/usr/bin/env python3
"""Test module imports for utilities.

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


class TestUtilsImports(unittest.TestCase):
    """Test that utility functions can be imported correctly."""
    
    def test_truncate_string_importable(self):
        """truncate_string関数をutils_helpers.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing truncate_string import", {"test_method": "test_truncate_string_importable"})
        
        try:
            from src.utils_helpers import truncate_string
            # 関数が存在し、呼び出し可能なことを確認
            self.assertTrue(callable(truncate_string))
            # 基本的な動作確認
            result = truncate_string("Hello world!", 10)
            self.assertEqual(result, "Hello w...")
            
            logger.info("truncate_string import test passed", {
                "duration": time.time() - start_time,
                "function_tested": "truncate_string",
                "test_result": result
            })
        except ImportError as e:
            logger.error("truncate_string import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import truncate_string: {e}")
    
    def test_format_file_path_importable(self):
        """format_file_path関数をutils_helpers.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing format_file_path import", {"test_method": "test_format_file_path_importable"})
        
        try:
            from src.utils_helpers import format_file_path
            # 関数が存在し、呼び出し可能なことを確認
            self.assertTrue(callable(format_file_path))
            # 基本的な動作確認
            result = format_file_path("/home/user/file.txt")
            self.assertIsInstance(result, str)
            
            logger.info("format_file_path import test passed", {
                "duration": time.time() - start_time,
                "function_tested": "format_file_path",
                "result_type": type(result).__name__
            })
        except ImportError as e:
            logger.error("format_file_path import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import format_file_path: {e}")
    
    def test_thread_management_importable(self):
        """ensure_thread_is_usable関数をutils_helpers.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing ensure_thread_is_usable import", {"test_method": "test_thread_management_importable"})
        
        try:
            from src.utils_helpers import ensure_thread_is_usable
            # 関数が存在し、呼び出し可能なことを確認
            self.assertTrue(callable(ensure_thread_is_usable))
            
            logger.info("ensure_thread_is_usable import test passed", {
                "duration": time.time() - start_time,
                "function_tested": "ensure_thread_is_usable"
            })
        except ImportError as e:
            logger.error("ensure_thread_is_usable import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import ensure_thread_is_usable: {e}")
    
    def test_session_thread_cache_accessible(self):
        """SESSION_THREAD_CACHEがutils_helpers.pyからアクセスできることを確認"""
        start_time = time.time()
        logger.info("Testing SESSION_THREAD_CACHE import", {"test_method": "test_session_thread_cache_accessible"})
        
        try:
            from src.utils_helpers import SESSION_THREAD_CACHE
            # 辞書であることを確認
            self.assertIsInstance(SESSION_THREAD_CACHE, dict)
            
            logger.info("SESSION_THREAD_CACHE import test passed", {
                "duration": time.time() - start_time,
                "cache_type": type(SESSION_THREAD_CACHE).__name__,
                "cache_size": len(SESSION_THREAD_CACHE)
            })
        except ImportError as e:
            logger.error("SESSION_THREAD_CACHE import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import SESSION_THREAD_CACHE: {e}")


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting utils integration test suite", {"test_file": __file__})
    
    try:
        print("=== Utils Integration Tests ===")
        unittest.main()
        logger.info("Utils test suite completed successfully", {
            "duration": time.time() - start_time
        })
    except Exception as e:
        logger.error("Utils test suite failed", {
            "error": str(e),
            "duration": time.time() - start_time
        })
        raise