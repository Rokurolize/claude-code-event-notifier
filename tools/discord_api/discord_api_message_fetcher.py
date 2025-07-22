#!/usr/bin/env python3
"""Discord API message fetcher and analyzer.

Tool for fetching specific Discord messages by ID and analyzing their structure.
Refactored from fetch_specific_message.py with enhanced analysis capabilities.
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional

from shared import make_discord_request, extract_message_info


def fetch_message_by_id(channel_id: str, message_id: str) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """Fetch specific message from Discord API by ID.

    Args:
        channel_id: Discord channel ID containing the message
        message_id: Discord message ID to fetch

    Returns:
        Tuple of (success, message_data, error_message)
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    return make_discord_request(url)


def analyze_message_structure(message_data: dict[str, Any]) -> None:
    """Analyze and display detailed message structure.

    Args:
        message_data: Raw message data from Discord API
    """
    print("📋 Message Structure Analysis")
    print("=" * 60)
    
    # Basic info
    basic_info = extract_message_info(message_data)
    print("🔍 Basic Information:")
    print(f"   Message ID: {basic_info['id']}")
    print(f"   Author: {basic_info['author']['username']} (ID: {basic_info['author']['id']})")
    print(f"   Bot Account: {'Yes' if basic_info['author']['bot'] else 'No'}")
    print(f"   Timestamp: {basic_info['timestamp']}")
    print(f"   Content Length: {len(message_data.get('content', ''))} characters")
    print()
    
    # Content analysis
    content = message_data.get('content', '')
    print("💬 Message Content:")
    print("-" * 40)
    if content:
        print(content)
    else:
        print("(No text content)")
    print("-" * 40)
    print()
    
    # Embeds analysis
    embeds = message_data.get('embeds', [])
    print(f"📎 Embeds Analysis ({len(embeds)} found):")
    if embeds:
        for i, embed in enumerate(embeds):
            print(f"\n   📋 Embed {i+1}:")
            print(f"      Title: {embed.get('title', 'N/A')}")
            print(f"      Description Length: {len(embed.get('description', ''))}")
            print(f"      Color: {embed.get('color', 'N/A')}")
            
            # Description preview
            description = embed.get('description', '')
            if description:
                preview = description[:100] + "..." if len(description) > 100 else description
                print(f"      Description Preview: {preview}")
            
            # Fields analysis
            fields = embed.get('fields', [])
            if fields:
                print(f"      Fields: {len(fields)}")
                for j, field in enumerate(fields):
                    value_preview = field.get('value', '')[:50] + "..." if len(field.get('value', '')) > 50 else field.get('value', '')
                    print(f"         {j+1}. {field.get('name', 'N/A')}: {value_preview}")
            
            # Footer
            footer = embed.get('footer', {})
            if footer:
                print(f"      Footer: {footer.get('text', 'N/A')}")
            
            # Timestamp
            if embed.get('timestamp'):
                print(f"      Embed Timestamp: {embed['timestamp']}")
    else:
        print("   (No embeds found)")
    print()
    
    # Attachments analysis
    attachments = message_data.get('attachments', [])
    print(f"📎 Attachments ({len(attachments)} found):")
    if attachments:
        for i, attachment in enumerate(attachments):
            print(f"   {i+1}. {attachment.get('filename', 'Unknown')}")
            print(f"      Size: {attachment.get('size', 0):,} bytes")
            print(f"      URL: {attachment.get('url', 'N/A')}")
    else:
        print("   (No attachments found)")
    print()
    
    # Reactions analysis
    reactions = message_data.get('reactions', [])
    print(f"😀 Reactions ({len(reactions)} found):")
    if reactions:
        for reaction in reactions:
            emoji = reaction.get('emoji', {})
            emoji_name = emoji.get('name', 'Unknown')
            count = reaction.get('count', 0)
            print(f"   {emoji_name}: {count}")
    else:
        print("   (No reactions found)")


def analyze_discord_notifier_message(message_data: dict[str, Any]) -> None:
    """Analyze if message is from Discord Notifier and show relevant info.

    Args:
        message_data: Raw message data from Discord API
    """
    print("🤖 Discord Notifier Analysis")
    print("=" * 60)
    
    # Check embeds for Discord Notifier signature
    embeds = message_data.get('embeds', [])
    notifier_embeds = []
    
    for embed in embeds:
        footer = embed.get('footer', {})
        footer_text = footer.get('text', '')
        if 'Discord Notifier' in footer_text:
            notifier_embeds.append(embed)
    
    if notifier_embeds:
        print(f"✅ Discord Notifier message detected ({len(notifier_embeds)} relevant embeds)")
        
        for i, embed in enumerate(notifier_embeds):
            print(f"\n   📋 Notifier Embed {i+1}:")
            print(f"      Title: {embed.get('title', 'N/A')}")
            print(f"      Color: #{embed.get('color', 0):06x}")
            
            # Extract session info
            footer_text = embed.get('footer', {}).get('text', '')
            if 'Session:' in footer_text:
                session_part = footer_text.split('Session:')[1].split('|')[0].strip()
                print(f"      Session ID: {session_part}")
            
            # Extract event type
            if 'Event:' in footer_text:
                event_part = footer_text.split('Event:')[1].split('|')[0].strip()
                print(f"      Event Type: {event_part}")
            
            # Show fields for additional context
            fields = embed.get('fields', [])
            if fields:
                print(f"      Fields:")
                for field in fields:
                    print(f"         {field.get('name', 'N/A')}: {field.get('value', 'N/A')}")
    else:
        print("❌ Not a Discord Notifier message")
    
    print()


def save_message_data(message_data: dict[str, Any], output_path: Optional[Path] = None) -> Path:
    """Save message data to JSON file for detailed analysis.

    Args:
        message_data: Raw message data to save
        output_path: Custom output path (optional)

    Returns:
        Path to the saved file
    """
    if output_path is None:
        message_id = message_data.get('id', 'unknown')
        timestamp = message_data.get('timestamp', '').replace(':', '-').replace('.', '-')
        output_path = Path(f"message_{message_id}_{timestamp}.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(message_data, f, indent=2, ensure_ascii=False)
    
    return output_path


def parse_discord_url(url: str) -> tuple[Optional[str], Optional[str]]:
    """Parse Discord message URL to extract channel and message IDs.

    Args:
        url: Discord message URL

    Returns:
        Tuple of (channel_id, message_id) or (None, None) if invalid
    """
    # Expected format: https://discord.com/channels/guild_id/channel_id/message_id
    parts = url.split('/')
    
    if len(parts) >= 3 and 'discord.com' in url:
        try:
            # Get the last three parts (guild, channel, message)
            if len(parts) >= 7:  # Full URL
                channel_id = parts[-2]
                message_id = parts[-1]
                return channel_id, message_id
        except (IndexError, ValueError):
            pass
    
    return None, None


def main() -> None:
    """Main entry point for message fetcher."""
    import argparse
    
    description = """Discord API message fetcher and analyzer

Fetches specific Discord messages by ID and provides detailed structural
analysis including embeds, attachments, and reactions. Supports Discord/Simple
Notifier message detection and analysis."""
    
    epilog = """Examples:
  # Fetch using channel and message IDs
  %(prog)s --channel-id 1391964875600822366 --message-id 1396369875953389590
  
  # Fetch using Discord URL (easiest method)
  %(prog)s --url "https://discord.com/channels/1141224103580274760/1391964875600822366/1396369875953389590"
  
  # Analyze Discord/Simple Notifier message
  %(prog)s --url "DISCORD_MESSAGE_URL" --analyze-notifier
  
  # Save raw JSON to specific file
  %(prog)s --url "DISCORD_MESSAGE_URL" --output analysis_output.json

Configuration:
  Bot token must be set via:
  - Environment: DISCORD_BOT_TOKEN
  - Config file: ~/.claude/.env

URL Format:
  https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
  
  The tool automatically extracts channel_id and message_id from the URL.

Output includes:
  - Message structure analysis (content, embeds, attachments)
  - Author information and timestamps
  - Embed details with fields and footers
  - Discord/Simple Notifier detection (with --analyze-notifier)
  - Raw JSON export for further analysis

--analyze-notifier option:
  When enabled, performs specialized analysis for Discord/Simple Notifier messages:
  - Detects notifier messages by footer signatures
  - Extracts session IDs and event types
  - Identifies notifier version information
  - Highlights any naming inconsistencies
  
  Note: Currently detects "Discord Notifier" and "Simple Notifier" patterns.
"""
    
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--channel-id",
        help="Discord channel ID (18-digit number). Required with --message-id"
    )
    parser.add_argument(
        "--message-id",
        help="Discord message ID (18-digit number). Required with --channel-id"
    )
    parser.add_argument(
        "--url",
        help="Discord message URL. Preferred method - automatically extracts IDs"
    )
    parser.add_argument(
        "--output",
        help="Custom output file path for raw JSON data (default: auto-generated)"
    )
    parser.add_argument(
        "--analyze-notifier",
        action="store_true",
        help="Enable Discord/Simple Notifier analysis to extract session info and metadata"
    )
    
    args = parser.parse_args()
    
    # Parse URL if provided
    if args.url:
        channel_id, message_id = parse_discord_url(args.url)
        if not channel_id or not message_id:
            print("❌ Invalid Discord URL format")
            print("   Expected: https://discord.com/channels/guild_id/channel_id/message_id")
            sys.exit(1)
    else:
        channel_id = args.channel_id
        message_id = args.message_id
    
    # Validate required parameters
    if not channel_id or not message_id:
        print("❌ Channel ID and Message ID are required")
        print("   Use --channel-id and --message-id, or --url")
        sys.exit(1)
    
    print("🔍 Discord Message Fetcher & Analyzer")
    print("=" * 60)
    print(f"Channel ID: {channel_id}")
    print(f"Message ID: {message_id}")
    if args.url:
        print(f"Source URL: {args.url}")
    print()
    
    # Fetch message
    print("📡 Fetching message...")
    success, message_data, error = fetch_message_by_id(channel_id, message_id)
    
    if not success or not message_data:
        print(f"❌ Failed to fetch message: {error}")
        sys.exit(1)
    
    print("✅ Message fetched successfully")
    print()
    
    # Analyze message
    analyze_message_structure(message_data)
    
    # Discord Notifier specific analysis
    if args.analyze_notifier:
        analyze_discord_notifier_message(message_data)
    
    # Save to file
    output_path = Path(args.output) if args.output else None
    saved_path = save_message_data(message_data, output_path)
    
    print("💾 Data Export")
    print("=" * 60)
    print(f"Full message data saved to: {saved_path}")
    print(f"File size: {saved_path.stat().st_size:,} bytes")
    
    print()
    print("🎯 Message analysis completed!")


if __name__ == "__main__":
    main()