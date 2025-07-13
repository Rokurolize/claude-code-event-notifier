#!/usr/bin/env python3
"""Test module imports for ConfigLoader.

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


class TestConfigLoaderImports(unittest.TestCase):
    """Test that ConfigLoader can be imported correctly."""
    
    def test_config_loader_importable(self):
        """ConfigLoaderをcore.config_loader.pyからインポートできることを確認"""
        start_time = time.time()
        logger.info("Testing ConfigLoader import", {"test_method": "test_config_loader_importable"})
        
        try:
            from src.core.config_loader import ConfigLoader
            # クラスが存在することを確認
            self.assertTrue(hasattr(ConfigLoader, 'load'))
            self.assertTrue(callable(ConfigLoader.load))
            
            logger.info("ConfigLoader import test passed", {
                "duration": time.time() - start_time,
                "class_tested": "ConfigLoader",
                "methods_verified": ["load"]
            })
        except ImportError as e:
            logger.error("ConfigLoader import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import ConfigLoader: {e}")
    
    def test_config_defaults_accessible(self):
        """DEFAULT_CONFIGがアクセスできることを確認"""
        start_time = time.time()
        logger.info("Testing DEFAULT_CONFIG import", {"test_method": "test_config_defaults_accessible"})
        
        try:
            from src.core.config_loader import DEFAULT_CONFIG
            # 辞書であることを確認
            self.assertIsInstance(DEFAULT_CONFIG, dict)
            # 基本的なキーが存在することを確認
            self.assertIn('debug', DEFAULT_CONFIG)
            self.assertIn('use_threads', DEFAULT_CONFIG)
            
            logger.info("DEFAULT_CONFIG import test passed", {
                "duration": time.time() - start_time,
                "config_type": type(DEFAULT_CONFIG).__name__,
                "config_keys": list(DEFAULT_CONFIG.keys()),
                "required_keys_present": ["debug", "use_threads"]
            })
        except ImportError as e:
            logger.error("DEFAULT_CONFIG import failed", {
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.fail(f"Failed to import DEFAULT_CONFIG: {e}")


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting config loader integration test suite", {"test_file": __file__})
    
    try:
        print("=== Config Loader Integration Tests ===")
        unittest.main()
        logger.info("Config loader test suite completed successfully", {
            "duration": time.time() - start_time
        })
    except Exception as e:
        logger.error("Config loader test suite failed", {
            "error": str(e),
            "duration": time.time() - start_time
        })
        raise