#!/usr/bin/env python3
"""Test Configuration Validation Functionality.

This module provides comprehensive tests for configuration validation
functionality, including completeness verification, type safety validation,
environment variable handling, default value application, and configuration
schema compliance.
"""

import asyncio
import json
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
from src.core.config import ConfigManager
from src.core.config_loader import ConfigLoader
from src.exceptions import ConfigValidationError
from src.utils.validation import ConfigValidator


class TestConfigValidation(unittest.IsolatedAsyncioTestCase):
    """Test cases for configuration validation functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "validation_mode": "strict",
            "require_all_fields": True,
            "allow_unknown_fields": False,
            "type_checking": True,
            "debug": True
        }
        
        # Valid configuration schemas for testing
        self.valid_config_schemas = {
            "minimal_webhook": {
                "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                "DISCORD_USE_THREADS": "false",
                "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse,Stop"
            },
            "complete_bot": {
                "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                "DISCORD_CHANNEL_ID": "123456789012345678",
                "DISCORD_USE_THREADS": "true",
                "DISCORD_THREAD_NAME_TEMPLATE": "Claude Session {session_id}",
                "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse,Stop,Error",
                "DISCORD_DEBUG": "true",
                "DISCORD_MAX_EMBED_FIELDS": "25",
                "DISCORD_FIELD_CHARACTER_LIMIT": "1024"
            },
            "mixed_config": {
                "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                "DISCORD_CHANNEL_ID": "123456789012345678",
                "DISCORD_USE_THREADS": "true",
                "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse"
            }
        }
        
        # Invalid configuration test cases
        self.invalid_config_cases = {
            "missing_required_fields": {
                "config": {
                    "DISCORD_USE_THREADS": "true"
                    # Missing DISCORD_TOKEN or DISCORD_WEBHOOK_URL
                },
                "expected_errors": ["Missing required Discord configuration"]
            },
            "invalid_webhook_url": {
                "config": {
                    "DISCORD_WEBHOOK_URL": "not-a-valid-url",
                    "DISCORD_USE_THREADS": "false"
                },
                "expected_errors": ["Invalid webhook URL format"]
            },
            "invalid_token_format": {
                "config": {
                    "DISCORD_TOKEN": "invalid-token-format",
                    "DISCORD_CHANNEL_ID": "123456789012345678"
                },
                "expected_errors": ["Invalid bot token format"]
            },
            "invalid_channel_id": {
                "config": {
                    "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                    "DISCORD_CHANNEL_ID": "not-a-number"
                },
                "expected_errors": ["Invalid channel ID format"]
            },
            "invalid_boolean_values": {
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                    "DISCORD_USE_THREADS": "maybe",
                    "DISCORD_DEBUG": "yes"
                },
                "expected_errors": ["Invalid boolean value", "Invalid boolean value"]
            },
            "invalid_numeric_values": {
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                    "DISCORD_MAX_EMBED_FIELDS": "not-a-number",
                    "DISCORD_FIELD_CHARACTER_LIMIT": "-1"
                },
                "expected_errors": ["Invalid numeric value", "Value out of range"]
            },
            "conflicting_configurations": {
                "config": {
                    "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                    "DISCORD_CHANNEL_ID": "123456789012345678"
                    # Both token+channel and webhook specified
                },
                "expected_errors": ["Conflicting authentication methods"]
            }
        }
        
        # Configuration schema definition
        self.config_schema = {
            "discord": {
                "authentication": {
                    "webhook_url": {
                        "type": "string",
                        "pattern": r"^https://discord\.com/api/webhooks/\d+/[\w\-]+$",
                        "required": False,
                        "description": "Discord webhook URL for sending messages"
                    },
                    "bot_token": {
                        "type": "string", 
                        "pattern": r"^Bot [A-Za-z0-9]{24}\.[A-Za-z0-9]{6}\.[A-Za-z0-9\-_]{38}$",
                        "required": False,
                        "description": "Discord bot token"
                    },
                    "channel_id": {
                        "type": "string",
                        "pattern": r"^\d{17,20}$",
                        "required": False,
                        "description": "Discord channel ID for bot messages"
                    }
                },
                "features": {
                    "use_threads": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable thread organization for messages"
                    },
                    "thread_name_template": {
                        "type": "string",
                        "default": "Claude Session {session_id}",
                        "description": "Template for thread names"
                    },
                    "enabled_events": {
                        "type": "list",
                        "items": {"type": "string", "enum": ["PreToolUse", "PostToolUse", "Stop", "Error"]},
                        "default": ["PreToolUse", "PostToolUse", "Stop"],
                        "description": "List of events to send to Discord"
                    }
                },
                "limits": {
                    "max_embed_fields": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 25,
                        "description": "Maximum number of fields in Discord embeds"
                    },
                    "field_character_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1024,
                        "default": 1024,
                        "description": "Character limit for Discord embed fields"
                    }
                },
                "debug": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable debug logging"
                }
            }
        }
        
        # Default configuration values
        self.default_config = {
            "DISCORD_USE_THREADS": "false",
            "DISCORD_THREAD_NAME_TEMPLATE": "Claude Session {session_id}",
            "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse,Stop",
            "DISCORD_MAX_EMBED_FIELDS": "25",
            "DISCORD_FIELD_CHARACTER_LIMIT": "1024",
            "DISCORD_DEBUG": "false"
        }
    
    async def test_configuration_completeness_validation(self) -> None:
        """Test validation of configuration completeness."""
        with patch('src.core.config_loader.ConfigLoader') as mock_config_loader:
            mock_instance = MagicMock()
            mock_config_loader.return_value = mock_instance
            
            # Configure completeness validation
            def validate_completeness(config: Dict[str, Any]) -> Dict[str, Any]:
                """Validate that configuration has all required fields."""
                validation_result = {
                    "is_complete": True,
                    "missing_fields": [],
                    "required_fields_present": [],
                    "validation_errors": []
                }
                
                # Check for authentication method
                has_webhook = "DISCORD_WEBHOOK_URL" in config and config["DISCORD_WEBHOOK_URL"]
                has_bot_config = ("DISCORD_TOKEN" in config and config["DISCORD_TOKEN"] and
                                "DISCORD_CHANNEL_ID" in config and config["DISCORD_CHANNEL_ID"])
                
                if not has_webhook and not has_bot_config:
                    validation_result["is_complete"] = False
                    validation_result["missing_fields"].append("authentication_method")
                    validation_result["validation_errors"].append(
                        "Missing required Discord configuration: either DISCORD_WEBHOOK_URL or (DISCORD_TOKEN + DISCORD_CHANNEL_ID)"
                    )
                else:
                    if has_webhook:
                        validation_result["required_fields_present"].append("DISCORD_WEBHOOK_URL")
                    if has_bot_config:
                        validation_result["required_fields_present"].extend(["DISCORD_TOKEN", "DISCORD_CHANNEL_ID"])
                
                # Check for conflicting authentication methods
                if has_webhook and has_bot_config:
                    validation_result["validation_errors"].append(
                        "Conflicting authentication methods: both webhook and bot token specified"
                    )
                
                return validation_result
            
            mock_instance.validate_completeness.side_effect = validate_completeness
            
            config_loader = ConfigLoader()
            
            # Test completeness validation for each valid schema
            for schema_name, config in self.valid_config_schemas.items():
                with self.subTest(schema=schema_name):
                    result = config_loader.validate_completeness(config)
                    
                    # Valid schemas should pass completeness check
                    self.assertTrue(result["is_complete"],
                                  f"Schema {schema_name} failed completeness validation: {result['validation_errors']}")
                    self.assertEqual(len(result["validation_errors"]), 0,
                                   f"Schema {schema_name} has validation errors: {result['validation_errors']}")
                    self.assertGreater(len(result["required_fields_present"]), 0,
                                     f"Schema {schema_name} has no required fields present")
            
            # Test completeness validation for invalid cases
            for case_name, case_data in self.invalid_config_cases.items():
                if "missing_required_fields" in case_name or "conflicting" in case_name:
                    with self.subTest(case=case_name):
                        result = config_loader.validate_completeness(case_data["config"])
                        
                        # Invalid cases should fail completeness check
                        if "missing_required_fields" in case_name:
                            self.assertFalse(result["is_complete"],
                                           f"Case {case_name} should fail completeness validation")
                            self.assertGreater(len(result["missing_fields"]), 0,
                                             f"Case {case_name} should have missing fields")
                        
                        self.assertGreater(len(result["validation_errors"]), 0,
                                         f"Case {case_name} should have validation errors")
    
    async def test_configuration_type_safety_validation(self) -> None:
        """Test type safety validation of configuration values."""
        with patch('src.utils.validation.ConfigValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure type safety validation
            def validate_types(config: Dict[str, Any]) -> Dict[str, Any]:
                """Validate types of configuration values."""
                validation_result = {
                    "types_valid": True,
                    "type_errors": [],
                    "converted_values": {},
                    "validation_warnings": []
                }
                
                type_validators = {
                    "DISCORD_WEBHOOK_URL": lambda v: isinstance(v, str) and v.startswith("https://"),
                    "DISCORD_TOKEN": lambda v: isinstance(v, str) and v.startswith("Bot "),
                    "DISCORD_CHANNEL_ID": lambda v: isinstance(v, str) and v.isdigit(),
                    "DISCORD_USE_THREADS": lambda v: v.lower() in ["true", "false"],
                    "DISCORD_DEBUG": lambda v: v.lower() in ["true", "false"],
                    "DISCORD_MAX_EMBED_FIELDS": lambda v: v.isdigit() and 1 <= int(v) <= 25,
                    "DISCORD_FIELD_CHARACTER_LIMIT": lambda v: v.isdigit() and 1 <= int(v) <= 1024
                }
                
                for key, value in config.items():
                    if key in type_validators:
                        try:
                            if type_validators[key](value):
                                # Convert boolean strings
                                if key in ["DISCORD_USE_THREADS", "DISCORD_DEBUG"]:
                                    validation_result["converted_values"][key] = value.lower() == "true"
                                # Convert numeric strings
                                elif key in ["DISCORD_MAX_EMBED_FIELDS", "DISCORD_FIELD_CHARACTER_LIMIT"]:
                                    validation_result["converted_values"][key] = int(value)
                                else:
                                    validation_result["converted_values"][key] = value
                            else:
                                validation_result["types_valid"] = False
                                validation_result["type_errors"].append(f"Invalid value for {key}: {value}")
                        except (ValueError, AttributeError) as e:
                            validation_result["types_valid"] = False
                            validation_result["type_errors"].append(f"Type validation error for {key}: {e}")
                    else:
                        validation_result["validation_warnings"].append(f"Unknown configuration field: {key}")
                
                return validation_result
            
            mock_instance.validate_types.side_effect = validate_types
            
            validator = ConfigValidator()
            
            # Test type validation for valid configurations
            for schema_name, config in self.valid_config_schemas.items():
                with self.subTest(schema=schema_name):
                    result = validator.validate_types(config)
                    
                    # Valid configurations should pass type validation
                    self.assertTrue(result["types_valid"],
                                  f"Schema {schema_name} failed type validation: {result['type_errors']}")
                    self.assertEqual(len(result["type_errors"]), 0,
                                   f"Schema {schema_name} has type errors: {result['type_errors']}")
                    
                    # Check converted values
                    converted = result["converted_values"]
                    for key, value in converted.items():
                        if key in ["DISCORD_USE_THREADS", "DISCORD_DEBUG"]:
                            self.assertIsInstance(value, bool,
                                                f"Boolean field {key} not converted properly")
                        elif key in ["DISCORD_MAX_EMBED_FIELDS", "DISCORD_FIELD_CHARACTER_LIMIT"]:
                            self.assertIsInstance(value, int,
                                                f"Numeric field {key} not converted properly")
            
            # Test type validation for invalid configurations
            invalid_type_cases = [
                case_data for case_name, case_data in self.invalid_config_cases.items()
                if "invalid" in case_name and "conflicting" not in case_name
            ]
            
            for case_data in invalid_type_cases:
                result = validator.validate_types(case_data["config"])
                
                # Invalid configurations should fail type validation
                self.assertFalse(result["types_valid"],
                               f"Invalid config should fail type validation: {case_data['config']}")
                self.assertGreater(len(result["type_errors"]), 0,
                                 f"Invalid config should have type errors: {case_data['config']}")
    
    async def test_environment_variable_handling_validation(self) -> None:
        """Test validation of environment variable handling."""
        with patch.dict(os.environ, {}, clear=True):
            # Set up test environment variables
            test_env_vars = {
                "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                "DISCORD_USE_THREADS": "true",
                "DISCORD_ENABLED_EVENTS": "PreToolUse,PostToolUse,Stop",
                "DISCORD_DEBUG": "false",
                "INVALID_VAR": "should_be_ignored"
            }
            
            with patch.dict(os.environ, test_env_vars):
                with patch('src.core.config_loader.ConfigLoader') as mock_config_loader:
                    mock_instance = MagicMock()
                    mock_config_loader.return_value = mock_instance
                    
                    # Configure environment variable handling
                    def load_from_environment() -> Dict[str, Any]:
                        """Load configuration from environment variables."""
                        env_config = {}
                        discord_prefix = "DISCORD_"
                        
                        for key, value in os.environ.items():
                            if key.startswith(discord_prefix):
                                env_config[key] = value
                        
                        return env_config
                    
                    def validate_environment_variables(env_config: Dict[str, Any]) -> Dict[str, Any]:
                        """Validate environment variable configuration."""
                        validation_result = {
                            "env_vars_valid": True,
                            "loaded_vars": list(env_config.keys()),
                            "ignored_vars": [],
                            "validation_errors": [],
                            "security_warnings": []
                        }
                        
                        known_vars = {
                            "DISCORD_WEBHOOK_URL", "DISCORD_TOKEN", "DISCORD_CHANNEL_ID",
                            "DISCORD_USE_THREADS", "DISCORD_THREAD_NAME_TEMPLATE",
                            "DISCORD_ENABLED_EVENTS", "DISCORD_MAX_EMBED_FIELDS",
                            "DISCORD_FIELD_CHARACTER_LIMIT", "DISCORD_DEBUG"
                        }
                        
                        for key in env_config.keys():
                            if key not in known_vars:
                                validation_result["ignored_vars"].append(key)
                                validation_result["validation_errors"].append(f"Unknown environment variable: {key}")
                        
                        # Security validation
                        for key, value in env_config.items():
                            if "TOKEN" in key and not value.startswith("Bot "):
                                validation_result["security_warnings"].append(f"Token format warning for {key}")
                            elif "WEBHOOK_URL" in key and not value.startswith("https://discord.com/"):
                                validation_result["security_warnings"].append(f"Webhook URL security warning for {key}")
                        
                        if validation_result["validation_errors"] or validation_result["security_warnings"]:
                            validation_result["env_vars_valid"] = False
                        
                        return validation_result
                    
                    mock_instance.load_from_environment.side_effect = load_from_environment
                    mock_instance.validate_environment_variables.side_effect = validate_environment_variables
                    
                    config_loader = ConfigLoader()
                    
                    # Test environment variable loading
                    env_config = config_loader.load_from_environment()
                    
                    # Verify expected variables are loaded
                    expected_vars = ["DISCORD_WEBHOOK_URL", "DISCORD_USE_THREADS", "DISCORD_ENABLED_EVENTS", "DISCORD_DEBUG"]
                    for var in expected_vars:
                        self.assertIn(var, env_config,
                                    f"Environment variable {var} not loaded")
                        self.assertEqual(env_config[var], test_env_vars[var],
                                       f"Environment variable {var} value mismatch")
                    
                    # Test environment variable validation
                    validation_result = config_loader.validate_environment_variables(env_config)
                    
                    # Check validation results
                    self.assertEqual(len(validation_result["loaded_vars"]), 4,
                                   f"Expected 4 loaded vars, got {len(validation_result['loaded_vars'])}")
                    self.assertEqual(len(validation_result["ignored_vars"]), 0,
                                   f"Should have no ignored vars with valid config")
                    self.assertEqual(len(validation_result["validation_errors"]), 0,
                                   f"Should have no validation errors: {validation_result['validation_errors']}")
                    self.assertEqual(len(validation_result["security_warnings"]), 0,
                                   f"Should have no security warnings: {validation_result['security_warnings']}")
                    self.assertTrue(validation_result["env_vars_valid"],
                                  "Environment variables should be valid")
    
    async def test_default_value_application_validation(self) -> None:
        """Test validation of default value application."""
        with patch('src.core.config.ConfigManager') as mock_config_manager:
            mock_instance = MagicMock()
            mock_config_manager.return_value = mock_instance
            
            # Configure default value application
            def apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
                """Apply default values to configuration."""
                result_config = config.copy()
                
                # Apply defaults for missing fields
                for key, default_value in self.default_config.items():
                    if key not in result_config:
                        result_config[key] = default_value
                
                return result_config
            
            def validate_defaults(config: Dict[str, Any], defaults_applied: Dict[str, Any]) -> Dict[str, Any]:
                """Validate default value application."""
                validation_result = {
                    "defaults_applied_correctly": True,
                    "applied_defaults": [],
                    "override_warnings": [],
                    "validation_errors": []
                }
                
                for key, default_value in self.default_config.items():
                    if key not in config:
                        # Should be applied
                        if key in defaults_applied and defaults_applied[key] == default_value:
                            validation_result["applied_defaults"].append({
                                "field": key,
                                "default_value": default_value
                            })
                        else:
                            validation_result["defaults_applied_correctly"] = False
                            validation_result["validation_errors"].append(f"Default not applied for {key}")
                    else:
                        # User provided value, check for conflicts
                        user_value = config[key]
                        if user_value != default_value:
                            validation_result["override_warnings"].append({
                                "field": key,
                                "user_value": user_value,
                                "default_value": default_value
                            })
                
                return validation_result
            
            mock_instance.apply_defaults.side_effect = apply_defaults
            mock_instance.validate_defaults.side_effect = validate_defaults
            
            config_manager = ConfigManager()
            
            # Test default application scenarios
            test_scenarios = [
                {
                    "name": "minimal_config",
                    "input_config": {
                        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456"
                    },
                    "expected_defaults": [
                        "DISCORD_USE_THREADS", "DISCORD_THREAD_NAME_TEMPLATE",
                        "DISCORD_ENABLED_EVENTS", "DISCORD_MAX_EMBED_FIELDS",
                        "DISCORD_FIELD_CHARACTER_LIMIT", "DISCORD_DEBUG"
                    ]
                },
                {
                    "name": "partial_config",
                    "input_config": {
                        "DISCORD_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
                        "DISCORD_CHANNEL_ID": "123456789012345678",
                        "DISCORD_USE_THREADS": "true",
                        "DISCORD_DEBUG": "true"
                    },
                    "expected_defaults": [
                        "DISCORD_THREAD_NAME_TEMPLATE", "DISCORD_ENABLED_EVENTS",
                        "DISCORD_MAX_EMBED_FIELDS", "DISCORD_FIELD_CHARACTER_LIMIT"
                    ]
                },
                {
                    "name": "complete_config", 
                    "input_config": self.valid_config_schemas["complete_bot"],
                    "expected_defaults": []
                }
            ]
            
            for scenario in test_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    input_config = scenario["input_config"]
                    expected_defaults = scenario["expected_defaults"]
                    
                    # Apply defaults
                    config_with_defaults = config_manager.apply_defaults(input_config)
                    
                    # Validate default application
                    validation_result = config_manager.validate_defaults(input_config, config_with_defaults)
                    
                    # Check that defaults were applied correctly
                    self.assertTrue(validation_result["defaults_applied_correctly"],
                                  f"Defaults not applied correctly for {scenario['name']}: {validation_result['validation_errors']}")
                    
                    # Check that expected defaults were applied
                    applied_fields = [item["field"] for item in validation_result["applied_defaults"]]
                    for expected_field in expected_defaults:
                        self.assertIn(expected_field, applied_fields,
                                    f"Expected default {expected_field} not applied in {scenario['name']}")
                    
                    # Verify final configuration has all required fields
                    for key in self.default_config.keys():
                        self.assertIn(key, config_with_defaults,
                                    f"Field {key} missing from final config in {scenario['name']}")
    
    async def test_configuration_schema_compliance_validation(self) -> None:
        """Test validation of configuration schema compliance."""
        with patch('src.utils.validation.ConfigValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure schema compliance validation
            def validate_schema_compliance(config: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
                """Validate configuration against schema."""
                validation_result = {
                    "schema_compliant": True,
                    "schema_violations": [],
                    "field_validations": {},
                    "validation_summary": {
                        "total_fields": 0,
                        "valid_fields": 0,
                        "invalid_fields": 0,
                        "missing_required": 0
                    }
                }
                
                # Flatten schema for easier validation
                flattened_schema = self._flatten_schema(schema)
                validation_result["validation_summary"]["total_fields"] = len(config)
                
                for field_path, field_config in flattened_schema.items():
                    # Convert schema path to environment variable name
                    env_var_name = self._schema_path_to_env_var(field_path)
                    
                    field_validation = {
                        "field": env_var_name,
                        "present": env_var_name in config,
                        "type_valid": False,
                        "pattern_valid": False,
                        "range_valid": False,
                        "errors": []
                    }
                    
                    if env_var_name in config:
                        value = config[env_var_name]
                        
                        # Type validation
                        expected_type = field_config.get("type")
                        if expected_type == "string":
                            field_validation["type_valid"] = isinstance(value, str)
                        elif expected_type == "boolean":
                            field_validation["type_valid"] = value.lower() in ["true", "false"]
                        elif expected_type == "integer":
                            field_validation["type_valid"] = value.isdigit()
                        elif expected_type == "list":
                            field_validation["type_valid"] = isinstance(value, str) and "," in value
                        
                        # Pattern validation
                        pattern = field_config.get("pattern")
                        if pattern and field_validation["type_valid"]:
                            import re
                            field_validation["pattern_valid"] = bool(re.match(pattern, value))
                        else:
                            field_validation["pattern_valid"] = True
                        
                        # Range validation for numeric types
                        if expected_type == "integer" and field_validation["type_valid"]:
                            int_value = int(value)
                            minimum = field_config.get("minimum")
                            maximum = field_config.get("maximum")
                            
                            range_valid = True
                            if minimum is not None and int_value < minimum:
                                range_valid = False
                                field_validation["errors"].append(f"Value {int_value} below minimum {minimum}")
                            if maximum is not None and int_value > maximum:
                                range_valid = False
                                field_validation["errors"].append(f"Value {int_value} above maximum {maximum}")
                            
                            field_validation["range_valid"] = range_valid
                        else:
                            field_validation["range_valid"] = True
                        
                        # Overall field validity
                        if all([field_validation["type_valid"], field_validation["pattern_valid"], field_validation["range_valid"]]):
                            validation_result["validation_summary"]["valid_fields"] += 1
                        else:
                            validation_result["validation_summary"]["invalid_fields"] += 1
                            validation_result["schema_compliant"] = False
                            
                            errors = []
                            if not field_validation["type_valid"]:
                                errors.append(f"Invalid type for {env_var_name}")
                            if not field_validation["pattern_valid"]:
                                errors.append(f"Pattern mismatch for {env_var_name}")
                            errors.extend(field_validation["errors"])
                            
                            validation_result["schema_violations"].extend(errors)
                    
                    elif field_config.get("required", False):
                        validation_result["validation_summary"]["missing_required"] += 1
                        validation_result["schema_compliant"] = False
                        validation_result["schema_violations"].append(f"Missing required field: {env_var_name}")
                    
                    validation_result["field_validations"][env_var_name] = field_validation
                
                return validation_result
            
            mock_instance.validate_schema_compliance.side_effect = validate_schema_compliance
            
            validator = ConfigValidator()
            
            # Test schema compliance for valid configurations
            for schema_name, config in self.valid_config_schemas.items():
                with self.subTest(schema=schema_name):
                    result = validator.validate_schema_compliance(config, self.config_schema)
                    
                    # Valid configurations should be schema compliant
                    self.assertTrue(result["schema_compliant"],
                                  f"Schema {schema_name} not compliant: {result['schema_violations']}")
                    self.assertEqual(len(result["schema_violations"]), 0,
                                   f"Schema {schema_name} has violations: {result['schema_violations']}")
                    self.assertEqual(result["validation_summary"]["missing_required"], 0,
                                   f"Schema {schema_name} has missing required fields")
                    self.assertGreater(result["validation_summary"]["valid_fields"], 0,
                                     f"Schema {schema_name} has no valid fields")
            
            # Test schema compliance for invalid configurations
            for case_name, case_data in self.invalid_config_cases.items():
                with self.subTest(case=case_name):
                    result = validator.validate_schema_compliance(case_data["config"], self.config_schema)
                    
                    # Invalid configurations should not be schema compliant
                    self.assertFalse(result["schema_compliant"],
                                   f"Invalid case {case_name} should not be schema compliant")
                    self.assertGreater(len(result["schema_violations"]), 0,
                                     f"Invalid case {case_name} should have schema violations")
    
    async def test_configuration_security_validation(self) -> None:
        """Test security aspects of configuration validation."""
        security_test_cases = [
            {
                "name": "exposed_token_in_webhook",
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/TEST_WEBHOOK_TOKEN_SECURITY",
                    "DISCORD_TOKEN": "Bot TEST_TOKEN_SECURITY"
                },
                "expected_warnings": ["Token exposure risk", "Redundant authentication"]
            },
            {
                "name": "weak_token_format",
                "config": {
                    "DISCORD_TOKEN": "weak_token_123",
                    "DISCORD_CHANNEL_ID": "123456789012345678"
                },
                "expected_warnings": ["Weak token format"]
            },
            {
                "name": "insecure_webhook_url",
                "config": {
                    "DISCORD_WEBHOOK_URL": "http://discord.com/api/webhooks/123456789/abcdef123456"
                },
                "expected_warnings": ["Insecure webhook URL (HTTP instead of HTTPS)"]
            },
            {
                "name": "debug_enabled_in_production",
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdef123456",
                    "DISCORD_DEBUG": "true"
                },
                "expected_warnings": ["Debug mode enabled - security risk in production"]
            }
        ]
        
        with patch('src.utils.validation.ConfigValidator') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            
            # Configure security validation
            def validate_security(config: Dict[str, Any]) -> Dict[str, Any]:
                """Validate security aspects of configuration."""
                security_result = {
                    "security_compliant": True,
                    "security_warnings": [],
                    "security_errors": [],
                    "risk_level": "low"
                }
                
                # Check for token exposure
                webhook_url = config.get("DISCORD_WEBHOOK_URL", "")
                bot_token = config.get("DISCORD_TOKEN", "")
                
                if webhook_url and bot_token:
                    security_result["security_warnings"].append("Redundant authentication methods configured")
                
                if bot_token and not bot_token.startswith("Bot "):
                    security_result["security_warnings"].append("Weak token format")
                    security_result["risk_level"] = "medium"
                
                if webhook_url and webhook_url.startswith("http://"):
                    security_result["security_warnings"].append("Insecure webhook URL (HTTP instead of HTTPS)")
                    security_result["risk_level"] = "high"
                
                if config.get("DISCORD_DEBUG", "").lower() == "true":
                    security_result["security_warnings"].append("Debug mode enabled - security risk in production")
                
                if security_result["security_warnings"]:
                    security_result["security_compliant"] = False
                
                return security_result
            
            mock_instance.validate_security.side_effect = validate_security
            
            validator = ConfigValidator()
            
            # Test security validation for each case
            for case in security_test_cases:
                with self.subTest(case=case["name"]):
                    result = validator.validate_security(case["config"])
                    
                    # Should have security warnings
                    self.assertFalse(result["security_compliant"],
                                   f"Case {case['name']} should have security issues")
                    self.assertGreater(len(result["security_warnings"]), 0,
                                     f"Case {case['name']} should have security warnings")
                    
                    # Check that expected warnings are present
                    warning_messages = " ".join(result["security_warnings"])
                    for expected_warning in case["expected_warnings"]:
                        self.assertIn(expected_warning.lower(), warning_messages.lower(),
                                    f"Expected warning '{expected_warning}' not found in {case['name']}")
    
    # Helper methods
    
    def _flatten_schema(self, schema: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested schema structure."""
        flattened = {}
        
        for key, value in schema.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict) and "type" not in value:
                # Nested structure
                flattened.update(self._flatten_schema(value, full_key))
            else:
                # Leaf node with field definition
                flattened[full_key] = value
        
        return flattened
    
    def _schema_path_to_env_var(self, schema_path: str) -> str:
        """Convert schema path to environment variable name."""
        # Remove 'discord.' prefix and convert to uppercase with underscores
        path_parts = schema_path.split(".")[1:]  # Remove 'discord'
        
        # Handle special cases
        path_mapping = {
            "authentication.webhook_url": "DISCORD_WEBHOOK_URL",
            "authentication.bot_token": "DISCORD_TOKEN",
            "authentication.channel_id": "DISCORD_CHANNEL_ID",
            "features.use_threads": "DISCORD_USE_THREADS",
            "features.thread_name_template": "DISCORD_THREAD_NAME_TEMPLATE",
            "features.enabled_events": "DISCORD_ENABLED_EVENTS",
            "limits.max_embed_fields": "DISCORD_MAX_EMBED_FIELDS",
            "limits.field_character_limit": "DISCORD_FIELD_CHARACTER_LIMIT",
            "debug": "DISCORD_DEBUG"
        }
        
        path_key = ".".join(path_parts)
        return path_mapping.get(path_key, f"DISCORD_{path_key.upper().replace('.', '_')}")


def run_config_validation_tests() -> None:
    """Run configuration validation tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigValidation)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nConfiguration Validation Tests Summary:")
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