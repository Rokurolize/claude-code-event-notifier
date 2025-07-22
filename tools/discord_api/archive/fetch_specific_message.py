#!/usr/bin/env python3
"""Fetch specific Discord message by ID for analysis."""

import json
import urllib.request
import urllib.error
from pathlib import Path
import sys

def get_discord_bot_token() -> str | None:
    """Get Discord bot token from config file."""
    config_path = Path.home() / ".claude" / ".env"
    
    if not config_path.exists():
        return None
    
    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('DISCORD_BOT_TOKEN='):
                return line.split('=', 1)[1]
    
    return None

def fetch_message(channel_id: str, message_id: str) -> dict | None:
    """Fetch specific message from Discord API."""
    token = get_discord_bot_token()
    if not token:
        print("❌ Discord bot token not found")
        return None
    
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    
    try:
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bot {token}")
        request.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data
            else:
                print(f"❌ API error: {response.status}")
                return None
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP error: {e.code} - {e.reason}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def analyze_message(message_data: dict):
    """Analyze and display message content."""
    print("📋 Message Analysis")
    print("=" * 50)
    print(f"Message ID: {message_data.get('id')}")
    print(f"Author: {message_data.get('author', {}).get('username')}")
    print(f"Timestamp: {message_data.get('timestamp')}")
    print(f"Content Length: {len(message_data.get('content', ''))}")
    print()
    
    # Display content
    content = message_data.get('content', '')
    print("💬 Message Content:")
    print("-" * 30)
    print(content)
    print("-" * 30)
    print()
    
    # Display embeds
    embeds = message_data.get('embeds', [])
    print(f"📎 Embeds: {len(embeds)}")
    if embeds:
        for i, embed in enumerate(embeds):
            print(f"\n📋 Embed {i+1}:")
            print(f"  Title: {embed.get('title', 'N/A')}")
            print(f"  Description: {embed.get('description', 'N/A')[:100]}...")
            print(f"  Color: {embed.get('color', 'N/A')}")
            
            fields = embed.get('fields', [])
            if fields:
                print(f"  Fields: {len(fields)}")
                for field in fields:
                    print(f"    - {field.get('name')}: {field.get('value', '')[:50]}...")

if __name__ == "__main__":
    # Message details from URL: https://discord.com/channels/1141224103580274760/1391964875600822366/1396369875953389590
    channel_id = "1391964875600822366"
    message_id = "1396369875953389590"
    
    print(f"🔍 Fetching message {message_id} from channel {channel_id}")
    
    message_data = fetch_message(channel_id, message_id)
    if message_data:
        analyze_message(message_data)
        
        # Save full message data for detailed analysis
        output_file = Path("message_analysis.json")
        with open(output_file, 'w') as f:
            json.dump(message_data, f, indent=2)
        print(f"\n💾 Full message data saved to: {output_file}")
    else:
        print("❌ Failed to fetch message")
        sys.exit(1)