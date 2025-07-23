#!/usr/bin/env python3
"""Setup guide for Claude Code Discord notifications.

This is the main entry point for setting up Discord notifications.
It guides users to choose the appropriate architecture.
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Show setup options and guide user."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║        Claude Code Discord Notifier Setup Guide           ║
╚═══════════════════════════════════════════════════════════╝

This project offers two architectures:

📦 Simple Architecture (Recommended)
   • Zero dependencies - pure Python 3.13+
   • Fast and lightweight (~900 lines)
   • Fail-silent design
   • Perfect for basic notifications
   
   Setup: uv run python setup_simple.py

🏗️  Full Architecture (Advanced)
   • Modular design with advanced features
   • Threading support for Task tools
   • Session management and history
   • Rich formatting with embeds
   • ~8000+ lines of code
   
   Setup: uv run python setup_full.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose your architecture:
  1) Simple (Recommended for most users)
  2) Full (Advanced features)
  3) Exit

""")
    
    while True:
        try:
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == "1":
                print("\n🚀 Starting Simple Architecture setup...\n")
                return run_setup("setup_simple.py")
            elif choice == "2":
                print("\n🏗️  Starting Full Architecture setup...\n")
                return run_setup("setup_full.py")
            elif choice == "3":
                print("\n👋 Setup cancelled.")
                return 0
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\n\n👋 Setup cancelled.")
            return 0


def run_setup(script_name: str) -> int:
    """Run the selected setup script."""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"❌ Error: Setup script not found: {script_path}")
        return 1
        
    # Check if --test flag should be added
    print("Would you like to test the integration after setup? (y/N): ", end="")
    try:
        test_choice = input().strip().lower()
        test_flag = ["--test"] if test_choice in ["y", "yes"] else []
    except KeyboardInterrupt:
        test_flag = []
        print()
    
    # Run the setup script
    cmd = ["uv", "run", "python", str(script_path)] + test_flag
    
    try:
        return subprocess.run(cmd).returncode
    except Exception as e:
        print(f"❌ Error running setup: {e}")
        return 1


if __name__ == "__main__":
    # Print deprecation notice if old scripts are used
    script_name = Path(sys.argv[0]).name
    if script_name in ["configure_hooks.py", "configure_hooks_simple.py"]:
        print(f"""
⚠️  DEPRECATION WARNING ⚠️

The script '{script_name}' is deprecated.

Please use one of the new setup scripts:
  • setup_simple.py  - For simple architecture (recommended)
  • setup_full.py    - For full architecture
  • setup_guide.py   - Interactive setup guide

Run: uv run python setup_guide.py
""")
        sys.exit(1)
    
    sys.exit(main())