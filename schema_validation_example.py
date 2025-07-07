#!/usr/bin/env python3
"""
Example implementation of JSON schema validation for type inference improvement.

This demonstrates how schema validation can convert `Any` types from json.loads()
into properly typed structures that type checkers can understand.
"""

import json
from typing import Any, TypedDict, Literal, cast, TypeGuard
from dataclasses import dataclass

# Type definitions (existing)
class BashToolInput(TypedDict, total=False):
    """Bash tool input structure."""
    command: str
    description: str

class PreToolUseEventData(TypedDict):
    """PreToolUse event data structure."""
    session_id: str
    transcript_path: str
    hook_event_name: str
    tool_name: str
    tool_input: dict[str, Any]

EventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]

# JSON Schema definitions (what we would add)
EVENT_SCHEMAS = {
    "PreToolUse": {
        "type": "object",
        "required": ["session_id", "hook_event_name", "tool_name", "tool_input"],
        "properties": {
            "session_id": {"type": "string"},
            "transcript_path": {"type": "string"},
            "hook_event_name": {"type": "string"},
            "tool_name": {"type": "string"},
            "tool_input": {"type": "object"}
        }
    },
    "PostToolUse": {
        "type": "object",
        "required": ["session_id", "hook_event_name", "tool_name", "tool_input", "tool_response"],
        "properties": {
            "session_id": {"type": "string"},
            "transcript_path": {"type": "string"},
            "hook_event_name": {"type": "string"},
            "tool_name": {"type": "string"},
            "tool_input": {"type": "object"},
            "tool_response": {}  # Can be string, dict, or list
        }
    }
}

TOOL_INPUT_SCHEMAS = {
    "Bash": {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["command"]
    },
    "Edit": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"}
        },
        "required": ["file_path", "old_string", "new_string"]
    }
}

@dataclass
class ValidationError(Exception):
    """Schema validation error."""
    message: str
    path: str = ""

class SchemaValidator:
    """Simple JSON schema validator focused on type checking."""
    
    def __init__(self):
        self.event_schemas = EVENT_SCHEMAS
        self.tool_schemas = TOOL_INPUT_SCHEMAS
    
    def validate_event(self, event_type: str, data: Any) -> bool:
        """Validate event data against schema."""
        if event_type not in self.event_schemas:
            return False
        
        schema = self.event_schemas[event_type]
        return self._validate_object(data, schema)
    
    def validate_tool_input(self, tool_name: str, data: Any) -> bool:
        """Validate tool input against schema."""
        if tool_name not in self.tool_schemas:
            return True  # Allow unknown tools
        
        schema = self.tool_schemas[tool_name]
        return self._validate_object(data, schema)
    
    def _validate_object(self, data: Any, schema: dict[str, Any]) -> bool:
        """Validate data against object schema."""
        if not isinstance(data, dict):
            return False
        
        # Check required fields
        for field in schema.get("required", []):
            if field not in data:
                return False
        
        # Check field types
        properties = schema.get("properties", {})
        for field, value in data.items():
            if field in properties:
                field_schema = properties[field]
                if not self._validate_field(value, field_schema):
                    return False
        
        return True
    
    def _validate_field(self, value: Any, field_schema: dict[str, Any]) -> bool:
        """Validate individual field."""
        expected_type = field_schema.get("type")
        
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "object":
            return isinstance(value, dict)
        elif expected_type == "array":
            return isinstance(value, list)
        else:
            return True  # Allow any type if not specified

# Type guards using schema validation
def is_valid_pre_tool_use_event(data: Any) -> TypeGuard[PreToolUseEventData]:
    """Type guard for PreToolUse events using schema validation."""
    validator = SchemaValidator()
    return validator.validate_event("PreToolUse", data)

def is_valid_bash_tool_input(data: Any) -> TypeGuard[BashToolInput]:
    """Type guard for Bash tool input using schema validation."""
    validator = SchemaValidator()
    return validator.validate_tool_input("Bash", data)

# Usage examples showing improved type inference
def process_event_with_validation(raw_json: str, event_type: str) -> None:
    """Example showing how validation improves type inference."""
    # This returns Any
    data = json.loads(raw_json)
    
    # Before validation: data is Any, no type inference
    # session_id = data.get("session_id")  # Type: Any
    
    # After validation: data becomes properly typed
    if event_type == "PreToolUse" and is_valid_pre_tool_use_event(data):
        # Now data is typed as PreToolUseEventData
        session_id = data["session_id"]  # Type: str
        tool_name = data["tool_name"]    # Type: str
        tool_input = data["tool_input"]  # Type: dict[str, Any]
        
        # Further validation for tool input
        if tool_name == "Bash" and is_valid_bash_tool_input(tool_input):
            # Now tool_input is typed as BashToolInput
            command = tool_input["command"]  # Type: str
            description = tool_input.get("description", "")  # Type: str
            
            print(f"Processing Bash command: {command}")
            if description:
                print(f"Description: {description}")
        else:
            print(f"Processing {tool_name} tool with generic input")
    else:
        print("Invalid event data")

def load_config_with_validation(config_data: Any) -> dict[str, Any]:
    """Example of config validation improving type inference."""
    # Define config schema
    config_schema = {
        "type": "object",
        "properties": {
            "webhook_url": {"type": "string"},
            "bot_token": {"type": "string"},
            "channel_id": {"type": "string"},
            "debug": {"type": "boolean"},
            "use_threads": {"type": "boolean"},
            "channel_type": {"type": "string", "enum": ["text", "forum"]},
            "thread_prefix": {"type": "string"},
            "mention_user_id": {"type": "string"}
        }
    }
    
    validator = SchemaValidator()
    if validator._validate_object(config_data, config_schema):
        # After validation, we know the structure is correct
        return cast(dict[str, Any], config_data)
    else:
        raise ValidationError("Invalid configuration structure")

# Benefits demonstration
def demonstrate_benefits():
    """Show the benefits of schema validation for type inference."""
    
    # Example 1: Event processing
    event_json = '''
    {
        "session_id": "abc123",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {
            "command": "ls -la",
            "description": "List files"
        }
    }
    '''
    
    process_event_with_validation(event_json, "PreToolUse")
    
    # Example 2: Configuration validation
    config_data = {
        "webhook_url": "https://discord.com/api/webhooks/123/abc",
        "debug": True,
        "use_threads": False,
        "channel_type": "text"
    }
    
    try:
        validated_config = load_config_with_validation(config_data)
        print("Config validation successful")
    except ValidationError as e:
        print(f"Config validation failed: {e.message}")

if __name__ == "__main__":
    demonstrate_benefits()