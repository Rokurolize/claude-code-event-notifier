#!/usr/bin/env python3
"""Test SQLite Operations Functionality.

This module provides comprehensive tests for SQLite database operations
functionality, including transaction safety, concurrent access, data integrity,
backup and recovery, schema migration, and performance optimization.
"""

import asyncio
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.thread_storage import ThreadStorage
from src.exceptions import DatabaseError, TransactionError


class TestSQLiteOperations(unittest.IsolatedAsyncioTestCase):
    """Test cases for SQLite operations functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "database_mode": "test",
            "transaction_safety": True,
            "concurrent_access": True,
            "backup_enabled": True,
            "debug": True
        }
        
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Test thread storage data
        self.test_thread_data = [
            {
                "session_id": "test_session_001",
                "thread_id": "123456789012345678",
                "thread_name": "Test Thread 1",
                "channel_id": "987654321098765432",
                "created_at": "2025-07-12T22:00:00.000Z",
                "last_used": "2025-07-12T22:05:00.000Z",
                "is_archived": False,
                "message_count": 5
            },
            {
                "session_id": "test_session_002",
                "thread_id": "234567890123456789",
                "thread_name": "Test Thread 2",
                "channel_id": "987654321098765432",
                "created_at": "2025-07-12T21:30:00.000Z",
                "last_used": "2025-07-12T21:45:00.000Z",
                "is_archived": False,
                "message_count": 12
            },
            {
                "session_id": "test_session_003",
                "thread_id": "345678901234567890",
                "thread_name": "Archived Thread",
                "channel_id": "987654321098765432",
                "created_at": "2025-07-12T20:00:00.000Z",
                "last_used": "2025-07-12T20:30:00.000Z",
                "is_archived": True,
                "message_count": 8
            }
        ]
        
        # Database schema for testing
        self.test_schema = {
            "threads": {
                "columns": [
                    ("session_id", "TEXT PRIMARY KEY"),
                    ("thread_id", "TEXT UNIQUE NOT NULL"),
                    ("thread_name", "TEXT"),
                    ("channel_id", "TEXT"),
                    ("created_at", "TEXT"),
                    ("last_used", "TEXT"),
                    ("is_archived", "BOOLEAN DEFAULT 0"),
                    ("message_count", "INTEGER DEFAULT 0")
                ],
                "indexes": [
                    ("idx_thread_id", "thread_id"),
                    ("idx_channel_id", "channel_id"),
                    ("idx_last_used", "last_used"),
                    ("idx_archived", "is_archived")
                ]
            },
            "sessions": {
                "columns": [
                    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
                    ("session_id", "TEXT UNIQUE NOT NULL"),
                    ("start_time", "TEXT"),
                    ("end_time", "TEXT"),
                    ("tool_count", "INTEGER DEFAULT 0"),
                    ("error_count", "INTEGER DEFAULT 0"),
                    ("status", "TEXT DEFAULT 'active'")
                ],
                "indexes": [
                    ("idx_session_id", "session_id"),
                    ("idx_status", "status"),
                    ("idx_start_time", "start_time")
                ]
            }
        }
        
        # Performance test scenarios
        self.performance_scenarios = {
            "small_dataset": {"records": 100, "concurrent_operations": 5},
            "medium_dataset": {"records": 1000, "concurrent_operations": 10},
            "large_dataset": {"records": 10000, "concurrent_operations": 20}
        }
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        try:
            Path(self.db_path).unlink(missing_ok=True)
        except Exception:
            pass
    
    async def test_transaction_safety_validation(self) -> None:
        """Test transaction safety and ACID compliance."""
        with patch('src.thread_storage.ThreadStorage') as mock_thread_storage:
            mock_instance = MagicMock()
            mock_thread_storage.return_value = mock_instance
            
            # Configure transaction safety testing
            def create_database_connection(db_path: str) -> sqlite3.Connection:
                """Create a test database connection."""
                conn = sqlite3.connect(db_path, isolation_level=None)
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = FULL")
                return conn
            
            def test_transaction_rollback(conn: sqlite3.Connection) -> Dict[str, Any]:
                """Test transaction rollback functionality."""
                rollback_result = {
                    "rollback_successful": True,
                    "data_consistency": True,
                    "error_handling": True,
                    "transaction_log": []
                }
                
                try:
                    # Start transaction
                    conn.execute("BEGIN TRANSACTION")
                    rollback_result["transaction_log"].append("Transaction started")
                    
                    # Insert test data
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS test_rollback (
                            id INTEGER PRIMARY KEY,
                            value TEXT
                        )
                    """)
                    rollback_result["transaction_log"].append("Table created")
                    
                    conn.execute("INSERT INTO test_rollback (value) VALUES (?)", ("test_value",))
                    rollback_result["transaction_log"].append("Data inserted")
                    
                    # Verify data exists
                    cursor = conn.execute("SELECT COUNT(*) FROM test_rollback")
                    count_before = cursor.fetchone()[0]
                    rollback_result["transaction_log"].append(f"Count before rollback: {count_before}")
                    
                    # Force rollback
                    conn.execute("ROLLBACK")
                    rollback_result["transaction_log"].append("Transaction rolled back")
                    
                    # Verify data was rolled back
                    try:
                        cursor = conn.execute("SELECT COUNT(*) FROM test_rollback")
                        count_after = cursor.fetchone()[0]
                        rollback_result["transaction_log"].append(f"Count after rollback: {count_after}")
                        
                        if count_after == 0:
                            rollback_result["data_consistency"] = True
                        else:
                            rollback_result["data_consistency"] = False
                            rollback_result["rollback_successful"] = False
                    except sqlite3.OperationalError:
                        # Table doesn't exist - perfect rollback
                        rollback_result["data_consistency"] = True
                        rollback_result["transaction_log"].append("Table properly rolled back")
                
                except Exception as e:
                    rollback_result["rollback_successful"] = False
                    rollback_result["error_handling"] = False
                    rollback_result["transaction_log"].append(f"Error: {e}")
                
                return rollback_result
            
            def test_transaction_commit(conn: sqlite3.Connection) -> Dict[str, Any]:
                """Test transaction commit functionality."""
                commit_result = {
                    "commit_successful": True,
                    "data_persisted": True,
                    "isolation_maintained": True,
                    "transaction_log": []
                }
                
                try:
                    # Start transaction
                    conn.execute("BEGIN TRANSACTION")
                    commit_result["transaction_log"].append("Transaction started")
                    
                    # Create and populate test table
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS test_commit (
                            id INTEGER PRIMARY KEY,
                            value TEXT,
                            timestamp TEXT
                        )
                    """)
                    commit_result["transaction_log"].append("Table created")
                    
                    # Insert multiple records
                    test_data = [
                        ("value1", "2025-07-12T22:00:00.000Z"),
                        ("value2", "2025-07-12T22:01:00.000Z"),
                        ("value3", "2025-07-12T22:02:00.000Z")
                    ]
                    
                    for value, timestamp in test_data:
                        conn.execute("INSERT INTO test_commit (value, timestamp) VALUES (?, ?)", (value, timestamp))
                    
                    commit_result["transaction_log"].append(f"Inserted {len(test_data)} records")
                    
                    # Commit transaction
                    conn.execute("COMMIT")
                    commit_result["transaction_log"].append("Transaction committed")
                    
                    # Verify data persistence
                    cursor = conn.execute("SELECT COUNT(*) FROM test_commit")
                    count = cursor.fetchone()[0]
                    
                    if count == len(test_data):
                        commit_result["data_persisted"] = True
                        commit_result["transaction_log"].append(f"All {count} records persisted")
                    else:
                        commit_result["data_persisted"] = False
                        commit_result["commit_successful"] = False
                        commit_result["transaction_log"].append(f"Data loss: expected {len(test_data)}, got {count}")
                
                except Exception as e:
                    commit_result["commit_successful"] = False
                    commit_result["transaction_log"].append(f"Error: {e}")
                
                return commit_result
            
            mock_instance.create_database_connection.side_effect = create_database_connection
            mock_instance.test_transaction_rollback.side_effect = test_transaction_rollback
            mock_instance.test_transaction_commit.side_effect = test_transaction_commit
            
            thread_storage = ThreadStorage(self.db_path)
            
            # Create database connection
            conn = thread_storage.create_database_connection(self.db_path)
            
            # Test transaction rollback
            rollback_result = thread_storage.test_transaction_rollback(conn)
            
            self.assertTrue(rollback_result["rollback_successful"],
                           f"Transaction rollback failed: {rollback_result['transaction_log']}")
            self.assertTrue(rollback_result["data_consistency"],
                           "Data consistency violated during rollback")
            self.assertTrue(rollback_result["error_handling"],
                           "Error handling failed during rollback test")
            
            # Test transaction commit
            commit_result = thread_storage.test_transaction_commit(conn)
            
            self.assertTrue(commit_result["commit_successful"],
                          f"Transaction commit failed: {commit_result['transaction_log']}")
            self.assertTrue(commit_result["data_persisted"],
                          "Data not properly persisted after commit")
            
            conn.close()
    
    async def test_concurrent_access_safety(self) -> None:
        """Test safe concurrent access to SQLite database."""
        # Create actual database for concurrent testing
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS concurrent_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_name TEXT,
                value INTEGER,
                timestamp TEXT
            )
        """)
        conn.close()
        
        # Results tracking
        results = {
            "successful_operations": 0,
            "failed_operations": 0,
            "conflicts": 0,
            "data_integrity_issues": 0,
            "operation_log": []
        }
        results_lock = threading.Lock()
        
        def concurrent_database_operation(thread_id: int, operation_count: int) -> None:
            """Perform concurrent database operations."""
            thread_name = f"thread_{thread_id}"
            
            try:
                # Create connection for this thread
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                conn.execute("PRAGMA busy_timeout = 30000")
                
                for i in range(operation_count):
                    try:
                        # Start transaction
                        conn.execute("BEGIN IMMEDIATE")
                        
                        # Insert data
                        timestamp = f"2025-07-12T22:{thread_id:02d}:{i:02d}.000Z"
                        conn.execute(
                            "INSERT INTO concurrent_test (thread_name, value, timestamp) VALUES (?, ?, ?)",
                            (thread_name, i, timestamp)
                        )
                        
                        # Simulate some processing time
                        time.sleep(0.001)
                        
                        # Update existing data
                        conn.execute(
                            "UPDATE concurrent_test SET value = value + 1 WHERE thread_name = ? AND value < ?",
                            (thread_name, i)
                        )
                        
                        # Commit transaction
                        conn.execute("COMMIT")
                        
                        with results_lock:
                            results["successful_operations"] += 1
                            results["operation_log"].append(f"{thread_name}: operation {i} completed")
                    
                    except sqlite3.OperationalError as e:
                        # Handle database locked/busy errors
                        try:
                            conn.execute("ROLLBACK")
                        except:
                            pass
                        
                        with results_lock:
                            if "locked" in str(e).lower() or "busy" in str(e).lower():
                                results["conflicts"] += 1
                                results["operation_log"].append(f"{thread_name}: conflict in operation {i}")
                            else:
                                results["failed_operations"] += 1
                                results["operation_log"].append(f"{thread_name}: error in operation {i}: {e}")
                    
                    except Exception as e:
                        try:
                            conn.execute("ROLLBACK")
                        except:
                            pass
                        
                        with results_lock:
                            results["failed_operations"] += 1
                            results["operation_log"].append(f"{thread_name}: unexpected error in operation {i}: {e}")
                
                conn.close()
            
            except Exception as e:
                with results_lock:
                    results["failed_operations"] += operation_count
                    results["operation_log"].append(f"{thread_name}: connection error: {e}")
        
        # Test concurrent access with multiple threads
        concurrent_threads = 5
        operations_per_thread = 10
        
        threads = []
        for i in range(concurrent_threads):
            thread = threading.Thread(
                target=concurrent_database_operation,
                args=(i, operations_per_thread)
            )
            threads.append(thread)
        
        # Start all threads simultaneously
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30.0)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify data integrity
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM concurrent_test")
        total_records = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT thread_name, COUNT(*) FROM concurrent_test GROUP BY thread_name")
        thread_counts = dict(cursor.fetchall())
        conn.close()
        
        # Analyze results
        expected_total_operations = concurrent_threads * operations_per_thread
        actual_successful = results["successful_operations"]
        
        self.assertGreater(actual_successful, 0,
                         "No operations completed successfully")
        
        # Allow for some conflicts due to concurrent access, but ensure most operations succeed
        success_rate = actual_successful / expected_total_operations
        self.assertGreaterEqual(success_rate, 0.8,
                              f"Success rate too low: {success_rate:.2f}")
        
        # Verify no data integrity issues
        for thread_name, count in thread_counts.items():
            self.assertGreaterEqual(count, 1,
                                  f"Thread {thread_name} had no successful operations")
        
        # Log concurrent access analysis
        self.logger.info(
            "Concurrent access test analysis",
            context={
                "total_threads": concurrent_threads,
                "operations_per_thread": operations_per_thread,
                "successful_operations": results["successful_operations"],
                "failed_operations": results["failed_operations"],
                "conflicts": results["conflicts"],
                "success_rate": success_rate,
                "total_time": total_time,
                "operations_per_second": actual_successful / total_time if total_time > 0 else 0,
                "thread_record_counts": thread_counts
            }
        )
    
    async def test_data_integrity_validation(self) -> None:
        """Test data integrity constraints and validation."""
        with patch('src.thread_storage.ThreadStorage') as mock_thread_storage:
            mock_instance = MagicMock()
            mock_thread_storage.return_value = mock_instance
            
            # Configure data integrity testing
            def setup_database_with_constraints(db_path: str) -> sqlite3.Connection:
                """Set up database with integrity constraints."""
                conn = sqlite3.connect(db_path)
                
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Create tables with constraints
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_sessions (
                        session_id TEXT PRIMARY KEY,
                        start_time TEXT NOT NULL,
                        status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'error')),
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_threads (
                        thread_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        thread_name TEXT NOT NULL,
                        message_count INTEGER NOT NULL CHECK (message_count >= 0),
                        is_archived BOOLEAN NOT NULL DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES test_sessions (session_id) ON DELETE CASCADE
                    )
                """)
                
                # Create unique indexes
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_thread_session ON test_threads (session_id, thread_name)")
                
                return conn
            
            def test_constraint_violations(conn: sqlite3.Connection) -> Dict[str, Any]:
                """Test various constraint violations."""
                violation_results = {
                    "primary_key_violations": [],
                    "foreign_key_violations": [],
                    "check_constraint_violations": [],
                    "unique_constraint_violations": [],
                    "not_null_violations": []
                }
                
                # Test primary key violation
                try:
                    conn.execute("INSERT INTO test_sessions (session_id, start_time, status) VALUES (?, ?, ?)",
                               ("session_001", "2025-07-12T22:00:00.000Z", "active"))
                    conn.execute("INSERT INTO test_sessions (session_id, start_time, status) VALUES (?, ?, ?)",
                               ("session_001", "2025-07-12T22:01:00.000Z", "active"))  # Duplicate primary key
                    violation_results["primary_key_violations"].append("Primary key violation not detected")
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint" in str(e) or "PRIMARY KEY constraint" in str(e):
                        violation_results["primary_key_violations"].append("Primary key violation correctly detected")
                    else:
                        violation_results["primary_key_violations"].append(f"Unexpected error: {e}")
                
                # Test foreign key violation
                try:
                    conn.execute("INSERT INTO test_threads (thread_id, session_id, thread_name, message_count) VALUES (?, ?, ?, ?)",
                               ("thread_001", "nonexistent_session", "Test Thread", 0))
                    violation_results["foreign_key_violations"].append("Foreign key violation not detected")
                except sqlite3.IntegrityError as e:
                    if "FOREIGN KEY constraint" in str(e):
                        violation_results["foreign_key_violations"].append("Foreign key violation correctly detected")
                    else:
                        violation_results["foreign_key_violations"].append(f"Unexpected error: {e}")
                
                # Test check constraint violation
                try:
                    conn.execute("INSERT INTO test_sessions (session_id, start_time, status) VALUES (?, ?, ?)",
                               ("session_002", "2025-07-12T22:00:00.000Z", "invalid_status"))
                    violation_results["check_constraint_violations"].append("Check constraint violation not detected")
                except sqlite3.IntegrityError as e:
                    if "CHECK constraint" in str(e):
                        violation_results["check_constraint_violations"].append("Check constraint violation correctly detected")
                    else:
                        violation_results["check_constraint_violations"].append(f"Unexpected error: {e}")
                
                # Test NOT NULL violation
                try:
                    conn.execute("INSERT INTO test_sessions (session_id, start_time, status) VALUES (?, ?, ?)",
                               ("session_003", None, "active"))
                    violation_results["not_null_violations"].append("NOT NULL violation not detected")
                except sqlite3.IntegrityError as e:
                    if "NOT NULL constraint" in str(e):
                        violation_results["not_null_violations"].append("NOT NULL violation correctly detected")
                    else:
                        violation_results["not_null_violations"].append(f"Unexpected error: {e}")
                
                # Test unique constraint violation
                try:
                    # Insert valid session first
                    conn.execute("INSERT INTO test_sessions (session_id, start_time, status) VALUES (?, ?, ?)",
                               ("session_004", "2025-07-12T22:00:00.000Z", "active"))
                    
                    # Insert first thread
                    conn.execute("INSERT INTO test_threads (thread_id, session_id, thread_name, message_count) VALUES (?, ?, ?, ?)",
                               ("thread_002", "session_004", "Unique Thread", 0))
                    
                    # Try to insert duplicate session_id + thread_name combination
                    conn.execute("INSERT INTO test_threads (thread_id, session_id, thread_name, message_count) VALUES (?, ?, ?, ?)",
                               ("thread_003", "session_004", "Unique Thread", 5))
                    
                    violation_results["unique_constraint_violations"].append("Unique constraint violation not detected")
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint" in str(e):
                        violation_results["unique_constraint_violations"].append("Unique constraint violation correctly detected")
                    else:
                        violation_results["unique_constraint_violations"].append(f"Unexpected error: {e}")
                
                return violation_results
            
            def test_data_consistency(conn: sqlite3.Connection) -> Dict[str, Any]:
                """Test data consistency across related tables."""
                consistency_result = {
                    "referential_integrity": True,
                    "data_consistency": True,
                    "cascade_operations": True,
                    "consistency_errors": []
                }
                
                try:
                    # Insert valid test data
                    conn.execute("INSERT OR REPLACE INTO test_sessions (session_id, start_time, status) VALUES (?, ?, ?)",
                               ("session_005", "2025-07-12T22:00:00.000Z", "active"))
                    
                    conn.execute("INSERT OR REPLACE INTO test_threads (thread_id, session_id, thread_name, message_count) VALUES (?, ?, ?, ?)",
                               ("thread_004", "session_005", "Consistency Test", 10))
                    
                    # Verify data exists
                    cursor = conn.execute("SELECT COUNT(*) FROM test_sessions WHERE session_id = ?", ("session_005",))
                    session_count = cursor.fetchone()[0]
                    
                    cursor = conn.execute("SELECT COUNT(*) FROM test_threads WHERE session_id = ?", ("session_005",))
                    thread_count = cursor.fetchone()[0]
                    
                    if session_count != 1 or thread_count != 1:
                        consistency_result["data_consistency"] = False
                        consistency_result["consistency_errors"].append("Initial data insertion inconsistent")
                    
                    # Test cascade delete
                    conn.execute("DELETE FROM test_sessions WHERE session_id = ?", ("session_005",))
                    
                    # Verify cascade worked
                    cursor = conn.execute("SELECT COUNT(*) FROM test_threads WHERE session_id = ?", ("session_005",))
                    remaining_threads = cursor.fetchone()[0]
                    
                    if remaining_threads != 0:
                        consistency_result["cascade_operations"] = False
                        consistency_result["consistency_errors"].append("Cascade delete failed")
                
                except Exception as e:
                    consistency_result["referential_integrity"] = False
                    consistency_result["consistency_errors"].append(f"Consistency test error: {e}")
                
                return consistency_result
            
            mock_instance.setup_database_with_constraints.side_effect = setup_database_with_constraints
            mock_instance.test_constraint_violations.side_effect = test_constraint_violations
            mock_instance.test_data_consistency.side_effect = test_data_consistency
            
            thread_storage = ThreadStorage(self.db_path)
            
            # Set up database with constraints
            conn = thread_storage.setup_database_with_constraints(self.db_path)
            
            # Test constraint violations
            violation_results = thread_storage.test_constraint_violations(conn)
            
            # Verify constraint violations are properly detected
            for constraint_type, violations in violation_results.items():
                self.assertGreater(len(violations), 0,
                                 f"No {constraint_type} tests performed")
                for violation in violations:
                    self.assertIn("correctly detected", violation,
                                f"Constraint violation not properly handled: {violation}")
            
            # Test data consistency
            consistency_result = thread_storage.test_data_consistency(conn)
            
            self.assertTrue(consistency_result["referential_integrity"],
                          f"Referential integrity failed: {consistency_result['consistency_errors']}")
            self.assertTrue(consistency_result["data_consistency"],
                          f"Data consistency failed: {consistency_result['consistency_errors']}")
            self.assertTrue(consistency_result["cascade_operations"],
                          f"Cascade operations failed: {consistency_result['consistency_errors']}")
            
            conn.close()
    
    async def test_backup_and_recovery_operations(self) -> None:
        """Test database backup and recovery operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "backup.db"
            
            # Create original database with test data
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE backup_test (
                    id INTEGER PRIMARY KEY,
                    data TEXT,
                    timestamp TEXT
                )
            """)
            
            test_data = [
                ("test_data_1", "2025-07-12T22:00:00.000Z"),
                ("test_data_2", "2025-07-12T22:01:00.000Z"),
                ("test_data_3", "2025-07-12T22:02:00.000Z")
            ]
            
            for data, timestamp in test_data:
                conn.execute("INSERT INTO backup_test (data, timestamp) VALUES (?, ?)", (data, timestamp))
            
            conn.commit()
            
            # Test backup operation
            def create_backup(source_path: str, backup_path: str) -> Dict[str, Any]:
                """Create database backup."""
                backup_result = {
                    "backup_successful": True,
                    "backup_size": 0,
                    "records_backed_up": 0,
                    "backup_time": 0,
                    "backup_errors": []
                }
                
                start_time = time.time()
                
                try:
                    # Create backup using SQLite backup API
                    source_conn = sqlite3.connect(source_path)
                    backup_conn = sqlite3.connect(backup_path)
                    
                    # Perform backup
                    source_conn.backup(backup_conn)
                    
                    # Verify backup
                    cursor = backup_conn.execute("SELECT COUNT(*) FROM backup_test")
                    backup_result["records_backed_up"] = cursor.fetchone()[0]
                    
                    backup_result["backup_size"] = Path(backup_path).stat().st_size
                    backup_result["backup_time"] = time.time() - start_time
                    
                    source_conn.close()
                    backup_conn.close()
                
                except Exception as e:
                    backup_result["backup_successful"] = False
                    backup_result["backup_errors"].append(str(e))
                
                return backup_result
            
            # Test recovery operation
            def test_recovery(backup_path: str, recovery_path: str) -> Dict[str, Any]:
                """Test database recovery from backup."""
                recovery_result = {
                    "recovery_successful": True,
                    "records_recovered": 0,
                    "data_integrity": True,
                    "recovery_time": 0,
                    "recovery_errors": []
                }
                
                start_time = time.time()
                
                try:
                    # Copy backup to recovery location
                    import shutil
                    shutil.copy2(backup_path, recovery_path)
                    
                    # Verify recovered data
                    recovery_conn = sqlite3.connect(recovery_path)
                    
                    # Check record count
                    cursor = recovery_conn.execute("SELECT COUNT(*) FROM backup_test")
                    recovery_result["records_recovered"] = cursor.fetchone()[0]
                    
                    # Check data integrity
                    cursor = recovery_conn.execute("SELECT data, timestamp FROM backup_test ORDER BY id")
                    recovered_data = cursor.fetchall()
                    
                    expected_data = [(data, timestamp) for data, timestamp in test_data]
                    
                    if recovered_data == expected_data:
                        recovery_result["data_integrity"] = True
                    else:
                        recovery_result["data_integrity"] = False
                        recovery_result["recovery_errors"].append("Data integrity check failed")
                    
                    recovery_result["recovery_time"] = time.time() - start_time
                    
                    recovery_conn.close()
                
                except Exception as e:
                    recovery_result["recovery_successful"] = False
                    recovery_result["recovery_errors"].append(str(e))
                
                return recovery_result
            
            # Perform backup
            backup_result = create_backup(self.db_path, str(backup_path))
            
            self.assertTrue(backup_result["backup_successful"],
                          f"Backup failed: {backup_result['backup_errors']}")
            self.assertEqual(backup_result["records_backed_up"], len(test_data),
                           "Not all records were backed up")
            self.assertGreater(backup_result["backup_size"], 0,
                             "Backup file is empty")
            
            # Test recovery
            recovery_path = Path(temp_dir) / "recovered.db"
            recovery_result = test_recovery(str(backup_path), str(recovery_path))
            
            self.assertTrue(recovery_result["recovery_successful"],
                          f"Recovery failed: {recovery_result['recovery_errors']}")
            self.assertEqual(recovery_result["records_recovered"], len(test_data),
                           "Not all records were recovered")
            self.assertTrue(recovery_result["data_integrity"],
                          "Data integrity check failed after recovery")
            
            conn.close()
    
    async def test_schema_migration_operations(self) -> None:
        """Test database schema migration operations."""
        # Create initial schema version
        conn = sqlite3.connect(self.db_path)
        
        # Version 1 schema
        conn.execute("""
            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE threads_v1 (
                session_id TEXT PRIMARY KEY,
                thread_id TEXT,
                thread_name TEXT
            )
        """)
        
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.commit()
        
        # Test migration to version 2
        def migrate_to_v2(conn: sqlite3.Connection) -> Dict[str, Any]:
            """Migrate database schema to version 2."""
            migration_result = {
                "migration_successful": True,
                "schema_changes": [],
                "data_preserved": True,
                "migration_errors": []
            }
            
            try:
                # Check current version
                cursor = conn.execute("SELECT MAX(version) FROM schema_version")
                current_version = cursor.fetchone()[0]
                
                if current_version < 2:
                    # Add new columns
                    conn.execute("ALTER TABLE threads_v1 ADD COLUMN channel_id TEXT")
                    migration_result["schema_changes"].append("Added channel_id column")
                    
                    conn.execute("ALTER TABLE threads_v1 ADD COLUMN created_at TEXT")
                    migration_result["schema_changes"].append("Added created_at column")
                    
                    conn.execute("ALTER TABLE threads_v1 ADD COLUMN is_archived BOOLEAN DEFAULT 0")
                    migration_result["schema_changes"].append("Added is_archived column")
                    
                    # Create index
                    conn.execute("CREATE INDEX idx_threads_v1_channel ON threads_v1 (channel_id)")
                    migration_result["schema_changes"].append("Created channel_id index")
                    
                    # Update schema version
                    conn.execute("INSERT INTO schema_version (version) VALUES (2)")
                    migration_result["schema_changes"].append("Updated schema version to 2")
                    
                    conn.commit()
            
            except Exception as e:
                migration_result["migration_successful"] = False
                migration_result["migration_errors"].append(str(e))
                try:
                    conn.rollback()
                except:
                    pass
            
            return migration_result
        
        # Test migration to version 3 (rename table)
        def migrate_to_v3(conn: sqlite3.Connection) -> Dict[str, Any]:
            """Migrate database schema to version 3."""
            migration_result = {
                "migration_successful": True,
                "schema_changes": [],
                "data_preserved": True,
                "migration_errors": []
            }
            
            try:
                # Check current version
                cursor = conn.execute("SELECT MAX(version) FROM schema_version")
                current_version = cursor.fetchone()[0]
                
                if current_version < 3:
                    # Preserve existing data
                    cursor = conn.execute("SELECT COUNT(*) FROM threads_v1")
                    original_count = cursor.fetchone()[0]
                    
                    # Create new table with better schema
                    conn.execute("""
                        CREATE TABLE threads (
                            session_id TEXT PRIMARY KEY,
                            thread_id TEXT UNIQUE NOT NULL,
                            thread_name TEXT,
                            channel_id TEXT,
                            created_at TEXT,
                            last_used TEXT,
                            is_archived BOOLEAN DEFAULT 0,
                            message_count INTEGER DEFAULT 0
                        )
                    """)
                    migration_result["schema_changes"].append("Created new threads table")
                    
                    # Migrate data
                    conn.execute("""
                        INSERT INTO threads (session_id, thread_id, thread_name, channel_id, created_at, is_archived)
                        SELECT session_id, thread_id, thread_name, channel_id, created_at, is_archived
                        FROM threads_v1
                    """)
                    
                    # Verify data migration
                    cursor = conn.execute("SELECT COUNT(*) FROM threads")
                    new_count = cursor.fetchone()[0]
                    
                    if new_count != original_count:
                        migration_result["data_preserved"] = False
                        migration_result["migration_errors"].append(f"Data loss during migration: {original_count} -> {new_count}")
                    else:
                        migration_result["schema_changes"].append(f"Migrated {new_count} records")
                    
                    # Drop old table
                    conn.execute("DROP TABLE threads_v1")
                    migration_result["schema_changes"].append("Dropped old threads_v1 table")
                    
                    # Create indexes
                    conn.execute("CREATE INDEX idx_threads_thread_id ON threads (thread_id)")
                    conn.execute("CREATE INDEX idx_threads_channel_id ON threads (channel_id)")
                    migration_result["schema_changes"].append("Created optimized indexes")
                    
                    # Update schema version
                    conn.execute("INSERT INTO schema_version (version) VALUES (3)")
                    migration_result["schema_changes"].append("Updated schema version to 3")
                    
                    conn.commit()
            
            except Exception as e:
                migration_result["migration_successful"] = False
                migration_result["migration_errors"].append(str(e))
                try:
                    conn.rollback()
                except:
                    pass
            
            return migration_result
        
        # Insert test data before migration
        test_data = [
            ("session_001", "thread_123", "Test Thread 1"),
            ("session_002", "thread_456", "Test Thread 2")
        ]
        
        for session_id, thread_id, thread_name in test_data:
            conn.execute("INSERT INTO threads_v1 (session_id, thread_id, thread_name) VALUES (?, ?, ?)",
                        (session_id, thread_id, thread_name))
        conn.commit()
        
        # Perform migrations
        v2_result = migrate_to_v2(conn)
        self.assertTrue(v2_result["migration_successful"],
                       f"Migration to v2 failed: {v2_result['migration_errors']}")
        self.assertGreater(len(v2_result["schema_changes"]), 0,
                         "No schema changes recorded for v2 migration")
        
        v3_result = migrate_to_v3(conn)
        self.assertTrue(v3_result["migration_successful"],
                       f"Migration to v3 failed: {v3_result['migration_errors']}")
        self.assertTrue(v3_result["data_preserved"],
                      "Data not preserved during v3 migration")
        self.assertGreater(len(v3_result["schema_changes"]), 0,
                         "No schema changes recorded for v3 migration")
        
        # Verify final schema
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        final_version = cursor.fetchone()[0]
        self.assertEqual(final_version, 3, "Final schema version incorrect")
        
        cursor = conn.execute("SELECT COUNT(*) FROM threads")
        final_count = cursor.fetchone()[0]
        self.assertEqual(final_count, len(test_data), "Data lost during migrations")
        
        conn.close()
    
    async def test_performance_optimization(self) -> None:
        """Test database performance optimization strategies."""
        performance_results = {}
        
        for scenario_name, scenario_config in self.performance_scenarios.items():
            with self.subTest(scenario=scenario_name):
                # Create fresh database for this test
                test_db_path = f"{self.db_path}_{scenario_name}"
                
                try:
                    conn = sqlite3.connect(test_db_path)
                    
                    # Create test table
                    conn.execute("""
                        CREATE TABLE performance_test (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT,
                            data TEXT,
                            value INTEGER,
                            timestamp TEXT
                        )
                    """)
                    
                    record_count = scenario_config["records"]
                    
                    # Test INSERT performance
                    start_time = time.time()
                    
                    conn.execute("BEGIN TRANSACTION")
                    for i in range(record_count):
                        conn.execute(
                            "INSERT INTO performance_test (session_id, data, value, timestamp) VALUES (?, ?, ?, ?)",
                            (f"session_{i % 100}", f"test_data_{i}", i, f"2025-07-12T22:{i%60:02d}:00.000Z")
                        )
                    conn.execute("COMMIT")
                    
                    insert_time = time.time() - start_time
                    insert_rate = record_count / insert_time
                    
                    # Test SELECT performance without indexes
                    start_time = time.time()
                    cursor = conn.execute("SELECT * FROM performance_test WHERE session_id = ? AND value > ?", ("session_50", 5000))
                    unindexed_results = cursor.fetchall()
                    unindexed_time = time.time() - start_time
                    
                    # Create indexes
                    start_time = time.time()
                    conn.execute("CREATE INDEX idx_session_id ON performance_test (session_id)")
                    conn.execute("CREATE INDEX idx_value ON performance_test (value)")
                    conn.execute("CREATE INDEX idx_session_value ON performance_test (session_id, value)")
                    index_creation_time = time.time() - start_time
                    
                    # Test SELECT performance with indexes
                    start_time = time.time()
                    cursor = conn.execute("SELECT * FROM performance_test WHERE session_id = ? AND value > ?", ("session_50", 5000))
                    indexed_results = cursor.fetchall()
                    indexed_time = time.time() - start_time
                    
                    # Test UPDATE performance
                    start_time = time.time()
                    conn.execute("UPDATE performance_test SET value = value + 1 WHERE session_id LIKE 'session_5%'")
                    conn.commit()
                    update_time = time.time() - start_time
                    
                    # Test DELETE performance
                    start_time = time.time()
                    conn.execute("DELETE FROM performance_test WHERE value > ?", (record_count - 100,))
                    conn.commit()
                    delete_time = time.time() - start_time
                    
                    # Calculate performance metrics
                    performance_improvement = (unindexed_time - indexed_time) / unindexed_time * 100 if unindexed_time > 0 else 0
                    
                    scenario_results = {
                        "record_count": record_count,
                        "insert_time": insert_time,
                        "insert_rate": insert_rate,
                        "unindexed_select_time": unindexed_time,
                        "indexed_select_time": indexed_time,
                        "index_creation_time": index_creation_time,
                        "performance_improvement": performance_improvement,
                        "update_time": update_time,
                        "delete_time": delete_time,
                        "unindexed_results": len(unindexed_results),
                        "indexed_results": len(indexed_results)
                    }
                    
                    performance_results[scenario_name] = scenario_results
                    
                    # Verify results consistency
                    self.assertEqual(len(unindexed_results), len(indexed_results),
                                   f"Scenario {scenario_name}: Index changed query results")
                    
                    # Verify performance improvement
                    self.assertGreaterEqual(performance_improvement, 0,
                                          f"Scenario {scenario_name}: Indexes made performance worse")
                    
                    # Verify reasonable performance for large datasets
                    if record_count >= 1000:
                        self.assertLessEqual(indexed_time, unindexed_time,
                                           f"Scenario {scenario_name}: Indexes should improve performance for large datasets")
                    
                    conn.close()
                
                finally:
                    # Clean up test database
                    try:
                        Path(test_db_path).unlink(missing_ok=True)
                    except Exception:
                        pass
        
        # Log performance analysis
        self.logger.info(
            "SQLite performance analysis",
            context={
                "scenarios_tested": len(performance_results),
                "performance_results": performance_results
            }
        )


def run_sqlite_operations_tests() -> None:
    """Run SQLite operations tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestSQLiteOperations)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nSQLite Operations Tests Summary:")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    asyncio.run(main())