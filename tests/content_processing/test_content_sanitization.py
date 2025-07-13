#!/usr/bin/env python3
"""Test Content Sanitization Functionality.

This module provides comprehensive tests for content sanitization functionality,
including XSS prevention, injection attack mitigation, malicious content filtering,
data validation, and safe content processing.
"""

import asyncio
import base64
import html
import json
import re
import time
import unittest
import urllib.parse
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
from src.utils.validation import ContentValidator
from src.formatters.embed_utils import EmbedUtils


class TestContentSanitization(unittest.IsolatedAsyncioTestCase):
    """Test cases for content sanitization functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Malicious content test samples
        self.malicious_content_samples = {
            "xss_attempts": {
                "basic_script": "<script>alert('XSS')</script>",
                "script_with_attributes": '<script type="text/javascript">window.location="http://evil.com"</script>',
                "img_onerror": '<img src="x" onerror="alert(\'XSS\')">',
                "svg_script": '<svg onload="alert(\'XSS\')">',
                "iframe_injection": '<iframe src="javascript:alert(\'XSS\')"></iframe>',
                "event_handlers": '<div onclick="alert(\'XSS\')" onmouseover="steal_cookies()">Click me</div>',
                "javascript_urls": '<a href="javascript:alert(\'XSS\')">Click here</a>',
                "data_urls": '<a href="data:text/html,<script>alert(\'XSS\')</script>">Link</a>',
                "encoded_scripts": '&lt;script&gt;alert(\'XSS\')&lt;/script&gt;',
                "unicode_encoded": '\\u003cscript\\u003ealert(\'XSS\')\\u003c/script\\u003e'
            },
            "injection_attempts": {
                "sql_injection": "'; DROP TABLE users; --",
                "nosql_injection": '{"$where": "function(){return true;}"}',
                "command_injection": "; rm -rf /; #",
                "ldap_injection": "*)(uid=*))(|(uid=*",
                "xpath_injection": "' or 1=1 or ''='",
                "template_injection": "{{7*7}}[[7*7]]${7*7}#",
                "ssti_python": "{{config.items()}}",
                "ssti_jinja2": "{{''.__class__.__mro__[2].__subclasses__()[40]('/etc/passwd').read()}}",
                "path_traversal": "../../../etc/passwd",
                "null_byte": "file.txt\x00.jpg"
            },
            "malicious_urls": {
                "javascript_protocol": "javascript:alert('XSS')",
                "data_protocol": "data:text/html,<script>alert('XSS')</script>",
                "vbscript_protocol": "vbscript:msgbox('XSS')",
                "file_protocol": "file:///etc/passwd",
                "suspicious_domains": "http://evil-site.com/steal.php",
                "ip_addresses": "http://192.168.1.1/malware.exe",
                "shortened_urls": "http://bit.ly/suspicious",
                "unicode_domains": "http://еxample.com",  # Cyrillic characters
                "homograph_attack": "http://goog1e.com",
                "encoded_urls": "http://example.com/%2e%2e%2f%2e%2e%2f"
            },
            "data_exfiltration": {
                "base64_encoded": base64.b64encode(b"sensitive_data_here").decode(),
                "hex_encoded": "73656e73697469766520646174612068657265",
                "url_encoded": urllib.parse.quote("SELECT * FROM users WHERE password='admin'"),
                "unicode_escape": "\\u0053\\u0045\\u004c\\u0045\\u0043\\u0054",
                "rot13": "FRYRPG * SEBZ hfref JURER cnffjbeq='nqzva'",
                "hidden_content": "<!--SECRET_API_KEY=abc123xyz789-->"
            },
            "content_manipulation": {
                "html_entities": "&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;",
                "mixed_encoding": "%3Cscript%3Ealert('XSS')%3C/script%3E",
                "case_variations": "<ScRiPt>alert('XSS')</ScRiPt>",
                "whitespace_evasion": "< script >alert('XSS')< /script >",
                "comment_evasion": "<script>/*comment*/alert('XSS')/*comment*/</script>",
                "attribute_breaking": '<img """><script>alert(\'XSS\')</script>">',
                "null_byte_evasion": "<script\x00>alert('XSS')</script>",
                "newline_evasion": "<script\nalert('XSS')\n</script>"
            }
        }
        
        # Safe content samples for testing false positives
        self.safe_content_samples = {
            "legitimate_code": {
                "python_code": 'print("Hello, World!")\nfor i in range(10):\n    print(i)',
                "javascript_code": 'console.log("Debug message");\nvar x = 5;',
                "html_content": '<p>This is a <strong>legitimate</strong> HTML paragraph.</p>',
                "json_data": '{"name": "John", "age": 30, "city": "New York"}',
                "markdown": '# Header\n\n**Bold text** and *italic text*\n\n```python\nprint("code")\n```',
                "sql_query": 'SELECT name, email FROM users WHERE active = 1',
                "regex_pattern": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                "url_examples": 'Visit https://example.com for more information'
            },
            "user_content": {
                "comments": "This is a great article! Thanks for sharing.",
                "feedback": "The tool works well, but could use better error messages.",
                "descriptions": "A comprehensive solution for automated testing and deployment.",
                "file_paths": "/home/user/documents/project/main.py",
                "commands": "python manage.py migrate --fake-initial",
                "error_messages": "Error: Connection timeout after 30 seconds",
                "log_entries": "[2025-07-12 22:00:00] INFO: Processing request from 192.168.1.100"
            }
        }
        
        # Sanitization configurations
        self.sanitization_configs = {
            "strict": {
                "allow_html": False,
                "allow_scripts": False,
                "allow_external_urls": False,
                "max_length": 1000,
                "encoding": "strict"
            },
            "moderate": {
                "allow_html": True,
                "allow_scripts": False,
                "allow_external_urls": True,
                "max_length": 5000,
                "encoding": "permissive",
                "allowed_tags": ["p", "br", "strong", "em", "a", "code"]
            },
            "permissive": {
                "allow_html": True,
                "allow_scripts": False,
                "allow_external_urls": True,
                "max_length": 10000,
                "encoding": "permissive",
                "allowed_tags": ["*"],
                "allowed_attributes": ["href", "src", "alt", "title"]
            }
        }
    
    async def test_xss_prevention(self) -> None:
        """Test XSS (Cross-Site Scripting) prevention."""
        with patch('src.utils.validation.ContentValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure XSS prevention
            def sanitize_against_xss(content: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
                """Sanitize content against XSS attacks."""
                config = config or self.sanitization_configs["strict"]
                
                original_content = content
                sanitized_content = content
                threats_detected = []
                
                # Detect and remove script tags
                script_patterns = [
                    r'<\s*script[^>]*>.*?<\s*/\s*script\s*>',
                    r'<\s*script[^>]*>.*',
                    r'javascript\s*:',
                    r'vbscript\s*:',
                    r'data\s*:.*text/html',
                ]
                
                for pattern in script_patterns:
                    if re.search(pattern, sanitized_content, re.IGNORECASE | re.DOTALL):
                        threats_detected.append(f"script_injection_{pattern[:20]}")
                        sanitized_content = re.sub(pattern, '[REMOVED_SCRIPT]', sanitized_content, flags=re.IGNORECASE | re.DOTALL)
                
                # Detect and remove event handlers
                event_patterns = [
                    r'on\w+\s*=\s*["\'][^"\']*["\']',
                    r'on\w+\s*=\s*[^>\s]+',
                ]
                
                for pattern in event_patterns:
                    if re.search(pattern, sanitized_content, re.IGNORECASE):
                        threats_detected.append(f"event_handler_{pattern[:20]}")
                        sanitized_content = re.sub(pattern, '[REMOVED_EVENT]', sanitized_content, flags=re.IGNORECASE)
                
                # Handle HTML entities and encoding
                if not config.get("allow_html", False):
                    # Escape HTML
                    sanitized_content = html.escape(sanitized_content)
                    if '<' in original_content or '>' in original_content:
                        threats_detected.append("html_content")
                
                # Detect dangerous tags
                dangerous_tags = ['script', 'iframe', 'object', 'embed', 'applet', 'meta', 'link']
                for tag in dangerous_tags:
                    pattern = f'<\s*{tag}[^>]*>'
                    if re.search(pattern, sanitized_content, re.IGNORECASE):
                        threats_detected.append(f"dangerous_tag_{tag}")
                        sanitized_content = re.sub(pattern, f'[REMOVED_{tag.upper()}]', sanitized_content, flags=re.IGNORECASE)
                
                # Check for encoded malicious content
                encoded_patterns = [
                    r'&lt;script&gt;',
                    r'\\u003c.*script.*\\u003e',
                    r'%3Cscript%3E',
                ]
                
                for pattern in encoded_patterns:
                    if re.search(pattern, sanitized_content, re.IGNORECASE):
                        threats_detected.append(f"encoded_script_{pattern[:15]}")
                        sanitized_content = re.sub(pattern, '[REMOVED_ENCODED]', sanitized_content, flags=re.IGNORECASE)
                
                return {
                    "original_content": original_content,
                    "sanitized_content": sanitized_content,
                    "threats_detected": threats_detected,
                    "is_safe": len(threats_detected) == 0,
                    "content_modified": sanitized_content != original_content,
                    "sanitization_level": "xss_prevention"
                }
            
            mock_instance.sanitize_against_xss.side_effect = sanitize_against_xss
            
            validator = ContentValidator()
            
            # Test XSS prevention
            for category, samples in self.malicious_content_samples["xss_attempts"].items():
                with self.subTest(xss_type=category):
                    result = validator.sanitize_against_xss(samples, self.sanitization_configs["strict"])
                    
                    # Verify threat detection
                    self.assertGreater(len(result["threats_detected"]), 0,
                                     f"XSS threat not detected in {category}")
                    self.assertFalse(result["is_safe"],
                                   f"XSS content marked as safe: {category}")
                    self.assertTrue(result["content_modified"],
                                  f"XSS content not modified: {category}")
                    
                    # Verify dangerous content is removed/escaped
                    sanitized = result["sanitized_content"]
                    self.assertNotIn("<script", sanitized.lower())
                    self.assertNotIn("javascript:", sanitized.lower())
                    self.assertNotIn("onerror=", sanitized.lower())
                    
                    # Log XSS prevention results
                    self.logger.info(
                        f"XSS prevention: {category}",
                        context={
                            "threats_detected": result["threats_detected"],
                            "original_length": len(result["original_content"]),
                            "sanitized_length": len(result["sanitized_content"]),
                            "is_safe": result["is_safe"]
                        }
                    )
            
            # Test false positives with safe content
            for category, safe_content in self.safe_content_samples["legitimate_code"].items():
                with self.subTest(safe_content_type=category):
                    result = validator.sanitize_against_xss(safe_content, self.sanitization_configs["moderate"])
                    
                    # Should have minimal or no threats for legitimate content
                    if result["threats_detected"]:
                        # Some legitimate code might trigger warnings, but should not be overly aggressive
                        self.assertLessEqual(len(result["threats_detected"]), 2,
                                           f"Too many false positives for {category}")
    
    async def test_injection_attack_mitigation(self) -> None:
        """Test mitigation of various injection attacks."""
        with patch('src.utils.validation.ContentValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure injection prevention
            def prevent_injection_attacks(content: str, attack_types: List[str] = None) -> Dict[str, Any]:
                """Prevent various types of injection attacks."""
                attack_types = attack_types or ["sql", "nosql", "command", "ldap", "xpath", "template"]
                
                original_content = content
                sanitized_content = content
                injection_threats = []
                
                # SQL Injection patterns
                if "sql" in attack_types:
                    sql_patterns = [
                        r"('|(\\))|(;)|(--)|(\||(\*|((\%27)|(')|(\%2527)|('))",
                        r"((\%3D)|(=))[^\n]*((\%27)|(')|(\%3D)|(\%2527))",
                        r"((\%27)|(')|(\%3D))[^\n]*((\%3B)|(;))",
                        r"union.*select|select.*from|drop.*table|insert.*into|delete.*from",
                        r"or\s+1\s*=\s*1|and\s+1\s*=\s*1",
                    ]
                    
                    for pattern in sql_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            injection_threats.append(f"sql_injection_{pattern[:20]}")
                            sanitized_content = re.sub(pattern, '[SQL_FILTERED]', sanitized_content, flags=re.IGNORECASE)
                
                # NoSQL Injection patterns
                if "nosql" in attack_types:
                    nosql_patterns = [
                        r'\$where.*function',
                        r'\$gt.*\$lt',
                        r'\$ne.*null',
                        r'this\..*==',
                    ]
                    
                    for pattern in nosql_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            injection_threats.append(f"nosql_injection_{pattern[:20]}")
                            sanitized_content = re.sub(pattern, '[NOSQL_FILTERED]', sanitized_content, flags=re.IGNORECASE)
                
                # Command Injection patterns
                if "command" in attack_types:
                    command_patterns = [
                        r'[;&|`\$\(\)]',
                        r'rm\s+-rf',
                        r'cat\s+/etc/passwd',
                        r'wget\s+http',
                        r'curl\s+http',
                        r'nc\s+-l',
                    ]
                    
                    for pattern in command_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            injection_threats.append(f"command_injection_{pattern[:20]}")
                            sanitized_content = re.sub(pattern, '[CMD_FILTERED]', sanitized_content, flags=re.IGNORECASE)
                
                # Template Injection patterns
                if "template" in attack_types:
                    template_patterns = [
                        r'\{\{.*\}\}',
                        r'\[\[.*\]\]',
                        r'\$\{.*\}',
                        r'#\{.*\}',
                        r'<%.*%>',
                    ]
                    
                    for pattern in template_patterns:
                        if re.search(pattern, content):
                            injection_threats.append(f"template_injection_{pattern[:20]}")
                            sanitized_content = re.sub(pattern, '[TEMPLATE_FILTERED]', sanitized_content)
                
                # Path Traversal patterns
                path_traversal_patterns = [
                    r'\.\./\.\./\.\.',
                    r'\.\.\\\.\.\\\.\.\\',
                    r'%2e%2e%2f',
                    r'%2e%2e%5c',
                ]
                
                for pattern in path_traversal_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        injection_threats.append(f"path_traversal_{pattern[:20]}")
                        sanitized_content = re.sub(pattern, '[PATH_FILTERED]', sanitized_content, flags=re.IGNORECASE)
                
                return {
                    "original_content": original_content,
                    "sanitized_content": sanitized_content,
                    "injection_threats": injection_threats,
                    "is_safe": len(injection_threats) == 0,
                    "content_modified": sanitized_content != original_content,
                    "attack_types_checked": attack_types
                }
            
            mock_instance.prevent_injection_attacks.side_effect = prevent_injection_attacks
            
            validator = ContentValidator()
            
            # Test injection prevention
            for category, malicious_content in self.malicious_content_samples["injection_attempts"].items():
                with self.subTest(injection_type=category):
                    result = validator.prevent_injection_attacks(malicious_content)
                    
                    # Verify injection threats are detected
                    self.assertGreater(len(result["injection_threats"]), 0,
                                     f"Injection threat not detected in {category}")
                    self.assertFalse(result["is_safe"],
                                   f"Injection content marked as safe: {category}")
                    
                    # Verify content is sanitized
                    if result["content_modified"]:
                        sanitized = result["sanitized_content"]
                        self.assertIn("FILTERED", sanitized,
                                    f"Expected filtering markers in {category}")
                    
                    # Log injection prevention results
                    self.logger.info(
                        f"Injection prevention: {category}",
                        context={
                            "injection_threats": result["injection_threats"],
                            "attack_types_checked": result["attack_types_checked"],
                            "content_modified": result["content_modified"],
                            "is_safe": result["is_safe"]
                        }
                    )
    
    async def test_malicious_url_filtering(self) -> None:
        """Test filtering of malicious URLs."""
        with patch('src.utils.validation.ContentValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure URL filtering
            def filter_malicious_urls(content: str, strict_mode: bool = True) -> Dict[str, Any]:
                """Filter malicious URLs from content."""
                
                original_content = content
                sanitized_content = content
                url_threats = []
                
                # URL patterns
                url_pattern = r'https?://[^\s<>"\']+|ftp://[^\s<>"\']+|javascript:[^\s<>"\']+|data:[^\s<>"\']*'
                urls_found = re.findall(url_pattern, content, re.IGNORECASE)
                
                for url in urls_found:
                    threats_in_url = []
                    
                    # Check for dangerous protocols
                    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:', 'about:']
                    for protocol in dangerous_protocols:
                        if url.lower().startswith(protocol):
                            threats_in_url.append(f"dangerous_protocol_{protocol}")
                    
                    # Check for suspicious domains
                    suspicious_patterns = [
                        r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
                        r'bit\.ly|tinyurl\.com|t\.co',  # URL shorteners (potentially suspicious)
                        r'[а-я]',  # Cyrillic characters (potential homograph attack)
                        r'[1l0o]',  # Common character substitutions in domain names
                    ]
                    
                    for pattern in suspicious_patterns:
                        if re.search(pattern, url, re.IGNORECASE):
                            threats_in_url.append(f"suspicious_domain_{pattern[:15]}")
                    
                    # Check for encoded content
                    if '%' in url and strict_mode:
                        try:
                            decoded_url = urllib.parse.unquote(url)
                            if decoded_url != url:
                                # Check if decoded URL contains dangerous patterns
                                if any(dangerous in decoded_url.lower() for dangerous in ['<script', 'javascript:', '../']):
                                    threats_in_url.append("url_encoding_evasion")
                        except Exception:
                            threats_in_url.append("url_decode_error")
                    
                    # If threats found, handle the URL
                    if threats_in_url:
                        url_threats.extend(threats_in_url)
                        if strict_mode:
                            sanitized_content = sanitized_content.replace(url, '[FILTERED_URL]')
                        else:
                            sanitized_content = sanitized_content.replace(url, f'[WARNING: Suspicious URL - {url[:20]}...]')
                
                return {
                    "original_content": original_content,
                    "sanitized_content": sanitized_content,
                    "url_threats": url_threats,
                    "urls_found": urls_found,
                    "is_safe": len(url_threats) == 0,
                    "content_modified": sanitized_content != original_content,
                    "strict_mode": strict_mode
                }
            
            mock_instance.filter_malicious_urls.side_effect = filter_malicious_urls
            
            validator = ContentValidator()
            
            # Test malicious URL filtering
            for category, malicious_url in self.malicious_content_samples["malicious_urls"].items():
                with self.subTest(url_type=category):
                    # Test in strict mode
                    result = validator.filter_malicious_urls(malicious_url, strict_mode=True)
                    
                    # Verify URL threats are detected
                    self.assertGreater(len(result["url_threats"]), 0,
                                     f"URL threat not detected in {category}")
                    self.assertFalse(result["is_safe"],
                                   f"Malicious URL marked as safe: {category}")
                    
                    # Verify URLs are found
                    self.assertGreater(len(result["urls_found"]), 0,
                                     f"No URLs found in {category}")
                    
                    # In strict mode, dangerous URLs should be filtered
                    if result["strict_mode"] and result["content_modified"]:
                        self.assertIn("FILTERED", result["sanitized_content"])
                    
                    # Log URL filtering results
                    self.logger.info(
                        f"URL filtering: {category}",
                        context={
                            "url_threats": result["url_threats"],
                            "urls_found": len(result["urls_found"]),
                            "content_modified": result["content_modified"],
                            "is_safe": result["is_safe"]
                        }
                    )
            
            # Test legitimate URLs (should not be filtered)
            legitimate_urls = [
                "https://github.com/user/repo",
                "https://docs.python.org/3/",
                "http://localhost:8000/api/v1/",
                "https://example.com/page?param=value",
            ]
            
            for url in legitimate_urls:
                with self.subTest(legitimate_url=url):
                    result = validator.filter_malicious_urls(url, strict_mode=True)
                    
                    # Legitimate URLs should generally be safe
                    # (Some might trigger warnings but should not be filtered)
                    if not result["is_safe"]:
                        # If marked as unsafe, it should be a warning, not filtered
                        self.assertNotIn("FILTERED_URL", result["sanitized_content"])
    
    async def test_data_validation_and_sanitization(self) -> None:
        """Test data validation and sanitization."""
        with patch('src.utils.validation.ContentValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure data validation
            def validate_and_sanitize_data(data: Any, data_type: str = "text") -> Dict[str, Any]:
                """Validate and sanitize different types of data."""
                
                validation_result = {
                    "original_data": data,
                    "sanitized_data": data,
                    "data_type": data_type,
                    "validation_errors": [],
                    "sanitization_applied": [],
                    "is_valid": True,
                    "is_safe": True
                }
                
                if data_type == "text":
                    # Text validation
                    if not isinstance(data, str):
                        validation_result["validation_errors"].append("not_string")
                        validation_result["is_valid"] = False
                        return validation_result
                    
                    # Check for null bytes
                    if '\x00' in data:
                        validation_result["sanitization_applied"].append("null_bytes_removed")
                        validation_result["sanitized_data"] = data.replace('\x00', '')
                        validation_result["is_safe"] = False
                    
                    # Check for control characters
                    control_chars = [c for c in data if ord(c) < 32 and c not in '\t\n\r']
                    if control_chars:
                        validation_result["sanitization_applied"].append("control_chars_removed")
                        for char in control_chars:
                            validation_result["sanitized_data"] = validation_result["sanitized_data"].replace(char, '')
                        validation_result["is_safe"] = False
                    
                    # Check for excessively long content
                    if len(data) > 10000:
                        validation_result["validation_errors"].append("content_too_long")
                        validation_result["sanitized_data"] = data[:10000] + "...[truncated]"
                        validation_result["sanitization_applied"].append("length_truncation")
                        validation_result["is_valid"] = False
                
                elif data_type == "json":
                    # JSON validation
                    try:
                        if isinstance(data, str):
                            parsed_data = json.loads(data)
                            validation_result["sanitized_data"] = json.dumps(parsed_data, ensure_ascii=True)
                        else:
                            validation_result["sanitized_data"] = json.dumps(data, ensure_ascii=True)
                    except json.JSONDecodeError as e:
                        validation_result["validation_errors"].append(f"invalid_json: {str(e)}")
                        validation_result["is_valid"] = False
                        validation_result["sanitized_data"] = str(data)
                
                elif data_type == "base64":
                    # Base64 validation
                    try:
                        if isinstance(data, str):
                            decoded = base64.b64decode(data, validate=True)
                            # Check if decoded content is safe
                            decoded_str = decoded.decode('utf-8', errors='ignore')
                            if '<script' in decoded_str.lower() or 'javascript:' in decoded_str.lower():
                                validation_result["validation_errors"].append("malicious_base64_content")
                                validation_result["is_safe"] = False
                        else:
                            validation_result["validation_errors"].append("not_string")
                            validation_result["is_valid"] = False
                    except Exception as e:
                        validation_result["validation_errors"].append(f"invalid_base64: {str(e)}")
                        validation_result["is_valid"] = False
                
                elif data_type == "url":
                    # URL validation
                    try:
                        parsed = urllib.parse.urlparse(str(data))
                        if not parsed.scheme or not parsed.netloc:
                            validation_result["validation_errors"].append("invalid_url_format")
                            validation_result["is_valid"] = False
                        elif parsed.scheme not in ['http', 'https', 'ftp']:
                            validation_result["validation_errors"].append("unsafe_url_scheme")
                            validation_result["is_safe"] = False
                    except Exception:
                        validation_result["validation_errors"].append("url_parse_error")
                        validation_result["is_valid"] = False
                
                return validation_result
            
            mock_instance.validate_and_sanitize_data.side_effect = validate_and_sanitize_data
            
            validator = ContentValidator()
            
            # Test data validation for malicious content
            test_cases = [
                {
                    "data": self.malicious_content_samples["data_exfiltration"]["base64_encoded"],
                    "type": "base64",
                    "should_be_safe": True  # Base64 itself should be valid
                },
                {
                    "data": "SELECT * FROM users; DROP TABLE users;",
                    "type": "text",
                    "should_be_safe": True  # Text should be valid but might trigger other checks
                },
                {
                    "data": '{"malicious": "<script>alert(\'XSS\')</script>"}',
                    "type": "json",
                    "should_be_safe": True  # Valid JSON
                },
                {
                    "data": "javascript:alert('XSS')",
                    "type": "url",
                    "should_be_safe": False  # Unsafe URL scheme
                },
                {
                    "data": "text with null\x00byte",
                    "type": "text",
                    "should_be_safe": False  # Contains null byte
                },
                {
                    "data": "text with control\x01char",
                    "type": "text",
                    "should_be_safe": False  # Contains control character
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                with self.subTest(test_case_index=i):
                    result = validator.validate_and_sanitize_data(
                        test_case["data"], 
                        test_case["type"]
                    )
                    
                    # Verify validation
                    self.assertIsNotNone(result["sanitized_data"])
                    
                    # Check safety expectation
                    if not test_case["should_be_safe"]:
                        self.assertFalse(result["is_safe"] and len(result["validation_errors"]) == 0,
                                       f"Expected unsafe data to be detected: {test_case['data'][:50]}")
                    
                    # Verify sanitization was applied if needed
                    if not result["is_safe"] or result["validation_errors"]:
                        self.assertTrue(
                            len(result["sanitization_applied"]) > 0 or 
                            result["sanitized_data"] != result["original_data"],
                            "Expected sanitization to be applied"
                        )
                    
                    # Log validation results
                    self.logger.info(
                        f"Data validation: {test_case['type']}",
                        context={
                            "data_type": result["data_type"],
                            "is_valid": result["is_valid"],
                            "is_safe": result["is_safe"],
                            "validation_errors": result["validation_errors"],
                            "sanitization_applied": result["sanitization_applied"]
                        }
                    )
    
    async def test_safe_content_processing(self) -> None:
        """Test processing of safe content without false positives."""
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure safe content processing
            def process_safe_content(content: str, processing_level: str = "standard") -> Dict[str, Any]:
                """Process safe content while minimizing false positives."""
                
                original_content = content
                processed_content = content
                warnings = []
                modifications = []
                
                # Apply minimal processing for safe content
                if processing_level == "strict":
                    # In strict mode, even safe content might get some processing
                    
                    # Escape HTML entities in code examples
                    if '<' in content and '>' in content:
                        # But check if it's likely code documentation
                        if any(keyword in content.lower() for keyword in ['example:', 'code:', '```', 'function', 'class']):
                            warnings.append("html_in_code_context")
                        else:
                            processed_content = html.escape(content)
                            modifications.append("html_escaped")
                    
                    # Check for URLs but be lenient with documentation
                    if 'http' in content.lower():
                        if 'documentation' in content.lower() or 'docs.' in content.lower():
                            warnings.append("documentation_url")
                        else:
                            warnings.append("external_url")
                
                elif processing_level == "standard":
                    # Standard processing - very minimal for safe content
                    
                    # Only process obviously dangerous patterns
                    if '<script' in content.lower():
                        processed_content = content.replace('<script', '&lt;script')
                        modifications.append("script_tag_escaped")
                    
                elif processing_level == "lenient":
                    # Lenient processing - almost no changes for safe content
                    pass
                
                return {
                    "original_content": original_content,
                    "processed_content": processed_content,
                    "processing_level": processing_level,
                    "warnings": warnings,
                    "modifications": modifications,
                    "content_preserved": processed_content == original_content,
                    "false_positive_risk": len(warnings) + len(modifications)
                }
            
            mock_instance.process_safe_content.side_effect = process_safe_content
            
            embed_utils = EmbedUtils()
            
            # Test safe content processing with different levels
            processing_levels = ["strict", "standard", "lenient"]
            
            for level in processing_levels:
                for category, safe_samples in self.safe_content_samples.items():
                    for sample_name, safe_content in safe_samples.items():
                        with self.subTest(level=level, category=category, sample=sample_name):
                            result = embed_utils.process_safe_content(safe_content, processing_level=level)
                            
                            # Verify content processing
                            self.assertIsNotNone(result["processed_content"])
                            
                            # Check for excessive false positives
                            false_positive_score = result["false_positive_risk"]
                            
                            if level == "lenient":
                                # Lenient mode should have minimal changes
                                self.assertLessEqual(false_positive_score, 1,
                                                   f"Too many modifications in lenient mode for {sample_name}")
                            elif level == "standard":
                                # Standard mode should be balanced
                                self.assertLessEqual(false_positive_score, 3,
                                                   f"Too many modifications in standard mode for {sample_name}")
                            elif level == "strict":
                                # Strict mode can have more changes but should still be reasonable
                                self.assertLessEqual(false_positive_score, 5,
                                                   f"Too many modifications in strict mode for {sample_name}")
                            
                            # For legitimate code, content should generally be preserved
                            if category == "legitimate_code" and level != "strict":
                                # Code should generally be preserved unless in strict mode
                                if not result["content_preserved"]:
                                    self.assertLessEqual(len(result["modifications"]), 2,
                                                       f"Too many modifications to legitimate code: {sample_name}")
                            
                            # Log safe content processing
                            self.logger.info(
                                f"Safe content processing: {level}/{category}/{sample_name}",
                                context={
                                    "processing_level": level,
                                    "content_preserved": result["content_preserved"],
                                    "warnings": len(result["warnings"]),
                                    "modifications": len(result["modifications"]),
                                    "false_positive_risk": false_positive_score
                                }
                            )
    
    async def test_comprehensive_sanitization_pipeline(self) -> None:
        """Test comprehensive sanitization pipeline combining all methods."""
        with patch('src.utils.validation.ContentValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure comprehensive sanitization
            def comprehensive_sanitize(content: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
                """Comprehensive sanitization pipeline."""
                config = config or self.sanitization_configs["moderate"]
                
                pipeline_results = {
                    "original_content": content,
                    "final_content": content,
                    "stages": [],
                    "total_threats": 0,
                    "is_safe": True,
                    "config_used": config
                }
                
                current_content = content
                
                # Stage 1: XSS Prevention
                xss_result = {
                    "stage": "xss_prevention",
                    "threats_found": 0,
                    "content_modified": False
                }
                
                # Basic XSS detection
                xss_patterns = [r'<script.*?</script>', r'javascript:', r'on\w+\s*=']
                for pattern in xss_patterns:
                    if re.search(pattern, current_content, re.IGNORECASE):
                        xss_result["threats_found"] += 1
                        current_content = re.sub(pattern, '[XSS_REMOVED]', current_content, flags=re.IGNORECASE)
                        xss_result["content_modified"] = True
                
                pipeline_results["stages"].append(xss_result)
                pipeline_results["total_threats"] += xss_result["threats_found"]
                
                # Stage 2: Injection Prevention
                injection_result = {
                    "stage": "injection_prevention",
                    "threats_found": 0,
                    "content_modified": False
                }
                
                injection_patterns = [r"';.*drop.*table", r"\|\||\|\&", r"\$\{.*\}"]
                for pattern in injection_patterns:
                    if re.search(pattern, current_content, re.IGNORECASE):
                        injection_result["threats_found"] += 1
                        current_content = re.sub(pattern, '[INJECTION_REMOVED]', current_content, flags=re.IGNORECASE)
                        injection_result["content_modified"] = True
                
                pipeline_results["stages"].append(injection_result)
                pipeline_results["total_threats"] += injection_result["threats_found"]
                
                # Stage 3: URL Filtering
                url_result = {
                    "stage": "url_filtering",
                    "threats_found": 0,
                    "content_modified": False
                }
                
                dangerous_protocols = ['javascript:', 'data:', 'vbscript:']
                for protocol in dangerous_protocols:
                    if protocol in current_content.lower():
                        url_result["threats_found"] += 1
                        current_content = current_content.replace(protocol, '[URL_REMOVED]')
                        url_result["content_modified"] = True
                
                pipeline_results["stages"].append(url_result)
                pipeline_results["total_threats"] += url_result["threats_found"]
                
                # Stage 4: Data Validation
                validation_result = {
                    "stage": "data_validation",
                    "threats_found": 0,
                    "content_modified": False
                }
                
                # Check for null bytes and control characters
                if '\x00' in current_content:
                    validation_result["threats_found"] += 1
                    current_content = current_content.replace('\x00', '')
                    validation_result["content_modified"] = True
                
                control_chars = [c for c in current_content if ord(c) < 32 and c not in '\t\n\r']
                if control_chars:
                    validation_result["threats_found"] += 1
                    for char in control_chars:
                        current_content = current_content.replace(char, '')
                    validation_result["content_modified"] = True
                
                pipeline_results["stages"].append(validation_result)
                pipeline_results["total_threats"] += validation_result["threats_found"]
                
                # Stage 5: Length and Format Validation
                format_result = {
                    "stage": "format_validation",
                    "threats_found": 0,
                    "content_modified": False
                }
                
                max_length = config.get("max_length", 5000)
                if len(current_content) > max_length:
                    format_result["threats_found"] += 1
                    current_content = current_content[:max_length] + "...[truncated]"
                    format_result["content_modified"] = True
                
                pipeline_results["stages"].append(format_result)
                pipeline_results["total_threats"] += format_result["threats_found"]
                
                # Final assessment
                pipeline_results["final_content"] = current_content
                pipeline_results["is_safe"] = pipeline_results["total_threats"] == 0
                pipeline_results["content_modified"] = current_content != content
                
                return pipeline_results
            
            mock_instance.comprehensive_sanitize.side_effect = comprehensive_sanitize
            
            validator = ContentValidator()
            
            # Test comprehensive sanitization on various content types
            test_cases = [
                {
                    "name": "clean_content",
                    "content": "This is normal, safe content for testing.",
                    "expected_threats": 0
                },
                {
                    "name": "mixed_threats",
                    "content": '<script>alert("XSS")</script> and ; DROP TABLE users; and javascript:alert("more XSS")',
                    "expected_threats": 3  # XSS, SQL injection, malicious URL
                },
                {
                    "name": "encoded_threats",
                    "content": "Content with null\x00byte and control\x01char",
                    "expected_threats": 2  # Null byte and control char
                },
                {
                    "name": "legitimate_code_sample",
                    "content": 'function example() {\n    console.log("Hello World");\n    return true;\n}',
                    "expected_threats": 0
                }
            ]
            
            for test_case in test_cases:
                with self.subTest(test_name=test_case["name"]):
                    result = validator.comprehensive_sanitize(
                        test_case["content"], 
                        self.sanitization_configs["moderate"]
                    )
                    
                    # Verify pipeline execution
                    self.assertEqual(len(result["stages"]), 5, "All sanitization stages should execute")
                    
                    # Verify threat detection accuracy
                    if test_case["expected_threats"] == 0:
                        self.assertEqual(result["total_threats"], 0,
                                       f"Expected no threats in {test_case['name']}")
                        self.assertTrue(result["is_safe"],
                                     f"Expected content to be safe: {test_case['name']}")
                    else:
                        self.assertGreaterEqual(result["total_threats"], 1,
                                              f"Expected threats in {test_case['name']}")
                        self.assertFalse(result["is_safe"],
                                       f"Expected content to be unsafe: {test_case['name']}")
                    
                    # Verify sanitization effectiveness
                    if result["total_threats"] > 0:
                        sanitized = result["final_content"]
                        # Should not contain common threat patterns
                        self.assertNotRegex(sanitized, r'<script.*?</script>', 
                                          "Script tags should be removed")
                        self.assertNotIn("javascript:", sanitized.lower(),
                                       "JavaScript URLs should be removed")
                    
                    # Log comprehensive sanitization results
                    self.logger.info(
                        f"Comprehensive sanitization: {test_case['name']}",
                        context={
                            "total_threats": result["total_threats"],
                            "expected_threats": test_case["expected_threats"],
                            "is_safe": result["is_safe"],
                            "content_modified": result["content_modified"],
                            "stages": [stage["stage"] for stage in result["stages"]],
                            "threats_by_stage": {stage["stage"]: stage["threats_found"] for stage in result["stages"]}
                        }
                    )


def run_content_sanitization_tests() -> None:
    """Run content sanitization tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestContentSanitization)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nContent Sanitization Tests Summary:")
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