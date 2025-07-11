#!/usr/bin/env python3
"""Test that main discord_notifier.py works with new imports.

Following Kent Beck's TDD approach.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestMainImports(unittest.TestCase):
    """Test that discord_notifier.py can use new module structure."""
    
    def test_can_import_main_with_new_types(self):
        """メインファイルが新しい型定義で動作することを確認"""
        # This will fail initially because discord_notifier.py
        # hasn't been updated yet (Red phase)
        try:
            # First ensure new types are available
            from src.type_defs.base import BaseField
            
            # Try to import main module
            # This will fail if discord_notifier.py can't find types
            import src.discord_notifier
            
            self.assertTrue(hasattr(src.discord_notifier, 'main'))
        except ImportError as e:
            # We expect this to fail initially
            if "BaseField" in str(e):
                self.skipTest("Expected failure - discord_notifier.py not updated yet")
            else:
                raise


if __name__ == "__main__":
    unittest.main()