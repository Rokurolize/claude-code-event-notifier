#!/usr/bin/env python3
"""Content Accuracy Validator.

This module provides comprehensive validation for content accuracy including:
- Event formatting accuracy and consistency
- Tool output format compliance
- Content integrity across transformations
- Cross-reference validation between inputs and outputs
- Data loss detection during processing
- Timestamp accuracy and timezone handling
- Unicode and encoding preservation
"""

import asyncio
import json
import re
import difflib
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone
from dataclasses import dataclass, field
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.formatters.event_formatters import format_event
from src.formatters.tool_formatters import format_tool_output
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# Content accuracy validation types
@dataclass
class ContentAccuracyResult:
    """Result of content accuracy validation."""
    validation_id: str
    content_type: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    accuracy_score: float  # 0-100
    data_integrity_preserved: bool
    formatting_accurate: bool
    content_completeness: float  # 0-100
    transformation_fidelity: float  # 0-100
    validation_errors: List[str]
    validation_warnings: List[str]
    accuracy_metrics: Dict[str, float]
    content_differences: List[Dict[str, Any]]


@dataclass
class ContentValidationSpec:
    """Specification for content validation."""
    content_type: str
    required_fields: List[str]
    optional_fields: List[str]
    transformation_rules: Dict[str, Any]
    accuracy_thresholds: Dict[str, float]
    validation_functions: List[str]


class EventContentValidator:
    """Validates accuracy of event content formatting."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.validation_specs = self._load_validation_specs()
        
    def _load_validation_specs(self) -> Dict[str, ContentValidationSpec]:
        """Load content validation specifications for different event types."""
        return {
            "Write": ContentValidationSpec(
                content_type="file_operation",
                required_fields=["file_path", "content"],
                optional_fields=["encoding", "line_count"],
                transformation_rules={
                    "content_truncation": {"max_length": 2000, "truncation_suffix": "..."},
                    "path_normalization": {"preserve_absolute": True, "case_sensitive": True},
                    "timestamp_format": "iso8601_with_timezone"
                },
                accuracy_thresholds={
                    "content_preservation": 95.0,
                    "path_accuracy": 100.0,
                    "timestamp_accuracy": 100.0
                },
                validation_functions=["validate_file_path", "validate_content_integrity", "validate_timestamp"]
            ),
            "Edit": ContentValidationSpec(
                content_type="file_modification",
                required_fields=["file_path", "old_string", "new_string"],
                optional_fields=["line_number", "context"],
                transformation_rules={
                    "diff_representation": {"preserve_whitespace": True, "show_context": True},
                    "string_escaping": {"preserve_newlines": True, "escape_quotes": True}
                },
                accuracy_thresholds={
                    "diff_accuracy": 100.0,
                    "string_preservation": 100.0,
                    "context_accuracy": 95.0
                },
                validation_functions=["validate_diff_accuracy", "validate_string_changes"]
            ),
            "Read": ContentValidationSpec(
                content_type="file_reading",
                required_fields=["file_path", "content"],
                optional_fields=["line_range", "encoding"],
                transformation_rules={
                    "content_sampling": {"preview_length": 500, "preserve_structure": True},
                    "encoding_detection": {"preserve_original": True}
                },
                accuracy_thresholds={
                    "content_sampling_accuracy": 100.0,
                    "encoding_preservation": 100.0
                },
                validation_functions=["validate_content_sampling", "validate_encoding"]
            ),
            "Bash": ContentValidationSpec(
                content_type="command_execution",
                required_fields=["command", "exit_code"],
                optional_fields=["output", "error", "duration"],
                transformation_rules={
                    "command_sanitization": {"preserve_args": True, "mask_secrets": True},
                    "output_truncation": {"max_length": 1000, "preserve_errors": True}
                },
                accuracy_thresholds={
                    "command_accuracy": 100.0,
                    "exit_code_accuracy": 100.0,
                    "output_fidelity": 90.0
                },
                validation_functions=["validate_command_format", "validate_exit_code", "validate_output"]
            ),
            "Glob": ContentValidationSpec(
                content_type="file_search",
                required_fields=["pattern", "results"],
                optional_fields=["path", "recursive"],
                transformation_rules={
                    "pattern_preservation": {"preserve_wildcards": True, "case_sensitivity": True},
                    "results_formatting": {"sort_results": True, "relative_paths": True}
                },
                accuracy_thresholds={
                    "pattern_accuracy": 100.0,
                    "results_completeness": 95.0
                },
                validation_functions=["validate_pattern", "validate_search_results"]
            ),
            "Grep": ContentValidationSpec(
                content_type="content_search",
                required_fields=["pattern", "matches"],
                optional_fields=["files", "line_numbers", "context"],
                transformation_rules={
                    "regex_preservation": {"preserve_flags": True, "escape_special": False},
                    "match_formatting": {"include_line_numbers": True, "show_context": True}
                },
                accuracy_thresholds={
                    "pattern_accuracy": 100.0,
                    "match_accuracy": 95.0,
                    "context_preservation": 90.0
                },
                validation_functions=["validate_regex_pattern", "validate_matches"]
            ),
            "Task": ContentValidationSpec(
                content_type="task_execution",
                required_fields=["description", "result"],
                optional_fields=["duration", "steps", "artifacts"],
                transformation_rules={
                    "description_formatting": {"preserve_intent": True, "normalize_whitespace": True},
                    "result_summarization": {"key_points_only": True, "preserve_status": True}
                },
                accuracy_thresholds={
                    "description_fidelity": 95.0,
                    "result_accuracy": 90.0
                },
                validation_functions=["validate_task_description", "validate_task_result"]
            )
        }
    
    def validate_event_formatting(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any]) -> ContentAccuracyResult:
        """Validate accuracy of event formatting transformation."""
        validation_id = f"event_{input_event.get('event_type', 'unknown')}_{int(datetime.now().timestamp() * 1000)}"
        event_type = input_event.get("event_type", "unknown")
        
        validation_errors = []
        validation_warnings = []
        accuracy_metrics = {}
        content_differences = []
        
        # Get validation specification
        spec = self.validation_specs.get(event_type)
        if not spec:
            validation_errors.append(f"No validation specification for event type: {event_type}")
            return self._create_failed_result(validation_id, event_type, input_event, formatted_output, validation_errors)
        
        # Validate required fields preservation
        field_accuracy = self._validate_field_preservation(input_event, formatted_output, spec)
        accuracy_metrics.update(field_accuracy["metrics"])
        validation_errors.extend(field_accuracy["errors"])
        validation_warnings.extend(field_accuracy["warnings"])
        content_differences.extend(field_accuracy["differences"])
        
        # Validate transformation rules compliance
        transformation_accuracy = self._validate_transformation_rules(input_event, formatted_output, spec)
        accuracy_metrics.update(transformation_accuracy["metrics"])
        validation_errors.extend(transformation_accuracy["errors"])
        validation_warnings.extend(transformation_accuracy["warnings"])
        
        # Validate content integrity
        integrity_result = self._validate_content_integrity(input_event, formatted_output, spec)
        accuracy_metrics.update(integrity_result["metrics"])
        validation_errors.extend(integrity_result["errors"])
        
        # Validate timestamp accuracy
        timestamp_result = self._validate_timestamp_accuracy(input_event, formatted_output)
        accuracy_metrics.update(timestamp_result["metrics"])
        validation_errors.extend(timestamp_result["errors"])
        validation_warnings.extend(timestamp_result["warnings"])
        
        # Calculate overall scores
        accuracy_score = self._calculate_accuracy_score(accuracy_metrics, spec)
        data_integrity_preserved = len([e for e in validation_errors if "integrity" in e.lower()]) == 0
        formatting_accurate = len([e for e in validation_errors if "format" in e.lower()]) == 0
        content_completeness = accuracy_metrics.get("content_completeness", 0.0)
        transformation_fidelity = accuracy_metrics.get("transformation_fidelity", 0.0)
        
        return ContentAccuracyResult(
            validation_id=validation_id,
            content_type=event_type,
            input_data=input_event,
            output_data=formatted_output,
            accuracy_score=accuracy_score,
            data_integrity_preserved=data_integrity_preserved,
            formatting_accurate=formatting_accurate,
            content_completeness=content_completeness,
            transformation_fidelity=transformation_fidelity,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            accuracy_metrics=accuracy_metrics,
            content_differences=content_differences
        )
    
    def _validate_field_preservation(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any], spec: ContentValidationSpec) -> Dict[str, Any]:
        """Validate that required fields are preserved in formatting."""
        errors = []
        warnings = []
        differences = []
        metrics = {}
        
        input_data = input_event.get("data", {})
        
        # Check required fields
        required_preserved = 0
        for field in spec.required_fields:
            if field in input_data:
                input_value = input_data[field]
                
                # Look for field value in formatted output
                output_str = json.dumps(formatted_output)
                
                if isinstance(input_value, str):
                    # For string fields, check if content is preserved (allowing for truncation)
                    if len(input_value) <= 100:
                        # Short strings should be preserved exactly
                        if input_value in output_str:
                            required_preserved += 1
                        else:
                            errors.append(f"Required field '{field}' value not found in output")
                            differences.append({
                                "field": field,
                                "input_value": input_value,
                                "found_in_output": False,
                                "difference_type": "missing_content"
                            })
                    else:
                        # Long strings may be truncated
                        truncated_value = input_value[:50]  # Check first 50 chars
                        if truncated_value in output_str:
                            required_preserved += 1
                        else:
                            errors.append(f"Required field '{field}' content not preserved in output")
                            differences.append({
                                "field": field,
                                "input_value": input_value[:100] + "..." if len(input_value) > 100 else input_value,
                                "found_in_output": False,
                                "difference_type": "content_mismatch"
                            })
                else:
                    # For non-string fields, check if string representation is present
                    if str(input_value) in output_str:
                        required_preserved += 1
                    else:
                        warnings.append(f"Required field '{field}' value may not be preserved in output")
        
        required_preservation_rate = (required_preserved / len(spec.required_fields)) * 100 if spec.required_fields else 100
        metrics["required_field_preservation"] = required_preservation_rate
        
        # Check optional fields
        optional_preserved = 0
        for field in spec.optional_fields:
            if field in input_data:
                input_value = input_data[field]
                output_str = json.dumps(formatted_output)
                
                if str(input_value) in output_str:
                    optional_preserved += 1
        
        optional_preservation_rate = (optional_preserved / len(spec.optional_fields)) * 100 if spec.optional_fields else 100
        metrics["optional_field_preservation"] = optional_preservation_rate
        
        return {
            "errors": errors,
            "warnings": warnings,
            "differences": differences,
            "metrics": metrics
        }
    
    def _validate_transformation_rules(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any], spec: ContentValidationSpec) -> Dict[str, Any]:
        """Validate that transformation rules are properly applied."""
        errors = []
        warnings = []
        metrics = {}
        
        for rule_name, rule_config in spec.transformation_rules.items():
            if rule_name == "content_truncation":
                truncation_result = self._validate_content_truncation(input_event, formatted_output, rule_config)
                metrics.update(truncation_result["metrics"])
                errors.extend(truncation_result["errors"])
                warnings.extend(truncation_result["warnings"])
                
            elif rule_name == "timestamp_format":
                timestamp_result = self._validate_timestamp_format(input_event, formatted_output, rule_config)
                metrics.update(timestamp_result["metrics"])
                errors.extend(timestamp_result["errors"])
                
            elif rule_name == "path_normalization":
                path_result = self._validate_path_normalization(input_event, formatted_output, rule_config)
                metrics.update(path_result["metrics"])
                errors.extend(path_result["errors"])
                
            elif rule_name == "command_sanitization":
                sanitization_result = self._validate_command_sanitization(input_event, formatted_output, rule_config)
                metrics.update(sanitization_result["metrics"])
                errors.extend(sanitization_result["errors"])
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }
    
    def _validate_content_truncation(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any], rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate content truncation rules."""
        errors = []
        warnings = []
        metrics = {}
        
        max_length = rule_config.get("max_length", 2000)
        truncation_suffix = rule_config.get("truncation_suffix", "...")
        
        # Check if content fields are properly truncated
        input_data = input_event.get("data", {})
        output_str = json.dumps(formatted_output)
        
        for field, value in input_data.items():
            if isinstance(value, str) and len(value) > max_length:
                # Content should be truncated
                expected_truncated = value[:max_length - len(truncation_suffix)] + truncation_suffix
                
                if expected_truncated[:50] in output_str:  # Check first part of truncated content
                    metrics[f"{field}_truncation_correct"] = 100.0
                else:
                    # Check if any truncation occurred
                    if value[:50] in output_str and len(output_str) < len(value):
                        metrics[f"{field}_truncation_correct"] = 75.0  # Truncated but maybe different method
                        warnings.append(f"Field '{field}' truncated but not according to specified rules")
                    else:
                        metrics[f"{field}_truncation_correct"] = 0.0
                        errors.append(f"Field '{field}' not properly truncated")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }
    
    def _validate_timestamp_format(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any], expected_format: str) -> Dict[str, Any]:
        """Validate timestamp format compliance."""
        errors = []
        metrics = {}
        
        # Look for timestamp in input
        input_timestamp = input_event.get("timestamp")
        if not input_timestamp:
            return {"errors": [], "metrics": {"timestamp_format_compliance": 100.0}}
        
        # Check if timestamp appears in output in correct format
        output_str = json.dumps(formatted_output)
        
        if expected_format == "iso8601_with_timezone":
            # Look for ISO8601 format timestamps in output
            iso_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})'
            timestamps_in_output = re.findall(iso_pattern, output_str)
            
            if timestamps_in_output:
                # Verify at least one timestamp matches input
                try:
                    input_dt = datetime.fromisoformat(input_timestamp.replace("Z", "+00:00"))
                    for ts in timestamps_in_output:
                        output_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if abs((input_dt - output_dt).total_seconds()) < 1:  # Allow 1 second difference
                            metrics["timestamp_format_compliance"] = 100.0
                            return {"errors": errors, "metrics": metrics}
                    
                    errors.append("Timestamp in output doesn't match input timestamp")
                    metrics["timestamp_format_compliance"] = 50.0
                    
                except ValueError as e:
                    errors.append(f"Invalid timestamp format: {str(e)}")
                    metrics["timestamp_format_compliance"] = 0.0
            else:
                errors.append("No properly formatted timestamps found in output")
                metrics["timestamp_format_compliance"] = 0.0
        
        return {
            "errors": errors,
            "metrics": metrics
        }
    
    def _validate_path_normalization(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any], rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate file path normalization."""
        errors = []
        metrics = {}
        
        input_data = input_event.get("data", {})
        file_path = input_data.get("file_path")
        
        if not file_path:
            return {"errors": [], "metrics": {"path_normalization_compliance": 100.0}}
        
        output_str = json.dumps(formatted_output)
        preserve_absolute = rule_config.get("preserve_absolute", True)
        case_sensitive = rule_config.get("case_sensitive", True)
        
        # Check if file path appears in output
        if case_sensitive:
            path_found = file_path in output_str
        else:
            path_found = file_path.lower() in output_str.lower()
        
        if path_found:
            metrics["path_normalization_compliance"] = 100.0
        else:
            # Check for partial path preservation
            path_parts = file_path.split("/")
            filename = path_parts[-1] if path_parts else file_path
            
            if filename in output_str:
                metrics["path_normalization_compliance"] = 70.0
                if not preserve_absolute:
                    # Relative path is acceptable
                    metrics["path_normalization_compliance"] = 100.0
            else:
                errors.append(f"File path '{file_path}' not preserved in output")
                metrics["path_normalization_compliance"] = 0.0
        
        return {
            "errors": errors,
            "metrics": metrics
        }
    
    def _validate_command_sanitization(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any], rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate command sanitization rules."""
        errors = []
        metrics = {}
        
        input_data = input_event.get("data", {})
        command = input_data.get("command")
        
        if not command:
            return {"errors": [], "metrics": {"command_sanitization_compliance": 100.0}}
        
        output_str = json.dumps(formatted_output)
        preserve_args = rule_config.get("preserve_args", True)
        mask_secrets = rule_config.get("mask_secrets", True)
        
        # Check if command appears in output
        if command in output_str:
            metrics["command_sanitization_compliance"] = 100.0
            
            # Check for potential secrets if masking is enabled
            if mask_secrets:
                secret_patterns = [
                    r'password[=\s]+\S+',
                    r'token[=\s]+\S+',
                    r'key[=\s]+\S+',
                    r'secret[=\s]+\S+'
                ]
                
                for pattern in secret_patterns:
                    if re.search(pattern, output_str, re.IGNORECASE):
                        errors.append("Potential secret detected in command output")
                        metrics["command_sanitization_compliance"] = 50.0
                        break
        else:
            # Check if command parts are preserved
            command_parts = command.split()
            if command_parts:
                base_command = command_parts[0]
                if base_command in output_str:
                    if preserve_args and len(command_parts) > 1:
                        metrics["command_sanitization_compliance"] = 50.0
                    else:
                        metrics["command_sanitization_compliance"] = 100.0
                else:
                    errors.append(f"Command '{command}' not preserved in output")
                    metrics["command_sanitization_compliance"] = 0.0
        
        return {
            "errors": errors,
            "metrics": metrics
        }
    
    def _validate_content_integrity(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any], spec: ContentValidationSpec) -> Dict[str, Any]:
        """Validate overall content integrity."""
        errors = []
        metrics = {}
        
        input_data = input_event.get("data", {})
        output_str = json.dumps(formatted_output)
        
        # Calculate content preservation ratio
        total_chars_input = sum(len(str(v)) for v in input_data.values() if isinstance(v, (str, int, float)))
        
        # Count how much input content appears in output
        preserved_chars = 0
        for value in input_data.values():
            if isinstance(value, str):
                # Check substring preservation
                for i in range(0, len(value), 50):  # Check in 50-char chunks
                    chunk = value[i:i+50]
                    if chunk in output_str:
                        preserved_chars += len(chunk)
            elif isinstance(value, (int, float)):
                if str(value) in output_str:
                    preserved_chars += len(str(value))
        
        content_preservation_ratio = (preserved_chars / total_chars_input * 100) if total_chars_input > 0 else 100
        metrics["content_preservation_ratio"] = content_preservation_ratio
        
        # Check against threshold
        threshold = spec.accuracy_thresholds.get("content_preservation", 95.0)
        if content_preservation_ratio < threshold:
            errors.append(f"Content preservation ratio {content_preservation_ratio:.1f}% below threshold {threshold}%")
        
        # Validate encoding preservation
        encoding_errors = self._validate_encoding_preservation(input_data, output_str)
        errors.extend(encoding_errors)
        
        # Calculate overall integrity score
        integrity_score = min(100.0, content_preservation_ratio)
        if encoding_errors:
            integrity_score *= 0.8  # Penalize encoding issues
        
        metrics["content_integrity_score"] = integrity_score
        
        return {
            "errors": errors,
            "metrics": metrics
        }
    
    def _validate_encoding_preservation(self, input_data: Dict[str, Any], output_str: str) -> List[str]:
        """Validate that encoding is preserved."""
        errors = []
        
        for field, value in input_data.items():
            if isinstance(value, str):
                # Check for Unicode characters
                unicode_chars = [c for c in value if ord(c) > 127]
                if unicode_chars:
                    # Check if Unicode characters are preserved in output
                    for char in unicode_chars[:5]:  # Check first 5 Unicode chars
                        if char not in output_str:
                            errors.append(f"Unicode character '{char}' from field '{field}' not preserved")
                            break
        
        return errors
    
    def _validate_timestamp_accuracy(self, input_event: Dict[str, Any], formatted_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate timestamp accuracy and timezone handling."""
        errors = []
        warnings = []
        metrics = {}
        
        input_timestamp = input_event.get("timestamp")
        if not input_timestamp:
            metrics["timestamp_accuracy"] = 100.0
            return {"errors": errors, "warnings": warnings, "metrics": metrics}
        
        output_str = json.dumps(formatted_output)
        
        try:
            # Parse input timestamp
            input_dt = datetime.fromisoformat(input_timestamp.replace("Z", "+00:00"))
            
            # Look for timestamps in output
            timestamp_patterns = [
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',  # ISO8601
                r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # Simple datetime
                r'\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}',  # US format
            ]
            
            found_timestamps = []
            for pattern in timestamp_patterns:
                matches = re.findall(pattern, output_str)
                found_timestamps.extend(matches)
            
            if found_timestamps:
                # Check if any timestamp matches input (allowing for timezone conversion)
                accuracy_scores = []
                
                for ts_str in found_timestamps:
                    try:
                        # Try to parse found timestamp
                        if 'T' in ts_str and ('+' in ts_str or 'Z' in ts_str):
                            # ISO format
                            output_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        else:
                            # Assume UTC for simple formats
                            output_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                        
                        # Calculate time difference
                        time_diff = abs((input_dt - output_dt).total_seconds())
                        
                        if time_diff <= 1:
                            accuracy_scores.append(100.0)
                        elif time_diff <= 60:
                            accuracy_scores.append(90.0)
                        elif time_diff <= 3600:
                            accuracy_scores.append(70.0)
                        else:
                            accuracy_scores.append(0.0)
                            
                    except ValueError:
                        continue
                
                if accuracy_scores:
                    metrics["timestamp_accuracy"] = max(accuracy_scores)
                    if max(accuracy_scores) < 100.0:
                        warnings.append("Timestamp accuracy not perfect - possible timezone conversion")
                else:
                    errors.append("Found timestamps but none match input timestamp")
                    metrics["timestamp_accuracy"] = 0.0
            else:
                errors.append("No timestamps found in output")
                metrics["timestamp_accuracy"] = 0.0
                
        except ValueError as e:
            errors.append(f"Invalid input timestamp format: {str(e)}")
            metrics["timestamp_accuracy"] = 0.0
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }
    
    def _calculate_accuracy_score(self, metrics: Dict[str, float], spec: ContentValidationSpec) -> float:
        """Calculate overall accuracy score."""
        
        # Weight different metrics based on importance
        weights = {
            "required_field_preservation": 0.3,
            "content_preservation_ratio": 0.25,
            "timestamp_accuracy": 0.15,
            "content_integrity_score": 0.15,
            "transformation_fidelity": 0.1,
            "optional_field_preservation": 0.05
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in metrics:
                total_score += metrics[metric] * weight
                total_weight += weight
        
        # Calculate transformation fidelity if not explicitly set
        if "transformation_fidelity" not in metrics:
            transformation_scores = [
                metrics.get(f"{field}_truncation_correct", 100.0) 
                for field in ["content", "output", "description"]
                if f"{field}_truncation_correct" in metrics
            ]
            if transformation_scores:
                metrics["transformation_fidelity"] = sum(transformation_scores) / len(transformation_scores)
                total_score += metrics["transformation_fidelity"] * weights["transformation_fidelity"]
                total_weight += weights["transformation_fidelity"]
        
        # Apply threshold penalties
        for threshold_name, threshold_value in spec.accuracy_thresholds.items():
            metric_name = threshold_name.replace("_threshold", "")
            if metric_name in metrics and metrics[metric_name] < threshold_value:
                penalty = (threshold_value - metrics[metric_name]) / threshold_value * 0.1
                total_score *= (1 - penalty)
        
        return min(100.0, total_score / total_weight * 100) if total_weight > 0 else 0.0
    
    def _create_failed_result(self, validation_id: str, content_type: str, input_data: Dict[str, Any], output_data: Dict[str, Any], errors: List[str]) -> ContentAccuracyResult:
        """Create a failed validation result."""
        return ContentAccuracyResult(
            validation_id=validation_id,
            content_type=content_type,
            input_data=input_data,
            output_data=output_data,
            accuracy_score=0.0,
            data_integrity_preserved=False,
            formatting_accurate=False,
            content_completeness=0.0,
            transformation_fidelity=0.0,
            validation_errors=errors,
            validation_warnings=[],
            accuracy_metrics={},
            content_differences=[]
        )


class ToolContentValidator:
    """Validates accuracy of tool-specific content formatting."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        
    def validate_tool_output_accuracy(self, tool_name: str, input_data: Dict[str, Any], formatted_output: Dict[str, Any]) -> ContentAccuracyResult:
        """Validate accuracy of tool-specific output formatting."""
        validation_id = f"tool_{tool_name}_{int(datetime.now().timestamp() * 1000)}"
        
        validation_errors = []
        validation_warnings = []
        accuracy_metrics = {}
        content_differences = []
        
        # Tool-specific validation
        if tool_name == "Bash":
            result = self._validate_bash_output(input_data, formatted_output)
        elif tool_name == "Read":
            result = self._validate_read_output(input_data, formatted_output)
        elif tool_name == "Write":
            result = self._validate_write_output(input_data, formatted_output)
        elif tool_name == "Edit":
            result = self._validate_edit_output(input_data, formatted_output)
        elif tool_name in ["Glob", "Grep"]:
            result = self._validate_search_output(tool_name, input_data, formatted_output)
        else:
            result = self._validate_generic_tool_output(tool_name, input_data, formatted_output)
        
        accuracy_metrics.update(result["metrics"])
        validation_errors.extend(result["errors"])
        validation_warnings.extend(result["warnings"])
        content_differences.extend(result.get("differences", []))
        
        # Calculate overall scores
        accuracy_score = sum(accuracy_metrics.values()) / len(accuracy_metrics) if accuracy_metrics else 0.0
        data_integrity_preserved = len([e for e in validation_errors if "integrity" in e.lower()]) == 0
        formatting_accurate = len([e for e in validation_errors if "format" in e.lower()]) == 0
        
        return ContentAccuracyResult(
            validation_id=validation_id,
            content_type=f"tool_{tool_name}",
            input_data=input_data,
            output_data=formatted_output,
            accuracy_score=accuracy_score,
            data_integrity_preserved=data_integrity_preserved,
            formatting_accurate=formatting_accurate,
            content_completeness=accuracy_metrics.get("content_completeness", 0.0),
            transformation_fidelity=accuracy_metrics.get("transformation_fidelity", 0.0),
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            accuracy_metrics=accuracy_metrics,
            content_differences=content_differences
        )
    
    def _validate_bash_output(self, input_data: Dict[str, Any], formatted_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Bash command output formatting."""
        errors = []
        warnings = []
        metrics = {}
        
        command = input_data.get("command", "")
        exit_code = input_data.get("exit_code", 0)
        output = input_data.get("output", "")
        
        output_str = json.dumps(formatted_output)
        
        # Validate command preservation
        if command and command in output_str:
            metrics["command_accuracy"] = 100.0
        elif command:
            # Check if command base is preserved
            base_command = command.split()[0] if command.split() else command
            if base_command in output_str:
                metrics["command_accuracy"] = 75.0
                warnings.append("Command base preserved but full command may be truncated")
            else:
                metrics["command_accuracy"] = 0.0
                errors.append("Command not preserved in output")
        else:
            metrics["command_accuracy"] = 100.0  # No command to validate
        
        # Validate exit code
        if str(exit_code) in output_str:
            metrics["exit_code_accuracy"] = 100.0
        else:
            errors.append("Exit code not found in output")
            metrics["exit_code_accuracy"] = 0.0
        
        # Validate output content
        if output:
            if len(output) <= 500:
                # Short output should be preserved fully
                if output[:100] in output_str:
                    metrics["output_fidelity"] = 100.0
                else:
                    metrics["output_fidelity"] = 0.0
                    errors.append("Command output not preserved")
            else:
                # Long output may be truncated
                if output[:100] in output_str:
                    metrics["output_fidelity"] = 90.0
                else:
                    metrics["output_fidelity"] = 0.0
                    errors.append("Command output not preserved")
        else:
            metrics["output_fidelity"] = 100.0  # No output to validate
        
        metrics["content_completeness"] = (metrics["command_accuracy"] + metrics["exit_code_accuracy"] + metrics["output_fidelity"]) / 3
        metrics["transformation_fidelity"] = metrics["content_completeness"]
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }
    
    def _validate_read_output(self, input_data: Dict[str, Any], formatted_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Read operation output formatting."""
        errors = []
        warnings = []
        metrics = {}
        
        file_path = input_data.get("file_path", "")
        content = input_data.get("content", "")
        
        output_str = json.dumps(formatted_output)
        
        # Validate file path
        if file_path and file_path in output_str:
            metrics["path_accuracy"] = 100.0
        elif file_path:
            # Check for filename only
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            if filename in output_str:
                metrics["path_accuracy"] = 80.0
            else:
                metrics["path_accuracy"] = 0.0
                errors.append("File path not preserved in output")
        else:
            metrics["path_accuracy"] = 100.0
        
        # Validate content sampling
        if content:
            content_preview = content[:200]  # First 200 chars
            if content_preview in output_str:
                metrics["content_sampling_accuracy"] = 100.0
            elif content[:50] in output_str:
                metrics["content_sampling_accuracy"] = 75.0
                warnings.append("Content sampling may be truncated differently than expected")
            else:
                metrics["content_sampling_accuracy"] = 0.0
                errors.append("File content not preserved in output")
        else:
            metrics["content_sampling_accuracy"] = 100.0
        
        metrics["content_completeness"] = (metrics["path_accuracy"] + metrics["content_sampling_accuracy"]) / 2
        metrics["transformation_fidelity"] = metrics["content_completeness"]
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }
    
    def _validate_write_output(self, input_data: Dict[str, Any], formatted_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Write operation output formatting."""
        errors = []
        warnings = []
        metrics = {}
        
        file_path = input_data.get("file_path", "")
        content = input_data.get("content", "")
        
        output_str = json.dumps(formatted_output)
        
        # Validate file path
        if file_path and file_path in output_str:
            metrics["path_accuracy"] = 100.0
        elif file_path:
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            if filename in output_str:
                metrics["path_accuracy"] = 80.0
            else:
                metrics["path_accuracy"] = 0.0
                errors.append("File path not preserved in output")
        else:
            metrics["path_accuracy"] = 100.0
        
        # Validate content preservation
        if content:
            if len(content) <= 100:
                # Short content should be preserved
                if content in output_str:
                    metrics["content_preservation"] = 100.0
                else:
                    metrics["content_preservation"] = 0.0
                    errors.append("File content not preserved in output")
            else:
                # Long content may be truncated
                content_preview = content[:100]
                if content_preview in output_str:
                    metrics["content_preservation"] = 90.0
                else:
                    metrics["content_preservation"] = 0.0
                    errors.append("File content not preserved in output")
        else:
            metrics["content_preservation"] = 100.0
        
        metrics["content_completeness"] = (metrics["path_accuracy"] + metrics["content_preservation"]) / 2
        metrics["transformation_fidelity"] = metrics["content_completeness"]
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }
    
    def _validate_edit_output(self, input_data: Dict[str, Any], formatted_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Edit operation output formatting."""
        errors = []
        warnings = []
        metrics = {}
        differences = []
        
        file_path = input_data.get("file_path", "")
        old_string = input_data.get("old_string", "")
        new_string = input_data.get("new_string", "")
        
        output_str = json.dumps(formatted_output)
        
        # Validate file path
        if file_path and file_path in output_str:
            metrics["path_accuracy"] = 100.0
        elif file_path:
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            if filename in output_str:
                metrics["path_accuracy"] = 80.0
            else:
                metrics["path_accuracy"] = 0.0
                errors.append("File path not preserved in output")
        else:
            metrics["path_accuracy"] = 100.0
        
        # Validate diff representation
        old_preserved = old_string in output_str if old_string else True
        new_preserved = new_string in output_str if new_string else True
        
        if old_preserved and new_preserved:
            metrics["diff_accuracy"] = 100.0
        elif old_preserved or new_preserved:
            metrics["diff_accuracy"] = 50.0
            warnings.append("Only partial diff information preserved")
            differences.append({
                "field": "edit_changes",
                "old_preserved": old_preserved,
                "new_preserved": new_preserved,
                "difference_type": "partial_diff"
            })
        else:
            metrics["diff_accuracy"] = 0.0
            errors.append("Edit changes not preserved in output")
            differences.append({
                "field": "edit_changes",
                "old_preserved": False,
                "new_preserved": False,
                "difference_type": "missing_diff"
            })
        
        metrics["content_completeness"] = (metrics["path_accuracy"] + metrics["diff_accuracy"]) / 2
        metrics["transformation_fidelity"] = metrics["content_completeness"]
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
            "differences": differences
        }
    
    def _validate_search_output(self, tool_name: str, input_data: Dict[str, Any], formatted_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search operation (Glob/Grep) output formatting."""
        errors = []
        warnings = []
        metrics = {}
        
        pattern = input_data.get("pattern", "")
        results = input_data.get("results", []) if tool_name == "Glob" else input_data.get("matches", [])
        
        output_str = json.dumps(formatted_output)
        
        # Validate pattern preservation
        if pattern and pattern in output_str:
            metrics["pattern_accuracy"] = 100.0
        elif pattern:
            # Check for escaped pattern
            escaped_chars = ["*", "?", "[", "]", "\\", ".", "+", "^", "$"]
            pattern_found = False
            for char in escaped_chars:
                if char in pattern and pattern.replace(char, f"\\{char}") in output_str:
                    pattern_found = True
                    break
            
            if pattern_found:
                metrics["pattern_accuracy"] = 90.0
            else:
                metrics["pattern_accuracy"] = 0.0
                errors.append("Search pattern not preserved in output")
        else:
            metrics["pattern_accuracy"] = 100.0
        
        # Validate results
        if results:
            results_preserved = 0
            for result in results[:5]:  # Check first 5 results
                if str(result) in output_str:
                    results_preserved += 1
            
            preservation_rate = (results_preserved / min(5, len(results))) * 100
            metrics["results_completeness"] = preservation_rate
            
            if preservation_rate < 80:
                warnings.append(f"Only {preservation_rate:.0f}% of search results preserved")
        else:
            metrics["results_completeness"] = 100.0
        
        metrics["content_completeness"] = (metrics["pattern_accuracy"] + metrics["results_completeness"]) / 2
        metrics["transformation_fidelity"] = metrics["content_completeness"]
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }
    
    def _validate_generic_tool_output(self, tool_name: str, input_data: Dict[str, Any], formatted_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generic tool output formatting."""
        errors = []
        warnings = []
        metrics = {}
        
        output_str = json.dumps(formatted_output)
        
        # Basic preservation check
        preserved_fields = 0
        total_fields = len(input_data)
        
        for field, value in input_data.items():
            if isinstance(value, (str, int, float)) and str(value) in output_str:
                preserved_fields += 1
        
        preservation_rate = (preserved_fields / total_fields * 100) if total_fields > 0 else 100
        metrics["field_preservation"] = preservation_rate
        
        if preservation_rate < 70:
            errors.append(f"Low field preservation rate: {preservation_rate:.0f}%")
        elif preservation_rate < 90:
            warnings.append(f"Moderate field preservation rate: {preservation_rate:.0f}%")
        
        metrics["content_completeness"] = preservation_rate
        metrics["transformation_fidelity"] = preservation_rate
        
        return {
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics
        }


class ContentAccuracyValidator(BaseQualityChecker):
    """Comprehensive content accuracy validator."""
    
    def __init__(self):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.event_validator = EventContentValidator()
        self.tool_validator = ToolContentValidator()
        self.validation_results = []
        
    async def validate_event_content_accuracy(self, input_event: Dict[str, Any]) -> ContentAccuracyResult:
        """Validate content accuracy for event formatting."""
        try:
            # Format the event using the actual formatter
            formatted_output = format_event(input_event)
            
            # Validate accuracy
            result = self.event_validator.validate_event_formatting(input_event, formatted_output)
            self.validation_results.append(result)
            
            return result
            
        except Exception as e:
            self.logger.error("Event content validation failed", error=str(e), event=input_event)
            
            # Return failed result
            validation_id = f"event_error_{int(datetime.now().timestamp() * 1000)}"
            return ContentAccuracyResult(
                validation_id=validation_id,
                content_type="error",
                input_data=input_event,
                output_data={},
                accuracy_score=0.0,
                data_integrity_preserved=False,
                formatting_accurate=False,
                content_completeness=0.0,
                transformation_fidelity=0.0,
                validation_errors=[f"Validation failed: {str(e)}"],
                validation_warnings=[],
                accuracy_metrics={},
                content_differences=[]
            )
    
    async def validate_tool_content_accuracy(self, tool_name: str, input_data: Dict[str, Any]) -> ContentAccuracyResult:
        """Validate content accuracy for tool output formatting."""
        try:
            # Format the tool output using the actual formatter
            formatted_output = format_tool_output(tool_name, input_data)
            
            # Validate accuracy
            result = self.tool_validator.validate_tool_output_accuracy(tool_name, input_data, formatted_output)
            self.validation_results.append(result)
            
            return result
            
        except Exception as e:
            self.logger.error("Tool content validation failed", error=str(e), tool=tool_name, data=input_data)
            
            # Return failed result
            validation_id = f"tool_error_{int(datetime.now().timestamp() * 1000)}"
            return ContentAccuracyResult(
                validation_id=validation_id,
                content_type=f"tool_{tool_name}_error",
                input_data=input_data,
                output_data={},
                accuracy_score=0.0,
                data_integrity_preserved=False,
                formatting_accurate=False,
                content_completeness=0.0,
                transformation_fidelity=0.0,
                validation_errors=[f"Tool validation failed: {str(e)}"],
                validation_warnings=[],
                accuracy_metrics={},
                content_differences=[]
            )
    
    async def validate_batch_content_accuracy(self, test_cases: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Validate content accuracy for a batch of test cases."""
        batch_results = []
        
        for case_type, test_data in test_cases:
            if case_type == "event":
                result = await self.validate_event_content_accuracy(test_data)
            elif case_type.startswith("tool_"):
                tool_name = case_type.replace("tool_", "")
                result = await self.validate_tool_content_accuracy(tool_name, test_data)
            else:
                continue
            
            batch_results.append(result)
        
        # Calculate batch statistics
        total_validations = len(batch_results)
        successful_validations = sum(1 for r in batch_results if r.accuracy_score >= 90.0)
        average_accuracy = sum(r.accuracy_score for r in batch_results) / total_validations if total_validations > 0 else 0
        average_completeness = sum(r.content_completeness for r in batch_results) / total_validations if total_validations > 0 else 0
        average_fidelity = sum(r.transformation_fidelity for r in batch_results) / total_validations if total_validations > 0 else 0
        
        # Group by content type
        content_type_stats = {}
        for result in batch_results:
            content_type = result.content_type
            if content_type not in content_type_stats:
                content_type_stats[content_type] = {
                    "total": 0,
                    "successful": 0,
                    "avg_accuracy": 0,
                    "avg_completeness": 0,
                    "avg_fidelity": 0
                }
            
            stats = content_type_stats[content_type]
            stats["total"] += 1
            if result.accuracy_score >= 90.0:
                stats["successful"] += 1
            stats["avg_accuracy"] += result.accuracy_score
            stats["avg_completeness"] += result.content_completeness
            stats["avg_fidelity"] += result.transformation_fidelity
        
        # Calculate averages for each content type
        for content_type, stats in content_type_stats.items():
            if stats["total"] > 0:
                stats["avg_accuracy"] /= stats["total"]
                stats["avg_completeness"] /= stats["total"]
                stats["avg_fidelity"] /= stats["total"]
                stats["success_rate"] = stats["successful"] / stats["total"]
        
        return {
            "batch_summary": {
                "total_validations": total_validations,
                "successful_validations": successful_validations,
                "success_rate": successful_validations / total_validations if total_validations > 0 else 0,
                "average_accuracy_score": average_accuracy,
                "average_content_completeness": average_completeness,
                "average_transformation_fidelity": average_fidelity
            },
            "content_type_statistics": content_type_stats,
            "individual_results": batch_results,
            "quality_assessment": self._assess_content_quality(batch_results)
        }
    
    def _assess_content_quality(self, results: List[ContentAccuracyResult]) -> str:
        """Assess overall content quality."""
        if not results:
            return "no_data"
        
        avg_accuracy = sum(r.accuracy_score for r in results) / len(results)
        avg_completeness = sum(r.content_completeness for r in results) / len(results)
        avg_fidelity = sum(r.transformation_fidelity for r in results) / len(results)
        
        integrity_rate = sum(1 for r in results if r.data_integrity_preserved) / len(results)
        format_rate = sum(1 for r in results if r.formatting_accurate) / len(results)
        
        if (avg_accuracy >= 95 and avg_completeness >= 95 and avg_fidelity >= 95 and 
            integrity_rate >= 0.95 and format_rate >= 0.95):
            return "excellent"
        elif (avg_accuracy >= 90 and avg_completeness >= 90 and avg_fidelity >= 90 and
              integrity_rate >= 0.90 and format_rate >= 0.90):
            return "good"
        elif (avg_accuracy >= 80 and avg_completeness >= 80 and avg_fidelity >= 80 and
              integrity_rate >= 0.80 and format_rate >= 0.80):
            return "acceptable"
        elif (avg_accuracy >= 60 and avg_completeness >= 60 and avg_fidelity >= 60):
            return "poor"
        else:
            return "critical"
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check overall quality of content accuracy validation."""
        if not self.validation_results:
            return {
                "quality_level": "unknown",
                "message": "No validation results available"
            }
        
        total_validations = len(self.validation_results)
        high_accuracy_validations = sum(1 for r in self.validation_results if r.accuracy_score >= 90.0)
        avg_accuracy = sum(r.accuracy_score for r in self.validation_results) / total_validations
        avg_completeness = sum(r.content_completeness for r in self.validation_results) / total_validations
        avg_fidelity = sum(r.transformation_fidelity for r in self.validation_results) / total_validations
        
        # Count integrity and formatting preservation
        integrity_preserved = sum(1 for r in self.validation_results if r.data_integrity_preserved)
        formatting_accurate = sum(1 for r in self.validation_results if r.formatting_accurate)
        
        # Determine quality level
        quality_assessment = self._assess_content_quality(self.validation_results)
        
        return {
            "quality_level": quality_assessment,
            "total_validations": total_validations,
            "high_accuracy_rate": high_accuracy_validations / total_validations,
            "average_accuracy_score": avg_accuracy,
            "average_content_completeness": avg_completeness,
            "average_transformation_fidelity": avg_fidelity,
            "data_integrity_preservation_rate": integrity_preserved / total_validations,
            "formatting_accuracy_rate": formatting_accurate / total_validations,
            "validation_summary": {
                "total_errors": sum(len(r.validation_errors) for r in self.validation_results),
                "total_warnings": sum(len(r.validation_warnings) for r in self.validation_results),
                "content_differences_detected": sum(len(r.content_differences) for r in self.validation_results)
            }
        }