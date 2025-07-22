#!/usr/bin/env python3
"""Discord API advanced validation and analysis tool.

Comprehensive Discord API validation with message analysis, statistics,
and repeated verification capabilities.
Refactored from src/utils/discord_api_validator.py with improved architecture.
"""

import sys
import time
from datetime import datetime, timezone
from typing import Optional, TypedDict

from shared import get_discord_channel_id, make_discord_request, extract_message_info


class ValidationResult(TypedDict):
    """Result structure for channel validation."""
    success: bool
    channel_id: str
    message_count: int
    latest_message: Optional[dict[str, str]]
    validation_timestamp: str
    error_message: Optional[str]
    has_notifier_messages: bool
    notifier_message_count: int


class HealthAnalysis(TypedDict):
    """Health analysis result structure."""
    status: str
    success_rate: str
    successful_attempts: int
    total_attempts: int
    latest_success: bool
    has_notifier_messages: bool
    max_notifier_messages: int
    last_error: Optional[str]


def fetch_channel_messages(channel_id: str, limit: int = 50) -> ValidationResult:
    """Fetch recent messages from Discord channel with analysis.

    Args:
        channel_id: Discord channel ID to fetch messages from
        limit: Maximum number of messages to fetch

    Returns:
        Validation result with message information and statistics
    """
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Construct Discord API URL
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
    
    # Make API request
    success, data, error = make_discord_request(url)
    
    if not success or not data:
        return ValidationResult(
            success=False,
            channel_id=channel_id,
            message_count=0,
            latest_message=None,
            validation_timestamp=current_time,
            error_message=error or "Unknown error",
            has_notifier_messages=False,
            notifier_message_count=0,
        )
    
    # Validate response format
    if not isinstance(data, list):
        return ValidationResult(
            success=False,
            channel_id=channel_id,
            message_count=0,
            latest_message=None,
            validation_timestamp=current_time,
            error_message="Unexpected API response format",
            has_notifier_messages=False,
            notifier_message_count=0,
        )
    
    # Analyze messages
    message_count = len(data)
    latest_message = None
    notifier_message_count = 0
    
    if data:
        # Extract latest message info
        latest_msg_data = data[0]
        latest_message = extract_message_info(latest_msg_data)
        
        # Count Discord Notifier messages
        for msg in data:
            embeds = msg.get("embeds", [])
            for embed in embeds:
                footer = embed.get("footer", {})
                footer_text = footer.get("text", "")
                if "Discord Notifier" in footer_text:
                    notifier_message_count += 1
                    break
    
    has_notifier_messages = notifier_message_count > 0
    
    return ValidationResult(
        success=True,
        channel_id=channel_id,
        message_count=message_count,
        latest_message=latest_message,
        validation_timestamp=current_time,
        error_message=None,
        has_notifier_messages=has_notifier_messages,
        notifier_message_count=notifier_message_count,
    )


def verify_channel_repeatedly(
    channel_id: str,
    iterations: int = 3,
    delay_seconds: int = 2,
) -> list[ValidationResult]:
    """Perform repeated channel verification for real-time validation.

    Args:
        channel_id: Discord channel ID to verify
        iterations: Number of verification attempts
        delay_seconds: Delay between attempts in seconds

    Returns:
        List of validation results from each attempt
    """
    print(f"🔍 Starting repeated verification for channel {channel_id}")
    print(f"   Iterations: {iterations}, Delay: {delay_seconds}s")
    print()
    
    results = []
    
    for i in range(iterations):
        print(f"🔄 Verification attempt {i + 1}/{iterations}...")
        
        result = fetch_channel_messages(channel_id)
        results.append(result)
        
        if result["success"]:
            print(f"✅ Success: Found {result['message_count']} messages")
            if result["has_notifier_messages"]:
                print(f"   📢 {result['notifier_message_count']} Discord Notifier messages detected")
            else:
                print("   📢 No Discord Notifier messages found")
        else:
            print(f"❌ Failed: {result['error_message']}")
        
        # Wait before next attempt (except for the last one)
        if i < iterations - 1:
            print(f"   ⏳ Waiting {delay_seconds}s before next attempt...")
            time.sleep(delay_seconds)
        
        print()
    
    return results


def analyze_channel_health(results: list[ValidationResult]) -> HealthAnalysis:
    """Analyze channel health from multiple validation attempts.

    Args:
        results: List of validation results

    Returns:
        Comprehensive health analysis
    """
    if not results:
        return HealthAnalysis(
            status="no_data",
            success_rate="0.0%",
            successful_attempts=0,
            total_attempts=0,
            latest_success=False,
            has_notifier_messages=False,
            max_notifier_messages=0,
            last_error="No validation results available",
        )
    
    success_count = sum(1 for r in results if r["success"])
    total_attempts = len(results)
    success_rate = success_count / total_attempts if total_attempts > 0 else 0
    
    latest_result = results[-1]
    
    # Determine overall health status
    if success_rate >= 0.8:
        status = "healthy"
    elif success_rate >= 0.5:
        status = "partial_issues"
    else:
        status = "unhealthy"
    
    return HealthAnalysis(
        status=status,
        success_rate=f"{success_rate:.1%}",
        successful_attempts=success_count,
        total_attempts=total_attempts,
        latest_success=latest_result["success"],
        has_notifier_messages=any(r.get("has_notifier_messages", False) for r in results),
        max_notifier_messages=max((r.get("notifier_message_count", 0) for r in results), default=0),
        last_error=latest_result.get("error_message") if not latest_result["success"] else None,
    )


def print_health_analysis(health: HealthAnalysis) -> None:
    """Print health analysis in a formatted way.

    Args:
        health: Health analysis results
    """
    print("📊 Channel Health Analysis")
    print("=" * 60)
    
    # Status with emoji
    status_emoji = {
        "healthy": "✅",
        "partial_issues": "⚠️",
        "unhealthy": "❌",
        "no_data": "📊",
    }
    
    emoji = status_emoji.get(health["status"], "❓")
    print(f"Overall Status: {emoji} {health['status'].title()}")
    print(f"Success Rate: {health['success_rate']}")
    print(f"Successful Attempts: {health['successful_attempts']}/{health['total_attempts']}")
    print(f"Latest Attempt: {'✅ Success' if health['latest_success'] else '❌ Failed'}")
    
    print(f"\nDiscord Notifier Detection:")
    if health["has_notifier_messages"]:
        print(f"   ✅ Found Discord Notifier messages (max: {health['max_notifier_messages']})")
    else:
        print(f"   ❌ No Discord Notifier messages detected")
    
    if health["last_error"]:
        print(f"\nLast Error: {health['last_error']}")


def print_latest_message_info(result: ValidationResult) -> None:
    """Print information about the latest message.

    Args:
        result: Validation result containing message info
    """
    if not result["success"] or not result["latest_message"]:
        return
    
    print("📝 Latest Message Information")
    print("=" * 60)
    
    msg = result["latest_message"]
    print(f"Message ID: {msg['id']}")
    print(f"Author: {msg['author']['username']} (ID: {msg['author']['id']})")
    print(f"Bot Account: {'Yes' if msg['author']['bot'] else 'No'}")
    print(f"Timestamp: {msg['timestamp']}")
    print(f"Content Length: {len(msg['content'])} characters")
    print(f"Embeds: {msg['embeds_count']}")
    print(f"Attachments: {msg['attachments_count']}")
    print(f"Reactions: {msg['reactions_count']}")
    
    if msg['content']:
        preview = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
        print(f"\nContent Preview:")
        print(f"   {preview}")


def main() -> None:
    """Main entry point for advanced validator."""
    import argparse
    
    description = """Discord API advanced validator with message analysis

Performs comprehensive validation of Discord channel access with repeated
verification, message statistics, and health analysis. Detects Discord/Simple
Notifier messages and provides detailed channel health metrics."""
    
    epilog = """What it validates:
  - Message retrieval capability and consistency
  - Discord/Simple Notifier message detection
  - API response reliability over multiple attempts
  - Channel health status with statistical analysis

Examples:
  # Validate default channel with default settings
  %(prog)s
  
  # Validate specific channel with 5 iterations
  %(prog)s --channel-id 1391964875600822366 --iterations 5
  
  # Quick validation with 1 iteration, no delay
  %(prog)s --iterations 1 --delay 0
  
  # Fetch more messages for analysis
  %(prog)s --limit 100

Configuration:
  Bot token and channel ID can be set via:
  - Environment: DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
  - Config file: ~/.claude/.env

Output includes:
  - Success rate percentage
  - Message count and notifier message detection
  - Health status: healthy (≥80%), partial_issues (≥50%), unhealthy (<50%)
  - Latest message information
  - Detailed failure reasons if any

Exit codes:
  0 - Healthy or partial issues (≥50% success rate)
  1 - Unhealthy (major issues detected)
"""
    
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--channel-id",
        help="Discord channel ID to validate. If not specified, uses DISCORD_CHANNEL_ID from config"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of validation iterations for reliability testing (default: 3)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=2,
        help="Delay between iterations in seconds to avoid rate limits (default: 2)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum messages to fetch per iteration for analysis (default: 50, max: 100)"
    )
    
    args = parser.parse_args()
    
    # Get channel ID
    channel_id = args.channel_id or get_discord_channel_id()
    if not channel_id:
        print("❌ Channel ID not provided and not found in config")
        print("   Use --channel-id or set DISCORD_CHANNEL_ID")
        sys.exit(1)
    
    print("🚀 Discord API Advanced Validator")
    print("=" * 60)
    print(f"Target Channel: {channel_id}")
    print(f"Message Limit: {args.limit}")
    print()
    
    # Perform repeated verification
    results = verify_channel_repeatedly(
        channel_id,
        iterations=args.iterations,
        delay_seconds=args.delay,
    )
    
    # Analyze results
    health = analyze_channel_health(results)
    print_health_analysis(health)
    
    # Show latest message info if available
    if results:
        print()
        print_latest_message_info(results[-1])
    
    print()
    print("=" * 60)
    print("🎯 Advanced validation completed!")
    
    # Exit with appropriate code
    if health["status"] in ["healthy", "partial_issues"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()