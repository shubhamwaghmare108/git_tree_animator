#!/usr/bin/env python3
"""
Git Tree Animator - Main Entry Point

Run with: python run.py
"""

import subprocess
import sys

def main():
    """Launch the Streamlit application."""
    return subprocess.call([sys.executable, "-m", "streamlit", "run", "ui/app.py"])


if __name__ == "__main__":
    raise SystemExit(main())
