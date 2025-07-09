#!/usr/bin/env python3
"""Test script for thread persistence functionality.

This script tests the core thread persistence features to ensure
duplicate thread creation is properly prevented.
"""

import tempfile
from pathlib import Path

# Import the modules
from src.thread_storage import ThreadStorage


def _test_store_thread(storage, session_id, thread_id, channel_id, thread_name):
    """Test storing a thread."""
    print(f"  📝 Storing thread: {session_id} -> {thread_id}")

    success = storage.store_thread(
        session_id=session_id,
        thread_id=thread_id,
        channel_id=channel_id,
        thread_name=thread_name,
        is_archived=False,
    )

    if success:
        print("  ✅ Thread stored successfully")
    else:
        print("  ❌ Failed to store thread")
    return success


def _test_retrieve_thread(storage, session_id):
    """Test retrieving a thread."""
    print(f"  🔍 Retrieving thread for session: {session_id}")
    record = storage.get_thread(session_id)

    if record:
        print(f"  ✅ Thread retrieved: {record.thread_id}")
        print(f"     Thread name: {record.thread_name}")
        print(f"     Created: {record.created_at}")
        print(f"     Archived: {record.is_archived}")
        return True
    print("  ❌ Failed to retrieve thread")
    return False


def _test_search_by_name(storage, channel_id, thread_name, session_id):
    """Test searching thread by name."""
    print(f"  🔎 Searching for thread by name: {thread_name}")
    found_thread = storage.find_thread_by_name(channel_id, thread_name)

    if found_thread and found_thread.session_id == session_id:
        print("  ✅ Thread found by name search")
        return True
    print("  ❌ Thread not found by name search")
    return False


def _test_update_thread_status(storage, session_id):
    """Test updating thread status."""
    print("  🔄 Testing thread status update...")
    success = storage.update_thread_status(session_id, is_archived=True)

    if success:
        updated_record = storage.get_thread(session_id)
        if updated_record and updated_record.is_archived:
            print("  ✅ Thread status updated successfully")
            return True
        print("  ❌ Thread status update failed")
        return False
    print("  ❌ Failed to update thread status")
    return False


def _test_remove_thread(storage, session_id):
    """Test removing a thread."""
    print("  🗑️  Removing thread...")
    success = storage.remove_thread(session_id)

    if success:
        removed_record = storage.get_thread(session_id)
        if removed_record is None:
            print("  ✅ Thread removed successfully")
            return True
        print("  ❌ Thread still exists after removal")
        return False
    print("  ❌ Failed to remove thread")
    return False


def test_basic_storage_operations():
    """Test basic ThreadStorage operations."""
    print("🧪 Testing basic ThreadStorage operations...")

    # Create temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_threads.db"
        storage = ThreadStorage(db_path=db_path, cleanup_days=30)

        # Test data
        session_id = "test-session-12345"
        thread_id = "987654321098765432"
        channel_id = "123456789012345678"
        thread_name = "Session test-ses"

        # Run tests
        if not _test_store_thread(storage, session_id, thread_id, channel_id, thread_name):
            return False

        if not _test_retrieve_thread(storage, session_id):
            return False

        if not _test_search_by_name(storage, channel_id, thread_name, session_id):
            return False

        # Test statistics
        stats = storage.get_stats()
        print(
            f"  📊 Storage stats: {stats['total_threads']} threads, {stats['active_threads']} active"
        )

        if not _test_update_thread_status(storage, session_id):
            return False

        if not _test_remove_thread(storage, session_id):
            return False

    return True


def test_multiple_sessions():
    """Test handling multiple sessions."""
    print("\n🧪 Testing multiple session handling...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_threads.db"
        storage = ThreadStorage(db_path=db_path)

        # Store multiple sessions
        sessions = [
            ("session-1", "987654321098765430", "Session session-1"),
            ("session-2", "987654321098765431", "Session session-2"),
            ("session-3", "987654321098765432", "Session session-3"),
        ]

        channel_id = "123456789012345678"

        print(f"  📝 Storing {len(sessions)} sessions...")
        for session_id, thread_id, thread_name in sessions:
            success = storage.store_thread(
                session_id=session_id,
                thread_id=thread_id,
                channel_id=channel_id,
                thread_name=thread_name,
                is_archived=False,
            )
            if not success:
                print(f"  ❌ Failed to store session {session_id}")
                return False

        print("  ✅ All sessions stored")

        # Retrieve all threads for channel
        print("  🔍 Retrieving all threads for channel...")
        threads = storage.find_threads_by_channel(channel_id)

        if len(threads) == len(sessions):
            print(f"  ✅ Found {len(threads)} threads in channel")
        else:
            print(f"  ❌ Expected {len(sessions)} threads, found {len(threads)}")
            return False

        # Test individual retrieval
        print("  🔍 Testing individual session retrieval...")
        for session_id, expected_thread_id, _ in sessions:
            record = storage.get_thread(session_id)
            if record and record.thread_id == expected_thread_id:
                print(f"    ✅ Session {session_id}: {record.thread_id}")
            else:
                print(f"    ❌ Session {session_id}: retrieval failed")
                return False

    return True


def test_persistence_across_instances():
    """Test that data persists across ThreadStorage instances."""
    print("\n🧪 Testing persistence across instances...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "persistent_test.db"

        session_id = "persistent-session"
        thread_id = "987654321098765433"
        channel_id = "123456789012345678"
        thread_name = "Persistent Session persist"

        # Create first instance and store data
        print("  📝 Storing data with first instance...")
        storage1 = ThreadStorage(db_path=db_path)
        success = storage1.store_thread(
            session_id=session_id,
            thread_id=thread_id,
            channel_id=channel_id,
            thread_name=thread_name,
            is_archived=False,
        )

        if not success:
            print("  ❌ Failed to store with first instance")
            return False

        # Close first instance (Python will handle cleanup)
        del storage1

        # Create second instance and retrieve data
        print("  🔍 Retrieving data with second instance...")
        storage2 = ThreadStorage(db_path=db_path)
        record = storage2.get_thread(session_id)

        if record and record.thread_id == thread_id:
            print("  ✅ Data persisted across instances")
            print(f"     Retrieved: {record.session_id} -> {record.thread_id}")
        else:
            print("  ❌ Data not persisted across instances")
            return False

    return True


def main():
    """Run all tests."""
    print("🚀 Running Thread Persistence Tests\n")

    tests = [
        ("Basic Storage Operations", test_basic_storage_operations),
        ("Multiple Sessions", test_multiple_sessions),
        ("Persistence Across Instances", test_persistence_across_instances),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"{'=' * 60}")
        print(f"Test: {test_name}")
        print(f"{'=' * 60}")

        try:
            if test_func():
                print(f"\n✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            print(f"\n💥 {test_name}: ERROR - {e}")

    print(f"\n{'=' * 60}")
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print(f"{'=' * 60}")

    if passed == total:
        print("🎉 All tests passed! Thread persistence is working correctly.")
        return True
    print("⚠️  Some tests failed. Check the output above for details.")
    return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
