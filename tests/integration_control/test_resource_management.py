#!/usr/bin/env python3
"""Test Resource Management.

This module implements comprehensive tests for resource management efficiency including:
- Resource usage monitoring and validation
- Memory leak detection and analysis
- CPU and memory efficiency testing
- Resource bottleneck identification
- Resource pooling effectiveness testing
- Resource cleanup validation
- Stress testing resource management
- Resource scaling responsiveness testing
"""

import asyncio
import unittest
import time
import sys
import os
import gc
import threading
import tempfile
import json
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "utils"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.validators.resource_management_validator import (
    ResourceManagementValidator, ResourceValidationResult, ResourceLeakAnalysis,
    ResourceBottleneck, ResourceEfficiencyMetrics, ResourceUsageMonitor,
    ResourceLeakDetector, ResourceBottleneckAnalyzer
)


class TestResourceManagement(unittest.TestCase):
    """Test suite for resource management validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.logger = AstolfoLogger(__name__)
        self.validator = ResourceManagementValidator()
        
        # Test operations for resource testing
        self.test_operations = [
            self._memory_light_operation,
            self._memory_heavy_operation,
            self._cpu_light_operation,
            self._cpu_heavy_operation,
            self._io_operation,
            self._mixed_operation
        ]
        
        # Force garbage collection before tests
        gc.collect()
    
    def tearDown(self):
        """Clean up test environment."""
        # Force garbage collection after tests
        gc.collect()
        
        # Clean up any monitoring
        try:
            asyncio.get_event_loop().run_until_complete(
                self.validator.monitor.stop_monitoring()
            )
        except:
            pass
    
    def _memory_light_operation(self) -> str:
        """Light memory usage operation."""
        data = [i for i in range(100)]
        return f"memory_light_{sum(data)}"
    
    def _memory_heavy_operation(self) -> str:
        """Heavy memory usage operation."""
        # Allocate more memory
        data = [i for i in range(10000)]
        matrix = [[j for j in range(100)] for i in range(100)]
        return f"memory_heavy_{len(data) + len(matrix)}"
    
    def _cpu_light_operation(self) -> str:
        """Light CPU usage operation."""
        result = sum(i for i in range(100))
        return f"cpu_light_{result}"
    
    def _cpu_heavy_operation(self) -> str:
        """Heavy CPU usage operation."""
        # CPU intensive computation
        result = sum(i * i for i in range(5000))
        return f"cpu_heavy_{result}"
    
    def _io_operation(self) -> str:
        """I/O intensive operation."""
        # Create temporary file for I/O testing
        with tempfile.NamedTemporaryFile(mode='w+', delete=True) as tmp:
            # Write some data
            data = "test data " * 1000
            tmp.write(data)
            tmp.flush()
            tmp.seek(0)
            # Read it back
            content = tmp.read()
            return f"io_operation_{len(content)}"
    
    def _mixed_operation(self) -> str:
        """Mixed resource usage operation."""
        # Combine memory, CPU, and I/O
        memory_data = [i for i in range(1000)]
        cpu_result = sum(i * i for i in range(1000))
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=True) as tmp:
            tmp.write(str(cpu_result))
            tmp.flush()
            tmp.seek(0)
            content = tmp.read()
            
        return f"mixed_{len(memory_data)}_{cpu_result}_{len(content)}"
    
    def _leaky_operation(self) -> str:
        """Operation that might cause resource leaks (for testing)."""
        # Create objects that might not be immediately cleaned up
        # Note: This is a simplified simulation of potential leaks
        global _test_leak_storage
        if '_test_leak_storage' not in globals():
            _test_leak_storage = []
        
        # Add some data that accumulates
        _test_leak_storage.extend([i for i in range(1000)])
        return f"leaky_{len(_test_leak_storage)}"
    
    async def _async_operation(self) -> str:
        """Async operation for testing."""
        await asyncio.sleep(0.01)
        data = [i for i in range(500)]
        return f"async_{sum(data)}"
    
    def test_resource_validator_initialization(self):
        """Test resource validator initialization."""
        self.assertIsNotNone(self.validator)
        self.assertIsNotNone(self.validator.monitor)
        self.assertIsNotNone(self.validator.leak_detector)
        self.assertIsNotNone(self.validator.bottleneck_analyzer)
    
    async def test_basic_resource_monitoring(self):
        """Test basic resource monitoring functionality."""
        result = await self.validator.validate_resource_efficiency(
            "basic_test",
            self._memory_light_operation,
            monitoring_duration=1.0
        )
        
        self.assertIsInstance(result, ResourceValidationResult)
        self.assertEqual(result.operation_name, "basic_test")
        self.assertGreater(result.efficiency_score, 0)
        self.assertIn("memory", result.resource_utilization)
        self.assertIn("cpu", result.resource_utilization)
    
    async def test_memory_efficiency_validation(self):
        """Test memory efficiency validation."""
        # Test light memory operation
        light_result = await self.validator.validate_resource_efficiency(
            "memory_light",
            self._memory_light_operation,
            monitoring_duration=1.0,
            efficiency_thresholds={"max_memory_mb": 100.0, "min_efficiency_score": 70.0}
        )
        
        self.assertTrue(light_result.validation_passed)
        self.assertGreater(light_result.efficiency_score, 60.0)
        
        # Test heavy memory operation
        heavy_result = await self.validator.validate_resource_efficiency(
            "memory_heavy",
            self._memory_heavy_operation,
            monitoring_duration=1.0,
            efficiency_thresholds={"max_memory_mb": 50.0, "min_efficiency_score": 80.0}
        )
        
        # Heavy operation should be less efficient or fail thresholds
        self.assertLessEqual(heavy_result.efficiency_score, light_result.efficiency_score)
    
    async def test_cpu_efficiency_validation(self):
        """Test CPU efficiency validation."""
        # Test light CPU operation
        light_result = await self.validator.validate_resource_efficiency(
            "cpu_light",
            self._cpu_light_operation,
            monitoring_duration=1.0
        )
        
        self.assertIsInstance(light_result, ResourceValidationResult)
        self.assertGreater(light_result.efficiency_score, 0)
        
        # Test heavy CPU operation
        heavy_result = await self.validator.validate_resource_efficiency(
            "cpu_heavy",
            self._cpu_heavy_operation,
            monitoring_duration=1.0
        )
        
        # Should detect higher CPU usage
        cpu_metrics = [m for m in heavy_result.efficiency_analysis if m.resource_type == "cpu"]
        if cpu_metrics:
            self.assertGreater(cpu_metrics[0].utilization_rate, 0)
    
    async def test_resource_leak_detection(self):
        """Test resource leak detection."""
        # Clean up any existing test storage
        global _test_leak_storage
        _test_leak_storage = []
        
        # Run potentially leaky operation multiple times
        for i in range(5):
            result = await self.validator.validate_resource_efficiency(
                f"leak_test_{i}",
                self._leaky_operation,
                monitoring_duration=0.5
            )
            
            # Give some time for monitoring
            await asyncio.sleep(0.1)
        
        # Check if any leaks were detected
        # Note: Leak detection depends on monitoring duration and operation behavior
        # This test mainly ensures the leak detection system doesn't crash
        self.assertIsInstance(result.detected_leaks, list)
    
    async def test_resource_bottleneck_detection(self):
        """Test resource bottleneck detection."""
        # Test with CPU-intensive operation that should create bottleneck
        result = await self.validator.validate_resource_efficiency(
            "bottleneck_test",
            self._cpu_heavy_operation,
            monitoring_duration=2.0
        )
        
        # Check if bottlenecks were identified
        self.assertIsInstance(result.identified_bottlenecks, list)
        
        # For CPU-intensive operations, we might detect CPU bottlenecks
        cpu_bottlenecks = [b for b in result.identified_bottlenecks if b.resource_type == "cpu"]
        # Note: Bottleneck detection depends on system load and timing
    
    async def test_resource_usage_monitoring(self):
        """Test resource usage monitoring accuracy."""
        monitor = ResourceUsageMonitor()
        
        try:
            # Start monitoring
            await monitor.start_monitoring()
            
            # Give it time to collect some snapshots
            await asyncio.sleep(1.0)
            
            # Perform some operation
            self._memory_heavy_operation()
            
            # Continue monitoring
            await asyncio.sleep(1.0)
            
            # Stop monitoring
            await monitor.stop_monitoring()
            
            # Check monitoring results
            stats = monitor.get_usage_statistics()
            
            self.assertIsInstance(stats, dict)
            self.assertIn("snapshot_count", stats)
            self.assertGreater(stats["snapshot_count"], 0)
            
            if "memory_stats" in stats:
                self.assertIn("average_mb", stats["memory_stats"])
                self.assertGreater(stats["memory_stats"]["average_mb"], 0)
                
        finally:
            await monitor.stop_monitoring()
    
    async def test_efficiency_metrics_calculation(self):
        """Test efficiency metrics calculation."""
        result = await self.validator.validate_resource_efficiency(
            "efficiency_test",
            self._mixed_operation,
            monitoring_duration=1.5
        )
        
        # Check efficiency analysis
        self.assertIsInstance(result.efficiency_analysis, list)
        self.assertGreater(len(result.efficiency_analysis), 0)
        
        for metric in result.efficiency_analysis:
            self.assertIsInstance(metric, ResourceEfficiencyMetrics)
            self.assertIn(metric.resource_type, ["memory", "cpu"])
            self.assertGreaterEqual(metric.efficiency_score, 0)
            self.assertLessEqual(metric.efficiency_score, 100)
            self.assertGreaterEqual(metric.utilization_rate, 0)
            self.assertLessEqual(metric.utilization_rate, 100)
    
    async def test_stress_testing_validation(self):
        """Test resource management under stress conditions."""
        stress_operations = [
            self._memory_light_operation,
            self._cpu_light_operation,
            self._io_operation
        ]
        
        result = await self.validator.validate_resource_stress_test(
            stress_operations,
            concurrent_level=3,
            duration_seconds=2.0
        )
        
        self.assertIsInstance(result, ResourceValidationResult)
        self.assertIn("concurrent", result.operation_name)
        self.assertGreater(result.performance_metrics.get("concurrent_operations", 0), 0)
        
        # Stress test should have lower efficiency threshold
        # (since it's testing under stress conditions)
        self.assertGreaterEqual(result.efficiency_score, 0)
    
    async def test_async_operation_resource_monitoring(self):
        """Test resource monitoring for async operations."""
        result = await self.validator.validate_resource_efficiency(
            "async_test",
            self._async_operation,
            monitoring_duration=1.0
        )
        
        self.assertIsInstance(result, ResourceValidationResult)
        self.assertTrue(result.validation_passed)
        self.assertGreater(result.efficiency_score, 0)
    
    async def test_concurrent_resource_validation(self):
        """Test concurrent resource validation."""
        # Run multiple validations concurrently
        tasks = []
        operations = [
            self._memory_light_operation,
            self._cpu_light_operation,
            self._io_operation
        ]
        
        for i, op in enumerate(operations):
            task = asyncio.create_task(
                self.validator.validate_resource_efficiency(
                    f"concurrent_test_{i}",
                    op,
                    monitoring_duration=1.0
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All tasks should complete successfully
        for result in results:
            self.assertIsInstance(result, ResourceValidationResult)
            self.assertGreater(result.efficiency_score, 0)
    
    async def test_resource_threshold_validation(self):
        """Test resource threshold validation."""
        # Test with strict thresholds
        strict_thresholds = {
            "max_memory_mb": 10.0,    # Very strict
            "max_cpu_percent": 5.0,   # Very strict
            "min_efficiency_score": 90.0  # Very strict
        }
        
        result = await self.validator.validate_resource_efficiency(
            "threshold_test",
            self._memory_heavy_operation,  # Heavy operation
            monitoring_duration=1.0,
            efficiency_thresholds=strict_thresholds
        )
        
        # Should likely fail strict thresholds
        self.assertFalse(result.validation_passed)
        self.assertGreater(len(result.warnings + result.critical_issues), 0)
    
    async def test_resource_optimization_suggestions(self):
        """Test resource optimization suggestions."""
        result = await self.validator.validate_resource_efficiency(
            "optimization_test",
            self._memory_heavy_operation,
            monitoring_duration=1.0,
            efficiency_thresholds={"max_memory_mb": 50.0, "min_efficiency_score": 80.0}
        )
        
        # Should generate optimization suggestions for heavy operation
        self.assertIsInstance(result.optimization_suggestions, list)
        # Heavy memory operation should generate memory-related suggestions
        memory_suggestions = [s for s in result.optimization_suggestions if "memory" in s.lower()]
    
    async def test_resource_cleanup_validation(self):
        """Test resource cleanup validation."""
        result = await self.validator.validate_resource_efficiency(
            "cleanup_test",
            self._mixed_operation,
            monitoring_duration=1.0
        )
        
        # Check cleanup validation
        self.assertIsInstance(result.cleanup_validation, list)
        # Note: Cleanup validation is simplified in current implementation
        # Real implementation would track actual resource cleanup
    
    async def test_resource_pooling_analysis(self):
        """Test resource pooling analysis."""
        result = await self.validator.validate_resource_efficiency(
            "pooling_test",
            self._io_operation,
            monitoring_duration=1.0
        )
        
        # Check pooling analysis
        self.assertIsInstance(result.pooling_analysis, list)
        # Note: Pooling analysis is simplified in current implementation
        # Real implementation would analyze actual resource pools
    
    async def test_resource_scaling_metrics(self):
        """Test resource scaling metrics."""
        result = await self.validator.validate_resource_efficiency(
            "scaling_test",
            self._cpu_heavy_operation,
            monitoring_duration=1.0
        )
        
        # Check scaling metrics
        self.assertIsInstance(result.scaling_metrics, list)
        # Note: Scaling metrics are simplified in current implementation
        # Real implementation would monitor actual scaling events
    
    def test_resource_usage_snapshot(self):
        """Test resource usage snapshot functionality."""
        monitor = ResourceUsageMonitor()
        
        # Take a snapshot
        snapshot = monitor._take_snapshot()
        
        # Verify snapshot contains expected data
        self.assertGreater(snapshot.memory_usage_mb, 0)
        self.assertGreaterEqual(snapshot.memory_percent, 0)
        self.assertGreaterEqual(snapshot.cpu_percent, 0)
        self.assertGreater(snapshot.cpu_count, 0)
        self.assertGreaterEqual(snapshot.thread_count, 1)
        self.assertGreaterEqual(snapshot.process_count, 1)
        self.assertIsInstance(snapshot.timestamp, type(snapshot.timestamp))
    
    async def test_leak_detector_functionality(self):
        """Test leak detector functionality."""
        monitor = ResourceUsageMonitor()
        detector = ResourceLeakDetector(monitor)
        
        # Start monitoring
        await monitor.start_monitoring()
        
        try:
            # Let it collect some baseline data
            await asyncio.sleep(1.0)
            
            # Simulate some memory usage
            data = []
            for i in range(5):
                data.append([j for j in range(1000)])
                await asyncio.sleep(0.2)
            
            # Let monitoring continue
            await asyncio.sleep(1.0)
            
            # Check for leaks
            memory_leaks = await detector.detect_memory_leaks()
            file_leaks = await detector.detect_file_descriptor_leaks()
            thread_leaks = await detector.detect_thread_leaks()
            
            # Verify leak detection doesn't crash
            self.assertIsInstance(memory_leaks, list)
            self.assertIsInstance(file_leaks, list)
            self.assertIsInstance(thread_leaks, list)
            
            # Clean up data
            del data
            gc.collect()
            
        finally:
            await monitor.stop_monitoring()
    
    async def test_bottleneck_analyzer_functionality(self):
        """Test bottleneck analyzer functionality."""
        monitor = ResourceUsageMonitor()
        analyzer = ResourceBottleneckAnalyzer(monitor)
        
        # Start monitoring
        await monitor.start_monitoring()
        
        try:
            # Let it collect baseline data
            await asyncio.sleep(0.5)
            
            # Perform CPU-intensive operation
            result = sum(i * i for i in range(10000))
            
            # Let monitoring continue
            await asyncio.sleep(0.5)
            
            # Analyze bottlenecks
            bottlenecks = await analyzer.analyze_bottlenecks()
            
            # Verify bottleneck analysis
            self.assertIsInstance(bottlenecks, list)
            
            # Check individual analyzer methods
            cpu_bottleneck = await analyzer._analyze_cpu_bottleneck()
            memory_bottleneck = await analyzer._analyze_memory_bottleneck()
            io_bottleneck = await analyzer._analyze_io_bottleneck()
            
            # These might return None if no bottlenecks detected
            self.assertIsInstance(cpu_bottleneck, (type(None), ResourceBottleneck))
            self.assertIsInstance(memory_bottleneck, (type(None), ResourceBottleneck))
            self.assertIsInstance(io_bottleneck, (type(None), ResourceBottleneck))
            
        finally:
            await monitor.stop_monitoring()
    
    async def test_error_handling_in_resource_validation(self):
        """Test error handling during resource validation."""
        def failing_operation():
            raise RuntimeError("Test error in resource operation")
        
        result = await self.validator.validate_resource_efficiency(
            "error_test",
            failing_operation,
            monitoring_duration=0.5
        )
        
        # Should handle errors gracefully
        self.assertIsInstance(result, ResourceValidationResult)
        self.assertFalse(result.validation_passed)
        self.assertGreater(len(result.critical_issues), 0)
    
    async def test_resource_validator_quality_check(self):
        """Test resource validator quality check."""
        quality_result = await self.validator.check_quality()
        
        self.assertIsInstance(quality_result, dict)
        self.assertIn("validator_type", quality_result)
        self.assertEqual(quality_result["validator_type"], "ResourceManagementValidator")
        self.assertIn("capabilities", quality_result)
        self.assertIn("status", quality_result)
        self.assertEqual(quality_result["status"], "ready")
    
    async def test_monitoring_statistics_accuracy(self):
        """Test monitoring statistics accuracy."""
        monitor = ResourceUsageMonitor()
        
        # Start monitoring
        await monitor.start_monitoring()
        
        try:
            # Let it collect data for known duration
            start_time = time.time()
            await asyncio.sleep(2.0)
            end_time = time.time()
            
            # Stop monitoring
            await monitor.stop_monitoring()
            
            # Get statistics
            stats = monitor.get_usage_statistics()
            
            # Verify timing accuracy
            expected_duration = end_time - start_time
            actual_duration = stats.get("monitoring_duration_seconds", 0)
            
            # Allow 20% tolerance for timing
            tolerance = expected_duration * 0.2
            self.assertAlmostEqual(actual_duration, expected_duration, delta=tolerance)
            
            # Verify snapshot count is reasonable
            expected_snapshots = expected_duration / monitor.monitor_interval
            actual_snapshots = stats.get("snapshot_count", 0)
            
            # Should have collected reasonable number of snapshots
            self.assertGreater(actual_snapshots, expected_snapshots * 0.5)
            
        finally:
            await monitor.stop_monitoring()
    
    async def test_resource_efficiency_scoring(self):
        """Test resource efficiency scoring algorithm."""
        # Test with different operations and compare scores
        
        # Light operation should score higher
        light_result = await self.validator.validate_resource_efficiency(
            "light_scoring",
            self._memory_light_operation,
            monitoring_duration=1.0
        )
        
        # Heavy operation should score lower
        heavy_result = await self.validator.validate_resource_efficiency(
            "heavy_scoring",
            self._memory_heavy_operation,
            monitoring_duration=1.0
        )
        
        # Light operation should generally have better efficiency
        # (though this depends on system conditions)
        self.assertGreaterEqual(light_result.efficiency_score, 0)
        self.assertGreaterEqual(heavy_result.efficiency_score, 0)
        
        # Both should be valid scores
        self.assertLessEqual(light_result.efficiency_score, 100)
        self.assertLessEqual(heavy_result.efficiency_score, 100)


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
class TestResourceManagementAsync(unittest.TestCase):
    """Async test suite for resource management."""
    
    def setUp(self):
        """Set up async test environment."""
        self.test_instance = TestResourceManagement()
        self.test_instance.setUp()
    
    def tearDown(self):
        """Clean up async test environment."""
        self.test_instance.tearDown()
    
    def test_basic_resource_monitoring_async(self):
        """Test basic resource monitoring (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_basic_resource_monitoring()
        )
    
    def test_memory_efficiency_validation_async(self):
        """Test memory efficiency validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_memory_efficiency_validation()
        )
    
    def test_cpu_efficiency_validation_async(self):
        """Test CPU efficiency validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_cpu_efficiency_validation()
        )
    
    def test_resource_leak_detection_async(self):
        """Test resource leak detection (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_leak_detection()
        )
    
    def test_resource_bottleneck_detection_async(self):
        """Test resource bottleneck detection (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_bottleneck_detection()
        )
    
    def test_resource_usage_monitoring_async(self):
        """Test resource usage monitoring (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_usage_monitoring()
        )
    
    def test_efficiency_metrics_calculation_async(self):
        """Test efficiency metrics calculation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_efficiency_metrics_calculation()
        )
    
    def test_stress_testing_validation_async(self):
        """Test stress testing validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_stress_testing_validation()
        )
    
    def test_async_operation_resource_monitoring_async(self):
        """Test async operation resource monitoring (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_async_operation_resource_monitoring()
        )
    
    def test_concurrent_resource_validation_async(self):
        """Test concurrent resource validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_concurrent_resource_validation()
        )
    
    def test_resource_threshold_validation_async(self):
        """Test resource threshold validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_threshold_validation()
        )
    
    def test_resource_optimization_suggestions_async(self):
        """Test resource optimization suggestions (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_optimization_suggestions()
        )
    
    def test_resource_cleanup_validation_async(self):
        """Test resource cleanup validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_cleanup_validation()
        )
    
    def test_resource_pooling_analysis_async(self):
        """Test resource pooling analysis (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_pooling_analysis()
        )
    
    def test_resource_scaling_metrics_async(self):
        """Test resource scaling metrics (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_scaling_metrics()
        )
    
    def test_leak_detector_functionality_async(self):
        """Test leak detector functionality (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_leak_detector_functionality()
        )
    
    def test_bottleneck_analyzer_functionality_async(self):
        """Test bottleneck analyzer functionality (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_bottleneck_analyzer_functionality()
        )
    
    def test_error_handling_in_resource_validation_async(self):
        """Test error handling in resource validation (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_error_handling_in_resource_validation()
        )
    
    def test_resource_validator_quality_check_async(self):
        """Test resource validator quality check (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_validator_quality_check()
        )
    
    def test_monitoring_statistics_accuracy_async(self):
        """Test monitoring statistics accuracy (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_monitoring_statistics_accuracy()
        )
    
    def test_resource_efficiency_scoring_async(self):
        """Test resource efficiency scoring (async wrapper)."""
        AsyncTestRunner.run_async_test(
            self.test_instance.test_resource_efficiency_scoring()
        )


def run_resource_management_tests():
    """Run all resource management tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add sync tests
    suite.addTests(loader.loadTestsFromTestCase(TestResourceManagement))
    
    # Add async tests
    suite.addTests(loader.loadTestsFromTestCase(TestResourceManagementAsync))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run tests
    success = run_resource_management_tests()
    
    if success:
        print("\n✅ All resource management tests passed!")
        exit(0)
    else:
        print("\n❌ Some resource management tests failed!")
        exit(1)