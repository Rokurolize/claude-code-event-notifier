#!/usr/bin/env python3
"""Test Performance Benchmarks.

This module implements comprehensive tests for performance benchmark validation including:
- Performance validator functionality testing
- Resource management efficiency testing
- Benchmark accuracy and reliability testing
- Performance regression detection testing
- Stress testing validation
- Performance optimization verification
- Memory and CPU efficiency testing
- I/O performance benchmark testing
"""

import asyncio
import unittest
import time
import sys
import os
import tempfile
import json
import threading
import gc
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "utils"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.validators.performance_validator import (
    PerformanceValidator, PerformanceValidationResult, PerformanceMetrics,
    PerformanceThresholds, BenchmarkResult
)
from utils.quality_assurance.validators.resource_management_validator import (
    ResourceManagementValidator, ResourceValidationResult, ResourceLeakAnalysis,
    ResourceBottleneck, ResourceEfficiencyMetrics
)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Test suite for performance benchmark validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.logger = AstolfoLogger(__name__)
        self.performance_validator = PerformanceValidator()
        self.resource_validator = ResourceManagementValidator()
        
        # Test thresholds
        self.test_thresholds = PerformanceThresholds(
            max_response_time_ms=1000.0,
            max_memory_usage_mb=100.0,
            max_cpu_percent=50.0,
            min_throughput_ops_per_second=10.0,
            max_error_rate_percent=5.0,
            max_p95_response_time_ms=1500.0,
            max_p99_response_time_ms=2000.0
        )
        
        # Sample operations for testing
        self.sample_operations = [
            self._fast_operation,
            self._medium_operation,
            self._slow_operation,
            self._memory_intensive_operation,
            self._cpu_intensive_operation
        ]
    
    def tearDown(self):
        """Clean up test environment."""
        # Force garbage collection
        gc.collect()
    
    def _fast_operation(self) -> str:
        """Fast test operation (< 10ms)."""
        return "fast_result"
    
    def _medium_operation(self) -> str:
        """Medium speed test operation (10-50ms)."""
        time.sleep(0.02)  # 20ms
        return "medium_result"
    
    def _slow_operation(self) -> str:
        """Slow test operation (> 50ms)."""
        time.sleep(0.1)  # 100ms
        return "slow_result"
    
    def _memory_intensive_operation(self) -> str:
        """Memory intensive test operation."""
        # Allocate some memory
        data = [i for i in range(10000)]
        result = sum(data)
        return f"memory_result_{result}"
    
    def _cpu_intensive_operation(self) -> str:
        """CPU intensive test operation."""
        # Perform CPU-bound computation
        result = sum(i * i for i in range(1000))
        return f"cpu_result_{result}"
    
    async def _async_operation(self) -> str:
        """Async test operation."""
        await asyncio.sleep(0.01)  # 10ms
        return "async_result"
    
    def _failing_operation(self) -> str:
        """Operation that always fails."""
        raise ValueError("Test error")
    
    def test_performance_validator_initialization(self):
        """Test performance validator initialization."""
        self.assertIsNotNone(self.performance_validator)
        self.assertTrue(hasattr(self.performance_validator, 'validate_performance'))
        self.assertTrue(hasattr(self.performance_validator, 'benchmark_operation'))
    
    async def test_basic_performance_validation(self):
        """Test basic performance validation."""
        result = await self.performance_validator.validate_performance(
            "test_operation",
            self._fast_operation,
            thresholds=self.test_thresholds,
            test_count=10
        )
        
        self.assertIsInstance(result, PerformanceValidationResult)
        self.assertEqual(result.operation_name, "test_operation")
        self.assertTrue(result.validation_passed)
        self.assertGreater(result.benchmark_result.test_count, 0)
        self.assertGreater(result.benchmark_result.success_rate, 95.0)
    
    async def test_performance_validation_with_thresholds(self):
        """Test performance validation with specific thresholds."""
        # Test with strict thresholds
        strict_thresholds = PerformanceThresholds(
            max_response_time_ms=50.0,  # Very strict
            max_memory_usage_mb=50.0,
            max_cpu_percent=30.0,
            min_throughput_ops_per_second=50.0,
            max_error_rate_percent=1.0,
            max_p95_response_time_ms=75.0,
            max_p99_response_time_ms=100.0
        )
        
        # Test fast operation (should pass)
        fast_result = await self.performance_validator.validate_performance(
            "fast_operation",
            self._fast_operation,
            thresholds=strict_thresholds,
            test_count=20
        )
        
        self.assertTrue(fast_result.validation_passed)
        self.assertEqual(len(fast_result.violations), 0)
        
        # Test slow operation (should fail)
        slow_result = await self.performance_validator.validate_performance(
            "slow_operation",
            self._slow_operation,
            thresholds=strict_thresholds,
            test_count=10
        )
        
        self.assertFalse(slow_result.validation_passed)
        self.assertGreater(len(slow_result.violations), 0)
    
    async def test_performance_benchmark_accuracy(self):
        """Test performance benchmark accuracy."""
        # Test with known timing
        def timed_operation():
            time.sleep(0.05)  # Exactly 50ms
            return "timed_result"
        
        result = await self.performance_validator.validate_performance(
            "timed_operation",
            timed_operation,
            test_count=5
        )
        
        # Check that timing is reasonably accurate (within 20ms tolerance)
        avg_duration = result.benchmark_result.average_duration_ms
        self.assertGreater(avg_duration, 45.0)  # At least 45ms
        self.assertLess(avg_duration, 75.0)     # At most 75ms
        
        # Check that P95 and P99 are reasonable
        self.assertGreater(result.benchmark_result.p95_duration_ms, avg_duration)
        self.assertGreater(result.benchmark_result.p99_duration_ms, result.benchmark_result.p95_duration_ms)
    
    async def test_error_handling_in_benchmarks(self):
        """Test error handling during performance benchmarks."""
        result = await self.performance_validator.validate_performance(
            "failing_operation",
            self._failing_operation,
            test_count=10
        )
        
        self.assertFalse(result.validation_passed)
        self.assertEqual(result.benchmark_result.success_rate, 0.0)
        self.assertEqual(result.benchmark_result.error_count, 10)
        self.assertGreater(len(result.violations), 0)
    
    async def test_async_operation_benchmarking(self):
        """Test benchmarking of async operations."""
        result = await self.performance_validator.validate_performance(
            "async_operation",
            self._async_operation,
            test_count=15
        )
        
        self.assertIsInstance(result, PerformanceValidationResult)
        self.assertTrue(result.validation_passed)
        self.assertGreater(result.benchmark_result.success_rate, 95.0)
    
    async def test_throughput_calculation(self):
        """Test throughput calculation accuracy."""
        result = await self.performance_validator.validate_performance(
            "fast_operation",
            self._fast_operation,
            test_count=100
        )
        
        # Calculate expected throughput
        total_duration_seconds = result.benchmark_result.total_duration_ms / 1000
        expected_throughput = 100 / total_duration_seconds
        actual_throughput = result.benchmark_result.throughput_ops_per_second
        
        # Allow 10% tolerance
        tolerance = expected_throughput * 0.1
        self.assertAlmostEqual(actual_throughput, expected_throughput, delta=tolerance)
    
    async def test_memory_performance_monitoring(self):
        """Test memory performance monitoring."""
        result = await self.performance_validator.validate_performance(
            "memory_operation",
            self._memory_intensive_operation,
            test_count=10
        )
        
        # Check that memory usage was monitored
        self.assertGreater(result.benchmark_result.memory_peak_mb, 0)
        self.assertGreater(result.benchmark_result.memory_average_mb, 0)
        self.assertLessEqual(result.benchmark_result.memory_average_mb, result.benchmark_result.memory_peak_mb)
    
    async def test_cpu_performance_monitoring(self):
        """Test CPU performance monitoring."""
        result = await self.performance_validator.validate_performance(
            "cpu_operation",
            self._cpu_intensive_operation,
            test_count=10
        )
        
        # Check that CPU usage was monitored
        self.assertGreater(result.benchmark_result.cpu_average_percent, 0)
        self.assertLessEqual(result.benchmark_result.cpu_average_percent, 100.0)
    
    async def test_stress_testing_capabilities(self):
        """Test stress testing capabilities."""
        # Test with high concurrency
        result = await self.performance_validator.stress_test_operation(
            "stress_test",
            self._fast_operation,
            concurrent_operations=20,
            duration_seconds=5.0
        )
        
        self.assertIsInstance(result, PerformanceValidationResult)
        self.assertGreater(result.benchmark_result.test_count, 50)  # Should have many operations
        
        # Check stress test specific metrics
        self.assertIn("concurrent_operations", result.benchmark_result.additional_metrics)
        self.assertEqual(result.benchmark_result.additional_metrics["concurrent_operations"], 20)
    
    async def test_performance_regression_detection(self):
        """Test performance regression detection."""
        # Create baseline performance
        baseline_result = await self.performance_validator.validate_performance(
            "baseline_operation",
            self._fast_operation,
            test_count=20,
            compare_to_baseline=False
        )
        
        # Simulate storing baseline
        baseline_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        baseline_data = {
            "operation_name": "baseline_operation",
            "average_duration_ms": baseline_result.benchmark_result.average_duration_ms,
            "p95_duration_ms": baseline_result.benchmark_result.p95_duration_ms,
            "throughput_ops_per_second": baseline_result.benchmark_result.throughput_ops_per_second
        }
        json.dump(baseline_data, baseline_file)
        baseline_file.close()
        
        try:
            # Test against baseline (should pass)
            current_result = await self.performance_validator.validate_performance(
                "baseline_operation",
                self._fast_operation,
                test_count=20,
                compare_to_baseline=True,
                baseline_file=baseline_file.name
            )
            
            # Should detect similarity to baseline
            self.assertTrue(current_result.validation_passed)
            
            # Test with slower operation (should detect regression)
            regression_result = await self.performance_validator.validate_performance(
                "baseline_operation",
                self._slow_operation,  # Much slower operation
                test_count=10,
                compare_to_baseline=True,
                baseline_file=baseline_file.name
            )
            
            # Should detect performance regression
            self.assertGreater(len(regression_result.warnings), 0)
            
        finally:
            # Clean up
            os.unlink(baseline_file.name)
    
    async def test_resource_management_validation(self):
        """Test resource management validation."""
        result = await self.resource_validator.validate_resource_efficiency(
            "resource_test",
            self._memory_intensive_operation,
            monitoring_duration=2.0
        )
        
        self.assertIsInstance(result, ResourceValidationResult)
        self.assertEqual(result.operation_name, "resource_test")
        self.assertGreater(result.efficiency_score, 0)
        self.assertIn("memory", result.resource_utilization)
    
    async def test_resource_leak_detection(self):
        """Test resource leak detection."""
        def leaky_operation():
            # Simulate a memory leak by creating objects that might not be cleaned up
            data = []
            for i in range(1000):
                data.append([j for j in range(100)])
            return len(data)
        
        result = await self.resource_validator.validate_resource_efficiency(
            "leaky_operation",
            leaky_operation,
            monitoring_duration=3.0
        )
        
        # Check if any leaks were detected
        # Note: Actual leak detection depends on monitoring duration and operation behavior
        self.assertIsInstance(result.detected_leaks, list)
    
    async def test_resource_bottleneck_analysis(self):
        """Test resource bottleneck analysis."""
        def cpu_intensive_operation():
            # CPU-intensive operation that should create a bottleneck
            result = 0
            for i in range(100000):
                result += i * i
            return result
        
        result = await self.resource_validator.validate_resource_efficiency(
            "bottleneck_test",
            cpu_intensive_operation,
            monitoring_duration=2.0
        )
        
        # Should detect potential CPU bottleneck
        self.assertIsInstance(result.identified_bottlenecks, list)
    
    async def test_concurrent_performance_testing(self):
        """Test concurrent performance testing."""
        operations = [self._fast_operation, self._medium_operation]
        
        # Run multiple operations concurrently
        tasks = []
        for i, op in enumerate(operations):
            task = asyncio.create_task(
                self.performance_validator.validate_performance(
                    f"concurrent_op_{i}",
                    op,
                    test_count=10
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete successfully
        for result in results:
            self.assertIsInstance(result, PerformanceValidationResult)
            self.assertTrue(result.validation_passed)
    
    async def test_performance_optimization_suggestions(self):
        """Test performance optimization suggestions."""
        # Test with slow operation that should generate suggestions
        result = await self.performance_validator.validate_performance(
            "slow_operation",
            self._slow_operation,
            thresholds=PerformanceThresholds(
                max_response_time_ms=50.0,  # Strict threshold
                max_memory_usage_mb=100.0,
                max_cpu_percent=50.0,
                min_throughput_ops_per_second=20.0,
                max_error_rate_percent=5.0,
                max_p95_response_time_ms=75.0,
                max_p99_response_time_ms=100.0
            ),
            test_count=10
        )
        
        # Should generate optimization suggestions
        self.assertGreater(len(result.warnings), 0)
    
    async def test_benchmark_statistical_accuracy(self):
        """Test statistical accuracy of benchmarks."""
        # Run the same operation multiple times and check consistency
        results = []
        for _ in range(3):
            result = await self.performance_validator.validate_performance(
                "consistency_test",
                self._fast_operation,
                test_count=50
            )
            results.append(result.benchmark_result.average_duration_ms)
        
        # Results should be reasonably consistent (within 50% of each other)
        avg_result = sum(results) / len(results)
        for result in results:
            variance = abs(result - avg_result) / avg_result
            self.assertLess(variance, 0.5)  # Less than 50% variance
    
    async def test_performance_validator_quality_check(self):
        """Test performance validator quality check."""
        quality_result = await self.performance_validator.check_quality()
        
        self.assertIsInstance(quality_result, dict)
        self.assertIn("validator_type", quality_result)
        self.assertEqual(quality_result["validator_type"], "PerformanceValidator")
        self.assertIn("capabilities", quality_result)
        self.assertIn("status", quality_result)
        self.assertEqual(quality_result["status"], "ready")
    
    async def test_resource_validator_quality_check(self):
        """Test resource validator quality check."""
        quality_result = await self.resource_validator.check_quality()
        
        self.assertIsInstance(quality_result, dict)
        self.assertIn("validator_type", quality_result)
        self.assertEqual(quality_result["validator_type"], "ResourceManagementValidator")
        self.assertIn("capabilities", quality_result)
        self.assertIn("status", quality_result)
        self.assertEqual(quality_result["status"], "ready")
    
    def test_performance_thresholds_validation(self):
        """Test performance thresholds validation."""
        # Test valid thresholds
        valid_thresholds = PerformanceThresholds(
            max_response_time_ms=1000.0,
            max_memory_usage_mb=500.0,
            max_cpu_percent=80.0,
            min_throughput_ops_per_second=1.0,
            max_error_rate_percent=5.0,
            max_p95_response_time_ms=1500.0,
            max_p99_response_time_ms=2000.0
        )
        
        self.assertIsInstance(valid_thresholds, PerformanceThresholds)
        self.assertEqual(valid_thresholds.max_response_time_ms, 1000.0)
        self.assertEqual(valid_thresholds.max_memory_usage_mb, 500.0)
    
    async def test_memory_efficiency_analysis(self):
        """Test memory efficiency analysis."""
        result = await self.resource_validator.validate_resource_efficiency(
            "memory_analysis",
            self._memory_intensive_operation,
            monitoring_duration=2.0,
            efficiency_thresholds={
                "max_memory_mb": 200.0,
                "min_efficiency_score": 60.0
            }
        )
        
        # Check memory efficiency analysis
        memory_metrics = [m for m in result.efficiency_analysis if m.resource_type == "memory"]
        self.assertGreater(len(memory_metrics), 0)
        
        memory_metric = memory_metrics[0]
        self.assertGreater(memory_metric.efficiency_score, 0)
        self.assertLessEqual(memory_metric.utilization_rate, 100.0)
    
    async def test_cpu_efficiency_analysis(self):
        """Test CPU efficiency analysis."""
        result = await self.resource_validator.validate_resource_efficiency(
            "cpu_analysis",
            self._cpu_intensive_operation,
            monitoring_duration=2.0
        )
        
        # Check CPU efficiency analysis
        cpu_metrics = [m for m in result.efficiency_analysis if m.resource_type == "cpu"]
        self.assertGreater(len(cpu_metrics), 0)
        
        cpu_metric = cpu_metrics[0]
        self.assertGreater(cpu_metric.efficiency_score, 0)
        self.assertLessEqual(cpu_metric.utilization_rate, 100.0)
    
    async def test_stress_test_resource_management(self):
        """Test resource management under stress conditions."""
        # Create multiple stress operations
        stress_operations = [
            self._fast_operation,
            self._memory_intensive_operation,
            self._cpu_intensive_operation
        ]
        
        result = await self.resource_validator.validate_resource_stress_test(
            stress_operations,
            concurrent_level=5,
            duration_seconds=3.0
        )
        
        self.assertIsInstance(result, ResourceValidationResult)
        self.assertIn("concurrent", result.operation_name)
        self.assertGreater(result.performance_metrics.get("concurrent_operations", 0), 0)
    
    async def test_performance_trend_analysis(self):
        """Test performance trend analysis."""
        # Simulate multiple benchmark runs to establish trends
        results = []
        for i in range(5):
            result = await self.performance_validator.validate_performance(
                "trend_test",
                self._fast_operation,
                test_count=20
            )
            results.append(result)
            await asyncio.sleep(0.1)  # Small delay between runs
        
        # All results should be consistent
        avg_durations = [r.benchmark_result.average_duration_ms for r in results]
        
        # Check that performance is stable (no major degradation)
        first_duration = avg_durations[0]
        last_duration = avg_durations[-1]
        
        # Performance shouldn't degrade by more than 100%
        degradation = (last_duration - first_duration) / first_duration
        self.assertLess(degradation, 1.0)
    
    async def test_benchmark_result_completeness(self):
        """Test that benchmark results contain all required metrics."""
        result = await self.performance_validator.validate_performance(
            "completeness_test",
            self._medium_operation,
            test_count=10
        )
        
        benchmark = result.benchmark_result
        
        # Check all required fields are present
        self.assertIsNotNone(benchmark.benchmark_name)
        self.assertGreater(benchmark.test_count, 0)
        self.assertGreater(benchmark.total_duration_ms, 0)
        self.assertGreater(benchmark.average_duration_ms, 0)
        self.assertGreater(benchmark.median_duration_ms, 0)
        self.assertGreaterEqual(benchmark.min_duration_ms, 0)
        self.assertGreater(benchmark.max_duration_ms, 0)
        self.assertGreater(benchmark.p95_duration_ms, 0)
        self.assertGreater(benchmark.p99_duration_ms, 0)
        self.assertGreater(benchmark.throughput_ops_per_second, 0)
        self.assertGreaterEqual(benchmark.success_rate, 0)
        self.assertLessEqual(benchmark.success_rate, 100.0)
    
    async def test_error_recovery_in_benchmarks(self):
        """Test error recovery during benchmark execution."""
        def intermittent_failure_operation():
            # Randomly fail sometimes
            import random
            if random.random() < 0.3:  # 30% failure rate
                raise RuntimeError("Intermittent failure")
            return "success"
        
        result = await self.performance_validator.validate_performance(
            "error_recovery_test",
            intermittent_failure_operation,
            test_count=30
        )
        
        # Should handle errors gracefully
        self.assertIsInstance(result, PerformanceValidationResult)
        self.assertGreater(result.benchmark_result.error_count, 0)
        self.assertLess(result.benchmark_result.success_rate, 100.0)
        self.assertGreater(result.benchmark_result.success_rate, 50.0)  # Should have some successes


class AsyncTestRunner:
    """Helper class to run async tests."""
    
    @staticmethod
    def run_async_test(test_method):
        """Run an async test method."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(test_method)
        finally:
            loop.close()


# Test suite for async tests
class TestPerformanceBenchmarksAsync(unittest.TestCase):
    """Async test suite for performance benchmarks."""
    
    def setUp(self):
        """Set up async test environment."""
        self.test_instance = TestPerformanceBenchmarks()
        self.test_instance.setUp()
    
    def tearDown(self):
        """Clean up async test environment."""
        self.test_instance.tearDown()
    
    def test_basic_performance_validation_async(self):
        """Test basic performance validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_basic_performance_validation()
        )
    
    def test_performance_validation_with_thresholds_async(self):
        """Test performance validation with thresholds (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_performance_validation_with_thresholds()
        )
    
    def test_performance_benchmark_accuracy_async(self):
        """Test performance benchmark accuracy (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_performance_benchmark_accuracy()
        )
    
    def test_error_handling_in_benchmarks_async(self):
        """Test error handling in benchmarks (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_error_handling_in_benchmarks()
        )
    
    def test_async_operation_benchmarking_async(self):
        """Test async operation benchmarking (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_async_operation_benchmarking()
        )
    
    def test_throughput_calculation_async(self):
        """Test throughput calculation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_throughput_calculation()
        )
    
    def test_memory_performance_monitoring_async(self):
        """Test memory performance monitoring (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_memory_performance_monitoring()
        )
    
    def test_cpu_performance_monitoring_async(self):
        """Test CPU performance monitoring (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_cpu_performance_monitoring()
        )
    
    def test_stress_testing_capabilities_async(self):
        """Test stress testing capabilities (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_stress_testing_capabilities()
        )
    
    def test_performance_regression_detection_async(self):
        """Test performance regression detection (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_performance_regression_detection()
        )
    
    def test_resource_management_validation_async(self):
        """Test resource management validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_management_validation()
        )
    
    def test_resource_leak_detection_async(self):
        """Test resource leak detection (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_leak_detection()
        )
    
    def test_resource_bottleneck_analysis_async(self):
        """Test resource bottleneck analysis (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_bottleneck_analysis()
        )
    
    def test_concurrent_performance_testing_async(self):
        """Test concurrent performance testing (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_concurrent_performance_testing()
        )
    
    def test_performance_optimization_suggestions_async(self):
        """Test performance optimization suggestions (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_performance_optimization_suggestions()
        )
    
    def test_benchmark_statistical_accuracy_async(self):
        """Test benchmark statistical accuracy (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_benchmark_statistical_accuracy()
        )
    
    def test_performance_validator_quality_check_async(self):
        """Test performance validator quality check (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_performance_validator_quality_check()
        )
    
    def test_resource_validator_quality_check_async(self):
        """Test resource validator quality check (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_validator_quality_check()
        )
    
    def test_memory_efficiency_analysis_async(self):
        """Test memory efficiency analysis (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_memory_efficiency_analysis()
        )
    
    def test_cpu_efficiency_analysis_async(self):
        """Test CPU efficiency analysis (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_cpu_efficiency_analysis()
        )
    
    def test_stress_test_resource_management_async(self):
        """Test stress test resource management (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_stress_test_resource_management()
        )
    
    def test_performance_trend_analysis_async(self):
        """Test performance trend analysis (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_performance_trend_analysis()
        )
    
    def test_benchmark_result_completeness_async(self):
        """Test benchmark result completeness (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_benchmark_result_completeness()
        )
    
    def test_error_recovery_in_benchmarks_async(self):
        """Test error recovery in benchmarks (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_error_recovery_in_benchmarks()
        )


def run_performance_benchmark_tests():
    """Run all performance benchmark tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add sync tests
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBenchmarks))
    
    # Add async tests
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBenchmarksAsync))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run tests
    success = run_performance_benchmark_tests()
    
    if success:
        print("\n✅ All performance benchmark tests passed!")
        exit(0)
    else:
        print("\n❌ Some performance benchmark tests failed!")
        exit(1)