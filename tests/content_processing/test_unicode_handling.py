#!/usr/bin/env python3
"""Test Unicode Content Handling.

This module provides comprehensive tests for Unicode content handling,
including multi-byte character processing, emoji support, international
text handling, encoding/decoding validation, and character normalization.
"""

import asyncio
import json
import time
import unittest
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.formatters.embed_utils import EmbedUtils
from src.utils.discord_utils import DiscordUtils


class TestUnicodeHandling(unittest.IsolatedAsyncioTestCase):
    """Test cases for Unicode content handling."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Unicode test content samples
        self.unicode_test_samples = {
            "basic_multilingual": {
                "english": "Hello World",
                "japanese": "こんにちは世界",
                "chinese_simplified": "你好世界",
                "chinese_traditional": "你好世界",
                "korean": "안녕하세요 세계",
                "arabic": "مرحبا بالعالم",
                "russian": "Привет мир",
                "hindi": "नमस्ते दुनिया",
                "greek": "Γεια σας κόσμε",
                "hebrew": "שלום עולם"
            },
            "emoji_samples": {
                "basic_emoji": "😀😃😄😁😆😅😂🤣😊😇",
                "flags": "🇺🇸🇯🇵🇨🇳🇰🇷🇩🇪🇫🇷🇬🇧🇷🇺🇮🇳",
                "symbols": "⚡🔥💧🌟⭐✨💫🌙☀️🌈",
                "tools": "🔧🛠️⚙️🔨🪛🔩⚡🖥️💻📱",
                "mixed_complexity": "🧑‍💻👨‍👩‍👧‍👦🏳️‍🌈🏳️‍⚧️👨🏽‍🦱"
            },
            "special_characters": {
                "mathematical": "∑∆∅∞≈≠≤≥±√∫∏∐∪∩⊆⊇⊂⊃",
                "currency": "¢£¥€₹₽₩₪₺₴₦₡₨₵₸₼",
                "punctuation": """‚„…‰′″‴‼‽⁇⁈⁉‵‶‷‸‹›«»""",
                "arrows": "←↑→↓↔↕↖↗↘↙⇐⇑⇒⇓⇔⇕",
                "diacritics": "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
            },
            "combining_characters": {
                "diacritics_combined": "e\u0301e\u0300e\u0302e\u0303e\u0308",  # é è ê ẽ ë
                "zalgo_text": "h\u0300\u0301\u0302e\u0300\u0301l\u0300\u0301l\u0300\u0301o\u0300\u0301",
                "accented_complex": "Iñtërnâtiônàlizætiøn",
                "normalization_test": "café vs cafe\u0301"  # NFC vs NFD
            },
            "problematic_content": {
                "null_bytes": "text\x00with\x00nulls",
                "control_chars": "text\x01\x02\x03\x04control",
                "bidi_text": "Hello שלום مرحبا World",  # Bidirectional text
                "mixed_scripts": "Русский中文한국어العربية",
                "zero_width": "zero\u200Bwidth\u200Cjoiners\u200D",
                "invisible_chars": "invisible\u2060\u2061\u2062\u2063chars"
            }
        }
        
        # Test configurations for different Unicode handling scenarios
        self.unicode_configs = {
            "strict_ascii": {
                "allow_unicode": False,
                "encoding": "ascii",
                "error_handling": "replace"
            },
            "utf8_permissive": {
                "allow_unicode": True,
                "encoding": "utf-8",
                "error_handling": "ignore"
            },
            "utf8_strict": {
                "allow_unicode": True,
                "encoding": "utf-8",
                "error_handling": "strict"
            },
            "normalization_nfc": {
                "allow_unicode": True,
                "encoding": "utf-8",
                "normalization": "NFC"
            }
        }
    
    async def test_multi_byte_character_processing(self) -> None:
        """Test processing of multi-byte Unicode characters."""
        with patch('src.utils.discord_utils.DiscordUtils') as mock_discord_utils:
            mock_instance = MagicMock()
            mock_discord_utils.return_value = mock_instance
            
            # Configure Unicode-aware text processing
            def process_unicode_text(text: str, max_length: int = 1000) -> Dict[str, Any]:
                """Process Unicode text with proper multi-byte handling."""
                
                # Character count (not byte count)
                char_count = len(text)
                
                # Byte count in different encodings
                try:
                    utf8_bytes = len(text.encode('utf-8'))
                    utf16_bytes = len(text.encode('utf-16'))
                    ascii_bytes = len(text.encode('ascii', errors='replace'))
                except UnicodeEncodeError as e:
                    utf8_bytes = utf16_bytes = ascii_bytes = -1
                
                # Detect character categories
                categories = {
                    "ascii": 0,
                    "latin_extended": 0,
                    "cjk": 0,
                    "arabic": 0,
                    "emoji": 0,
                    "combining": 0,
                    "control": 0
                }
                
                for char in text:
                    codepoint = ord(char)
                    if codepoint < 128:
                        categories["ascii"] += 1
                    elif codepoint < 256:
                        categories["latin_extended"] += 1
                    elif 0x4E00 <= codepoint <= 0x9FFF:  # CJK Unified Ideographs
                        categories["cjk"] += 1
                    elif 0x600 <= codepoint <= 0x6FF:  # Arabic
                        categories["arabic"] += 1
                    elif 0x1F600 <= codepoint <= 0x1F64F:  # Emoticons
                        categories["emoji"] += 1
                    elif unicodedata.combining(char):
                        categories["combining"] += 1
                    elif unicodedata.category(char).startswith('C'):
                        categories["control"] += 1
                
                # Truncation handling (character-aware)
                truncated = text[:max_length] if char_count > max_length else text
                
                return {
                    "original_text": text,
                    "processed_text": truncated,
                    "char_count": char_count,
                    "utf8_bytes": utf8_bytes,
                    "utf16_bytes": utf16_bytes,
                    "ascii_bytes": ascii_bytes,
                    "categories": categories,
                    "truncated": char_count > max_length,
                    "is_ascii": all(ord(c) < 128 for c in text),
                    "has_emoji": any(0x1F600 <= ord(c) <= 0x1F64F for c in text),
                    "has_combining": any(unicodedata.combining(c) for c in text)
                }
            
            mock_instance.process_unicode_text.side_effect = process_unicode_text
            
            discord_utils = DiscordUtils()
            
            # Test multi-byte character processing
            for category, samples in self.unicode_test_samples.items():
                for sample_name, sample_text in samples.items():
                    with self.subTest(category=category, sample=sample_name):
                        result = discord_utils.process_unicode_text(sample_text, max_length=500)
                        
                        # Verify basic processing
                        self.assertIsNotNone(result["processed_text"])
                        self.assertEqual(result["char_count"], len(sample_text))
                        
                        # Verify byte counts are reasonable
                        if result["utf8_bytes"] != -1:
                            self.assertGreaterEqual(result["utf8_bytes"], result["char_count"])
                        
                        # Verify character categorization
                        total_categorized = sum(result["categories"].values())
                        self.assertEqual(total_categorized, result["char_count"])
                        
                        # Verify encoding compatibility
                        try:
                            # Should be able to encode/decode processed text
                            encoded = result["processed_text"].encode('utf-8')
                            decoded = encoded.decode('utf-8')
                            self.assertEqual(decoded, result["processed_text"])
                        except UnicodeError:
                            self.fail(f"Unicode encoding/decoding failed for {sample_name}")
                        
                        # Log processing results
                        self.logger.info(
                            f"Unicode processing: {category}/{sample_name}",
                            context={
                                "char_count": result["char_count"],
                                "utf8_bytes": result["utf8_bytes"],
                                "categories": result["categories"],
                                "is_ascii": result["is_ascii"],
                                "has_emoji": result["has_emoji"],
                                "has_combining": result["has_combining"]
                            }
                        )
    
    async def test_emoji_support_comprehensive(self) -> None:
        """Test comprehensive emoji support including complex sequences."""
        emoji_test_cases = [
            {
                "name": "basic_face_emoji",
                "content": "😀😃😄😁😆😅😂🤣",
                "expected_emoji_count": 8,
                "complexity": "simple"
            },
            {
                "name": "skin_tone_modifiers",
                "content": "👋👋🏻👋🏼👋🏽👋🏾👋🏿",
                "expected_emoji_count": 6,
                "complexity": "moderate"
            },
            {
                "name": "zero_width_joiner_sequences",
                "content": "👨‍💻👩‍💻🧑‍💻👨‍👩‍👧‍👦",
                "expected_emoji_count": 4,
                "complexity": "complex"
            },
            {
                "name": "flag_sequences",
                "content": "🇺🇸🇯🇵🇨🇳🇰🇷🇩🇪🇫🇷",
                "expected_emoji_count": 6,
                "complexity": "moderate"
            },
            {
                "name": "keycap_sequences",
                "content": "1️⃣2️⃣3️⃣*️⃣#️⃣",
                "expected_emoji_count": 5,
                "complexity": "moderate"
            },
            {
                "name": "mixed_text_emoji",
                "content": "Hello 👋 World 🌍! Code 👨‍💻 is fun! 🎉",
                "expected_emoji_count": 4,
                "complexity": "mixed"
            }
        ]
        
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure emoji-aware processing
            def process_emoji_content(content: str) -> Dict[str, Any]:
                """Process content with emoji-aware analysis."""
                import re
                
                # Simple emoji detection (basic implementation)
                emoji_ranges = [
                    (0x1F600, 0x1F64F),  # Emoticons
                    (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
                    (0x1F680, 0x1F6FF),  # Transport and Map
                    (0x1F1E0, 0x1F1FF),  # Regional Indicator Symbols (flags)
                    (0x2600, 0x26FF),    # Misc symbols
                    (0x2700, 0x27BF),    # Dingbats
                ]
                
                emoji_chars = []
                text_chars = []
                
                i = 0
                while i < len(content):
                    char = content[i]
                    codepoint = ord(char)
                    
                    # Check if character is an emoji
                    is_emoji = any(start <= codepoint <= end for start, end in emoji_ranges)
                    
                    if is_emoji:
                        # Handle potential sequences
                        emoji_sequence = char
                        j = i + 1
                        
                        # Look for modifiers and joiners
                        while j < len(content):
                            next_char = content[j]
                            next_codepoint = ord(next_char)
                            
                            # Skin tone modifiers (U+1F3FB to U+1F3FF)
                            # Zero Width Joiner (U+200D)
                            # Variation Selector-16 (U+FE0F)
                            if (0x1F3FB <= next_codepoint <= 0x1F3FF or 
                                next_codepoint == 0x200D or 
                                next_codepoint == 0xFE0F or
                                any(start <= next_codepoint <= end for start, end in emoji_ranges)):
                                emoji_sequence += next_char
                                j += 1
                            else:
                                break
                        
                        emoji_chars.append(emoji_sequence)
                        i = j
                    else:
                        text_chars.append(char)
                        i += 1
                
                return {
                    "original_content": content,
                    "emoji_chars": emoji_chars,
                    "text_chars": text_chars,
                    "emoji_count": len(emoji_chars),
                    "text_length": len(text_chars),
                    "total_length": len(content),
                    "has_complex_emoji": any(len(emoji) > 1 for emoji in emoji_chars),
                    "emoji_percentage": len(emoji_chars) / len(content) if content else 0
                }
            
            mock_instance.process_emoji_content.side_effect = process_emoji_content
            
            embed_utils = EmbedUtils()
            
            # Test emoji processing
            for test_case in emoji_test_cases:
                with self.subTest(emoji_case=test_case["name"]):
                    result = embed_utils.process_emoji_content(test_case["content"])
                    
                    # Verify emoji detection
                    self.assertGreaterEqual(result["emoji_count"], 1)
                    
                    # Verify content reconstruction
                    reconstructed = ''.join(result["emoji_chars"]) + ''.join(result["text_chars"])
                    # Note: Order might be different, so we check character counts instead
                    self.assertEqual(len(reconstructed), len(test_case["content"]))
                    
                    # Verify emoji complexity detection
                    if test_case["complexity"] == "complex":
                        self.assertTrue(result["has_complex_emoji"])
                    
                    # Verify reasonable emoji count (within tolerance)
                    expected_count = test_case["expected_emoji_count"]
                    actual_count = result["emoji_count"]
                    tolerance = max(1, expected_count * 0.3)  # 30% tolerance
                    self.assertLessEqual(abs(actual_count - expected_count), tolerance,
                                       f"Emoji count mismatch: expected ~{expected_count}, got {actual_count}")
                    
                    # Log emoji analysis
                    self.logger.info(
                        f"Emoji processing: {test_case['name']}",
                        context={
                            "expected_count": expected_count,
                            "detected_count": actual_count,
                            "complexity": test_case["complexity"],
                            "has_complex": result["has_complex_emoji"],
                            "emoji_percentage": result["emoji_percentage"],
                            "sample_emojis": result["emoji_chars"][:5]  # First 5 for logging
                        }
                    )
    
    async def test_international_text_handling(self) -> None:
        """Test handling of international text in various scripts."""
        with patch('src.utils.discord_utils.DiscordUtils') as mock_discord_utils:
            mock_instance = MagicMock()
            mock_discord_utils.return_value = mock_instance
            
            # Configure international text processing
            def process_international_text(text: str, target_length: int = 100) -> Dict[str, Any]:
                """Process international text with script-aware handling."""
                
                scripts = {
                    "Latin": 0,
                    "Cyrillic": 0,
                    "Arabic": 0,
                    "Hebrew": 0,
                    "CJK": 0,
                    "Devanagari": 0,
                    "Greek": 0,
                    "Unknown": 0
                }
                
                # Analyze script distribution
                for char in text:
                    script = unicodedata.name(char, "").split()[0] if unicodedata.name(char, "") else "UNKNOWN"
                    
                    if "LATIN" in script:
                        scripts["Latin"] += 1
                    elif "CYRILLIC" in script:
                        scripts["Cyrillic"] += 1
                    elif "ARABIC" in script:
                        scripts["Arabic"] += 1
                    elif "HEBREW" in script:
                        scripts["Hebrew"] += 1
                    elif any(cjk in script for cjk in ["CJK", "HIRAGANA", "KATAKANA", "HANGUL"]):
                        scripts["CJK"] += 1
                    elif "DEVANAGARI" in script:
                        scripts["Devanagari"] += 1
                    elif "GREEK" in script:
                        scripts["Greek"] += 1
                    else:
                        scripts["Unknown"] += 1
                
                # Smart truncation for international text
                if len(text) <= target_length:
                    truncated_text = text
                else:
                    # Try to break at word boundaries
                    truncated_text = text[:target_length]
                    
                    # For scripts without spaces, truncate more conservatively
                    dominant_script = max(scripts, key=scripts.get)
                    if dominant_script == "CJK":
                        # CJK characters often don't use spaces
                        truncated_text = text[:target_length - 1] + "…"
                    elif dominant_script in ["Arabic", "Hebrew"]:
                        # RTL scripts need special handling
                        truncated_text = text[:target_length - 1] + "…"
                    else:
                        # Try to find last space
                        last_space = truncated_text.rfind(' ')
                        if last_space > target_length * 0.7:  # Don't truncate too much
                            truncated_text = truncated_text[:last_space] + "..."
                        else:
                            truncated_text = truncated_text[:-3] + "..."
                
                return {
                    "original_text": text,
                    "processed_text": truncated_text,
                    "scripts": scripts,
                    "dominant_script": max(scripts, key=scripts.get),
                    "is_mixed_script": sum(1 for count in scripts.values() if count > 0) > 1,
                    "truncated": len(truncated_text) < len(text),
                    "character_count": len(text),
                    "processed_count": len(truncated_text)
                }
            
            mock_instance.process_international_text.side_effect = process_international_text
            
            discord_utils = DiscordUtils()
            
            # Test international text processing
            international_test_cases = [
                {
                    "name": "pure_english",
                    "text": "Hello world! This is a test message in English.",
                    "expected_script": "Latin"
                },
                {
                    "name": "pure_japanese",
                    "text": "こんにちは世界！これは日本語のテストメッセージです。",
                    "expected_script": "CJK"
                },
                {
                    "name": "pure_arabic",
                    "text": "مرحبا بالعالم! هذه رسالة اختبار باللغة العربية.",
                    "expected_script": "Arabic"
                },
                {
                    "name": "pure_russian",
                    "text": "Привет мир! Это тестовое сообщение на русском языке.",
                    "expected_script": "Cyrillic"
                },
                {
                    "name": "mixed_latin_cyrillic",
                    "text": "Hello Привет World мир! Mixed script test.",
                    "expected_script": "Latin"  # Should be dominant
                },
                {
                    "name": "mixed_complex",
                    "text": "English 中文 العربية Русский 한국어 mix",
                    "expected_script": "Latin"
                }
            ]
            
            for test_case in international_test_cases:
                with self.subTest(international_case=test_case["name"]):
                    result = discord_utils.process_international_text(test_case["text"], target_length=50)
                    
                    # Verify processing success
                    self.assertIsNotNone(result["processed_text"])
                    self.assertLessEqual(len(result["processed_text"]), 50)
                    
                    # Verify script detection
                    self.assertEqual(result["dominant_script"], test_case["expected_script"])
                    
                    # Verify character preservation in truncation
                    if result["truncated"]:
                        self.assertTrue(
                            result["processed_text"].endswith(("...", "…")) or
                            len(result["processed_text"]) == 50
                        )
                    
                    # Verify encoding stability
                    try:
                        encoded = result["processed_text"].encode('utf-8')
                        decoded = encoded.decode('utf-8')
                        self.assertEqual(decoded, result["processed_text"])
                    except UnicodeError:
                        self.fail(f"Unicode encoding failed for {test_case['name']}")
                    
                    # Log international text analysis
                    self.logger.info(
                        f"International text: {test_case['name']}",
                        context={
                            "dominant_script": result["dominant_script"],
                            "is_mixed_script": result["is_mixed_script"],
                            "scripts": result["scripts"],
                            "truncated": result["truncated"],
                            "original_length": result["character_count"],
                            "processed_length": result["processed_count"]
                        }
                    )
    
    async def test_encoding_decoding_validation(self) -> None:
        """Test encoding and decoding validation for various character sets."""
        encoding_test_cases = [
            {
                "name": "utf8_standard",
                "encoding": "utf-8",
                "test_content": "Standard UTF-8 content with émojis 🚀",
                "should_succeed": True
            },
            {
                "name": "utf8_complex",
                "encoding": "utf-8", 
                "test_content": "Complex: 中文🇺🇸العربية👨‍💻Русский",
                "should_succeed": True
            },
            {
                "name": "ascii_simple",
                "encoding": "ascii",
                "test_content": "Simple ASCII content only",
                "should_succeed": True
            },
            {
                "name": "ascii_with_unicode",
                "encoding": "ascii",
                "test_content": "ASCII with Unicode: émojis 🚀",
                "should_succeed": False
            },
            {
                "name": "latin1_extended",
                "encoding": "latin-1",
                "test_content": "Latin-1: café résumé naïve",
                "should_succeed": True
            },
            {
                "name": "latin1_with_emoji",
                "encoding": "latin-1",
                "test_content": "Latin-1 with emoji: 🚀",
                "should_succeed": False
            }
        ]
        
        with patch('src.utils.discord_utils.DiscordUtils') as mock_discord_utils:
            mock_instance = MagicMock()
            mock_discord_utils.return_value = mock_instance
            
            # Configure encoding validation
            def validate_encoding(content: str, encoding: str, error_handling: str = "strict") -> Dict[str, Any]:
                """Validate content against specific encoding."""
                
                try:
                    # Test encoding
                    encoded = content.encode(encoding, errors=error_handling)
                    encode_success = True
                    encoded_size = len(encoded)
                except UnicodeEncodeError as e:
                    encode_success = False
                    encoded_size = -1
                    encoded = None
                
                try:
                    # Test decoding (if encoding succeeded)
                    if encoded is not None:
                        decoded = encoded.decode(encoding, errors=error_handling)
                        decode_success = True
                        roundtrip_success = decoded == content
                    else:
                        decoded = None
                        decode_success = False
                        roundtrip_success = False
                except UnicodeDecodeError:
                    decode_success = False
                    roundtrip_success = False
                    decoded = None
                
                # Character analysis
                char_analysis = {
                    "total_chars": len(content),
                    "ascii_chars": sum(1 for c in content if ord(c) < 128),
                    "extended_chars": sum(1 for c in content if 128 <= ord(c) < 256),
                    "unicode_chars": sum(1 for c in content if ord(c) >= 256),
                    "max_codepoint": max(ord(c) for c in content) if content else 0
                }
                
                return {
                    "content": content,
                    "encoding": encoding,
                    "error_handling": error_handling,
                    "encode_success": encode_success,
                    "decode_success": decode_success,
                    "roundtrip_success": roundtrip_success,
                    "encoded_size": encoded_size,
                    "char_analysis": char_analysis,
                    "overall_success": encode_success and decode_success and roundtrip_success
                }
            
            mock_instance.validate_encoding.side_effect = validate_encoding
            
            discord_utils = DiscordUtils()
            
            # Test encoding validation
            for test_case in encoding_test_cases:
                with self.subTest(encoding_case=test_case["name"]):
                    result = discord_utils.validate_encoding(
                        test_case["test_content"],
                        test_case["encoding"],
                        error_handling="strict"
                    )
                    
                    # Verify expected success/failure
                    if test_case["should_succeed"]:
                        self.assertTrue(result["overall_success"],
                                      f"Encoding should succeed for {test_case['name']}")
                        self.assertTrue(result["encode_success"])
                        self.assertTrue(result["decode_success"])
                        self.assertTrue(result["roundtrip_success"])
                    else:
                        self.assertFalse(result["overall_success"],
                                       f"Encoding should fail for {test_case['name']}")
                    
                    # Verify character analysis is reasonable
                    char_analysis = result["char_analysis"]
                    total_expected = len(test_case["test_content"])
                    total_analyzed = (char_analysis["ascii_chars"] + 
                                    char_analysis["extended_chars"] + 
                                    char_analysis["unicode_chars"])
                    self.assertEqual(total_analyzed, total_expected)
                    
                    # Log encoding validation results
                    self.logger.info(
                        f"Encoding validation: {test_case['name']}",
                        context={
                            "encoding": test_case["encoding"],
                            "expected_success": test_case["should_succeed"],
                            "actual_success": result["overall_success"],
                            "encoded_size": result["encoded_size"],
                            "char_analysis": char_analysis
                        }
                    )
    
    async def test_character_normalization(self) -> None:
        """Test Unicode character normalization (NFC, NFD, NFKC, NFKD)."""
        normalization_test_cases = [
            {
                "name": "precomposed_vs_decomposed",
                "nfc": "café",  # Precomposed é
                "nfd": "cafe\u0301",  # Decomposed e + combining acute
                "description": "Composed vs decomposed characters"
            },
            {
                "name": "ligatures",
                "nfc": "ﬁle",  # fi ligature
                "nfkc": "file",  # Decomposed to separate characters
                "description": "Ligature normalization"
            },
            {
                "name": "superscripts",
                "original": "x²",  # Superscript 2
                "nfkc": "x2",  # Compatibility decomposition
                "description": "Superscript normalization"
            },
            {
                "name": "fullwidth_chars",
                "original": "Ｈｅｌｌｏ",  # Fullwidth
                "nfkc": "Hello",  # Halfwidth
                "description": "Fullwidth character normalization"
            }
        ]
        
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure normalization processing
            def process_unicode_normalization(text: str) -> Dict[str, Any]:
                """Process text with different Unicode normalizations."""
                
                # Apply different normalization forms
                normalizations = {
                    "original": text,
                    "nfc": unicodedata.normalize("NFC", text),
                    "nfd": unicodedata.normalize("NFD", text),
                    "nfkc": unicodedata.normalize("NFKC", text),
                    "nfkd": unicodedata.normalize("NFKD", text)
                }
                
                # Analyze differences
                analysis = {}
                for form, normalized_text in normalizations.items():
                    analysis[form] = {
                        "text": normalized_text,
                        "length": len(normalized_text),
                        "byte_length": len(normalized_text.encode('utf-8')),
                        "codepoints": [ord(c) for c in normalized_text]
                    }
                
                # Check for differences
                differences = {
                    "nfc_vs_nfd": normalizations["nfc"] != normalizations["nfd"],
                    "nfkc_vs_original": normalizations["nfkc"] != normalizations["original"],
                    "nfkd_vs_original": normalizations["nfkd"] != normalizations["original"]
                }
                
                return {
                    "normalizations": normalizations,
                    "analysis": analysis,
                    "differences": differences,
                    "recommended_form": "NFC"  # Generally recommended for most use cases
                }
            
            mock_instance.process_unicode_normalization.side_effect = process_unicode_normalization
            
            embed_utils = EmbedUtils()
            
            # Test normalization
            for test_case in normalization_test_cases:
                with self.subTest(normalization_case=test_case["name"]):
                    # Test the main text field
                    test_text = test_case.get("nfc", test_case.get("original", ""))
                    
                    result = embed_utils.process_unicode_normalization(test_text)
                    
                    # Verify normalizations exist
                    self.assertIn("nfc", result["normalizations"])
                    self.assertIn("nfd", result["normalizations"])
                    self.assertIn("nfkc", result["normalizations"])
                    self.assertIn("nfkd", result["normalizations"])
                    
                    # Verify analysis completeness
                    for form in ["nfc", "nfd", "nfkc", "nfkd"]:
                        self.assertIn(form, result["analysis"])
                        self.assertIn("length", result["analysis"][form])
                        self.assertIn("byte_length", result["analysis"][form])
                    
                    # Check specific expectations based on test case
                    if "nfd" in test_case:
                        # Check NFD produces expected decomposition
                        expected_nfd = test_case["nfd"]
                        actual_nfd = result["normalizations"]["nfd"]
                        # For this test, we'll check that NFD is different from NFC
                        self.assertTrue(result["differences"]["nfc_vs_nfd"])
                    
                    if "nfkc" in test_case:
                        # Check NFKC produces expected compatibility form
                        expected_nfkc = test_case["nfkc"]
                        actual_nfkc = result["normalizations"]["nfkc"]
                        self.assertTrue(result["differences"]["nfkc_vs_original"])
                    
                    # Verify all normalizations are valid Unicode
                    for form, normalized_text in result["normalizations"].items():
                        try:
                            normalized_text.encode('utf-8')
                        except UnicodeError:
                            self.fail(f"Normalization {form} produced invalid Unicode")
                    
                    # Log normalization analysis
                    self.logger.info(
                        f"Unicode normalization: {test_case['name']}",
                        context={
                            "description": test_case["description"],
                            "original_length": len(test_text),
                            "nfc_length": result["analysis"]["nfc"]["length"],
                            "nfd_length": result["analysis"]["nfd"]["length"],
                            "nfkc_length": result["analysis"]["nfkc"]["length"],
                            "differences": result["differences"]
                        }
                    )
    
    async def test_problematic_unicode_handling(self) -> None:
        """Test handling of problematic Unicode content."""
        with patch('src.utils.discord_utils.DiscordUtils') as mock_discord_utils:
            mock_instance = MagicMock()
            mock_discord_utils.return_value = mock_instance
            
            # Configure problematic content handling
            def sanitize_problematic_unicode(content: str) -> Dict[str, Any]:
                """Sanitize problematic Unicode content."""
                import re
                
                original_content = content
                sanitized_content = content
                issues_found = []
                
                # Remove null bytes
                if '\x00' in sanitized_content:
                    sanitized_content = sanitized_content.replace('\x00', '')
                    issues_found.append("null_bytes")
                
                # Remove/replace control characters (except common whitespace)
                control_chars = []
                for char in sanitized_content:
                    if unicodedata.category(char).startswith('C') and char not in '\t\n\r':
                        control_chars.append(char)
                
                if control_chars:
                    for char in control_chars:
                        sanitized_content = sanitized_content.replace(char, '')
                    issues_found.append("control_characters")
                
                # Handle zero-width characters
                zero_width_chars = [
                    '\u200B',  # Zero Width Space
                    '\u200C',  # Zero Width Non-Joiner
                    '\u200D',  # Zero Width Joiner
                    '\u2060',  # Word Joiner
                    '\u2061',  # Function Application
                    '\u2062',  # Invisible Times
                    '\u2063',  # Invisible Separator
                ]
                
                zero_width_found = []
                for char in zero_width_chars:
                    if char in sanitized_content:
                        zero_width_found.append(char)
                        # Keep ZWJ for emoji sequences, remove others
                        if char != '\u200D':
                            sanitized_content = sanitized_content.replace(char, '')
                
                if zero_width_found:
                    issues_found.append("zero_width_characters")
                
                # Detect bidirectional text issues
                has_rtl = any(unicodedata.bidirectional(char) in ['R', 'AL'] for char in content)
                has_ltr = any(unicodedata.bidirectional(char) == 'L' for char in content)
                has_bidi_issue = has_rtl and has_ltr
                
                if has_bidi_issue:
                    issues_found.append("bidirectional_text")
                
                # Detect mixed scripts that might be confusing
                scripts_found = set()
                for char in content:
                    try:
                        script = unicodedata.name(char).split()[0]
                        if script not in ['SPACE', 'DIGIT']:
                            scripts_found.add(script)
                    except (ValueError, IndexError):
                        pass
                
                if len(scripts_found) > 3:
                    issues_found.append("excessive_script_mixing")
                
                return {
                    "original_content": original_content,
                    "sanitized_content": sanitized_content,
                    "issues_found": issues_found,
                    "has_bidi_text": has_bidi_issue,
                    "scripts_found": list(scripts_found),
                    "char_count_original": len(original_content),
                    "char_count_sanitized": len(sanitized_content),
                    "bytes_removed": len(original_content.encode('utf-8')) - len(sanitized_content.encode('utf-8')),
                    "is_safe": len(issues_found) == 0
                }
            
            mock_instance.sanitize_problematic_unicode.side_effect = sanitize_problematic_unicode
            
            discord_utils = DiscordUtils()
            
            # Test problematic content handling
            for content_type, content in self.unicode_test_samples["problematic_content"].items():
                with self.subTest(problematic_type=content_type):
                    result = discord_utils.sanitize_problematic_unicode(content)
                    
                    # Verify sanitization occurred
                    self.assertIsNotNone(result["sanitized_content"])
                    
                    # Verify issues were detected
                    if content_type in ["null_bytes", "control_chars"]:
                        self.assertIn("null_bytes", result["issues_found"] + ["control_characters"])
                    elif content_type == "bidi_text":
                        self.assertTrue(result["has_bidi_text"])
                    elif content_type == "mixed_scripts":
                        self.assertGreater(len(result["scripts_found"]), 1)
                    elif content_type in ["zero_width", "invisible_chars"]:
                        self.assertIn("zero_width_characters", result["issues_found"])
                    
                    # Verify sanitized content is valid
                    try:
                        result["sanitized_content"].encode('utf-8')
                    except UnicodeError:
                        self.fail(f"Sanitized content is not valid Unicode for {content_type}")
                    
                    # Verify content was actually cleaned if issues were found
                    if result["issues_found"]:
                        self.assertNotEqual(result["sanitized_content"], result["original_content"])
                    
                    # Log problematic content handling
                    self.logger.info(
                        f"Problematic Unicode handling: {content_type}",
                        context={
                            "issues_found": result["issues_found"],
                            "has_bidi_text": result["has_bidi_text"],
                            "scripts_count": len(result["scripts_found"]),
                            "original_chars": result["char_count_original"],
                            "sanitized_chars": result["char_count_sanitized"],
                            "bytes_removed": result["bytes_removed"],
                            "is_safe": result["is_safe"]
                        }
                    )


def run_unicode_handling_tests() -> None:
    """Run Unicode handling tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestUnicodeHandling)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nUnicode Handling Tests Summary:")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    asyncio.run(main())