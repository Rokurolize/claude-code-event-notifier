#!/usr/bin/env python3
"""Unit tests for simple utils module."""

import unittest
from pathlib import Path

# Import the utils module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.simple.utils import sanitize_log_input, escape_discord_markdown, parse_bool


class TestUtils(unittest.TestCase):
    """Test utility functions."""
    
    def test_sanitize_log_input(self):
        """Test log input sanitization."""
        # Test newline removal
        self.assertEqual(sanitize_log_input("test\nstring"), "teststring")
        self.assertEqual(sanitize_log_input("test\rstring"), "teststring")
        self.assertEqual(sanitize_log_input("test\r\nstring"), "teststring")
        
        # Test with clean input
        self.assertEqual(sanitize_log_input("clean string"), "clean string")
        
        # Test with None
        self.assertEqual(sanitize_log_input(None), "None")
        
        # Test with numbers
        self.assertEqual(sanitize_log_input(123), "123")
        
        # Test with empty string
        self.assertEqual(sanitize_log_input(""), "")
    
    def test_escape_discord_markdown(self):
        """Test Discord markdown escaping."""
        # Test basic markdown characters
        self.assertEqual(escape_discord_markdown("*bold*"), "\\*bold\\*")
        self.assertEqual(escape_discord_markdown("_italic_"), "\\_italic\\_")
        self.assertEqual(escape_discord_markdown("**bold**"), "\\*\\*bold\\*\\*")
        self.assertEqual(escape_discord_markdown("__underline__"), "\\_\\_underline\\_\\_")
        self.assertEqual(escape_discord_markdown("~~strike~~"), "\\~\\~strike\\~\\~")
        self.assertEqual(escape_discord_markdown("`code`"), "\\`code\\`")
        self.assertEqual(escape_discord_markdown("||spoiler||"), "\\|\\|spoiler\\|\\|")
        
        # Test multiple characters
        self.assertEqual(
            escape_discord_markdown("*bold* and _italic_"),
            "\\*bold\\* and \\_italic\\_"
        )
        
        # Test with no markdown
        self.assertEqual(escape_discord_markdown("plain text"), "plain text")
        
        # Test empty string
        self.assertEqual(escape_discord_markdown(""), "")
        
        # Test None (should return empty string)
        self.assertEqual(escape_discord_markdown(None), "")
    
    def test_parse_bool(self):
        """Test string to boolean conversion."""
        # Test true values
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("True"))
        self.assertTrue(parse_bool("TRUE"))
        self.assertTrue(parse_bool("yes"))
        self.assertTrue(parse_bool("YES"))
        self.assertTrue(parse_bool("on"))
        self.assertTrue(parse_bool("1"))
        
        # Test false values
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool("FALSE"))
        self.assertFalse(parse_bool("no"))
        self.assertFalse(parse_bool("NO"))
        self.assertFalse(parse_bool("off"))
        self.assertFalse(parse_bool("0"))
        
        # Test empty values
        self.assertFalse(parse_bool(""))
        # Note: parse_bool doesn't handle None - it expects a string
        
        # Test other values (should be false)
        self.assertFalse(parse_bool("maybe"))
        self.assertFalse(parse_bool("2"))
        self.assertFalse(parse_bool("random"))
    
    def test_escape_discord_markdown_complex(self):
        """Test Discord markdown escaping with complex cases."""
        # Test code blocks (should not escape inside)
        text = "Here is `some code` and ```\\ncode block\\n```"
        expected = "Here is \\`some code\\` and \\`\\`\\`\\ncode block\\n\\`\\`\\`"
        self.assertEqual(escape_discord_markdown(text), expected)
        
        # Test URLs (should not break)
        text = "Check out https://example.com/path_with_underscores"
        expected = "Check out https://example.com/path\\_with\\_underscores"
        self.assertEqual(escape_discord_markdown(text), expected)
        
        # Test mixed formatting
        text = "This has *bold*, _italic_, and ||spoilers|| all together!"
        expected = "This has \\*bold\\*, \\_italic\\_, and \\|\\|spoilers\\|\\| all together!"
        self.assertEqual(escape_discord_markdown(text), expected)


if __name__ == "__main__":
    unittest.main()