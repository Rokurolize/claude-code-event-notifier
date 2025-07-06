#!/usr/bin/env python3
"""
Quick installation script for Claude Code Event Notifier
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from hook_installer import main

if __name__ == "__main__":
    main()
