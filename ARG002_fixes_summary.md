# ARG002 Fixes Summary

## Overview
Fixed all ARG002 errors (Unused method/function arguments) in the codebase by prefixing unused parameters with underscore.

## Files Fixed

### 1. `/examples/discord_notifier_refactor_example.py`
- **Line 219**: Changed `token: str` to `_token: str` in `post_bot_api` method
  - This parameter is part of the interface but not used in the mock implementation

### 2. `/examples/generic_integration_example.py`
- **Line 154**: Changed `event_data: Any` to `_event_data: Any` in `_default_formatter` method
  - The default formatter returns a generic response without using the event data

### 3. `/examples/generic_types_refactor_example.py`
- **Line 461**: Changed `request: HTTPRequest[TReq]` to `_request: HTTPRequest[TReq]` in `execute` method
  - This is a mock implementation that doesn't use the request parameter

### 4. `/examples/variance_issue_demonstration.py`
- **Line 171**: Changed `data: dict[str, Any]` to `_data: dict[str, Any]` in `format` method of `FormatterBase`
  - The base formatter returns a fixed response without using the data parameter

### 5. `/utils/validate_json_types.py`
- **Line 65**: Changed `node: ast.Call` to `_node: ast.Call` in `_check_json_loads_usage` method
  - The method logs a generic issue without inspecting the specific node

## Rationale
All these parameters are either:
1. Required by an interface/protocol that the method must implement
2. Part of a callback signature that cannot be changed
3. In mock/example implementations where the parameter isn't needed

By prefixing with underscore, we indicate that the parameter is intentionally unused while maintaining the required method signature.