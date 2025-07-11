#!/usr/bin/env python3
"""Test module imports for type definitions.

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


class TestTypeImports(unittest.TestCase):
    """Test that type modules can be imported correctly."""
    
    def test_base_types_importable(self):
        """基本型定義をtype_defs.baseからインポートできることを確認"""
        try:
            from src.type_defs.base import BaseField, TimestampedField, SessionAware, PathAware
            # 型が存在することを確認
            self.assertTrue(hasattr(BaseField, '__annotations__'))
            self.assertTrue(hasattr(TimestampedField, '__annotations__'))
            self.assertTrue(hasattr(SessionAware, '__annotations__'))
            self.assertTrue(hasattr(PathAware, '__annotations__'))
        except ImportError as e:
            self.fail(f"Failed to import base types: {e}")
    
    def test_discord_types_importable(self):
        """Discord関連型をtype_defs.discordからインポートできることを確認"""
        try:
            from src.type_defs.discord import (
                DiscordFooter, DiscordFieldBase, DiscordField,
                DiscordEmbedBase, DiscordEmbed, DiscordMessageBase,
                DiscordMessage, DiscordChannel, DiscordThread,
                DiscordThreadMessage
            )
            # 型が存在することを確認
            self.assertTrue(hasattr(DiscordFooter, '__annotations__'))
            self.assertTrue(hasattr(DiscordField, '__annotations__'))
            self.assertTrue(hasattr(DiscordEmbed, '__annotations__'))
            self.assertTrue(hasattr(DiscordThread, '__annotations__'))
        except ImportError as e:
            self.fail(f"Failed to import Discord types: {e}")
    
    def test_config_types_importable(self):
        """Config関連型をtype_defs.configからインポートできることを確認"""
        try:
            from src.type_defs.config import (
                DiscordCredentials, ThreadConfiguration,
                NotificationConfiguration, EventFilterConfiguration,
                Config
            )
            # 型が存在することを確認
            self.assertTrue(hasattr(DiscordCredentials, '__annotations__'))
            self.assertTrue(hasattr(ThreadConfiguration, '__annotations__'))
            self.assertTrue(hasattr(NotificationConfiguration, '__annotations__'))
            self.assertTrue(hasattr(EventFilterConfiguration, '__annotations__'))
            self.assertTrue(hasattr(Config, '__annotations__'))
        except ImportError as e:
            self.fail(f"Failed to import config types: {e}")
    
    def test_tool_types_importable(self):
        """Tool関連型をtype_defs.toolsからインポートできることを確認"""
        try:
            from src.type_defs.tools import (
                ToolInputBase, BashToolInput, FileEditOperation,
                FileToolInputBase, ReadToolInput, WriteToolInput,
                EditToolInput, MultiEditToolInput, ListToolInput,
                SearchToolInputBase, GlobToolInput, GrepToolInput,
                TaskToolInput, WebToolInput, FileToolInput, SearchToolInput,
                ToolInput, ToolResponseBase, BashToolResponse,
                FileOperationResponse, SearchResponse, ToolResponse
            )
            # 代表的な型が存在することを確認
            self.assertTrue(hasattr(ToolInputBase, '__annotations__'))
            self.assertTrue(hasattr(BashToolInput, '__annotations__'))
            self.assertTrue(hasattr(ToolResponseBase, '__annotations__'))
            self.assertTrue(hasattr(BashToolResponse, '__annotations__'))
        except ImportError as e:
            self.fail(f"Failed to import tool types: {e}")
    
    def test_event_types_importable(self):
        """Event関連型をtype_defs.eventsからインポートできることを確認"""
        try:
            from src.type_defs.events import (
                BaseEventData, ToolEventDataBase, PreToolUseEventData,
                PostToolUseEventData, NotificationEventData,
                StopEventDataBase, StopEventData, SubagentStopEventData,
                EventData
            )
            # 代表的な型が存在することを確認
            self.assertTrue(hasattr(BaseEventData, '__annotations__'))
            self.assertTrue(hasattr(ToolEventDataBase, '__annotations__'))
            self.assertTrue(hasattr(StopEventData, '__annotations__'))
            self.assertTrue(hasattr(SubagentStopEventData, '__annotations__'))
        except ImportError as e:
            self.fail(f"Failed to import event types: {e}")
    
    def test_discord_notifier_can_use_base_types(self):
        """discord_notifier.pyが新しい型定義を使用できることを確認"""
        # First, modify discord_notifier.py to import from new location
        # This test will initially fail (Red phase)
        try:
            # Simulate what discord_notifier.py will need to do
            from src.type_defs.base import BaseField, TimestampedField, SessionAware, PathAware
            
            # Verify the types are usable
            test_field: BaseField = {}
            test_timestamp: TimestampedField = {"timestamp": "2023-01-01T00:00:00Z"}
            test_session: SessionAware = {"session_id": "test123"}
            test_path: PathAware = {"file_path": "/test/path"}
            
            self.assertIsInstance(test_field, dict)
            self.assertIsInstance(test_timestamp, dict)
            self.assertIsInstance(test_session, dict)
            self.assertIsInstance(test_path, dict)
        except Exception as e:
            self.fail(f"Failed to use base types: {e}")


if __name__ == "__main__":
    unittest.main()