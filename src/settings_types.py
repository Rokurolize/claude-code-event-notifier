#!/usr/bin/env python3
"""
Complete TypedDict definitions for Claude Code settings.json structure.

This module provides comprehensive type definitions for the entire settings
dictionary that's loaded from JSON, ensuring type safety when working with
Claude Code's hook system configuration.
"""

from typing import TypedDict, Literal, Any


# Hook-related types
class HookEntry(TypedDict):
    """Individual hook command entry."""
    type: Literal["command"]
    command: str


class HookConfig(TypedDict, total=False):
    """Hook configuration with hooks list and optional matcher."""
    hooks: list[HookEntry]
    matcher: str  # Optional, only for PreToolUse/PostToolUse


# Event type literal
HookEventType = Literal[
    "PreToolUse", 
    "PostToolUse", 
    "Notification", 
    "Stop", 
    "SubagentStop"
]


# Hooks dictionary type
HooksDict = dict[HookEventType, list[HookConfig]]


# Main settings structure
class ClaudeSettings(TypedDict, total=False):
    """Complete Claude Code settings.json structure."""
    
    # Hook configuration
    hooks: HooksDict
    
    # Other potential settings fields (based on Claude Code's capabilities)
    # These are optional and may not be present in all settings files
    theme: Literal["light", "dark", "auto"]
    editorFontSize: int
    editorFontFamily: str
    editorTabSize: int
    editorWordWrap: bool
    telemetryEnabled: bool
    autoSave: bool
    autoSaveDelay: int
    confirmBeforeClose: bool
    
    # Extension/plugin settings (if applicable)
    extensions: dict[str, Any]
    
    # Custom user preferences
    preferences: dict[str, Any]


# Helper type for partial settings updates
class PartialClaudeSettings(TypedDict, total=False):
    """Partial Claude Code settings for updates."""
    hooks: HooksDict


# Specific hook configurations for different event types
class ToolHookConfig(HookConfig):
    """Hook configuration specifically for tool events (Pre/PostToolUse)."""
    matcher: str  # Required for tool events


class NonToolHookConfig(TypedDict):
    """Hook configuration for non-tool events."""
    hooks: list[HookEntry]
    # No matcher field for non-tool events


# Union type for all hook configurations
AnyHookConfig = ToolHookConfig | NonToolHookConfig


# Example usage type guards
def is_tool_event(event_type: str) -> bool:
    """Check if an event type is a tool event requiring a matcher."""
    return event_type in ["PreToolUse", "PostToolUse"]


def validate_hook_config(event_type: HookEventType, config: HookConfig) -> bool:
    """Validate that a hook configuration is appropriate for its event type."""
    if is_tool_event(event_type):
        # Tool events should have a matcher
        return "matcher" in config and isinstance(config["matcher"], str)
    else:
        # Non-tool events should not have a matcher
        return "matcher" not in config


# Settings validation
def validate_settings(settings: Any) -> ClaudeSettings:
    """Validate and type-cast settings dictionary."""
    if not isinstance(settings, dict):
        raise TypeError("Settings must be a dictionary")
    
    # Validate hooks if present
    if "hooks" in settings:
        hooks = settings["hooks"]
        if not isinstance(hooks, dict):
            raise TypeError("Hooks must be a dictionary")
        
        for event_type, hook_list in hooks.items():
            if event_type not in ["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]:
                raise ValueError(f"Invalid hook event type: {event_type}")
            
            if not isinstance(hook_list, list):
                raise TypeError(f"Hooks for {event_type} must be a list")
            
            for hook_config in hook_list:
                if not isinstance(hook_config, dict):
                    raise TypeError(f"Hook config for {event_type} must be a dictionary")
                
                if "hooks" not in hook_config or not isinstance(hook_config["hooks"], list):
                    raise TypeError(f"Hook config for {event_type} must have a 'hooks' list")
                
                # Validate matcher presence based on event type
                if is_tool_event(event_type) and "matcher" not in hook_config:
                    raise ValueError(f"Tool event {event_type} requires a 'matcher' field")
                elif not is_tool_event(event_type) and "matcher" in hook_config:
                    raise ValueError(f"Non-tool event {event_type} should not have a 'matcher' field")
    
    return settings  # Type assertion after validation


# Default settings factory
def create_default_settings() -> ClaudeSettings:
    """Create a default Claude settings structure."""
    return {
        "hooks": {
            "PreToolUse": [],
            "PostToolUse": [],
            "Notification": [],
            "Stop": [],
            "SubagentStop": []
        }
    }


# Hook builder utilities
def create_hook_entry(command: str) -> HookEntry:
    """Create a hook entry."""
    return {
        "type": "command",
        "command": command
    }


def create_tool_hook_config(command: str, matcher: str = ".*") -> ToolHookConfig:
    """Create a hook configuration for tool events."""
    return {
        "hooks": [create_hook_entry(command)],
        "matcher": matcher
    }


def create_non_tool_hook_config(command: str) -> NonToolHookConfig:
    """Create a hook configuration for non-tool events."""
    return {
        "hooks": [create_hook_entry(command)]
    }


def create_hook_config(event_type: HookEventType, command: str, matcher: str = ".*") -> HookConfig:
    """Create an appropriate hook configuration based on event type."""
    if is_tool_event(event_type):
        return create_tool_hook_config(command, matcher)
    else:
        return create_non_tool_hook_config(command)