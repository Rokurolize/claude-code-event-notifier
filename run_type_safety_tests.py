#!/usr/bin/env python3
"""
Comprehensive test runner for Discord notifier type safety tests.

This script runs all type safety tests and provides a summary of results,
specifically focusing on verifying the configuration handling code's type safety.
"""

import sys
import unittest
import traceback
from pathlib import Path
from typing import Dict, List, Tuple

def run_test_suite(test_module_name: str) -> Tuple[bool, str, int, int]:
    """
    Run a specific test suite and return results.
    
    Returns:
        Tuple of (success, output, tests_run, failures)
    """
    try:
        # Import the test module
        test_module = __import__(test_module_name)
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Custom test runner to capture results
        runner = unittest.TextTestRunner(
            stream=sys.stdout,
            verbosity=2,
            buffer=True
        )
        
        result = runner.run(suite)
        
        # Calculate metrics
        tests_run = result.testsRun
        failures = len(result.failures) + len(result.errors)
        success = failures == 0
        
        # Generate output summary
        output_lines = []
        output_lines.append(f"Tests run: {tests_run}")
        output_lines.append(f"Failures: {len(result.failures)}")
        output_lines.append(f"Errors: {len(result.errors)}")
        
        if result.failures:
            output_lines.append("\nFAILURES:")
            for test, traceback_text in result.failures:
                output_lines.append(f"  {test}: {traceback_text}")
        
        if result.errors:
            output_lines.append("\nERRORS:")
            for test, traceback_text in result.errors:
                output_lines.append(f"  {test}: {traceback_text}")
        
        output = "\n".join(output_lines)
        return success, output, tests_run, failures
        
    except Exception as e:
        error_output = f"Failed to run {test_module_name}: {str(e)}\n{traceback.format_exc()}"
        return False, error_output, 0, 1


def main() -> None:
    """Run all type safety test suites and provide comprehensive results."""
    print("=" * 80)
    print("DISCORD NOTIFIER TYPE SAFETY TEST SUITE")
    print("=" * 80)
    print()
    
    # Define test suites to run
    test_suites = [
        ("test_config_type_safety", "Configuration Type Safety Tests"),
        ("test_runtime_type_validation", "Runtime Type Validation Tests"),
        ("test_type_guards_validation", "Type Guards and Validation Tests"),
    ]
    
    total_tests = 0
    total_failures = 0
    suite_results: List[Tuple[str, bool, str, int, int]] = []
    
    # Run each test suite
    for module_name, description in test_suites:
        print(f"Running {description}...")
        print("-" * 60)
        
        success, output, tests_run, failures = run_test_suite(module_name)
        suite_results.append((description, success, output, tests_run, failures))
        
        total_tests += tests_run
        total_failures += failures
        
        if success:
            print(f"✅ {description}: PASSED ({tests_run} tests)")
        else:
            print(f"❌ {description}: FAILED ({failures}/{tests_run} failed)")
            print(f"   Details: {output}")
        
        print()
    
    # Overall summary
    print("=" * 80)
    print("OVERALL RESULTS")
    print("=" * 80)
    
    success_count = sum(1 for _, success, _, _, _ in suite_results if success)
    total_suites = len(suite_results)
    
    print(f"Test Suites: {success_count}/{total_suites} passed")
    print(f"Total Tests: {total_tests}")
    print(f"Total Failures: {total_failures}")
    print()
    
    if total_failures == 0:
        print("🎉 ALL TYPE SAFETY TESTS PASSED!")
        print()
        print("Configuration handling code demonstrates:")
        print("  ✅ Proper TypedDict structure and inheritance")
        print("  ✅ Runtime type validation and coercion")
        print("  ✅ Graceful error handling and degradation")
        print("  ✅ Type guard functions work correctly")
        print("  ✅ Event data validation maintains type safety")
        print("  ✅ Environment variable parsing is type-safe")
        print("  ✅ Configuration precedence rules are enforced")
        print("  ✅ Edge cases and malformed data are handled")
        
        exit_code = 0
    else:
        print("❌ SOME TYPE SAFETY TESTS FAILED")
        print()
        print("Issues found in:")
        for description, success, output, tests_run, failures in suite_results:
            if not success:
                print(f"  • {description}: {failures} failures")
        
        print()
        print("Review the detailed output above to identify and fix type safety issues.")
        exit_code = 1
    
    print()
    print("=" * 80)
    
    # Detailed summary of what was tested
    print("TYPE SAFETY COVERAGE SUMMARY:")
    print()
    print("1. Configuration Type Definitions:")
    print("   - Config TypedDict completeness and structure")
    print("   - Inheritance from component TypedDicts")
    print("   - Literal type constraints (channel_type)")
    print("   - Proper handling of optional fields")
    print()
    print("2. Configuration Loading:")
    print("   - Return type correctness")
    print("   - Type casting safety (strings to booleans)")
    print("   - Invalid value handling")
    print("   - Environment variable type coercion")
    print("   - None value handling")
    print()
    print("3. Configuration Validation:")
    print("   - Validator input/output types")
    print("   - Credential validation logic")
    print("   - Thread configuration validation")
    print("   - Mention user ID validation")
    print()
    print("4. Runtime Type Safety:")
    print("   - Malformed configuration handling")
    print("   - Invalid type coercion scenarios")
    print("   - Edge case string values")
    print("   - Unicode and special character support")
    print("   - Error propagation and exception typing")
    print()
    print("5. Type Guards and Event Validation:")
    print("   - Event type identification")
    print("   - Tool-specific type guards")
    print("   - Event data structure validation")
    print("   - Tool input validation")
    print("   - Type guard integration with validators")
    print()
    print("6. Environment Variable Parsing:")
    print("   - Type-safe parsing of .env files")
    print("   - Malformed line handling")
    print("   - Quote stripping and value processing")
    print("   - I/O error handling")
    print("   - Encoding issue management")
    print()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()