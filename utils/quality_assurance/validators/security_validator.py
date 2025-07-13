#!/usr/bin/env python3
"""Security Validator.

This module provides comprehensive security validation including:
- Input sanitization validation and injection attack prevention
- Authentication security checks and token validation
- Data protection validation and encryption verification
- Access control validation and permission verification
- Vulnerability assessment and security pattern detection
- Network security validation and secure communication checks
"""

import asyncio
import json
import re
import hashlib
import hmac
import secrets
import base64
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone
from dataclasses import dataclass, field
import sys
from pathlib import Path
import urllib.parse

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# Security validation types
@dataclass
class SecurityValidationResult:
    """Result of security validation."""
    validation_id: str
    validation_type: str
    security_level: str  # "safe", "warning", "danger", "critical"
    vulnerabilities_detected: List[str]
    security_score: float  # 0-100
    input_sanitization_passed: bool
    authentication_secure: bool
    data_protection_adequate: bool
    access_controls_valid: bool
    network_security_compliant: bool
    security_recommendations: List[str]
    compliance_issues: List[str]
    threat_indicators: List[Dict[str, Any]]


@dataclass
class SecurityThreat:
    """Definition of a security threat pattern."""
    threat_id: str
    threat_type: str  # "injection", "xss", "csrf", "disclosure", "privilege_escalation"
    severity: str  # "low", "medium", "high", "critical"
    pattern: str
    description: str
    mitigation: str


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    policy_id: str
    policy_name: str
    required_authentication: bool
    required_encryption: bool
    allowed_origins: List[str]
    forbidden_patterns: List[str]
    required_headers: List[str]
    content_security_rules: Dict[str, Any]


class InputSanitizationValidator:
    """Validates input sanitization and injection prevention."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.injection_patterns = self._load_injection_patterns()
        
    def _load_injection_patterns(self) -> List[SecurityThreat]:
        """Load known injection attack patterns."""
        return [
            SecurityThreat(
                threat_id="sql_injection",
                threat_type="injection",
                severity="critical",
                pattern=r"(?i)(union\s+select|drop\s+table|insert\s+into|delete\s+from|'.*or.*'|;.*--|\/\*.*\*\/)",
                description="SQL injection attack patterns",
                mitigation="Use parameterized queries and input validation"
            ),
            SecurityThreat(
                threat_id="command_injection",
                threat_type="injection", 
                severity="critical",
                pattern=r"(?i)(;|\||&|`|\$\(|<\(|>\(|\{\{.*\}\}|eval\s*\(|exec\s*\()",
                description="Command injection attack patterns",
                mitigation="Sanitize shell metacharacters and use safe APIs"
            ),
            SecurityThreat(
                threat_id="xss_basic",
                threat_type="xss",
                severity="high",
                pattern=r"(?i)(<script[^>]*>|javascript:|on\w+\s*=|<iframe[^>]*>|<object[^>]*>|<embed[^>]*>)",
                description="Cross-site scripting attack patterns",
                mitigation="Encode user input and use Content Security Policy"
            ),
            SecurityThreat(
                threat_id="path_traversal",
                threat_type="injection",
                severity="high",
                pattern=r"(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e%5c|\.\.%2f|\.\.%5c)",
                description="Path traversal attack patterns",
                mitigation="Validate and canonicalize file paths"
            ),
            SecurityThreat(
                threat_id="template_injection",
                threat_type="injection",
                severity="high",
                pattern=r"(\{\{.*\}\}|\{%.*%\}|\${.*}|<%.*%>|\[\[.*\]\])",
                description="Template injection attack patterns",
                mitigation="Use safe template engines and sandboxing"
            ),
            SecurityThreat(
                threat_id="ldap_injection",
                threat_type="injection",
                severity="medium",
                pattern=r"(\*|\(|\)|\\|\||&|!|=|<|>|~|;|,|\+|-|\")",
                description="LDAP injection attack patterns",
                mitigation="Escape LDAP special characters"
            )
        ]
    
    def validate_input_content(self, content: str, input_type: str = "generic") -> Dict[str, Any]:
        """Validate input content for security threats."""
        validation_result = {
            "input_safe": True,
            "threats_detected": [],
            "sanitization_required": False,
            "risk_level": "safe",
            "recommendations": []
        }
        
        if not content:
            return validation_result
        
        # Check against known threat patterns
        for threat in self.injection_patterns:
            if re.search(threat.pattern, content, re.IGNORECASE | re.MULTILINE):
                validation_result["input_safe"] = False
                validation_result["threats_detected"].append({
                    "threat_id": threat.threat_id,
                    "threat_type": threat.threat_type,
                    "severity": threat.severity,
                    "description": threat.description,
                    "mitigation": threat.mitigation,
                    "pattern_matched": threat.pattern
                })
                validation_result["sanitization_required"] = True
        
        # Determine overall risk level
        if validation_result["threats_detected"]:
            severities = [t["severity"] for t in validation_result["threats_detected"]]
            if "critical" in severities:
                validation_result["risk_level"] = "critical"
            elif "high" in severities:
                validation_result["risk_level"] = "high"
            elif "medium" in severities:
                validation_result["risk_level"] = "medium"
            else:
                validation_result["risk_level"] = "low"
        
        # Generate recommendations
        if validation_result["sanitization_required"]:
            validation_result["recommendations"].extend([
                "Implement input validation and sanitization",
                "Use parameterized queries for database operations",
                "Encode output data appropriately",
                "Implement Content Security Policy headers"
            ])
        
        # Additional checks for specific input types
        if input_type == "url":
            validation_result.update(self._validate_url_content(content))
        elif input_type == "json":
            validation_result.update(self._validate_json_content(content))
        elif input_type == "file_path":
            validation_result.update(self._validate_file_path(content))
        
        return validation_result
    
    def _validate_url_content(self, url: str) -> Dict[str, Any]:
        """Validate URL for security issues."""
        url_validation = {
            "url_safe": True,
            "url_issues": []
        }
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ['http', 'https']:
                url_validation["url_safe"] = False
                url_validation["url_issues"].append("Non-HTTP(S) protocol detected")
            
            # Check for suspicious characters
            if any(char in url for char in ['<', '>', '"', "'"]):
                url_validation["url_safe"] = False
                url_validation["url_issues"].append("Suspicious characters in URL")
            
            # Check for data URIs
            if url.startswith('data:'):
                url_validation["url_safe"] = False
                url_validation["url_issues"].append("Data URI detected - potential XSS vector")
            
            # Check for javascript protocol
            if url.lower().startswith('javascript:'):
                url_validation["url_safe"] = False
                url_validation["url_issues"].append("JavaScript protocol detected - XSS vector")
                
        except Exception as e:
            url_validation["url_safe"] = False
            url_validation["url_issues"].append(f"URL parsing error: {str(e)}")
        
        return url_validation
    
    def _validate_json_content(self, json_str: str) -> Dict[str, Any]:
        """Validate JSON content for security issues."""
        json_validation = {
            "json_safe": True,
            "json_issues": []
        }
        
        try:
            # Check for JSON structure
            json.loads(json_str)
            
            # Check for excessive nesting (potential DoS)
            nesting_level = self._count_json_nesting(json_str)
            if nesting_level > 20:
                json_validation["json_safe"] = False
                json_validation["json_issues"].append("Excessive JSON nesting detected - potential DoS")
            
            # Check for large strings (potential DoS)
            if len(json_str) > 1000000:  # 1MB
                json_validation["json_safe"] = False
                json_validation["json_issues"].append("Large JSON payload detected - potential DoS")
                
        except json.JSONDecodeError as e:
            json_validation["json_safe"] = False
            json_validation["json_issues"].append(f"Invalid JSON structure: {str(e)}")
        
        return json_validation
    
    def _validate_file_path(self, file_path: str) -> Dict[str, Any]:
        """Validate file path for security issues."""
        path_validation = {
            "path_safe": True,
            "path_issues": []
        }
        
        # Check for path traversal
        if ".." in file_path:
            path_validation["path_safe"] = False
            path_validation["path_issues"].append("Path traversal pattern detected")
        
        # Check for absolute paths outside project
        if file_path.startswith('/') and not file_path.startswith('/home/ubuntu/claude_code_event_notifier'):
            path_validation["path_safe"] = False
            path_validation["path_issues"].append("Absolute path outside project directory")
        
        # Check for suspicious file extensions
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.sh', '.ps1', '.scr', '.pif']
        if any(file_path.lower().endswith(ext) for ext in dangerous_extensions):
            path_validation["path_safe"] = False
            path_validation["path_issues"].append("Potentially dangerous file extension")
        
        return path_validation
    
    def _count_json_nesting(self, json_str: str) -> int:
        """Count maximum nesting level in JSON string."""
        max_depth = 0
        current_depth = 0
        
        for char in json_str:
            if char in '{[':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in '}]':
                current_depth -= 1
        
        return max_depth


class AuthenticationValidator:
    """Validates authentication security mechanisms."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        
    def validate_discord_webhook_url(self, webhook_url: str) -> Dict[str, Any]:
        """Validate Discord webhook URL security."""
        validation = {
            "webhook_secure": True,
            "security_issues": [],
            "recommendations": []
        }
        
        if not webhook_url:
            validation["webhook_secure"] = False
            validation["security_issues"].append("No webhook URL provided")
            return validation
        
        # Check URL format
        discord_webhook_pattern = r'^https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+$'
        if not re.match(discord_webhook_pattern, webhook_url):
            validation["webhook_secure"] = False
            validation["security_issues"].append("Invalid Discord webhook URL format")
        
        # Check for HTTPS
        if not webhook_url.startswith('https://'):
            validation["webhook_secure"] = False
            validation["security_issues"].append("Webhook URL is not using HTTPS")
        
        # Extract and validate token
        try:
            parts = webhook_url.split('/')
            if len(parts) >= 2:
                webhook_token = parts[-1]
                token_validation = self._validate_webhook_token(webhook_token)
                validation.update(token_validation)
        except Exception as e:
            validation["webhook_secure"] = False
            validation["security_issues"].append(f"Error extracting webhook token: {str(e)}")
        
        # Security recommendations
        if validation["webhook_secure"]:
            validation["recommendations"].extend([
                "Store webhook URL securely (environment variables)",
                "Rotate webhook URL periodically",
                "Monitor webhook usage for anomalies"
            ])
        
        return validation
    
    def validate_bot_token(self, bot_token: str) -> Dict[str, Any]:
        """Validate Discord bot token security."""
        validation = {
            "token_secure": True,
            "security_issues": [],
            "recommendations": []
        }
        
        if not bot_token:
            validation["token_secure"] = False
            validation["security_issues"].append("No bot token provided")
            return validation
        
        # Check bot token format
        bot_token_pattern = r'^[A-Za-z0-9]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}$'
        if not re.match(bot_token_pattern, bot_token):
            validation["token_secure"] = False
            validation["security_issues"].append("Invalid Discord bot token format")
        
        # Check for common security issues
        if bot_token in ['your_bot_token', 'bot_token_here', 'placeholder']:
            validation["token_secure"] = False
            validation["security_issues"].append("Placeholder bot token detected")
        
        # Validate token entropy
        entropy_validation = self._validate_token_entropy(bot_token)
        validation.update(entropy_validation)
        
        # Security recommendations
        if validation["token_secure"]:
            validation["recommendations"].extend([
                "Store bot token securely (environment variables)",
                "Use bot token scopes appropriately",
                "Rotate bot token if compromised",
                "Monitor bot token usage"
            ])
        
        return validation
    
    def _validate_webhook_token(self, token: str) -> Dict[str, Any]:
        """Validate webhook token security properties."""
        validation = {
            "token_format_valid": True,
            "token_entropy_adequate": True,
            "token_issues": []
        }
        
        # Check length
        if len(token) < 60:
            validation["token_format_valid"] = False
            validation["token_issues"].append("Webhook token too short")
        
        # Check character set
        if not re.match(r'^[A-Za-z0-9_-]+$', token):
            validation["token_format_valid"] = False
            validation["token_issues"].append("Invalid characters in webhook token")
        
        # Check entropy
        entropy = self._calculate_entropy(token)
        if entropy < 4.0:  # Minimum entropy threshold
            validation["token_entropy_adequate"] = False
            validation["token_issues"].append("Low entropy in webhook token")
        
        return validation
    
    def _validate_token_entropy(self, token: str) -> Dict[str, Any]:
        """Validate token entropy for security."""
        validation = {
            "entropy_adequate": True,
            "entropy_score": 0.0,
            "entropy_issues": []
        }
        
        entropy = self._calculate_entropy(token)
        validation["entropy_score"] = entropy
        
        if entropy < 3.5:
            validation["entropy_adequate"] = False
            validation["entropy_issues"].append("Very low token entropy")
        elif entropy < 4.0:
            validation["entropy_adequate"] = False
            validation["entropy_issues"].append("Low token entropy")
        
        return validation
    
    def _calculate_entropy(self, data: str) -> float:
        """Calculate Shannon entropy of data."""
        if not data:
            return 0.0
        
        # Count character frequencies
        char_counts = {}
        for char in data:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate entropy
        data_len = len(data)
        entropy = 0.0
        
        for count in char_counts.values():
            probability = count / data_len
            if probability > 0:
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy


class DataProtectionValidator:
    """Validates data protection and privacy mechanisms."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.sensitive_patterns = self._load_sensitive_patterns()
        
    def _load_sensitive_patterns(self) -> List[Dict[str, str]]:
        """Load patterns for detecting sensitive data."""
        return [
            {
                "name": "credit_card",
                "pattern": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                "severity": "critical"
            },
            {
                "name": "social_security",
                "pattern": r'\b\d{3}-\d{2}-\d{4}\b',
                "severity": "critical"
            },
            {
                "name": "email_address",
                "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "severity": "medium"
            },
            {
                "name": "phone_number",
                "pattern": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                "severity": "medium"
            },
            {
                "name": "api_key",
                "pattern": r'\b[A-Za-z0-9]{32,}\b',
                "severity": "high"
            },
            {
                "name": "private_key",
                "pattern": r'-----BEGIN [A-Z]+ PRIVATE KEY-----',
                "severity": "critical"
            },
            {
                "name": "password",
                "pattern": r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^"\'\s]+)',
                "severity": "high"
            }
        ]
    
    def validate_data_content(self, content: str, data_type: str = "generic") -> Dict[str, Any]:
        """Validate content for sensitive data exposure."""
        validation = {
            "data_protected": True,
            "sensitive_data_detected": [],
            "privacy_issues": [],
            "protection_recommendations": []
        }
        
        if not content:
            return validation
        
        # Check for sensitive data patterns
        for pattern_info in self.sensitive_patterns:
            matches = re.finditer(pattern_info["pattern"], content, re.IGNORECASE)
            for match in matches:
                validation["data_protected"] = False
                validation["sensitive_data_detected"].append({
                    "type": pattern_info["name"],
                    "severity": pattern_info["severity"],
                    "position": match.span(),
                    "preview": content[max(0, match.start()-10):match.end()+10]
                })
        
        # Additional checks for specific data types
        if data_type == "log":
            validation.update(self._validate_log_data(content))
        elif data_type == "config":
            validation.update(self._validate_config_data(content))
        elif data_type == "message":
            validation.update(self._validate_message_data(content))
        
        # Generate protection recommendations
        if not validation["data_protected"]:
            validation["protection_recommendations"].extend([
                "Implement data masking for sensitive information",
                "Use encryption for sensitive data storage",
                "Implement data loss prevention (DLP) policies",
                "Regular audit of data handling practices"
            ])
        
        return validation
    
    def _validate_log_data(self, log_content: str) -> Dict[str, Any]:
        """Validate log data for sensitive information."""
        log_validation = {
            "log_safe": True,
            "log_issues": []
        }
        
        # Check for credentials in logs
        credential_patterns = [
            r'(?i)(token|key|password|secret)\s*[=:]\s*["\']?([^"\'\s]+)',
            r'(?i)authorization:\s*bearer\s+([A-Za-z0-9]+)',
            r'(?i)x-api-key:\s*([A-Za-z0-9]+)'
        ]
        
        for pattern in credential_patterns:
            if re.search(pattern, log_content):
                log_validation["log_safe"] = False
                log_validation["log_issues"].append("Credentials detected in log content")
                break
        
        return log_validation
    
    def _validate_config_data(self, config_content: str) -> Dict[str, Any]:
        """Validate configuration data security."""
        config_validation = {
            "config_secure": True,
            "config_issues": []
        }
        
        # Check for plaintext secrets
        if re.search(r'(?i)(password|secret|key)\s*[=:]\s*["\']?[^"\'\s]+', config_content):
            config_validation["config_secure"] = False
            config_validation["config_issues"].append("Plaintext secrets in configuration")
        
        # Check for default/weak passwords
        weak_patterns = [
            r'(?i)password\s*[=:]\s*["\']?(admin|password|123456|default)',
            r'(?i)secret\s*[=:]\s*["\']?(secret|default|changeme)'
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, config_content):
                config_validation["config_secure"] = False
                config_validation["config_issues"].append("Weak/default credentials in configuration")
                break
        
        return config_validation
    
    def _validate_message_data(self, message_content: str) -> Dict[str, Any]:
        """Validate message data for privacy compliance."""
        message_validation = {
            "message_private": True,
            "privacy_issues": []
        }
        
        # Check for PII in messages
        pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',  # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
        ]
        
        for pattern in pii_patterns:
            if re.search(pattern, message_content):
                message_validation["message_private"] = False
                message_validation["privacy_issues"].append("PII detected in message content")
                break
        
        return message_validation


class AccessControlValidator:
    """Validates access control and authorization mechanisms."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        
    def validate_discord_permissions(self, permissions: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Discord permission configuration."""
        validation = {
            "permissions_secure": True,
            "permission_issues": [],
            "recommendations": []
        }
        
        # Check for overprivileged permissions
        dangerous_permissions = [
            "ADMINISTRATOR",
            "MANAGE_GUILD",
            "MANAGE_ROLES",
            "MANAGE_CHANNELS",
            "BAN_MEMBERS",
            "KICK_MEMBERS"
        ]
        
        for perm in dangerous_permissions:
            if permissions.get(perm, False):
                validation["permissions_secure"] = False
                validation["permission_issues"].append(f"Dangerous permission granted: {perm}")
        
        # Check for minimum required permissions
        required_permissions = ["SEND_MESSAGES", "VIEW_CHANNEL"]
        for perm in required_permissions:
            if not permissions.get(perm, False):
                validation["permission_issues"].append(f"Missing required permission: {perm}")
        
        # Generate recommendations
        if validation["permission_issues"]:
            validation["recommendations"].extend([
                "Follow principle of least privilege",
                "Regularly audit bot permissions",
                "Use role-based access control",
                "Document permission requirements"
            ])
        
        return validation
    
    def validate_file_access_patterns(self, file_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate file access patterns for security."""
        validation = {
            "file_access_secure": True,
            "access_issues": [],
            "suspicious_patterns": []
        }
        
        for operation in file_operations:
            file_path = operation.get("file_path", "")
            operation_type = operation.get("operation", "")
            
            # Check for suspicious file access
            if self._is_suspicious_file_access(file_path, operation_type):
                validation["file_access_secure"] = False
                validation["access_issues"].append(f"Suspicious file access: {file_path}")
                validation["suspicious_patterns"].append({
                    "file_path": file_path,
                    "operation": operation_type,
                    "risk_level": self._assess_file_access_risk(file_path, operation_type)
                })
        
        return validation
    
    def _is_suspicious_file_access(self, file_path: str, operation: str) -> bool:
        """Check if file access pattern is suspicious."""
        suspicious_patterns = [
            r'/etc/',
            r'/proc/',
            r'/sys/',
            r'\.ssh/',
            r'\.aws/',
            r'config',
            r'passwd',
            r'shadow',
            r'\.env',
            r'\.secret'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        
        # Check for write operations to system directories
        if operation in ["write", "delete"] and file_path.startswith("/"):
            return True
        
        return False
    
    def _assess_file_access_risk(self, file_path: str, operation: str) -> str:
        """Assess risk level of file access."""
        if any(pattern in file_path.lower() for pattern in ['/etc/', 'passwd', 'shadow', '.ssh/']):
            return "critical"
        elif any(pattern in file_path.lower() for pattern in ['.env', '.secret', 'config']):
            return "high"
        elif operation in ["write", "delete"]:
            return "medium"
        else:
            return "low"


class VulnerabilityScanner:
    """Scans for common security vulnerabilities."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.vulnerability_patterns = self._load_vulnerability_patterns()
        
    def _load_vulnerability_patterns(self) -> List[Dict[str, Any]]:
        """Load vulnerability detection patterns."""
        return [
            {
                "id": "hardcoded_secrets",
                "severity": "critical",
                "pattern": r'(?i)(password|secret|key|token)\s*[=:]\s*["\'][^"\']+["\']',
                "description": "Hardcoded secrets in source code"
            },
            {
                "id": "weak_crypto",
                "severity": "high", 
                "pattern": r'(?i)(md5|sha1|des|rc4)',
                "description": "Use of weak cryptographic algorithms"
            },
            {
                "id": "debug_info",
                "severity": "medium",
                "pattern": r'(?i)(debug|trace|print|console\.log)',
                "description": "Debug information in production code"
            },
            {
                "id": "unsafe_eval",
                "severity": "critical",
                "pattern": r'(?i)(eval\s*\(|exec\s*\(|system\s*\()',
                "description": "Use of unsafe evaluation functions"
            },
            {
                "id": "weak_random",
                "severity": "medium",
                "pattern": r'(?i)(random\.random|math\.random)',
                "description": "Use of weak random number generation"
            }
        ]
    
    def scan_content(self, content: str, content_type: str = "code") -> Dict[str, Any]:
        """Scan content for security vulnerabilities."""
        scan_result = {
            "vulnerabilities_found": [],
            "vulnerability_count": 0,
            "highest_severity": "none",
            "security_score": 100.0,
            "remediation_required": False
        }
        
        # Scan for known vulnerability patterns
        for vuln_pattern in self.vulnerability_patterns:
            matches = list(re.finditer(vuln_pattern["pattern"], content, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                vulnerability = {
                    "id": vuln_pattern["id"],
                    "severity": vuln_pattern["severity"],
                    "description": vuln_pattern["description"],
                    "line_number": content[:match.start()].count('\n') + 1,
                    "match_text": match.group(),
                    "position": match.span()
                }
                
                scan_result["vulnerabilities_found"].append(vulnerability)
                scan_result["vulnerability_count"] += 1
                
                # Update highest severity
                severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                current_severity = severity_levels.get(vuln_pattern["severity"], 0)
                highest_severity_level = severity_levels.get(scan_result["highest_severity"], 0)
                
                if current_severity > highest_severity_level:
                    scan_result["highest_severity"] = vuln_pattern["severity"]
        
        # Calculate security score
        if scan_result["vulnerability_count"] > 0:
            scan_result["remediation_required"] = True
            
            # Deduct points based on vulnerabilities
            score_deduction = 0
            for vuln in scan_result["vulnerabilities_found"]:
                if vuln["severity"] == "critical":
                    score_deduction += 30
                elif vuln["severity"] == "high":
                    score_deduction += 20
                elif vuln["severity"] == "medium":
                    score_deduction += 10
                else:
                    score_deduction += 5
            
            scan_result["security_score"] = max(0, 100 - score_deduction)
        
        return scan_result


class SecurityValidator(BaseQualityChecker):
    """Comprehensive security validator."""
    
    def __init__(self):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.input_validator = InputSanitizationValidator()
        self.auth_validator = AuthenticationValidator()
        self.data_validator = DataProtectionValidator()
        self.access_validator = AccessControlValidator()
        self.vulnerability_scanner = VulnerabilityScanner()
        self.validation_results = []
        
    async def validate_security_comprehensive(
        self,
        content: str,
        content_type: str = "generic",
        context: Optional[Dict[str, Any]] = None
    ) -> SecurityValidationResult:
        """Perform comprehensive security validation."""
        
        validation_id = f"security_{int(datetime.now().timestamp() * 1000)}"
        vulnerabilities_detected = []
        security_recommendations = []
        compliance_issues = []
        threat_indicators = []
        
        # Input sanitization validation
        input_validation = self.input_validator.validate_input_content(content, content_type)
        if not input_validation["input_safe"]:
            vulnerabilities_detected.extend([
                f"Input validation: {threat['description']}" 
                for threat in input_validation["threats_detected"]
            ])
            threat_indicators.extend(input_validation["threats_detected"])
        
        # Data protection validation
        data_validation = self.data_validator.validate_data_content(content, content_type)
        if not data_validation["data_protected"]:
            vulnerabilities_detected.extend([
                f"Data protection: {item['type']} detected"
                for item in data_validation["sensitive_data_detected"]
            ])
            compliance_issues.extend(data_validation["privacy_issues"])
        
        # Vulnerability scanning
        vuln_scan = self.vulnerability_scanner.scan_content(content, content_type)
        if vuln_scan["vulnerability_count"] > 0:
            vulnerabilities_detected.extend([
                f"Vulnerability: {vuln['description']}"
                for vuln in vuln_scan["vulnerabilities_found"]
            ])
        
        # Authentication validation (if context provides auth info)
        authentication_secure = True
        if context:
            if "webhook_url" in context:
                webhook_validation = self.auth_validator.validate_discord_webhook_url(context["webhook_url"])
                if not webhook_validation["webhook_secure"]:
                    authentication_secure = False
                    vulnerabilities_detected.extend([
                        f"Webhook security: {issue}"
                        for issue in webhook_validation["security_issues"]
                    ])
            
            if "bot_token" in context:
                token_validation = self.auth_validator.validate_bot_token(context["bot_token"])
                if not token_validation["token_secure"]:
                    authentication_secure = False
                    vulnerabilities_detected.extend([
                        f"Token security: {issue}"
                        for issue in token_validation["security_issues"]
                    ])
        
        # Calculate overall security score
        base_score = 100.0
        if vulnerabilities_detected:
            base_score -= len(vulnerabilities_detected) * 15
        if compliance_issues:
            base_score -= len(compliance_issues) * 10
        
        security_score = max(0.0, min(100.0, base_score))
        
        # Determine security level
        if security_score >= 90:
            security_level = "safe"
        elif security_score >= 70:
            security_level = "warning"
        elif security_score >= 50:
            security_level = "danger"
        else:
            security_level = "critical"
        
        # Generate recommendations
        if security_score < 100:
            security_recommendations.extend([
                "Implement comprehensive input validation",
                "Use secure authentication mechanisms", 
                "Encrypt sensitive data at rest and in transit",
                "Regular security audits and penetration testing",
                "Implement security monitoring and alerting"
            ])
        
        result = SecurityValidationResult(
            validation_id=validation_id,
            validation_type="comprehensive_security",
            security_level=security_level,
            vulnerabilities_detected=vulnerabilities_detected,
            security_score=security_score,
            input_sanitization_passed=input_validation["input_safe"],
            authentication_secure=authentication_secure,
            data_protection_adequate=data_validation["data_protected"],
            access_controls_valid=True,  # Would need specific context to validate
            network_security_compliant=True,  # Would need network context to validate
            security_recommendations=security_recommendations,
            compliance_issues=compliance_issues,
            threat_indicators=threat_indicators
        )
        
        self.validation_results.append(result)
        return result
    
    async def validate_discord_security(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate Discord-specific security configuration."""
        
        security_assessment = {
            "overall_secure": True,
            "webhook_security": None,
            "bot_token_security": None,
            "configuration_issues": [],
            "security_recommendations": []
        }
        
        # Validate webhook URL
        if webhook_url:
            webhook_validation = self.auth_validator.validate_discord_webhook_url(webhook_url)
            security_assessment["webhook_security"] = webhook_validation
            
            if not webhook_validation["webhook_secure"]:
                security_assessment["overall_secure"] = False
                security_assessment["configuration_issues"].extend(webhook_validation["security_issues"])
        
        # Validate bot token
        if bot_token:
            token_validation = self.auth_validator.validate_bot_token(bot_token)
            security_assessment["bot_token_security"] = token_validation
            
            if not token_validation["token_secure"]:
                security_assessment["overall_secure"] = False
                security_assessment["configuration_issues"].extend(token_validation["security_issues"])
        
        # Generate overall recommendations
        if not security_assessment["overall_secure"]:
            security_assessment["security_recommendations"].extend([
                "Review and update Discord API credentials",
                "Implement proper secret management",
                "Use environment variables for sensitive configuration",
                "Regular rotation of API credentials"
            ])
        
        return security_assessment
    
    async def validate_file_operations_security(self, file_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate security of file operations."""
        
        file_security = {
            "operations_secure": True,
            "security_violations": [],
            "risk_assessment": {},
            "mitigation_recommendations": []
        }
        
        # Validate access patterns
        access_validation = self.access_validator.validate_file_access_patterns(file_operations)
        
        if not access_validation["file_access_secure"]:
            file_security["operations_secure"] = False
            file_security["security_violations"].extend(access_validation["access_issues"])
            file_security["risk_assessment"]["suspicious_patterns"] = access_validation["suspicious_patterns"]
        
        # Analyze file content if available
        for operation in file_operations:
            if "content" in operation:
                content_validation = await self.validate_security_comprehensive(
                    operation["content"], 
                    "file_content"
                )
                
                if content_validation.security_level in ["danger", "critical"]:
                    file_security["operations_secure"] = False
                    file_security["security_violations"].append(
                        f"Insecure content in {operation.get('file_path', 'unknown file')}"
                    )
        
        # Generate mitigation recommendations
        if not file_security["operations_secure"]:
            file_security["mitigation_recommendations"].extend([
                "Implement file access controls",
                "Validate file paths and contents",
                "Use principle of least privilege",
                "Monitor file system access patterns"
            ])
        
        return file_security
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check overall security validation quality."""
        
        if not self.validation_results:
            return {
                "quality_level": "unknown",
                "message": "No security validation results available"
            }
        
        total_validations = len(self.validation_results)
        secure_validations = sum(1 for r in self.validation_results if r.security_level == "safe")
        average_security_score = sum(r.security_score for r in self.validation_results) / total_validations
        
        # Count vulnerabilities by severity
        vulnerability_summary = {}
        for result in self.validation_results:
            for threat in result.threat_indicators:
                severity = threat.get("severity", "unknown")
                vulnerability_summary[severity] = vulnerability_summary.get(severity, 0) + 1
        
        # Determine overall security posture
        security_rate = secure_validations / total_validations
        if security_rate >= 0.95 and average_security_score >= 90:
            quality_level = "excellent"
        elif security_rate >= 0.85 and average_security_score >= 80:
            quality_level = "good"
        elif security_rate >= 0.70 and average_security_score >= 70:
            quality_level = "acceptable"
        else:
            quality_level = "needs_improvement"
        
        return {
            "quality_level": quality_level,
            "total_validations": total_validations,
            "secure_validations": secure_validations,
            "security_rate": security_rate,
            "average_security_score": average_security_score,
            "vulnerability_summary": vulnerability_summary,
            "security_posture": {
                "overall_secure": security_rate >= 0.8,
                "critical_vulnerabilities": vulnerability_summary.get("critical", 0),
                "high_vulnerabilities": vulnerability_summary.get("high", 0),
                "needs_immediate_attention": vulnerability_summary.get("critical", 0) > 0
            }
        }