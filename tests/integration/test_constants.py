#!/usr/bin/env python3
"""Test module imports for constants and enums.

Following Kent Beck's TDD approach:
1. Write failing tests (Red)
2. Make them pass with minimal code (Green)
3. Refactor while keeping tests green
"""

import sys
import unittest
from pathlib import Path
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestConstantsImports(unittest.TestCase):
    """Test that constants and enums can be imported correctly."""
    
    def test_enums_importable(self):
        """EnumをConstants.pyからインポートできることを確認"""
        try:
            from src.constants import ToolNames, EventTypes
            # Enumが存在することを確認
            self.assertTrue(issubclass(ToolNames, Enum))
            self.assertTrue(issubclass(EventTypes, Enum))
            # 代表的な値が存在することを確認
            self.assertIn('BASH', ToolNames.__members__)
            self.assertIn('PRE_TOOL_USE', EventTypes.__members__)
        except ImportError as e:
            self.fail(f"Failed to import enums: {e}")
    
    def test_limit_constants_importable(self):
        """制限定数をConstants.pyからインポートできることを確認"""
        try:
            from src.constants import TruncationLimits, DiscordLimits
            # クラスが存在することを確認
            self.assertTrue(hasattr(TruncationLimits, 'DEFAULT'))
            self.assertTrue(hasattr(DiscordLimits, 'EMBED_DESCRIPTION_MAX'))
        except ImportError as e:
            self.fail(f"Failed to import limit constants: {e}")
    
    def test_color_constants_importable(self):
        """色定数をConstants.pyからインポートできることを確認"""
        try:
            from src.constants import DiscordColors, EVENT_TYPE_COLORS, TOOL_EMOJIS
            # クラスと辞書が存在することを確認
            self.assertTrue(hasattr(DiscordColors, 'SUCCESS'))
            self.assertIsInstance(EVENT_TYPE_COLORS, dict)
            self.assertIsInstance(TOOL_EMOJIS, dict)
        except ImportError as e:
            self.fail(f"Failed to import color constants: {e}")
    
    def test_env_constants_importable(self):
        """環境変数名をConstants.pyからインポートできることを確認"""
        try:
            from src.constants import (
                ENV_WEBHOOK_URL, ENV_BOT_TOKEN, ENV_CHANNEL_ID,
                THREAD_CACHE_EXPIRY, CONFIG_FILE_NAME
            )
            # 定数が文字列であることを確認
            self.assertIsInstance(ENV_WEBHOOK_URL, str)
            self.assertIsInstance(CONFIG_FILE_NAME, str)
            self.assertIsInstance(THREAD_CACHE_EXPIRY, (int, float))
        except ImportError as e:
            self.fail(f"Failed to import env constants: {e}")


if __name__ == "__main__":
    unittest.main()