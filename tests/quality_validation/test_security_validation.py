#!/usr/bin/env python3
"""Test Security Validation Functionality.

This module provides comprehensive tests for security validation functionality,
including authentication, authorization, API key protection, sensitive data handling,
vulnerability scanning, and security best practices enforcement.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, PropertyMock
import sys
import re
import hashlib
import hmac
import base64
import secrets
import os
import tempfile
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.core.config import ConfigManager
from src.exceptions import SecurityError, AuthenticationError, AuthorizationError
from src.type_defs.config import ConfigDict, DiscordConfig
from src.validators import validate_discord_webhook_url, validate_config
from src.core.http_client import HTTPClient


# Security test types
@dataclass
class SecurityVulnerability:
    """Security vulnerability description."""
    name: str
    severity: str  # critical, high, medium, low
    category: str
    description: str
    cwe_id: Optional[str] = None
    remediation: Optional[str] = None
    false_positive: bool = False


@dataclass
class SecurityScanResult:
    """Result of security scan."""
    passed: bool
    vulnerabilities: List[SecurityVulnerability] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scan_time: float = 0.0
    confidence_score: float = 1.0


@dataclass
class CredentialCheck:
    """Credential security check."""
    credential_type: str
    location: str
    exposed: bool
    severity: str
    recommendation: str


class SecurityValidator(Protocol):
    """Protocol for security validators."""
    def validate_authentication(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate authentication configuration."""
        ...
    
    def scan_for_vulnerabilities(self, code_path: Path) -> SecurityScanResult:
        """Scan for security vulnerabilities."""
        ...
    
    def check_credentials(self, content: str) -> List[CredentialCheck]:
        """Check for exposed credentials."""
        ...


class TestSecurityValidation(unittest.IsolatedAsyncioTestCase):
    """Test cases for security validation functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.temp_dir = tempfile.mkdtemp()
        
        # Test configuration
        self.test_config = {
            "security_mode": "strict",
            "validate_auth": True,
            "scan_credentials": True,
            "enforce_https": True,
            "validate_permissions": True,
            "debug": True
        }
        
        # Common security patterns
        self.credential_patterns = {
            "discord_token": re.compile(r'[A-Za-z0-9_\-]{24}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27}'),
            "discord_webhook": re.compile(r'https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_\-]+'),
            "api_key": re.compile(r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([A-Za-z0-9_\-]+)["\']?'),
            "password": re.compile(r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'),
            "secret": re.compile(r'(?i)(secret|private[_-]?key)\s*[:=]\s*["\']?([A-Za-z0-9_\-]+)["\']?'),
            "aws_key": re.compile(r'AKIA[0-9A-Z]{16}'),
            "github_token": re.compile(r'ghp_[A-Za-z0-9]{36}'),
            "base64_cred": re.compile(r'(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?')
        }
    
    async def test_authentication_validation(self) -> None:
        """Test authentication configuration validation."""
        test_configs = [
            # Valid webhook auth
            {
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/abc123"
                },
                "expected_valid": True,
                "auth_type": "webhook"
            },
            # Valid bot token auth
            {
                "config": {
                    "DISCORD_TOKEN": "TEST_TOKEN_INVALID",
                    "DISCORD_CHANNEL_ID": "123456789012345678"
                },
                "expected_valid": True,
                "auth_type": "bot"
            },
            # Missing auth
            {
                "config": {},
                "expected_valid": False,
                "auth_type": "none"
            },
            # Invalid webhook URL
            {
                "config": {
                    "DISCORD_WEBHOOK_URL": "http://discord.com/api/webhooks/123/abc"
                },
                "expected_valid": False,
                "auth_type": "webhook",
                "security_issue": "insecure_protocol"
            },
            # Exposed token in config
            {
                "config": {
                    "DISCORD_TOKEN": "EXPOSED_TOKEN_IN_CONFIG",
                    "TOKEN_SOURCE": "hardcoded"
                },
                "expected_valid": False,
                "auth_type": "bot",
                "security_issue": "hardcoded_credential"
            }
        ]
        
        for test_case in test_configs:
            with self.subTest(auth_type=test_case["auth_type"]):
                valid, issues = self._validate_authentication(test_case["config"])
                
                self.assertEqual(valid, test_case["expected_valid"])
                
                if test_case.get("security_issue"):
                    self.assertTrue(
                        any(test_case["security_issue"] in issue for issue in issues),
                        f"Expected security issue '{test_case['security_issue']}' not found"
                    )
    
    async def test_api_key_protection(self) -> None:
        """Test API key protection mechanisms."""
        # Test environment variable usage
        with patch.dict(os.environ, {"DISCORD_TOKEN": "test-token"}):
            config = ConfigManager().load_config()
            
            # Token should be loaded from env
            self.assertIsNotNone(config.get("DISCORD_TOKEN"))
            
            # Token should not be logged
            with patch('src.utils.astolfo_logger.AstolfoLogger.info') as mock_log:
                self._log_config(config)
                
                # Check logs don't contain token
                for call in mock_log.call_args_list:
                    log_content = str(call)
                    self.assertNotIn("test-token", log_content)
                    self.assertIn("[REDACTED]", log_content)
        
        # Test token masking in errors
        try:
            raise SecurityError("Invalid token: test-token-value")
        except SecurityError as e:
            error_msg = self._sanitize_error_message(str(e))
            self.assertNotIn("test-token-value", error_msg)
            self.assertIn("[REDACTED]", error_msg)
    
    async def test_credential_scanning(self) -> None:
        """Test credential scanning in code."""
        test_files = [
            # File with exposed Discord token
            {
                "filename": "test_exposed_token.py",
                "content": '''
DISCORD_TOKEN = "TEST_TOKEN_INVALID"
                ''',
                "expected_vulnerabilities": ["discord_token_exposure"]
            },
            # File with hardcoded webhook
            {
                "filename": "test_webhook.py",
                "content": '''
webhook_url = "https://discord.com/api/webhooks/123456789/abcdefghijklmnop"
                ''',
                "expected_vulnerabilities": ["discord_webhook_exposure"]
            },
            # File with API key
            {
                "filename": "test_api_key.py",
                "content": '''
api_key = "sk-1234567890abcdefghijklmnop"
API_KEY = "1234567890abcdefghijklmnop"
                ''',
                "expected_vulnerabilities": ["api_key_exposure"]
            },
            # Safe file with env usage
            {
                "filename": "test_safe.py",
                "content": '''
import os
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
                ''',
                "expected_vulnerabilities": []
            }
        ]
        
        for test_file in test_files:
            # Write test file
            file_path = Path(self.temp_dir) / test_file["filename"]
            file_path.write_text(test_file["content"])
            
            # Scan for credentials
            scan_result = self._scan_file_for_credentials(file_path)
            
            # Verify expected vulnerabilities
            found_vulns = [v.name for v in scan_result.vulnerabilities]
            for expected_vuln in test_file["expected_vulnerabilities"]:
                self.assertIn(
                    expected_vuln,
                    found_vulns,
                    f"Expected vulnerability '{expected_vuln}' not found in {test_file['filename']}"
                )
    
    async def test_https_enforcement(self) -> None:
        """Test HTTPS enforcement for external connections."""
        test_urls = [
            # Valid HTTPS URLs
            ("https://discord.com/api/webhooks/123/abc", True),
            ("https://api.discord.com/v10/channels/123", True),
            
            # Invalid HTTP URLs
            ("http://discord.com/api/webhooks/123/abc", False),
            ("http://api.discord.com/v10/channels/123", False),
            
            # Mixed content
            ("https://example.com/redirect?url=http://discord.com", False),
        ]
        
        for url, expected_secure in test_urls:
            with self.subTest(url=url):
                is_secure, issue = self._validate_url_security(url)
                self.assertEqual(is_secure, expected_secure)
                
                if not expected_secure:
                    self.assertIsNotNone(issue)
                    self.assertIn("insecure", issue.lower())
    
    async def test_permission_validation(self) -> None:
        """Test permission and access control validation."""
        # Test file permissions
        test_file = Path(self.temp_dir) / "test_permissions.txt"
        test_file.write_text("test content")
        
        # Check file permissions
        file_mode = test_file.stat().st_mode & 0o777
        
        # File should not be world-writable
        self.assertFalse(file_mode & 0o002, "File is world-writable")
        
        # Test directory permissions
        test_dir = Path(self.temp_dir) / "secure_dir"
        test_dir.mkdir(mode=0o700)
        
        dir_mode = test_dir.stat().st_mode & 0o777
        self.assertEqual(dir_mode, 0o700, "Directory should have secure permissions")
    
    async def test_injection_prevention(self) -> None:
        """Test injection attack prevention."""
        injection_tests = [
            # SQL injection attempt
            {
                "input": "'; DROP TABLE threads; --",
                "context": "database",
                "should_block": True
            },
            # Command injection attempt
            {
                "input": "; rm -rf /",
                "context": "shell",
                "should_block": True
            },
            # Path traversal attempt
            {
                "input": "../../../etc/passwd",
                "context": "file_path",
                "should_block": True
            },
            # JSON injection attempt
            {
                "input": '{"key": "value", "injected": true}',
                "context": "json_field",
                "should_block": False  # Valid JSON
            }
        ]
        
        for test in injection_tests:
            result = self._validate_input_security(
                test["input"],
                test["context"]
            )
            
            if test["should_block"]:
                self.assertFalse(result.is_safe)
                self.assertTrue(result.vulnerabilities)
            else:
                self.assertTrue(result.is_safe)
    
    async def test_sensitive_data_handling(self) -> None:
        """Test handling of sensitive data."""
        sensitive_data = {
            "discord_token": "TEST_TOKEN_INVALID",
            "user_id": "123456789012345678",
            "session_id": "session_abc123def456",
            "api_response": {"id": "123", "token": "secret123"}
        }
        
        # Test data masking
        masked_data = self._mask_sensitive_data(sensitive_data)
        
        # Verify masking
        self.assertIn("[REDACTED]", masked_data["discord_token"])
        self.assertNotIn("1234567890abcdefghijklmnop", str(masked_data))
        self.assertEqual(masked_data["user_id"], "123456789012345678")  # IDs are safe
        self.assertIn("[REDACTED]", masked_data["api_response"]["token"])
    
    async def test_cryptographic_security(self) -> None:
        """Test cryptographic security measures."""
        # Test secure random generation
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)
        self.assertNotEqual(token1, token2)
        self.assertGreaterEqual(len(token1), 32)
        
        # Test HMAC signature
        secret_key = b"test_secret_key"
        message = b"test_message"
        
        signature = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
        
        # Verify signature
        expected_sig = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
        self.assertEqual(signature, expected_sig)
        
        # Test constant-time comparison
        self.assertTrue(hmac.compare_digest(signature, expected_sig))
        self.assertFalse(hmac.compare_digest(signature, "wrong_signature"))
    
    async def test_security_headers_validation(self) -> None:
        """Test security headers in HTTP responses."""
        mock_response = {
            "headers": {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": "default-src 'self'"
            }
        }
        
        # Validate security headers
        validation_result = self._validate_security_headers(mock_response["headers"])
        
        self.assertTrue(validation_result.passed)
        self.assertFalse(validation_result.vulnerabilities)
        
        # Test missing headers
        insecure_response = {"headers": {}}
        validation_result = self._validate_security_headers(insecure_response["headers"])
        
        self.assertFalse(validation_result.passed)
        self.assertTrue(validation_result.vulnerabilities)
    
    async def test_rate_limiting_security(self) -> None:
        """Test rate limiting for security."""
        # Simulate rapid requests
        request_times = []
        max_requests = 10
        time_window = 1.0  # 1 second
        
        for i in range(max_requests + 5):
            current_time = datetime.now(timezone.utc).timestamp()
            
            # Check if rate limit exceeded
            recent_requests = [
                t for t in request_times 
                if current_time - t < time_window
            ]
            
            if len(recent_requests) >= max_requests:
                # Should be rate limited
                self.assertGreaterEqual(len(recent_requests), max_requests)
                break
            else:
                request_times.append(current_time)
        
        # Verify rate limiting triggered
        self.assertGreater(len(request_times), max_requests)
    
    async def test_vulnerability_scanning(self) -> None:
        """Test comprehensive vulnerability scanning."""
        # Scan project for vulnerabilities
        scan_result = self._scan_project_security(Path(project_root / "src"))
        
        # Check for critical vulnerabilities
        critical_vulns = [
            v for v in scan_result.vulnerabilities 
            if v.severity == "critical"
        ]
        
        # No critical vulnerabilities should exist
        self.assertEqual(
            len(critical_vulns), 
            0,
            f"Found critical vulnerabilities: {[v.name for v in critical_vulns]}"
        )
        
        # Log scan results
        self.logger.info(
            "security_scan_complete",
            total_vulnerabilities=len(scan_result.vulnerabilities),
            critical=len([v for v in scan_result.vulnerabilities if v.severity == "critical"]),
            high=len([v for v in scan_result.vulnerabilities if v.severity == "high"]),
            medium=len([v for v in scan_result.vulnerabilities if v.severity == "medium"]),
            low=len([v for v in scan_result.vulnerabilities if v.severity == "low"])
        )
    
    def _validate_authentication(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate authentication configuration."""
        issues = []
        
        # Check for authentication presence
        has_webhook = "DISCORD_WEBHOOK_URL" in config
        has_bot_token = "DISCORD_TOKEN" in config and "DISCORD_CHANNEL_ID" in config
        
        if not has_webhook and not has_bot_token:
            issues.append("no_authentication_configured")
            return False, issues
        
        # Validate webhook URL
        if has_webhook:
            webhook_url = config["DISCORD_WEBHOOK_URL"]
            if not webhook_url.startswith("https://"):
                issues.append("insecure_protocol")
            if not validate_discord_webhook_url(webhook_url):
                issues.append("invalid_webhook_format")
        
        # Check for hardcoded credentials
        if config.get("TOKEN_SOURCE") == "hardcoded":
            issues.append("hardcoded_credential")
        
        return len(issues) == 0, issues
    
    def _scan_file_for_credentials(self, file_path: Path) -> SecurityScanResult:
        """Scan file for exposed credentials."""
        result = SecurityScanResult(passed=True)
        
        try:
            content = file_path.read_text()
            
            # Check each credential pattern
            for cred_type, pattern in self.credential_patterns.items():
                matches = pattern.findall(content)
                if matches:
                    # Check if it's actually exposed (not from env)
                    for match in matches:
                        line_with_match = next(
                            (line for line in content.split('\n') if str(match) in line),
                            ""
                        )
                        
                        # Skip if loading from environment
                        if any(env_func in line_with_match for env_func in ["os.getenv", "os.environ", "getenv"]):
                            continue
                        
                        # Found exposed credential
                        result.passed = False
                        result.vulnerabilities.append(
                            SecurityVulnerability(
                                name=f"{cred_type}_exposure",
                                severity="critical" if "token" in cred_type else "high",
                                category="credential_exposure",
                                description=f"Exposed {cred_type} found in {file_path.name}",
                                cwe_id="CWE-798",
                                remediation="Use environment variables to store sensitive credentials"
                            )
                        )
        except Exception as e:
            result.warnings.append(f"Error scanning file: {str(e)}")
        
        return result
    
    def _validate_url_security(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL security."""
        if not url.startswith("https://"):
            return False, "URL must use HTTPS protocol"
        
        # Check for HTTP in query parameters
        if "http://" in url:
            return False, "URL contains insecure HTTP reference"
        
        return True, None
    
    def _validate_input_security(self, input_data: str, context: str) -> Any:
        """Validate input for security issues."""
        class Result:
            is_safe = True
            vulnerabilities = []
        
        result = Result()
        
        if context == "database":
            # Check for SQL injection patterns
            sql_patterns = ["DROP", "DELETE", "INSERT", "UPDATE", "--", "/*", "*/"]
            if any(pattern in input_data.upper() for pattern in sql_patterns):
                result.is_safe = False
                result.vulnerabilities.append("sql_injection")
        
        elif context == "shell":
            # Check for command injection
            shell_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">"]
            if any(char in input_data for char in shell_chars):
                result.is_safe = False
                result.vulnerabilities.append("command_injection")
        
        elif context == "file_path":
            # Check for path traversal
            if ".." in input_data or input_data.startswith("/"):
                result.is_safe = False
                result.vulnerabilities.append("path_traversal")
        
        return result
    
    def _mask_sensitive_data(self, data: Any) -> Any:
        """Mask sensitive data for safe logging."""
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in ["token", "password", "secret", "key"]):
                    masked[key] = "[REDACTED]"
                else:
                    masked[key] = self._mask_sensitive_data(value)
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        else:
            return data
    
    def _validate_security_headers(self, headers: Dict[str, str]) -> SecurityScanResult:
        """Validate security headers."""
        result = SecurityScanResult(passed=True)
        
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "Strict-Transport-Security": None,  # Just needs to be present
        }
        
        for header, expected_values in required_headers.items():
            if header not in headers:
                result.passed = False
                result.vulnerabilities.append(
                    SecurityVulnerability(
                        name=f"missing_{header.lower().replace('-', '_')}",
                        severity="medium",
                        category="missing_security_header",
                        description=f"Missing security header: {header}",
                        remediation=f"Add {header} header to responses"
                    )
                )
            elif expected_values:
                actual_value = headers[header]
                if isinstance(expected_values, list):
                    if actual_value not in expected_values:
                        result.passed = False
                        result.vulnerabilities.append(
                            SecurityVulnerability(
                                name=f"invalid_{header.lower().replace('-', '_')}",
                                severity="medium",
                                category="invalid_security_header",
                                description=f"Invalid value for {header}: {actual_value}",
                                remediation=f"Set {header} to one of: {expected_values}"
                            )
                        )
                elif actual_value != expected_values:
                    result.passed = False
                    result.vulnerabilities.append(
                        SecurityVulnerability(
                            name=f"invalid_{header.lower().replace('-', '_')}",
                            severity="medium",
                            category="invalid_security_header",
                            description=f"Invalid value for {header}: {actual_value}",
                            remediation=f"Set {header} to: {expected_values}"
                        )
                    )
        
        return result
    
    def _scan_project_security(self, project_path: Path) -> SecurityScanResult:
        """Scan project for security vulnerabilities."""
        result = SecurityScanResult(passed=True)
        
        # Scan Python files
        for py_file in project_path.rglob("*.py"):
            if "test" not in str(py_file):  # Skip test files
                file_result = self._scan_file_for_credentials(py_file)
                result.vulnerabilities.extend(file_result.vulnerabilities)
        
        result.passed = len(result.vulnerabilities) == 0
        return result
    
    def _log_config(self, config: Dict[str, Any]) -> None:
        """Log configuration with sensitive data masked."""
        masked_config = self._mask_sensitive_data(config)
        self.logger.info("config_loaded", config=masked_config)
    
    def _sanitize_error_message(self, error_msg: str) -> str:
        """Sanitize error messages to remove sensitive data."""
        # Simple token pattern matching and replacement
        sanitized = error_msg
        for pattern in self.credential_patterns.values():
            sanitized = pattern.sub("[REDACTED]", sanitized)
        return sanitized


if __name__ == "__main__":
    unittest.main()