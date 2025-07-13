# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Overview

Discord notifier for Claude Code hooks. Sends real-time notifications when Claude Code performs actions (file operations, command execution, etc.). Zero dependencies, uses only Python 3.13+ standard library.

## Commands

**IMPORTANT: This project requires Python 3.13 or higher. All commands must use Python 3.13+.**

```bash
# Install/configure the notifier in Claude Code (MUST use Python 3.13+)
uv run --no-sync --python 3.13 python configure_hooks.py
# Or if you have Python 3.13+ installed:
# python3.13 configure_hooks.py

# Remove the notifier from Claude Code
uv run --no-sync --python 3.13 python configure_hooks.py --remove

# Run all tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests -p "test_*.py"

# Run specific test categories
uv run --no-sync --python 3.13 python -m unittest discover -s tests/unit -p "test_*.py"      # Unit tests only
uv run --no-sync --python 3.13 python -m unittest discover -s tests/feature -p "test_*.py"    # Feature tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/integration -p "test_*.py" # Integration tests

# Run single test file
uv run --no-sync --python 3.13 python -m unittest tests/unit/test_discord_notifier.py

# Development quality assurance (MANDATORY before commits)
uv run --no-sync --python 3.13 python utils/development_checker.py

# Enhanced comprehensive quality assurance (ADVANCED - includes full QA system)
uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced

# Comprehensive quality assurance system (NEW - complete QA framework)
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py

# Quality gates (graduated quality verification)
uv run --no-sync --python 3.13 python utils/quality_assurance/gates/level1_basic_gate.py        # Basic quality
uv run --no-sync --python 3.13 python utils/quality_assurance/gates/level2_functional_gate.py  # Functional quality
uv run --no-sync --python 3.13 python utils/quality_assurance/gates/level3_integration_gate.py # Integration quality
uv run --no-sync --python 3.13 python utils/quality_assurance/gates/level4_production_gate.py  # Production ready

# Automated quality checks (development workflow)
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/instant_checker.py     # 30s quick check
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/category_checker.py    # Category-specific
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/full_checker.py        # Complete check

# Specialized validators
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/timestamp_accuracy_validator.py
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/api_response_validator.py
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/security_validator.py

# Type checking and linting (requires Python 3.13+)
uv run --no-sync --python 3.13 python -m mypy src/ configure_hooks.py
ruff check src/ configure_hooks.py utils/
ruff format src/ configure_hooks.py utils/

# Timestamp accuracy testing (CRITICAL for time display features)
uv run --no-sync --python 3.13 python -m unittest tests.timestamp.test_timestamp_accuracy -v

# View debug logs (requires DISCORD_DEBUG=1)  
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

## Architecture

### Core Structure

The project is organized into focused modules:

```
src/
├── discord_notifier.py    # Main entry point and event processing
├── thread_storage.py       # SQLite-based thread persistence
├── type_guards.py          # Runtime type validation with TypeGuard/TypeIs
└── settings_types.py       # TypedDict definitions for Claude Code settings

src/core/
├── config.py              # Configuration loading and validation
└── http_client.py         # Discord API client implementation

src/handlers/
├── discord_sender.py      # Message sending logic
├── event_registry.py      # Event type registration and dispatch
└── thread_manager.py      # Thread lookup and management

src/formatters/
├── base.py                # Base formatter protocol
├── event_formatters.py    # Event-specific formatters
└── tool_formatters.py     # Tool-specific formatters
```

### Event Processing Flow

1. **Hook Trigger**: Claude Code executes a tool and triggers the configured hook
2. **Event Reception**: `discord_notifier.py` receives JSON event data via stdin
3. **Event Parsing**: Event type determined from `CLAUDE_HOOK_EVENT` environment variable
4. **Filtering**: Check if event type is enabled/disabled in configuration
5. **Formatting**: Event-specific formatter creates Discord embed with appropriate details
6. **Thread Management**: If threads enabled, perform 4-tier lookup:
   - Check in-memory cache (`SESSION_THREAD_CACHE`)
   - Check SQLite storage (`thread_storage.py`)
   - Search Discord API for existing threads
   - Create new thread if needed
7. **Sending**: Use webhook or bot API to send formatted message
8. **Non-blocking Exit**: Always exit 0 to avoid blocking Claude Code

### Key Design Patterns

**Type Safety Throughout**:
- All data structures defined as TypedDict
- Runtime validation with TypeGuard functions
- Python 3.13+ type features (`TypeIs`, union types)

**Modular HTTP Client**:
- Separate methods for webhook vs bot API
- Built-in retry logic with exponential backoff
- Comprehensive error handling with custom exceptions

**Smart Thread Management**:
- Persistent storage prevents thread duplication
- Automatic thread unarchiving when reused
- Graceful fallback to main channel on errors

**Event-Specific Formatting**:
- Each event type has dedicated formatter
- Tool-specific details extracted and displayed
- Automatic truncation for Discord limits

### Configuration

Configuration follows a precedence hierarchy:
1. Environment variables (highest priority)
2. `.env` file in project root
3. Default values (lowest priority)

Key configuration options:
- `DISCORD_WEBHOOK_URL` or `DISCORD_TOKEN` + `DISCORD_CHANNEL_ID`
- `DISCORD_USE_THREADS` - Enable thread organization
- `DISCORD_ENABLED_EVENTS` / `DISCORD_DISABLED_EVENTS` - Event filtering
- `DISCORD_DEBUG` - Enable detailed logging

### Hook Integration

Hooks are configured to execute source files directly:
- No copying of files to hooks directory
- Changes to source code take effect immediately
- Must restart Claude Code after running `configure_hooks.py`

## Testing and Development

**CRITICAL: All testing must be done with Python 3.13 or higher.**

### Quality Assurance Workflow

**MANDATORY: Run development checks before any commit or deployment:**

```bash
# Pre-commit quality check (REQUIRED before committing)
uv run --no-sync --python 3.13 python utils/development_checker.py

# Timestamp accuracy verification (CRITICAL for time display)
uv run --no-sync --python 3.13 python -m unittest tests.timestamp.test_timestamp_accuracy -v

# Formatting-only tests (Discord API not required)
uv run --no-sync --python 3.13 python test_formatting_only.py

# Complete integration test (requires Discord credentials)
uv run --no-sync --python 3.13 python run_full_integration_test.py
```

### Development Standards

**Feature Completion Definition**: A feature is NOT complete until:
1. All unit/integration tests pass
2. Development quality checker passes
3. Real environment verification completed (not just mocked tests)
4. Timestamp accuracy verified in actual Discord notifications

**Time-Related Changes**: Any changes affecting timestamps require:
1. Timestamp accuracy tests pass
2. Manual verification in Discord with actual timestamp values
3. UTC leak detection passes
4. Cross-timezone functionality verified

### Test Categories

```bash
# Basic functionality tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/unit -p "test_*.py"      # Unit tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/feature -p "test_*.py"    # Feature tests  
uv run --no-sync --python 3.13 python -m unittest discover -s tests/integration -p "test_*.py" # Integration tests

# Specialized test suites
uv run --no-sync --python 3.13 python -m unittest discover -s tests/timestamp -p "test_*.py"   # Timestamp accuracy

# Development verification
uv run --no-sync --python 3.13 python utils/development_checker.py  # Quality checks

# Smoke tests
echo '{"session_id":"test123"}' | CLAUDE_HOOK_EVENT=Stop uv run --no-sync --python 3.13 python src/discord_notifier.py
uv run --no-sync --python 3.13 python -m py_compile src/*.py  # Syntax verification
```

### Error Prevention Systems

Automated Checks:
- UTC Timestamp Leak Detection: Prevents UTC timestamps in user-facing code
- Realtime Timestamp Validation: Verifies actual timestamp accuracy  
- Import Consistency Verification: Catches circular imports and missing dependencies
- Test Coverage Analysis: Ensures critical functionality has adequate testing

Development Workflow:
1. Write code with timestamp functionality
2. Run development checker (`python utils/development_checker.py`)
3. Fix any violations before proceeding
4. Test in real environment (not just mocked data)
5. Verify Discord output matches expected format and timezone
6. Commit only after all checks pass

### Known Issues Prevention

Timestamp Display Problems: 
- Previous Issue: Tests passed but actual Discord showed UTC times
- Solution: Mandatory realtime timestamp verification
- Prevention: Development checker catches UTC patterns in user-facing code

Testing Blind Spots:
- Previous Issue: Mock data tests missed actual implementation bugs  
- Solution: Real environment verification required for feature completion
- Prevention: Feature completion checklist enforces real testing

### Python Environment

The project uses Python 3.13+ features including:
- `TypeIs` for type guards
- `ReadOnly` for TypedDict fields  
- Other Python 3.13+ typing improvements

**NEVER test with system python3** which may be 3.12 or older:
```bash
# WRONG: python3 src/discord_notifier.py  
# RIGHT: uv run --no-sync --python 3.13 python src/discord_notifier.py
```

Testing with older Python versions will fail with import errors.

## Comprehensive Quality Assurance System

The project includes a comprehensive quality assurance system providing multi-layered validation for production-grade quality control.

### Enhanced Development Checker

The enhanced development checker integrates the original quality checks with comprehensive QA capabilities:

```bash
# Standard development checker (original functionality)
uv run --no-sync --python 3.13 python utils/development_checker.py

# Enhanced checker with comprehensive QA system
uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced

# Enhanced checker without comprehensive QA (fallback mode)
uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced --no-comprehensive
```

### Quality Assurance Components

#### 1. Quality Gates (4-Level Validation)

Quality gates provide progressive validation with increasing rigor:

```bash
# Level 1: Basic Quality Gate (syntax, imports, basic validation)
# Level 2: Functional Quality Gate (unit tests, functionality validation)  
# Level 3: Integration Quality Gate (integration tests, system validation)
# Level 4: Production Quality Gate (performance, security, deployment readiness)
```

#### 2. Category-Specific Checkers

Specialized checkers for different system components:

- Discord Integration Checker: API connectivity, authentication, rate limiting
- Content Processing Checker: Formatting accuracy, timestamp precision, prompt mixing detection
- Data Management Checker: Configuration safety, SQLite operations, session management
- Quality Validation Checker: Type safety, error handling, logging completeness
- Integration Control Checker: Hook integration, event dispatch, parallel processing

#### 3. Automation Checkers

Different automation levels for various development scenarios:

```bash
# Instant checker (fast feedback for development)
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/instant_checker.py

# Category checker (targeted validation by component)
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/category_checker.py

# Comprehensive checker (full system validation)
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/comprehensive_checker.py
```

#### 4. Specialized Validators

Targeted validators for specific quality concerns:

```bash
# Timestamp accuracy validation (critical for time display)
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/timestamp_accuracy_validator.py

# API response validation
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/api_response_validator.py

# Content accuracy validation  
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/content_accuracy_validator.py

# Security validation
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/security_validator.py
```

### Quality Assurance Test Categories

The comprehensive test suite is organized into specialized categories:

```bash
# Discord Integration Tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/discord_integration -p "test_*.py"

# Content Processing Tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/content_processing -p "test_*.py"

# Data Management Tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/data_management -p "test_*.py"

# Quality Validation Tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/quality_validation -p "test_*.py"

# Integration Control Tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/integration_control -p "test_*.py"

# End-to-End Tests
uv run --no-sync --python 3.13 python -m unittest discover -s tests/end_to_end -p "test_*.py"
```

### Quality Metrics and Reporting

The system provides detailed quality metrics and reporting:

- Quality Scores: Numerical quality assessment (0-100) for each component
- Execution Time Tracking: Performance metrics for all quality checks
- Issue Classification: Categorization of issues by severity (high/medium/low priority)
- Recommendation Engine: Automated suggestions for quality improvements
- Trend Analysis: Quality progression tracking over time

### CI/CD Integration

The quality assurance system integrates with CI/CD pipelines:

```bash
# CI/CD quality gate execution
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/cicd_integrator.py

# Generate quality reports for CI/CD
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/cicd_integrator.py --generate-reports

# Execute specific quality gates in CI/CD context
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/cicd_integrator.py --gate level1
```

### Configuration Management

Quality assurance behavior can be configured through multiple mechanisms:

1. **Configuration File**: `utils/development_checker_config.json`
2. **Environment Variables**: `DEVCHECKER_*` prefixed variables
3. **Command Line Arguments**: Runtime configuration overrides

```bash
# Create default configuration
uv run --no-sync --python 3.13 python utils/development_checker_config.py --create-default

# Show integration status
uv run --no-sync --python 3.13 python utils/development_checker_config.py --status

# Validate configuration
uv run --no-sync --python 3.13 python utils/development_checker_config.py --validate
```

### Best Practices for Quality Assurance

Pre-Commit Workflow:
1. Run standard development checker for quick validation
2. Run enhanced checker with comprehensive QA for critical changes
3. Execute category-specific tests for affected components
4. Verify timestamp accuracy for time-related changes
5. Generate quality report for documentation

Feature Development Workflow:
1. Implement feature with appropriate logging and error handling
2. Write comprehensive tests covering happy path and edge cases
3. Run relevant category checkers during development
4. Execute full quality gates before merge
5. Validate in real environment with actual Discord integration

Production Deployment Workflow:
1. Execute all quality gates (Level 1-4)
2. Run comprehensive system validation
3. Generate quality metrics report
4. Verify timestamp accuracy in production environment
5. Monitor quality trends post-deployment

### Troubleshooting Quality Issues

Common Quality Check Failures:

- UTC Timestamp Leaks: Check `src/formatters/` for direct UTC usage
- Import Consistency: Verify circular import dependencies
- Test Coverage: Ensure critical functionality has adequate test coverage
- Type Safety: Review runtime type validation implementations
- Performance: Analyze execution time metrics for bottlenecks

Quality Score Improvement:

- Score < 60: Address critical issues before proceeding
- Score 60-75: Acceptable but needs improvement
- Score 75-90: Good quality with minor issues
- Score > 90: Excellent quality ready for production

The comprehensive quality assurance system ensures production-grade reliability while maintaining development velocity through automated validation and clear quality metrics.