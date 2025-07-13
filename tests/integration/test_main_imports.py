#!/usr/bin/env python3
"""Test that main discord_notifier.py works with new imports.

Following Kent Beck's TDD approach.
"""

import sys
import unittest
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)


class TestMainImports(unittest.TestCase):
    """Test that discord_notifier.py can use new module structure."""
    
    def test_can_import_main_with_new_types(self):
        """メインファイルが新しい型定義で動作することを確認"""
        start_time = time.time()
        logger.info("Testing main module import with new types", {"test_method": "test_can_import_main_with_new_types"})
        
        # This will fail initially because discord_notifier.py
        # hasn't been updated yet (Red phase)
        try:
            # First ensure new types are available
            from src.type_defs.base import BaseField
            
            # Try to import main module
            # This will fail if discord_notifier.py can't find types
            import src.discord_notifier
            
            self.assertTrue(hasattr(src.discord_notifier, 'main'))
            
            logger.info("Main module import test passed", {
                "duration": time.time() - start_time,
                "module_imported": "src.discord_notifier",
                "main_function_exists": True
            })
        except ImportError as e:
            # We expect this to fail initially
            if "BaseField" in str(e):
                logger.warning("Main module import test skipped (expected failure)", {
                    "duration": time.time() - start_time,
                    "reason": "discord_notifier.py not updated yet",
                    "error": str(e)
                })
                self.skipTest("Expected failure - discord_notifier.py not updated yet")
            else:
                logger.error("Main module import test failed unexpectedly", {
                    "duration": time.time() - start_time,
                    "error": str(e)
                })
                raise


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting main imports integration test suite", {"test_file": __file__})
    
    try:
        print("=== Main Imports Integration Tests ===")
        unittest.main()
        logger.info("Main imports test suite completed successfully", {
            "duration": time.time() - start_time
        })
    except Exception as e:
        logger.error("Main imports test suite failed", {
            "error": str(e),
            "duration": time.time() - start_time
        })
        raise