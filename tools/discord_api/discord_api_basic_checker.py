#!/usr/bin/env python3
"""Discord API basic access and permissions checker.

Simple tool to verify Discord API access and permissions for bot.
Refactored from utils/check_discord_access.py with improved error handling.
"""

import sys
from typing import Optional

from shared import get_discord_bot_token, get_discord_channel_id, make_discord_request, print_api_response


def check_channel_access(channel_id: str) -> bool:
    """Check if bot can access the specified channel.

    Args:
        channel_id: Discord channel ID to test

    Returns:
        True if access successful, False otherwise
    """
    print(f"🔍 Checking channel access: {channel_id}")
    
    url = f"https://discord.com/api/v10/channels/{channel_id}"
    success, data, error = make_discord_request(url)
    
    print_api_response(success, data, error, "Channel access check")
    
    if success and data:
        channel_name = data.get("name", "Unknown")
        channel_type = data.get("type", "Unknown")
        print(f"   Channel: {channel_name} (Type: {channel_type})")
    
    return success


def check_bot_user_info() -> bool:
    """Check bot user information.

    Returns:
        True if check successful, False otherwise
    """
    print("🤖 Checking bot user info...")
    
    url = "https://discord.com/api/v10/users/@me"
    success, data, error = make_discord_request(url)
    
    print_api_response(success, data, error, "Bot user info check")
    
    if success and data:
        username = data.get("username", "Unknown")
        bot_id = data.get("id", "Unknown")
        print(f"   Bot: {username} (ID: {bot_id})")
    
    return success


def check_archived_threads(channel_id: str) -> bool:
    """Check access to archived threads in the channel.

    Args:
        channel_id: Discord channel ID to test

    Returns:
        True if check successful, False otherwise
    """
    print(f"📁 Checking archived threads access: {channel_id}")
    
    url = f"https://discord.com/api/v10/channels/{channel_id}/threads/archived/public"
    success, data, error = make_discord_request(url)
    
    print_api_response(success, data, error, "Archived threads check")
    
    if success and data:
        threads = data.get("threads", [])
        print(f"   Found {len(threads)} archived threads")
    
    return success


def check_specific_thread(thread_id: str) -> bool:
    """Check access to a specific thread.

    Args:
        thread_id: Discord thread ID to test

    Returns:
        True if check successful, False otherwise
    """
    print(f"🧵 Checking specific thread: {thread_id}")
    
    url = f"https://discord.com/api/v10/channels/{thread_id}"
    success, data, error = make_discord_request(url)
    
    print_api_response(success, data, error, "Thread access check")
    
    if success and data:
        thread_name = data.get("name", "Unknown")
        parent_id = data.get("parent_id", "Unknown")
        print(f"   Thread: {thread_name} (Parent: {parent_id})")
    
    return success


def run_comprehensive_check(
    channel_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> bool:
    """Run comprehensive Discord API access checks.

    Args:
        channel_id: Channel ID to test (if not provided, uses config)
        thread_id: Thread ID to test (optional)

    Returns:
        True if all checks pass, False otherwise
    """
    print("🚀 Discord API Basic Access Check")
    print("=" * 60)
    
    # Use provided channel_id or get from config
    if not channel_id:
        channel_id = get_discord_channel_id()
        if not channel_id:
            print("❌ Channel ID not provided and not found in config")
            return False
    
    print(f"Target Channel: {channel_id}")
    if thread_id:
        print(f"Target Thread: {thread_id}")
    print()
    
    # Run all checks
    results = []
    
    # 1. Bot user info
    results.append(check_bot_user_info())
    print()
    
    # 2. Channel access
    results.append(check_channel_access(channel_id))
    print()
    
    # 3. Archived threads (only if channel access succeeds)
    if results[-1]:
        results.append(check_archived_threads(channel_id))
        print()
    
    # 4. Specific thread (if provided)
    if thread_id:
        results.append(check_specific_thread(thread_id))
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = passed / total if total > 0 else 0
    
    print("📊 Check Summary")
    print("=" * 60)
    print(f"Passed: {passed}/{total} ({success_rate:.1%})")
    
    if success_rate == 1.0:
        print("✅ All checks passed - Discord API access is fully functional")
        return True
    elif success_rate >= 0.8:
        print("⚠️  Most checks passed - Some features may be limited")
        return False
    else:
        print("❌ Multiple checks failed - Discord API access has issues")
        return False


def main() -> None:
    """Main entry point for the basic checker."""
    import argparse
    
    description = """Discord API basic access and permissions checker

This tool verifies your bot's access to Discord channels and threads,
checking authentication, permissions, and API connectivity."""
    
    epilog = """Examples:
  # Check default channel from config
  %(prog)s
  
  # Check specific channel
  %(prog)s --channel-id 1391964875600822366
  
  # Check channel and thread
  %(prog)s --channel-id 1391964875600822366 --thread-id 1391977832007208990

Configuration:
  Bot token and channel ID can be set via:
  - Environment: DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
  - Config file: ~/.claude/.env

Output:
  - Bot authentication status
  - Channel access permissions
  - Archived threads list
  - Comprehensive permission analysis
  - Overall health status with success rate

Exit codes:
  0 - All checks passed
  1 - One or more checks failed
"""
    
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--channel-id",
        help="Discord channel ID to test (18-digit number). If not provided, uses DISCORD_CHANNEL_ID from environment or config"
    )
    parser.add_argument(
        "--thread-id",
        help="Discord thread ID to test (optional). Tests thread-specific permissions"
    )
    
    args = parser.parse_args()
    
    # Check configuration
    token = get_discord_bot_token()
    if not token:
        print("❌ Discord bot token not found")
        print("   Set DISCORD_BOT_TOKEN environment variable or add to ~/.claude/.env")
        sys.exit(1)
    
    # Run checks
    success = run_comprehensive_check(
        channel_id=args.channel_id,
        thread_id=args.thread_id,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()