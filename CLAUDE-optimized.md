# CLAUDE.md - Discord Event Notifier

Simple architecture implementation guide for Claude Code Discord notifications.

## 📚 Essential Documentation
- **@docs/simple-architecture-complete-guide.md** - Technical specifications
- **@docs/troubleshooting.md** - Troubleshooting guide
- **@docs/architecture-guide.md** - Configuration reference
- **@~/.claude/discord-event-notifier-personal-config.md** - Personal preferences

## 🎯 Core Principles

### Documentation After Success
**When you solve an error, document it immediately in CLAUDE.md:**
1. Error encountered
2. Solution found
3. Why it worked
4. Prevention strategy

### Key Lessons Learned
- **Module naming**: Avoid stdlib conflicts (`types.py` → `event_types.py`)
- **Environment isolation**: Use `--no-project` flag for hooks
- **Timestamps**: Always use `date +"%Y-%m-%d-%H-%M-%S"`
- **Working directory**: Shows `[/path]` in Discord notifications

## 🚀 Current Implementation

### Simple Architecture (555 lines, 5 files)
```
src/simple/
├── event_types.py    # Type definitions (94 lines)
├── config.py         # Configuration (117 lines)
├── discord_client.py # Discord API (71 lines)
├── handlers.py       # Event handlers (190 lines)
└── main.py          # Entry point (83 lines)
```

**Features:**
- 93% code reduction (8,000 → 555 lines)
- Pure Python 3.13+ with zero dependencies
- Fail-silent design (never blocks Claude Code)
- Easy extension: 1 function + 1 line per new event

## 🔧 Essential Commands

### Setup & Configuration
```bash
# Setup hooks (simple architecture)
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks_simple.py

# Validate configuration
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks_simple.py --validate

# End-to-end testing
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py --validate-end-to-end

# Hot reload config
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py --reload
```

### Debug Commands
```bash
# Check logs
tail -f ~/.claude/hooks/logs/discord_notifier_*.log

# Verify Python environment
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python -c "from typing import ReadOnly, TypeIs; import os; print(f'Python 3.13+ features: OK')"
```

## ⚠️ Critical Requirements

### Python Execution
**NEVER use `python3` - ALWAYS use `uv run --python 3.13 python`**

```bash
# ❌ FORBIDDEN
python3 configure_hooks.py

# ✅ REQUIRED
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py

# Hook execution with isolation
uv run --python 3.13 --no-project python /path/to/script.py
```

### Configuration Files
- **Discord settings**: `~/.claude/.env`
- **Hook configuration**: `~/.claude/settings.json`

## 📋 Quick Reference

### Status Summary
- **Implementation**: Simple architecture (555 lines) is primary
- **Python**: 3.13+ with ReadOnly/TypeIs support
- **Dependencies**: Zero (stdlib only)
- **Entry point**: `src/simple/main.py`
- **Setup script**: `configure_hooks_simple.py`

### Next Steps
- Long-term stability monitoring
- Support for new event types
- Complete migration from 8k-line architecture

---
*Last updated: 2025-07-19-16-08-01*