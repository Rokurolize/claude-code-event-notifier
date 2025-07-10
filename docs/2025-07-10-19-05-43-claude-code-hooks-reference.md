# Claude Code Hooks Reference Documentation

## Overview

Hooks are user-defined shell commands that execute at various points in Claude Code's lifecycle, providing deterministic control over its behavior. They allow you to run custom commands before or after tool execution.

## Key Hook Events

1. **PreToolUse**: Runs before tool calls
2. **PostToolUse**: Runs after tool completion  
3. **Notification**: Runs when notifications are sent
4. **Stop**: Runs when main agent finishes
5. **SubagentStop**: Runs when subagent finishes

## Configuration Structure

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here"
          }
        ]
      }
    ]
  }
}
```

## Common Matchers

- Task
- Bash
- Glob
- Grep
- Read
- Edit/MultiEdit
- Write
- WebFetch/WebSearch

## Hook Input Data Structure

Hooks receive input via stdin as JSON:

```json
{
  "session_id": "abc123",
  "transcript_path": "path/to/transcript.jsonl",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "file content"
  }
}
```

## Hook Output Methods

### 1. Exit Codes
- **0**: Success (continue normal execution)
- **2**: Blocking error (stop execution)
- **Others**: Non-blocking error (log but continue)

### 2. JSON Output
Hooks can output JSON to:
- Control continuation
- Provide decision reasons
- Block/approve tool calls

## Example Use Cases

1. **Automatically run a Python formatter after Claude modifies Python files**
2. **Prevent modifications to production configuration files by blocking Write operations**

## Security Warning

⚠️ **Important**: Hooks execute shell commands with your full user permissions without confirmation. Be careful with the commands you configure.

## Claude Code Overview

Claude Code is an agentic coding tool that helps developers turn ideas into code faster.

### Key Features

1. **Feature Building**
   - Tell Claude what you want to build in plain English
   - It will make a plan, write the code, and ensure it works

2. **Debugging**
   - Describe a bug or paste an error message
   - Claude Code will analyze your codebase, identify the problem, and implement a fix

3. **Codebase Navigation**
   - Can answer questions about project structure
   - Maintains awareness of entire project
   - Can pull information from external sources (Google Drive, Figma, Slack) via Model Context Protocol (MCP)

4. **Automation**
   - Fix lint issues
   - Resolve merge conflicts
   - Write release notes
   - Supports command-line and CI workflows

### Installation

```bash
npm install -g @anthropic-ai/claude-code
cd your-awesome-project
claude
```

## SDK Integration

### Authentication Methods

1. **Anthropic API Key**
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

2. **Third-Party Providers**
   - Amazon Bedrock: `export CLAUDE_CODE_USE_BEDROCK=1`
   - Google Vertex AI: `export CLAUDE_CODE_USE_VERTEX=1`

### Basic Usage Examples

#### Command Line
```bash
# Run a single prompt
claude -p "Write a function to calculate Fibonacci numbers"

# Output in JSON
claude -p "Generate code" --output-format json
```

#### TypeScript
```typescript
import { query } from "@anthropic-ai/claude-code";

for await (const message of query({
  prompt: "Write a haiku about foo.py",
  options: { maxTurns: 3 }
})) {
  // Process messages
}
```

#### Python
```python
from claude_code_sdk import query, ClaudeCodeOptions

async def main():
    async for message in query(
        prompt="Write a haiku about foo.py",
        options=ClaudeCodeOptions(max_turns=3)
    ):
        # Process messages
```

### Advanced Features
- Multi-turn conversations
- Custom system prompts
- Model Context Protocol (MCP) configuration
- Flexible permission handling

## Integration with Discord Notifier

This project (claude_code_event_notifier) uses hooks to send real-time notifications to Discord when Claude Code performs actions. The configuration is set up by `configure_hooks.py` which installs hooks for various events and tools.