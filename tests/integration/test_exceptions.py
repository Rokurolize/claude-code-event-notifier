#!/usr/bin/env python3
"""Test module imports for exception classes.

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


class TestExceptionImports(unittest.TestCase):
    """Test that exception classes can be imported correctly."""
    
    def test_exceptions_importable(self):
        """例外クラスをexceptions.pyからインポートできることを確認"""
        try:
            from src.exceptions import (
                DiscordNotifierError, ConfigurationError,
                DiscordAPIError, EventProcessingError,
                InvalidEventTypeError, ThreadManagementError,
                ThreadStorageError
            )
            # 例外クラスが存在することを確認
            self.assertTrue(issubclass(DiscordNotifierError, Exception))
            self.assertTrue(issubclass(ConfigurationError, DiscordNotifierError))
            self.assertTrue(issubclass(DiscordAPIError, DiscordNotifierError))
            self.assertTrue(issubclass(EventProcessingError, DiscordNotifierError))
            self.assertTrue(issubclass(InvalidEventTypeError, DiscordNotifierError))
            self.assertTrue(issubclass(ThreadManagementError, DiscordNotifierError))
            self.assertTrue(issubclass(ThreadStorageError, DiscordNotifierError))
        except ImportError as e:
            self.fail(f"Failed to import exceptions: {e}")


if __name__ == "__main__":
    unittest.main()