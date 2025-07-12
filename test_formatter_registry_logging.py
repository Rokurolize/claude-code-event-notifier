#!/usr/bin/env python3
"""Test script to verify formatter registry logging functionality."""

import os
import sys

# Set debug mode to see logs
os.environ["DISCORD_DEBUG"] = "1"

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.formatters.registry import FormatterRegistry, EventFormatter
from src.type_defs.discord import DiscordEmbed
from src.type_defs.events import EventData

def custom_formatter(event_data: EventData, session_id: str) -> DiscordEmbed:
    """Custom test formatter."""
    return {
        "title": "Custom Event",
        "description": "This is a custom formatter",
        "color": 0xFF0000,
        "timestamp": "2025-07-12T00:00:00.000Z"
    }

def main():
    print("Testing FormatterRegistry with AstolfoLogger...\n")
    
    # Create registry (should log initialization)
    print("1. Creating FormatterRegistry...")
    registry = FormatterRegistry()
    
    # Get existing formatter (should log successful retrieval)
    print("\n2. Getting formatter for 'Stop' event...")
    stop_formatter = registry.get_formatter("Stop")
    
    # Get non-existent formatter (should log warning and create default)
    print("\n3. Getting formatter for unknown 'CustomEvent'...")
    unknown_formatter = registry.get_formatter("CustomEvent")
    
    # Register new formatter (should log registration)
    print("\n4. Registering custom formatter for 'CustomEvent'...")
    registry.register("CustomEvent", custom_formatter)
    
    # Overwrite existing formatter (should log warning about overwrite)
    print("\n5. Overwriting formatter for 'Stop' event...")
    registry.register("Stop", custom_formatter)
    
    print("\nTest completed! Check the log output above for AstolfoLogger messages.")

if __name__ == "__main__":
    main()