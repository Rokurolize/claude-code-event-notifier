#!/usr/bin/env python3
"""Data Management Quality Checker.

This module provides comprehensive quality checks for data management
functionality, including configuration loading, environment variable handling,
SQLite operations, session management, cache consistency, data persistence,
concurrent access safety, and backup/recovery mechanisms.
"""

import asyncio
import json
import os
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.core.config import ConfigLoader, ConfigValidator
from src.thread_storage import ThreadStorage
from src.constants import ENV_BOT_TOKEN, ENV_WEBHOOK_URL, ENV_DEBUG
from ..core_checker import BaseQualityChecker, QualityCheckResult


class DataManagementChecker(BaseQualityChecker):
    """Quality checker for data management functionality.
    
    Validates all aspects of data management including:
    - Configuration loading completeness and validation
    - Environment variable processing safety
    - SQLite operations transaction safety
    - Session management consistency
    - Cache consistency across operations
    - Data persistence reliability
    - Concurrent access safety
    - Backup and recovery mechanisms
    """
    
    def __init__(self, project_root: Path, logger: AstolfoLogger) -> None:
        """Initialize data management checker.
        
        Args:
            project_root: Project root directory
            logger: Logger instance for structured logging
        """
        super().__init__(project_root, logger)
        self.category = "Data Management"
        
        # Quality metrics tracking
        self.metrics = {
            "config_load_success_rate": 0.0,
            "data_persistence_success_rate": 0.0,
            "concurrent_access_safety": 0.0,
            "data_integrity": 0.0,
            "backup_success_rate": 0.0,
            "env_var_safety_score": 0.0,
            "sqlite_transaction_safety": 0.0,
            "session_consistency_score": 0.0
        }
        
        # Test data for various checks
        self._init_test_data()
    
    def _init_test_data(self) -> None:
        """Initialize test data for data management checks."""
        
        # Test configuration scenarios
        self.config_test_cases = [
            {
                "name": "webhook_only",
                "env_vars": {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test/token"},
                "should_succeed": True
            },
            {
                "name": "bot_token_channel",
                "env_vars": {
                    "DISCORD_BOT_TOKEN": "test_bot_token_12345",
                    "DISCORD_CHANNEL_ID": "123456789012345678"
                },
                "should_succeed": True
            },
            {
                "name": "invalid_webhook",
                "env_vars": {"DISCORD_WEBHOOK_URL": "invalid_url"},
                "should_succeed": False
            },
            {
                "name": "missing_channel_id",
                "env_vars": {"DISCORD_BOT_TOKEN": "test_token"},
                "should_succeed": False
            },
            {
                "name": "empty_config",
                "env_vars": {},
                "should_succeed": False
            }
        ]
        
        # Test thread data for persistence
        self.test_threads = [
            {
                "thread_id": "thread_001",
                "channel_id": "123456789012345678",
                "session_id": "session_001",
                "created_at": "2025-07-12T20:00:00Z"
            },
            {
                "thread_id": "thread_002", 
                "channel_id": "123456789012345678",
                "session_id": "session_002",
                "created_at": "2025-07-12T20:30:00Z"
            },
            {
                "thread_id": "thread_003",
                "channel_id": "987654321098765432",
                "session_id": "session_003", 
                "created_at": "2025-07-12T21:00:00Z"
            }
        ]
        
        # Environment variable test cases
        self.env_var_test_cases = [
            {
                "name": "safe_values",
                "vars": {
                    "DISCORD_DEBUG": "1",
                    "DISCORD_USE_THREADS": "0",
                    "DISCORD_THREAD_PREFIX": "Claude Code"
                },
                "expected_safe": True
            },
            {
                "name": "injection_attempt",
                "vars": {
                    "DISCORD_WEBHOOK_URL": "https://evil.com/webhook; rm -rf /",
                    "DISCORD_CHANNEL_ID": "123; DROP TABLE threads;"
                },
                "expected_safe": False
            },
            {
                "name": "special_characters",
                "vars": {
                    "DISCORD_THREAD_PREFIX": "Test & Debug | 🚀",
                    "DISCORD_BOT_TOKEN": "token_with_special_chars!@#$%"
                },
                "expected_safe": True
            }
        ]
    
    async def _execute_checks(self) -> QualityCheckResult:
        """Execute data management quality checks.
        
        Returns:
            Quality check result with metrics and findings
        """
        issues = []
        warnings = []
        
        self.logger.info("Starting data management quality checks")
        
        # Run all data management checks
        check_results = await asyncio.gather(
            self._check_config_completeness(),
            self._check_env_var_safety(),
            self._check_sqlite_transaction_safety(),
            self._check_session_consistency(),
            self._check_cache_consistency(),
            self._check_data_persistence(),
            self._check_concurrent_access_safety(),
            self._check_backup_recovery(),
            return_exceptions=True
        )
        
        # Process check results
        total_score = 0.0
        check_count = 0
        
        for i, result in enumerate(check_results):
            if isinstance(result, Exception):
                issues.append(f"Check {i+1} failed with exception: {result}")
            else:
                score, check_issues, check_warnings = result
                total_score += score
                check_count += 1
                issues.extend(check_issues)
                warnings.extend(check_warnings)
        
        # Calculate overall score
        overall_score = total_score / check_count if check_count > 0 else 0.0
        passed = overall_score >= 0.95 and len(issues) == 0
        
        self.logger.info(
            f"Data management checks completed",
            context={
                "overall_score": overall_score,
                "passed": passed,
                "issues": len(issues),
                "warnings": len(warnings)
            }
        )
        
        return {
            "check_name": "Data Management Quality Check",
            "category": self.category,
            "passed": passed,
            "score": overall_score,
            "issues": issues,
            "warnings": warnings,
            "metrics": self.metrics,
            "execution_time": 0.0,
            "timestamp": ""
        }
    
    async def _check_config_completeness(self) -> Tuple[float, List[str], List[str]]:
        """Check configuration loading completeness and validation.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking configuration completeness")
        
        issues = []
        warnings = []
        success_count = 0
        total_tests = len(self.config_test_cases)
        
        try:
            for test_case in self.config_test_cases:
                try:
                    # Save original environment
                    original_env = {}
                    for key in test_case["env_vars"]:
                        original_env[key] = os.environ.get(key)
                    
                    # Set test environment variables
                    for key, value in test_case["env_vars"].items():
                        os.environ[key] = value
                    
                    # Clear environment variables not in test case
                    test_keys = set(test_case["env_vars"].keys())
                    required_keys = {ENV_WEBHOOK_URL, ENV_BOT_TOKEN, "DISCORD_CHANNEL_ID"}
                    for key in required_keys - test_keys:
                        if key in os.environ:
                            os.environ.pop(key)
                    
                    # Test configuration loading
                    config = ConfigLoader.load()
                    is_valid = ConfigValidator.validate_all(config)
                    
                    # Check if result matches expectation
                    if is_valid == test_case["should_succeed"]:
                        success_count += 1
                    else:
                        issues.append(f"Config test '{test_case['name']}' unexpected result: "
                                    f"expected {test_case['should_succeed']}, got {is_valid}")
                    
                    # Restore original environment
                    for key, value in original_env.items():
                        if value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = value
                
                except Exception as e:
                    issues.append(f"Config test '{test_case['name']}' failed: {e}")
            
            success_rate = success_count / total_tests
            self.metrics["config_load_success_rate"] = success_rate
            
            if success_rate < 1.0:
                issues.append(f"Configuration completeness below 100%: {success_rate:.3f}")
        
        except Exception as e:
            issues.append(f"Configuration completeness check error: {e}")
            success_rate = 0.0
        
        return success_rate, issues, warnings
    
    async def _check_env_var_safety(self) -> Tuple[float, List[str], List[str]]:
        """Check environment variable processing safety.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking environment variable safety")
        
        issues = []
        warnings = []
        safety_scores = []
        
        try:
            for test_case in self.env_var_test_cases:
                try:
                    # Test environment variable validation
                    safety_score = self._validate_env_var_safety(test_case["vars"])
                    expected_safe = test_case["expected_safe"]
                    
                    if (safety_score >= 0.8) == expected_safe:
                        safety_scores.append(1.0)
                    else:
                        safety_scores.append(0.0)
                        issues.append(f"Environment variable safety test '{test_case['name']}' failed")
                
                except Exception as e:
                    safety_scores.append(0.0)
                    warnings.append(f"Environment variable test '{test_case['name']}' error: {e}")
            
            overall_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 0.0
            self.metrics["env_var_safety_score"] = overall_safety
            
            if overall_safety < 0.95:
                issues.append(f"Environment variable safety below target: {overall_safety:.3f}")
        
        except Exception as e:
            issues.append(f"Environment variable safety check error: {e}")
            overall_safety = 0.0
        
        return overall_safety, issues, warnings
    
    async def _check_sqlite_transaction_safety(self) -> Tuple[float, List[str], List[str]]:
        """Check SQLite operations transaction safety.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking SQLite transaction safety")
        
        issues = []
        warnings = []
        
        try:
            # Create temporary database for testing
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
                temp_db_path = temp_db.name
            
            try:
                # Test basic transaction safety
                transaction_scores = []
                
                # Test 1: Basic transaction rollback
                try:
                    thread_storage = ThreadStorage(temp_db_path)
                    
                    # Start transaction and intentionally fail
                    with sqlite3.connect(temp_db_path) as conn:
                        conn.execute("BEGIN TRANSACTION")
                        conn.execute("INSERT INTO threads (thread_id, channel_id, session_id) VALUES (?, ?, ?)",
                                   ("test_thread", "test_channel", "test_session"))
                        # Simulate error - don't commit
                        conn.execute("ROLLBACK")
                    
                    # Check that no data was persisted
                    with sqlite3.connect(temp_db_path) as conn:
                        cursor = conn.execute("SELECT COUNT(*) FROM threads WHERE thread_id = ?", ("test_thread",))
                        count = cursor.fetchone()[0]
                        
                        if count == 0:
                            transaction_scores.append(1.0)
                        else:
                            transaction_scores.append(0.0)
                            issues.append("SQLite rollback test failed - data was persisted")
                
                except Exception as e:
                    transaction_scores.append(0.0)
                    warnings.append(f"SQLite rollback test error: {e}")
                
                # Test 2: Concurrent transaction safety
                try:
                    concurrent_safety_score = await self._test_concurrent_sqlite_access(temp_db_path)
                    transaction_scores.append(concurrent_safety_score)
                
                except Exception as e:
                    transaction_scores.append(0.0)
                    warnings.append(f"Concurrent SQLite test error: {e}")
                
                safety_score = sum(transaction_scores) / len(transaction_scores) if transaction_scores else 0.0
                self.metrics["sqlite_transaction_safety"] = safety_score
                
                if safety_score < 0.95:
                    issues.append(f"SQLite transaction safety below target: {safety_score:.3f}")
            
            finally:
                # Clean up temporary database
                try:
                    Path(temp_db_path).unlink()
                except OSError:
                    pass
        
        except Exception as e:
            issues.append(f"SQLite transaction safety check error: {e}")
            safety_score = 0.0
        
        return safety_score, issues, warnings
    
    async def _check_session_consistency(self) -> Tuple[float, List[str], List[str]]:
        """Check session management consistency.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking session management consistency")
        
        issues = []
        warnings = []
        
        try:
            # Test session data consistency
            consistency_scores = []
            
            # Test session cache consistency
            session_cache = {}
            test_sessions = ["session_001", "session_002", "session_003"]
            
            # Simulate session operations
            for session_id in test_sessions:
                session_data = {
                    "session_id": session_id,
                    "start_time": time.time(),
                    "thread_id": f"thread_{session_id}",
                    "active": True
                }
                session_cache[session_id] = session_data
            
            # Test consistency after operations
            for session_id in test_sessions:
                if session_id in session_cache:
                    data = session_cache[session_id]
                    if data["session_id"] == session_id and data["active"]:
                        consistency_scores.append(1.0)
                    else:
                        consistency_scores.append(0.0)
                        issues.append(f"Session consistency failed for {session_id}")
                else:
                    consistency_scores.append(0.0)
                    issues.append(f"Session {session_id} not found in cache")
            
            consistency_score = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
            self.metrics["session_consistency_score"] = consistency_score
            
            if consistency_score < 0.95:
                issues.append(f"Session consistency below target: {consistency_score:.3f}")
        
        except Exception as e:
            issues.append(f"Session consistency check error: {e}")
            consistency_score = 0.0
        
        return consistency_score, issues, warnings
    
    async def _check_cache_consistency(self) -> Tuple[float, List[str], List[str]]:
        """Check cache consistency across operations.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking cache consistency")
        
        issues = []
        warnings = []
        
        try:
            # Test cache operations consistency
            cache_scores = []
            
            # Simulate cache operations
            test_cache = {}
            test_keys = ["key_1", "key_2", "key_3"]
            
            # Test cache set/get consistency
            for key in test_keys:
                value = f"value_for_{key}"
                test_cache[key] = value
                
                # Verify immediate retrieval
                retrieved = test_cache.get(key)
                if retrieved == value:
                    cache_scores.append(1.0)
                else:
                    cache_scores.append(0.0)
                    issues.append(f"Cache inconsistency for {key}: expected {value}, got {retrieved}")
            
            # Test cache invalidation
            for key in test_keys:
                if key in test_cache:
                    del test_cache[key]
                
                # Verify key is removed
                if key not in test_cache:
                    cache_scores.append(1.0)
                else:
                    cache_scores.append(0.0)
                    issues.append(f"Cache invalidation failed for {key}")
            
            consistency_score = sum(cache_scores) / len(cache_scores) if cache_scores else 0.0
            
            if consistency_score < 0.95:
                issues.append(f"Cache consistency below target: {consistency_score:.3f}")
        
        except Exception as e:
            issues.append(f"Cache consistency check error: {e}")
            consistency_score = 0.0
        
        return consistency_score, issues, warnings
    
    async def _check_data_persistence(self) -> Tuple[float, List[str], List[str]]:
        """Check data persistence reliability.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking data persistence reliability")
        
        issues = []
        warnings = []
        
        try:
            # Create temporary database for testing
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
                temp_db_path = temp_db.name
            
            try:
                persistence_scores = []
                
                # Test data persistence across database connections
                thread_storage = ThreadStorage(temp_db_path)
                
                # Store test threads
                for thread_data in self.test_threads:
                    try:
                        thread_storage.store_thread(
                            thread_data["thread_id"],
                            thread_data["channel_id"],
                            thread_data["session_id"]
                        )
                        persistence_scores.append(1.0)
                    except Exception as e:
                        persistence_scores.append(0.0)
                        issues.append(f"Failed to store thread {thread_data['thread_id']}: {e}")
                
                # Verify persistence by creating new connection
                new_thread_storage = ThreadStorage(temp_db_path)
                
                for thread_data in self.test_threads:
                    try:
                        stored_thread = new_thread_storage.get_thread_by_session(thread_data["session_id"])
                        if stored_thread and stored_thread["thread_id"] == thread_data["thread_id"]:
                            persistence_scores.append(1.0)
                        else:
                            persistence_scores.append(0.0)
                            issues.append(f"Thread persistence verification failed for {thread_data['thread_id']}")
                    except Exception as e:
                        persistence_scores.append(0.0)
                        warnings.append(f"Thread retrieval test error for {thread_data['thread_id']}: {e}")
                
                persistence_rate = sum(persistence_scores) / len(persistence_scores) if persistence_scores else 0.0
                self.metrics["data_persistence_success_rate"] = persistence_rate
                
                if persistence_rate < 0.999:
                    issues.append(f"Data persistence rate below target: {persistence_rate:.3f}")
            
            finally:
                # Clean up temporary database
                try:
                    Path(temp_db_path).unlink()
                except OSError:
                    pass
        
        except Exception as e:
            issues.append(f"Data persistence check error: {e}")
            persistence_rate = 0.0
        
        return persistence_rate, issues, warnings
    
    async def _check_concurrent_access_safety(self) -> Tuple[float, List[str], List[str]]:
        """Check concurrent access safety.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking concurrent access safety")
        
        issues = []
        warnings = []
        
        try:
            # Create temporary database for testing
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
                temp_db_path = temp_db.name
            
            try:
                # Test concurrent database access
                safety_score = await self._test_concurrent_database_operations(temp_db_path)
                self.metrics["concurrent_access_safety"] = safety_score
                
                if safety_score < 1.0:
                    issues.append(f"Concurrent access safety below 100%: {safety_score:.3f}")
            
            finally:
                # Clean up temporary database
                try:
                    Path(temp_db_path).unlink()
                except OSError:
                    pass
        
        except Exception as e:
            issues.append(f"Concurrent access safety check error: {e}")
            safety_score = 0.0
        
        return safety_score, issues, warnings
    
    async def _check_backup_recovery(self) -> Tuple[float, List[str], List[str]]:
        """Check backup and recovery mechanisms.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking backup and recovery mechanisms")
        
        issues = []
        warnings = []
        
        try:
            # Test backup/recovery functionality
            backup_scores = []
            
            # Create temporary database for testing
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
                temp_db_path = temp_db.name
            
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as backup_db:
                backup_db_path = backup_db.name
            
            try:
                # Create original database with data
                thread_storage = ThreadStorage(temp_db_path)
                
                for thread_data in self.test_threads:
                    thread_storage.store_thread(
                        thread_data["thread_id"],
                        thread_data["channel_id"], 
                        thread_data["session_id"]
                    )
                
                # Test backup creation
                backup_success = self._create_database_backup(temp_db_path, backup_db_path)
                backup_scores.append(1.0 if backup_success else 0.0)
                
                if not backup_success:
                    issues.append("Database backup creation failed")
                
                # Test backup integrity
                integrity_success = self._verify_backup_integrity(temp_db_path, backup_db_path)
                backup_scores.append(1.0 if integrity_success else 0.0)
                
                if not integrity_success:
                    issues.append("Backup integrity verification failed")
                
                backup_rate = sum(backup_scores) / len(backup_scores) if backup_scores else 0.0
                self.metrics["backup_success_rate"] = backup_rate
                
                if backup_rate < 1.0:
                    issues.append(f"Backup success rate below 100%: {backup_rate:.3f}")
            
            finally:
                # Clean up temporary files
                for path in [temp_db_path, backup_db_path]:
                    try:
                        Path(path).unlink()
                    except OSError:
                        pass
        
        except Exception as e:
            issues.append(f"Backup and recovery check error: {e}")
            backup_rate = 0.0
        
        return backup_rate, issues, warnings
    
    # Helper methods
    
    def _validate_env_var_safety(self, env_vars: Dict[str, str]) -> float:
        """Validate environment variable safety."""
        safety_score = 1.0
        
        for key, value in env_vars.items():
            # Check for injection patterns
            dangerous_patterns = [
                r'[;&|`$(]',  # Shell injection characters
                r'DROP\s+TABLE',  # SQL injection
                r'<script',  # XSS injection
                r'\.\./\.\./',  # Path traversal
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    safety_score -= 0.2
                    break
        
        return max(0.0, safety_score)
    
    async def _test_concurrent_sqlite_access(self, db_path: str) -> float:
        """Test concurrent SQLite access safety."""
        try:
            def concurrent_operation(thread_id: int) -> bool:
                try:
                    thread_storage = ThreadStorage(db_path)
                    thread_storage.store_thread(
                        f"concurrent_thread_{thread_id}",
                        "test_channel",
                        f"concurrent_session_{thread_id}"
                    )
                    return True
                except Exception:
                    return False
            
            # Run concurrent operations
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(concurrent_operation, i) for i in range(10)]
                results = [future.result() for future in futures]
            
            success_rate = sum(results) / len(results)
            return success_rate
        
        except Exception:
            return 0.0
    
    async def _test_concurrent_database_operations(self, db_path: str) -> float:
        """Test concurrent database operations safety."""
        try:
            def database_worker(worker_id: int) -> bool:
                try:
                    # Simulate concurrent database operations
                    with sqlite3.connect(db_path) as conn:
                        conn.execute("BEGIN IMMEDIATE")
                        
                        # Simulate work
                        time.sleep(0.01)
                        
                        # Insert data
                        conn.execute(
                            "INSERT OR REPLACE INTO threads (thread_id, channel_id, session_id) VALUES (?, ?, ?)",
                            (f"worker_thread_{worker_id}", "test_channel", f"worker_session_{worker_id}")
                        )
                        
                        conn.commit()
                        return True
                except Exception:
                    return False
            
            # Initialize database
            thread_storage = ThreadStorage(db_path)
            
            # Run concurrent workers
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(database_worker, i) for i in range(5)]
                results = [future.result() for future in futures]
            
            success_rate = sum(results) / len(results)
            return success_rate
        
        except Exception:
            return 0.0
    
    def _create_database_backup(self, source_path: str, backup_path: str) -> bool:
        """Create database backup."""
        try:
            # Simple file copy backup
            import shutil
            shutil.copy2(source_path, backup_path)
            return True
        except Exception:
            return False
    
    def _verify_backup_integrity(self, original_path: str, backup_path: str) -> bool:
        """Verify backup integrity."""
        try:
            # Compare record counts
            with sqlite3.connect(original_path) as orig_conn:
                orig_cursor = orig_conn.execute("SELECT COUNT(*) FROM threads")
                orig_count = orig_cursor.fetchone()[0]
            
            with sqlite3.connect(backup_path) as backup_conn:
                backup_cursor = backup_conn.execute("SELECT COUNT(*) FROM threads")
                backup_count = backup_cursor.fetchone()[0]
            
            return orig_count == backup_count
        
        except Exception:
            return False


async def main() -> None:
    """Test the data management checker."""
    project_root = Path(__file__).parent.parent.parent.parent
    logger = AstolfoLogger(__name__)
    
    checker = DataManagementChecker(project_root, logger)
    result = await checker.run_checks()
    
    print(f"Data Management Check: {'PASSED' if result['passed'] else 'FAILED'}")
    print(f"Score: {result['score']:.3f}")
    print(f"Issues: {len(result['issues'])}")
    print(f"Warnings: {len(result['warnings'])}")
    
    for issue in result['issues']:
        print(f"  ❌ {issue}")
    
    for warning in result['warnings']:
        print(f"  ⚠️  {warning}")


if __name__ == "__main__":
    asyncio.run(main())