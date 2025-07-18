# User-Level Development Standards

## Core Principles

- Start simple. Stay simple.
- Python code enforces strict type checking.
- **NEVER manually type timestamps** - Always use `date +"%Y-%m-%d-%H-%M-%S"` command to generate timestamps
- When creating document files, use the naming format `{timestamp(yyyy-MM-dd-HH-mm-ss)}-[descriptive name].md` to facilitate future file retrieval.
- You should code with the expectation of implementing detailed logging processes from the outset, to make later debugging by yourself easier.
- **Pure Python design philosophy** - Prioritize standard library solutions over external dependencies whenever possible.

## Localization and Global Development

- The user is Japanese and speaks Japanese.
- GitHub is a global platform, so source codes should be written in English.

## Python Development Standards

### Environment Requirements
- **Python 3.14+ Enforcement**: All Python projects must use Python 3.14 or higher to access revolutionary features (`TypeIs`, `ReadOnly`, `process_cpu_count()`, tail-call optimization, GIL-free execution)
- **Zero System Python**: Never use system `python3` which may be outdated; always use explicit version specification
- **Command Pattern**: `cd project_root && uv run --python 3.14 python` for all Python execution (context-independent execution)
- **Environment Contamination Prevention**: Avoid `--no-sync` flag to prevent contaminated environments from forcing older Python versions
- **Performance Revolution Awareness**: Python 3.14 delivers 30% performance improvement through tail-call interpreter optimization
- **GIL Liberation**: Enable parallel processing capabilities with `sys.set_gil_enabled(False)` for CPU-intensive tasks

### Type Safety Standards
- **Runtime Type Validation**: Implement TypeGuard functions for all external data inputs
- **TypedDict Everywhere**: Use TypedDict for all structured data, avoid generic dictionaries
- **Type Narrowing**: Leverage Python 3.14+ type narrowing with `TypeIs` for precise validation
- **ReadOnly Enforcement**: Use `ReadOnly` for configuration values and immutable data structures to prevent runtime modification
- **Mypy Integration**: Run `cd project_root && uv run --python 3.14 python -m mypy` for static type checking in all projects
- **Zero Fallback Policy**: Never use `typing_extensions` as fallback - maintain Pure Python 3.14+ design integrity
- **PEP 649 Optimization**: Leverage delayed annotation evaluation for 20% type checking performance improvement
- **Container CPU Detection**: Use `os.process_cpu_count()` instead of `os.cpu_count()` for accurate container resource detection

### Code Quality Standards
- **Ruff Integration**: Use `ruff check` and `ruff format` for linting and formatting
- **Zero Magic Numbers**: All numeric constants must be named variables with clear intent
- **Explicit Error Handling**: Never use bare `except:` clauses, always specify exception types
- **Import Organization**: Use absolute imports, group imports by standard/third-party/local

## Quality Assurance Patterns

### Development Workflow Standards
- **Pre-Commit Quality Gates**: Run quality checks before every commit
- **Real Environment Verification**: Test in actual deployment environment, not just mocks
- **Feature Completion Definition**: Features are complete only when all quality gates pass AND real environment verification succeeds

### Quality Gate Graduation Principles
- **Level 1**: Syntax correctness, critical errors only
- **Level 2**: Type safety, security vulnerabilities, import consistency
- **Level 3**: Code hygiene, style compliance, test coverage
- **Level 4**: Production readiness, performance, documentation completeness

### Error Prevention Systems
- **Automated Detection**: Implement automated checks for common failure patterns
- **Realtime Validation**: Verify critical functionality in real-time, not just at build time
- **UTC Leak Prevention**: Detect and prevent UTC timestamp exposure in user-facing interfaces
- **Dependency Verification**: Validate all imports and dependencies before deployment
- **Python 3.14 Syntax Compliance**: Detect and prevent PEP 765 violations (return/break/continue in finally blocks)
- **AST Compatibility Verification**: Ensure no usage of deprecated AST nodes (ast.Num, ast.Str, ast.Bytes, etc.)
- **Future Annotation Safety**: Prepare for `from __future__ import annotations` deprecation and PEP 649 transition

## Critical Learning Principles

### The Sacred Law: Error → Fix → Success → Documentation
**This principle is fundamental to all development work. Failure to follow this leads to infinite error repetition.**

#### The Absolute Process
1. **Error Occurs** → Something is wrong
2. **Attempt Fixes** → Try various solutions
3. **Success Achieved** → Find the correct method
4. **CRITICAL MOMENT**: **The successful method IS the "correct way"**
5. **MANDATORY**: **Document the successful method immediately in project memory**

#### Fatal Consequences of Non-Documentation
- Infinite repetition of the same errors
- Complete abandonment of learning capability
- Betrayal of developer progress
- Waste of precious development time

### Timestamp Automation: The Zero-Error Principle
**Manual timestamp entry is a cardinal sin in documentation creation.**

#### Mandatory Commands
```bash
# ALWAYS use this command for timestamp generation
date +"%Y-%m-%d-%H-%M-%S"

# NEVER manually type timestamps like "2025-01-16-14-30-00"
# This leads to typing errors and inconsistency
```

#### Helper Functions Integration
```bash
# Use existing helper functions when available
create_timestamped_doc "analysis-report" "Report content..."
mkdoc "findings" "Important findings..."
```

### Subagent Coordination Mastery
**Multiple subagents working in parallel create exponential capability amplification.**

#### Effective Subagent Distribution Patterns
1. **Analysis Subagents** - Architecture, Technology, Infrastructure analysis
2. **Implementation Subagents** - Backend, Frontend, Integration specialists  
3. **Quality Subagents** - Testing, Documentation, Review specialists
4. **Coordination Subagents** - Project management, Timeline, Resource optimization

#### Subagent Knowledge Transfer Requirements
- Each subagent must document findings in timestamped files
- Knowledge must be transferable to new Claude Code instances
- Implementation guides must be complete and actionable
- Cross-subagent integration must be explicitly designed

### Real-time Systems Development Expertise
**Python 3.14 enables revolutionary real-time capabilities with <5ms performance targets becoming achievable.**

#### Python 3.14 Performance Revolution
- **Tail-Call Optimization**: Up to 30% performance improvement in recursive and deep call chains
- **GIL-Free Parallel Processing**: `sys.set_gil_enabled(False)` for true multicore utilization (5.5x speedup measured)
- **Standard Library Optimization**: asyncio +10%, sqlite3 +25%, io +15%, json internal optimizations
- **Memory Efficiency**: 10-16% reduction in memory usage across Python objects

#### Core Technologies for Sub-5ms Processing
- **Server-Sent Events (SSE)** - Preferred over WebSocket for one-way real-time updates, now 15% faster with io improvements
- **Web Components** - Pure JavaScript ES2024+ without external frameworks
- **SQLite Performance** - 25% faster with Python 3.14 integration + latest SQLite engine
- **Parallel Processing** - `process_cpu_count()` + GIL-free execution for container-optimized parallelism
- **Asyncio Optimization** - 10% performance + 10% memory reduction in Python 3.14

#### Achievable Performance Standards (Python 3.14)
- **<5ms processing targets** - Now realistic with 30% base performance improvement
- **Real-time data pipelines** - Target processing: 8-12ms → 5-8ms (goal achievement range)
- **Concurrent connections** - 1,000 → 1,300 (+30% capacity with memory optimizations)
- **Zero external dependencies** - All optimizations from standard library
- **Container optimization** - Accurate CPU detection for optimal resource utilization

## Knowledge Base Management Pattern

### External Knowledge Organization
- **Knowledge Base Location**: `~/knowledge/` for cross-project reference patterns
- **Domain Organization**: Structure by technology domains (python/, security/, testing/, etc.)
- **Update Automation**: Maintain automated update scripts for knowledge repositories
- **Memory Integration**: Link project memory to knowledge base for pattern discovery

### Knowledge Base Principles
- **Problem-Solution Mapping**: Map specific development challenges to knowledge domains
- **Recall Triggers**: Document specific scenarios that warrant knowledge base consultation
- **Industry Standards**: Maintain connections to proven patterns and best practices
- **Evolution Tracking**: Update knowledge base as technologies and patterns evolve

### Memory Hierarchy
- **User Memory** (`~/.claude/CLAUDE.md`): Cross-project standards and patterns
- **Project Memory** (`./CLAUDE.md`): Project-specific implementation details
- **External Knowledge** (`~/knowledge/`): Industry standards and reference patterns
- **Session Context**: Current conversation and immediate development tasks

## Development Workflow Standards

### Command Execution Standards
- **Quality Check Integration**: Always run quality checks before commit/deployment
- **Environment Validation**: Verify correct Python version and dependencies using `cd project_root && uv run --python 3.14 python --version`
- **Test Coverage Requirements**: Maintain comprehensive test coverage for critical functionality
- **Documentation Synchronization**: Keep documentation in sync with code changes
- **Context-Independent Execution**: Always change to project directory before running Python commands to avoid path-related issues

### Best Practices for Project Setup
- **Hook Integration**: Implement development hooks for automated quality enforcement
- **Configuration Precedence**: Environment variables > .env file > default values
- **Logging Architecture**: Implement structured logging from project inception
- **Security by Default**: Apply security patterns from project start, not as afterthought

### Cross-Project Consistency
- **Naming Conventions**: Use consistent variable and function naming across projects
- **File Organization**: Maintain consistent project structure and module organization
- **Testing Patterns**: Apply consistent testing strategies across all Python projects
- **Quality Standards**: Use same quality gates and automation across projects

## Integration with Project Memory

Project-specific CLAUDE.md files should:
- Import these user-level standards via `@~/.claude/CLAUDE.md`
- Focus on project-specific implementation details
- Reference user-level patterns while implementing domain-specific solutions
- Maintain project-specific knowledge base domains while using general knowledge patterns

## Tool Configuration Standards

### Ruff Configuration
- Line length: Project-specific but consistent within project
- Import organization: Always sort imports
- Error suppression: Document all error suppressions with clear rationale

### MyPy Configuration
- Strict mode: Enable for all new projects
- Type checking: Require type annotations for all public functions
- Error handling: Treat type violations as errors, not warnings
- Command execution: Use `cd project_root && uv run --python 3.14 python -m mypy` for consistent environment

### Testing Standards
- Test organization: Mirror source code structure in tests
- Mock usage: Mock external dependencies, test real implementations
- Coverage requirements: Maintain high coverage for critical paths
- Integration testing: Always include real environment integration tests

This user-level memory serves as the foundation for consistent, high-quality Python development across all projects while allowing project-specific customization and implementation details.

## Advanced Development Principles (2025+)

### Pure Python 3.14+ Design Philosophy
**External dependencies are technical debt. Pure Python solutions are investments in long-term maintainability. Python 3.14 validates this philosophy with revolutionary performance gains.**

#### Core Tenets
- **Standard Library First**: Exhaust standard library possibilities before considering external dependencies
- **Zero Fallback Policy**: Never compromise design integrity with compatibility layers like `typing_extensions`
- **Future-Forward Design**: Use cutting-edge Python features to stay ahead of the curve
- **Container Optimization**: Leverage `process_cpu_count()` for accurate resource detection in containerized environments
- **Performance Revolution Adoption**: Leverage Python 3.14's 30% performance improvement as competitive advantage
- **GIL-Free Capability**: Design for parallel processing with `sys.set_gil_enabled(False)` in CPU-intensive scenarios

#### Python 3.14 Migration Imperatives
- **Syntax Compliance**: Eliminate PEP 765 violations (return/break/continue in finally blocks cause SyntaxError)
- **AST Modernization**: Replace deprecated AST nodes (ast.Num → ast.Constant) for tools that manipulate AST
- **Annotation Optimization**: Prepare for PEP 649 delayed evaluation benefits
- **Performance Validation**: Benchmark applications to confirm 20-30% performance improvements

### Modern Architecture Patterns
**Contemporary applications require real-time capabilities, microservice-ready design, and sub-millisecond performance.**

#### Real-time Application Standards
- **SSE over WebSocket**: Server-Sent Events for uni-directional real-time updates
- **Pure JavaScript ES2024+**: Web Components without external framework dependencies
- **SQLite Performance Optimization**: High-speed indexing and parallel processing
- **Context-Independent Deployment**: Applications that work regardless of execution context

### Crisis Prevention and Recovery
**Learn from past failures to prevent future catastrophes.**

#### Environment Contamination Prevention
- Never use `--no-sync` flag which can force older Python versions
- Always use explicit project directory changes: `cd project_root && uv run --python 3.14 python`
- Verify Python version before any significant development work: `uv run --python 3.14 python --version`
- Document successful environment configurations immediately
- **Python 3.14 Syntax Validation**: Run `find src -name "*.py" -exec uv run --python 3.14 python -m py_compile {} \;` to catch PEP 765 violations early
- **AST Compatibility Check**: Search for deprecated AST usage with `grep -r "ast\.\(Num\|Str\|Bytes\|NameConstant\|Ellipsis\)" --include="*.py" .`

#### Documentation Crisis Prevention
- Automate timestamp generation to prevent human error
- Implement the Sacred Law: Error → Fix → Success → Documentation
- Create implementation guides that new team members can follow independently
- Maintain user-level and project-level memory hierarchy

### Excellence Through Iteration
**Continuous improvement through rigorous learning and documentation.**

#### Knowledge Compound Growth
- Each project's lessons elevate user-level standards
- Successful patterns become automated workflows
- Crisis responses become prevention protocols
- Individual discoveries become team-wide capabilities

**The ultimate goal: Create development standards so robust that any Claude Code instance can achieve excellence by following them.**
