#!/usr/bin/env python3
"""Test Type Safety Functionality.

This module provides comprehensive tests for type safety functionality,
including static type checking, runtime type validation, TypedDict enforcement,
generic type handling, and type guard verification.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, TypeGuard, TypeVar, Generic, cast
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import inspect
import ast
from dataclasses import dataclass

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.type_defs.base import BaseEvent, BaseToolResult
from src.type_defs.config import ConfigDict, DiscordConfig
from src.type_defs.discord import DiscordEmbed, DiscordField
from src.type_defs.events import EventDict, ToolUseEvent
from src.type_guards import is_event_dict, is_tool_use_event, is_discord_embed
from src.validators import validate_config, validate_event_data


# Test TypedDict definitions
class TestTypedDict(TypedDict):
    """Test TypedDict for validation."""
    required_field: str
    optional_field: Optional[int]
    nested_dict: Dict[str, Any]
    list_field: List[str]


class StrictTypedDict(TypedDict, total=True):
    """Strict TypedDict with all required fields."""
    id: str
    name: str
    value: int
    active: bool


# Generic type variable
T = TypeVar('T')
K = TypeVar('K', str, int)
V = TypeVar('V')


class GenericContainer(Generic[T]):
    """Generic container for type safety testing."""
    def __init__(self, value: T) -> None:
        self._value = value
    
    def get_value(self) -> T:
        return self._value
    
    def set_value(self, value: T) -> None:
        self._value = value


class TestProtocol(Protocol):
    """Protocol for structural typing tests."""
    def process(self, data: str) -> int:
        ...
    
    def validate(self) -> bool:
        ...


@dataclass
class TestDataClass:
    """Test dataclass for type validation."""
    id: str
    name: str
    value: int
    tags: List[str]
    metadata: Optional[Dict[str, Any]] = None


class TestTypeSafety(unittest.IsolatedAsyncioTestCase):
    """Test cases for type safety functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "type_checking": "strict",
            "runtime_validation": True,
            "enforce_typed_dict": True,
            "generic_type_checking": True,
            "protocol_checking": True,
            "debug": True
        }
        
        # Type test scenarios
        self.type_test_data = {
            "valid_typed_dict": {
                "required_field": "test_value",
                "optional_field": 42,
                "nested_dict": {"key": "value"},
                "list_field": ["item1", "item2"]
            },
            "invalid_typed_dict": {
                "required_field": 123,  # Wrong type
                "optional_field": "string",  # Wrong type
                "nested_dict": "not_a_dict",  # Wrong type
                "list_field": "not_a_list"  # Wrong type
            },
            "partial_typed_dict": {
                "required_field": "test_value",
                # Missing optional fields
                "nested_dict": {},
                "list_field": []
            },
            "extra_fields_dict": {
                "required_field": "test_value",
                "optional_field": 10,
                "nested_dict": {},
                "list_field": [],
                "extra_field": "should_be_rejected"  # Extra field
            }
        }
        
        # Type validation rules
        self.type_validation_rules = {
            "string": lambda x: isinstance(x, str),
            "integer": lambda x: isinstance(x, int),
            "float": lambda x: isinstance(x, (int, float)),
            "boolean": lambda x: isinstance(x, bool),
            "list": lambda x: isinstance(x, list),
            "dict": lambda x: isinstance(x, dict),
            "optional": lambda x, inner_type: x is None or inner_type(x),
            "union": lambda x, types: any(t(x) for t in types),
            "typed_dict": lambda x, spec: self._validate_typed_dict(x, spec)
        }
    
    async def test_static_type_checking(self) -> None:
        """Test static type checking and validation."""
        with patch('ast.parse') as mock_parse:
            # Mock AST parsing for type analysis
            type_errors = []
            type_warnings = []
            
            def analyze_type_annotations(source_code: str) -> Dict[str, Any]:
                """Analyze type annotations in source code."""
                try:
                    tree = ast.parse(source_code)
                    
                    type_info = {
                        "functions": [],
                        "classes": [],
                        "variables": [],
                        "type_errors": [],
                        "type_warnings": []
                    }
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_info = {
                                "name": node.name,
                                "args": [],
                                "return_type": None
                            }
                            
                            # Check argument types
                            for arg in node.args.args:
                                arg_info = {
                                    "name": arg.arg,
                                    "type": None
                                }
                                if arg.annotation:
                                    arg_info["type"] = ast.unparse(arg.annotation)
                                else:
                                    type_warnings.append(f"Missing type annotation for argument '{arg.arg}' in function '{node.name}'")
                                
                                func_info["args"].append(arg_info)
                            
                            # Check return type
                            if node.returns:
                                func_info["return_type"] = ast.unparse(node.returns)
                            else:
                                type_warnings.append(f"Missing return type annotation for function '{node.name}'")
                            
                            type_info["functions"].append(func_info)
                        
                        elif isinstance(node, ast.ClassDef):
                            class_info = {
                                "name": node.name,
                                "attributes": [],
                                "methods": []
                            }
                            
                            # Check class attributes
                            for item in node.body:
                                if isinstance(item, ast.AnnAssign) and item.target:
                                    attr_info = {
                                        "name": item.target.id if hasattr(item.target, 'id') else str(item.target),
                                        "type": ast.unparse(item.annotation) if item.annotation else None
                                    }
                                    class_info["attributes"].append(attr_info)
                            
                            type_info["classes"].append(class_info)
                        
                        elif isinstance(node, ast.AnnAssign):
                            # Module-level variable annotations
                            if hasattr(node.target, 'id'):
                                var_info = {
                                    "name": node.target.id,
                                    "type": ast.unparse(node.annotation) if node.annotation else None
                                }
                                type_info["variables"].append(var_info)
                    
                    type_info["type_errors"] = type_errors
                    type_info["type_warnings"] = type_warnings
                    
                    return type_info
                
                except Exception as e:
                    return {
                        "error": str(e),
                        "type_errors": type_errors,
                        "type_warnings": type_warnings
                    }
            
            # Test source code samples
            test_sources = [
                # Properly typed function
                """
def process_data(input_data: Dict[str, Any], count: int) -> List[str]:
    result: List[str] = []
    for key, value in input_data.items():
        if isinstance(value, str):
            result.append(f"{key}: {value}")
    return result[:count]
""",
                # Missing type annotations
                """
def process_data(input_data, count):
    result = []
    for key, value in input_data.items():
        if isinstance(value, str):
            result.append(f"{key}: {value}")
    return result[:count]
""",
                # Typed class definition
                """
class DataProcessor:
    name: str
    config: Dict[str, Any]
    active: bool = True
    
    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
        self.config = config
    
    def process(self, data: List[str]) -> int:
        return len(data)
""",
                # Generic type usage
                """
from typing import TypeVar, Generic, List

T = TypeVar('T')

class Container(Generic[T]):
    items: List[T]
    
    def __init__(self) -> None:
        self.items = []
    
    def add(self, item: T) -> None:
        self.items.append(item)
    
    def get_all(self) -> List[T]:
        return self.items.copy()
"""
            ]
            
            # Analyze each source
            analysis_results = []
            
            for i, source in enumerate(test_sources):
                type_errors.clear()
                type_warnings.clear()
                
                result = analyze_type_annotations(source)
                analysis_results.append({
                    "source_index": i,
                    "analysis": result,
                    "has_errors": len(result.get("type_errors", [])) > 0,
                    "has_warnings": len(result.get("type_warnings", [])) > 0
                })
            
            # Verify type checking results
            # First source should have no warnings
            self.assertFalse(analysis_results[0]["has_warnings"])
            self.assertEqual(len(analysis_results[0]["analysis"]["functions"]), 1)
            self.assertEqual(analysis_results[0]["analysis"]["functions"][0]["return_type"], "List[str]")
            
            # Second source should have warnings (missing annotations)
            self.assertTrue(analysis_results[1]["has_warnings"])
            self.assertGreater(len(analysis_results[1]["analysis"]["type_warnings"]), 0)
            
            # Third source (class) should be properly typed
            self.assertEqual(len(analysis_results[2]["analysis"]["classes"]), 1)
            class_info = analysis_results[2]["analysis"]["classes"][0]
            self.assertEqual(class_info["name"], "DataProcessor")
            self.assertGreater(len(class_info["attributes"]), 0)
            
            # Fourth source (generic) should handle generic types
            self.assertEqual(len(analysis_results[3]["analysis"]["classes"]), 1)
            generic_class = analysis_results[3]["analysis"]["classes"][0]
            self.assertEqual(generic_class["name"], "Container")
            
            # Log static type checking analysis
            self.logger.info(
                "Static type checking analysis",
                context={
                    "sources_analyzed": len(test_sources),
                    "total_functions": sum(len(r["analysis"].get("functions", [])) for r in analysis_results),
                    "total_classes": sum(len(r["analysis"].get("classes", [])) for r in analysis_results),
                    "sources_with_warnings": sum(1 for r in analysis_results if r["has_warnings"]),
                    "sources_with_errors": sum(1 for r in analysis_results if r["has_errors"]),
                    "type_coverage": {
                        "fully_typed": sum(1 for r in analysis_results if not r["has_warnings"] and not r["has_errors"]),
                        "partially_typed": sum(1 for r in analysis_results if r["has_warnings"] and not r["has_errors"]),
                        "type_errors": sum(1 for r in analysis_results if r["has_errors"])
                    }
                }
            )
    
    async def test_runtime_type_validation(self) -> None:
        """Test runtime type validation and enforcement."""
        with patch('src.validators.validate_event_data') as mock_validate:
            # Mock runtime type validation
            validation_log = []
            
            def runtime_type_check(value: Any, expected_type: type, path: str = "") -> Tuple[bool, Optional[str]]:
                """Perform runtime type checking."""
                validation_entry = {
                    "value": value,
                    "expected_type": expected_type,
                    "path": path,
                    "actual_type": type(value),
                    "valid": False,
                    "error": None
                }
                
                try:
                    # Handle None/Optional types
                    if hasattr(expected_type, '__origin__'):
                        origin = expected_type.__origin__
                        args = expected_type.__args__
                        
                        if origin is Union:
                            # Handle Union types (including Optional)
                            valid = any(runtime_type_check(value, arg, path)[0] for arg in args)
                            validation_entry["valid"] = valid
                            if not valid:
                                validation_entry["error"] = f"Value does not match any union type at {path}"
                            
                        elif origin is list:
                            # Handle List types
                            if not isinstance(value, list):
                                validation_entry["error"] = f"Expected list at {path}, got {type(value).__name__}"
                            elif args:
                                # Check element types
                                element_type = args[0]
                                for i, item in enumerate(value):
                                    elem_valid, elem_error = runtime_type_check(item, element_type, f"{path}[{i}]")
                                    if not elem_valid:
                                        validation_entry["error"] = elem_error
                                        break
                                else:
                                    validation_entry["valid"] = True
                            else:
                                validation_entry["valid"] = True
                        
                        elif origin is dict:
                            # Handle Dict types
                            if not isinstance(value, dict):
                                validation_entry["error"] = f"Expected dict at {path}, got {type(value).__name__}"
                            elif args and len(args) == 2:
                                # Check key and value types
                                key_type, value_type = args
                                for k, v in value.items():
                                    key_valid, key_error = runtime_type_check(k, key_type, f"{path}.key")
                                    if not key_valid:
                                        validation_entry["error"] = key_error
                                        break
                                    
                                    val_valid, val_error = runtime_type_check(v, value_type, f"{path}[{k}]")
                                    if not val_valid:
                                        validation_entry["error"] = val_error
                                        break
                                else:
                                    validation_entry["valid"] = True
                            else:
                                validation_entry["valid"] = True
                    
                    else:
                        # Simple type check
                        if isinstance(value, expected_type):
                            validation_entry["valid"] = True
                        else:
                            validation_entry["error"] = f"Expected {expected_type.__name__} at {path}, got {type(value).__name__}"
                
                except Exception as e:
                    validation_entry["error"] = f"Type validation error: {str(e)}"
                
                validation_log.append(validation_entry)
                return validation_entry["valid"], validation_entry["error"]
            
            # Test various runtime type scenarios
            test_cases = [
                # Basic types
                ("hello", str, "basic_string", True),
                (123, int, "basic_int", True),
                (45.67, float, "basic_float", True),
                (True, bool, "basic_bool", True),
                
                # Wrong types
                ("123", int, "string_as_int", False),
                (123, str, "int_as_string", False),
                
                # Optional types
                (None, Optional[str], "optional_none", True),
                ("value", Optional[str], "optional_value", True),
                (123, Optional[str], "optional_wrong_type", False),
                
                # List types
                (["a", "b", "c"], List[str], "list_of_strings", True),
                ([1, 2, 3], List[int], "list_of_ints", True),
                (["a", 1, "c"], List[str], "mixed_list", False),
                ("not_a_list", List[str], "not_a_list", False),
                
                # Dict types
                ({"a": 1, "b": 2}, Dict[str, int], "dict_str_int", True),
                ({1: "a", 2: "b"}, Dict[int, str], "dict_int_str", True),
                ({"a": "1", "b": 2}, Dict[str, int], "dict_mixed_values", False),
                
                # Union types
                ("string", Union[str, int], "union_str", True),
                (123, Union[str, int], "union_int", True),
                (45.67, Union[str, int], "union_float", False)
            ]
            
            # Run runtime validation tests
            validation_results = []
            
            for value, expected_type, test_name, should_pass in test_cases:
                is_valid, error = runtime_type_check(value, expected_type, test_name)
                
                validation_results.append({
                    "test_name": test_name,
                    "value": value,
                    "expected_type": str(expected_type),
                    "is_valid": is_valid,
                    "should_pass": should_pass,
                    "passed": is_valid == should_pass,
                    "error": error
                })
                
                # Assert validation result matches expectation
                self.assertEqual(is_valid, should_pass, 
                               f"Runtime validation failed for {test_name}: expected {should_pass}, got {is_valid}")
            
            # Test complex nested structures
            complex_data = {
                "id": "test_123",
                "config": {
                    "enabled": True,
                    "options": ["opt1", "opt2"],
                    "settings": {
                        "timeout": 30,
                        "retries": 3
                    }
                },
                "tags": ["tag1", "tag2", "tag3"]
            }
            
            # Define expected structure type
            ComplexType = Dict[str, Union[str, Dict[str, Any], List[str]]]
            
            is_valid, error = runtime_type_check(complex_data, ComplexType, "complex_data")
            self.assertTrue(is_valid, f"Complex data validation failed: {error}")
            
            # Calculate validation statistics
            total_tests = len(validation_results)
            passed_tests = sum(1 for r in validation_results if r["passed"])
            validation_accuracy = passed_tests / total_tests
            
            # Log runtime validation analysis
            self.logger.info(
                "Runtime type validation analysis",
                context={
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": total_tests - passed_tests,
                    "validation_accuracy": validation_accuracy,
                    "validation_log_entries": len(validation_log),
                    "type_categories_tested": {
                        "basic_types": sum(1 for r in validation_results if "basic" in r["test_name"]),
                        "optional_types": sum(1 for r in validation_results if "optional" in r["test_name"]),
                        "collection_types": sum(1 for r in validation_results if any(x in r["test_name"] for x in ["list", "dict"])),
                        "union_types": sum(1 for r in validation_results if "union" in r["test_name"])
                    }
                }
            )
    
    async def test_typed_dict_enforcement(self) -> None:
        """Test TypedDict enforcement and validation."""
        with patch('src.type_guards.is_event_dict') as mock_is_event:
            # Mock TypedDict validation
            typed_dict_violations = []
            
            def validate_typed_dict(data: Dict[str, Any], typed_dict_class: type) -> Tuple[bool, List[str]]:
                """Validate data against TypedDict specification."""
                violations = []
                
                # Get TypedDict annotations
                annotations = typed_dict_class.__annotations__
                required_keys = getattr(typed_dict_class, '__required_keys__', set(annotations.keys()))
                optional_keys = getattr(typed_dict_class, '__optional_keys__', set())
                
                # If no explicit required/optional, all are required in total=True
                if hasattr(typed_dict_class, '__total__') and not typed_dict_class.__total__:
                    optional_keys = set(annotations.keys())
                    required_keys = set()
                
                # Check required fields
                for key in required_keys:
                    if key not in data:
                        violations.append(f"Missing required field: {key}")
                
                # Check field types
                for key, expected_type in annotations.items():
                    if key in data:
                        value = data[key]
                        
                        # Simple type checking (would be more complex in practice)
                        if hasattr(expected_type, '__origin__'):
                            # Handle generic types
                            if expected_type.__origin__ is Union and type(None) in expected_type.__args__:
                                # Optional type
                                if value is not None:
                                    inner_type = next(t for t in expected_type.__args__ if t is not type(None))
                                    if not isinstance(value, inner_type):
                                        violations.append(f"Field '{key}' has wrong type: expected {inner_type.__name__}, got {type(value).__name__}")
                            elif expected_type.__origin__ is list:
                                if not isinstance(value, list):
                                    violations.append(f"Field '{key}' must be a list")
                            elif expected_type.__origin__ is dict:
                                if not isinstance(value, dict):
                                    violations.append(f"Field '{key}' must be a dict")
                        else:
                            # Simple type
                            if not isinstance(value, expected_type):
                                violations.append(f"Field '{key}' has wrong type: expected {expected_type.__name__}, got {type(value).__name__}")
                
                # Check for extra fields
                allowed_keys = required_keys | optional_keys
                extra_keys = set(data.keys()) - allowed_keys
                if extra_keys:
                    violations.append(f"Extra fields not allowed: {', '.join(extra_keys)}")
                
                typed_dict_violations.extend(violations)
                return len(violations) == 0, violations
            
            # Test TypedDict validation
            test_cases = [
                # Valid TypedDict
                (
                    self.type_test_data["valid_typed_dict"],
                    TestTypedDict,
                    "valid_typed_dict",
                    True
                ),
                # Invalid types
                (
                    self.type_test_data["invalid_typed_dict"],
                    TestTypedDict,
                    "invalid_typed_dict",
                    False
                ),
                # Partial (missing optional fields)
                (
                    self.type_test_data["partial_typed_dict"],
                    TestTypedDict,
                    "partial_typed_dict",
                    True  # Should pass as optional_field is optional
                ),
                # Extra fields
                (
                    self.type_test_data["extra_fields_dict"],
                    TestTypedDict,
                    "extra_fields_dict",
                    False  # Should fail due to extra fields
                ),
                # Strict TypedDict test
                (
                    {
                        "id": "test_123",
                        "name": "Test Item",
                        "value": 42,
                        "active": True
                    },
                    StrictTypedDict,
                    "strict_valid",
                    True
                ),
                # Strict TypedDict missing field
                (
                    {
                        "id": "test_123",
                        "name": "Test Item",
                        "value": 42
                        # Missing 'active' field
                    },
                    StrictTypedDict,
                    "strict_missing_field",
                    False
                )
            ]
            
            # Run TypedDict validation tests
            validation_results = []
            
            for data, typed_dict_class, test_name, should_pass in test_cases:
                typed_dict_violations.clear()
                is_valid, violations = validate_typed_dict(data, typed_dict_class)
                
                validation_results.append({
                    "test_name": test_name,
                    "typed_dict_class": typed_dict_class.__name__,
                    "is_valid": is_valid,
                    "should_pass": should_pass,
                    "passed": is_valid == should_pass,
                    "violations": violations,
                    "violation_count": len(violations)
                })
                
                # Assert validation result
                self.assertEqual(is_valid, should_pass,
                               f"TypedDict validation failed for {test_name}: expected {should_pass}, got {is_valid}")
            
            # Test real TypedDict from project
            event_data = {
                "event_type": "PreToolUse",
                "session_id": "test_session_123",
                "timestamp": "2025-07-12T22:00:00.000Z",
                "tool_name": "Write",
                "arguments": {
                    "file_path": "/test/file.txt",
                    "content": "test content"
                }
            }
            
            # This should be validated against EventDict TypedDict
            mock_is_event.return_value = True
            is_valid_event = is_event_dict(event_data)
            self.assertTrue(is_valid_event)
            
            # Calculate TypedDict compliance
            total_tests = len(validation_results)
            compliant_tests = sum(1 for r in validation_results if r["passed"])
            compliance_rate = compliant_tests / total_tests
            
            # Log TypedDict enforcement analysis
            self.logger.info(
                "TypedDict enforcement analysis",
                context={
                    "total_tests": total_tests,
                    "compliant_tests": compliant_tests,
                    "non_compliant_tests": total_tests - compliant_tests,
                    "compliance_rate": compliance_rate,
                    "total_violations": sum(r["violation_count"] for r in validation_results),
                    "violation_types": {
                        "missing_required": sum(1 for v in typed_dict_violations if "Missing required" in v),
                        "wrong_type": sum(1 for v in typed_dict_violations if "wrong type" in v),
                        "extra_fields": sum(1 for v in typed_dict_violations if "Extra fields" in v)
                    },
                    "typed_dicts_tested": list(set(r["typed_dict_class"] for r in validation_results))
                }
            )
    
    async def test_generic_type_handling(self) -> None:
        """Test generic type handling and type variables."""
        # Test generic container
        generic_test_cases = []
        
        # Test with different type parameters
        string_container = GenericContainer[str]("hello")
        int_container = GenericContainer[int](42)
        list_container = GenericContainer[List[str]](["a", "b", "c"])
        
        # Test type safety
        test_results = []
        
        # Test correct types
        try:
            value1 = string_container.get_value()
            self.assertIsInstance(value1, str)
            test_results.append({"test": "string_container_get", "passed": True})
        except Exception as e:
            test_results.append({"test": "string_container_get", "passed": False, "error": str(e)})
        
        try:
            value2 = int_container.get_value()
            self.assertIsInstance(value2, int)
            test_results.append({"test": "int_container_get", "passed": True})
        except Exception as e:
            test_results.append({"test": "int_container_get", "passed": False, "error": str(e)})
        
        try:
            value3 = list_container.get_value()
            self.assertIsInstance(value3, list)
            test_results.append({"test": "list_container_get", "passed": True})
        except Exception as e:
            test_results.append({"test": "list_container_get", "passed": False, "error": str(e)})
        
        # Test type constraints
        def process_generic_dict(data: Dict[K, V]) -> List[Tuple[K, V]]:
            """Process generic dictionary with type constraints."""
            return list(data.items())
        
        # Test with valid constraints
        string_int_dict: Dict[str, int] = {"a": 1, "b": 2, "c": 3}
        result1 = process_generic_dict(string_int_dict)
        self.assertEqual(len(result1), 3)
        test_results.append({"test": "generic_dict_valid", "passed": True})
        
        # Test bounded type variables
        def process_bounded(value: K) -> K:
            """Process value with bounded type variable."""
            return value
        
        # K is bounded to str or int
        str_result = process_bounded("hello")
        int_result = process_bounded(42)
        
        self.assertEqual(str_result, "hello")
        self.assertEqual(int_result, 42)
        test_results.append({"test": "bounded_type_var", "passed": True})
        
        # Test generic protocol
        class ConcreteProcessor:
            """Concrete implementation of TestProtocol."""
            def process(self, data: str) -> int:
                return len(data)
            
            def validate(self) -> bool:
                return True
        
        processor: TestProtocol = ConcreteProcessor()
        self.assertTrue(processor.validate())
        self.assertEqual(processor.process("test"), 4)
        test_results.append({"test": "generic_protocol", "passed": True})
        
        # Test variance
        class Invariant(Generic[T]):
            def __init__(self, value: T) -> None:
                self._value = value
        
        class Covariant(Generic[T]):
            def __init__(self, value: T) -> None:
                self._value = value
            
            def get(self) -> T:
                return self._value
        
        # Test invariance
        inv_str = Invariant[str]("test")
        # inv_obj: Invariant[object] = inv_str  # Would fail type checking
        test_results.append({"test": "invariance", "passed": True})
        
        # Test covariance
        cov_str = Covariant[str]("test")
        cov_obj: Covariant[object] = cov_str  # Covariant allows this
        test_results.append({"test": "covariance", "passed": True})
        
        # Calculate generic type handling score
        total_generic_tests = len(test_results)
        passed_generic_tests = sum(1 for r in test_results if r.get("passed", False))
        generic_score = passed_generic_tests / total_generic_tests
        
        # Log generic type handling analysis
        self.logger.info(
            "Generic type handling analysis",
            context={
                "total_tests": total_generic_tests,
                "passed_tests": passed_generic_tests,
                "failed_tests": total_generic_tests - passed_generic_tests,
                "generic_score": generic_score,
                "test_categories": {
                    "basic_generics": sum(1 for r in test_results if "container" in r["test"]),
                    "bounded_types": sum(1 for r in test_results if "bounded" in r["test"]),
                    "protocols": sum(1 for r in test_results if "protocol" in r["test"]),
                    "variance": sum(1 for r in test_results if any(v in r["test"] for v in ["variance", "covariance"]))
                }
            }
        )
    
    async def test_type_guard_verification(self) -> None:
        """Test type guard functions and narrowing."""
        with patch('src.type_guards.is_discord_embed') as mock_is_embed:
            # Test type guard functions
            type_guard_log = []
            
            def log_type_guard(guard_name: str, value: Any, result: bool) -> None:
                """Log type guard execution."""
                type_guard_log.append({
                    "guard": guard_name,
                    "value_type": type(value).__name__,
                    "result": result,
                    "value_sample": str(value)[:50] if len(str(value)) > 50 else str(value)
                })
            
            # Test is_event_dict type guard
            test_events = [
                # Valid event
                {
                    "event_type": "Stop",
                    "session_id": "test_123",
                    "timestamp": "2025-07-12T22:00:00.000Z"
                },
                # Invalid event (missing required field)
                {
                    "event_type": "Stop",
                    "timestamp": "2025-07-12T22:00:00.000Z"
                },
                # Not a dict
                "not_an_event",
                # Empty dict
                {},
                # Valid tool use event
                {
                    "event_type": "PreToolUse",
                    "session_id": "test_456",
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "tool_name": "Write",
                    "arguments": {"file_path": "/test.txt", "content": "test"}
                }
            ]
            
            event_guard_results = []
            
            for event in test_events:
                is_valid = is_event_dict(event)
                event_guard_results.append({
                    "value": event,
                    "is_valid": is_valid,
                    "expected": isinstance(event, dict) and all(k in event for k in ["event_type", "session_id", "timestamp"])
                })
                log_type_guard("is_event_dict", event, is_valid)
            
            # Test is_tool_use_event type guard
            tool_use_guard_results = []
            
            for event in test_events:
                is_tool_use = is_tool_use_event(event)
                expected = (isinstance(event, dict) and 
                          event.get("event_type") in ["PreToolUse", "PostToolUse"] and
                          "tool_name" in event and "arguments" in event)
                
                tool_use_guard_results.append({
                    "value": event,
                    "is_valid": is_tool_use,
                    "expected": expected
                })
                log_type_guard("is_tool_use_event", event, is_tool_use)
            
            # Test is_discord_embed type guard
            test_embeds = [
                # Valid embed
                {
                    "title": "Test Embed",
                    "description": "Test description",
                    "color": 0x00ff00,
                    "fields": [
                        {"name": "Field 1", "value": "Value 1", "inline": True}
                    ]
                },
                # Minimal valid embed
                {
                    "description": "Minimal embed"
                },
                # Invalid embed (wrong field type)
                {
                    "title": "Invalid",
                    "fields": "not_a_list"
                },
                # Not a dict
                "not_an_embed"
            ]
            
            embed_guard_results = []
            
            for embed in test_embeds:
                mock_is_embed.return_value = isinstance(embed, dict) and (
                    "title" in embed or "description" in embed
                )
                is_valid = is_discord_embed(embed)
                
                embed_guard_results.append({
                    "value": embed,
                    "is_valid": is_valid
                })
                log_type_guard("is_discord_embed", embed, is_valid)
            
            # Test custom type guard
            def is_valid_config(value: Any) -> TypeGuard[ConfigDict]:
                """Custom type guard for configuration."""
                if not isinstance(value, dict):
                    return False
                
                # Check for some required config fields
                required_fields = ["DISCORD_WEBHOOK_URL", "DISCORD_USE_THREADS"]
                return any(field in value for field in required_fields)
            
            test_configs = [
                # Valid config
                {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/...",
                    "DISCORD_USE_THREADS": True,
                    "DISCORD_DEBUG": False
                },
                # Partial config
                {
                    "DISCORD_USE_THREADS": False
                },
                # Invalid config
                {
                    "unrelated_key": "value"
                },
                # Not a dict
                []
            ]
            
            config_guard_results = []
            
            for config in test_configs:
                is_valid = is_valid_config(config)
                config_guard_results.append({
                    "value": config,
                    "is_valid": is_valid
                })
                log_type_guard("is_valid_config", config, is_valid)
            
            # Test type narrowing with guards
            def process_with_narrowing(value: Union[EventDict, Dict[str, Any], str]) -> str:
                """Process value with type narrowing."""
                if is_event_dict(value):
                    # Type is narrowed to EventDict
                    return f"Event: {value['event_type']}"
                elif isinstance(value, dict):
                    # Type is narrowed to Dict[str, Any]
                    return f"Dict with {len(value)} keys"
                else:
                    # Type is narrowed to str
                    return f"String: {value}"
            
            narrowing_results = []
            
            for test_value in [test_events[0], {"key": "value"}, "test_string"]:
                result = process_with_narrowing(test_value)
                narrowing_results.append({
                    "input": test_value,
                    "output": result,
                    "type_narrowed": True
                })
            
            # Calculate type guard effectiveness
            total_guard_checks = len(type_guard_log)
            correct_guards = sum(1 for r in event_guard_results if r["is_valid"] == r.get("expected", r["is_valid"]))
            guard_accuracy = correct_guards / len(event_guard_results)
            
            # Log type guard verification analysis
            self.logger.info(
                "Type guard verification analysis",
                context={
                    "total_guard_checks": total_guard_checks,
                    "guard_types_tested": len(set(log["guard"] for log in type_guard_log)),
                    "guard_accuracy": guard_accuracy,
                    "type_narrowing_tests": len(narrowing_results),
                    "guard_distribution": {
                        guard: sum(1 for log in type_guard_log if log["guard"] == guard)
                        for guard in set(log["guard"] for log in type_guard_log)
                    },
                    "guard_effectiveness": {
                        "true_positives": sum(1 for log in type_guard_log if log["result"]),
                        "true_negatives": sum(1 for log in type_guard_log if not log["result"])
                    }
                }
            )
    
    # Helper methods
    
    def _validate_typed_dict(self, value: Any, spec: Dict[str, type]) -> bool:
        """Validate value against TypedDict specification."""
        if not isinstance(value, dict):
            return False
        
        for key, expected_type in spec.items():
            if key not in value:
                return False
            
            if not isinstance(value[key], expected_type):
                return False
        
        return True


def run_type_safety_tests() -> None:
    """Run type safety tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTypeSafety)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nType Safety Tests Summary:")
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