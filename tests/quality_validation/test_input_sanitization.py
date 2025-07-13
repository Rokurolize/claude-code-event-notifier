#!/usr/bin/env python3
"""Test Input Sanitization Functionality.

This module provides comprehensive tests for input sanitization functionality,
including XSS prevention, SQL injection prevention, path traversal protection,
command injection prevention, and general input validation security.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import sys
import re
import html
import urllib.parse
import base64
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.utils.validation import sanitize_content, validate_unicode
from src.validators import validate_event_data, validate_config
from src.type_defs.discord import DiscordMessage, DiscordEmbed, DiscordField
from src.formatters.base import BaseFormatter
from src.exceptions import ValidationError, SecurityError


# Attack vector types
@dataclass
class AttackVector:
    """Attack vector configuration."""
    name: str
    category: str
    payload: str
    expected_sanitized: str
    should_block: bool = False
    severity: str = "medium"
    description: str = ""


@dataclass
class SanitizationResult:
    """Result of sanitization operation."""
    original_input: str
    sanitized_output: str
    blocked: bool = False
    vulnerabilities_found: List[str] = field(default_factory=list)
    sanitization_steps: List[str] = field(default_factory=list)
    confidence_score: float = 1.0


class InputSanitizer(Protocol):
    """Protocol for input sanitizers."""
    def sanitize(self, input_data: str, context: Dict[str, Any]) -> SanitizationResult:
        """Sanitize input and return result."""
        ...
    
    def detect_attack(self, input_data: str) -> Optional[AttackVector]:
        """Detect potential attack vectors."""
        ...


class TestInputSanitization(unittest.IsolatedAsyncioTestCase):
    """Test cases for input sanitization functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "sanitization_mode": "strict",
            "block_malicious": True,
            "encode_special_chars": True,
            "validate_unicode": True,
            "prevent_injections": True,
            "debug": True
        }
        
        # Common attack vectors
        self.attack_vectors = [
            # XSS attacks
            AttackVector(
                name="basic_xss",
                category="xss",
                payload="<script>alert('XSS')</script>",
                expected_sanitized="&lt;script&gt;alert('XSS')&lt;/script&gt;",
                severity="high",
                description="Basic XSS with script tag"
            ),
            AttackVector(
                name="img_xss",
                category="xss",
                payload='<img src="x" onerror="alert(1)">',
                expected_sanitized='&lt;img src="x" onerror="alert(1)"&gt;',
                severity="high",
                description="XSS via img tag"
            ),
            AttackVector(
                name="javascript_url",
                category="xss",
                payload='<a href="javascript:alert(1)">Click</a>',
                expected_sanitized='&lt;a href="javascript:alert(1)"&gt;Click&lt;/a&gt;',
                severity="high",
                description="XSS via javascript URL"
            ),
            
            # SQL injection
            AttackVector(
                name="basic_sqli",
                category="sqli",
                payload="'; DROP TABLE users; --",
                expected_sanitized="''; DROP TABLE users; --",
                should_block=True,
                severity="critical",
                description="Basic SQL injection"
            ),
            AttackVector(
                name="union_sqli",
                category="sqli",
                payload="1' UNION SELECT * FROM passwords--",
                expected_sanitized="1'' UNION SELECT * FROM passwords--",
                should_block=True,
                severity="critical",
                description="UNION-based SQL injection"
            ),
            
            # Path traversal
            AttackVector(
                name="basic_path_traversal",
                category="path_traversal",
                payload="../../../etc/passwd",
                expected_sanitized="etc/passwd",
                should_block=True,
                severity="high",
                description="Basic path traversal"
            ),
            AttackVector(
                name="encoded_path_traversal",
                category="path_traversal",
                payload="..%2F..%2F..%2Fetc%2Fpasswd",
                expected_sanitized="etc/passwd",
                should_block=True,
                severity="high",
                description="URL-encoded path traversal"
            ),
            
            # Command injection
            AttackVector(
                name="basic_cmd_injection",
                category="cmd_injection",
                payload="; rm -rf /",
                expected_sanitized="rm -rf /",
                should_block=True,
                severity="critical",
                description="Basic command injection"
            ),
            AttackVector(
                name="backtick_cmd_injection",
                category="cmd_injection",
                payload="`cat /etc/passwd`",
                expected_sanitized="cat /etc/passwd",
                should_block=True,
                severity="critical",
                description="Backtick command injection"
            ),
            
            # Unicode attacks
            AttackVector(
                name="unicode_normalization",
                category="unicode",
                payload="ﬁle",  # Unicode ligature
                expected_sanitized="file",
                severity="low",
                description="Unicode normalization attack"
            ),
            AttackVector(
                name="rtl_override",
                category="unicode",
                payload="test\u202Egnp.exe",  # Right-to-left override
                expected_sanitized="test[RLO]gnp.exe",
                severity="medium",
                description="Right-to-left override attack"
            )
        ]
    
    async def test_xss_prevention(self) -> None:
        """Test XSS attack prevention."""
        xss_vectors = [v for v in self.attack_vectors if v.category == "xss"]
        
        for vector in xss_vectors:
            with self.subTest(vector=vector.name):
                # Test sanitization
                result = self._sanitize_input(vector.payload, {"context": "discord_message"})
                
                # Verify XSS prevention
                self.assertNotIn("<script", result.sanitized_output)
                self.assertNotIn("javascript:", result.sanitized_output)
                self.assertNotIn("onerror=", result.sanitized_output)
                
                # Check for proper encoding
                if "<" in vector.payload:
                    self.assertIn("&lt;", result.sanitized_output)
                if ">" in vector.payload:
                    self.assertIn("&gt;", result.sanitized_output)
                
                # Log sanitization
                self.logger.info(
                    "xss_prevention_test",
                    attack_type="xss",
                    vector=vector.name,
                    original=vector.payload,
                    sanitized=result.sanitized_output,
                    blocked=result.blocked
                )
    
    async def test_sql_injection_prevention(self) -> None:
        """Test SQL injection prevention."""
        sqli_vectors = [v for v in self.attack_vectors if v.category == "sqli"]
        
        for vector in sqli_vectors:
            with self.subTest(vector=vector.name):
                # Test sanitization
                result = self._sanitize_input(vector.payload, {"context": "database_query"})
                
                # Verify SQL injection prevention
                if vector.should_block:
                    self.assertTrue(result.blocked)
                else:
                    # Check quote escaping
                    self.assertNotIn("'", result.sanitized_output.replace("''", ""))
                    self.assertNotIn('"', result.sanitized_output.replace('""', ""))
                
                # Check for dangerous keywords
                dangerous_keywords = ["DROP", "DELETE", "UNION", "SELECT", "--"]
                if not result.blocked:
                    for keyword in dangerous_keywords:
                        if keyword in vector.payload.upper():
                            self.assertIn("sqli", result.vulnerabilities_found)
    
    async def test_path_traversal_prevention(self) -> None:
        """Test path traversal attack prevention."""
        path_vectors = [v for v in self.attack_vectors if v.category == "path_traversal"]
        
        for vector in path_vectors:
            with self.subTest(vector=vector.name):
                # Test sanitization
                result = self._sanitize_input(vector.payload, {"context": "file_path"})
                
                # Verify path traversal prevention
                self.assertNotIn("..", result.sanitized_output)
                self.assertNotIn("../", result.sanitized_output)
                self.assertNotIn("..\\", result.sanitized_output)
                
                # Check URL decoding handled
                self.assertNotIn("%2F", result.sanitized_output)
                self.assertNotIn("%5C", result.sanitized_output)
                
                # Should be blocked or sanitized
                if vector.should_block:
                    self.assertTrue(result.blocked)
    
    async def test_command_injection_prevention(self) -> None:
        """Test command injection prevention."""
        cmd_vectors = [v for v in self.attack_vectors if v.category == "cmd_injection"]
        
        for vector in cmd_vectors:
            with self.subTest(vector=vector.name):
                # Test sanitization
                result = self._sanitize_input(vector.payload, {"context": "shell_command"})
                
                # Verify command injection prevention
                dangerous_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">"]
                
                if vector.should_block:
                    self.assertTrue(result.blocked)
                else:
                    for char in dangerous_chars:
                        if char in vector.payload:
                            self.assertNotIn(char, result.sanitized_output)
    
    async def test_unicode_security(self) -> None:
        """Test Unicode-based attack prevention."""
        unicode_vectors = [v for v in self.attack_vectors if v.category == "unicode"]
        
        for vector in unicode_vectors:
            with self.subTest(vector=vector.name):
                # Test sanitization
                result = self._sanitize_input(vector.payload, {"context": "user_input"})
                
                # Verify Unicode security
                # Check for dangerous Unicode characters
                dangerous_unicode = [
                    "\u202E",  # Right-to-left override
                    "\u202D",  # Left-to-right override
                    "\u202A",  # Left-to-right embedding
                    "\u202B",  # Right-to-left embedding
                    "\u202C",  # Pop directional formatting
                    "\u200E",  # Left-to-right mark
                    "\u200F",  # Right-to-left mark
                ]
                
                for char in dangerous_unicode:
                    if char in vector.payload:
                        self.assertNotIn(char, result.sanitized_output)
    
    async def test_discord_specific_sanitization(self) -> None:
        """Test Discord-specific input sanitization."""
        discord_inputs = [
            # Discord markdown injection
            {
                "input": "**bold** *italic* __underline__",
                "expected_markdown": True,
                "should_preserve": True
            },
            # Discord mention injection
            {
                "input": "<@123456789> <@&987654321> <#456789123>",
                "expected_mentions": True,
                "should_validate": True
            },
            # Discord emoji injection
            {
                "input": ":smile: <:custom:123456789>",
                "expected_emojis": True,
                "should_validate": True
            },
            # Malicious Discord formatting
            {
                "input": "```\nmalicious code\n```\n<script>alert(1)</script>",
                "expected_code_block": True,
                "should_sanitize_html": True
            }
        ]
        
        for test_case in discord_inputs:
            result = self._sanitize_discord_input(test_case["input"])
            
            # Verify Discord-specific handling
            if test_case.get("should_sanitize_html"):
                self.assertNotIn("<script", result.sanitized_output)
            
            if test_case.get("should_validate"):
                # Validate Discord IDs
                mention_pattern = r'<@!?\d+>|<@&\d+>|<#\d+>'
                mentions = re.findall(mention_pattern, test_case["input"])
                for mention in mentions:
                    # Extract ID and validate
                    id_match = re.search(r'\d+', mention)
                    if id_match:
                        discord_id = id_match.group()
                        self.assertTrue(discord_id.isdigit())
                        self.assertTrue(len(discord_id) >= 17)  # Discord IDs are snowflakes
    
    async def test_multi_layer_attacks(self) -> None:
        """Test multi-layered attack prevention."""
        complex_attacks = [
            # XSS + SQL injection
            {
                "payload": "'; <script>alert(document.cookie)</script>--",
                "expected_blocks": ["xss", "sqli"]
            },
            # Path traversal + command injection
            {
                "payload": "../../../bin/sh; cat /etc/passwd",
                "expected_blocks": ["path_traversal", "cmd_injection"]
            },
            # Unicode + XSS
            {
                "payload": "\u202E<script>alert(1)</script>",
                "expected_blocks": ["unicode", "xss"]
            },
            # Encoded multi-layer
            {
                "payload": base64.b64encode(b"<script>alert(1)</script>").decode(),
                "expected_blocks": ["encoding"]
            }
        ]
        
        for attack in complex_attacks:
            result = self._sanitize_input(attack["payload"], {"context": "multi_context"})
            
            # Should detect multiple attack types
            detected_types = set()
            for vuln in result.vulnerabilities_found:
                for expected in attack["expected_blocks"]:
                    if expected in vuln.lower():
                        detected_types.add(expected)
            
            # Verify all expected attack types detected
            for expected_type in attack["expected_blocks"]:
                self.assertIn(
                    expected_type,
                    detected_types,
                    f"Failed to detect {expected_type} in multi-layer attack"
                )
    
    async def test_sanitization_performance(self) -> None:
        """Test sanitization performance impact."""
        import time
        
        # Large input test
        large_input = "A" * 10000 + "<script>alert(1)</script>" + "B" * 10000
        
        # Measure sanitization time
        start_time = time.time()
        result = self._sanitize_input(large_input, {"context": "performance_test"})
        sanitization_time = time.time() - start_time
        
        # Performance assertions
        self.assertLess(sanitization_time, 0.1)  # Should complete within 100ms
        self.assertIn("&lt;script&gt;", result.sanitized_output)
        
        # Ensure no exponential regex issues
        regex_bomb = "a" * 100 + "X" + "a" * 100
        start_time = time.time()
        result = self._sanitize_input(regex_bomb, {"context": "regex_test"})
        regex_time = time.time() - start_time
        
        self.assertLess(regex_time, 0.01)  # Should be very fast
    
    async def test_edge_cases(self) -> None:
        """Test edge case handling."""
        edge_cases = [
            # Empty input
            {"input": "", "expected": ""},
            # Only whitespace
            {"input": "   \n\t\r   ", "expected": "   \n\t\r   "},
            # Null bytes
            {"input": "test\x00value", "expected": "testvalue"},
            # Very long input
            {"input": "A" * 100000, "expected_length": 100000},
            # Mixed encodings
            {"input": "test\u00e9\u00e8", "expected_contains": "test"},
            # Control characters
            {"input": "test\x1b[31mred\x1b[0m", "expected": "test[31mred[0m"}
        ]
        
        for case in edge_cases:
            result = self._sanitize_input(case["input"], {"context": "edge_case"})
            
            if "expected" in case:
                self.assertEqual(result.sanitized_output, case["expected"])
            elif "expected_length" in case:
                self.assertEqual(len(result.sanitized_output), case["expected_length"])
            elif "expected_contains" in case:
                self.assertIn(case["expected_contains"], result.sanitized_output)
    
    def _sanitize_input(self, input_data: str, context: Dict[str, Any]) -> SanitizationResult:
        """Sanitize input based on context."""
        result = SanitizationResult(
            original_input=input_data,
            sanitized_output=input_data
        )
        
        # HTML encoding
        if any(char in input_data for char in ["<", ">", "&", '"', "'"]):
            result.sanitized_output = html.escape(result.sanitized_output)
            result.sanitization_steps.append("html_escape")
        
        # SQL injection prevention
        if context.get("context") == "database_query":
            if any(keyword in input_data.upper() for keyword in ["DROP", "DELETE", "UNION", "SELECT"]):
                result.blocked = True
                result.vulnerabilities_found.append("sqli")
                return result
            result.sanitized_output = result.sanitized_output.replace("'", "''")
            result.sanitization_steps.append("sql_escape")
        
        # Path traversal prevention
        if context.get("context") == "file_path":
            if ".." in input_data:
                result.blocked = True
                result.vulnerabilities_found.append("path_traversal")
                return result
            result.sanitized_output = result.sanitized_output.replace("../", "").replace("..\\", "")
            result.sanitization_steps.append("path_normalization")
        
        # Command injection prevention
        if context.get("context") == "shell_command":
            dangerous_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">"]
            if any(char in input_data for char in dangerous_chars):
                result.blocked = True
                result.vulnerabilities_found.append("cmd_injection")
                return result
        
        # Unicode security
        dangerous_unicode = ["\u202E", "\u202D", "\u202A", "\u202B", "\u202C"]
        for char in dangerous_unicode:
            if char in result.sanitized_output:
                result.sanitized_output = result.sanitized_output.replace(char, f"[{ord(char):04X}]")
                result.vulnerabilities_found.append("unicode_control_char")
                result.sanitization_steps.append("unicode_sanitization")
        
        # Null byte removal
        if "\x00" in result.sanitized_output:
            result.sanitized_output = result.sanitized_output.replace("\x00", "")
            result.sanitization_steps.append("null_byte_removal")
        
        return result
    
    def _sanitize_discord_input(self, input_data: str) -> SanitizationResult:
        """Sanitize Discord-specific input."""
        result = self._sanitize_input(input_data, {"context": "discord"})
        
        # Additional Discord-specific sanitization
        # Validate mention IDs
        mention_pattern = r'<@!?(\d+)>|<@&(\d+)>|<#(\d+)>'
        
        def validate_mention(match):
            discord_id = match.group(1) or match.group(2) or match.group(3)
            if discord_id and len(discord_id) >= 17:  # Valid snowflake
                return match.group(0)
            else:
                result.vulnerabilities_found.append("invalid_discord_id")
                return "[INVALID_MENTION]"
        
        result.sanitized_output = re.sub(mention_pattern, validate_mention, result.sanitized_output)
        
        return result


if __name__ == "__main__":
    unittest.main()