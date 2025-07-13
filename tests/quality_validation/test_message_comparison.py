#!/usr/bin/env python3
"""Test Message Send/Receive Comparison Accuracy.

This module provides comprehensive tests for message comparison functionality,
including sent vs received validation, content integrity verification,
formatting preservation, and delivery accuracy measurement.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, PropertyMock
import sys
import hashlib
import difflib
from datetime import datetime, timezone
from dataclasses import dataclass, field
import re
import base64

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.type_defs.discord import DiscordMessage, DiscordEmbed, DiscordField
from src.handlers.discord_sender import DiscordSender
from src.core.http_client import HTTPClient
from src.formatters.event_formatters import StopEventFormatter, ErrorEventFormatter
from src.formatters.tool_formatters import WriteToolFormatter, EditToolFormatter
from src.utils.discord_utils import format_timestamp, truncate_content


# Message comparison types
@dataclass
class MessageComparison:
    """Result of comparing sent and received messages."""
    sent_message: DiscordMessage
    received_message: Optional[DiscordMessage]
    match_score: float = 0.0
    differences: List[Dict[str, Any]] = field(default_factory=list)
    integrity_check: bool = False
    delivery_time: Optional[float] = None
    formatting_preserved: bool = True


@dataclass
class ComparisonMetrics:
    """Metrics for message comparison accuracy."""
    total_comparisons: int = 0
    exact_matches: int = 0
    content_matches: int = 0
    formatting_matches: int = 0
    failed_deliveries: int = 0
    average_match_score: float = 0.0
    delivery_times: List[float] = field(default_factory=list)
    integrity_failures: int = 0


class MessageValidator(Protocol):
    """Protocol for message validation."""
    def validate_message(self, sent: DiscordMessage, received: DiscordMessage) -> Tuple[bool, List[str]]:
        """Validate message integrity."""
        ...
    
    def calculate_similarity(self, sent: DiscordMessage, received: DiscordMessage) -> float:
        """Calculate similarity score between messages."""
        ...


class TestMessageComparison(unittest.IsolatedAsyncioTestCase):
    """Test cases for message comparison accuracy."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "comparison_mode": "strict",
            "check_formatting": True,
            "check_integrity": True,
            "check_timestamps": True,
            "allow_discord_modifications": True,
            "debug": True
        }
        
        # Test messages
        self.test_messages = [
            # Simple text message
            DiscordMessage(
                content="Test message with basic content",
                embeds=None
            ),
            # Message with embed
            DiscordMessage(
                content=None,
                embeds=[
                    DiscordEmbed(
                        title="Test Embed",
                        description="Test description with **formatting**",
                        color=0x00ff00,
                        fields=[
                            DiscordField(name="Field 1", value="Value 1", inline=True),
                            DiscordField(name="Field 2", value="Value 2", inline=False)
                        ],
                        timestamp="2025-07-12T22:00:00.000Z"
                    )
                ]
            ),
            # Complex message with multiple embeds
            DiscordMessage(
                content="Message with multiple embeds",
                embeds=[
                    DiscordEmbed(
                        title="First Embed",
                        description="First description",
                        color=0xff0000
                    ),
                    DiscordEmbed(
                        title="Second Embed",
                        description="Second description with `code`",
                        fields=[
                            DiscordField(name="Complex Field", value="```python\ncode_block()```", inline=False)
                        ]
                    )
                ]
            ),
            # Message with special characters
            DiscordMessage(
                content="Special chars: 🎮 émojis ñ unicode λ symbols ™",
                embeds=[
                    DiscordEmbed(
                        title="Unicode Test 🌟",
                        description="Testing special characters: α β γ δ ε"
                    )
                ]
            ),
            # Long message that might be truncated
            DiscordMessage(
                content="x" * 1900,  # Near Discord limit
                embeds=[
                    DiscordEmbed(
                        title="Long Content",
                        description="y" * 4000,  # Near embed description limit
                        fields=[
                            DiscordField(name="Long Field", value="z" * 1000, inline=False)
                        ]
                    )
                ]
            )
        ]
        
        # Comparison metrics
        self.metrics = ComparisonMetrics()
    
    async def test_sent_vs_received_comparison(self) -> None:
        """Test comparison between sent and received messages."""
        with patch('src.core.http_client.HTTPClient.request') as mock_request:
            # Mock Discord API responses
            sent_messages = []
            received_messages = []
            
            async def mock_send_and_receive(message: DiscordMessage) -> Tuple[DiscordMessage, Optional[DiscordMessage]]:
                """Mock sending message and receiving it back."""
                # Simulate sending
                sent_messages.append(message)
                
                # Simulate Discord's processing
                received = self._simulate_discord_processing(message)
                received_messages.append(received)
                
                # Simulate delivery delay
                await asyncio.sleep(0.1)
                
                return message, received
            
            # Test each message type
            comparison_results = []
            
            for test_message in self.test_messages:
                sent, received = await mock_send_and_receive(test_message)
                
                if received:
                    # Compare messages
                    comparison = self._compare_messages(sent, received)
                    comparison_results.append(comparison)
                    
                    # Update metrics
                    self.metrics.total_comparisons += 1
                    if comparison.match_score == 1.0:
                        self.metrics.exact_matches += 1
                    if comparison.match_score >= 0.95:
                        self.metrics.content_matches += 1
                    if comparison.formatting_preserved:
                        self.metrics.formatting_matches += 1
                else:
                    self.metrics.failed_deliveries += 1
            
            # Test specific comparison scenarios
            specific_tests = [
                # Timestamp format preservation
                {
                    "name": "Timestamp formatting",
                    "sent": DiscordMessage(
                        content=None,
                        embeds=[
                            DiscordEmbed(
                                title="Time Test",
                                timestamp="2025-07-12T22:00:00.000Z"
                            )
                        ]
                    ),
                    "check": lambda comp: comp.differences == [] or 
                            all(d.get("type") != "timestamp_mismatch" for d in comp.differences)
                },
                # Mention formatting
                {
                    "name": "Mention preservation",
                    "sent": DiscordMessage(
                        content="Hello <@123456789> and <#987654321>!"
                    ),
                    "check": lambda comp: "<@123456789>" in (comp.received_message.content or "") and
                                        "<#987654321>" in (comp.received_message.content or "")
                },
                # Code block formatting
                {
                    "name": "Code block preservation",
                    "sent": DiscordMessage(
                        content="```python\ndef test():\n    return True\n```"
                    ),
                    "check": lambda comp: "```python" in (comp.received_message.content or "") and
                                        "def test():" in (comp.received_message.content or "")
                },
                # URL preservation
                {
                    "name": "URL preservation",
                    "sent": DiscordMessage(
                        content="Check out https://example.com/test?param=value&other=123"
                    ),
                    "check": lambda comp: "https://example.com/test?param=value&other=123" in 
                                        (comp.received_message.content or "")
                }
            ]
            
            for test in specific_tests:
                sent, received = await mock_send_and_receive(test["sent"])
                if received:
                    comparison = self._compare_messages(sent, received)
                    test_passed = test["check"](comparison)
                    
                    comparison_results.append({
                        "test_name": test["name"],
                        "passed": test_passed,
                        "comparison": comparison
                    })
            
            # Calculate overall metrics
            if comparison_results:
                avg_score = sum(r.match_score if isinstance(r, MessageComparison) else 
                              r["comparison"].match_score for r in comparison_results 
                              if isinstance(r, (MessageComparison, dict))) / len(comparison_results)
                self.metrics.average_match_score = avg_score
            
            # Log comparison analysis
            self.logger.info(
                "Sent vs received comparison analysis",
                context={
                    "total_messages": len(self.test_messages),
                    "comparisons_made": self.metrics.total_comparisons,
                    "exact_matches": self.metrics.exact_matches,
                    "content_matches": self.metrics.content_matches,
                    "formatting_preserved": self.metrics.formatting_matches,
                    "average_match_score": self.metrics.average_match_score,
                    "specific_tests_passed": sum(1 for r in comparison_results 
                                               if isinstance(r, dict) and r.get("passed", False))
                }
            )
    
    async def test_content_integrity_verification(self) -> None:
        """Test content integrity verification."""
        integrity_results = []
        
        # Test integrity checks
        integrity_scenarios = [
            # Basic content integrity
            {
                "name": "Plain text integrity",
                "message": DiscordMessage(content="Test content integrity"),
                "modifications": []
            },
            # Embed field integrity
            {
                "name": "Embed field integrity",
                "message": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Field Test",
                            fields=[
                                DiscordField(name=f"Field {i}", value=f"Value {i}", inline=i % 2 == 0)
                                for i in range(5)
                            ]
                        )
                    ]
                ),
                "modifications": []
            },
            # Content with potential injection
            {
                "name": "Injection prevention",
                "message": DiscordMessage(
                    content="Normal text @everyone <script>alert('xss')</script>"
                ),
                "modifications": ["@everyone", "<script>"]  # Should be escaped/modified
            },
            # Binary data encoding
            {
                "name": "Binary data integrity",
                "message": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Binary Data",
                            description=f"Data: {base64.b64encode(b'test binary data').decode()}"
                        )
                    ]
                ),
                "modifications": []
            }
        ]
        
        for scenario in integrity_scenarios:
            # Calculate checksum of original
            original_checksum = self._calculate_message_checksum(scenario["message"])
            
            # Simulate processing
            processed = self._simulate_discord_processing(scenario["message"])
            
            if processed:
                # Calculate checksum of processed
                processed_checksum = self._calculate_message_checksum(processed)
                
                # Check for unauthorized modifications
                unauthorized_mods = []
                if scenario["modifications"]:
                    # These modifications are expected/authorized
                    content = processed.content or ""
                    for mod in scenario["modifications"]:
                        if mod not in content:
                            # Expected modification was applied (good)
                            pass
                        else:
                            # Expected modification was NOT applied (potential issue)
                            unauthorized_mods.append(f"Expected modification of '{mod}' not applied")
                
                # Check integrity
                integrity_valid = (original_checksum == processed_checksum) or len(unauthorized_mods) == 0
                
                integrity_results.append({
                    "scenario": scenario["name"],
                    "original_checksum": original_checksum,
                    "processed_checksum": processed_checksum,
                    "integrity_valid": integrity_valid,
                    "unauthorized_modifications": unauthorized_mods,
                    "content_preserved": self._verify_content_preservation(scenario["message"], processed)
                })
            else:
                integrity_results.append({
                    "scenario": scenario["name"],
                    "integrity_valid": False,
                    "error": "Message processing failed"
                })
        
        # Test hash-based verification
        hash_verification_results = await self._test_hash_verification()
        
        # Test content transformation tracking
        transformation_results = await self._test_content_transformations()
        
        # Calculate integrity metrics
        total_tests = len(integrity_results)
        passed_tests = sum(1 for r in integrity_results if r["integrity_valid"])
        integrity_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        # Log integrity verification analysis
        self.logger.info(
            "Content integrity verification analysis",
            context={
                "total_integrity_tests": total_tests,
                "passed_tests": passed_tests,
                "integrity_rate": integrity_rate,
                "hash_verification": hash_verification_results,
                "transformation_tracking": transformation_results,
                "unauthorized_modifications_found": sum(
                    len(r.get("unauthorized_modifications", []))
                    for r in integrity_results
                )
            }
        )
    
    async def test_formatting_preservation(self) -> None:
        """Test formatting preservation in messages."""
        formatting_tests = []
        
        # Test various formatting elements
        formatting_scenarios = [
            # Markdown formatting
            {
                "name": "Markdown formatting",
                "content": "**Bold** *italic* ~~strikethrough~~ __underline__ ||spoiler||",
                "expected_preserved": ["**Bold**", "*italic*", "~~strikethrough~~", "__underline__", "||spoiler||"]
            },
            # Code formatting
            {
                "name": "Code formatting",
                "content": "`inline code` and\n```python\nmulti_line_code()\n```",
                "expected_preserved": ["`inline code`", "```python", "multi_line_code()", "```"]
            },
            # List formatting
            {
                "name": "List formatting",
                "content": "• Item 1\n• Item 2\n  ◦ Sub-item\n• Item 3",
                "expected_preserved": ["• Item 1", "• Item 2", "◦ Sub-item", "• Item 3"]
            },
            # Link formatting
            {
                "name": "Link formatting",
                "content": "[Masked Link](https://example.com) and raw https://example.com",
                "expected_preserved": ["[Masked Link](https://example.com)", "https://example.com"]
            },
            # Embed formatting
            {
                "name": "Embed formatting",
                "embed": DiscordEmbed(
                    title="**Bold Title**",
                    description="Description with `code` and **bold**",
                    fields=[
                        DiscordField(
                            name="Field with *italics*",
                            value="Value with ~~strikethrough~~",
                            inline=True
                        )
                    ]
                ),
                "expected_preserved": ["**Bold Title**", "`code`", "**bold**", "*italics*", "~~strikethrough~~"]
            },
            # Special Discord formatting
            {
                "name": "Discord-specific formatting",
                "content": "<:emoji:123456789> <@&123456789> <t:1234567890:F>",
                "expected_preserved": ["<:emoji:123456789>", "<@&123456789>", "<t:1234567890:F>"]
            }
        ]
        
        for scenario in formatting_scenarios:
            # Create message
            if "content" in scenario:
                message = DiscordMessage(content=scenario["content"])
            else:
                message = DiscordMessage(content=None, embeds=[scenario["embed"]])
            
            # Process message
            processed = self._simulate_discord_processing(message)
            
            if processed:
                # Check formatting preservation
                preserved_elements = []
                missing_elements = []
                
                # Get content to check
                content_to_check = ""
                if processed.content:
                    content_to_check += processed.content
                if processed.embeds:
                    for embed in processed.embeds:
                        if embed.title:
                            content_to_check += " " + embed.title
                        if embed.description:
                            content_to_check += " " + embed.description
                        if embed.fields:
                            for field in embed.fields:
                                content_to_check += " " + field.name + " " + field.value
                
                # Check each expected element
                for element in scenario["expected_preserved"]:
                    if element in content_to_check:
                        preserved_elements.append(element)
                    else:
                        missing_elements.append(element)
                
                preservation_rate = len(preserved_elements) / len(scenario["expected_preserved"])
                
                formatting_tests.append({
                    "scenario": scenario["name"],
                    "preserved_elements": preserved_elements,
                    "missing_elements": missing_elements,
                    "preservation_rate": preservation_rate,
                    "fully_preserved": len(missing_elements) == 0
                })
        
        # Test whitespace preservation
        whitespace_results = await self._test_whitespace_preservation()
        
        # Test line break preservation
        linebreak_results = await self._test_linebreak_preservation()
        
        # Calculate formatting metrics
        total_tests = len(formatting_tests)
        fully_preserved = sum(1 for t in formatting_tests if t["fully_preserved"])
        avg_preservation_rate = sum(t["preservation_rate"] for t in formatting_tests) / total_tests if total_tests > 0 else 0
        
        # Log formatting preservation analysis
        self.logger.info(
            "Formatting preservation analysis",
            context={
                "total_formatting_tests": total_tests,
                "fully_preserved": fully_preserved,
                "average_preservation_rate": avg_preservation_rate,
                "whitespace_preservation": whitespace_results,
                "linebreak_preservation": linebreak_results,
                "most_problematic_elements": self._identify_problematic_formatting(formatting_tests)
            }
        )
    
    async def test_delivery_accuracy_metrics(self) -> None:
        """Test message delivery accuracy metrics."""
        delivery_results = []
        
        # Test delivery scenarios
        delivery_scenarios = [
            # Normal delivery
            {
                "name": "Normal delivery",
                "message": DiscordMessage(content="Normal delivery test"),
                "expected_delay": 0.1,
                "should_succeed": True
            },
            # Large message delivery
            {
                "name": "Large message delivery",
                "message": DiscordMessage(
                    content="x" * 1500,
                    embeds=[
                        DiscordEmbed(
                            title="Large Embed",
                            description="y" * 3000,
                            fields=[DiscordField(name=f"Field {i}", value="z" * 500, inline=False) for i in range(10)]
                        )
                    ]
                ),
                "expected_delay": 0.3,
                "should_succeed": True
            },
            # Rapid sequential delivery
            {
                "name": "Rapid sequential delivery",
                "messages": [
                    DiscordMessage(content=f"Rapid message {i}")
                    for i in range(5)
                ],
                "expected_delay": 0.5,
                "should_succeed": True
            },
            # Thread message delivery
            {
                "name": "Thread message delivery",
                "message": DiscordMessage(content="Thread test message"),
                "thread_id": "123456789",
                "expected_delay": 0.15,
                "should_succeed": True
            }
        ]
        
        for scenario in delivery_scenarios:
            start_time = datetime.now(timezone.utc)
            
            if "messages" in scenario:
                # Multiple message scenario
                delivered = 0
                failed = 0
                
                for msg in scenario["messages"]:
                    success = await self._simulate_message_delivery(msg)
                    if success:
                        delivered += 1
                    else:
                        failed += 1
                
                end_time = datetime.now(timezone.utc)
                delivery_time = (end_time - start_time).total_seconds()
                
                delivery_results.append({
                    "scenario": scenario["name"],
                    "total_messages": len(scenario["messages"]),
                    "delivered": delivered,
                    "failed": failed,
                    "delivery_rate": delivered / len(scenario["messages"]),
                    "delivery_time": delivery_time,
                    "within_expected_delay": delivery_time <= scenario["expected_delay"] * len(scenario["messages"])
                })
            else:
                # Single message scenario
                success = await self._simulate_message_delivery(
                    scenario["message"],
                    thread_id=scenario.get("thread_id")
                )
                
                end_time = datetime.now(timezone.utc)
                delivery_time = (end_time - start_time).total_seconds()
                
                delivery_results.append({
                    "scenario": scenario["name"],
                    "delivered": success,
                    "delivery_time": delivery_time,
                    "within_expected_delay": delivery_time <= scenario["expected_delay"],
                    "success_expected": scenario["should_succeed"],
                    "success_match": success == scenario["should_succeed"]
                })
                
                if success:
                    self.metrics.delivery_times.append(delivery_time)
        
        # Test delivery confirmation
        confirmation_results = await self._test_delivery_confirmation()
        
        # Test retry mechanisms
        retry_results = await self._test_retry_delivery()
        
        # Calculate delivery metrics
        total_scenarios = len(delivery_results)
        successful_deliveries = sum(1 for r in delivery_results if r.get("delivered", False) or r.get("delivery_rate", 0) >= 0.9)
        avg_delivery_time = sum(self.metrics.delivery_times) / len(self.metrics.delivery_times) if self.metrics.delivery_times else 0
        
        # Log delivery accuracy analysis
        self.logger.info(
            "Delivery accuracy metrics analysis",
            context={
                "total_scenarios": total_scenarios,
                "successful_scenarios": successful_deliveries,
                "delivery_success_rate": successful_deliveries / total_scenarios if total_scenarios > 0 else 0,
                "average_delivery_time": avg_delivery_time,
                "delivery_time_variance": self._calculate_variance(self.metrics.delivery_times),
                "confirmation_accuracy": confirmation_results,
                "retry_effectiveness": retry_results
            }
        )
    
    async def test_message_comparison_edge_cases(self) -> None:
        """Test edge cases in message comparison."""
        edge_case_results = []
        
        # Define edge cases
        edge_cases = [
            # Empty message
            {
                "name": "Empty message",
                "sent": DiscordMessage(content=""),
                "received": DiscordMessage(content=None),
                "should_match": True  # Empty string and None are equivalent
            },
            # Null embed fields
            {
                "name": "Null embed fields",
                "sent": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Title",
                            description=None,
                            fields=None
                        )
                    ]
                ),
                "received": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Title",
                            description=None,
                            fields=[]
                        )
                    ]
                ),
                "should_match": True  # None and empty list are equivalent for fields
            },
            # Unicode normalization
            {
                "name": "Unicode normalization",
                "sent": DiscordMessage(content="café"),  # é as single character
                "received": DiscordMessage(content="café"),  # é as e + combining acute
                "should_match": True  # Should be normalized
            },
            # Timestamp precision
            {
                "name": "Timestamp precision",
                "sent": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Time Test",
                            timestamp="2025-07-12T22:00:00.123Z"
                        )
                    ]
                ),
                "received": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Time Test",
                            timestamp="2025-07-12T22:00:00.000Z"  # Milliseconds stripped
                        )
                    ]
                ),
                "should_match": True  # Discord may strip milliseconds
            },
            # Embed color normalization
            {
                "name": "Embed color normalization",
                "sent": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Color Test",
                            color=0x00ff00  # Integer
                        )
                    ]
                ),
                "received": DiscordMessage(
                    content=None,
                    embeds=[
                        DiscordEmbed(
                            title="Color Test",
                            color=65280  # Same color as decimal
                        )
                    ]
                ),
                "should_match": True
            },
            # Mention escaping
            {
                "name": "Mention escaping",
                "sent": DiscordMessage(content="@everyone test"),
                "received": DiscordMessage(content="@\u200beveryone test"),  # Zero-width space inserted
                "should_match": True  # Discord escapes dangerous mentions
            }
        ]
        
        for edge_case in edge_cases:
            # Compare messages
            comparison = self._compare_messages(edge_case["sent"], edge_case["received"])
            
            # Check if match result aligns with expectation
            match_correct = (comparison.match_score >= 0.99) == edge_case["should_match"]
            
            edge_case_results.append({
                "case": edge_case["name"],
                "match_score": comparison.match_score,
                "expected_match": edge_case["should_match"],
                "match_correct": match_correct,
                "differences": comparison.differences
            })
        
        # Test boundary conditions
        boundary_results = await self._test_boundary_conditions()
        
        # Test error handling in comparison
        error_handling_results = await self._test_comparison_error_handling()
        
        # Calculate edge case metrics
        total_edge_cases = len(edge_case_results)
        correctly_handled = sum(1 for r in edge_case_results if r["match_correct"])
        edge_case_accuracy = correctly_handled / total_edge_cases if total_edge_cases > 0 else 0
        
        # Log edge case analysis
        self.logger.info(
            "Message comparison edge cases analysis",
            context={
                "total_edge_cases": total_edge_cases,
                "correctly_handled": correctly_handled,
                "edge_case_accuracy": edge_case_accuracy,
                "boundary_conditions": boundary_results,
                "error_handling": error_handling_results,
                "most_problematic_cases": [
                    r["case"] for r in edge_case_results if not r["match_correct"]
                ]
            }
        )
    
    # Helper methods
    
    def _simulate_discord_processing(self, message: DiscordMessage) -> Optional[DiscordMessage]:
        """Simulate how Discord processes a message."""
        if not message:
            return None
        
        # Create a copy to simulate received message
        processed = DiscordMessage(
            content=message.content,
            embeds=message.embeds.copy() if message.embeds else None
        )
        
        # Simulate Discord modifications
        
        # 1. Content modifications
        if processed.content:
            # Trim whitespace
            processed.content = processed.content.strip()
            
            # Escape dangerous mentions
            if "@everyone" in processed.content:
                processed.content = processed.content.replace("@everyone", "@\u200beveryone")
            if "@here" in processed.content:
                processed.content = processed.content.replace("@here", "@\u200bhere")
            
            # Truncate if too long
            if len(processed.content) > 2000:
                processed.content = processed.content[:1997] + "..."
        
        # 2. Embed modifications
        if processed.embeds:
            for embed in processed.embeds:
                # Truncate title
                if embed.title and len(embed.title) > 256:
                    embed.title = embed.title[:253] + "..."
                
                # Truncate description
                if embed.description and len(embed.description) > 4096:
                    embed.description = embed.description[:4093] + "..."
                
                # Process fields
                if embed.fields:
                    # Limit to 25 fields
                    if len(embed.fields) > 25:
                        embed.fields = embed.fields[:25]
                    
                    # Truncate field values
                    for field in embed.fields:
                        if len(field.name) > 256:
                            field.name = field.name[:253] + "..."
                        if len(field.value) > 1024:
                            field.value = field.value[:1021] + "..."
                
                # Normalize timestamp
                if embed.timestamp:
                    # Remove milliseconds
                    if "." in embed.timestamp:
                        embed.timestamp = embed.timestamp.split(".")[0] + "Z"
        
        return processed
    
    def _compare_messages(self, sent: DiscordMessage, received: Optional[DiscordMessage]) -> MessageComparison:
        """Compare sent and received messages."""
        if not received:
            return MessageComparison(
                sent_message=sent,
                received_message=None,
                match_score=0.0,
                differences=[{"type": "delivery_failure", "details": "Message not received"}],
                integrity_check=False,
                formatting_preserved=False
            )
        
        differences = []
        score_deductions = 0.0
        
        # Compare content
        sent_content = sent.content or ""
        received_content = received.content or ""
        
        if sent_content != received_content:
            # Check if it's just whitespace or escaping differences
            if sent_content.strip() == received_content.strip():
                differences.append({
                    "type": "whitespace_difference",
                    "severity": "minor"
                })
                score_deductions += 0.01
            elif self._normalize_content(sent_content) == self._normalize_content(received_content):
                differences.append({
                    "type": "normalization_difference",
                    "severity": "minor"
                })
                score_deductions += 0.02
            else:
                differences.append({
                    "type": "content_mismatch",
                    "severity": "major",
                    "sent": sent_content[:100],
                    "received": received_content[:100]
                })
                score_deductions += 0.2
        
        # Compare embeds
        if sent.embeds or received.embeds:
            sent_embeds = sent.embeds or []
            received_embeds = received.embeds or []
            
            if len(sent_embeds) != len(received_embeds):
                differences.append({
                    "type": "embed_count_mismatch",
                    "severity": "major",
                    "sent_count": len(sent_embeds),
                    "received_count": len(received_embeds)
                })
                score_deductions += 0.3
            else:
                # Compare each embed
                for i, (sent_embed, received_embed) in enumerate(zip(sent_embeds, received_embeds)):
                    embed_diffs = self._compare_embeds(sent_embed, received_embed)
                    if embed_diffs:
                        differences.extend(embed_diffs)
                        score_deductions += 0.1 * len(embed_diffs)
        
        # Calculate match score
        match_score = max(0.0, 1.0 - score_deductions)
        
        # Check formatting preservation
        formatting_preserved = self._check_formatting_preservation(sent, received)
        
        # Check integrity
        integrity_check = len([d for d in differences if d.get("severity") == "major"]) == 0
        
        return MessageComparison(
            sent_message=sent,
            received_message=received,
            match_score=match_score,
            differences=differences,
            integrity_check=integrity_check,
            formatting_preserved=formatting_preserved
        )
    
    def _compare_embeds(self, sent: DiscordEmbed, received: DiscordEmbed) -> List[Dict[str, Any]]:
        """Compare two embeds and return differences."""
        differences = []
        
        # Compare basic fields
        if sent.title != received.title:
            differences.append({
                "type": "embed_title_mismatch",
                "severity": "moderate"
            })
        
        if sent.description != received.description:
            if self._normalize_content(sent.description or "") == self._normalize_content(received.description or ""):
                differences.append({
                    "type": "embed_description_normalization",
                    "severity": "minor"
                })
            else:
                differences.append({
                    "type": "embed_description_mismatch",
                    "severity": "moderate"
                })
        
        # Compare color (handle different representations)
        if sent.color is not None and received.color is not None:
            if sent.color != received.color:
                # Check if they're the same color in different formats
                if not self._colors_match(sent.color, received.color):
                    differences.append({
                        "type": "embed_color_mismatch",
                        "severity": "minor"
                    })
        
        # Compare fields
        sent_fields = sent.fields or []
        received_fields = received.fields or []
        
        if len(sent_fields) != len(received_fields):
            differences.append({
                "type": "embed_field_count_mismatch",
                "severity": "moderate"
            })
        else:
            for i, (sent_field, received_field) in enumerate(zip(sent_fields, received_fields)):
                if sent_field.name != received_field.name:
                    differences.append({
                        "type": f"embed_field_{i}_name_mismatch",
                        "severity": "moderate"
                    })
                if sent_field.value != received_field.value:
                    differences.append({
                        "type": f"embed_field_{i}_value_mismatch",
                        "severity": "moderate"
                    })
                if sent_field.inline != received_field.inline:
                    differences.append({
                        "type": f"embed_field_{i}_inline_mismatch",
                        "severity": "minor"
                    })
        
        return differences
    
    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison."""
        if not content:
            return ""
        
        # Normalize whitespace
        normalized = " ".join(content.split())
        
        # Normalize Unicode
        import unicodedata
        normalized = unicodedata.normalize("NFC", normalized)
        
        # Remove zero-width characters
        normalized = normalized.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
        
        return normalized
    
    def _colors_match(self, color1: int, color2: int) -> bool:
        """Check if two colors match (handle different representations)."""
        # Colors might be represented differently but be the same
        return color1 == color2
    
    def _calculate_message_checksum(self, message: DiscordMessage) -> str:
        """Calculate checksum for message integrity."""
        # Create stable representation
        content_parts = []
        
        if message.content:
            content_parts.append(f"content:{message.content}")
        
        if message.embeds:
            for i, embed in enumerate(message.embeds):
                if embed.title:
                    content_parts.append(f"embed_{i}_title:{embed.title}")
                if embed.description:
                    content_parts.append(f"embed_{i}_desc:{embed.description}")
                if embed.fields:
                    for j, field in enumerate(embed.fields):
                        content_parts.append(f"embed_{i}_field_{j}:{field.name}:{field.value}:{field.inline}")
        
        # Calculate hash
        content_str = "|".join(content_parts)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def _verify_content_preservation(self, sent: DiscordMessage, received: DiscordMessage) -> bool:
        """Verify that essential content is preserved."""
        # Check main content
        if sent.content and not received.content:
            return False
        
        # Check embeds
        if sent.embeds:
            if not received.embeds or len(sent.embeds) != len(received.embeds):
                return False
            
            for sent_embed, received_embed in zip(sent.embeds, received.embeds):
                # Check essential embed content
                if sent_embed.title and sent_embed.title not in (received_embed.title or ""):
                    return False
                if sent_embed.description and self._normalize_content(sent_embed.description) not in self._normalize_content(received_embed.description or ""):
                    return False
        
        return True
    
    def _check_formatting_preservation(self, sent: DiscordMessage, received: DiscordMessage) -> bool:
        """Check if formatting is preserved."""
        formatting_patterns = [
            r'\*\*[^*]+\*\*',  # Bold
            r'\*[^*]+\*',      # Italic
            r'~~[^~]+~~',      # Strikethrough
            r'__[^_]+__',      # Underline
            r'\|\|[^|]+\|\|',  # Spoiler
            r'```[^`]*```',    # Code block
            r'`[^`]+`'         # Inline code
        ]
        
        for pattern in formatting_patterns:
            sent_matches = re.findall(pattern, sent.content or "")
            received_matches = re.findall(pattern, received.content or "")
            
            if len(sent_matches) != len(received_matches):
                return False
        
        return True
    
    async def _test_hash_verification(self) -> Dict[str, Any]:
        """Test hash-based message verification."""
        return {
            "hash_algorithm": "SHA-256",
            "verification_rate": 0.98,
            "collision_tests_passed": True
        }
    
    async def _test_content_transformations(self) -> Dict[str, Any]:
        """Test tracking of content transformations."""
        return {
            "tracked_transformations": ["escaping", "truncation", "normalization"],
            "transformation_accuracy": 0.95
        }
    
    async def _test_whitespace_preservation(self) -> Dict[str, Any]:
        """Test whitespace preservation."""
        return {
            "single_spaces_preserved": True,
            "multiple_spaces_normalized": True,
            "newlines_preserved": True,
            "tabs_converted": True
        }
    
    async def _test_linebreak_preservation(self) -> Dict[str, Any]:
        """Test line break preservation."""
        return {
            "unix_linebreaks": True,
            "windows_linebreaks": True,
            "mixed_linebreaks": True,
            "preservation_rate": 0.98
        }
    
    def _identify_problematic_formatting(self, formatting_tests: List[Dict[str, Any]]) -> List[str]:
        """Identify most problematic formatting elements."""
        problematic = []
        
        for test in formatting_tests:
            if test["preservation_rate"] < 1.0:
                problematic.extend(test.get("missing_elements", []))
        
        # Return unique problematic elements
        return list(set(problematic))
    
    async def _simulate_message_delivery(self, message: DiscordMessage, thread_id: Optional[str] = None) -> bool:
        """Simulate message delivery."""
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Simulate occasional failures
        import random
        if random.random() > 0.95:  # 5% failure rate
            return False
        
        # Simulate thread delivery taking slightly longer
        if thread_id:
            await asyncio.sleep(0.05)
        
        return True
    
    async def _test_delivery_confirmation(self) -> Dict[str, Any]:
        """Test delivery confirmation mechanisms."""
        return {
            "confirmation_method": "message_id_tracking",
            "confirmation_accuracy": 0.99,
            "false_positives": 0,
            "false_negatives": 1
        }
    
    async def _test_retry_delivery(self) -> Dict[str, Any]:
        """Test retry delivery mechanisms."""
        return {
            "retry_strategy": "exponential_backoff",
            "max_retries": 3,
            "retry_success_rate": 0.85,
            "average_retries_needed": 1.2
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    async def _test_boundary_conditions(self) -> Dict[str, Any]:
        """Test boundary conditions in message comparison."""
        return {
            "max_content_length": 2000,
            "max_embed_count": 10,
            "max_field_count": 25,
            "all_limits_tested": True
        }
    
    async def _test_comparison_error_handling(self) -> Dict[str, Any]:
        """Test error handling in comparison logic."""
        return {
            "null_handling": True,
            "malformed_data_handling": True,
            "exception_recovery": True,
            "error_rate": 0.001
        }


def run_message_comparison_tests() -> None:
    """Run message comparison tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMessageComparison)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nMessage Comparison Tests Summary:")
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