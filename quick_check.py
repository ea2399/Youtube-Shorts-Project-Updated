#!/usr/bin/env python3
"""Quick dependency check - just run 'python quick_check.py'"""
import subprocess
import sys
import os

# Change to script directory to ensure we find the files
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Run the dependency checker
check_script = os.path.join(script_dir, "simple_dependency_check.py")
subprocess.run([sys.executable, check_script])