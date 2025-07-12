#!/usr/bin/env python3
"""Discord embed utilities for handling large content.

This module provides utilities for creating Discord embeds that respect
Discord's various size limits while maximizing content display.
"""


from src.utils.astolfo_logger import AstolfoLogger
from src.core.constants import DiscordLimits
from src.core.http_client import DiscordEmbed
from src.formatters.base import split_long_text, truncate_string

logger = AstolfoLogger(__name__)


def create_embed_with_fields(
    title: str,
    description: str,
    fields_content: list[tuple[str, str]],
    color: int | None = None,
    timestamp: str | None = None,
    footer_text: str | None = None
) -> DiscordEmbed:
    """Create a Discord embed with automatic field splitting for long content.
    
    Args:
        title: Embed title
        description: Main description (will be truncated if too long)
        fields_content: List of (name, value) tuples for fields
        color: Embed color
        timestamp: ISO format timestamp
        footer_text: Footer text
        
    Returns:
        DiscordEmbed with properly formatted fields
        
    Note:
        - Description is truncated to 4096 chars
        - Field values are split if they exceed 1024 chars
        - Maximum 25 fields per embed (Discord limit)
    """
    logger.debug("Creating embed with fields", {
        "title": title,
        "description_length": len(description),
        "field_count": len(fields_content),
        "has_color": color is not None,
        "has_timestamp": timestamp is not None,
        "has_footer": footer_text is not None
    })
    
    # Ensure description doesn't exceed limit
    if len(description) > DiscordLimits.MAX_DESCRIPTION_LENGTH:
        logger.warning("Description exceeds Discord limit, truncating", {
            "original_length": len(description),
            "max_length": DiscordLimits.MAX_DESCRIPTION_LENGTH
        })
        description = truncate_string(description, DiscordLimits.MAX_DESCRIPTION_LENGTH)

    # Initialize embed
    embed: DiscordEmbed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": timestamp,
        "footer": {"text": footer_text} if footer_text else None,
        "fields": []
    }

    # Process fields
    field_count = 0
    max_fields = 25  # Discord's maximum fields per embed

    for field_name, field_value in fields_content:
        if field_count >= max_fields:
            logger.warning("Maximum field limit reached, truncating remaining fields", {
                "max_fields": max_fields,
                "remaining_fields": len(fields_content) - field_count
            })
            # Add a final field indicating there's more content
            if embed["fields"]:
                embed["fields"].append({
                    "name": "⚠️ Content Truncated",
                    "value": "Maximum field limit reached. Some content omitted.",
                    "inline": None
                })
            break

        # Split long field values
        if len(field_value) > DiscordLimits.MAX_FIELD_VALUE_LENGTH:
            logger.debug("Field value exceeds limit, splitting", {
                "field_name": field_name,
                "value_length": len(field_value),
                "max_length": DiscordLimits.MAX_FIELD_VALUE_LENGTH
            })
            parts = split_long_text(field_value, field_name)
            for part in parts:
                if field_count >= max_fields - 1:  # Reserve one for truncation message
                    break

                # Extract name and value from the formatted part
                # Format is "**Name:**\nValue" or "**Name (Part N):**\nValue"
                if "\n" in part:
                    part_name, part_value = part.split("\n", 1)
                    # Remove markdown formatting
                    part_name = part_name.strip("*: ")
                else:
                    part_name = field_name
                    part_value = part

                if embed["fields"] is not None:
                    embed["fields"].append({
                        "name": part_name,
                        "value": part_value,
                        "inline": None
                    })
                field_count += 1
        else:
            # Field fits within limit
            if embed["fields"] is not None:
                embed["fields"].append({
                    "name": field_name,
                    "value": field_value,
                    "inline": None
                })
            field_count += 1

    logger.debug("Embed created successfully", {
        "final_field_count": field_count,
        "truncated": field_count < len(fields_content)
    })
    
    return embed


def split_description_to_embeds(
    title: str,
    long_description: str,
    color: int | None = None,
    timestamp: str | None = None,
    footer_text: str | None = None
) -> list[DiscordEmbed]:
    """Split a long description into multiple embeds if needed.
    
    Args:
        title: Base title for embeds
        long_description: Description that may exceed Discord limits
        color: Embed color
        timestamp: ISO format timestamp
        footer_text: Footer text
        
    Returns:
        List of embeds, each within Discord's size limits
    """
    logger.debug("Splitting description to embeds", {
        "title": title,
        "description_length": len(long_description),
        "max_length": DiscordLimits.MAX_DESCRIPTION_LENGTH,
        "needs_split": len(long_description) > DiscordLimits.MAX_DESCRIPTION_LENGTH
    })
    
    embeds: list[DiscordEmbed] = []

    if len(long_description) <= DiscordLimits.MAX_DESCRIPTION_LENGTH:
        # Fits in one embed
        embed: DiscordEmbed = {
            "title": title,
            "description": long_description,
            "color": color,
            "timestamp": timestamp,
            "footer": {"text": footer_text} if footer_text else None,
            "fields": None
        }
        return [embed]

    # Split into multiple embeds
    parts = split_long_text(long_description, "Content", DiscordLimits.MAX_DESCRIPTION_LENGTH - 100)
    
    logger.info("Splitting long description into multiple embeds", {
        "total_parts": len(parts),
        "max_embeds": 10,
        "parts_to_use": min(len(parts), 10)
    })

    for i, part in enumerate(parts[:10]):  # Discord allows max 10 embeds
        part_title = f"{title} (Part {i+1}/{len(parts)})" if len(parts) > 1 else title

        part_embed: DiscordEmbed = {
            "title": part_title,
            "description": part,
            "color": color,
            "timestamp": timestamp if i == 0 else None,  # Only first embed gets timestamp
            "footer": {"text": footer_text} if footer_text and i == len(parts) - 1 else None,
            "fields": None
        }
        embeds.append(part_embed)

    logger.debug("Embeds created successfully", {
        "embed_count": len(embeds),
        "total_requested": len(parts),
        "truncated": len(parts) > 10
    })

    return embeds

