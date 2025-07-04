#!/usr/bin/env python3
"""
Pre-Build Validation Script
Run before Docker builds to catch dependency conflicts early
"""

import os
import sys
import subprocess

def main():
    print("🚀 Pre-Build Dependency Validation")
    print("=" * 50)
    
    # Get script directory and requirements file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_file = os.path.join(script_dir, "requirements-runpod.txt")
    
    # Check if requirements file exists
    if not os.path.exists(requirements_file):
        print("❌ requirements-runpod.txt not found!")
        print(f"   Looking for: {requirements_file}")
        return 1
    
    print("📝 Requirements file found")
    print("🔍 Running dependency conflict check...")
    print()
    
    # Run the dependency checker
    try:
        result = subprocess.run([sys.executable, "simple_dependency_check.py"], 
                              capture_output=False, text=True)
        
        if result.returncode == 0:
            print()
            print("✅ Dependency check passed!")
            print("🐳 Ready to build Docker image")
            print()
            print("To build now, run:")
            print("  docker build -f Dockerfile.runpod -t youtube-shorts-editor .")
            print()
            print("Or to build on RunPod, upload your files and use:")
            print("  Dockerfile.runpod as the container file")
            return 0
        else:
            print()
            print("❌ Dependency check failed!")
            print("🛠️  Fix conflicts before building Docker image")
            return 1
            
    except FileNotFoundError:
        print("❌ simple_dependency_check.py not found!")
        print("   Make sure all files are in the project directory")
        return 1
    except Exception as e:
        print(f"❌ Error running dependency check: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)