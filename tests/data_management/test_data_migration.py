#!/usr/bin/env python3
"""Test Data Migration Functionality.

This module provides comprehensive tests for data migration functionality,
including schema migrations, data transformations, migration rollbacks,
version compatibility, and migration integrity validation.
"""

import asyncio
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import shutil
import uuid

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.thread_storage import ThreadStorage
from src.exceptions import MigrationError, DataIntegrityError
from src.utils.validation import DataValidator


class TestDataMigration(unittest.IsolatedAsyncioTestCase):
    """Test cases for data migration functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "migration_mode": "safe",
            "backup_before_migration": True,
            "rollback_on_failure": True,
            "validate_after_migration": True,
            "migration_batch_size": 100,
            "debug": True
        }
        
        # Create temporary directory for test databases
        self.temp_dir = tempfile.mkdtemp()
        
        # Migration scenarios and versions
        self.migration_versions = {
            "v1.0.0": {
                "version": "1.0.0",
                "description": "Initial schema",
                "schema": {
                    "threads": {
                        "columns": [
                            ("id", "INTEGER PRIMARY KEY"),
                            ("session_id", "TEXT UNIQUE"),
                            ("thread_id", "TEXT"),
                            ("created_at", "TEXT")
                        ]
                    }
                },
                "data_transformations": []
            },
            "v1.1.0": {
                "version": "1.1.0",
                "description": "Add thread metadata",
                "schema": {
                    "threads": {
                        "columns": [
                            ("id", "INTEGER PRIMARY KEY"),
                            ("session_id", "TEXT UNIQUE"),
                            ("thread_id", "TEXT"),
                            ("thread_name", "TEXT"),
                            ("channel_id", "TEXT"),
                            ("created_at", "TEXT"),
                            ("last_used", "TEXT"),
                            ("is_archived", "BOOLEAN DEFAULT 0")
                        ]
                    }
                },
                "data_transformations": [
                    {
                        "type": "add_column",
                        "table": "threads",
                        "column": "thread_name",
                        "default_value": "Unnamed Thread"
                    },
                    {
                        "type": "add_column",
                        "table": "threads",
                        "column": "channel_id",
                        "default_value": "unknown"
                    },
                    {
                        "type": "add_column",
                        "table": "threads",
                        "column": "last_used",
                        "default_value": lambda row: row.get("created_at", "")
                    },
                    {
                        "type": "add_column",
                        "table": "threads",
                        "column": "is_archived",
                        "default_value": False
                    }
                ]
            },
            "v2.0.0": {
                "version": "2.0.0",
                "description": "Add sessions table and normalize data",
                "schema": {
                    "threads": {
                        "columns": [
                            ("id", "INTEGER PRIMARY KEY"),
                            ("thread_id", "TEXT UNIQUE"),
                            ("thread_name", "TEXT"),
                            ("channel_id", "TEXT"),
                            ("session_id", "TEXT"),
                            ("created_at", "TEXT"),
                            ("last_used", "TEXT"),
                            ("is_archived", "BOOLEAN DEFAULT 0"),
                            ("message_count", "INTEGER DEFAULT 0")
                        ],
                        "foreign_keys": [
                            ("session_id", "sessions", "session_id")
                        ]
                    },
                    "sessions": {
                        "columns": [
                            ("id", "INTEGER PRIMARY KEY"),
                            ("session_id", "TEXT UNIQUE"),
                            ("status", "TEXT DEFAULT 'active'"),
                            ("user_id", "TEXT"),
                            ("created_at", "TEXT"),
                            ("completed_at", "TEXT"),
                            ("metadata", "TEXT")  # JSON
                        ]
                    }
                },
                "data_transformations": [
                    {
                        "type": "create_table",
                        "table": "sessions",
                        "extract_from": "threads",
                        "transform": lambda row: {
                            "session_id": row.get("session_id"),
                            "status": "completed",  # Assume old sessions are completed
                            "user_id": f"user_{hash(row.get('session_id', '')) % 1000}",
                            "created_at": row.get("created_at"),
                            "completed_at": row.get("last_used"),
                            "metadata": json.dumps({"migrated": True})
                        }
                    },
                    {
                        "type": "normalize_column",
                        "table": "threads",
                        "column": "session_id",
                        "remove_duplicates": True
                    }
                ]
            },
            "v2.1.0": {
                "version": "2.1.0",
                "description": "Add user preferences and indexes",
                "schema": {
                    "threads": {
                        "columns": [
                            ("id", "INTEGER PRIMARY KEY"),
                            ("thread_id", "TEXT UNIQUE"),
                            ("thread_name", "TEXT"),
                            ("channel_id", "TEXT"),
                            ("session_id", "TEXT"),
                            ("created_at", "TEXT"),
                            ("last_used", "TEXT"),
                            ("is_archived", "BOOLEAN DEFAULT 0"),
                            ("message_count", "INTEGER DEFAULT 0")
                        ],
                        "indexes": [
                            ("idx_thread_id", "thread_id"),
                            ("idx_session_id", "session_id"),
                            ("idx_channel_id", "channel_id")
                        ]
                    },
                    "sessions": {
                        "columns": [
                            ("id", "INTEGER PRIMARY KEY"),
                            ("session_id", "TEXT UNIQUE"),
                            ("status", "TEXT DEFAULT 'active'"),
                            ("user_id", "TEXT"),
                            ("created_at", "TEXT"),
                            ("completed_at", "TEXT"),
                            ("metadata", "TEXT")
                        ],
                        "indexes": [
                            ("idx_session_id", "session_id"),
                            ("idx_user_id", "user_id"),
                            ("idx_status", "status")
                        ]
                    },
                    "user_preferences": {
                        "columns": [
                            ("id", "INTEGER PRIMARY KEY"),
                            ("user_id", "TEXT UNIQUE"),
                            ("preferences", "TEXT"),  # JSON
                            ("created_at", "TEXT"),
                            ("updated_at", "TEXT")
                        ]
                    }
                },
                "data_transformations": [
                    {
                        "type": "create_table",
                        "table": "user_preferences",
                        "extract_from": "sessions",
                        "transform": lambda row: {
                            "user_id": row.get("user_id"),
                            "preferences": json.dumps({
                                "notification_enabled": True,
                                "auto_archive": False,
                                "thread_naming": "auto"
                            }),
                            "created_at": row.get("created_at"),
                            "updated_at": row.get("created_at")
                        }
                    }
                ]
            }
        }
        
        # Test data for migrations
        self.test_data = {
            "v1.0.0": [
                {
                    "session_id": "migration_test_001",
                    "thread_id": "123456789012345678",
                    "created_at": "2025-07-12T20:00:00.000Z"
                },
                {
                    "session_id": "migration_test_002",
                    "thread_id": "234567890123456789",
                    "created_at": "2025-07-12T21:00:00.000Z"
                },
                {
                    "session_id": "migration_test_003",
                    "thread_id": "345678901234567890",
                    "created_at": "2025-07-12T22:00:00.000Z"
                }
            ]
        }
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_schema_migration_basic(self) -> None:
        """Test basic schema migration functionality."""
        with patch('sqlite3.connect') as mock_connect:
            # Create mock database connections
            source_db_path = Path(self.temp_dir) / "source_v1.db"
            target_db_path = Path(self.temp_dir) / "target_v2.db"
            
            source_conn = MagicMock()
            target_conn = MagicMock()
            
            def connect_handler(db_path):
                if "source" in str(db_path):
                    return source_conn
                elif "target" in str(db_path):
                    return target_conn
                return MagicMock()
            
            mock_connect.side_effect = connect_handler
            
            # Mock database operations
            source_data = {}
            target_data = {}
            migration_log = []
            
            def execute_source(query, params=()):
                cursor = source_conn.cursor()
                if "SELECT" in query:
                    if "threads" in query:
                        cursor.fetchall.return_value = [
                            (1, "migration_test_001", "123456789012345678", "2025-07-12T20:00:00.000Z"),
                            (2, "migration_test_002", "234567890123456789", "2025-07-12T21:00:00.000Z"),
                            (3, "migration_test_003", "345678901234567890", "2025-07-12T22:00:00.000Z")
                        ]
                    else:
                        cursor.fetchall.return_value = []
                elif "CREATE TABLE" in query:
                    table_name = self._extract_table_name(query)
                    source_data[table_name] = {"created": True, "schema": query}
                elif "INSERT" in query:
                    migration_log.append({"operation": "insert", "query": query, "params": params})
                
                return cursor
            
            def execute_target(query, params=()):
                cursor = target_conn.cursor()
                if "CREATE TABLE" in query:
                    table_name = self._extract_table_name(query)
                    target_data[table_name] = {"created": True, "schema": query}
                elif "INSERT" in query:
                    table_name = self._extract_table_name_from_insert(query)
                    if table_name not in target_data:
                        target_data[table_name] = {"rows": []}
                    target_data[table_name]["rows"].append(params)
                    migration_log.append({"operation": "target_insert", "table": table_name, "params": params})
                elif "CREATE INDEX" in query:
                    index_name = self._extract_index_name(query)
                    migration_log.append({"operation": "create_index", "index": index_name})
                
                return cursor
            
            source_conn.execute.side_effect = execute_source
            target_conn.execute.side_effect = execute_target
            source_conn.commit.return_value = None
            target_conn.commit.return_value = None
            
            # Test migration from v1.0.0 to v2.0.0
            source_version = "v1.0.0"
            target_version = "v2.0.0"
            
            migration_result = await self._perform_schema_migration(
                source_db_path, target_db_path, source_version, target_version
            )
            
            # Verify migration success
            self.assertTrue(migration_result["success"])
            self.assertEqual(migration_result["source_version"], source_version)
            self.assertEqual(migration_result["target_version"], target_version)
            
            # Verify schema creation
            self.assertIn("threads", target_data)
            self.assertIn("sessions", target_data)
            self.assertTrue(target_data["threads"]["created"])
            self.assertTrue(target_data["sessions"]["created"])
            
            # Verify data migration
            threads_rows = target_data.get("threads", {}).get("rows", [])
            sessions_rows = target_data.get("sessions", {}).get("rows", [])
            
            self.assertEqual(len(threads_rows), 3)  # Original 3 threads
            self.assertEqual(len(sessions_rows), 3)  # Extracted 3 sessions
            
            # Verify migration log
            insert_operations = [log for log in migration_log if log["operation"] in ["insert", "target_insert"]]
            self.assertGreaterEqual(len(insert_operations), 6)  # At least 3 threads + 3 sessions
            
            # Log migration analysis
            self.logger.info(
                "Schema migration analysis",
                context={
                    "source_version": source_version,
                    "target_version": target_version,
                    "migration_success": migration_result["success"],
                    "tables_created": len(target_data),
                    "data_rows_migrated": len(insert_operations),
                    "migration_duration": migration_result.get("duration", 0)
                }
            )
    
    async def test_data_transformation_pipeline(self) -> None:
        """Test data transformation pipeline during migration."""
        with patch('src.utils.validation.DataValidator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator.return_value = mock_validator_instance
            
            # Mock transformation pipeline
            transformation_pipeline = []
            transformation_results = []
            
            def apply_transformation(transformation: Dict[str, Any], data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                """Apply a single transformation to data."""
                transformation_type = transformation.get("type")
                
                if transformation_type == "add_column":
                    column_name = transformation["column"]
                    default_value = transformation["default_value"]
                    
                    for row in data:
                        if callable(default_value):
                            row[column_name] = default_value(row)
                        else:
                            row[column_name] = default_value
                    
                    transformation_results.append({
                        "type": transformation_type,
                        "column": column_name,
                        "rows_affected": len(data)
                    })
                
                elif transformation_type == "normalize_column":
                    column_name = transformation["column"]
                    
                    if transformation.get("remove_duplicates", False):
                        seen_values = set()
                        unique_data = []
                        for row in data:
                            value = row.get(column_name)
                            if value not in seen_values:
                                seen_values.add(value)
                                unique_data.append(row)
                        data[:] = unique_data
                    
                    transformation_results.append({
                        "type": transformation_type,
                        "column": column_name,
                        "original_count": len(data) + len([v for v in seen_values if v in seen_values]),
                        "normalized_count": len(data)
                    })
                
                elif transformation_type == "extract_data":
                    source_table = transformation["source_table"]
                    target_table = transformation["target_table"]
                    extract_function = transformation["extract_function"]
                    
                    extracted_data = []
                    for row in data:
                        extracted_row = extract_function(row)
                        if extracted_row:
                            extracted_data.append(extracted_row)
                    
                    transformation_results.append({
                        "type": transformation_type,
                        "source_table": source_table,
                        "target_table": target_table,
                        "rows_extracted": len(extracted_data)
                    })
                    
                    return data, extracted_data
                
                elif transformation_type == "data_validation":
                    validation_rules = transformation["rules"]
                    validation_errors = []
                    
                    for i, row in enumerate(data):
                        for field, rule in validation_rules.items():
                            if field in row:
                                value = row[field]
                                if rule.get("required", False) and not value:
                                    validation_errors.append(f"Row {i}: {field} is required")
                                if "type" in rule and not isinstance(value, rule["type"]):
                                    validation_errors.append(f"Row {i}: {field} type mismatch")
                    
                    transformation_results.append({
                        "type": transformation_type,
                        "validation_errors": validation_errors,
                        "rows_validated": len(data)
                    })
                    
                    if validation_errors:
                        raise DataIntegrityError(f"Validation failed: {validation_errors}")
                
                return data
            
            def run_transformation_pipeline(data: List[Dict[str, Any]], 
                                          transformations: List[Dict[str, Any]]) -> Dict[str, Any]:
                """Run complete transformation pipeline."""
                pipeline_start = time.time()
                
                try:
                    current_data = data.copy()
                    additional_tables = {}
                    
                    for transformation in transformations:
                        result = apply_transformation(transformation, current_data)
                        
                        # Handle extractions that create additional data
                        if isinstance(result, tuple) and len(result) == 2:
                            current_data, extracted_data = result
                            table_name = transformation.get("target_table", "extracted")
                            additional_tables[table_name] = extracted_data
                    
                    pipeline_duration = time.time() - pipeline_start
                    
                    return {
                        "success": True,
                        "transformed_data": current_data,
                        "additional_tables": additional_tables,
                        "transformation_results": transformation_results,
                        "pipeline_duration": pipeline_duration
                    }
                
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "transformation_results": transformation_results,
                        "pipeline_duration": time.time() - pipeline_start
                    }
            
            mock_validator_instance.run_transformation_pipeline.side_effect = run_transformation_pipeline
            
            validator = DataValidator(self.test_config, self.logger)
            
            # Test data transformation for v1.0.0 to v1.1.0 migration
            source_data = [
                {
                    "id": 1,
                    "session_id": "transform_test_001",
                    "thread_id": "123456789012345678",
                    "created_at": "2025-07-12T20:00:00.000Z"
                },
                {
                    "id": 2,
                    "session_id": "transform_test_002",
                    "thread_id": "234567890123456789",
                    "created_at": "2025-07-12T21:00:00.000Z"
                },
                {
                    "id": 3,
                    "session_id": "transform_test_002",  # Duplicate session_id
                    "thread_id": "345678901234567890",
                    "created_at": "2025-07-12T22:00:00.000Z"
                }
            ]
            
            # Define transformation pipeline
            transformations = [
                {
                    "type": "add_column",
                    "column": "thread_name",
                    "default_value": "Migrated Thread"
                },
                {
                    "type": "add_column",
                    "column": "channel_id",
                    "default_value": "987654321098765432"
                },
                {
                    "type": "add_column",
                    "column": "last_used",
                    "default_value": lambda row: row.get("created_at", "")
                },
                {
                    "type": "normalize_column",
                    "column": "session_id",
                    "remove_duplicates": True
                },
                {
                    "type": "extract_data",
                    "source_table": "threads",
                    "target_table": "sessions",
                    "extract_function": lambda row: {
                        "session_id": row.get("session_id"),
                        "status": "migrated",
                        "user_id": f"user_{hash(row.get('session_id', '')) % 1000}",
                        "created_at": row.get("created_at"),
                        "metadata": json.dumps({"source": "migration"})
                    }
                },
                {
                    "type": "data_validation",
                    "rules": {
                        "session_id": {"required": True, "type": str},
                        "thread_id": {"required": True, "type": str},
                        "created_at": {"required": True, "type": str}
                    }
                }
            ]
            
            # Run transformation pipeline
            pipeline_result = validator.run_transformation_pipeline(source_data, transformations)
            
            # Verify transformation success
            self.assertTrue(pipeline_result["success"])
            
            # Verify transformed data
            transformed_data = pipeline_result["transformed_data"]
            self.assertEqual(len(transformed_data), 2)  # Duplicates removed
            
            # Verify added columns
            for row in transformed_data:
                self.assertIn("thread_name", row)
                self.assertIn("channel_id", row)
                self.assertIn("last_used", row)
                self.assertEqual(row["thread_name"], "Migrated Thread")
                self.assertEqual(row["channel_id"], "987654321098765432")
                self.assertEqual(row["last_used"], row["created_at"])
            
            # Verify extracted sessions
            sessions_data = pipeline_result["additional_tables"].get("sessions", [])
            self.assertEqual(len(sessions_data), 2)  # Should match unique sessions
            
            for session in sessions_data:
                self.assertIn("session_id", session)
                self.assertIn("status", session)
                self.assertIn("user_id", session)
                self.assertEqual(session["status"], "migrated")
            
            # Verify transformation results
            transformation_results = pipeline_result["transformation_results"]
            add_column_results = [r for r in transformation_results if r["type"] == "add_column"]
            normalize_results = [r for r in transformation_results if r["type"] == "normalize_column"]
            extract_results = [r for r in transformation_results if r["type"] == "extract_data"]
            validation_results = [r for r in transformation_results if r["type"] == "data_validation"]
            
            self.assertEqual(len(add_column_results), 3)  # 3 columns added
            self.assertEqual(len(normalize_results), 1)  # 1 normalization
            self.assertEqual(len(extract_results), 1)  # 1 extraction
            self.assertEqual(len(validation_results), 1)  # 1 validation
            
            # Verify normalization removed duplicates
            normalize_result = normalize_results[0]
            self.assertGreater(normalize_result["original_count"], normalize_result["normalized_count"])
            
            # Log transformation analysis
            self.logger.info(
                "Data transformation pipeline analysis",
                context={
                    "source_rows": len(source_data),
                    "transformed_rows": len(transformed_data),
                    "extracted_sessions": len(sessions_data),
                    "transformations_applied": len(transformations),
                    "pipeline_duration": pipeline_result["pipeline_duration"],
                    "transformation_results": transformation_results
                }
            )
    
    async def test_migration_rollback_mechanisms(self) -> None:
        """Test migration rollback mechanisms and recovery."""
        with patch('src.thread_storage.ThreadStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_storage.return_value = mock_instance
            
            # Mock migration system with rollback capability
            migration_snapshots = {}
            migration_states = {}
            rollback_log = []
            
            def create_migration_snapshot(migration_id: str, data: Dict[str, Any]) -> str:
                """Create a snapshot before migration."""
                snapshot_id = f"snapshot_{migration_id}_{int(time.time())}"
                migration_snapshots[snapshot_id] = {
                    "migration_id": migration_id,
                    "data": data.copy(),
                    "timestamp": time.time(),
                    "size": len(json.dumps(data))
                }
                return snapshot_id
            
            def execute_migration_with_rollback(migration_id: str, migration_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
                """Execute migration with rollback capability."""
                migration_start = time.time()
                
                # Create snapshot
                initial_data = {"threads": self.test_data["v1.0.0"]}
                snapshot_id = create_migration_snapshot(migration_id, initial_data)
                
                try:
                    migration_states[migration_id] = {
                        "status": "in_progress",
                        "snapshot_id": snapshot_id,
                        "steps_completed": [],
                        "current_step": 0
                    }
                    
                    current_data = initial_data.copy()
                    
                    for i, step in enumerate(migration_steps):
                        migration_states[migration_id]["current_step"] = i
                        
                        # Simulate step execution
                        step_type = step.get("type")
                        
                        if step_type == "add_table":
                            table_name = step["table_name"]
                            current_data[table_name] = []
                            
                        elif step_type == "transform_data":
                            table_name = step["table_name"]
                            if table_name in current_data:
                                # Apply transformation
                                transformation = step["transformation"]
                                current_data[table_name] = [
                                    transformation(row) for row in current_data[table_name]
                                ]
                        
                        elif step_type == "fail_step":
                            # Simulate failure for testing
                            raise Exception(f"Migration step {i} failed: {step.get('error', 'Unknown error')}")
                        
                        migration_states[migration_id]["steps_completed"].append(i)
                    
                    migration_states[migration_id]["status"] = "completed"
                    migration_duration = time.time() - migration_start
                    
                    return {
                        "success": True,
                        "migration_id": migration_id,
                        "snapshot_id": snapshot_id,
                        "steps_completed": len(migration_steps),
                        "duration": migration_duration,
                        "final_data": current_data
                    }
                
                except Exception as e:
                    # Migration failed - initiate rollback
                    migration_states[migration_id]["status"] = "failed"
                    migration_states[migration_id]["error"] = str(e)
                    
                    rollback_result = perform_rollback(migration_id, snapshot_id)
                    
                    return {
                        "success": False,
                        "migration_id": migration_id,
                        "error": str(e),
                        "rollback_performed": rollback_result["success"],
                        "rollback_details": rollback_result
                    }
            
            def perform_rollback(migration_id: str, snapshot_id: str) -> Dict[str, Any]:
                """Perform rollback to snapshot."""
                rollback_start = time.time()
                
                try:
                    if snapshot_id not in migration_snapshots:
                        raise Exception(f"Snapshot {snapshot_id} not found")
                    
                    snapshot = migration_snapshots[snapshot_id]
                    restored_data = snapshot["data"].copy()
                    
                    rollback_log.append({
                        "migration_id": migration_id,
                        "snapshot_id": snapshot_id,
                        "rollback_timestamp": time.time(),
                        "data_size": snapshot["size"]
                    })
                    
                    rollback_duration = time.time() - rollback_start
                    
                    return {
                        "success": True,
                        "migration_id": migration_id,
                        "snapshot_id": snapshot_id,
                        "restored_data": restored_data,
                        "rollback_duration": rollback_duration
                    }
                
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "rollback_duration": time.time() - rollback_start
                    }
            
            def get_migration_status(migration_id: str) -> Dict[str, Any]:
                """Get migration status and details."""
                if migration_id not in migration_states:
                    return {"exists": False}
                
                state = migration_states[migration_id]
                snapshot_info = None
                
                if "snapshot_id" in state:
                    snapshot_id = state["snapshot_id"]
                    if snapshot_id in migration_snapshots:
                        snapshot_info = migration_snapshots[snapshot_id]
                
                return {
                    "exists": True,
                    "migration_id": migration_id,
                    "status": state["status"],
                    "steps_completed": state.get("steps_completed", []),
                    "current_step": state.get("current_step", 0),
                    "error": state.get("error"),
                    "snapshot_info": snapshot_info
                }
            
            mock_instance.create_migration_snapshot.side_effect = create_migration_snapshot
            mock_instance.execute_migration_with_rollback.side_effect = execute_migration_with_rollback
            mock_instance.perform_rollback.side_effect = perform_rollback
            mock_instance.get_migration_status.side_effect = get_migration_status
            
            storage = ThreadStorage("/tmp/rollback_test.db")
            
            # Test successful migration
            successful_migration_steps = [
                {
                    "type": "add_table",
                    "table_name": "sessions"
                },
                {
                    "type": "transform_data",
                    "table_name": "threads",
                    "transformation": lambda row: {
                        **row,
                        "thread_name": f"Thread {row.get('thread_id', '')[-4:]}",
                        "last_used": row.get("created_at")
                    }
                }
            ]
            
            success_result = storage.execute_migration_with_rollback(
                "test_migration_success", successful_migration_steps
            )
            
            self.assertTrue(success_result["success"])
            self.assertEqual(success_result["steps_completed"], 2)
            self.assertIn("final_data", success_result)
            
            # Test failed migration with rollback
            failed_migration_steps = [
                {
                    "type": "add_table",
                    "table_name": "sessions"
                },
                {
                    "type": "transform_data",
                    "table_name": "threads",
                    "transformation": lambda row: {**row, "new_field": "value"}
                },
                {
                    "type": "fail_step",
                    "error": "Simulated migration failure"
                }
            ]
            
            failure_result = storage.execute_migration_with_rollback(
                "test_migration_failure", failed_migration_steps
            )
            
            self.assertFalse(failure_result["success"])
            self.assertTrue(failure_result["rollback_performed"])
            self.assertIn("error", failure_result)
            
            # Verify rollback was logged
            rollback_entries = [log for log in rollback_log if log["migration_id"] == "test_migration_failure"]
            self.assertEqual(len(rollback_entries), 1)
            
            # Test migration status tracking
            success_status = storage.get_migration_status("test_migration_success")
            failure_status = storage.get_migration_status("test_migration_failure")
            
            self.assertTrue(success_status["exists"])
            self.assertEqual(success_status["status"], "completed")
            
            self.assertTrue(failure_status["exists"])
            self.assertEqual(failure_status["status"], "failed")
            self.assertIsNotNone(failure_status["error"])
            
            # Test snapshot management
            self.assertEqual(len(migration_snapshots), 2)  # One for each migration
            
            # Log rollback analysis
            self.logger.info(
                "Migration rollback mechanisms analysis",
                context={
                    "successful_migrations": 1,
                    "failed_migrations": 1,
                    "rollbacks_performed": len(rollback_log),
                    "snapshots_created": len(migration_snapshots),
                    "migration_states_tracked": len(migration_states),
                    "rollback_success_rate": 1.0
                }
            )
    
    async def test_version_compatibility_validation(self) -> None:
        """Test version compatibility validation and upgrade paths."""
        with patch('src.utils.validation.DataValidator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator.return_value = mock_validator_instance
            
            # Mock version compatibility system
            compatibility_matrix = {}
            upgrade_paths = {}
            validation_results = []
            
            def define_compatibility_matrix():
                """Define version compatibility matrix."""
                versions = ["v1.0.0", "v1.1.0", "v2.0.0", "v2.1.0"]
                
                for i, source in enumerate(versions):
                    compatibility_matrix[source] = {}
                    for j, target in enumerate(versions):
                        if i < j:
                            # Forward compatibility
                            compatibility_matrix[source][target] = {
                                "compatible": True,
                                "migration_required": True,
                                "complexity": "medium" if j - i == 1 else "high",
                                "breaking_changes": j - i > 1
                            }
                        elif i == j:
                            # Same version
                            compatibility_matrix[source][target] = {
                                "compatible": True,
                                "migration_required": False,
                                "complexity": "none"
                            }
                        else:
                            # Backward compatibility (downgrade)
                            compatibility_matrix[source][target] = {
                                "compatible": False,
                                "migration_required": True,
                                "complexity": "high",
                                "breaking_changes": True,
                                "requires_data_loss": True
                            }
            
            def calculate_upgrade_path(source_version: str, target_version: str) -> Dict[str, Any]:
                """Calculate optimal upgrade path between versions."""
                if source_version == target_version:
                    return {
                        "path": [source_version],
                        "steps": 0,
                        "complexity": "none",
                        "estimated_duration": 0
                    }
                
                # For this test, use simple direct path calculation
                source_idx = list(self.migration_versions.keys()).index(source_version)
                target_idx = list(self.migration_versions.keys()).index(target_version)
                
                if source_idx > target_idx:
                    return {
                        "path": [],
                        "steps": 0,
                        "complexity": "impossible",
                        "error": "Downgrade not supported"
                    }
                
                versions = list(self.migration_versions.keys())
                path = versions[source_idx:target_idx + 1]
                
                steps = len(path) - 1
                complexity = "low" if steps == 1 else "medium" if steps <= 2 else "high"
                estimated_duration = steps * 30  # 30 seconds per step
                
                return {
                    "path": path,
                    "steps": steps,
                    "complexity": complexity,
                    "estimated_duration": estimated_duration
                }
            
            def validate_version_compatibility(source_version: str, target_version: str, 
                                             source_data: Dict[str, Any]) -> Dict[str, Any]:
                """Validate compatibility between versions."""
                validation_start = time.time()
                
                try:
                    # Check if versions exist
                    if source_version not in self.migration_versions:
                        raise ValueError(f"Unknown source version: {source_version}")
                    
                    if target_version not in self.migration_versions:
                        raise ValueError(f"Unknown target version: {target_version}")
                    
                    # Get compatibility info
                    compatibility = compatibility_matrix.get(source_version, {}).get(target_version, {})
                    
                    if not compatibility.get("compatible", False):
                        return {
                            "compatible": False,
                            "error": "Versions are not compatible",
                            "compatibility_info": compatibility
                        }
                    
                    # Validate source data schema
                    source_schema = self.migration_versions[source_version]["schema"]
                    schema_validation = self._validate_data_against_schema(source_data, source_schema)
                    
                    if not schema_validation["valid"]:
                        return {
                            "compatible": False,
                            "error": "Source data does not match source version schema",
                            "schema_errors": schema_validation["errors"]
                        }
                    
                    # Calculate upgrade path
                    upgrade_path = calculate_upgrade_path(source_version, target_version)
                    
                    if upgrade_path.get("error"):
                        return {
                            "compatible": False,
                            "error": upgrade_path["error"],
                            "upgrade_path": upgrade_path
                        }
                    
                    # Estimate migration requirements
                    data_size = len(json.dumps(source_data))
                    estimated_memory = data_size * 2  # Assume 2x memory for migration
                    estimated_disk = data_size * 3  # Assume 3x disk for backups
                    
                    validation_result = {
                        "compatible": True,
                        "source_version": source_version,
                        "target_version": target_version,
                        "compatibility_info": compatibility,
                        "upgrade_path": upgrade_path,
                        "schema_validation": schema_validation,
                        "resource_requirements": {
                            "estimated_memory_mb": estimated_memory / 1024 / 1024,
                            "estimated_disk_mb": estimated_disk / 1024 / 1024,
                            "estimated_duration_seconds": upgrade_path["estimated_duration"]
                        },
                        "validation_duration": time.time() - validation_start
                    }
                    
                    validation_results.append(validation_result)
                    return validation_result
                
                except Exception as e:
                    return {
                        "compatible": False,
                        "error": str(e),
                        "validation_duration": time.time() - validation_start
                    }
            
            # Initialize compatibility matrix
            define_compatibility_matrix()
            
            mock_validator_instance.calculate_upgrade_path.side_effect = calculate_upgrade_path
            mock_validator_instance.validate_version_compatibility.side_effect = validate_version_compatibility
            
            validator = DataValidator(self.test_config, self.logger)
            
            # Test valid upgrade scenarios
            valid_upgrades = [
                ("v1.0.0", "v1.1.0"),
                ("v1.0.0", "v2.0.0"),
                ("v1.1.0", "v2.0.0"),
                ("v2.0.0", "v2.1.0"),
                ("v1.0.0", "v2.1.0")  # Multi-step upgrade
            ]
            
            test_data = {"threads": self.test_data["v1.0.0"]}
            
            for source_version, target_version in valid_upgrades:
                validation_result = validator.validate_version_compatibility(
                    source_version, target_version, test_data
                )
                
                self.assertTrue(validation_result["compatible"],
                              f"Upgrade {source_version} -> {target_version} should be compatible")
                self.assertIn("upgrade_path", validation_result)
                self.assertGreater(len(validation_result["upgrade_path"]["path"]), 0)
            
            # Test invalid upgrade scenarios
            invalid_upgrades = [
                ("v2.0.0", "v1.0.0"),  # Downgrade
                ("v2.1.0", "v1.1.0"),  # Downgrade
                ("v3.0.0", "v2.0.0"),  # Non-existent source version
                ("v1.0.0", "v3.0.0")   # Non-existent target version
            ]
            
            for source_version, target_version in invalid_upgrades:
                validation_result = validator.validate_version_compatibility(
                    source_version, target_version, test_data
                )
                
                self.assertFalse(validation_result["compatible"],
                               f"Upgrade {source_version} -> {target_version} should not be compatible")
                self.assertIn("error", validation_result)
            
            # Test same version compatibility
            same_version_result = validator.validate_version_compatibility(
                "v2.0.0", "v2.0.0", test_data
            )
            
            self.assertTrue(same_version_result["compatible"])
            self.assertEqual(same_version_result["upgrade_path"]["steps"], 0)
            
            # Test complex upgrade path calculation
            complex_upgrade = validator.calculate_upgrade_path("v1.0.0", "v2.1.0")
            
            self.assertEqual(len(complex_upgrade["path"]), 4)  # v1.0.0 -> v1.1.0 -> v2.0.0 -> v2.1.0
            self.assertEqual(complex_upgrade["steps"], 3)
            self.assertEqual(complex_upgrade["complexity"], "high")
            
            # Log compatibility analysis
            self.logger.info(
                "Version compatibility validation analysis",
                context={
                    "valid_upgrades_tested": len(valid_upgrades),
                    "invalid_upgrades_tested": len(invalid_upgrades),
                    "validation_results": len(validation_results),
                    "complex_upgrades": 1,
                    "compatibility_matrix_size": sum(len(targets) for targets in compatibility_matrix.values()),
                    "average_validation_duration": sum(r["validation_duration"] for r in validation_results) / max(len(validation_results), 1)
                }
            )
    
    async def test_migration_integrity_validation(self) -> None:
        """Test migration integrity validation and data consistency checks."""
        with patch('src.thread_storage.ThreadStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_storage.return_value = mock_instance
            
            # Mock integrity validation system
            integrity_checks = []
            validation_log = []
            
            def perform_pre_migration_validation(data: Dict[str, Any]) -> Dict[str, Any]:
                """Perform validation before migration."""
                validation_start = time.time()
                errors = []
                warnings = []
                
                # Check data structure
                if "threads" not in data:
                    errors.append("Missing required 'threads' table")
                
                threads = data.get("threads", [])
                
                # Check required fields
                required_fields = ["session_id", "thread_id", "created_at"]
                for i, thread in enumerate(threads):
                    for field in required_fields:
                        if field not in thread:
                            errors.append(f"Thread {i}: Missing required field '{field}'")
                
                # Check data types
                for i, thread in enumerate(threads):
                    if "session_id" in thread and not isinstance(thread["session_id"], str):
                        errors.append(f"Thread {i}: session_id must be string")
                    if "thread_id" in thread and not isinstance(thread["thread_id"], str):
                        errors.append(f"Thread {i}: thread_id must be string")
                
                # Check for duplicates
                session_ids = [t.get("session_id") for t in threads]
                thread_ids = [t.get("thread_id") for t in threads]
                
                if len(set(session_ids)) != len(session_ids):
                    warnings.append("Duplicate session_ids found")
                
                if len(set(thread_ids)) != len(thread_ids):
                    errors.append("Duplicate thread_ids found")
                
                validation_duration = time.time() - validation_start
                
                result = {
                    "valid": len(errors) == 0,
                    "errors": errors,
                    "warnings": warnings,
                    "validation_duration": validation_duration,
                    "checks_performed": ["structure", "required_fields", "data_types", "duplicates"]
                }
                
                validation_log.append({
                    "phase": "pre_migration",
                    "result": result,
                    "timestamp": time.time()
                })
                
                return result
            
            def perform_post_migration_validation(source_data: Dict[str, Any], 
                                                target_data: Dict[str, Any]) -> Dict[str, Any]:
                """Perform validation after migration."""
                validation_start = time.time()
                errors = []
                warnings = []
                
                # Check data preservation
                source_threads = source_data.get("threads", [])
                target_threads = target_data.get("threads", [])
                
                if len(target_threads) < len(source_threads):
                    errors.append("Data loss detected: fewer threads in target than source")
                
                # Check session extraction (if sessions table exists)
                if "sessions" in target_data:
                    target_sessions = target_data["sessions"]
                    unique_session_ids = set(t.get("session_id") for t in source_threads)
                    
                    if len(target_sessions) != len(unique_session_ids):
                        warnings.append(f"Session count mismatch: expected {len(unique_session_ids)}, got {len(target_sessions)}")
                
                # Check referential integrity
                for thread in target_threads:
                    session_id = thread.get("session_id")
                    if session_id and "sessions" in target_data:
                        session_exists = any(s.get("session_id") == session_id for s in target_data["sessions"])
                        if not session_exists:
                            errors.append(f"Referential integrity violation: thread references non-existent session {session_id}")
                
                # Check required fields in target
                for i, thread in enumerate(target_threads):
                    required_fields = ["session_id", "thread_id", "created_at"]
                    for field in required_fields:
                        if field not in thread:
                            errors.append(f"Target thread {i}: Missing required field '{field}'")
                
                # Check data consistency
                for i, source_thread in enumerate(source_threads):
                    # Find corresponding thread in target
                    source_session_id = source_thread.get("session_id")
                    target_thread = next((t for t in target_threads if t.get("session_id") == source_session_id), None)
                    
                    if target_thread:
                        # Check that critical data is preserved
                        if source_thread.get("thread_id") != target_thread.get("thread_id"):
                            errors.append(f"Thread ID mismatch for session {source_session_id}")
                        if source_thread.get("created_at") != target_thread.get("created_at"):
                            errors.append(f"Creation timestamp mismatch for session {source_session_id}")
                
                validation_duration = time.time() - validation_start
                
                result = {
                    "valid": len(errors) == 0,
                    "errors": errors,
                    "warnings": warnings,
                    "validation_duration": validation_duration,
                    "checks_performed": ["data_preservation", "referential_integrity", "field_requirements", "data_consistency"]
                }
                
                validation_log.append({
                    "phase": "post_migration",
                    "result": result,
                    "timestamp": time.time()
                })
                
                return result
            
            def perform_integrity_checksum(data: Dict[str, Any]) -> str:
                """Calculate integrity checksum for data."""
                # Create reproducible checksum
                data_str = json.dumps(data, sort_keys=True)
                return str(hash(data_str))
            
            def validate_migration_integrity(source_data: Dict[str, Any], target_data: Dict[str, Any], 
                                           migration_config: Dict[str, Any]) -> Dict[str, Any]:
                """Comprehensive migration integrity validation."""
                integrity_start = time.time()
                
                # Pre-migration validation
                pre_validation = perform_pre_migration_validation(source_data)
                if not pre_validation["valid"]:
                    return {
                        "valid": False,
                        "phase": "pre_migration",
                        "validation_result": pre_validation
                    }
                
                # Calculate source checksum
                source_checksum = perform_integrity_checksum(source_data)
                
                # Post-migration validation
                post_validation = perform_post_migration_validation(source_data, target_data)
                
                # Calculate target checksum
                target_checksum = perform_integrity_checksum(target_data)
                
                # Comprehensive integrity report
                integrity_duration = time.time() - integrity_start
                
                integrity_report = {
                    "valid": post_validation["valid"],
                    "source_checksum": source_checksum,
                    "target_checksum": target_checksum,
                    "pre_migration_validation": pre_validation,
                    "post_migration_validation": post_validation,
                    "integrity_checks": len(integrity_checks),
                    "total_errors": len(pre_validation["errors"]) + len(post_validation["errors"]),
                    "total_warnings": len(pre_validation["warnings"]) + len(post_validation["warnings"]),
                    "integrity_duration": integrity_duration
                }
                
                integrity_checks.append(integrity_report)
                
                return integrity_report
            
            mock_instance.perform_pre_migration_validation.side_effect = perform_pre_migration_validation
            mock_instance.perform_post_migration_validation.side_effect = perform_post_migration_validation
            mock_instance.perform_integrity_checksum.side_effect = perform_integrity_checksum
            mock_instance.validate_migration_integrity.side_effect = validate_migration_integrity
            
            storage = ThreadStorage("/tmp/integrity_test.db")
            
            # Test with valid data
            valid_source_data = {
                "threads": [
                    {
                        "session_id": "integrity_test_001",
                        "thread_id": "123456789012345678",
                        "created_at": "2025-07-12T20:00:00.000Z"
                    },
                    {
                        "session_id": "integrity_test_002",
                        "thread_id": "234567890123456789",
                        "created_at": "2025-07-12T21:00:00.000Z"
                    }
                ]
            }
            
            # Simulate target data after migration
            valid_target_data = {
                "threads": [
                    {
                        "session_id": "integrity_test_001",
                        "thread_id": "123456789012345678",
                        "thread_name": "Thread 5678",
                        "channel_id": "987654321098765432",
                        "created_at": "2025-07-12T20:00:00.000Z",
                        "last_used": "2025-07-12T20:00:00.000Z"
                    },
                    {
                        "session_id": "integrity_test_002",
                        "thread_id": "234567890123456789",
                        "thread_name": "Thread 6789",
                        "channel_id": "987654321098765432",
                        "created_at": "2025-07-12T21:00:00.000Z",
                        "last_used": "2025-07-12T21:00:00.000Z"
                    }
                ],
                "sessions": [
                    {
                        "session_id": "integrity_test_001",
                        "status": "migrated",
                        "user_id": "user_123",
                        "created_at": "2025-07-12T20:00:00.000Z",
                        "metadata": "{\"source\": \"migration\"}"
                    },
                    {
                        "session_id": "integrity_test_002",
                        "status": "migrated",
                        "user_id": "user_456",
                        "created_at": "2025-07-12T21:00:00.000Z",
                        "metadata": "{\"source\": \"migration\"}"
                    }
                ]
            }
            
            # Test valid migration integrity
            valid_integrity_result = storage.validate_migration_integrity(
                valid_source_data, valid_target_data, self.test_config
            )
            
            self.assertTrue(valid_integrity_result["valid"])
            self.assertEqual(valid_integrity_result["total_errors"], 0)
            self.assertIsNotNone(valid_integrity_result["source_checksum"])
            self.assertIsNotNone(valid_integrity_result["target_checksum"])
            
            # Test with invalid source data
            invalid_source_data = {
                "threads": [
                    {
                        "session_id": "integrity_test_003",
                        # Missing thread_id and created_at
                    },
                    {
                        "session_id": "integrity_test_004",
                        "thread_id": "345678901234567890",
                        "created_at": "2025-07-12T22:00:00.000Z"
                    },
                    {
                        "session_id": "integrity_test_004",  # Duplicate session_id
                        "thread_id": "456789012345678901",
                        "created_at": "2025-07-12T23:00:00.000Z"
                    }
                ]
            }
            
            # Test invalid migration integrity
            invalid_integrity_result = storage.validate_migration_integrity(
                invalid_source_data, {}, self.test_config
            )
            
            self.assertFalse(invalid_integrity_result["valid"])
            self.assertGreater(invalid_integrity_result["total_errors"], 0)
            
            # Test with data loss scenario
            data_loss_target = {
                "threads": [
                    # Only one thread instead of two
                    {
                        "session_id": "integrity_test_001",
                        "thread_id": "123456789012345678",
                        "created_at": "2025-07-12T20:00:00.000Z"
                    }
                ]
            }
            
            data_loss_result = storage.validate_migration_integrity(
                valid_source_data, data_loss_target, self.test_config
            )
            
            self.assertFalse(data_loss_result["valid"])
            self.assertIn("Data loss detected", str(data_loss_result["post_migration_validation"]["errors"]))
            
            # Analyze integrity validation performance
            total_validation_time = sum(log["result"]["validation_duration"] for log in validation_log)
            
            # Log integrity analysis
            self.logger.info(
                "Migration integrity validation analysis",
                context={
                    "integrity_checks_performed": len(integrity_checks),
                    "validation_phases": len(validation_log),
                    "valid_migrations": sum(1 for check in integrity_checks if check["valid"]),
                    "invalid_migrations": sum(1 for check in integrity_checks if not check["valid"]),
                    "total_validation_time": total_validation_time,
                    "average_check_duration": sum(check["integrity_duration"] for check in integrity_checks) / max(len(integrity_checks), 1),
                    "errors_detected": sum(check["total_errors"] for check in integrity_checks),
                    "warnings_detected": sum(check["total_warnings"] for check in integrity_checks)
                }
            )
    
    # Helper methods
    
    async def _perform_schema_migration(self, source_db_path: Path, target_db_path: Path, 
                                      source_version: str, target_version: str) -> Dict[str, Any]:
        """Perform schema migration between versions."""
        migration_start = time.time()
        
        try:
            source_schema = self.migration_versions[source_version]["schema"]
            target_schema = self.migration_versions[target_version]["schema"]
            transformations = self.migration_versions[target_version]["data_transformations"]
            
            # Simulate migration process
            migration_steps = []
            
            # Create target tables
            for table_name, table_def in target_schema.items():
                migration_steps.append(f"CREATE TABLE {table_name}")
            
            # Migrate data with transformations
            migration_steps.extend([f"MIGRATE DATA: {t['type']}" for t in transformations])
            
            migration_duration = time.time() - migration_start
            
            return {
                "success": True,
                "source_version": source_version,
                "target_version": target_version,
                "migration_steps": len(migration_steps),
                "duration": migration_duration
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - migration_start
            }
    
    def _extract_table_name(self, query: str) -> str:
        """Extract table name from CREATE TABLE query."""
        # Simple extraction for testing
        parts = query.split()
        if "TABLE" in parts:
            table_idx = parts.index("TABLE") + 1
            if table_idx < len(parts):
                return parts[table_idx].strip("()")
        return "unknown_table"
    
    def _extract_table_name_from_insert(self, query: str) -> str:
        """Extract table name from INSERT query."""
        # Simple extraction for testing
        parts = query.split()
        if "INTO" in parts:
            into_idx = parts.index("INTO") + 1
            if into_idx < len(parts):
                return parts[into_idx].strip("()")
        return "unknown_table"
    
    def _extract_index_name(self, query: str) -> str:
        """Extract index name from CREATE INDEX query."""
        # Simple extraction for testing
        parts = query.split()
        if "INDEX" in parts:
            index_idx = parts.index("INDEX") + 1
            if index_idx < len(parts):
                return parts[index_idx]
        return "unknown_index"
    
    def _validate_data_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema definition."""
        errors = []
        
        for table_name, table_def in schema.items():
            if table_name not in data:
                errors.append(f"Missing table: {table_name}")
                continue
            
            table_data = data[table_name]
            if not isinstance(table_data, list):
                errors.append(f"Table {table_name} is not a list")
                continue
            
            # Validate each row has required columns
            required_columns = [col[0] for col in table_def.get("columns", [])]
            for i, row in enumerate(table_data):
                if not isinstance(row, dict):
                    errors.append(f"Row {i} in table {table_name} is not a dictionary")
                    continue
                
                for col_name in required_columns:
                    if col_name not in row and "PRIMARY KEY" in str(table_def.get("columns", [])):
                        # Skip auto-generated primary keys
                        continue
                    if col_name not in row:
                        errors.append(f"Row {i} in table {table_name} missing column: {col_name}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


def run_data_migration_tests() -> None:
    """Run data migration tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDataMigration)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nData Migration Tests Summary:")
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