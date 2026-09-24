#!/usr/bin/env python3
"""
Git Tree Animator - Main Entry Point

Run with: python run.py
"""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "ui/app.py"])
