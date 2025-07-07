#!/usr/bin/env python3
"""
Simple validation script for JSON type handling patterns.
This checks for common type safety issues without requiring external tools.
"""

import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class JSONTypeChecker:
    """Checks for JSON type handling issues in Python code."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.json_loads_calls: Set[Tuple[str, int]] = set()
        self.json_dumps_calls: Set[Tuple[str, int]] = set()
        self.any_annotations: Set[Tuple[str, int]] = set()
        
    def check_file(self, file_path: Path) -> None:
        """Check a single Python file for JSON type issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            self._analyze_tree(tree, file_path)
            
        except Exception as e:
            self.issues.append({
                'file': str(file_path),
                'line': 0,
                'type': 'parse_error',
                'message': f"Failed to parse file: {e}"
            })
    
    def _analyze_tree(self, tree: ast.AST, file_path: Path) -> None:
        """Analyze AST tree for JSON type issues."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self._check_json_call(node, file_path)
            elif isinstance(node, ast.AnnAssign):
                self._check_type_annotation(node, file_path)
            elif isinstance(node, ast.FunctionDef):
                self._check_function_def(node, file_path)
    
    def _check_json_call(self, node: ast.Call, file_path: Path) -> None:
        """Check json.loads() and json.dumps() calls."""
        if (isinstance(node.func, ast.Attribute) and 
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'json'):
            
            line_no = node.lineno
            if node.func.attr == 'loads':
                self.json_loads_calls.add((str(file_path), line_no))
                # Check if result is immediately cast or validated
                self._check_json_loads_usage(node, file_path, line_no)
            elif node.func.attr == 'dumps':
                self.json_dumps_calls.add((str(file_path), line_no))
    
    def _check_json_loads_usage(self, node: ast.Call, file_path: Path, line_no: int) -> None:
        """Check how json.loads() result is used."""
        # This is a simplified check - in practice, you'd need more context
        # to determine if the result is properly validated
        self.issues.append({
            'file': str(file_path),
            'line': line_no,
            'type': 'json_loads_any',
            'message': 'json.loads() returns Any - consider adding type validation',
            'severity': 'info'
        })
    
    def _check_type_annotation(self, node: ast.AnnAssign, file_path: Path) -> None:
        """Check type annotations for Any usage."""
        if self._contains_any_annotation(node.annotation):
            self.any_annotations.add((str(file_path), node.lineno))
    
    def _check_function_def(self, node: ast.FunctionDef, file_path: Path) -> None:
        """Check function definitions for JSON-related patterns."""
        # Check for functions that handle JSON without proper typing
        if any(self._is_json_related_name(name) for name in self._get_function_names(node)):
            if not node.returns:
                self.issues.append({
                    'file': str(file_path),
                    'line': node.lineno,
                    'type': 'json_function_no_return_type',
                    'message': f"JSON-related function '{node.name}' lacks return type annotation",
                    'severity': 'warning'
                })
    
    def _contains_any_annotation(self, annotation: ast.AST) -> bool:
        """Check if annotation contains Any type."""
        if isinstance(annotation, ast.Name):
            return annotation.id == 'Any'
        elif isinstance(annotation, ast.Attribute):
            return annotation.attr == 'Any'
        elif isinstance(annotation, ast.Subscript):
            return self._contains_any_annotation(annotation.value)
        return False
    
    def _is_json_related_name(self, name: str) -> bool:
        """Check if name suggests JSON handling."""
        json_keywords = ['json', 'parse', 'load', 'dump', 'serialize', 'deserialize']
        return any(keyword in name.lower() for keyword in json_keywords)
    
    def _get_function_names(self, node: ast.FunctionDef) -> List[str]:
        """Get names used in function (simplified)."""
        names = [node.name]
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.append(child.id)
        return names
    
    def generate_report(self) -> str:
        """Generate a report of findings."""
        report = []
        report.append("JSON Type Checking Report")
        report.append("=" * 50)
        
        if not self.issues:
            report.append("✓ No major JSON type issues found")
        else:
            report.append(f"Found {len(self.issues)} potential issues:\n")
            
            for issue in sorted(self.issues, key=lambda x: (x['file'], x['line'])):
                severity = issue.get('severity', 'warning')
                symbol = "⚠️" if severity == 'warning' else "ℹ️"
                report.append(f"{symbol} {issue['file']}:{issue['line']}")
                report.append(f"   {issue['message']}")
                report.append("")
        
        report.append("\nSummary:")
        report.append(f"- json.loads() calls: {len(self.json_loads_calls)}")
        report.append(f"- json.dumps() calls: {len(self.json_dumps_calls)}")
        report.append(f"- Any annotations: {len(self.any_annotations)}")
        
        return "\n".join(report)


def main():
    """Main entry point."""
    checker = JSONTypeChecker()
    
    # Check main source files
    src_files = [
        Path("src/discord_notifier.py"),
        Path("configure_hooks.py"),
        Path("src/type_guards.py"),
        Path("src/settings_types.py"),
    ]
    
    for file_path in src_files:
        if file_path.exists():
            print(f"Checking {file_path}...")
            checker.check_file(file_path)
        else:
            print(f"Warning: {file_path} not found")
    
    # Generate and display report
    report = checker.generate_report()
    print("\n" + report)
    
    # Check if configuration files exist
    print("\nConfiguration Files:")
    config_files = [
        Path("pyproject.toml"),
        Path("mypy.ini"),
        Path(".mypy.ini"),
        Path("setup.cfg"),
    ]
    
    for config_file in config_files:
        if config_file.exists():
            print(f"✓ {config_file} exists")
        else:
            print(f"✗ {config_file} not found")


if __name__ == "__main__":
    main()