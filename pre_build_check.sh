#!/bin/bash
# Pre-Build Dependency Validation Script
# Run this before any Docker build to catch conflicts early

echo "🚀 Pre-Build Dependency Validation"
echo "=================================="

# Check if requirements file exists
if [ ! -f "requirements-runpod.txt" ]; then
    echo "❌ requirements-runpod.txt not found!"
    exit 1
fi

echo "📝 Requirements file found"

# Run our simple dependency checker
echo "🔍 Running dependency conflict check..."
python3 simple_dependency_check.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependency check passed!"
    echo "🐳 Ready to build Docker image"
    echo ""
    echo "To build now, run:"
    echo "  docker build -f Dockerfile.runpod -t youtube-shorts-editor ."
else
    echo ""
    echo "❌ Dependency check failed!"
    echo "🛠️  Fix conflicts before building Docker image"
    exit 1
fi