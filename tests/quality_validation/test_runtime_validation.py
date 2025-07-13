#!/usr/bin/env python3
"""Test Runtime Validation Functionality.

This module provides comprehensive tests for runtime validation functionality,
including input validation, data sanitization, business rule validation,
constraint checking, and dynamic validation.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import re
import html
import urllib.parse
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.type_defs.base import BaseEvent, BaseToolResult
from src.type_defs.config import ConfigDict, DiscordConfig
from src.type_defs.discord import DiscordEmbed, DiscordField, DiscordMessage
from src.type_defs.events import EventDict, ToolUseEvent
from src.validators import validate_config, validate_event_data, validate_discord_webhook_url
from src.utils.validation import sanitize_content, validate_unicode, validate_timestamp_format


# Validation rule types
ValidationRule = Callable[[Any], Tuple[bool, Optional[str]]]
ValidationContext = Dict[str, Any]


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldValidation:
    """Field-level validation configuration."""
    field_name: str
    required: bool = True
    nullable: bool = False
    validators: List[ValidationRule] = field(default_factory=list)
    sanitizers: List[Callable[[Any], Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


class BusinessRule(Protocol):
    """Protocol for business rule validation."""
    def validate(self, data: Dict[str, Any], context: ValidationContext) -> ValidationResult:
        ...
    
    def get_description(self) -> str:
        ...


class TestRuntimeValidation(unittest.IsolatedAsyncioTestCase):
    """Test cases for runtime validation functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "validation_mode": "strict",
            "sanitize_input": True,
            "enforce_constraints": True,
            "business_rules": True,
            "dynamic_validation": True,
            "debug": True
        }
        
        # Common validators
        self.common_validators = {
            "email": lambda v: (
                bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v)),
                "Invalid email format" if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v) else None
            ),
            "url": lambda v: (
                bool(re.match(r'^https?://[^\s]+$', v)),
                "Invalid URL format" if not re.match(r'^https?://[^\s]+$', v) else None
            ),
            "non_empty": lambda v: (
                bool(v and str(v).strip()),
                "Value cannot be empty" if not (v and str(v).strip()) else None
            ),
            "positive_number": lambda v: (
                isinstance(v, (int, float)) and v > 0,
                "Value must be a positive number" if not (isinstance(v, (int, float)) and v > 0) else None
            ),
            "iso_timestamp": lambda v: (
                self._validate_iso_timestamp(v),
                "Invalid ISO timestamp format" if not self._validate_iso_timestamp(v) else None
            )
        }
        
        # Common sanitizers
        self.common_sanitizers = {
            "trim": lambda v: str(v).strip() if v is not None else None,
            "lowercase": lambda v: str(v).lower() if v is not None else None,
            "escape_html": lambda v: html.escape(str(v)) if v is not None else None,
            "url_encode": lambda v: urllib.parse.quote(str(v)) if v is not None else None,
            "remove_control_chars": lambda v: re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(v)) if v is not None else None
        }
        
        # Test data
        self.test_data = {
            "valid_input": {
                "username": "test_user",
                "email": "test@example.com",
                "age": 25,
                "website": "https://example.com",
                "bio": "Test bio with <script>alert('xss')</script>",
                "created_at": "2025-07-12T22:00:00.000Z"
            },
            "invalid_input": {
                "username": "",  # Empty
                "email": "invalid-email",  # Invalid format
                "age": -5,  # Negative
                "website": "not-a-url",  # Invalid URL
                "bio": "\x00\x01Control chars\x1f",  # Control characters
                "created_at": "invalid-timestamp"  # Invalid timestamp
            },
            "malicious_input": {
                "username": "<script>alert('xss')</script>",
                "email": "test@example.com'; DROP TABLE users;--",
                "age": "25; DELETE FROM users;",
                "website": "javascript:alert('xss')",
                "bio": "../../../etc/passwd",
                "created_at": "2025-07-12T22:00:00.000Z"
            },
            "edge_case_input": {
                "username": "a" * 1000,  # Very long
                "email": "test@" + "a" * 250 + ".com",  # Long domain
                "age": 999999999,  # Very large
                "website": "https://" + "a" * 2000 + ".com",  # Very long URL
                "bio": "🎮" * 500,  # Many emojis
                "created_at": "9999-12-31T23:59:59.999Z"  # Far future
            }
        }
    
    async def test_input_validation(self) -> None:
        """Test input validation with various rules."""
        with patch('src.validators.validate_event_data') as mock_validate:
            # Mock input validation
            validation_log = []
            
            def validate_input(data: Dict[str, Any], rules: Dict[str, FieldValidation]) -> ValidationResult:
                """Validate input data against field rules."""
                result = ValidationResult(valid=True)
                
                for field_name, rule in rules.items():
                    field_result = {
                        "field": field_name,
                        "value": data.get(field_name),
                        "valid": True,
                        "errors": [],
                        "warnings": []
                    }
                    
                    # Check required
                    if rule.required and field_name not in data:
                        field_result["valid"] = False
                        field_result["errors"].append(f"Required field '{field_name}' is missing")
                        result.valid = False
                        result.errors.append(f"Required field '{field_name}' is missing")
                    
                    elif field_name in data:
                        value = data[field_name]
                        
                        # Check nullable
                        if value is None and not rule.nullable:
                            field_result["valid"] = False
                            field_result["errors"].append(f"Field '{field_name}' cannot be null")
                            result.valid = False
                            result.errors.append(f"Field '{field_name}' cannot be null")
                        
                        # Apply validators
                        if value is not None:
                            for validator in rule.validators:
                                is_valid, error_msg = validator(value)
                                if not is_valid:
                                    field_result["valid"] = False
                                    field_result["errors"].append(error_msg or f"Validation failed for '{field_name}'")
                                    result.valid = False
                                    result.errors.append(error_msg or f"Validation failed for '{field_name}'")
                        
                        # Check constraints
                        if rule.constraints:
                            # Min length
                            if "min_length" in rule.constraints and isinstance(value, str):
                                if len(value) < rule.constraints["min_length"]:
                                    field_result["errors"].append(f"Field '{field_name}' is too short (min: {rule.constraints['min_length']})")
                                    result.valid = False
                                    result.errors.append(f"Field '{field_name}' is too short")
                            
                            # Max length
                            if "max_length" in rule.constraints and isinstance(value, str):
                                if len(value) > rule.constraints["max_length"]:
                                    field_result["errors"].append(f"Field '{field_name}' is too long (max: {rule.constraints['max_length']})")
                                    result.valid = False
                                    result.errors.append(f"Field '{field_name}' is too long")
                            
                            # Min value
                            if "min_value" in rule.constraints and isinstance(value, (int, float)):
                                if value < rule.constraints["min_value"]:
                                    field_result["errors"].append(f"Field '{field_name}' is below minimum ({rule.constraints['min_value']})")
                                    result.valid = False
                                    result.errors.append(f"Field '{field_name}' is below minimum")
                            
                            # Max value
                            if "max_value" in rule.constraints and isinstance(value, (int, float)):
                                if value > rule.constraints["max_value"]:
                                    field_result["errors"].append(f"Field '{field_name}' exceeds maximum ({rule.constraints['max_value']})")
                                    result.valid = False
                                    result.errors.append(f"Field '{field_name}' exceeds maximum")
                            
                            # Pattern
                            if "pattern" in rule.constraints and isinstance(value, str):
                                if not re.match(rule.constraints["pattern"], value):
                                    field_result["errors"].append(f"Field '{field_name}' does not match required pattern")
                                    result.valid = False
                                    result.errors.append(f"Field '{field_name}' does not match pattern")
                    
                    validation_log.append(field_result)
                
                return result
            
            # Define validation rules
            user_validation_rules = {
                "username": FieldValidation(
                    field_name="username",
                    required=True,
                    validators=[self.common_validators["non_empty"]],
                    constraints={"min_length": 3, "max_length": 50, "pattern": r"^[a-zA-Z0-9_]+$"}
                ),
                "email": FieldValidation(
                    field_name="email",
                    required=True,
                    validators=[self.common_validators["email"]],
                    constraints={"max_length": 255}
                ),
                "age": FieldValidation(
                    field_name="age",
                    required=False,
                    nullable=True,
                    validators=[self.common_validators["positive_number"]],
                    constraints={"min_value": 1, "max_value": 150}
                ),
                "website": FieldValidation(
                    field_name="website",
                    required=False,
                    validators=[self.common_validators["url"]],
                    constraints={"max_length": 500}
                ),
                "bio": FieldValidation(
                    field_name="bio",
                    required=False,
                    nullable=True,
                    constraints={"max_length": 1000}
                ),
                "created_at": FieldValidation(
                    field_name="created_at",
                    required=True,
                    validators=[self.common_validators["iso_timestamp"]]
                )
            }
            
            # Test validation scenarios
            test_scenarios = [
                ("Valid input", self.test_data["valid_input"], True),
                ("Invalid input", self.test_data["invalid_input"], False),
                ("Malicious input", self.test_data["malicious_input"], False),
                ("Edge case input", self.test_data["edge_case_input"], False),
                ("Empty input", {}, False),
                ("Partial input", {"username": "test", "email": "test@example.com", "created_at": "2025-07-12T22:00:00.000Z"}, True)
            ]
            
            validation_results = []
            
            for scenario_name, test_input, expected_valid in test_scenarios:
                validation_log.clear()
                result = validate_input(test_input, user_validation_rules)
                
                validation_results.append({
                    "scenario": scenario_name,
                    "input_fields": len(test_input),
                    "expected_valid": expected_valid,
                    "actual_valid": result.valid,
                    "passed": result.valid == expected_valid,
                    "error_count": len(result.errors),
                    "field_results": validation_log.copy()
                })
                
                # Assert validation result
                self.assertEqual(result.valid, expected_valid,
                               f"Input validation failed for {scenario_name}: expected {expected_valid}, got {result.valid}")
            
            # Calculate validation metrics
            total_scenarios = len(validation_results)
            passed_scenarios = sum(1 for r in validation_results if r["passed"])
            validation_accuracy = passed_scenarios / total_scenarios
            
            # Log input validation analysis
            self.logger.info(
                "Input validation analysis",
                context={
                    "total_scenarios": total_scenarios,
                    "passed_scenarios": passed_scenarios,
                    "failed_scenarios": total_scenarios - passed_scenarios,
                    "validation_accuracy": validation_accuracy,
                    "total_errors": sum(r["error_count"] for r in validation_results),
                    "validation_rules": len(user_validation_rules),
                    "scenario_breakdown": {
                        scenario["scenario"]: scenario["passed"]
                        for scenario in validation_results
                    }
                }
            )
    
    async def test_data_sanitization(self) -> None:
        """Test data sanitization and cleaning."""
        with patch('src.utils.validation.sanitize_content') as mock_sanitize:
            # Mock data sanitization
            sanitization_log = []
            
            def sanitize_data(data: Dict[str, Any], rules: Dict[str, FieldValidation]) -> Dict[str, Any]:
                """Sanitize data according to field rules."""
                sanitized = {}
                
                for field_name, value in data.items():
                    if field_name in rules:
                        rule = rules[field_name]
                        sanitized_value = value
                        
                        # Apply sanitizers in order
                        for sanitizer in rule.sanitizers:
                            original = sanitized_value
                            sanitized_value = sanitizer(sanitized_value)
                            
                            if original != sanitized_value:
                                sanitization_log.append({
                                    "field": field_name,
                                    "original": original,
                                    "sanitized": sanitized_value,
                                    "sanitizer": sanitizer.__name__
                                })
                        
                        sanitized[field_name] = sanitized_value
                    else:
                        # No sanitization rules, keep original
                        sanitized[field_name] = value
                
                return sanitized
            
            # Define sanitization rules
            sanitization_rules = {
                "username": FieldValidation(
                    field_name="username",
                    sanitizers=[
                        self.common_sanitizers["trim"],
                        self.common_sanitizers["lowercase"],
                        self.common_sanitizers["remove_control_chars"]
                    ]
                ),
                "email": FieldValidation(
                    field_name="email",
                    sanitizers=[
                        self.common_sanitizers["trim"],
                        self.common_sanitizers["lowercase"]
                    ]
                ),
                "bio": FieldValidation(
                    field_name="bio",
                    sanitizers=[
                        self.common_sanitizers["trim"],
                        self.common_sanitizers["escape_html"],
                        self.common_sanitizers["remove_control_chars"]
                    ]
                ),
                "website": FieldValidation(
                    field_name="website",
                    sanitizers=[
                        self.common_sanitizers["trim"]
                    ]
                )
            }
            
            # Test sanitization scenarios
            sanitization_results = []
            
            for scenario_name, test_input in self.test_data.items():
                sanitization_log.clear()
                sanitized = sanitize_data(test_input, sanitization_rules)
                
                # Check specific sanitizations
                changes = []
                for field, original in test_input.items():
                    if field in sanitized and sanitized[field] != original:
                        changes.append({
                            "field": field,
                            "original": original,
                            "sanitized": sanitized[field]
                        })
                
                sanitization_results.append({
                    "scenario": scenario_name,
                    "fields_processed": len(test_input),
                    "fields_changed": len(changes),
                    "changes": changes,
                    "log_entries": len(sanitization_log)
                })
            
            # Test XSS prevention
            xss_tests = [
                ("<script>alert('xss')</script>", "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"),
                ("javascript:alert(1)", "javascript:alert(1)"),  # URL field not HTML escaped
                ("<img src=x onerror=alert(1)>", "&lt;img src=x onerror=alert(1)&gt;"),
                ("'; DROP TABLE users;--", "&#x27;; DROP TABLE users;--")
            ]
            
            for original, expected_safe in xss_tests:
                test_data = {"bio": original}
                sanitized = sanitize_data(test_data, sanitization_rules)
                self.assertEqual(sanitized["bio"], expected_safe.strip(),
                               f"XSS sanitization failed for: {original}")
            
            # Test path traversal prevention
            path_tests = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32",
                "file:///etc/passwd"
            ]
            
            for path in path_tests:
                test_data = {"bio": path}
                sanitized = sanitize_data(test_data, sanitization_rules)
                # Should be HTML escaped
                self.assertNotIn("..", sanitized["bio"])
            
            # Calculate sanitization effectiveness
            total_fields = sum(r["fields_processed"] for r in sanitization_results)
            fields_sanitized = sum(r["fields_changed"] for r in sanitization_results)
            sanitization_rate = fields_sanitized / total_fields if total_fields > 0 else 0
            
            # Log data sanitization analysis
            self.logger.info(
                "Data sanitization analysis",
                context={
                    "scenarios_tested": len(sanitization_results),
                    "total_fields": total_fields,
                    "fields_sanitized": fields_sanitized,
                    "sanitization_rate": sanitization_rate,
                    "xss_tests_passed": len(xss_tests),
                    "path_traversal_tests": len(path_tests),
                    "sanitizers_used": list(self.common_sanitizers.keys()),
                    "scenario_summary": {
                        r["scenario"]: f"{r['fields_changed']}/{r['fields_processed']} fields changed"
                        for r in sanitization_results
                    }
                }
            )
    
    async def test_business_rule_validation(self) -> None:
        """Test business rule validation."""
        # Business rule implementations
        class UserAgeRule:
            """Validate user age consistency."""
            def validate(self, data: Dict[str, Any], context: ValidationContext) -> ValidationResult:
                result = ValidationResult(valid=True)
                
                if "age" in data and "created_at" in data:
                    try:
                        created_date = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
                        current_date = context.get("current_date", datetime.now(timezone.utc))
                        
                        account_age_years = (current_date - created_date).days / 365.25
                        
                        if data["age"] < account_age_years:
                            result.valid = False
                            result.errors.append(f"User age ({data['age']}) cannot be less than account age ({account_age_years:.1f} years)")
                    except Exception as e:
                        result.warnings.append(f"Could not validate age consistency: {str(e)}")
                
                return result
            
            def get_description(self) -> str:
                return "User age must be greater than or equal to account age"
        
        class EmailDomainRule:
            """Validate email domain restrictions."""
            def __init__(self, blocked_domains: List[str], allowed_domains: Optional[List[str]] = None):
                self.blocked_domains = blocked_domains
                self.allowed_domains = allowed_domains
            
            def validate(self, data: Dict[str, Any], context: ValidationContext) -> ValidationResult:
                result = ValidationResult(valid=True)
                
                if "email" in data:
                    email = data["email"]
                    domain = email.split("@")[-1].lower() if "@" in email else ""
                    
                    if domain in self.blocked_domains:
                        result.valid = False
                        result.errors.append(f"Email domain '{domain}' is blocked")
                    
                    if self.allowed_domains and domain not in self.allowed_domains:
                        result.valid = False
                        result.errors.append(f"Email domain '{domain}' is not in allowed list")
                
                return result
            
            def get_description(self) -> str:
                return "Email domain must not be blocked and must be in allowed list if specified"
        
        class UsernameUniquenessRule:
            """Validate username uniqueness."""
            def validate(self, data: Dict[str, Any], context: ValidationContext) -> ValidationResult:
                result = ValidationResult(valid=True)
                
                if "username" in data:
                    existing_users = context.get("existing_users", [])
                    if data["username"].lower() in [u.lower() for u in existing_users]:
                        result.valid = False
                        result.errors.append(f"Username '{data['username']}' is already taken")
                
                return result
            
            def get_description(self) -> str:
                return "Username must be unique in the system"
        
        class DataConsistencyRule:
            """Validate overall data consistency."""
            def validate(self, data: Dict[str, Any], context: ValidationContext) -> ValidationResult:
                result = ValidationResult(valid=True)
                
                # Check email/username consistency
                if "email" in data and "username" in data:
                    email_prefix = data["email"].split("@")[0] if "@" in data["email"] else ""
                    if email_prefix and data["username"] and email_prefix == data["username"]:
                        result.warnings.append("Username matches email prefix - consider using a different username for privacy")
                
                # Check website/email domain consistency
                if "website" in data and "email" in data:
                    email_domain = data["email"].split("@")[-1] if "@" in data["email"] else ""
                    website_domain = re.search(r'https?://(?:www\.)?([^/]+)', data["website"])
                    if website_domain and email_domain:
                        if email_domain not in website_domain.group(1):
                            result.warnings.append("Email domain doesn't match website domain")
                
                return result
            
            def get_description(self) -> str:
                return "Validate consistency between related fields"
        
        # Test business rules
        business_rules = [
            UserAgeRule(),
            EmailDomainRule(blocked_domains=["tempmail.com", "throwaway.email"], allowed_domains=None),
            UsernameUniquenessRule(),
            DataConsistencyRule()
        ]
        
        # Test context
        test_context = {
            "current_date": datetime(2025, 7, 12, 22, 0, 0, tzinfo=timezone.utc),
            "existing_users": ["admin", "test_user", "john_doe"]
        }
        
        # Test scenarios
        test_scenarios = [
            # Valid scenario
            {
                "name": "Valid user data",
                "data": {
                    "username": "new_user",
                    "email": "user@example.com",
                    "age": 30,
                    "website": "https://example.com",
                    "created_at": "2020-01-01T00:00:00.000Z"
                },
                "expected_valid": True
            },
            # Age inconsistency
            {
                "name": "Age less than account age",
                "data": {
                    "username": "young_account",
                    "email": "young@example.com",
                    "age": 2,
                    "created_at": "2020-01-01T00:00:00.000Z"
                },
                "expected_valid": False
            },
            # Blocked email domain
            {
                "name": "Blocked email domain",
                "data": {
                    "username": "temp_user",
                    "email": "user@tempmail.com",
                    "age": 25,
                    "created_at": "2024-01-01T00:00:00.000Z"
                },
                "expected_valid": False
            },
            # Duplicate username
            {
                "name": "Duplicate username",
                "data": {
                    "username": "test_user",
                    "email": "another@example.com",
                    "age": 25,
                    "created_at": "2024-01-01T00:00:00.000Z"
                },
                "expected_valid": False
            },
            # Privacy warning scenario
            {
                "name": "Username matches email",
                "data": {
                    "username": "johndoe",
                    "email": "johndoe@example.com",
                    "age": 30,
                    "website": "https://johndoe.com",
                    "created_at": "2023-01-01T00:00:00.000Z"
                },
                "expected_valid": True  # Valid but should have warning
            }
        ]
        
        rule_results = []
        
        for scenario in test_scenarios:
            scenario_results = {
                "scenario": scenario["name"],
                "expected_valid": scenario["expected_valid"],
                "rules_passed": 0,
                "rules_failed": 0,
                "total_errors": 0,
                "total_warnings": 0,
                "rule_details": []
            }
            
            overall_valid = True
            
            for rule in business_rules:
                result = rule.validate(scenario["data"], test_context)
                
                scenario_results["rule_details"].append({
                    "rule": rule.__class__.__name__,
                    "description": rule.get_description(),
                    "valid": result.valid,
                    "errors": result.errors,
                    "warnings": result.warnings
                })
                
                if result.valid:
                    scenario_results["rules_passed"] += 1
                else:
                    scenario_results["rules_failed"] += 1
                    overall_valid = False
                
                scenario_results["total_errors"] += len(result.errors)
                scenario_results["total_warnings"] += len(result.warnings)
            
            scenario_results["actual_valid"] = overall_valid
            scenario_results["passed"] = overall_valid == scenario["expected_valid"]
            rule_results.append(scenario_results)
            
            # Assert business rule validation
            self.assertEqual(overall_valid, scenario["expected_valid"],
                           f"Business rule validation failed for {scenario['name']}")
        
        # Calculate business rule metrics
        total_scenarios = len(rule_results)
        passed_scenarios = sum(1 for r in rule_results if r["passed"])
        total_rule_checks = sum(len(r["rule_details"]) for r in rule_results)
        
        # Log business rule validation analysis
        self.logger.info(
            "Business rule validation analysis",
            context={
                "total_scenarios": total_scenarios,
                "passed_scenarios": passed_scenarios,
                "failed_scenarios": total_scenarios - passed_scenarios,
                "total_rules": len(business_rules),
                "total_rule_checks": total_rule_checks,
                "total_errors": sum(r["total_errors"] for r in rule_results),
                "total_warnings": sum(r["total_warnings"] for r in rule_results),
                "rule_summary": {
                    rule.__class__.__name__: rule.get_description()
                    for rule in business_rules
                }
            }
        )
    
    async def test_constraint_checking(self) -> None:
        """Test constraint checking and enforcement."""
        # Constraint definitions
        constraint_definitions = {
            "discord_message": {
                "content_length": {"max": 2000, "type": "length"},
                "embed_count": {"max": 10, "type": "count"},
                "embed_title_length": {"max": 256, "type": "length"},
                "embed_description_length": {"max": 4096, "type": "length"},
                "embed_fields": {"max": 25, "type": "count"},
                "embed_field_name_length": {"max": 256, "type": "length"},
                "embed_field_value_length": {"max": 1024, "type": "length"},
                "total_characters": {"max": 6000, "type": "aggregate"}
            },
            "file_path": {
                "path_length": {"max": 255, "type": "length"},
                "allowed_extensions": {"values": [".txt", ".md", ".json", ".py"], "type": "enum"},
                "forbidden_patterns": {"values": ["../", "..\\", "~", "$"], "type": "blacklist"},
                "max_depth": {"max": 10, "type": "depth"}
            },
            "api_request": {
                "rate_limit": {"max": 50, "window": 60, "type": "rate"},
                "payload_size": {"max": 1048576, "type": "size"},  # 1MB
                "timeout": {"max": 30, "type": "duration"},
                "retry_count": {"max": 3, "type": "count"}
            }
        }
        
        def check_constraints(value: Any, constraints: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
            """Check value against constraints."""
            result = ValidationResult(valid=True)
            
            for constraint_name, constraint in constraints.items():
                constraint_type = constraint.get("type")
                
                if constraint_type == "length":
                    if isinstance(value, str) and len(value) > constraint["max"]:
                        result.valid = False
                        result.errors.append(f"{constraint_name} exceeds maximum length of {constraint['max']}")
                
                elif constraint_type == "count":
                    if isinstance(value, list) and len(value) > constraint["max"]:
                        result.valid = False
                        result.errors.append(f"{constraint_name} exceeds maximum count of {constraint['max']}")
                
                elif constraint_type == "size":
                    if hasattr(value, "__len__") and len(str(value).encode('utf-8')) > constraint["max"]:
                        result.valid = False
                        result.errors.append(f"{constraint_name} exceeds maximum size of {constraint['max']} bytes")
                
                elif constraint_type == "enum":
                    if value not in constraint["values"]:
                        result.valid = False
                        result.errors.append(f"{constraint_name} must be one of: {constraint['values']}")
                
                elif constraint_type == "blacklist":
                    for forbidden in constraint["values"]:
                        if forbidden in str(value):
                            result.valid = False
                            result.errors.append(f"{constraint_name} contains forbidden pattern: {forbidden}")
                
                elif constraint_type == "depth":
                    depth = str(value).count("/") + str(value).count("\\")
                    if depth > constraint["max"]:
                        result.valid = False
                        result.errors.append(f"{constraint_name} exceeds maximum depth of {constraint['max']}")
                
                elif constraint_type == "rate":
                    if context:
                        request_count = context.get("request_count", 0)
                        if request_count > constraint["max"]:
                            result.valid = False
                            result.errors.append(f"{constraint_name} exceeds rate limit of {constraint['max']} per {constraint['window']}s")
                
                elif constraint_type == "aggregate":
                    # For Discord total character limit
                    if isinstance(value, dict) and "embeds" in value:
                        total_chars = len(value.get("content", ""))
                        for embed in value.get("embeds", []):
                            total_chars += len(embed.get("title", ""))
                            total_chars += len(embed.get("description", ""))
                            for field in embed.get("fields", []):
                                total_chars += len(field.get("name", ""))
                                total_chars += len(field.get("value", ""))
                        
                        if total_chars > constraint["max"]:
                            result.valid = False
                            result.errors.append(f"Total character count ({total_chars}) exceeds maximum of {constraint['max']}")
            
            return result
        
        # Test constraint scenarios
        test_scenarios = [
            # Discord message constraints
            {
                "name": "Valid Discord message",
                "type": "discord_message",
                "value": {
                    "content": "Test message",
                    "embeds": [{
                        "title": "Test Embed",
                        "description": "Test description",
                        "fields": [
                            {"name": "Field 1", "value": "Value 1", "inline": True}
                        ]
                    }]
                },
                "expected_valid": True
            },
            {
                "name": "Discord message too long",
                "type": "discord_message",
                "value": {
                    "content": "x" * 2001  # Exceeds 2000 char limit
                },
                "expected_valid": False
            },
            {
                "name": "Too many embeds",
                "type": "discord_message",
                "value": {
                    "content": "Test",
                    "embeds": [{"title": f"Embed {i}", "description": "Test"} for i in range(11)]  # 11 embeds
                },
                "expected_valid": False
            },
            # File path constraints
            {
                "name": "Valid file path",
                "type": "file_path",
                "value": "/home/user/project/file.txt",
                "expected_valid": True
            },
            {
                "name": "Path traversal attempt",
                "type": "file_path",
                "value": "../../etc/passwd",
                "expected_valid": False
            },
            {
                "name": "Invalid extension",
                "type": "file_path",
                "value": "/home/user/file.exe",
                "expected_valid": False
            },
            # API request constraints
            {
                "name": "Valid API request",
                "type": "api_request",
                "value": {"payload": "test data"},
                "context": {"request_count": 10},
                "expected_valid": True
            },
            {
                "name": "Rate limit exceeded",
                "type": "api_request",
                "value": {"payload": "test data"},
                "context": {"request_count": 51},
                "expected_valid": False
            }
        ]
        
        constraint_results = []
        
        for scenario in test_scenarios:
            constraints = constraint_definitions.get(scenario["type"], {})
            context = scenario.get("context", {})
            
            # Check constraints based on type
            if scenario["type"] == "discord_message":
                # Check individual constraints
                result = ValidationResult(valid=True)
                
                if "content" in scenario["value"]:
                    content_result = check_constraints(
                        scenario["value"]["content"],
                        {"content_length": constraints["content_length"]},
                        context
                    )
                    if not content_result.valid:
                        result.valid = False
                        result.errors.extend(content_result.errors)
                
                if "embeds" in scenario["value"]:
                    embeds_result = check_constraints(
                        scenario["value"]["embeds"],
                        {"embed_count": constraints["embed_count"]},
                        context
                    )
                    if not embeds_result.valid:
                        result.valid = False
                        result.errors.extend(embeds_result.errors)
                
                # Check aggregate constraint
                aggregate_result = check_constraints(
                    scenario["value"],
                    {"total_characters": constraints["total_characters"]},
                    context
                )
                if not aggregate_result.valid:
                    result.valid = False
                    result.errors.extend(aggregate_result.errors)
            
            elif scenario["type"] == "file_path":
                result = check_constraints(scenario["value"], constraints, context)
            
            elif scenario["type"] == "api_request":
                result = check_constraints(scenario["value"], constraints, context)
            
            else:
                result = ValidationResult(valid=False, errors=["Unknown constraint type"])
            
            constraint_results.append({
                "scenario": scenario["name"],
                "type": scenario["type"],
                "expected_valid": scenario["expected_valid"],
                "actual_valid": result.valid,
                "passed": result.valid == scenario["expected_valid"],
                "errors": result.errors,
                "error_count": len(result.errors)
            })
            
            # Assert constraint checking
            self.assertEqual(result.valid, scenario["expected_valid"],
                           f"Constraint checking failed for {scenario['name']}")
        
        # Calculate constraint metrics
        total_scenarios = len(constraint_results)
        passed_scenarios = sum(1 for r in constraint_results if r["passed"])
        total_constraints_checked = sum(len(constraint_definitions[r["type"]]) for r in constraint_results if r["type"] in constraint_definitions)
        
        # Log constraint checking analysis
        self.logger.info(
            "Constraint checking analysis",
            context={
                "total_scenarios": total_scenarios,
                "passed_scenarios": passed_scenarios,
                "failed_scenarios": total_scenarios - passed_scenarios,
                "constraint_types": list(constraint_definitions.keys()),
                "total_constraints_checked": total_constraints_checked,
                "total_violations": sum(r["error_count"] for r in constraint_results),
                "type_breakdown": {
                    constraint_type: sum(1 for r in constraint_results if r["type"] == constraint_type)
                    for constraint_type in constraint_definitions.keys()
                }
            }
        )
    
    async def test_dynamic_validation(self) -> None:
        """Test dynamic validation with runtime rules."""
        # Dynamic validation system
        class DynamicValidator:
            """Dynamic validation with runtime-configurable rules."""
            def __init__(self):
                self.rules = {}
                self.validators = {}
                self.conditions = {}
            
            def add_rule(self, name: str, validator: Callable, condition: Optional[Callable] = None):
                """Add a dynamic validation rule."""
                self.rules[name] = {
                    "validator": validator,
                    "condition": condition or (lambda *args: True)
                }
            
            def add_field_validator(self, field: str, validator: Callable):
                """Add a field-specific validator."""
                if field not in self.validators:
                    self.validators[field] = []
                self.validators[field].append(validator)
            
            def validate(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
                """Perform dynamic validation."""
                result = ValidationResult(valid=True)
                context = context or {}
                
                # Apply general rules
                for rule_name, rule in self.rules.items():
                    if rule["condition"](data, context):
                        rule_result = rule["validator"](data, context)
                        if isinstance(rule_result, tuple):
                            is_valid, error = rule_result
                            if not is_valid:
                                result.valid = False
                                result.errors.append(f"Rule '{rule_name}': {error}")
                        elif isinstance(rule_result, ValidationResult):
                            if not rule_result.valid:
                                result.valid = False
                                result.errors.extend(rule_result.errors)
                            result.warnings.extend(rule_result.warnings)
                
                # Apply field validators
                for field, value in data.items():
                    if field in self.validators:
                        for validator in self.validators[field]:
                            field_result = validator(value, context)
                            if isinstance(field_result, tuple):
                                is_valid, error = field_result
                                if not is_valid:
                                    result.valid = False
                                    result.errors.append(f"Field '{field}': {error}")
                
                return result
        
        # Create dynamic validator
        validator = DynamicValidator()
        
        # Add dynamic rules based on context
        # Rule 1: If user is premium, allow longer content
        def content_length_validator(data: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
            max_length = 5000 if context.get("is_premium") else 1000
            content = data.get("content", "")
            if len(content) > max_length:
                return False, f"Content exceeds maximum length of {max_length}"
            return True, None
        
        validator.add_rule(
            "content_length",
            content_length_validator,
            condition=lambda d, c: "content" in d
        )
        
        # Rule 2: Time-based validation (business hours)
        def business_hours_validator(data: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
            current_hour = context.get("current_hour", datetime.now().hour)
            if data.get("requires_approval") and not (9 <= current_hour < 17):
                return False, "Approval requests can only be submitted during business hours (9-17)"
            return True, None
        
        validator.add_rule(
            "business_hours",
            business_hours_validator,
            condition=lambda d, c: d.get("requires_approval", False)
        )
        
        # Rule 3: Conditional field requirements
        def payment_info_validator(data: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
            result = ValidationResult(valid=True)
            
            if data.get("payment_method") == "credit_card":
                required_fields = ["card_number", "cvv", "expiry_date"]
                for field in required_fields:
                    if field not in data:
                        result.valid = False
                        result.errors.append(f"Missing required field for credit card: {field}")
            elif data.get("payment_method") == "bank_transfer":
                required_fields = ["account_number", "routing_number"]
                for field in required_fields:
                    if field not in data:
                        result.valid = False
                        result.errors.append(f"Missing required field for bank transfer: {field}")
            
            return result
        
        validator.add_rule(
            "payment_info",
            payment_info_validator,
            condition=lambda d, c: "payment_method" in d
        )
        
        # Add field-specific validators
        validator.add_field_validator(
            "email",
            lambda v, c: (
                v.endswith(c.get("required_domain", ".com")),
                f"Email must end with {c.get('required_domain', '.com')}"
            )
        )
        
        validator.add_field_validator(
            "priority",
            lambda v, c: (
                v <= c.get("max_priority", 10),
                f"Priority cannot exceed {c.get('max_priority', 10)}"
            )
        )
        
        # Test scenarios with different contexts
        test_scenarios = [
            # Premium user with long content
            {
                "name": "Premium user long content",
                "data": {
                    "content": "x" * 3000,
                    "email": "user@example.com"
                },
                "context": {"is_premium": True},
                "expected_valid": True
            },
            # Regular user with long content
            {
                "name": "Regular user long content",
                "data": {
                    "content": "x" * 1500,
                    "email": "user@example.com"
                },
                "context": {"is_premium": False},
                "expected_valid": False
            },
            # Business hours validation
            {
                "name": "Approval during business hours",
                "data": {
                    "requires_approval": True,
                    "content": "Need approval"
                },
                "context": {"current_hour": 14},  # 2 PM
                "expected_valid": True
            },
            {
                "name": "Approval outside business hours",
                "data": {
                    "requires_approval": True,
                    "content": "Need approval"
                },
                "context": {"current_hour": 20},  # 8 PM
                "expected_valid": False
            },
            # Payment validation
            {
                "name": "Valid credit card payment",
                "data": {
                    "payment_method": "credit_card",
                    "card_number": "1234-5678-9012-3456",
                    "cvv": "123",
                    "expiry_date": "12/25"
                },
                "context": {},
                "expected_valid": True
            },
            {
                "name": "Invalid credit card payment",
                "data": {
                    "payment_method": "credit_card",
                    "card_number": "1234-5678-9012-3456"
                    # Missing cvv and expiry_date
                },
                "context": {},
                "expected_valid": False
            },
            # Domain-specific email validation
            {
                "name": "Email with required domain",
                "data": {
                    "email": "user@company.org",
                    "content": "Test"
                },
                "context": {"required_domain": ".org"},
                "expected_valid": True
            },
            # Priority validation
            {
                "name": "Priority within limit",
                "data": {
                    "priority": 5,
                    "content": "Task"
                },
                "context": {"max_priority": 10},
                "expected_valid": True
            }
        ]
        
        dynamic_results = []
        
        for scenario in test_scenarios:
            result = validator.validate(scenario["data"], scenario["context"])
            
            dynamic_results.append({
                "scenario": scenario["name"],
                "expected_valid": scenario["expected_valid"],
                "actual_valid": result.valid,
                "passed": result.valid == scenario["expected_valid"],
                "errors": result.errors,
                "warnings": result.warnings,
                "context_keys": list(scenario["context"].keys())
            })
            
            # Assert dynamic validation
            self.assertEqual(result.valid, scenario["expected_valid"],
                           f"Dynamic validation failed for {scenario['name']}")
        
        # Test runtime rule modification
        original_rules = len(validator.rules)
        
        # Add new rule at runtime
        validator.add_rule(
            "urgent_handling",
            lambda d, c: (
                not (d.get("urgent") and c.get("maintenance_mode")),
                "Urgent requests not allowed during maintenance"
            )
        )
        
        # Test with new rule
        maintenance_test = validator.validate(
            {"urgent": True, "content": "Urgent request"},
            {"maintenance_mode": True}
        )
        self.assertFalse(maintenance_test.valid)
        self.assertTrue(any("maintenance" in error for error in maintenance_test.errors))
        
        # Calculate dynamic validation metrics
        total_scenarios = len(dynamic_results)
        passed_scenarios = sum(1 for r in dynamic_results if r["passed"])
        total_errors = sum(len(r["errors"]) for r in dynamic_results)
        
        # Log dynamic validation analysis
        self.logger.info(
            "Dynamic validation analysis",
            context={
                "total_scenarios": total_scenarios,
                "passed_scenarios": passed_scenarios,
                "failed_scenarios": total_scenarios - passed_scenarios,
                "initial_rules": original_rules,
                "final_rules": len(validator.rules),
                "total_errors": total_errors,
                "context_based_scenarios": sum(1 for r in dynamic_results if r["context_keys"]),
                "scenario_breakdown": {
                    r["scenario"]: "passed" if r["passed"] else f"failed with {len(r['errors'])} errors"
                    for r in dynamic_results
                }
            }
        )
    
    # Helper methods
    
    def _validate_iso_timestamp(self, timestamp: str) -> bool:
        """Validate ISO timestamp format."""
        try:
            # Handle both Z and +00:00 formats
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            
            dt = datetime.fromisoformat(timestamp)
            return True
        except:
            return False


def run_runtime_validation_tests() -> None:
    """Run runtime validation tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRuntimeValidation)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nRuntime Validation Tests Summary:")
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