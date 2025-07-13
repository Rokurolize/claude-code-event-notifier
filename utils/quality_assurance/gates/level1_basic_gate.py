#!/usr/bin/env python3
"""Level 1 Basic Quality Gate.

This module implements the Level 1 Basic Quality Gate which provides:
- Essential syntax and import validation
- Basic type safety checks  
- Critical security vulnerability detection
- Basic functionality verification
- Fundamental error handling validation

Level 1 is the foundational gate that must pass before any higher-level testing.
"""

import asyncio
import json
import ast
import importlib.util
import sys
import traceback
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker
from utils.quality_assurance.validators.security_validator import SecurityValidator


# Level 1 Quality Gate types
@dataclass
class Level1ValidationResult:
    """Result of Level 1 basic validation."""
    gate_level: str = "Level1"
    validation_id: str = ""
    overall_status: str = "unknown"  # "pass", "fail", "warning"
    syntax_valid: bool = False
    imports_resolvable: bool = False
    basic_types_safe: bool = False
    critical_security_clear: bool = False
    basic_functionality_present: bool = False
    error_handling_minimal: bool = False
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    gate_requirements_met: Dict[str, bool] = field(default_factory=dict)
    next_gate_ready: bool = False
    remediation_actions: List[str] = field(default_factory=list)


@dataclass
class SyntaxValidationResult:
    """Result of syntax validation."""
    valid: bool
    ast_tree: Optional[ast.AST] = None
    syntax_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ImportValidationResult:
    """Result of import validation."""
    all_imports_valid: bool
    import_errors: List[str] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)
    circular_imports: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SyntaxValidator:
    """Validates Python syntax and AST structure."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        
    def validate_syntax(self, code: str, filename: str = "<string>") -> SyntaxValidationResult:
        """Validate Python syntax and generate AST."""
        try:
            # Parse the code into an AST
            ast_tree = ast.parse(code, filename=filename)
            
            # Perform basic AST validation
            warnings = self._validate_ast_structure(ast_tree)
            
            return SyntaxValidationResult(
                valid=True,
                ast_tree=ast_tree,
                syntax_errors=[],
                warnings=warnings
            )
            
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            return SyntaxValidationResult(
                valid=False,
                ast_tree=None,
                syntax_errors=[error_msg],
                warnings=[]
            )
        except Exception as e:
            error_msg = f"Unexpected error during syntax validation: {str(e)}"
            return SyntaxValidationResult(
                valid=False,
                ast_tree=None,
                syntax_errors=[error_msg],
                warnings=[]
            )
    
    def _validate_ast_structure(self, ast_tree: ast.AST) -> List[str]:
        """Validate AST structure for potential issues."""
        warnings = []
        
        # Check for dangerous constructs
        for node in ast.walk(ast_tree):
            # Check for eval/exec usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec']:
                        warnings.append(f"Dangerous function '{node.func.id}' used at line {node.lineno}")
            
            # Check for overly complex functions
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > 10:
                    warnings.append(f"High complexity function '{node.name}' at line {node.lineno} (complexity: {complexity})")
            
            # Check for very long lines (indication of poor structure)
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                if node.end_lineno and node.lineno:
                    if node.end_lineno - node.lineno > 50:
                        warnings.append(f"Very long code block starting at line {node.lineno}")
        
        return warnings
    
    def _calculate_cyclomatic_complexity(self, func_node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for node in ast.walk(func_node):
            # Decision points increase complexity
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.Return):
                # Multiple return points increase complexity
                complexity += 0.5
        
        return int(complexity)


class ImportValidator:
    """Validates import statements and dependencies."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.project_modules = self._discover_project_modules()
        
    def _discover_project_modules(self) -> Set[str]:
        """Discover available project modules."""
        project_modules = set()
        
        # Add project source modules
        src_path = project_root / "src"
        if src_path.exists():
            for py_file in src_path.rglob("*.py"):
                if py_file.name != "__init__.py":
                    # Convert file path to module name
                    rel_path = py_file.relative_to(src_path)
                    module_name = str(rel_path.with_suffix("")).replace("/", ".")
                    if module_name.startswith("src."):
                        module_name = module_name[4:]  # Remove 'src.' prefix
                    project_modules.add(f"src.{module_name}")
        
        return project_modules
    
    def validate_imports(self, ast_tree: ast.AST) -> ImportValidationResult:
        """Validate all import statements in the AST."""
        import_errors = []
        missing_dependencies = []
        circular_imports = []
        warnings = []
        
        # Extract all imports
        imports = self._extract_imports(ast_tree)
        
        # Validate each import
        for import_info in imports:
            module_name = import_info["module"]
            import_type = import_info["type"]
            line_number = import_info["line"]
            
            # Check if import is resolvable
            if not self._can_resolve_import(module_name):
                if module_name.startswith("src.") or module_name in self.project_modules:
                    import_errors.append(f"Project module '{module_name}' not found (line {line_number})")
                else:
                    # Check if it's a missing external dependency
                    if not self._is_stdlib_module(module_name):
                        missing_dependencies.append(module_name)
                        import_errors.append(f"External dependency '{module_name}' not available (line {line_number})")
            
            # Check for potential circular imports
            if self._might_be_circular(module_name):
                circular_imports.append(module_name)
                warnings.append(f"Potential circular import: '{module_name}' (line {line_number})")
        
        # Additional warnings
        if len(imports) > 20:
            warnings.append(f"High number of imports ({len(imports)}) - consider refactoring")
        
        return ImportValidationResult(
            all_imports_valid=len(import_errors) == 0,
            import_errors=import_errors,
            missing_dependencies=list(set(missing_dependencies)),
            circular_imports=circular_imports,
            warnings=warnings
        )
    
    def _extract_imports(self, ast_tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all import statements from AST."""
        imports = []
        
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "type": "import",
                        "line": node.lineno,
                        "alias": alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append({
                        "module": node.module,
                        "type": "from_import",
                        "line": node.lineno,
                        "names": [alias.name for alias in node.names]
                    })
        
        return imports
    
    def _can_resolve_import(self, module_name: str) -> bool:
        """Check if an import can be resolved."""
        try:
            # Try to find the module spec
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, ValueError, AttributeError):
            return False
    
    def _is_stdlib_module(self, module_name: str) -> bool:
        """Check if module is part of Python standard library."""
        # Common stdlib modules
        stdlib_modules = {
            'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'typing',
            'asyncio', 'threading', 'multiprocessing', 'sqlite3', 'unittest',
            'functools', 'itertools', 'collections', 'dataclasses', 're',
            'hashlib', 'hmac', 'secrets', 'base64', 'urllib', 'socket',
            'tempfile', 'shutil', 'traceback', 'logging', 'warnings'
        }
        
        root_module = module_name.split('.')[0]
        return root_module in stdlib_modules
    
    def _might_be_circular(self, module_name: str) -> bool:
        """Check if import might cause circular dependency."""
        # Simple heuristic: if importing from same package hierarchy
        if module_name.startswith("src."):
            # This is a simplified check - more sophisticated analysis would be needed
            # for comprehensive circular import detection
            return False
        return False


class BasicTypeValidator:
    """Validates basic type safety and usage."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        
    def validate_type_usage(self, ast_tree: ast.AST) -> Dict[str, Any]:
        """Validate basic type usage patterns."""
        validation = {
            "type_hints_present": False,
            "dangerous_type_usage": [],
            "missing_return_types": [],
            "untyped_parameters": [],
            "type_safety_score": 100.0,
            "recommendations": []
        }
        
        function_count = 0
        typed_function_count = 0
        
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1
                
                # Check function annotations
                has_return_type = node.returns is not None
                has_param_types = any(arg.annotation is not None for arg in node.args.args)
                
                if has_return_type or has_param_types:
                    typed_function_count += 1
                    validation["type_hints_present"] = True
                
                if not has_return_type and node.name != "__init__":
                    validation["missing_return_types"].append(f"Function '{node.name}' at line {node.lineno}")
                
                # Check for untyped parameters
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != "self":
                        validation["untyped_parameters"].append(f"Parameter '{arg.arg}' in function '{node.name}' at line {node.lineno}")
            
            # Check for dangerous type operations
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == "type":
                        validation["dangerous_type_usage"].append(f"Direct type() usage at line {node.lineno}")
                    elif node.func.id in ["hasattr", "getattr", "setattr"]:
                        validation["dangerous_type_usage"].append(f"Dynamic attribute access '{node.func.id}' at line {node.lineno}")
        
        # Calculate type safety score
        if function_count > 0:
            type_coverage = typed_function_count / function_count
            validation["type_safety_score"] = type_coverage * 100
        
        # Generate recommendations
        if validation["type_safety_score"] < 70:
            validation["recommendations"].append("Add type hints to improve type safety")
        if validation["missing_return_types"]:
            validation["recommendations"].append("Add return type annotations to functions")
        if validation["dangerous_type_usage"]:
            validation["recommendations"].append("Consider alternatives to dynamic type operations")
        
        return validation


class BasicFunctionalityValidator:
    """Validates basic functionality presence."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        
    def validate_functionality(self, ast_tree: ast.AST, file_type: str = "module") -> Dict[str, Any]:
        """Validate basic functionality patterns."""
        validation = {
            "has_main_functionality": False,
            "has_error_handling": False,
            "has_documentation": False,
            "function_count": 0,
            "class_count": 0,
            "complexity_issues": [],
            "functionality_score": 0.0
        }
        
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.FunctionDef):
                validation["function_count"] += 1
                
                # Check for main function or entry point
                if node.name in ["main", "run", "execute"]:
                    validation["has_main_functionality"] = True
                
                # Check for documentation
                if ast.get_docstring(node):
                    validation["has_documentation"] = True
                
                # Check for error handling
                for child in ast.walk(node):
                    if isinstance(child, (ast.Try, ast.Raise)):
                        validation["has_error_handling"] = True
                        break
            
            elif isinstance(node, ast.ClassDef):
                validation["class_count"] += 1
                
                # Check for class documentation
                if ast.get_docstring(node):
                    validation["has_documentation"] = True
            
            elif isinstance(node, ast.If):
                # Check for main guard
                if (isinstance(node.test, ast.Compare) and 
                    isinstance(node.test.left, ast.Name) and
                    node.test.left.id == "__name__"):
                    validation["has_main_functionality"] = True
        
        # Calculate functionality score
        score = 0
        if validation["function_count"] > 0 or validation["class_count"] > 0:
            score += 40  # Has content
        if validation["has_main_functionality"]:
            score += 30  # Has entry point
        if validation["has_error_handling"]:
            score += 20  # Has error handling
        if validation["has_documentation"]:
            score += 10  # Has documentation
        
        validation["functionality_score"] = score
        
        return validation


class Level1BasicQualityGate(BaseQualityChecker):
    """Level 1 Basic Quality Gate implementation."""
    
    def __init__(self):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.syntax_validator = SyntaxValidator()
        self.import_validator = ImportValidator()
        self.type_validator = BasicTypeValidator()
        self.functionality_validator = BasicFunctionalityValidator()
        self.security_validator = SecurityValidator()
        
        # Level 1 requirements
        self.requirements = {
            "syntax_valid": True,
            "imports_resolvable": True,
            "no_critical_security": True,
            "basic_functionality": 40.0,  # Minimum functionality score
            "min_type_safety": 30.0,  # Minimum type safety score
        }
    
    async def validate_file(self, file_path: str) -> Level1ValidationResult:
        """Validate a single file through Level 1 gate."""
        validation_id = f"level1_{int(datetime.now().timestamp() * 1000)}"
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return await self.validate_code(content, file_path, validation_id)
            
        except Exception as e:
            return Level1ValidationResult(
                validation_id=validation_id,
                overall_status="fail",
                validation_errors=[f"Failed to read file: {str(e)}"]
            )
    
    async def validate_code(self, code: str, filename: str = "<string>", validation_id: Optional[str] = None) -> Level1ValidationResult:
        """Validate code through Level 1 gate."""
        if not validation_id:
            validation_id = f"level1_{int(datetime.now().timestamp() * 1000)}"
        
        result = Level1ValidationResult(validation_id=validation_id)
        
        # Step 1: Syntax validation
        syntax_result = self.syntax_validator.validate_syntax(code, filename)
        result.syntax_valid = syntax_result.valid
        
        if not syntax_result.valid:
            result.validation_errors.extend(syntax_result.syntax_errors)
            result.overall_status = "fail"
            result.remediation_actions.append("Fix syntax errors before proceeding")
            return result
        
        if syntax_result.warnings:
            result.validation_warnings.extend(syntax_result.warnings)
        
        # Step 2: Import validation
        import_result = self.import_validator.validate_imports(syntax_result.ast_tree)
        result.imports_resolvable = import_result.all_imports_valid
        
        if not import_result.all_imports_valid:
            result.validation_errors.extend(import_result.import_errors)
        
        if import_result.warnings:
            result.validation_warnings.extend(import_result.warnings)
        
        # Step 3: Basic type safety
        type_result = self.type_validator.validate_type_usage(syntax_result.ast_tree)
        result.basic_types_safe = type_result["type_safety_score"] >= self.requirements["min_type_safety"]
        
        if type_result["dangerous_type_usage"]:
            result.validation_warnings.extend([
                f"Dangerous type usage: {usage}" for usage in type_result["dangerous_type_usage"]
            ])
        
        # Step 4: Critical security validation
        security_result = await self.security_validator.validate_security_comprehensive(code, "source_code")
        result.critical_security_clear = security_result.security_level not in ["critical", "danger"]
        
        if not result.critical_security_clear:
            result.validation_errors.extend([
                f"Critical security issue: {vuln}" for vuln in security_result.vulnerabilities_detected
            ])
        
        # Step 5: Basic functionality validation
        functionality_result = self.functionality_validator.validate_functionality(syntax_result.ast_tree)
        result.basic_functionality_present = functionality_result["functionality_score"] >= self.requirements["basic_functionality"]
        result.error_handling_minimal = functionality_result["has_error_handling"]
        
        # Step 6: Calculate overall quality score
        score_components = {
            "syntax": 100 if result.syntax_valid else 0,
            "imports": 100 if result.imports_resolvable else 50,
            "types": type_result["type_safety_score"],
            "security": security_result.security_score,
            "functionality": functionality_result["functionality_score"]
        }
        
        result.quality_score = sum(score_components.values()) / len(score_components)
        
        # Step 7: Check gate requirements
        result.gate_requirements_met = {
            "syntax_valid": result.syntax_valid,
            "imports_resolvable": result.imports_resolvable,
            "no_critical_security": result.critical_security_clear,
            "basic_functionality": result.basic_functionality_present,
            "min_type_safety": result.basic_types_safe
        }
        
        # Step 8: Determine overall status
        if all(result.gate_requirements_met.values()):
            result.overall_status = "pass"
            result.next_gate_ready = True
        elif result.syntax_valid and result.imports_resolvable and result.critical_security_clear:
            result.overall_status = "warning"
            result.next_gate_ready = False
        else:
            result.overall_status = "fail"
            result.next_gate_ready = False
        
        # Step 9: Generate remediation actions
        if not result.syntax_valid:
            result.remediation_actions.append("Fix all syntax errors")
        if not result.imports_resolvable:
            result.remediation_actions.append("Resolve import errors and missing dependencies")
        if not result.critical_security_clear:
            result.remediation_actions.append("Address critical security vulnerabilities")
        if not result.basic_functionality_present:
            result.remediation_actions.append("Implement basic functionality (main function, classes, or meaningful operations)")
        if not result.basic_types_safe:
            result.remediation_actions.append("Add type hints to improve type safety")
        if not result.error_handling_minimal:
            result.remediation_actions.append("Add basic error handling (try/except blocks)")
        
        return result
    
    async def validate_project(self, project_path: str = None) -> Dict[str, Any]:
        """Validate entire project through Level 1 gate."""
        if not project_path:
            project_path = str(project_root)
        
        project_validation = {
            "validation_id": f"level1_project_{int(datetime.now().timestamp() * 1000)}",
            "project_path": project_path,
            "total_files": 0,
            "passed_files": 0,
            "failed_files": 0,
            "warning_files": 0,
            "overall_status": "unknown",
            "file_results": {},
            "summary": {},
            "project_ready_for_level2": False
        }
        
        # Find Python files to validate
        project_path_obj = Path(project_path)
        python_files = list(project_path_obj.rglob("*.py"))
        
        # Filter out test files and __pycache__ for Level 1
        python_files = [
            f for f in python_files 
            if not any(part.startswith('.') for part in f.parts) and
               '__pycache__' not in str(f) and
               not str(f).endswith('_test.py')
        ]
        
        project_validation["total_files"] = len(python_files)
        
        # Validate each file
        for py_file in python_files:
            try:
                file_result = await self.validate_file(str(py_file))
                project_validation["file_results"][str(py_file)] = file_result
                
                if file_result.overall_status == "pass":
                    project_validation["passed_files"] += 1
                elif file_result.overall_status == "fail":
                    project_validation["failed_files"] += 1
                else:
                    project_validation["warning_files"] += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to validate {py_file}: {str(e)}")
                project_validation["failed_files"] += 1
        
        # Calculate overall project status
        if project_validation["total_files"] > 0:
            pass_rate = project_validation["passed_files"] / project_validation["total_files"]
            fail_rate = project_validation["failed_files"] / project_validation["total_files"]
            
            if pass_rate >= 0.9:
                project_validation["overall_status"] = "pass"
                project_validation["project_ready_for_level2"] = True
            elif fail_rate < 0.3:
                project_validation["overall_status"] = "warning"
                project_validation["project_ready_for_level2"] = False
            else:
                project_validation["overall_status"] = "fail"
                project_validation["project_ready_for_level2"] = False
        
        # Generate summary
        project_validation["summary"] = {
            "pass_rate": project_validation["passed_files"] / max(1, project_validation["total_files"]),
            "average_quality_score": self._calculate_average_quality_score(project_validation["file_results"]),
            "most_common_issues": self._identify_common_issues(project_validation["file_results"]),
            "critical_failures": self._identify_critical_failures(project_validation["file_results"])
        }
        
        return project_validation
    
    def _calculate_average_quality_score(self, file_results: Dict[str, Level1ValidationResult]) -> float:
        """Calculate average quality score across all files."""
        if not file_results:
            return 0.0
        
        total_score = sum(result.quality_score for result in file_results.values())
        return total_score / len(file_results)
    
    def _identify_common_issues(self, file_results: Dict[str, Level1ValidationResult]) -> List[str]:
        """Identify most common issues across files."""
        issue_counts = {}
        
        for result in file_results.values():
            for error in result.validation_errors:
                issue_type = error.split(':')[0]  # Get issue type prefix
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
            
            for warning in result.validation_warnings:
                issue_type = warning.split(':')[0]
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        # Return top 5 most common issues
        return sorted(issue_counts.keys(), key=lambda x: issue_counts[x], reverse=True)[:5]
    
    def _identify_critical_failures(self, file_results: Dict[str, Level1ValidationResult]) -> List[str]:
        """Identify critical failures that block progression."""
        critical_failures = []
        
        for filename, result in file_results.values():
            if result.overall_status == "fail":
                if not result.syntax_valid:
                    critical_failures.append(f"Syntax errors in {filename}")
                if not result.critical_security_clear:
                    critical_failures.append(f"Critical security issues in {filename}")
        
        return critical_failures
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check Level 1 gate quality and readiness."""
        return {
            "gate_level": "Level1",
            "gate_purpose": "Basic syntax, imports, and critical security validation",
            "requirements": self.requirements,
            "ready_for_validation": True,
            "estimated_validation_time": "1-3 minutes for full project"
        }