#!/usr/bin/env python3
"""Simple test runner for the Discord Event Notifier test suite."""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_all_tests():
    """Discover and run all tests."""
    # Create test loader
    loader = unittest.TestLoader()
    
    # Discover tests
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def run_unit_tests():
    """Run only unit tests."""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / 'unit'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


def run_integration_tests():
    """Run only integration tests."""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / 'integration'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Discord Event Notifier tests')
    parser.add_argument(
        '--type',
        choices=['all', 'unit', 'integration'],
        default='all',
        help='Type of tests to run'
    )
    
    args = parser.parse_args()
    
    if args.type == 'unit':
        sys.exit(run_unit_tests())
    elif args.type == 'integration':
        sys.exit(run_integration_tests())
    else:
        sys.exit(run_all_tests())