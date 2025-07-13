#!/usr/bin/env python3
"""Instant Quality Checker.

This module implements the instant quality check functionality that provides:
- Real-time quality validation during development
- Immediate feedback on code changes
- Lightweight checks for rapid iteration
- Integration with development workflows
- Automatic detection of quality regressions

The instant checker focuses on fast feedback for developers while maintaining accuracy.
"""

import asyncio
import json
import time
import sys
import subprocess
import traceback
import os
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import hashlib
import watchdog.observers
import watchdog.events

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker
from utils.quality_assurance.gates.level1_basic_gate import Level1BasicQualityGate, Level1ValidationResult
from utils.quality_assurance.gates.level2_functional_gate import Level2FunctionalQualityGate, Level2ValidationResult


# Instant check types
@dataclass
class InstantCheckResult:
    """Result of instant quality check."""
    check_id: str
    check_type: str  # "file", "snippet", "project_partial"
    timestamp: datetime
    target_path: str
    check_duration_ms: float
    overall_status: str  # "pass", "warning", "fail", "error"
    quality_score: float
    issues_found: int
    critical_issues: int
    blocking_issues: List[str]
    warnings: List[str]
    suggestions: List[str]
    next_actions: List[str]
    level1_result: Optional[Level1ValidationResult] = None
    level2_result: Optional[Level2ValidationResult] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    change_impact: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileChangeEvent:
    """File change event for monitoring."""
    file_path: str
    event_type: str  # "created", "modified", "deleted", "moved"
    timestamp: datetime
    file_size: int
    file_hash: Optional[str] = None


@dataclass
class InstantCheckConfig:
    """Configuration for instant checking."""
    enabled: bool = True
    auto_check_on_save: bool = True
    check_timeout_seconds: float = 5.0
    min_check_interval_ms: int = 100
    max_concurrent_checks: int = 3
    watch_patterns: List[str] = field(default_factory=lambda: ["*.py"])
    ignore_patterns: List[str] = field(default_factory=lambda: ["__pycache__", "*.pyc", ".git"])
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "min_quality_score": 70.0,
        "max_critical_issues": 0,
        "max_blocking_issues": 2
    })


class FileWatcher(watchdog.events.FileSystemEventHandler):
    """Watches for file changes to trigger instant checks."""
    
    def __init__(self, instant_checker: 'InstantQualityChecker'):
        super().__init__()
        self.instant_checker = instant_checker
        self.logger = AstolfoLogger(__name__)
        self.last_check_times = {}
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        file_path = event.src_path
        
        # Check if file matches watch patterns
        if not self._should_check_file(file_path):
            return
            
        # Throttle checks to avoid excessive triggering
        now = time.time()
        last_check = self.last_check_times.get(file_path, 0)
        min_interval = self.instant_checker.config.min_check_interval_ms / 1000.0
        
        if now - last_check < min_interval:
            return
            
        self.last_check_times[file_path] = now
        
        # Trigger instant check
        asyncio.create_task(self.instant_checker.check_file_async(file_path))
        
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self._should_check_file(event.src_path):
            asyncio.create_task(self.instant_checker.check_file_async(event.src_path))
            
    def _should_check_file(self, file_path: str) -> bool:
        """Check if file should be monitored."""
        path_obj = Path(file_path)
        
        # Check ignore patterns
        for ignore_pattern in self.instant_checker.config.ignore_patterns:
            if ignore_pattern in str(path_obj):
                return False
                
        # Check watch patterns
        for watch_pattern in self.instant_checker.config.watch_patterns:
            if path_obj.match(watch_pattern):
                return True
                
        return False


class InstantQualityChecker(BaseQualityChecker):
    """Instant quality checker for real-time development feedback."""
    
    def __init__(self, config: Optional[InstantCheckConfig] = None):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.config = config or InstantCheckConfig()
        
        # Quality gates for instant checking
        self.level1_gate = Level1BasicQualityGate()
        self.level2_gate = Level2FunctionalQualityGate()
        
        # File monitoring
        self.file_watcher = FileWatcher(self)
        self.observer = None
        self.watching = False
        
        # Concurrent check management
        self.active_checks = set()
        self.check_queue = asyncio.Queue()
        self.check_history = {}
        
        # Performance tracking
        self.check_times = []
        self.average_check_time = 0.0
        
    async def start_watching(self, watch_paths: List[str] = None) -> bool:
        """Start watching files for automatic instant checking."""
        if not self.config.enabled or not self.config.auto_check_on_save:
            return False
            
        if self.watching:
            await self.stop_watching()
            
        try:
            if not watch_paths:
                watch_paths = [str(project_root / "src")]
                
            self.observer = watchdog.observers.Observer()
            
            for watch_path in watch_paths:
                if Path(watch_path).exists():
                    self.observer.schedule(self.file_watcher, watch_path, recursive=True)
                    
            self.observer.start()
            self.watching = True
            
            self.logger.info(f"Started watching {len(watch_paths)} paths for instant quality checks")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start file watching: {str(e)}")
            return False
            
    async def stop_watching(self):
        """Stop watching files."""
        if self.observer and self.watching:
            self.observer.stop()
            self.observer.join()
            self.watching = False
            self.logger.info("Stopped file watching")
            
    async def check_file_instant(self, file_path: str) -> InstantCheckResult:
        """Perform instant quality check on a single file."""
        check_id = f"instant_{int(time.time() * 1000)}"
        start_time = time.time()
        
        try:
            # Check if we're already checking this file
            if file_path in self.active_checks:
                return InstantCheckResult(
                    check_id=check_id,
                    check_type="file",
                    timestamp=datetime.now(timezone.utc),
                    target_path=file_path,
                    check_duration_ms=0.0,
                    overall_status="error",
                    quality_score=0.0,
                    issues_found=1,
                    critical_issues=0,
                    blocking_issues=["Check already in progress"],
                    warnings=[],
                    suggestions=[],
                    next_actions=[]
                )
                
            self.active_checks.add(file_path)
            
            # Validate file exists and is readable
            if not Path(file_path).exists():
                return await self._create_error_result(check_id, file_path, "File not found", start_time)
                
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return await self._create_error_result(check_id, file_path, f"Cannot read file: {str(e)}", start_time)
                
            # Perform Level 1 basic validation (fast)
            level1_result = await self.level1_gate.validate_code(content, file_path)
            
            # Initialize result
            result = InstantCheckResult(
                check_id=check_id,
                check_type="file",
                timestamp=datetime.now(timezone.utc),
                target_path=file_path,
                check_duration_ms=0.0,
                overall_status="unknown",
                quality_score=level1_result.quality_score,
                issues_found=len(level1_result.validation_errors),
                critical_issues=0,
                blocking_issues=[],
                warnings=level1_result.validation_warnings.copy(),
                suggestions=[],
                next_actions=[],
                level1_result=level1_result
            )
            
            # Analyze Level 1 results
            if level1_result.overall_status == "fail":
                result.overall_status = "fail"
                result.critical_issues = len([e for e in level1_result.validation_errors if "critical" in e.lower()])
                result.blocking_issues = level1_result.validation_errors.copy()
                result.next_actions.extend(level1_result.remediation_actions)
            elif level1_result.overall_status == "warning":
                result.overall_status = "warning"
                result.suggestions.extend(level1_result.remediation_actions)
            else:
                # Level 1 passed, try Level 2 if time permits
                try:
                    level2_result = await asyncio.wait_for(
                        self.level2_gate.validate_code(content, file_path),
                        timeout=self.config.check_timeout_seconds - (time.time() - start_time)
                    )
                    
                    result.level2_result = level2_result
                    result.quality_score = (level1_result.quality_score + level2_result.quality_score) / 2
                    result.issues_found += len(level2_result.validation_errors)
                    result.warnings.extend(level2_result.validation_warnings)
                    
                    if level2_result.overall_status == "fail":
                        result.overall_status = "fail"
                        result.blocking_issues.extend(level2_result.validation_errors)
                        result.next_actions.extend(level2_result.remediation_actions)
                    elif level2_result.overall_status == "warning":
                        result.overall_status = "warning"
                        result.suggestions.extend(level2_result.remediation_actions)
                    else:
                        result.overall_status = "pass"
                        
                except asyncio.TimeoutError:
                    result.overall_status = "warning"
                    result.warnings.append("Level 2 check timed out - file may be complex")
                    result.suggestions.append("Consider breaking down complex code into smaller functions")
                    
            # Calculate performance metrics
            end_time = time.time()
            check_duration = (end_time - start_time) * 1000
            result.check_duration_ms = check_duration
            
            # Update performance tracking
            self.check_times.append(check_duration)
            if len(self.check_times) > 100:
                self.check_times.pop(0)
            self.average_check_time = sum(self.check_times) / len(self.check_times)
            
            result.performance_metrics = {
                "check_duration_ms": check_duration,
                "average_check_time_ms": self.average_check_time,
                "file_size_bytes": len(content),
                "lines_of_code": len(content.splitlines())
            }
            
            # Apply quality thresholds
            await self._apply_quality_thresholds(result)
            
            # Update check history
            self.check_history[file_path] = {
                "last_check": result.timestamp,
                "last_result": result.overall_status,
                "last_score": result.quality_score
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during instant check of {file_path}: {str(e)}")
            return await self._create_error_result(check_id, file_path, f"Unexpected error: {str(e)}", start_time)
            
        finally:
            self.active_checks.discard(file_path)
            
    async def check_file_async(self, file_path: str):
        """Async wrapper for file checking with queue management."""
        if len(self.active_checks) >= self.config.max_concurrent_checks:
            await self.check_queue.put(file_path)
            return
            
        result = await self.check_file_instant(file_path)
        await self._notify_check_result(result)
        
        # Process queued checks
        if not self.check_queue.empty():
            try:
                next_file = self.check_queue.get_nowait()
                asyncio.create_task(self.check_file_async(next_file))
            except asyncio.QueueEmpty:
                pass
                
    async def check_code_snippet(self, code: str, context: str = "snippet") -> InstantCheckResult:
        """Perform instant quality check on a code snippet."""
        check_id = f"snippet_{int(time.time() * 1000)}"
        start_time = time.time()
        
        try:
            # Quick Level 1 validation only for snippets
            level1_result = await self.level1_gate.validate_code(code, f"<{context}>")
            
            result = InstantCheckResult(
                check_id=check_id,
                check_type="snippet",
                timestamp=datetime.now(timezone.utc),
                target_path=context,
                check_duration_ms=(time.time() - start_time) * 1000,
                overall_status=level1_result.overall_status,
                quality_score=level1_result.quality_score,
                issues_found=len(level1_result.validation_errors),
                critical_issues=len([e for e in level1_result.validation_errors if "critical" in e.lower()]),
                blocking_issues=level1_result.validation_errors.copy(),
                warnings=level1_result.validation_warnings.copy(),
                suggestions=level1_result.remediation_actions.copy(),
                next_actions=[],
                level1_result=level1_result
            )
            
            result.performance_metrics = {
                "check_duration_ms": result.check_duration_ms,
                "code_length": len(code),
                "lines_of_code": len(code.splitlines())
            }
            
            return result
            
        except Exception as e:
            return await self._create_error_result(check_id, context, f"Error checking snippet: {str(e)}", start_time)
            
    async def check_project_changes(self, changed_files: List[str]) -> Dict[str, InstantCheckResult]:
        """Check multiple changed files in project."""
        results = {}
        
        # Limit concurrent checks
        semaphore = asyncio.Semaphore(self.config.max_concurrent_checks)
        
        async def check_file_with_semaphore(file_path: str):
            async with semaphore:
                return await self.check_file_instant(file_path)
                
        # Run checks concurrently
        tasks = [check_file_with_semaphore(file_path) for file_path in changed_files]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for file_path, result in zip(changed_files, check_results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to check {file_path}: {str(result)}")
                results[file_path] = await self._create_error_result(
                    f"error_{int(time.time() * 1000)}", 
                    file_path, 
                    f"Check failed: {str(result)}", 
                    time.time()
                )
            else:
                results[file_path] = result
                
        return results
        
    async def get_instant_status(self) -> Dict[str, Any]:
        """Get current instant checker status."""
        return {
            "enabled": self.config.enabled,
            "watching": self.watching,
            "active_checks": len(self.active_checks),
            "queued_checks": self.check_queue.qsize(),
            "average_check_time_ms": self.average_check_time,
            "total_checks_performed": len(self.check_history),
            "watch_patterns": self.config.watch_patterns,
            "quality_thresholds": self.config.quality_thresholds,
            "last_checks": {
                path: {
                    "timestamp": history["last_check"].isoformat(),
                    "status": history["last_result"],
                    "score": history["last_score"]
                }
                for path, history in list(self.check_history.items())[-10:]
            }
        }
        
    async def _create_error_result(self, check_id: str, target_path: str, error_message: str, start_time: float) -> InstantCheckResult:
        """Create error result for failed checks."""
        return InstantCheckResult(
            check_id=check_id,
            check_type="error",
            timestamp=datetime.now(timezone.utc),
            target_path=target_path,
            check_duration_ms=(time.time() - start_time) * 1000,
            overall_status="error",
            quality_score=0.0,
            issues_found=1,
            critical_issues=1,
            blocking_issues=[error_message],
            warnings=[],
            suggestions=[],
            next_actions=["Fix the error and try again"]
        )
        
    async def _apply_quality_thresholds(self, result: InstantCheckResult):
        """Apply quality thresholds to determine final status."""
        thresholds = self.config.quality_thresholds
        
        # Check critical issues threshold
        if result.critical_issues > thresholds.get("max_critical_issues", 0):
            if result.overall_status != "fail":
                result.overall_status = "fail"
            result.next_actions.append("Address critical quality issues immediately")
            
        # Check blocking issues threshold
        if len(result.blocking_issues) > thresholds.get("max_blocking_issues", 2):
            if result.overall_status != "fail":
                result.overall_status = "warning"
            result.suggestions.append("Too many blocking issues - consider refactoring")
            
        # Check minimum quality score
        min_score = thresholds.get("min_quality_score", 70.0)
        if result.quality_score < min_score:
            if result.overall_status == "pass":
                result.overall_status = "warning"
            result.suggestions.append(f"Quality score {result.quality_score:.1f} is below threshold {min_score}")
            
    async def _notify_check_result(self, result: InstantCheckResult):
        """Notify about check results (can be extended for IDE integration)."""
        # Log result summary
        status_emoji = {"pass": "✅", "warning": "⚠️", "fail": "❌", "error": "💥"}
        emoji = status_emoji.get(result.overall_status, "❓")
        
        self.logger.info(
            f"{emoji} Instant check {result.check_id}: {result.target_path} "
            f"({result.overall_status}, score: {result.quality_score:.1f}, "
            f"duration: {result.check_duration_ms:.1f}ms)"
        )
        
        # In a real IDE integration, this would send notifications to the editor
        
    async def check_quality(self) -> Dict[str, Any]:
        """Check instant checker quality and configuration."""
        return {
            "checker_type": "InstantQualityChecker",
            "version": "1.0.0",
            "configuration": {
                "enabled": self.config.enabled,
                "auto_check_on_save": self.config.auto_check_on_save,
                "check_timeout_seconds": self.config.check_timeout_seconds,
                "max_concurrent_checks": self.config.max_concurrent_checks
            },
            "performance": {
                "average_check_time_ms": self.average_check_time,
                "total_checks": len(self.check_times),
                "fastest_check_ms": min(self.check_times) if self.check_times else 0,
                "slowest_check_ms": max(self.check_times) if self.check_times else 0
            },
            "status": "ready" if self.config.enabled else "disabled"
        }


# CLI Interface for instant checking
async def main():
    """CLI interface for instant quality checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Instant Quality Checker")
    parser.add_argument("--file", "-f", help="Check specific file")
    parser.add_argument("--watch", "-w", action="store_true", help="Start watching for file changes")
    parser.add_argument("--status", "-s", action="store_true", help="Show checker status")
    parser.add_argument("--config", "-c", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load configuration
    config = InstantCheckConfig()
    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            # Update config with loaded data
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Create checker
    checker = InstantQualityChecker(config)
    
    try:
        if args.file:
            # Check specific file
            result = await checker.check_file_instant(args.file)
            print(json.dumps({
                "check_id": result.check_id,
                "status": result.overall_status,
                "quality_score": result.quality_score,
                "duration_ms": result.check_duration_ms,
                "issues": result.issues_found,
                "blocking_issues": result.blocking_issues,
                "warnings": result.warnings,
                "suggestions": result.suggestions
            }, indent=2))
            
        elif args.status:
            # Show status
            status = await checker.get_instant_status()
            print(json.dumps(status, indent=2))
            
        elif args.watch:
            # Start watching
            print("Starting file watcher...")
            success = await checker.start_watching()
            if success:
                print("Watching for file changes. Press Ctrl+C to stop.")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\nStopping file watcher...")
                    await checker.stop_watching()
            else:
                print("Failed to start file watcher")
                
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    return 0


if __name__ == "__main__":
    asyncio.run(main())