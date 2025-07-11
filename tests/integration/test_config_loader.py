#!/usr/bin/env python3
"""Test module imports for ConfigLoader.

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


class TestConfigLoaderImports(unittest.TestCase):
    """Test that ConfigLoader can be imported correctly."""
    
    def test_config_loader_importable(self):
        """ConfigLoaderをcore.config_loader.pyからインポートできることを確認"""
        try:
            from src.core.config_loader import ConfigLoader
            # クラスが存在することを確認
            self.assertTrue(hasattr(ConfigLoader, 'load'))
            self.assertTrue(callable(ConfigLoader.load))
        except ImportError as e:
            self.fail(f"Failed to import ConfigLoader: {e}")
    
    def test_config_defaults_accessible(self):
        """DEFAULT_CONFIGがアクセスできることを確認"""
        try:
            from src.core.config_loader import DEFAULT_CONFIG
            # 辞書であることを確認
            self.assertIsInstance(DEFAULT_CONFIG, dict)
            # 基本的なキーが存在することを確認
            self.assertIn('debug', DEFAULT_CONFIG)
            self.assertIn('use_threads', DEFAULT_CONFIG)
        except ImportError as e:
            self.fail(f"Failed to import DEFAULT_CONFIG: {e}")


if __name__ == "__main__":
    unittest.main()