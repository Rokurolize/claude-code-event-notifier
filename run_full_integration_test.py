#!/usr/bin/env python3
"""Complete integration test runner for Discord notification system.

This script runs the full send → receive → validate workflow to verify
that all Discord notifications are working correctly, including:
- Prompt mixing detection
- JST timestamp display
- Message content validation
- Error handling and recovery
"""

import json
import sys
from pathlib import Path

# Add src and utils to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from integration_tester import IntegrationTester
from src.utils.astolfo_logger import AstolfoLogger


def print_test_summary(report):
    """Print a beautiful test summary to console."""
    print("🎭" * 30)
    print("🎯 DISCORD INTEGRATION TEST RESULTS 🎯")
    print("🎭" * 30)
    
    # Basic stats
    print(f"\n📊 TEST EXECUTION SUMMARY:")
    print(f"   🏁 Test Run ID: {report['test_run_id']}")
    print(f"   ⏰ Start Time: {report['start_time']}")
    print(f"   🏁 End Time: {report['end_time']}")
    print(f"   📈 Total Scenarios: {report['total_scenarios']}")
    print(f"   ✅ Passed: {report['passed_scenarios']}")
    print(f"   ❌ Failed: {report['failed_scenarios']}")
    print(f"   🎯 Overall Success: {'YES! 🎉' if report['overall_success'] else 'NO 💥'}")
    
    # Individual test results
    print(f"\n📋 INDIVIDUAL TEST RESULTS:")
    for i, result in enumerate(report['test_results'], 1):
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"   {i}. {result['scenario_name']}: {status}")
        print(f"      Send: {'✅' if result['send_success'] else '❌'} | "
              f"Receive: {'✅' if result['receive_success'] else '❌'} | "
              f"Validate: {'✅' if result.get('validation_result', {}).get('success', False) else '❌'}")
        print(f"      Time: {result['execution_time_seconds']:.2f}s")
        
        if result['errors']:
            print(f"      ❌ Errors: {len(result['errors'])}")
            for error in result['errors'][:3]:  # Show first 3 errors
                print(f"         • {error}")
            if len(result['errors']) > 3:
                print(f"         ... and {len(result['errors']) - 3} more")
        
        if result['warnings']:
            print(f"      ⚠️ Warnings: {len(result['warnings'])}")
            for warning in result['warnings'][:2]:  # Show first 2 warnings
                print(f"         • {warning}")
        
        print()
    
    # Feature validation summary
    summary = report['summary']
    print(f"🔍 FEATURE VALIDATION RESULTS:")
    feature_val = summary['feature_validation']
    print(f"   📤 Send Success Rate: {feature_val['send_success_rate']:.1%}")
    print(f"   📥 Receive Success Rate: {feature_val['receive_success_rate']:.1%}")
    print(f"   ✅ Validation Success Rate: {feature_val['validation_success_rate']:.1%}")
    print(f"   ⚠️ Contamination Detection: {'✅ Working' if feature_val['contamination_detection_working'] else '❌ Not Working'}")
    print(f"   🕐 JST Timestamp: {'✅ Working' if feature_val['jst_timestamp_working'] else '❌ Not Working'}")
    
    # Performance stats
    exec_stats = summary['execution_statistics']
    print(f"\n⚡ PERFORMANCE STATISTICS:")
    print(f"   🏃 Total Execution Time: {exec_stats['total_execution_time']:.2f}s")
    print(f"   📊 Average Test Time: {exec_stats['average_execution_time']:.2f}s")
    print(f"   🚀 Fastest Test: {exec_stats['fastest_test']}")
    print(f"   🐌 Slowest Test: {exec_stats['slowest_test']}")
    
    # Error analysis
    error_analysis = summary['error_analysis']
    print(f"\n🔍 ERROR ANALYSIS:")
    print(f"   ❌ Total Errors: {error_analysis['total_errors']}")
    print(f"   ⚠️ Total Warnings: {error_analysis['total_warnings']}")
    
    if error_analysis['most_common_errors']:
        print(f"   🔥 Most Common Errors:")
        for error_msg, count in error_analysis['most_common_errors'][:3]:
            print(f"      • {error_msg}: {count} occurrences")
    
    print("\n🎭" * 30)
    
    if report['overall_success']:
        print("🎉 ALL TESTS PASSED! Discord notification system is working perfectly! ♡")
    else:
        print("💥 SOME TESTS FAILED! Please check the detailed report for issues.")
    
    print("🎭" * 30)


def main():
    """Run complete integration test suite."""
    logger = AstolfoLogger(__name__)
    
    print("🚀 Starting Complete Discord Integration Test Suite...")
    print("This will test: Send → Receive → Validate workflow")
    print("Features tested: Prompt mixing, JST timestamps, message validation")
    print()
    
    try:
        # Initialize tester
        logger.info("Initializing integration tester")
        tester = IntegrationTester()
        
        # Run comprehensive tests
        logger.info("Starting comprehensive test execution")
        report = tester.run_comprehensive_test()
        
        # Save detailed report
        report_path = tester.save_report(report)
        logger.info("Test report saved", report_path=report_path)
        
        # Print summary to console
        print_test_summary(report)
        
        # Additional analysis for debugging
        if not report['overall_success']:
            print(f"\n📄 DETAILED REPORT SAVED TO: {report_path}")
            print("Please review the detailed JSON report for complete error information.")
        
        # Exit with appropriate code
        sys.exit(0 if report['overall_success'] else 1)
        
    except Exception as e:
        logger.error("Integration test failed with exception", error=str(e))
        print(f"\n💥 TEST EXECUTION FAILED: {e}")
        print("Please check the configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()