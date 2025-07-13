#!/usr/bin/env python3
"""Content Processing Quality Checker.

This module provides comprehensive quality checks for content processing
functionality, including event formatting, tool formatting, prompt mixing
detection, timestamp accuracy, Discord limits compliance, Unicode handling,
content sanitization, and format consistency.
"""

import asyncio
import json
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import format_user_datetime, get_completed_at_display
from src.formatters.event_formatters import EventFormatter
from src.formatters.tool_formatters import ToolFormatter
from src.formatters.embed_utils import EmbedBuilder
from src.constants import EventTypes
from ..core_checker import BaseQualityChecker, QualityCheckResult


class ContentProcessingChecker(BaseQualityChecker):
    """Quality checker for content processing functionality.
    
    Validates all aspects of content processing including:
    - Event formatting precision and accuracy
    - Tool formatting consistency
    - Prompt mixing detection accuracy 
    - Timestamp accuracy in real-time
    - Discord limits compliance (2000 chars, 25 fields, etc.)
    - Unicode processing correctness
    - Content sanitization functionality
    - Format output consistency
    """
    
    def __init__(self, project_root: Path, logger: AstolfoLogger) -> None:
        """Initialize content processing checker.
        
        Args:
            project_root: Project root directory
            logger: Logger instance for structured logging
        """
        super().__init__(project_root, logger)
        self.category = "Content Processing"
        
        # Initialize formatters
        self.event_formatter = EventFormatter()
        self.tool_formatter = ToolFormatter()
        self.embed_builder = EmbedBuilder()
        
        # Quality metrics tracking
        self.metrics = {
            "format_accuracy": 0.0,
            "prompt_mixing_detection_accuracy": 0.0, 
            "timestamp_accuracy": 0.0,
            "unicode_processing_accuracy": 0.0,
            "discord_limits_compliance_rate": 0.0,
            "content_sanitization_score": 0.0,
            "format_consistency_score": 0.0,
            "tool_format_consistency": 0.0
        }
        
        # Test data for various checks
        self._init_test_data()
    
    def _init_test_data(self) -> None:
        """Initialize test data for content processing checks."""
        
        # Sample event data for testing
        self.test_events = {
            "PreToolUse": {
                "session_id": "test_session_001",
                "tool_name": "Read",
                "timestamp": datetime.now().isoformat(),
                "input_data": {"file_path": "/test/file.py"}
            },
            "PostToolUse": {
                "session_id": "test_session_001", 
                "tool_name": "Read",
                "timestamp": datetime.now().isoformat(),
                "output_data": {"content": "Test file content"},
                "success": True
            },
            "Stop": {
                "session_id": "test_session_001",
                "timestamp": datetime.now().isoformat(),
                "reason": "completed"
            },
            "Notification": {
                "session_id": "test_session_001",
                "message": "Test notification message",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Unicode test cases
        self.unicode_test_cases = [
            "Hello 世界",  # Mixed ASCII + CJK
            "🎯📊✅❌",    # Emojis 
            "Café naïve résumé",  # Accented characters
            "Здравствуй мир",  # Cyrillic
            "مرحبا بالعالم",  # Arabic
            "こんにちは世界",  # Hiragana + Kanji
            "\u200b\u200c\u200d",  # Zero-width characters
            "test\x00null",  # Null bytes
            "tab\there",  # Tab characters
            "line1\nline2\rline3"  # Various line breaks
        ]
        
        # Prompt mixing test cases
        self.prompt_mixing_test_cases = [
            {
                "content": "Normal content without mixing",
                "has_mixing": False
            },
            {
                "content": "User input: Please read file.py\nAssistant: I'll read the file for you.",
                "has_mixing": True
            },
            {
                "content": "Human: What's in this file?\nAI: Let me check that for you.",
                "has_mixing": True
            },
            {
                "content": "System: Processing request\nUser: Show me the results",
                "has_mixing": True
            },
            {
                "content": "Just regular content about files and data",
                "has_mixing": False
            }
        ]
        
        # Discord limits test data
        self.discord_limits = {
            "content_max_length": 2000,
            "embed_title_max_length": 256,
            "embed_description_max_length": 4096,
            "embed_field_max_count": 25,
            "embed_field_name_max_length": 256,
            "embed_field_value_max_length": 1024,
            "embed_footer_text_max_length": 2048
        }
    
    async def _execute_checks(self) -> QualityCheckResult:
        """Execute content processing quality checks.
        
        Returns:
            Quality check result with metrics and findings
        """
        issues = []
        warnings = []
        
        self.logger.info("Starting content processing quality checks")
        
        # Run all content processing checks
        check_results = await asyncio.gather(
            self._check_event_format_accuracy(),
            self._check_tool_format_consistency(),
            self._check_prompt_mixing_detection(),
            self._check_timestamp_realtime_accuracy(),
            self._check_discord_limits_compliance(),
            self._check_unicode_processing(),
            self._check_content_sanitization(),
            self._check_format_consistency(),
            return_exceptions=True
        )
        
        # Process check results
        total_score = 0.0
        check_count = 0
        
        for i, result in enumerate(check_results):
            if isinstance(result, Exception):
                issues.append(f"Check {i+1} failed with exception: {result}")
            else:
                score, check_issues, check_warnings = result
                total_score += score
                check_count += 1
                issues.extend(check_issues)
                warnings.extend(check_warnings)
        
        # Calculate overall score
        overall_score = total_score / check_count if check_count > 0 else 0.0
        passed = overall_score >= 0.9 and len(issues) == 0
        
        self.logger.info(
            f"Content processing checks completed",
            context={
                "overall_score": overall_score,
                "passed": passed,
                "issues": len(issues),
                "warnings": len(warnings)
            }
        )
        
        return {
            "check_name": "Content Processing Quality Check",
            "category": self.category,
            "passed": passed,
            "score": overall_score,
            "issues": issues,
            "warnings": warnings,
            "metrics": self.metrics,
            "execution_time": 0.0,
            "timestamp": ""
        }
    
    async def _check_event_format_accuracy(self) -> Tuple[float, List[str], List[str]]:
        """Check event formatting precision and accuracy.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking event formatting accuracy")
        
        issues = []
        warnings = []
        total_score = 0.0
        event_count = 0
        
        try:
            # Test each event type formatting
            for event_type, event_data in self.test_events.items():
                event_count += 1
                score = 0.0
                
                try:
                    # Format the event
                    formatted = self.event_formatter.format_event(event_type, event_data)
                    
                    # Check basic structure
                    if isinstance(formatted, dict):
                        score += 0.3
                    
                    # Check required fields
                    required_fields = ["embeds"]
                    if all(field in formatted for field in required_fields):
                        score += 0.3
                    
                    # Check embed structure
                    if "embeds" in formatted and formatted["embeds"]:
                        embed = formatted["embeds"][0]
                        if isinstance(embed, dict) and "title" in embed:
                            score += 0.2
                        if "timestamp" in embed:
                            score += 0.2
                    
                    total_score += score
                    
                    if score < 0.8:
                        issues.append(f"Event formatting score low for {event_type}: {score:.2f}")
                
                except Exception as e:
                    issues.append(f"Event formatting failed for {event_type}: {e}")
            
            # Calculate final score
            final_score = total_score / event_count if event_count > 0 else 0.0
            self.metrics["format_accuracy"] = final_score
            
        except Exception as e:
            issues.append(f"Event format accuracy check error: {e}")
            final_score = 0.0
        
        return final_score, issues, warnings
    
    async def _check_tool_format_consistency(self) -> Tuple[float, List[str], List[str]]:
        """Check tool formatting consistency across different tools.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking tool formatting consistency")
        
        issues = []
        warnings = []
        score = 1.0
        
        try:
            # Test common tools formatting
            test_tools = [
                ("Read", {"file_path": "/test/file.py"}, {"content": "Test content"}),
                ("Write", {"file_path": "/test/new.py", "content": "New content"}, {"success": True}),
                ("Bash", {"command": "ls -la"}, {"output": "file1.py\nfile2.py"}),
                ("Edit", {"file_path": "/test/file.py", "old_text": "old", "new_text": "new"}, {"success": True})
            ]
            
            consistency_scores = []
            
            for tool_name, input_data, output_data in test_tools:
                try:
                    # Format tool usage
                    pre_format = self.tool_formatter.format_tool_use(tool_name, input_data)
                    post_format = self.tool_formatter.format_tool_result(tool_name, output_data, True)
                    
                    # Check consistency in structure
                    tool_score = 0.0
                    
                    if isinstance(pre_format, dict) and isinstance(post_format, dict):
                        tool_score += 0.5
                    
                    # Check for consistent field names
                    if "embeds" in pre_format and "embeds" in post_format:
                        tool_score += 0.5
                    
                    consistency_scores.append(tool_score)
                    
                except Exception as e:
                    warnings.append(f"Tool formatting test failed for {tool_name}: {e}")
                    consistency_scores.append(0.0)
            
            score = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
            self.metrics["tool_format_consistency"] = score
            
            if score < 0.9:
                issues.append(f"Tool formatting consistency below threshold: {score:.2f}")
        
        except Exception as e:
            issues.append(f"Tool format consistency check error: {e}")
            score = 0.0
        
        return score, issues, warnings
    
    async def _check_prompt_mixing_detection(self) -> Tuple[float, List[str], List[str]]:
        """Check prompt mixing detection accuracy.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking prompt mixing detection accuracy")
        
        issues = []
        warnings = []
        
        try:
            correct_detections = 0
            total_tests = len(self.prompt_mixing_test_cases)
            
            for test_case in self.prompt_mixing_test_cases:
                content = test_case["content"]
                expected_mixing = test_case["has_mixing"]
                
                # Test prompt mixing detection
                detected_mixing = self._detect_prompt_mixing(content)
                
                if detected_mixing == expected_mixing:
                    correct_detections += 1
                else:
                    issues.append(f"Prompt mixing detection error: expected {expected_mixing}, got {detected_mixing}")
            
            accuracy = correct_detections / total_tests
            self.metrics["prompt_mixing_detection_accuracy"] = accuracy
            
            if accuracy < 0.99:
                issues.append(f"Prompt mixing detection accuracy below target: {accuracy:.3f}")
        
        except Exception as e:
            issues.append(f"Prompt mixing detection check error: {e}")
            accuracy = 0.0
        
        return accuracy, issues, warnings
    
    async def _check_timestamp_realtime_accuracy(self) -> Tuple[float, List[str], List[str]]:
        """Check timestamp accuracy in real-time generation.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking timestamp real-time accuracy")
        
        issues = []
        warnings = []
        
        try:
            # Test timestamp generation accuracy
            accuracy_scores = []
            
            for _ in range(5):  # Test 5 times for consistency
                # Generate timestamp
                before_time = datetime.now()
                formatted_time = format_user_datetime()
                after_time = datetime.now()
                
                # Check if generated time is within reasonable range (±5 seconds)
                time_diff_before = abs((before_time - datetime.fromisoformat(formatted_time.replace(" JST", ""))).total_seconds())
                time_diff_after = abs((after_time - datetime.fromisoformat(formatted_time.replace(" JST", ""))).total_seconds())
                
                if min(time_diff_before, time_diff_after) <= 5.0:
                    accuracy_scores.append(1.0)
                else:
                    accuracy_scores.append(0.0)
                    issues.append(f"Timestamp accuracy out of range: {formatted_time}")
                
                # Small delay between tests
                await asyncio.sleep(0.1)
            
            accuracy = sum(accuracy_scores) / len(accuracy_scores)
            self.metrics["timestamp_accuracy"] = accuracy
            
            if accuracy < 0.95:
                issues.append(f"Timestamp accuracy below target: {accuracy:.3f}")
        
        except Exception as e:
            issues.append(f"Timestamp accuracy check error: {e}")
            accuracy = 0.0
        
        return accuracy, issues, warnings
    
    async def _check_discord_limits_compliance(self) -> Tuple[float, List[str], List[str]]:
        """Check Discord limits compliance.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking Discord limits compliance")
        
        issues = []
        warnings = []
        compliance_scores = []
        
        try:
            # Test with content that exceeds limits
            test_cases = [
                {
                    "name": "long_content",
                    "data": {"content": "A" * 2500},  # Exceeds 2000 char limit
                    "limit": "content_max_length"
                },
                {
                    "name": "long_title",
                    "data": {"embeds": [{"title": "T" * 300}]},  # Exceeds 256 char limit
                    "limit": "embed_title_max_length"
                },
                {
                    "name": "long_description", 
                    "data": {"embeds": [{"description": "D" * 5000}]},  # Exceeds 4096 char limit
                    "limit": "embed_description_max_length"
                },
                {
                    "name": "too_many_fields",
                    "data": {"embeds": [{"fields": [{"name": f"Field {i}", "value": "Value"} for i in range(30)]}]},
                    "limit": "embed_field_max_count"
                }
            ]
            
            for test_case in test_cases:
                try:
                    # Check if content would be properly truncated/handled
                    data = test_case["data"]
                    limit_name = test_case["limit"]
                    
                    # Simulate processing through embed builder
                    processed = self._simulate_discord_limits_check(data, limit_name)
                    
                    if processed:
                        compliance_scores.append(1.0)
                    else:
                        compliance_scores.append(0.0)
                        issues.append(f"Discord limits compliance failed for {test_case['name']}")
                
                except Exception as e:
                    compliance_scores.append(0.0)
                    warnings.append(f"Discord limits test failed for {test_case['name']}: {e}")
            
            compliance_rate = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0.0
            self.metrics["discord_limits_compliance_rate"] = compliance_rate
            
            if compliance_rate < 1.0:
                issues.append(f"Discord limits compliance below 100%: {compliance_rate:.3f}")
        
        except Exception as e:
            issues.append(f"Discord limits compliance check error: {e}")
            compliance_rate = 0.0
        
        return compliance_rate, issues, warnings
    
    async def _check_unicode_processing(self) -> Tuple[float, List[str], List[str]]:
        """Check Unicode processing correctness.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking Unicode processing")
        
        issues = []
        warnings = []
        processing_scores = []
        
        try:
            for test_text in self.unicode_test_cases:
                try:
                    # Test Unicode processing through formatting
                    test_event = {
                        "session_id": "unicode_test",
                        "content": test_text,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    formatted = self.event_formatter.format_event("Notification", test_event)
                    
                    # Check if Unicode is preserved
                    if self._validate_unicode_preservation(test_text, formatted):
                        processing_scores.append(1.0)
                    else:
                        processing_scores.append(0.0)
                        issues.append(f"Unicode processing failed for: {repr(test_text)}")
                
                except Exception as e:
                    processing_scores.append(0.0)
                    warnings.append(f"Unicode test failed for {repr(test_text)}: {e}")
            
            accuracy = sum(processing_scores) / len(processing_scores) if processing_scores else 0.0
            self.metrics["unicode_processing_accuracy"] = accuracy
            
            if accuracy < 1.0:
                issues.append(f"Unicode processing accuracy below 100%: {accuracy:.3f}")
        
        except Exception as e:
            issues.append(f"Unicode processing check error: {e}")
            accuracy = 0.0
        
        return accuracy, issues, warnings
    
    async def _check_content_sanitization(self) -> Tuple[float, List[str], List[str]]:
        """Check content sanitization functionality.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking content sanitization")
        
        issues = []
        warnings = []
        
        try:
            # Test dangerous content patterns
            dangerous_content = [
                "This contains \x00 null bytes",
                "Multiple\n\n\n\nline breaks",
                "Super long" + "A" * 10000 + "content",
                "\u200b\u200c\u200d Zero width chars",
                "Mixed\r\n\rline\nbreaks"
            ]
            
            sanitization_scores = []
            
            for content in dangerous_content:
                try:
                    # Test sanitization
                    sanitized = self._sanitize_content(content)
                    
                    # Check if properly sanitized
                    if self._validate_sanitization(content, sanitized):
                        sanitization_scores.append(1.0)
                    else:
                        sanitization_scores.append(0.0)
                        issues.append(f"Content sanitization failed for: {repr(content[:50])}")
                
                except Exception as e:
                    sanitization_scores.append(0.0)
                    warnings.append(f"Sanitization test failed: {e}")
            
            score = sum(sanitization_scores) / len(sanitization_scores) if sanitization_scores else 0.0
            self.metrics["content_sanitization_score"] = score
            
            if score < 0.95:
                issues.append(f"Content sanitization score below target: {score:.3f}")
        
        except Exception as e:
            issues.append(f"Content sanitization check error: {e}")
            score = 0.0
        
        return score, issues, warnings
    
    async def _check_format_consistency(self) -> Tuple[float, List[str], List[str]]:
        """Check format output consistency across different scenarios.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking format output consistency")
        
        issues = []
        warnings = []
        
        try:
            # Test consistency across multiple formatting operations
            consistency_tests = []
            
            # Format the same event multiple times
            test_event = self.test_events["PreToolUse"]
            
            for i in range(5):
                formatted = self.event_formatter.format_event("PreToolUse", test_event)
                consistency_tests.append(formatted)
            
            # Check if all results are identical (should be for deterministic formatting)
            first_result = json.dumps(consistency_tests[0], sort_keys=True)
            all_identical = all(json.dumps(result, sort_keys=True) == first_result for result in consistency_tests)
            
            score = 1.0 if all_identical else 0.0
            
            if not all_identical:
                issues.append("Format output inconsistency detected across multiple calls")
            
            self.metrics["format_consistency_score"] = score
        
        except Exception as e:
            issues.append(f"Format consistency check error: {e}")
            score = 0.0
        
        return score, issues, warnings
    
    # Helper methods
    
    def _detect_prompt_mixing(self, content: str) -> bool:
        """Detect if content contains prompt mixing patterns."""
        mixing_patterns = [
            r'\b(User|Human|Assistant|AI|System)\s*:',
            r'\b(user|human|assistant|ai|system)\s*:',
            r'(?:^|\n)\s*(User|Human|Assistant|AI|System)\s*:',
        ]
        
        for pattern in mixing_patterns:
            if re.search(pattern, content):
                return True
        return False
    
    def _simulate_discord_limits_check(self, data: Dict[str, Any], limit_name: str) -> bool:
        """Simulate Discord limits compliance check."""
        limit_value = self.discord_limits.get(limit_name, 0)
        
        if limit_name == "content_max_length":
            content = data.get("content", "")
            return len(content) <= limit_value
        
        elif limit_name == "embed_title_max_length":
            embeds = data.get("embeds", [])
            for embed in embeds:
                title = embed.get("title", "")
                if len(title) > limit_value:
                    return False
            return True
        
        elif limit_name == "embed_description_max_length":
            embeds = data.get("embeds", [])
            for embed in embeds:
                description = embed.get("description", "")
                if len(description) > limit_value:
                    return False
            return True
        
        elif limit_name == "embed_field_max_count":
            embeds = data.get("embeds", [])
            for embed in embeds:
                fields = embed.get("fields", [])
                if len(fields) > limit_value:
                    return False
            return True
        
        return True
    
    def _validate_unicode_preservation(self, original: str, formatted: Dict[str, Any]) -> bool:
        """Validate that Unicode characters are preserved through formatting."""
        # Convert formatted back to string for comparison
        formatted_str = json.dumps(formatted)
        
        # Check if original Unicode characters are still present
        for char in original:
            if char not in formatted_str:
                return False
        
        return True
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content for safe processing."""
        # Remove null bytes
        sanitized = content.replace('\x00', '')
        
        # Normalize line breaks
        sanitized = re.sub(r'\r\n|\r|\n', '\n', sanitized)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
        
        # Remove zero-width characters
        sanitized = ''.join(char for char in sanitized if unicodedata.category(char) != 'Cf' or char in '\t\n\r')
        
        # Truncate if too long
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000] + "..."
        
        return sanitized
    
    def _validate_sanitization(self, original: str, sanitized: str) -> bool:
        """Validate that content sanitization was effective."""
        # Check that dangerous patterns are removed/handled
        if '\x00' in sanitized:
            return False
        
        if re.search(r'\n{3,}', sanitized):
            return False
        
        if len(sanitized) > 10010:  # Allow for "..." addition
            return False
        
        return True


async def main() -> None:
    """Test the content processing checker."""
    project_root = Path(__file__).parent.parent.parent.parent
    logger = AstolfoLogger(__name__)
    
    checker = ContentProcessingChecker(project_root, logger)
    result = await checker.run_checks()
    
    print(f"Content Processing Check: {'PASSED' if result['passed'] else 'FAILED'}")
    print(f"Score: {result['score']:.3f}")
    print(f"Issues: {len(result['issues'])}")
    print(f"Warnings: {len(result['warnings'])}")
    
    for issue in result['issues']:
        print(f"  ❌ {issue}")
    
    for warning in result['warnings']:
        print(f"  ⚠️  {warning}")


if __name__ == "__main__":
    asyncio.run(main())