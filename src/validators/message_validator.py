#!/usr/bin/env python3
"""Message validation for Discord send/receive verification.

This module provides comprehensive validation of Discord messages,
comparing sent content with received content for accuracy testing.
"""

import re
from datetime import datetime
from typing import Any, Optional, TypedDict

from src.core.discord_receiver import DiscordMessage
from src.core.http_client import DiscordEmbed
from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import get_user_datetime


class ValidationResult(TypedDict):
    """Result of message validation."""
    success: bool
    errors: list[str]
    warnings: list[str]
    details: dict[str, Any]


class ContentMismatch(TypedDict):
    """Details of content mismatch."""
    field: str
    expected: str
    actual: str
    similarity_score: float


class MessageValidator:
    """Validator for Discord message send/receive verification."""
    
    def __init__(self) -> None:
        """Initialize message validator."""
        self.logger = AstolfoLogger(__name__)
    
    def validate_subagent_message(
        self,
        sent_embed: DiscordEmbed,
        received_message: DiscordMessage,
        expected_subagent_id: str
    ) -> ValidationResult:
        """Validate a subagent completion message.
        
        Args:
            sent_embed: The embed that was sent
            received_message: The message received from Discord
            expected_subagent_id: Expected subagent identifier
            
        Returns:
            Validation result with success status and details
        """
        self.logger.info(
            "Validating subagent message",
            expected_subagent_id=expected_subagent_id,
            message_id=received_message.get("id", "unknown")
        )
        
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}
        
        # Extract received embed (should be first embed)
        received_embeds = received_message.get("embeds", [])
        if not received_embeds:
            errors.append("No embeds found in received message")
            return {
                "success": False,
                "errors": errors,
                "warnings": warnings,
                "details": details
            }
        
        received_embed = received_embeds[0]
        
        # Validate embed title
        sent_title = sent_embed.get("title", "")
        received_title = received_embed.get("title", "")
        if sent_title != received_title:
            errors.append(f"Title mismatch: expected '{sent_title}', got '{received_title}'")
        
        # Validate subagent ID in description
        received_description = received_embed.get("description", "")
        if f"Subagent ID:** {expected_subagent_id}" not in received_description:
            errors.append(f"Subagent ID '{expected_subagent_id}' not found in description")
        
        # Validate JST timestamp format
        jst_validation = self._validate_jst_timestamp(received_description)
        if not jst_validation["success"]:
            errors.extend(jst_validation["errors"])
            warnings.extend(jst_validation["warnings"])
        
        details.update(jst_validation["details"])
        
        # Check for contamination warnings
        contamination_check = self._check_contamination_warnings(received_embed)
        details.update(contamination_check)
        
        if contamination_check["contamination_detected"]:
            warnings.append("Contamination warnings detected in message fields")
        
        # Validate embed fields if present
        if "fields" in sent_embed and sent_embed["fields"]:
            field_validation = self._validate_embed_fields(
                sent_embed["fields"], 
                received_embed.get("fields", [])
            )
            errors.extend(field_validation["errors"])
            warnings.extend(field_validation["warnings"])
            details.update(field_validation["details"])
        
        success = len(errors) == 0
        
        self.logger.info(
            "Subagent message validation completed",
            success=success,
            error_count=len(errors),
            warning_count=len(warnings),
            expected_subagent_id=expected_subagent_id
        )
        
        return {
            "success": success,
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    def _validate_jst_timestamp(self, description: str) -> ValidationResult:
        """Validate JST timestamp format in description.
        
        Args:
            description: Embed description containing timestamp
            
        Returns:
            Validation result for timestamp
        """
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}
        
        # Look for "Completed at:" timestamp
        jst_pattern = r"Completed at:\*\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} JST)"
        match = re.search(jst_pattern, description)
        
        if not match:
            errors.append("JST timestamp not found in 'Completed at' field")
            details["timestamp_found"] = False
            return {
                "success": False,
                "errors": errors,
                "warnings": warnings,
                "details": details
            }
        
        timestamp_str = match.group(1)
        details["timestamp_found"] = True
        details["timestamp_string"] = timestamp_str
        
        # Parse timestamp
        try:
            # Remove JST suffix for parsing
            time_part = timestamp_str.replace(" JST", "")
            parsed_time = datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S")
            details["timestamp_parsed"] = True
            details["parsed_time"] = parsed_time.isoformat()
            
            # Check if timestamp is reasonably recent (within last 10 minutes)
            current_time = get_user_datetime()
            time_diff = abs((current_time.replace(tzinfo=None) - parsed_time).total_seconds())
            
            if time_diff > 600:  # 10 minutes
                warnings.append(f"Timestamp is {time_diff:.0f} seconds old (may be stale)")
            
            details["time_difference_seconds"] = time_diff
            
            # Validate JST suffix is present
            if not timestamp_str.endswith(" JST"):
                errors.append("Timestamp should end with ' JST' suffix")
            
        except ValueError as e:
            errors.append(f"Failed to parse timestamp '{timestamp_str}': {e}")
            details["timestamp_parsed"] = False
        
        return {
            "success": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    def _check_contamination_warnings(self, embed: dict[str, Any]) -> dict[str, Any]:
        """Check for contamination warning labels in embed.
        
        Args:
            embed: Discord embed to check
            
        Returns:
            Dictionary with contamination detection results
        """
        contamination_detected = False
        contaminated_fields: list[str] = []
        contamination_types: list[str] = []
        
        # Check embed fields for contamination warnings
        fields = embed.get("fields", [])
        for field in fields:
            field_value = field.get("value", "")
            field_name = field.get("name", "Unknown field")
            
            # Look for contamination warning pattern
            contamination_pattern = r"⚠️ \[CONTAMINATION DETECTED: ([^\]]+)\]"
            match = re.search(contamination_pattern, field_value)
            
            if match:
                contamination_detected = True
                contaminated_fields.append(field_name)
                contamination_type = match.group(1)
                contamination_types.append(contamination_type)
        
        return {
            "contamination_detected": contamination_detected,
            "contaminated_fields": contaminated_fields,
            "contamination_types": contamination_types,
            "contamination_count": len(contaminated_fields)
        }
    
    def _validate_embed_fields(
        self,
        sent_fields: list[dict[str, Any]],
        received_fields: list[dict[str, Any]]
    ) -> ValidationResult:
        """Validate embed fields match between sent and received.
        
        Args:
            sent_fields: Fields that were sent
            received_fields: Fields that were received
            
        Returns:
            Validation result for fields
        """
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}
        
        details["sent_field_count"] = len(sent_fields)
        details["received_field_count"] = len(received_fields)
        
        # Check field count matches
        if len(sent_fields) != len(received_fields):
            errors.append(
                f"Field count mismatch: sent {len(sent_fields)}, received {len(received_fields)}"
            )
        
        # Compare individual fields
        mismatches: list[ContentMismatch] = []
        
        for i, sent_field in enumerate(sent_fields):
            if i >= len(received_fields):
                errors.append(f"Missing received field at index {i}")
                continue
            
            received_field = received_fields[i]
            
            # Compare field names
            sent_name = sent_field.get("name", "")
            received_name = received_field.get("name", "")
            if sent_name != received_name:
                mismatches.append({
                    "field": f"field[{i}].name",
                    "expected": sent_name,
                    "actual": received_name,
                    "similarity_score": self._calculate_similarity(sent_name, received_name)
                })
            
            # Compare field values (with contamination awareness)
            sent_value = sent_field.get("value", "")
            received_value = received_field.get("value", "")
            
            # If contamination warning is present, extract original content
            contamination_pattern = r"⚠️ \[CONTAMINATION DETECTED: [^\]]+\] (.*)"
            contamination_match = re.search(contamination_pattern, received_value, re.DOTALL)
            
            if contamination_match:
                # Extract content after contamination warning
                clean_received_value = contamination_match.group(1)
                details[f"field_{i}_contamination_detected"] = True
            else:
                clean_received_value = received_value
                details[f"field_{i}_contamination_detected"] = False
            
            # Compare cleaned values
            if sent_value != clean_received_value:
                similarity = self._calculate_similarity(sent_value, clean_received_value)
                
                if similarity < 0.8:  # Less than 80% similar
                    mismatches.append({
                        "field": f"field[{i}].value",
                        "expected": sent_value[:100] + "..." if len(sent_value) > 100 else sent_value,
                        "actual": clean_received_value[:100] + "..." if len(clean_received_value) > 100 else clean_received_value,
                        "similarity_score": similarity
                    })
                else:
                    warnings.append(f"Field {i} value has minor differences (similarity: {similarity:.2f})")
        
        details["field_mismatches"] = mismatches
        
        # Add mismatch errors
        for mismatch in mismatches:
            errors.append(
                f"Field mismatch in {mismatch['field']}: "
                f"expected '{mismatch['expected']}', got '{mismatch['actual']}' "
                f"(similarity: {mismatch['similarity_score']:.2f})"
            )
        
        return {
            "success": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if text1 == text2:
            return 1.0
        
        if not text1 or not text2:
            return 0.0
        
        # Simple Levenshtein-based similarity
        # This is a basic implementation; could be enhanced with better algorithms
        longer = text1 if len(text1) > len(text2) else text2
        shorter = text2 if len(text1) > len(text2) else text1
        
        if len(longer) == 0:
            return 1.0
        
        # Calculate edit distance (simplified)
        edit_distance = self._levenshtein_distance(text1, text2)
        similarity = (len(longer) - edit_distance) / len(longer)
        
        return max(0.0, similarity)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Edit distance
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]