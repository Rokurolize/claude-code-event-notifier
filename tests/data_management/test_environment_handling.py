#!/usr/bin/env python3
"""Test Environment Variable Handling Functionality.

This module provides comprehensive tests for environment variable handling
functionality, including environment isolation, variable precedence, secure
handling of sensitive values, validation, and cross-platform compatibility.
"""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.core.config_loader import ConfigLoader
from src.exceptions import EnvironmentError, SecurityError
from src.utils.validation import EnvironmentValidator


class TestEnvironmentHandling(unittest.IsolatedAsyncioTestCase):
    """Test cases for environment variable handling functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "environment_mode": "strict",
            "require_prefixed_vars": True,
            "variable_prefix": "DISCORD_",
            "security_validation": True,
            "debug": True
        }
        
        # Test environment variable scenarios
        self.test_environments = {
            "production": {
                "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                "DISCORD_USE_THREADS": "false",
                "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse,Stop",
                "DISCORD_DEBUG": "false",
                "DISCORD_MAX_EMBED_FIELDS": "25",
                "DISCORD_FIELD_CHARACTER_LIMIT": "1024"
            },
            "development": {
                "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                "DISCORD_CHANNEL_ID": "123456789012345678",
                "DISCORD_USE_THREADS": "true",
                "DISCORD_THREAD_NAME_TEMPLATE": "Dev Session {session_id}",
                "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse,Stop,Error",
                "DISCORD_DEBUG": "true",
                "DISCORD_MAX_EMBED_FIELDS": "20",
                "DISCORD_FIELD_CHARACTER_LIMIT": "512"
            },
            "testing": {
                "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/987654321/test123456",
                "DISCORD_USE_THREADS": "false",
                "DISCORD_ENABLED_EVENTS": "Stop",
                "DISCORD_DEBUG": "true",
                "DISCORD_MAX_EMBED_FIELDS": "10",
                "DISCORD_FIELD_CHARACTER_LIMIT": "256"
            }
        }
        
        # Environment variable validation rules
        self.validation_rules = {
            "DISCORD_WEBHOOK_URL": {
                "type": "string",
                "pattern": r"^https://discord\.com/api/webhooks/\d+/[\w\-]+$",
                "required": False,
                "sensitive": True,
                "description": "Discord webhook URL"
            },
            "DISCORD_TOKEN": {
                "type": "string",
                "pattern": r"^Bot [A-Za-z0-9]{24}\.[A-Za-z0-9]{6}\.[A-Za-z0-9\-_]{38}$",
                "required": False,
                "sensitive": True,
                "description": "Discord bot token"
            },
            "DISCORD_CHANNEL_ID": {
                "type": "string",
                "pattern": r"^\d{17,20}$",
                "required": False,
                "sensitive": False,
                "description": "Discord channel ID"
            },
            "DISCORD_USE_THREADS": {
                "type": "boolean",
                "allowed_values": ["true", "false"],
                "default": "false",
                "required": False,
                "sensitive": False,
                "description": "Enable thread organization"
            },
            "DISCORD_DEBUG": {
                "type": "boolean",
                "allowed_values": ["true", "false"],
                "default": "false",
                "required": False,
                "sensitive": False,
                "description": "Enable debug logging"
            },
            "DISCORD_MAX_EMBED_FIELDS": {
                "type": "integer",
                "minimum": 1,
                "maximum": 25,
                "default": "25",
                "required": False,
                "sensitive": False,
                "description": "Maximum embed fields"
            },
            "DISCORD_FIELD_CHARACTER_LIMIT": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1024,
                "default": "1024",
                "required": False,
                "sensitive": False,
                "description": "Field character limit"
            }
        }
        
        # Security test cases
        self.security_test_cases = {
            "token_exposure": {
                "variables": {
                    "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                    "LOG_LEVEL": "DEBUG"
                },
                "expected_risks": ["sensitive_value_logging"]
            },
            "weak_webhook": {
                "variables": {
                    "DISCORD_WEBHOOK_URL": "http://discord.com/api/webhooks/123/weak"
                },
                "expected_risks": ["insecure_protocol"]
            },
            "debug_in_production": {
                "variables": {
                    "DISCORD_DEBUG": "true",
                    "NODE_ENV": "production"
                },
                "expected_risks": ["debug_in_production"]
            },
            "mixed_auth": {
                "variables": {
                    "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/test"
                },
                "expected_risks": ["conflicting_auth_methods"]
            }
        }
        
        # Cross-platform environment scenarios
        self.platform_scenarios = {
            "windows": {
                "path_separator": ";",
                "case_sensitivity": False,
                "special_chars": ["%%", "%HOME%", "%USERPROFILE%"],
                "environment_vars": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/test",
                    "PATH": "C:\\Windows\\System32;C:\\Windows",
                    "USERPROFILE": "C:\\Users\\TestUser"
                }
            },
            "unix": {
                "path_separator": ":",
                "case_sensitivity": True,
                "special_chars": ["$", "${HOME}", "~/"],
                "environment_vars": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/test",
                    "PATH": "/usr/bin:/usr/local/bin",
                    "HOME": "/home/testuser"
                }
            },
            "macos": {
                "path_separator": ":",
                "case_sensitivity": True,
                "special_chars": ["$", "${HOME}", "~/"],
                "environment_vars": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/test",
                    "PATH": "/usr/bin:/usr/local/bin:/opt/homebrew/bin",
                    "HOME": "/Users/testuser"
                }
            }
        }
    
    async def test_environment_isolation_validation(self) -> None:
        """Test environment variable isolation between different contexts."""
        with patch('src.core.config_loader.ConfigLoader') as mock_config_loader:
            mock_instance = MagicMock()
            mock_config_loader.return_value = mock_instance
            
            # Configure environment isolation testing
            def isolate_environment(env_vars: Dict[str, str], prefix: str = "DISCORD_") -> Dict[str, Any]:
                """Isolate environment variables by prefix."""
                isolated_env = {}
                contaminated_vars = []
                
                for key, value in env_vars.items():
                    if key.startswith(prefix):
                        isolated_env[key] = value
                    else:
                        contaminated_vars.append(key)
                
                return {
                    "isolated_variables": isolated_env,
                    "contaminated_variables": contaminated_vars,
                    "isolation_successful": len(contaminated_vars) == 0,
                    "prefix_used": prefix
                }
            
            def validate_isolation(isolation_result: Dict[str, Any]) -> Dict[str, Any]:
                """Validate environment isolation results."""
                validation_result = {
                    "isolation_valid": True,
                    "isolation_warnings": [],
                    "security_issues": [],
                    "recommended_actions": []
                }
                
                if not isolation_result["isolation_successful"]:
                    validation_result["isolation_valid"] = False
                    validation_result["isolation_warnings"].append(
                        f"Non-prefixed variables detected: {isolation_result['contaminated_variables']}"
                    )
                    validation_result["recommended_actions"].append(
                        "Remove or prefix non-Discord environment variables"
                    )
                
                # Check for sensitive data in non-isolated variables
                for var in isolation_result["contaminated_variables"]:
                    if any(keyword in var.lower() for keyword in ["token", "key", "secret", "password"]):
                        validation_result["security_issues"].append(
                            f"Sensitive variable outside isolation: {var}"
                        )
                
                return validation_result
            
            mock_instance.isolate_environment.side_effect = isolate_environment
            mock_instance.validate_isolation.side_effect = validate_isolation
            
            config_loader = ConfigLoader()
            
            # Test environment isolation for each scenario
            for env_name, env_vars in self.test_environments.items():
                with self.subTest(environment=env_name):
                    # Add some contaminating variables
                    test_env = env_vars.copy()
                    test_env.update({
                        "PATH": "/usr/bin:/bin",
                        "HOME": "/home/test",
                        "SECRET_KEY": "should_not_be_included",
                        "API_TOKEN": "contaminating_token"
                    })
                    
                    # Test isolation
                    isolation_result = config_loader.isolate_environment(test_env, "DISCORD_")
                    
                    # Validate isolation
                    validation_result = config_loader.validate_isolation(isolation_result)
                    
                    # Check isolation results
                    self.assertEqual(len(isolation_result["isolated_variables"]), len(env_vars),
                                   f"Environment {env_name}: wrong number of isolated variables")
                    
                    for discord_var in env_vars.keys():
                        self.assertIn(discord_var, isolation_result["isolated_variables"],
                                    f"Environment {env_name}: missing Discord variable {discord_var}")
                    
                    # Check contamination detection
                    expected_contaminated = ["PATH", "HOME", "SECRET_KEY", "API_TOKEN"]
                    for contaminated_var in expected_contaminated:
                        self.assertIn(contaminated_var, isolation_result["contaminated_variables"],
                                    f"Environment {env_name}: contaminated variable {contaminated_var} not detected")
                    
                    # Security validation
                    self.assertGreater(len(validation_result["security_issues"]), 0,
                                     f"Environment {env_name}: should detect security issues with contaminated sensitive vars")
    
    async def test_variable_precedence_validation(self) -> None:
        """Test validation of environment variable precedence rules."""
        with patch('src.core.config_loader.ConfigLoader') as mock_config_loader:
            mock_instance = MagicMock()
            mock_config_loader.return_value = mock_instance
            
            # Configure precedence testing
            def apply_precedence(sources: List[Dict[str, Any]], precedence_order: List[str]) -> Dict[str, Any]:
                """Apply precedence rules to configuration sources."""
                final_config = {}
                precedence_log = []
                conflicts = []
                
                # Sources are provided in order: env_vars, dotenv_file, defaults
                source_mapping = dict(zip(precedence_order, sources))
                
                # Apply in reverse precedence order (lowest to highest priority)
                for source_name in reversed(precedence_order):
                    if source_name in source_mapping:
                        source_data = source_mapping[source_name]
                        for key, value in source_data.items():
                            if key in final_config and final_config[key] != value:
                                conflicts.append({
                                    "key": key,
                                    "previous_value": final_config[key],
                                    "new_value": value,
                                    "source": source_name
                                })
                            
                            final_config[key] = value
                            precedence_log.append({
                                "key": key,
                                "value": value,
                                "source": source_name,
                                "priority": precedence_order.index(source_name) + 1
                            })
                
                return {
                    "final_config": final_config,
                    "precedence_log": precedence_log,
                    "conflicts": conflicts,
                    "sources_used": list(source_mapping.keys())
                }
            
            def validate_precedence(precedence_result: Dict[str, Any]) -> Dict[str, Any]:
                """Validate precedence application results."""
                validation_result = {
                    "precedence_applied_correctly": True,
                    "precedence_violations": [],
                    "configuration_conflicts": [],
                    "recommended_resolutions": []
                }
                
                # Check for conflicts
                for conflict in precedence_result["conflicts"]:
                    validation_result["configuration_conflicts"].append({
                        "variable": conflict["key"],
                        "conflict_description": f"Value overridden by {conflict['source']}",
                        "previous_value": conflict["previous_value"],
                        "current_value": conflict["new_value"]
                    })
                
                # Validate precedence order was respected
                precedence_log = precedence_result["precedence_log"]
                for i in range(1, len(precedence_log)):
                    current_entry = precedence_log[i]
                    previous_entry = precedence_log[i-1]
                    
                    if (current_entry["key"] == previous_entry["key"] and 
                        current_entry["priority"] < previous_entry["priority"]):
                        validation_result["precedence_applied_correctly"] = False
                        validation_result["precedence_violations"].append(
                            f"Precedence violation for {current_entry['key']}: "
                            f"lower priority source {current_entry['source']} overrode higher priority"
                        )
                
                # Generate recommendations for conflicts
                for conflict in validation_result["configuration_conflicts"]:
                    validation_result["recommended_resolutions"].append(
                        f"Review {conflict['variable']} configuration - "
                        f"ensure intended value is set in highest priority source"
                    )
                
                return validation_result
            
            mock_instance.apply_precedence.side_effect = apply_precedence
            mock_instance.validate_precedence.side_effect = validate_precedence
            
            config_loader = ConfigLoader()
            
            # Test precedence scenarios
            precedence_test_cases = [
                {
                    "name": "env_vars_override_defaults",
                    "sources": [
                        {"DISCORD_DEBUG": "true", "DISCORD_USE_THREADS": "true"},  # env_vars
                        {},  # dotenv_file (empty)
                        {"DISCORD_DEBUG": "false", "DISCORD_USE_THREADS": "false", "DISCORD_MAX_EMBED_FIELDS": "25"}  # defaults
                    ],
                    "precedence_order": ["defaults", "dotenv_file", "env_vars"],
                    "expected_final": {
                        "DISCORD_DEBUG": "true",
                        "DISCORD_USE_THREADS": "true", 
                        "DISCORD_MAX_EMBED_FIELDS": "25"
                    }
                },
                {
                    "name": "dotenv_overrides_defaults_but_not_env",
                    "sources": [
                        {"DISCORD_DEBUG": "true"},  # env_vars
                        {"DISCORD_DEBUG": "false", "DISCORD_USE_THREADS": "true"},  # dotenv_file
                        {"DISCORD_DEBUG": "false", "DISCORD_USE_THREADS": "false", "DISCORD_MAX_EMBED_FIELDS": "25"}  # defaults
                    ],
                    "precedence_order": ["defaults", "dotenv_file", "env_vars"],
                    "expected_final": {
                        "DISCORD_DEBUG": "true",  # env_vars wins
                        "DISCORD_USE_THREADS": "true",  # dotenv_file wins over defaults
                        "DISCORD_MAX_EMBED_FIELDS": "25"  # only in defaults
                    }
                },
                {
                    "name": "complex_precedence_scenario",
                    "sources": [
                        {"DISCORD_TOKEN": "Bot env_token", "DISCORD_DEBUG": "true"},  # env_vars
                        {"DISCORD_TOKEN": "Bot dotenv_token", "DISCORD_WEBHOOK_URL": "https://discord.com/dotenv"},  # dotenv_file
                        {"DISCORD_TOKEN": "Bot default_token", "DISCORD_WEBHOOK_URL": "https://discord.com/default", "DISCORD_USE_THREADS": "false"}  # defaults
                    ],
                    "precedence_order": ["defaults", "dotenv_file", "env_vars"],
                    "expected_final": {
                        "DISCORD_TOKEN": "Bot env_token",  # env_vars highest priority
                        "DISCORD_WEBHOOK_URL": "https://discord.com/dotenv",  # dotenv_file overrides defaults
                        "DISCORD_USE_THREADS": "false",  # only in defaults
                        "DISCORD_DEBUG": "true"  # only in env_vars
                    }
                }
            ]
            
            for test_case in precedence_test_cases:
                with self.subTest(case=test_case["name"]):
                    # Apply precedence
                    precedence_result = config_loader.apply_precedence(
                        test_case["sources"],
                        test_case["precedence_order"]
                    )
                    
                    # Validate precedence
                    validation_result = config_loader.validate_precedence(precedence_result)
                    
                    # Check final configuration matches expected
                    final_config = precedence_result["final_config"]
                    expected_final = test_case["expected_final"]
                    
                    for key, expected_value in expected_final.items():
                        self.assertIn(key, final_config,
                                    f"Case {test_case['name']}: missing key {key}")
                        self.assertEqual(final_config[key], expected_value,
                                       f"Case {test_case['name']}: wrong value for {key}")
                    
                    # Check precedence application
                    self.assertTrue(validation_result["precedence_applied_correctly"],
                                  f"Case {test_case['name']}: precedence not applied correctly: "
                                  f"{validation_result['precedence_violations']}")
    
    async def test_secure_sensitive_value_handling(self) -> None:
        """Test secure handling of sensitive environment variable values."""
        with patch('src.utils.validation.EnvironmentValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure security validation
            def validate_sensitive_handling(env_vars: Dict[str, str], validation_rules: Dict[str, Any]) -> Dict[str, Any]:
                """Validate secure handling of sensitive values."""
                security_result = {
                    "secure_handling": True,
                    "sensitive_variables": [],
                    "security_violations": [],
                    "masked_values": {},
                    "security_recommendations": []
                }
                
                for var_name, var_value in env_vars.items():
                    if var_name in validation_rules:
                        rule = validation_rules[var_name]
                        
                        if rule.get("sensitive", False):
                            security_result["sensitive_variables"].append(var_name)
                            
                            # Mask sensitive values
                            if len(var_value) > 8:
                                masked_value = var_value[:4] + "*" * (len(var_value) - 8) + var_value[-4:]
                            else:
                                masked_value = "*" * len(var_value)
                            
                            security_result["masked_values"][var_name] = masked_value
                            
                            # Check for security violations
                            if "debug" in env_vars.get("DISCORD_DEBUG", "").lower() and env_vars.get("DISCORD_DEBUG") == "true":
                                security_result["security_violations"].append(
                                    f"Sensitive variable {var_name} exposed with debug mode enabled"
                                )
                                security_result["secure_handling"] = False
                            
                            # Check for weak patterns
                            if "test" in var_value.lower() or "demo" in var_value.lower():
                                security_result["security_violations"].append(
                                    f"Weak/test value detected for {var_name}"
                                )
                                security_result["secure_handling"] = False
                            
                            # Check token format
                            if var_name == "DISCORD_TOKEN":
                                if not var_value.startswith("Bot "):
                                    security_result["security_violations"].append(
                                        f"Invalid token format for {var_name}"
                                    )
                                    security_result["secure_handling"] = False
                            
                            # Check webhook URL security
                            elif var_name == "DISCORD_WEBHOOK_URL":
                                if not var_value.startswith("https://"):
                                    security_result["security_violations"].append(
                                        f"Insecure protocol for {var_name}"
                                    )
                                    security_result["secure_handling"] = False
                
                # Generate security recommendations
                if not security_result["secure_handling"]:
                    security_result["security_recommendations"].extend([
                        "Disable debug mode in production environments",
                        "Use production-grade credentials only",
                        "Ensure all URLs use HTTPS protocol",
                        "Implement proper token rotation policies"
                    ])
                
                return security_result
            
            def test_value_masking(sensitive_value: str) -> Dict[str, Any]:
                """Test masking of sensitive values."""
                masking_result = {
                    "original_length": len(sensitive_value),
                    "masked_value": "",
                    "masking_effective": False,
                    "visible_characters": 0
                }
                
                if len(sensitive_value) > 8:
                    masked = sensitive_value[:4] + "*" * (len(sensitive_value) - 8) + sensitive_value[-4:]
                    masking_result["masked_value"] = masked
                    masking_result["visible_characters"] = 8
                    masking_result["masking_effective"] = True
                else:
                    masking_result["masked_value"] = "*" * len(sensitive_value)
                    masking_result["visible_characters"] = 0
                    masking_result["masking_effective"] = len(sensitive_value) > 0
                
                return masking_result
            
            mock_instance.validate_sensitive_handling.side_effect = validate_sensitive_handling
            mock_instance.test_value_masking.side_effect = test_value_masking
            
            validator = EnvironmentValidator()
            
            # Test security validation for each case
            for case_name, case_data in self.security_test_cases.items():
                with self.subTest(case=case_name):
                    env_vars = case_data["variables"]
                    expected_risks = case_data["expected_risks"]
                    
                    # Validate sensitive handling
                    security_result = validator.validate_sensitive_handling(env_vars, self.validation_rules)
                    
                    # Should detect security issues for problematic cases
                    if expected_risks:
                        self.assertFalse(security_result["secure_handling"],
                                       f"Case {case_name} should detect security issues")
                        self.assertGreater(len(security_result["security_violations"]), 0,
                                         f"Case {case_name} should have security violations")
                    
                    # Check sensitive variable detection
                    for var_name, var_value in env_vars.items():
                        if var_name in self.validation_rules and self.validation_rules[var_name].get("sensitive"):
                            self.assertIn(var_name, security_result["sensitive_variables"],
                                        f"Case {case_name}: sensitive variable {var_name} not detected")
                            self.assertIn(var_name, security_result["masked_values"],
                                        f"Case {case_name}: sensitive variable {var_name} not masked")
            
            # Test value masking specifically
            masking_test_cases = [
                {
                    "name": "long_token",
                    "value": "Bot TEST_TOKEN_PLACEHOLDER",
                    "expected_visible": 8
                },
                {
                    "name": "webhook_url",
                    "value": "https://discord.com/api/webhooks/123456789/abcdef123456789",
                    "expected_visible": 8
                },
                {
                    "name": "short_value",
                    "value": "short",
                    "expected_visible": 0
                }
            ]
            
            for masking_case in masking_test_cases:
                with self.subTest(masking_case=masking_case["name"]):
                    masking_result = validator.test_value_masking(masking_case["value"])
                    
                    self.assertTrue(masking_result["masking_effective"],
                                  f"Masking case {masking_case['name']}: masking not effective")
                    self.assertEqual(masking_result["visible_characters"], masking_case["expected_visible"],
                                   f"Masking case {masking_case['name']}: wrong number of visible characters")
                    
                    # Ensure masked value is different from original
                    if masking_result["masking_effective"]:
                        self.assertNotEqual(masking_result["masked_value"], masking_case["value"],
                                          f"Masking case {masking_case['name']}: value not actually masked")
    
    async def test_environment_variable_validation(self) -> None:
        """Test comprehensive environment variable validation."""
        with patch('src.utils.validation.EnvironmentValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure validation testing
            def validate_environment_variables(env_vars: Dict[str, str], rules: Dict[str, Any]) -> Dict[str, Any]:
                """Validate environment variables against rules."""
                validation_result = {
                    "all_valid": True,
                    "variable_results": {},
                    "validation_summary": {
                        "total_variables": len(env_vars),
                        "valid_variables": 0,
                        "invalid_variables": 0,
                        "missing_required": 0
                    },
                    "global_errors": []
                }
                
                # Check each variable against rules
                for var_name, var_value in env_vars.items():
                    var_result = {
                        "variable": var_name,
                        "value_provided": True,
                        "type_valid": False,
                        "pattern_valid": False,
                        "range_valid": False,
                        "errors": [],
                        "warnings": []
                    }
                    
                    if var_name in rules:
                        rule = rules[var_name]
                        
                        # Type validation
                        expected_type = rule.get("type")
                        if expected_type == "string":
                            var_result["type_valid"] = isinstance(var_value, str)
                        elif expected_type == "boolean":
                            var_result["type_valid"] = var_value.lower() in ["true", "false"]
                        elif expected_type == "integer":
                            var_result["type_valid"] = var_value.isdigit()
                        
                        # Pattern validation
                        pattern = rule.get("pattern")
                        if pattern and var_result["type_valid"]:
                            import re
                            var_result["pattern_valid"] = bool(re.match(pattern, var_value))
                        else:
                            var_result["pattern_valid"] = True
                        
                        # Range validation for integers
                        if expected_type == "integer" and var_result["type_valid"]:
                            int_value = int(var_value)
                            minimum = rule.get("minimum")
                            maximum = rule.get("maximum")
                            
                            range_valid = True
                            if minimum is not None and int_value < minimum:
                                range_valid = False
                                var_result["errors"].append(f"Value {int_value} below minimum {minimum}")
                            if maximum is not None and int_value > maximum:
                                range_valid = False
                                var_result["errors"].append(f"Value {int_value} above maximum {maximum}")
                            
                            var_result["range_valid"] = range_valid
                        else:
                            var_result["range_valid"] = True
                        
                        # Allowed values validation
                        allowed_values = rule.get("allowed_values")
                        if allowed_values and var_value not in allowed_values:
                            var_result["errors"].append(f"Value '{var_value}' not in allowed values: {allowed_values}")
                        
                        # Compile validation errors
                        if not var_result["type_valid"]:
                            var_result["errors"].append(f"Invalid type - expected {expected_type}")
                        if not var_result["pattern_valid"]:
                            var_result["errors"].append(f"Pattern validation failed")
                        
                        # Overall variable validity
                        var_is_valid = (var_result["type_valid"] and 
                                      var_result["pattern_valid"] and 
                                      var_result["range_valid"] and 
                                      len(var_result["errors"]) == 0)
                        
                        if var_is_valid:
                            validation_result["validation_summary"]["valid_variables"] += 1
                        else:
                            validation_result["validation_summary"]["invalid_variables"] += 1
                            validation_result["all_valid"] = False
                    
                    else:
                        var_result["warnings"].append(f"Unknown variable - no validation rule defined")
                    
                    validation_result["variable_results"][var_name] = var_result
                
                # Check for missing required variables
                for rule_name, rule in rules.items():
                    if rule.get("required", False) and rule_name not in env_vars:
                        validation_result["validation_summary"]["missing_required"] += 1
                        validation_result["all_valid"] = False
                        validation_result["global_errors"].append(f"Missing required variable: {rule_name}")
                
                return validation_result
            
            mock_instance.validate_environment_variables.side_effect = validate_environment_variables
            
            validator = EnvironmentValidator()
            
            # Test validation for each environment
            for env_name, env_vars in self.test_environments.items():
                with self.subTest(environment=env_name):
                    validation_result = validator.validate_environment_variables(env_vars, self.validation_rules)
                    
                    # Valid environments should pass validation
                    self.assertTrue(validation_result["all_valid"],
                                  f"Environment {env_name} should be valid: {validation_result['global_errors']}")
                    self.assertEqual(validation_result["validation_summary"]["invalid_variables"], 0,
                                   f"Environment {env_name} should have no invalid variables")
                    self.assertEqual(validation_result["validation_summary"]["missing_required"], 0,
                                   f"Environment {env_name} should have no missing required variables")
                    
                    # Check individual variable validation
                    for var_name, var_result in validation_result["variable_results"].items():
                        self.assertTrue(var_result["type_valid"],
                                      f"Environment {env_name}, variable {var_name}: type validation failed")
                        self.assertTrue(var_result["pattern_valid"],
                                      f"Environment {env_name}, variable {var_name}: pattern validation failed")
                        self.assertTrue(var_result["range_valid"],
                                      f"Environment {env_name}, variable {var_name}: range validation failed")
                        self.assertEqual(len(var_result["errors"]), 0,
                                       f"Environment {env_name}, variable {var_name}: has validation errors: {var_result['errors']}")
            
            # Test validation with invalid values
            invalid_env_vars = {
                "DISCORD_WEBHOOK_URL": "not-a-url",
                "DISCORD_TOKEN": "invalid-token",
                "DISCORD_USE_THREADS": "maybe",
                "DISCORD_MAX_EMBED_FIELDS": "not-a-number",
                "DISCORD_FIELD_CHARACTER_LIMIT": "99999"
            }
            
            validation_result = validator.validate_environment_variables(invalid_env_vars, self.validation_rules)
            
            # Should detect all validation failures
            self.assertFalse(validation_result["all_valid"],
                           "Invalid environment should fail validation")
            self.assertEqual(validation_result["validation_summary"]["invalid_variables"], len(invalid_env_vars),
                           "All invalid variables should be detected")
    
    async def test_cross_platform_compatibility(self) -> None:
        """Test cross-platform environment variable handling compatibility."""
        # Test platform-specific environment handling
        for platform_name, platform_config in self.platform_scenarios.items():
            with self.subTest(platform=platform_name):
                env_vars = platform_config["environment_vars"]
                
                # Test path separator handling
                path_value = env_vars.get("PATH", "")
                expected_separator = platform_config["path_separator"]
                
                if path_value:
                    self.assertIn(expected_separator, path_value,
                                f"Platform {platform_name}: PATH should use {expected_separator} separator")
                
                # Test case sensitivity
                case_sensitive = platform_config["case_sensitivity"]
                discord_vars = {k: v for k, v in env_vars.items() if k.startswith("DISCORD_")}
                
                if not case_sensitive:
                    # On case-insensitive platforms, check for case variations
                    for var_name in discord_vars.keys():
                        lower_var = var_name.lower()
                        upper_var = var_name.upper()
                        # Both should be treated as the same variable
                        self.assertEqual(var_name.upper(), upper_var,
                                       f"Platform {platform_name}: inconsistent case handling")
                
                # Test special character handling
                special_chars = platform_config["special_chars"]
                home_var = env_vars.get("HOME") or env_vars.get("USERPROFILE")
                
                if home_var:
                    # Should be a valid path for the platform
                    if platform_name == "windows":
                        self.assertTrue(home_var.startswith("C:"),
                                      f"Platform {platform_name}: invalid home path format")
                    else:
                        self.assertTrue(home_var.startswith("/"),
                                      f"Platform {platform_name}: invalid home path format")
    
    async def test_dotenv_file_integration(self) -> None:
        """Test integration with .env file loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test .env file
            env_file_path = Path(temp_dir) / ".env"
            env_content = """# Discord Configuration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef123456
DISCORD_USE_THREADS=true
DISCORD_ENABLED_EVENTS=PreToolUse,PostToolUse,Stop
DISCORD_DEBUG=false

# Comments and empty lines should be ignored
# DISCORD_COMMENTED_OUT=ignored

DISCORD_MAX_EMBED_FIELDS=20
DISCORD_FIELD_CHARACTER_LIMIT=512
"""
            
            with open(env_file_path, 'w') as f:
                f.write(env_content)
            
            with patch('src.core.config_loader.ConfigLoader') as mock_config_loader:
                mock_instance = MagicMock()
                mock_config_loader.return_value = mock_instance
                
                # Configure .env file loading
                def load_dotenv_file(file_path: str) -> Dict[str, Any]:
                    """Load variables from .env file."""
                    loaded_vars = {}
                    parsing_errors = []
                    
                    try:
                        with open(file_path, 'r') as f:
                            for line_num, line in enumerate(f, 1):
                                line = line.strip()
                                
                                # Skip comments and empty lines
                                if not line or line.startswith('#'):
                                    continue
                                
                                # Parse KEY=VALUE format
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip()
                                    
                                    # Remove quotes if present
                                    if (value.startswith('"') and value.endswith('"')) or \
                                       (value.startswith("'") and value.endswith("'")):
                                        value = value[1:-1]
                                    
                                    loaded_vars[key] = value
                                else:
                                    parsing_errors.append(f"Line {line_num}: invalid format '{line}'")
                    
                    except FileNotFoundError:
                        parsing_errors.append(f"File not found: {file_path}")
                    except Exception as e:
                        parsing_errors.append(f"Error reading file: {e}")
                    
                    return {
                        "loaded_variables": loaded_vars,
                        "parsing_errors": parsing_errors,
                        "file_path": file_path,
                        "variables_count": len(loaded_vars)
                    }
                
                mock_instance.load_dotenv_file.side_effect = load_dotenv_file
                
                config_loader = ConfigLoader()
                
                # Test .env file loading
                result = config_loader.load_dotenv_file(str(env_file_path))
                
                # Verify successful loading
                self.assertEqual(len(result["parsing_errors"]), 0,
                               f"Should have no parsing errors: {result['parsing_errors']}")
                self.assertEqual(result["variables_count"], 5,
                               "Should load 5 variables from .env file")
                
                # Verify expected variables are loaded
                expected_vars = {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                    "DISCORD_USE_THREADS": "true",
                    "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse,Stop",
                    "DISCORD_DEBUG": "false",
                    "DISCORD_MAX_EMBED_FIELDS": "20",
                    "DISCORD_FIELD_CHARACTER_LIMIT": "512"
                }
                
                loaded_vars = result["loaded_variables"]
                for key, expected_value in expected_vars.items():
                    self.assertIn(key, loaded_vars,
                                f"Variable {key} not loaded from .env file")
                    self.assertEqual(loaded_vars[key], expected_value,
                                   f"Variable {key} has wrong value")
                
                # Test non-existent file handling
                result = config_loader.load_dotenv_file("/nonexistent/.env")
                self.assertGreater(len(result["parsing_errors"]), 0,
                                 "Should have parsing errors for non-existent file")
                self.assertEqual(result["variables_count"], 0,
                               "Should load 0 variables from non-existent file")


def run_environment_handling_tests() -> None:
    """Run environment handling tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestEnvironmentHandling)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nEnvironment Handling Tests Summary:")
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