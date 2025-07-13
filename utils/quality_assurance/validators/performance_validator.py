#!/usr/bin/env python3
"""Performance Validator.

This module provides comprehensive performance validation and benchmarking including:
- Response time validation and analysis
- Throughput measurement and validation
- Memory usage monitoring and validation
- CPU performance analysis
- Concurrency performance testing
- Load testing and stress testing capabilities
- Performance regression detection
- Benchmark comparison and analysis
"""

import asyncio
import json
import time
import sys
import gc
import resource
import psutil
import threading
import statistics
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import subprocess

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# Performance validation types
@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation."""
    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    memory_usage_mb: float
    cpu_percent: float
    thread_count: int
    success: bool
    error_message: Optional[str] = None
    additional_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    benchmark_name: str
    test_count: int
    total_duration_ms: float
    average_duration_ms: float
    median_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    throughput_ops_per_second: float
    success_rate: float
    memory_peak_mb: float
    memory_average_mb: float
    cpu_average_percent: float
    cpu_peak_percent: float
    error_count: int
    error_types: Dict[str, int] = field(default_factory=dict)
    performance_metrics: List[PerformanceMetrics] = field(default_factory=list)


@dataclass
class PerformanceThresholds:
    """Performance validation thresholds."""
    max_response_time_ms: float
    max_memory_usage_mb: float
    max_cpu_percent: float
    min_throughput_ops_per_second: float
    max_error_rate_percent: float
    max_p95_response_time_ms: float
    max_p99_response_time_ms: float


@dataclass
class PerformanceValidationResult:
    """Result of performance validation."""
    validation_id: str
    timestamp: datetime
    operation_name: str
    benchmark_result: BenchmarkResult
    thresholds: PerformanceThresholds
    validation_passed: bool
    violations: List[str]
    warnings: List[str]
    performance_score: float  # 0-100
    regression_detected: bool
    comparison_baseline: Optional[BenchmarkResult] = None


class PerformanceProfiler:
    """Profiles performance of operations."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.active_profiles = {}
        self.process = psutil.Process()
        
    async def profile_operation(
        self, 
        operation_name: str, 
        operation_func: Callable, 
        *args, 
        **kwargs
    ) -> PerformanceMetrics:
        """Profile a single operation execution."""
        
        # Get initial metrics
        start_time = time.time()
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        initial_threads = threading.active_count()
        
        # Track CPU usage
        cpu_percent_start = self.process.cpu_percent()
        
        success = True
        error_message = None
        additional_metrics = {}
        
        try:
            # Execute operation
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)
                
            # Store result metrics if available
            if isinstance(result, dict) and "performance_metrics" in result:
                additional_metrics.update(result["performance_metrics"])
                
        except Exception as e:
            success = False
            error_message = str(e)
            self.logger.error(f"Operation {operation_name} failed: {error_message}")
            
        # Get final metrics
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = final_memory - initial_memory
        final_threads = threading.active_count()
        
        # Get CPU usage (average over operation duration)
        cpu_percent = self.process.cpu_percent()
        
        return PerformanceMetrics(
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            memory_usage_mb=memory_usage,
            cpu_percent=cpu_percent,
            thread_count=final_threads - initial_threads,
            success=success,
            error_message=error_message,
            additional_metrics=additional_metrics
        )
    
    async def profile_batch_operations(
        self,
        operation_name: str,
        operation_func: Callable,
        operation_count: int,
        *args,
        **kwargs
    ) -> List[PerformanceMetrics]:
        """Profile multiple executions of the same operation."""
        
        metrics = []
        
        for i in range(operation_count):
            try:
                metric = await self.profile_operation(
                    f"{operation_name}_batch_{i}",
                    operation_func,
                    *args,
                    **kwargs
                )
                metrics.append(metric)
                
                # Small delay to prevent overwhelming the system
                if i % 10 == 0:
                    await asyncio.sleep(0.001)
                    
            except Exception as e:
                self.logger.error(f"Batch operation {i} failed: {str(e)}")
                
        return metrics
    
    async def profile_concurrent_operations(
        self,
        operation_name: str,
        operation_func: Callable,
        concurrency_level: int,
        operations_per_worker: int,
        *args,
        **kwargs
    ) -> List[PerformanceMetrics]:
        """Profile concurrent executions of operations."""
        
        async def worker(worker_id: int) -> List[PerformanceMetrics]:
            worker_metrics = []
            for i in range(operations_per_worker):
                try:
                    metric = await self.profile_operation(
                        f"{operation_name}_concurrent_{worker_id}_{i}",
                        operation_func,
                        *args,
                        **kwargs
                    )
                    worker_metrics.append(metric)
                except Exception as e:
                    self.logger.error(f"Concurrent operation {worker_id}:{i} failed: {str(e)}")
            return worker_metrics
        
        # Create concurrent workers
        tasks = [worker(i) for i in range(concurrency_level)]
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all metrics
        all_metrics = []
        for result in worker_results:
            if isinstance(result, list):
                all_metrics.extend(result)
            else:
                self.logger.error(f"Worker failed: {str(result)}")
                
        return all_metrics


class PerformanceBenchmark:
    """Runs performance benchmarks and analyzes results."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.profiler = PerformanceProfiler()
        
    async def run_benchmark(
        self,
        benchmark_name: str,
        operation_func: Callable,
        test_count: int = 100,
        concurrency_level: int = 1,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """Run a comprehensive performance benchmark."""
        
        self.logger.info(f"Starting benchmark: {benchmark_name} (tests: {test_count}, concurrency: {concurrency_level})")
        
        start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Profile operations
        if concurrency_level == 1:
            metrics = await self.profiler.profile_batch_operations(
                benchmark_name, operation_func, test_count, *args, **kwargs
            )
        else:
            operations_per_worker = max(1, test_count // concurrency_level)
            metrics = await self.profiler.profile_concurrent_operations(
                benchmark_name, operation_func, concurrency_level, operations_per_worker, *args, **kwargs
            )
        
        end_time = time.time()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Analyze results
        successful_metrics = [m for m in metrics if m.success]
        failed_metrics = [m for m in metrics if not m.success]
        
        if not successful_metrics:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                test_count=len(metrics),
                total_duration_ms=(end_time - start_time) * 1000,
                average_duration_ms=0.0,
                median_duration_ms=0.0,
                min_duration_ms=0.0,
                max_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
                throughput_ops_per_second=0.0,
                success_rate=0.0,
                memory_peak_mb=final_memory,
                memory_average_mb=final_memory - initial_memory,
                cpu_average_percent=0.0,
                cpu_peak_percent=0.0,
                error_count=len(failed_metrics),
                performance_metrics=metrics
            )
        
        # Calculate duration statistics
        durations = [m.duration_ms for m in successful_metrics]
        total_duration_ms = (end_time - start_time) * 1000
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        p95_index = int(0.95 * len(sorted_durations))
        p99_index = int(0.99 * len(sorted_durations))
        
        # Calculate memory and CPU statistics
        memory_usages = [m.memory_usage_mb for m in successful_metrics]
        cpu_usages = [m.cpu_percent for m in successful_metrics]
        
        # Count error types
        error_types = {}
        for metric in failed_metrics:
            if metric.error_message:
                error_type = metric.error_message.split(":")[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return BenchmarkResult(
            benchmark_name=benchmark_name,
            test_count=len(metrics),
            total_duration_ms=total_duration_ms,
            average_duration_ms=statistics.mean(durations),
            median_duration_ms=statistics.median(durations),
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            p95_duration_ms=sorted_durations[p95_index] if p95_index < len(sorted_durations) else max(durations),
            p99_duration_ms=sorted_durations[p99_index] if p99_index < len(sorted_durations) else max(durations),
            throughput_ops_per_second=len(successful_metrics) / (total_duration_ms / 1000),
            success_rate=len(successful_metrics) / len(metrics) * 100,
            memory_peak_mb=final_memory,
            memory_average_mb=statistics.mean(memory_usages) if memory_usages else 0.0,
            cpu_average_percent=statistics.mean(cpu_usages) if cpu_usages else 0.0,
            cpu_peak_percent=max(cpu_usages) if cpu_usages else 0.0,
            error_count=len(failed_metrics),
            error_types=error_types,
            performance_metrics=metrics
        )
    
    async def run_load_test(
        self,
        test_name: str,
        operation_func: Callable,
        target_rps: float,  # requests per second
        duration_seconds: int,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """Run a load test with target requests per second."""
        
        self.logger.info(f"Starting load test: {test_name} (target: {target_rps} RPS, duration: {duration_seconds}s)")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        metrics = []
        
        request_interval = 1.0 / target_rps if target_rps > 0 else 0.1
        
        async def request_worker():
            while time.time() < end_time:
                try:
                    metric = await self.profiler.profile_operation(
                        f"{test_name}_load",
                        operation_func,
                        *args,
                        **kwargs
                    )
                    metrics.append(metric)
                    
                    # Wait for next request
                    await asyncio.sleep(request_interval)
                    
                except Exception as e:
                    self.logger.error(f"Load test request failed: {str(e)}")
        
        # Run the load test
        await request_worker()
        
        # Analyze results using benchmark analysis
        return await self._analyze_load_test_results(test_name, metrics, duration_seconds, target_rps)
    
    async def _analyze_load_test_results(
        self,
        test_name: str,
        metrics: List[PerformanceMetrics],
        duration_seconds: int,
        target_rps: float
    ) -> BenchmarkResult:
        """Analyze load test results."""
        
        if not metrics:
            return BenchmarkResult(
                benchmark_name=test_name,
                test_count=0,
                total_duration_ms=duration_seconds * 1000,
                average_duration_ms=0.0,
                median_duration_ms=0.0,
                min_duration_ms=0.0,
                max_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
                throughput_ops_per_second=0.0,
                success_rate=0.0,
                memory_peak_mb=0.0,
                memory_average_mb=0.0,
                cpu_average_percent=0.0,
                cpu_peak_percent=0.0,
                error_count=0,
                performance_metrics=[]
            )
        
        successful_metrics = [m for m in metrics if m.success]
        failed_metrics = [m for m in metrics if not m.success]
        
        actual_rps = len(metrics) / duration_seconds
        durations = [m.duration_ms for m in successful_metrics] if successful_metrics else [0.0]
        
        # Calculate statistics
        sorted_durations = sorted(durations)
        p95_index = int(0.95 * len(sorted_durations))
        p99_index = int(0.99 * len(sorted_durations))
        
        memory_usages = [m.memory_usage_mb for m in metrics]
        cpu_usages = [m.cpu_percent for m in metrics]
        
        return BenchmarkResult(
            benchmark_name=f"{test_name}_load_test",
            test_count=len(metrics),
            total_duration_ms=duration_seconds * 1000,
            average_duration_ms=statistics.mean(durations),
            median_duration_ms=statistics.median(durations),
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            p95_duration_ms=sorted_durations[p95_index] if p95_index < len(sorted_durations) else max(durations),
            p99_duration_ms=sorted_durations[p99_index] if p99_index < len(sorted_durations) else max(durations),
            throughput_ops_per_second=actual_rps,
            success_rate=len(successful_metrics) / len(metrics) * 100 if metrics else 0.0,
            memory_peak_mb=max(memory_usages) if memory_usages else 0.0,
            memory_average_mb=statistics.mean(memory_usages) if memory_usages else 0.0,
            cpu_average_percent=statistics.mean(cpu_usages) if cpu_usages else 0.0,
            cpu_peak_percent=max(cpu_usages) if cpu_usages else 0.0,
            error_count=len(failed_metrics),
            performance_metrics=metrics
        )


class PerformanceValidator(BaseQualityChecker):
    """Comprehensive performance validator and benchmark runner."""
    
    def __init__(self):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.benchmark = PerformanceBenchmark()
        self.baseline_results = {}
        self.validation_history = []
        
        # Default performance thresholds
        self.default_thresholds = PerformanceThresholds(
            max_response_time_ms=1000.0,
            max_memory_usage_mb=100.0,
            max_cpu_percent=80.0,
            min_throughput_ops_per_second=10.0,
            max_error_rate_percent=5.0,
            max_p95_response_time_ms=2000.0,
            max_p99_response_time_ms=5000.0
        )
    
    async def validate_performance(
        self,
        operation_name: str,
        operation_func: Callable,
        thresholds: Optional[PerformanceThresholds] = None,
        test_count: int = 50,
        compare_to_baseline: bool = True,
        *args,
        **kwargs
    ) -> PerformanceValidationResult:
        """Validate performance of an operation against thresholds."""
        
        validation_id = f"perf_validation_{int(time.time() * 1000)}"
        thresholds = thresholds or self.default_thresholds
        
        self.logger.info(f"Starting performance validation: {operation_name}")
        
        # Run benchmark
        benchmark_result = await self.benchmark.run_benchmark(
            operation_name, operation_func, test_count, 1, *args, **kwargs
        )
        
        # Validate against thresholds
        violations = []
        warnings = []
        
        # Response time validation
        if benchmark_result.average_duration_ms > thresholds.max_response_time_ms:
            violations.append(f"Average response time {benchmark_result.average_duration_ms:.1f}ms exceeds threshold {thresholds.max_response_time_ms}ms")
        
        if benchmark_result.p95_duration_ms > thresholds.max_p95_response_time_ms:
            violations.append(f"P95 response time {benchmark_result.p95_duration_ms:.1f}ms exceeds threshold {thresholds.max_p95_response_time_ms}ms")
        
        if benchmark_result.p99_duration_ms > thresholds.max_p99_response_time_ms:
            violations.append(f"P99 response time {benchmark_result.p99_duration_ms:.1f}ms exceeds threshold {thresholds.max_p99_response_time_ms}ms")
        
        # Memory usage validation
        if benchmark_result.memory_average_mb > thresholds.max_memory_usage_mb:
            violations.append(f"Average memory usage {benchmark_result.memory_average_mb:.1f}MB exceeds threshold {thresholds.max_memory_usage_mb}MB")
        
        # CPU usage validation
        if benchmark_result.cpu_average_percent > thresholds.max_cpu_percent:
            violations.append(f"Average CPU usage {benchmark_result.cpu_average_percent:.1f}% exceeds threshold {thresholds.max_cpu_percent}%")
        
        # Throughput validation
        if benchmark_result.throughput_ops_per_second < thresholds.min_throughput_ops_per_second:
            violations.append(f"Throughput {benchmark_result.throughput_ops_per_second:.1f} ops/sec below threshold {thresholds.min_throughput_ops_per_second}")
        
        # Error rate validation
        error_rate = (100.0 - benchmark_result.success_rate)
        if error_rate > thresholds.max_error_rate_percent:
            violations.append(f"Error rate {error_rate:.1f}% exceeds threshold {thresholds.max_error_rate_percent}%")
        
        # Performance warnings
        if benchmark_result.max_duration_ms > benchmark_result.average_duration_ms * 3:
            warnings.append("High variance in response times detected")
        
        if benchmark_result.memory_peak_mb > benchmark_result.memory_average_mb * 2:
            warnings.append("High memory usage spikes detected")
        
        # Compare to baseline if available and requested
        baseline_result = None
        regression_detected = False
        
        if compare_to_baseline and operation_name in self.baseline_results:
            baseline_result = self.baseline_results[operation_name]
            regression_detected = await self._detect_regression(benchmark_result, baseline_result)
            
            if regression_detected:
                violations.append("Performance regression detected compared to baseline")
        
        # Calculate performance score
        performance_score = await self._calculate_performance_score(benchmark_result, thresholds, violations, warnings)
        
        # Create validation result
        result = PerformanceValidationResult(
            validation_id=validation_id,
            timestamp=datetime.now(timezone.utc),
            operation_name=operation_name,
            benchmark_result=benchmark_result,
            thresholds=thresholds,
            validation_passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            performance_score=performance_score,
            regression_detected=regression_detected,
            comparison_baseline=baseline_result
        )
        
        self.validation_history.append(result)
        
        # Update baseline if this is a good result
        if result.validation_passed and not regression_detected:
            self.baseline_results[operation_name] = benchmark_result
        
        return result
    
    async def run_stress_test(
        self,
        operation_name: str,
        operation_func: Callable,
        max_concurrency: int = 50,
        step_size: int = 5,
        step_duration: int = 30,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Run a stress test with increasing concurrency levels."""
        
        self.logger.info(f"Starting stress test: {operation_name} (max concurrency: {max_concurrency})")
        
        stress_results = []
        
        for concurrency in range(step_size, max_concurrency + 1, step_size):
            self.logger.info(f"Testing concurrency level: {concurrency}")
            
            # Run benchmark at this concurrency level
            benchmark_result = await self.benchmark.run_benchmark(
                f"{operation_name}_stress_{concurrency}",
                operation_func,
                step_duration * 2,  # operations count
                concurrency,
                *args,
                **kwargs
            )
            
            stress_results.append({
                "concurrency_level": concurrency,
                "benchmark_result": benchmark_result,
                "degradation_factor": self._calculate_degradation_factor(stress_results, benchmark_result)
            })
            
            # Stop if error rate becomes too high
            if benchmark_result.success_rate < 50.0:
                self.logger.warning(f"Stopping stress test due to high error rate at concurrency {concurrency}")
                break
        
        # Analyze stress test results
        max_sustainable_concurrency = await self._find_max_sustainable_concurrency(stress_results)
        breaking_point = await self._find_breaking_point(stress_results)
        
        return {
            "operation_name": operation_name,
            "max_concurrency_tested": max_concurrency,
            "max_sustainable_concurrency": max_sustainable_concurrency,
            "breaking_point": breaking_point,
            "stress_results": stress_results,
            "summary": await self._generate_stress_test_summary(stress_results)
        }
    
    async def _detect_regression(self, current: BenchmarkResult, baseline: BenchmarkResult) -> bool:
        """Detect performance regression compared to baseline."""
        
        # Define regression thresholds (percentage increase that indicates regression)
        regression_thresholds = {
            "response_time": 20.0,  # 20% increase
            "memory_usage": 30.0,   # 30% increase
            "cpu_usage": 25.0,      # 25% increase
            "error_rate": 100.0     # 100% increase (doubling)
        }
        
        # Check response time regression
        response_time_increase = ((current.average_duration_ms - baseline.average_duration_ms) / baseline.average_duration_ms) * 100
        if response_time_increase > regression_thresholds["response_time"]:
            return True
        
        # Check memory usage regression
        memory_increase = ((current.memory_average_mb - baseline.memory_average_mb) / max(baseline.memory_average_mb, 1.0)) * 100
        if memory_increase > regression_thresholds["memory_usage"]:
            return True
        
        # Check CPU usage regression
        cpu_increase = ((current.cpu_average_percent - baseline.cpu_average_percent) / max(baseline.cpu_average_percent, 1.0)) * 100
        if cpu_increase > regression_thresholds["cpu_usage"]:
            return True
        
        # Check error rate regression
        current_error_rate = 100.0 - current.success_rate
        baseline_error_rate = 100.0 - baseline.success_rate
        error_rate_increase = ((current_error_rate - baseline_error_rate) / max(baseline_error_rate, 0.1)) * 100
        if error_rate_increase > regression_thresholds["error_rate"]:
            return True
        
        return False
    
    async def _calculate_performance_score(
        self,
        benchmark_result: BenchmarkResult,
        thresholds: PerformanceThresholds,
        violations: List[str],
        warnings: List[str]
    ) -> float:
        """Calculate overall performance score (0-100)."""
        
        base_score = 100.0
        
        # Deduct for violations (major)
        base_score -= len(violations) * 20.0
        
        # Deduct for warnings (minor)
        base_score -= len(warnings) * 5.0
        
        # Adjust score based on how close to thresholds
        response_time_ratio = benchmark_result.average_duration_ms / thresholds.max_response_time_ms
        memory_ratio = benchmark_result.memory_average_mb / thresholds.max_memory_usage_mb
        cpu_ratio = benchmark_result.cpu_average_percent / thresholds.max_cpu_percent
        throughput_ratio = thresholds.min_throughput_ops_per_second / max(benchmark_result.throughput_ops_per_second, 0.1)
        
        # Calculate efficiency scores
        response_efficiency = max(0, 100 - (response_time_ratio - 1) * 100) if response_time_ratio > 1 else 100
        memory_efficiency = max(0, 100 - (memory_ratio - 1) * 100) if memory_ratio > 1 else 100
        cpu_efficiency = max(0, 100 - (cpu_ratio - 1) * 100) if cpu_ratio > 1 else 100
        throughput_efficiency = max(0, 100 - (throughput_ratio - 1) * 100) if throughput_ratio > 1 else 100
        
        # Weight the efficiency scores
        efficiency_score = (
            response_efficiency * 0.3 +
            memory_efficiency * 0.2 +
            cpu_efficiency * 0.2 +
            throughput_efficiency * 0.2 +
            benchmark_result.success_rate * 0.1
        )
        
        # Combine base score with efficiency
        final_score = (base_score * 0.7) + (efficiency_score * 0.3)
        
        return max(0.0, min(100.0, final_score))
    
    def _calculate_degradation_factor(self, previous_results: List[Dict], current_result: BenchmarkResult) -> float:
        """Calculate performance degradation factor."""
        
        if not previous_results:
            return 1.0
        
        # Compare to first result (baseline)
        baseline = previous_results[0]["benchmark_result"]
        
        # Calculate degradation in response time
        response_degradation = current_result.average_duration_ms / baseline.average_duration_ms
        
        # Calculate degradation in throughput
        throughput_degradation = baseline.throughput_ops_per_second / max(current_result.throughput_ops_per_second, 0.1)
        
        # Return worst degradation
        return max(response_degradation, throughput_degradation)
    
    async def _find_max_sustainable_concurrency(self, stress_results: List[Dict]) -> int:
        """Find maximum sustainable concurrency level."""
        
        for result in reversed(stress_results):
            benchmark = result["benchmark_result"]
            degradation = result["degradation_factor"]
            
            # Consider sustainable if success rate > 95% and degradation < 2x
            if benchmark.success_rate > 95.0 and degradation < 2.0:
                return result["concurrency_level"]
        
        return 1 if stress_results else 0
    
    async def _find_breaking_point(self, stress_results: List[Dict]) -> Optional[int]:
        """Find the concurrency level where the system starts breaking."""
        
        for result in stress_results:
            benchmark = result["benchmark_result"]
            
            # Consider broken if success rate < 80% or very high degradation
            if benchmark.success_rate < 80.0 or result["degradation_factor"] > 5.0:
                return result["concurrency_level"]
        
        return None
    
    async def _generate_stress_test_summary(self, stress_results: List[Dict]) -> Dict[str, Any]:
        """Generate summary of stress test results."""
        
        if not stress_results:
            return {"status": "no_data"}
        
        # Find best and worst results
        best_result = min(stress_results, key=lambda x: x["degradation_factor"])
        worst_result = max(stress_results, key=lambda x: x["degradation_factor"])
        
        # Calculate averages
        avg_success_rate = statistics.mean([r["benchmark_result"].success_rate for r in stress_results])
        avg_response_time = statistics.mean([r["benchmark_result"].average_duration_ms for r in stress_results])
        avg_throughput = statistics.mean([r["benchmark_result"].throughput_ops_per_second for r in stress_results])
        
        return {
            "total_concurrency_levels_tested": len(stress_results),
            "best_concurrency_level": best_result["concurrency_level"],
            "worst_concurrency_level": worst_result["concurrency_level"],
            "average_success_rate": avg_success_rate,
            "average_response_time_ms": avg_response_time,
            "average_throughput_ops_per_sec": avg_throughput,
            "max_degradation_factor": worst_result["degradation_factor"],
            "min_degradation_factor": best_result["degradation_factor"],
            "stability_assessment": "stable" if worst_result["degradation_factor"] < 3.0 else "unstable"
        }
    
    async def set_baseline(self, operation_name: str, operation_func: Callable, *args, **kwargs) -> BenchmarkResult:
        """Set performance baseline for an operation."""
        
        self.logger.info(f"Setting performance baseline for: {operation_name}")
        
        baseline_result = await self.benchmark.run_benchmark(
            f"{operation_name}_baseline",
            operation_func,
            100,  # Use more samples for baseline
            1,
            *args,
            **kwargs
        )
        
        self.baseline_results[operation_name] = baseline_result
        
        self.logger.info(f"Baseline set for {operation_name}: {baseline_result.average_duration_ms:.1f}ms avg response time")
        
        return baseline_result
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check performance validator quality and status."""
        
        if not self.validation_history:
            return {
                "validator_status": "ready",
                "message": "No performance validations performed yet"
            }
        
        total_validations = len(self.validation_history)
        passed_validations = sum(1 for v in self.validation_history if v.validation_passed)
        
        # Calculate average performance score
        avg_performance_score = sum(v.performance_score for v in self.validation_history) / total_validations
        
        # Count regressions
        regressions_detected = sum(1 for v in self.validation_history if v.regression_detected)
        
        # Recent validation trend
        recent_validations = self.validation_history[-10:] if len(self.validation_history) >= 10 else self.validation_history
        recent_passed = sum(1 for v in recent_validations if v.validation_passed)
        recent_pass_rate = recent_passed / len(recent_validations)
        
        return {
            "validator_status": "active",
            "total_validations_performed": total_validations,
            "validation_pass_rate": passed_validations / total_validations,
            "average_performance_score": avg_performance_score,
            "regressions_detected": regressions_detected,
            "recent_validation_trend": "improving" if recent_pass_rate > 0.8 else "concerning",
            "baselines_established": len(self.baseline_results),
            "operations_with_baselines": list(self.baseline_results.keys()),
            "default_thresholds": {
                "max_response_time_ms": self.default_thresholds.max_response_time_ms,
                "max_memory_usage_mb": self.default_thresholds.max_memory_usage_mb,
                "max_cpu_percent": self.default_thresholds.max_cpu_percent,
                "min_throughput_ops_per_second": self.default_thresholds.min_throughput_ops_per_second
            }
        }


# CLI interface for performance validation
async def main():
    """CLI interface for performance validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Validator")
    parser.add_argument("--test", choices=["basic", "stress", "load"], default="basic", help="Type of test to run")
    parser.add_argument("--operation", help="Operation name to test")
    parser.add_argument("--count", type=int, default=50, help="Number of test iterations")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrency level")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    validator = PerformanceValidator()
    
    # Example test function
    async def example_operation():
        await asyncio.sleep(0.01)  # Simulate work
        return {"status": "success"}
    
    try:
        if args.test == "basic":
            result = await validator.validate_performance(
                args.operation or "example_operation",
                example_operation,
                test_count=args.count
            )
            output_data = {
                "validation_result": {
                    "passed": result.validation_passed,
                    "score": result.performance_score,
                    "violations": result.violations,
                    "warnings": result.warnings
                },
                "benchmark_results": {
                    "average_duration_ms": result.benchmark_result.average_duration_ms,
                    "throughput_ops_per_second": result.benchmark_result.throughput_ops_per_second,
                    "success_rate": result.benchmark_result.success_rate,
                    "memory_usage_mb": result.benchmark_result.memory_average_mb
                }
            }
            
        elif args.test == "stress":
            result = await validator.run_stress_test(
                args.operation or "example_operation",
                example_operation,
                max_concurrency=args.concurrency,
                step_duration=args.duration
            )
            output_data = result
            
        elif args.test == "load":
            result = await validator.benchmark.run_load_test(
                args.operation or "example_operation",
                example_operation,
                target_rps=args.count / args.duration,
                duration_seconds=args.duration
            )
            output_data = {
                "load_test_result": {
                    "target_rps": args.count / args.duration,
                    "actual_rps": result.throughput_ops_per_second,
                    "average_duration_ms": result.average_duration_ms,
                    "success_rate": result.success_rate,
                    "error_count": result.error_count
                }
            }
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"Results saved to: {args.output}")
        else:
            print(json.dumps(output_data, indent=2, default=str))
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    return 0


if __name__ == "__main__":
    asyncio.run(main())