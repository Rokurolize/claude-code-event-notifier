#!/usr/bin/env python3
"""
Setup script for Claude Code Event Notifier
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (
    (this_directory / "README.md").read_text()
    if (this_directory / "README.md").exists()
    else ""
)

setup(
    name="claude-code-event-notifier",
    version="1.0.0",
    author="Claude Code Event Notifier Contributors",
    description="Send Claude Code hook events to Discord for real-time monitoring",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/user/claude-code-event-notifier",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - uses standard library only
    ],
    entry_points={
        "console_scripts": [
            "claude-event-notifier=claude_code_event_notifier.src.event_notifier:main",
        ],
    },
    include_package_data=True,
    package_data={
        "claude_code_event_notifier": ["config/.env.discord.example"],
    },
)
