#!/usr/bin/env python3
"""API Response Validator.

This module provides comprehensive validation for API responses including:
- Discord API response structure validation
- Response time and performance validation
- Error response handling validation
- Rate limiting response validation
- Content validation and format checking
- Security validation for response data
"""

import asyncio
import json
import time
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone
from dataclasses import dataclass, field
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# API response validation types
@dataclass
class APIResponseValidationResult:
    """Result of API response validation."""
    response_id: str
    endpoint: str
    validation_type: str
    success: bool
    response_time: float
    status_code: Optional[int]
    validation_errors: List[str]
    validation_warnings: List[str]
    security_issues: List[str]
    performance_metrics: Dict[str, float]
    content_validation: Dict[str, bool]
    compliance_score: float  # 0-100


@dataclass
class APIEndpointSpec:
    """Specification for an API endpoint."""
    endpoint: str
    method: str
    required_fields: List[str]
    optional_fields: List[str]
    response_types: List[str]
    max_response_time: float
    rate_limit_info: Dict[str, Any]
    security_requirements: List[str]


class DiscordAPIValidator:
    """Validates Discord API responses according to Discord API specifications."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.endpoint_specs = self._load_discord_api_specs()
        
    def _load_discord_api_specs(self) -> Dict[str, APIEndpointSpec]:
        """Load Discord API endpoint specifications."""
        return {
            "webhook": APIEndpointSpec(
                endpoint="/api/webhooks/{webhook.id}/{webhook.token}",
                method="POST",
                required_fields=["id", "type", "timestamp"],
                optional_fields=["content", "embeds", "username", "avatar_url", "tts", "file", "flags"],
                response_types=["application/json"],
                max_response_time=5.0,
                rate_limit_info={
                    "limit": 5,
                    "window": 1.0,  # 1 second
                    "burst": 5
                },
                security_requirements=["webhook_token_validation", "rate_limiting"]
            ),
            "channel_message": APIEndpointSpec(
                endpoint="/api/channels/{channel.id}/messages",
                method="POST",
                required_fields=["id", "type", "timestamp", "channel_id", "author"],
                optional_fields=["content", "embeds", "attachments", "mention_roles", "mentions", "flags"],
                response_types=["application/json"],
                max_response_time=3.0,
                rate_limit_info={
                    "limit": 5,
                    "window": 5.0,  # 5 seconds
                    "burst": 5
                },
                security_requirements=["bot_token_validation", "permission_validation", "rate_limiting"]
            ),
            "thread_create": APIEndpointSpec(
                endpoint="/api/channels/{channel.id}/threads",
                method="POST",
                required_fields=["id", "name", "parent_id", "type", "message_count", "member_count"],
                optional_fields=["auto_archive_duration", "locked", "archived", "create_timestamp"],
                response_types=["application/json"],
                max_response_time=3.0,
                rate_limit_info={
                    "limit": 2,
                    "window": 60.0,  # 1 minute
                    "burst": 2
                },
                security_requirements=["bot_token_validation", "thread_permission_validation"]
            ),
            "thread_message": APIEndpointSpec(
                endpoint="/api/channels/{thread.id}/messages",
                method="POST",
                required_fields=["id", "type", "timestamp", "channel_id", "author"],
                optional_fields=["content", "embeds", "attachments", "thread_metadata"],
                response_types=["application/json"],
                max_response_time=3.0,
                rate_limit_info={
                    "limit": 5,
                    "window": 5.0,
                    "burst": 5
                },
                security_requirements=["bot_token_validation", "thread_access_validation"]
            )
        }
    
    def validate_response_structure(self, response: Dict[str, Any], endpoint_type: str) -> List[str]:
        """Validate response structure against API specification."""
        errors = []
        
        if endpoint_type not in self.endpoint_specs:
            errors.append(f"Unknown endpoint type: {endpoint_type}")
            return errors
            
        spec = self.endpoint_specs[endpoint_type]
        
        # Check required fields
        for field in spec.required_fields:
            if field not in response:
                errors.append(f"Missing required field: {field}")
            elif response[field] is None:
                errors.append(f"Required field is null: {field}")
        
        # Validate field types
        type_errors = self._validate_field_types(response, endpoint_type)
        errors.extend(type_errors)
        
        # Validate Discord-specific constraints
        constraint_errors = self._validate_discord_constraints(response, endpoint_type)
        errors.extend(constraint_errors)
        
        return errors
    
    def _validate_field_types(self, response: Dict[str, Any], endpoint_type: str) -> List[str]:
        """Validate field types according to Discord API."""
        errors = []
        
        # Common field type validations
        if "id" in response:
            if not isinstance(response["id"], str) or not response["id"].isdigit():
                errors.append("Field 'id' must be a snowflake (numeric string)")
        
        if "timestamp" in response:
            if not isinstance(response["timestamp"], str):
                errors.append("Field 'timestamp' must be an ISO8601 string")
            else:
                try:
                    datetime.fromisoformat(response["timestamp"].replace("Z", "+00:00"))
                except ValueError:
                    errors.append("Field 'timestamp' must be a valid ISO8601 timestamp")
        
        if "type" in response:
            if not isinstance(response["type"], int):
                errors.append("Field 'type' must be an integer")
        
        if "content" in response:
            if response["content"] is not None and not isinstance(response["content"], str):
                errors.append("Field 'content' must be a string or null")
            elif isinstance(response["content"], str) and len(response["content"]) > 2000:
                errors.append("Field 'content' exceeds Discord's 2000 character limit")
        
        if "embeds" in response:
            if not isinstance(response["embeds"], list):
                errors.append("Field 'embeds' must be an array")
            elif len(response["embeds"]) > 10:
                errors.append("Field 'embeds' exceeds Discord's 10 embed limit")
            else:
                for i, embed in enumerate(response["embeds"]):
                    embed_errors = self._validate_embed_structure(embed, i)
                    errors.extend(embed_errors)
        
        # Endpoint-specific validations
        if endpoint_type in ["channel_message", "thread_message"]:
            if "channel_id" in response:
                if not isinstance(response["channel_id"], str) or not response["channel_id"].isdigit():
                    errors.append("Field 'channel_id' must be a snowflake")
            
            if "author" in response:
                if not isinstance(response["author"], dict):
                    errors.append("Field 'author' must be an object")
                else:
                    author_errors = self._validate_author_structure(response["author"])
                    errors.extend(author_errors)
        
        elif endpoint_type == "thread_create":
            if "name" in response:
                if not isinstance(response["name"], str):
                    errors.append("Field 'name' must be a string")
                elif len(response["name"]) > 100:
                    errors.append("Field 'name' exceeds Discord's 100 character limit for thread names")
            
            if "parent_id" in response:
                if not isinstance(response["parent_id"], str) or not response["parent_id"].isdigit():
                    errors.append("Field 'parent_id' must be a snowflake")
        
        return errors
    
    def _validate_embed_structure(self, embed: Dict[str, Any], index: int) -> List[str]:
        """Validate Discord embed structure."""
        errors = []
        prefix = f"embeds[{index}]"
        
        if not isinstance(embed, dict):
            errors.append(f"{prefix} must be an object")
            return errors
        
        # Validate embed fields
        if "title" in embed:
            if not isinstance(embed["title"], str):
                errors.append(f"{prefix}.title must be a string")
            elif len(embed["title"]) > 256:
                errors.append(f"{prefix}.title exceeds 256 character limit")
        
        if "description" in embed:
            if not isinstance(embed["description"], str):
                errors.append(f"{prefix}.description must be a string")
            elif len(embed["description"]) > 4096:
                errors.append(f"{prefix}.description exceeds 4096 character limit")
        
        if "color" in embed:
            if not isinstance(embed["color"], int) or embed["color"] < 0 or embed["color"] > 0xFFFFFF:
                errors.append(f"{prefix}.color must be an integer between 0 and 16777215")
        
        if "fields" in embed:
            if not isinstance(embed["fields"], list):
                errors.append(f"{prefix}.fields must be an array")
            elif len(embed["fields"]) > 25:
                errors.append(f"{prefix}.fields exceeds 25 field limit")
            else:
                for i, field in enumerate(embed["fields"]):
                    field_errors = self._validate_embed_field(field, f"{prefix}.fields[{i}]")
                    errors.extend(field_errors)
        
        if "footer" in embed:
            footer_errors = self._validate_embed_footer(embed["footer"], f"{prefix}.footer")
            errors.extend(footer_errors)
        
        # Calculate total embed character count
        total_chars = 0
        total_chars += len(embed.get("title", ""))
        total_chars += len(embed.get("description", ""))
        if "fields" in embed:
            for field in embed["fields"]:
                total_chars += len(field.get("name", ""))
                total_chars += len(field.get("value", ""))
        if "footer" in embed:
            total_chars += len(embed["footer"].get("text", ""))
        if "author" in embed:
            total_chars += len(embed["author"].get("name", ""))
        
        if total_chars > 6000:
            errors.append(f"{prefix} total character count exceeds Discord's 6000 character limit")
        
        return errors
    
    def _validate_embed_field(self, field: Dict[str, Any], prefix: str) -> List[str]:
        """Validate Discord embed field structure."""
        errors = []
        
        if not isinstance(field, dict):
            errors.append(f"{prefix} must be an object")
            return errors
        
        if "name" not in field:
            errors.append(f"{prefix} missing required field 'name'")
        elif not isinstance(field["name"], str):
            errors.append(f"{prefix}.name must be a string")
        elif len(field["name"]) > 256:
            errors.append(f"{prefix}.name exceeds 256 character limit")
        
        if "value" not in field:
            errors.append(f"{prefix} missing required field 'value'")
        elif not isinstance(field["value"], str):
            errors.append(f"{prefix}.value must be a string")
        elif len(field["value"]) > 1024:
            errors.append(f"{prefix}.value exceeds 1024 character limit")
        
        if "inline" in field and not isinstance(field["inline"], bool):
            errors.append(f"{prefix}.inline must be a boolean")
        
        return errors
    
    def _validate_embed_footer(self, footer: Dict[str, Any], prefix: str) -> List[str]:
        """Validate Discord embed footer structure."""
        errors = []
        
        if not isinstance(footer, dict):
            errors.append(f"{prefix} must be an object")
            return errors
        
        if "text" in footer:
            if not isinstance(footer["text"], str):
                errors.append(f"{prefix}.text must be a string")
            elif len(footer["text"]) > 2048:
                errors.append(f"{prefix}.text exceeds 2048 character limit")
        
        if "icon_url" in footer:
            if not isinstance(footer["icon_url"], str):
                errors.append(f"{prefix}.icon_url must be a string")
            elif not self._is_valid_url(footer["icon_url"]):
                errors.append(f"{prefix}.icon_url must be a valid URL")
        
        return errors
    
    def _validate_author_structure(self, author: Dict[str, Any]) -> List[str]:
        """Validate Discord author structure."""
        errors = []
        
        if "id" in author:
            if not isinstance(author["id"], str) or not author["id"].isdigit():
                errors.append("author.id must be a snowflake")
        
        if "username" in author:
            if not isinstance(author["username"], str):
                errors.append("author.username must be a string")
            elif len(author["username"]) > 32:
                errors.append("author.username exceeds 32 character limit")
        
        if "discriminator" in author:
            if not isinstance(author["discriminator"], str):
                errors.append("author.discriminator must be a string")
            elif not re.match(r"^\d{4}$", author["discriminator"]):
                errors.append("author.discriminator must be a 4-digit string")
        
        return errors
    
    def _validate_discord_constraints(self, response: Dict[str, Any], endpoint_type: str) -> List[str]:
        """Validate Discord-specific business logic constraints."""
        errors = []
        
        # Webhook-specific constraints
        if endpoint_type == "webhook":
            if "content" not in response and "embeds" not in response:
                errors.append("Webhook message must have either content or embeds")
            
            if "content" in response and response["content"] == "":
                if "embeds" not in response or len(response["embeds"]) == 0:
                    errors.append("Message cannot be empty (no content and no embeds)")
        
        # Thread-specific constraints  
        elif endpoint_type == "thread_create":
            if "type" in response:
                valid_thread_types = [10, 11, 12]  # ANNOUNCEMENT_THREAD, PUBLIC_THREAD, PRIVATE_THREAD
                if response["type"] not in valid_thread_types:
                    errors.append(f"Invalid thread type: {response['type']}")
        
        # Message-specific constraints
        elif endpoint_type in ["channel_message", "thread_message"]:
            if "type" in response:
                valid_message_types = [0, 19, 20, 21]  # DEFAULT, REPLY, THREAD_STARTER_MESSAGE, etc.
                if response["type"] not in valid_message_types:
                    errors.append(f"Invalid message type: {response['type']}")
        
        return errors
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None


class APIResponseValidator(BaseQualityChecker):
    """Comprehensive API response validator."""
    
    def __init__(self):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.discord_validator = DiscordAPIValidator()
        self.validation_results = []
        
    async def validate_response(
        self, 
        response: Dict[str, Any], 
        endpoint_type: str,
        response_time: float,
        status_code: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None
    ) -> APIResponseValidationResult:
        """Validate a complete API response."""
        
        response_id = response.get("id", f"unknown_{int(time.time() * 1000)}")
        validation_errors = []
        validation_warnings = []
        security_issues = []
        performance_metrics = {}
        content_validation = {}
        
        # Structure validation
        try:
            structure_errors = self.discord_validator.validate_response_structure(response, endpoint_type)
            validation_errors.extend(structure_errors)
        except Exception as e:
            validation_errors.append(f"Structure validation failed: {str(e)}")
        
        # Performance validation
        performance_metrics = await self._validate_performance(response_time, endpoint_type)
        if response_time > self.discord_validator.endpoint_specs.get(endpoint_type, APIEndpointSpec("", "", [], [], [], 5.0, {}, [])).max_response_time:
            validation_warnings.append(f"Response time {response_time:.2f}s exceeds recommended maximum")
        
        # Content validation
        content_validation = await self._validate_content(response, endpoint_type)
        
        # Security validation
        security_issues = await self._validate_security(response, endpoint_type, request_data)
        
        # Rate limiting validation
        rate_limit_issues = await self._validate_rate_limiting(response, endpoint_type)
        if rate_limit_issues:
            validation_warnings.extend(rate_limit_issues)
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(
            validation_errors, validation_warnings, security_issues, performance_metrics, content_validation
        )
        
        result = APIResponseValidationResult(
            response_id=response_id,
            endpoint=endpoint_type,
            validation_type="comprehensive",
            success=len(validation_errors) == 0 and len(security_issues) == 0,
            response_time=response_time,
            status_code=status_code,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            security_issues=security_issues,
            performance_metrics=performance_metrics,
            content_validation=content_validation,
            compliance_score=compliance_score
        )
        
        self.validation_results.append(result)
        return result
    
    async def _validate_performance(self, response_time: float, endpoint_type: str) -> Dict[str, float]:
        """Validate response performance metrics."""
        metrics = {
            "response_time": response_time,
            "performance_score": 100.0
        }
        
        # Get endpoint specification
        spec = self.discord_validator.endpoint_specs.get(endpoint_type)
        if not spec:
            return metrics
        
        # Calculate performance score based on response time
        max_time = spec.max_response_time
        if response_time <= max_time * 0.5:
            metrics["performance_score"] = 100.0
        elif response_time <= max_time:
            metrics["performance_score"] = 100.0 - ((response_time - max_time * 0.5) / (max_time * 0.5)) * 50.0
        else:
            metrics["performance_score"] = max(0.0, 50.0 - ((response_time - max_time) / max_time) * 50.0)
        
        # Performance classification
        if response_time < 0.5:
            metrics["performance_class"] = "excellent"
        elif response_time < 1.0:
            metrics["performance_class"] = "good"
        elif response_time < 2.0:
            metrics["performance_class"] = "acceptable"
        elif response_time < 5.0:
            metrics["performance_class"] = "slow"
        else:
            metrics["performance_class"] = "very_slow"
        
        return metrics
    
    async def _validate_content(self, response: Dict[str, Any], endpoint_type: str) -> Dict[str, bool]:
        """Validate response content quality and completeness."""
        validation = {
            "has_required_content": True,
            "content_quality_good": True,
            "encoding_valid": True,
            "format_compliant": True
        }
        
        # Check content presence and quality
        if "content" in response and response["content"]:
            content = response["content"]
            
            # Check for control characters
            if any(ord(char) < 32 and char not in ['\n', '\r', '\t'] for char in content):
                validation["content_quality_good"] = False
            
            # Check encoding
            try:
                content.encode('utf-8')
            except UnicodeEncodeError:
                validation["encoding_valid"] = False
        
        # Check embeds content
        if "embeds" in response:
            for embed in response["embeds"]:
                if isinstance(embed, dict):
                    # Check embed text content quality
                    for field in ["title", "description"]:
                        if field in embed and embed[field]:
                            text = embed[field]
                            if any(ord(char) < 32 and char not in ['\n', '\r', '\t'] for char in text):
                                validation["content_quality_good"] = False
                    
                    # Check embed fields
                    if "fields" in embed:
                        for field in embed["fields"]:
                            if isinstance(field, dict):
                                for key in ["name", "value"]:
                                    if key in field and field[key]:
                                        text = field[key]
                                        if any(ord(char) < 32 and char not in ['\n', '\r', '\t'] for char in text):
                                            validation["content_quality_good"] = False
        
        # Check required content based on endpoint type
        if endpoint_type == "webhook":
            has_content = "content" in response and response["content"]
            has_embeds = "embeds" in response and len(response["embeds"]) > 0
            validation["has_required_content"] = has_content or has_embeds
        
        # Check format compliance
        required_fields = self.discord_validator.endpoint_specs.get(endpoint_type, APIEndpointSpec("", "", [], [], [], 5.0, {}, [])).required_fields
        for field in required_fields:
            if field not in response:
                validation["format_compliant"] = False
                break
        
        return validation
    
    async def _validate_security(
        self, 
        response: Dict[str, Any], 
        endpoint_type: str, 
        request_data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Validate security aspects of the response."""
        issues = []
        
        # Check for potential data leakage
        sensitive_patterns = [
            r'[A-Za-z0-9]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}',  # Discord bot token pattern
            r'https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+',  # Webhook URL pattern
            r'[A-Za-z0-9+/]{40,}={0,2}',  # Base64 pattern (potential secrets)
            r'-----BEGIN [A-Z ]+-----',  # PEM format
        ]
        
        # Check response content for sensitive data
        response_str = json.dumps(response)
        for pattern in sensitive_patterns:
            if re.search(pattern, response_str):
                issues.append(f"Potential sensitive data detected in response")
                break
        
        # Check for excessive information disclosure
        if "author" in response and isinstance(response["author"], dict):
            author = response["author"]
            # Check if unnecessary user information is exposed
            sensitive_user_fields = ["email", "phone", "mfa_enabled", "premium_type"]
            for field in sensitive_user_fields:
                if field in author:
                    issues.append(f"Potentially sensitive user information exposed: {field}")
        
        # Validate response doesn't contain request artifacts
        if request_data:
            # Check if tokens or sensitive request data leaked into response
            if "token" in request_data:
                if request_data["token"] in response_str:
                    issues.append("Authentication token leaked in response")
        
        # Check for XSS potential in content
        if "content" in response and response["content"]:
            xss_patterns = [
                r'<script[^>]*>',
                r'javascript:',
                r'on\w+\s*=',
                r'<iframe[^>]*>',
                r'<object[^>]*>',
                r'<embed[^>]*>'
            ]
            content = response["content"]
            for pattern in xss_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append("Potential XSS payload detected in content")
                    break
        
        # Check embeds for security issues
        if "embeds" in response:
            for i, embed in enumerate(response["embeds"]):
                if isinstance(embed, dict):
                    # Check URLs in embeds
                    for url_field in ["url", "image", "thumbnail", "video"]:
                        if url_field in embed:
                            url_obj = embed[url_field]
                            if isinstance(url_obj, dict) and "url" in url_obj:
                                url = url_obj["url"]
                            elif isinstance(url_obj, str):
                                url = url_obj
                            else:
                                continue
                            
                            # Check for suspicious URLs
                            if not url.startswith(("https://", "http://")):
                                issues.append(f"Non-HTTP(S) URL in embed[{i}].{url_field}")
                            elif re.search(r'[<>"\'\s]', url):
                                issues.append(f"Potentially malicious characters in embed[{i}].{url_field} URL")
        
        return issues
    
    async def _validate_rate_limiting(self, response: Dict[str, Any], endpoint_type: str) -> List[str]:
        """Validate rate limiting aspects of the response."""
        warnings = []
        
        # Check if response indicates rate limiting
        if "retry_after" in response:
            warnings.append(f"Rate limited response with retry_after: {response['retry_after']}")
        
        # Check for rate limit headers (if available in response)
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining", 
            "x-ratelimit-reset",
            "x-ratelimit-reset-after",
            "x-ratelimit-bucket"
        ]
        
        for header in rate_limit_headers:
            if header in response:
                # Log rate limit information
                self.logger.debug(f"Rate limit header {header}: {response[header]}")
        
        # Check remaining rate limit
        if "x-ratelimit-remaining" in response:
            remaining = response["x-ratelimit-remaining"]
            if isinstance(remaining, (int, str)) and int(remaining) < 2:
                warnings.append(f"Low rate limit remaining: {remaining}")
        
        return warnings
    
    def _calculate_compliance_score(
        self,
        validation_errors: List[str],
        validation_warnings: List[str], 
        security_issues: List[str],
        performance_metrics: Dict[str, float],
        content_validation: Dict[str, bool]
    ) -> float:
        """Calculate overall compliance score (0-100)."""
        
        base_score = 100.0
        
        # Deduct for validation errors (critical)
        base_score -= len(validation_errors) * 20.0
        
        # Deduct for security issues (critical)
        base_score -= len(security_issues) * 25.0
        
        # Deduct for warnings (moderate)
        base_score -= len(validation_warnings) * 5.0
        
        # Adjust for performance
        performance_score = performance_metrics.get("performance_score", 100.0)
        base_score = base_score * (performance_score / 100.0)
        
        # Adjust for content quality
        content_issues = sum(1 for valid in content_validation.values() if not valid)
        base_score -= content_issues * 10.0
        
        return max(0.0, min(100.0, base_score))
    
    async def validate_error_response(
        self, 
        response: Dict[str, Any], 
        expected_status: int,
        response_time: float
    ) -> APIResponseValidationResult:
        """Validate error response structure and content."""
        
        response_id = f"error_{int(time.time() * 1000)}"
        validation_errors = []
        validation_warnings = []
        
        # Check error response structure
        if "code" not in response:
            validation_errors.append("Error response missing 'code' field")
        elif not isinstance(response["code"], int):
            validation_errors.append("Error response 'code' must be an integer")
        
        if "message" not in response:
            validation_errors.append("Error response missing 'message' field")
        elif not isinstance(response["message"], str):
            validation_errors.append("Error response 'message' must be a string")
        elif len(response["message"]) == 0:
            validation_errors.append("Error response 'message' cannot be empty")
        
        # Validate error codes
        if "code" in response:
            code = response["code"]
            known_discord_errors = {
                10001: "Unknown account",
                10003: "Unknown channel",
                10004: "Unknown guild",
                10008: "Unknown message",
                10013: "Unknown user",
                50001: "Missing access",
                50013: "Missing permissions",
                50035: "Invalid form body"
            }
            
            if code in known_discord_errors:
                expected_message = known_discord_errors[code]
                if expected_message.lower() not in response.get("message", "").lower():
                    validation_warnings.append(f"Error message doesn't match expected pattern for code {code}")
        
        # Check response time for errors (should be fast)
        performance_metrics = {"response_time": response_time}
        if response_time > 2.0:
            validation_warnings.append("Error response took too long")
        
        return APIResponseValidationResult(
            response_id=response_id,
            endpoint="error_response",
            validation_type="error_validation",
            success=len(validation_errors) == 0,
            response_time=response_time,
            status_code=expected_status,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            security_issues=[],
            performance_metrics=performance_metrics,
            content_validation={"has_error_info": "code" in response and "message" in response},
            compliance_score=100.0 - len(validation_errors) * 20.0 - len(validation_warnings) * 5.0
        )
    
    async def validate_batch_responses(
        self, 
        responses: List[Tuple[Dict[str, Any], str, float]]
    ) -> Dict[str, Any]:
        """Validate a batch of API responses."""
        
        batch_results = []
        
        for response, endpoint_type, response_time in responses:
            result = await self.validate_response(response, endpoint_type, response_time)
            batch_results.append(result)
        
        # Calculate batch statistics
        total_responses = len(batch_results)
        successful_responses = sum(1 for r in batch_results if r.success)
        average_compliance = sum(r.compliance_score for r in batch_results) / total_responses if total_responses > 0 else 0
        average_response_time = sum(r.response_time for r in batch_results) / total_responses if total_responses > 0 else 0
        
        total_errors = sum(len(r.validation_errors) for r in batch_results)
        total_warnings = sum(len(r.validation_warnings) for r in batch_results)
        total_security_issues = sum(len(r.security_issues) for r in batch_results)
        
        return {
            "batch_summary": {
                "total_responses": total_responses,
                "successful_responses": successful_responses,
                "success_rate": successful_responses / total_responses if total_responses > 0 else 0,
                "average_compliance_score": average_compliance,
                "average_response_time": average_response_time,
                "total_validation_errors": total_errors,
                "total_validation_warnings": total_warnings,
                "total_security_issues": total_security_issues
            },
            "individual_results": batch_results,
            "quality_assessment": self._assess_batch_quality(batch_results)
        }
    
    def _assess_batch_quality(self, results: List[APIResponseValidationResult]) -> str:
        """Assess overall quality of a batch of responses."""
        
        if not results:
            return "no_data"
        
        success_rate = sum(1 for r in results if r.success) / len(results)
        avg_compliance = sum(r.compliance_score for r in results) / len(results)
        
        if success_rate >= 0.95 and avg_compliance >= 90:
            return "excellent"
        elif success_rate >= 0.90 and avg_compliance >= 80:
            return "good"
        elif success_rate >= 0.80 and avg_compliance >= 70:
            return "acceptable"
        elif success_rate >= 0.60 and avg_compliance >= 50:
            return "poor"
        else:
            return "critical"
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check overall quality of API response validation."""
        
        if not self.validation_results:
            return {
                "quality_level": "unknown",
                "message": "No validation results available"
            }
        
        total_validations = len(self.validation_results)
        successful_validations = sum(1 for r in self.validation_results if r.success)
        average_compliance = sum(r.compliance_score for r in self.validation_results) / total_validations
        
        # Group by endpoint type
        endpoint_stats = {}
        for result in self.validation_results:
            endpoint = result.endpoint
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "total": 0,
                    "successful": 0,
                    "avg_compliance": 0,
                    "avg_response_time": 0
                }
            
            stats = endpoint_stats[endpoint]
            stats["total"] += 1
            if result.success:
                stats["successful"] += 1
            stats["avg_compliance"] += result.compliance_score
            stats["avg_response_time"] += result.response_time
        
        # Calculate averages
        for endpoint, stats in endpoint_stats.items():
            if stats["total"] > 0:
                stats["avg_compliance"] /= stats["total"]
                stats["avg_response_time"] /= stats["total"]
                stats["success_rate"] = stats["successful"] / stats["total"]
        
        # Determine overall quality level
        success_rate = successful_validations / total_validations
        if success_rate >= 0.95 and average_compliance >= 90:
            quality_level = "excellent"
        elif success_rate >= 0.90 and average_compliance >= 80:
            quality_level = "good"
        elif success_rate >= 0.80 and average_compliance >= 70:
            quality_level = "acceptable"
        else:
            quality_level = "needs_improvement"
        
        return {
            "quality_level": quality_level,
            "total_validations": total_validations,
            "success_rate": success_rate,
            "average_compliance_score": average_compliance,
            "endpoint_statistics": endpoint_stats,
            "validation_summary": {
                "successful_validations": successful_validations,
                "failed_validations": total_validations - successful_validations,
                "total_errors": sum(len(r.validation_errors) for r in self.validation_results),
                "total_warnings": sum(len(r.validation_warnings) for r in self.validation_results),
                "total_security_issues": sum(len(r.security_issues) for r in self.validation_results)
            }
        }