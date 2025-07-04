#!/usr/bin/env python3
"""
Simple Dependency Conflict Checker - No external dependencies needed
"""

import re
import sys

def parse_simple_requirement(line):
    """Parse requirement line - simplified version"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None, None
    
    # Handle extras like celery[redis]==5.3.4
    if '[' in line:
        pkg_with_extra = line.split('==')[0].split('>=')[0]
        pkg_name = pkg_with_extra.split('[')[0]
        if '==' in line:
            version = line.split('==')[1].strip()
        else:
            version = None
    else:
        if '==' in line:
            pkg_name, version = line.split('==', 1)
            pkg_name = pkg_name.strip()
            version = version.strip()
        elif '>=' in line:
            pkg_name = line.split('>=')[0].strip()
            version = None
        else:
            pkg_name = line.strip()
            version = None
    
    return pkg_name, version

def check_known_conflicts(requirements):
    """Check for known common conflicts"""
    conflicts = []
    
    # Known conflict patterns
    known_issues = [
        {
            'packages': ['fastapi', 'anyio'],
            'rule': 'FastAPI 0.104.1 requires anyio<4.0.0, anyio>=4.0.0 conflicts'
        },
        {
            'packages': ['celery', 'redis'], 
            'rule': 'Celery 5.3.4 requires redis<5.0.0, redis>=5.0.0 conflicts'
        },
        {
            'packages': ['norfair', 'rich'],
            'rule': 'Norfair 2.2.0 requires rich<13.0.0, rich>=13.0.0 conflicts'
        },
        {
            'packages': ['runpod', 'aiohttp'],
            'rule': 'RunPod 1.6.2 requires aiohttp==3.9.3, other versions conflict'
        }
    ]
    
    for issue in known_issues:
        pkg_names = issue['packages']
        if all(pkg in requirements for pkg in pkg_names):
            # Check specific version conflicts
            if pkg_names == ['fastapi', 'anyio']:
                fastapi_ver = requirements.get('fastapi', {}).get('version')
                anyio_ver = requirements.get('anyio', {}).get('version')
                if fastapi_ver == '0.104.1' and anyio_ver and '4.' in anyio_ver:
                    conflicts.append(f"CONFLICT: FastAPI 0.104.1 + anyio {anyio_ver} - {issue['rule']}")
            
            elif pkg_names == ['celery', 'redis']:
                celery_ver = requirements.get('celery', {}).get('version')
                redis_ver = requirements.get('redis', {}).get('version')
                if celery_ver == '5.3.4' and redis_ver and redis_ver.startswith('5.'):
                    conflicts.append(f"CONFLICT: Celery 5.3.4 + redis {redis_ver} - {issue['rule']}")
            
            elif pkg_names == ['norfair', 'rich']:
                norfair_ver = requirements.get('norfair', {}).get('version')
                rich_ver = requirements.get('rich', {}).get('version')
                if norfair_ver and rich_ver and rich_ver.startswith('13.'):
                    conflicts.append(f"CONFLICT: Norfair {norfair_ver} + rich {rich_ver} - {issue['rule']}")
            
            elif pkg_names == ['runpod', 'aiohttp']:
                runpod_ver = requirements.get('runpod', {}).get('version')
                aiohttp_ver = requirements.get('aiohttp', {}).get('version')
                if runpod_ver == '1.6.2' and aiohttp_ver and aiohttp_ver != '3.9.3':
                    conflicts.append(f"CONFLICT: RunPod 1.6.2 + aiohttp {aiohttp_ver} - {issue['rule']}")
    
    return conflicts

def analyze_requirements(filepath):
    """Analyze requirements file"""
    print(f"🔍 Checking {filepath} for known dependency conflicts...\n")
    
    requirements = {}
    
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                pkg_name, version = parse_simple_requirement(line)
                if pkg_name:
                    requirements[pkg_name] = {
                        'version': version,
                        'line': line_num,
                        'raw': line.strip()
                    }
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return
    
    print(f"📦 Found {len(requirements)} packages\n")
    
    # Check for known conflicts
    conflicts = check_known_conflicts(requirements)
    
    # Check for common problematic packages
    problematic_packages = {
        'pydantic-v1': 'This package does not exist. Use pydantic>=2.0 instead.',
        'py-webrtcvad-wheels': 'Use webrtcvad instead.',
        'pyscenedetect': 'Use scenedetect instead.',
        'mediapipe-tasks': 'Included in mediapipe>=0.10.9, remove separate dependency.'
    }
    
    for pkg, issue in problematic_packages.items():
        if pkg in requirements:
            conflicts.append(f"INVALID PACKAGE: {pkg} - {issue}")
    
    # Display results
    print("="*60)
    if conflicts:
        print(f"❌ Found {len(conflicts)} potential issues:")
        print()
        for i, conflict in enumerate(conflicts, 1):
            print(f"{i}. {conflict}")
        print()
        
        print("🔧 Quick fixes based on our previous resolutions:")
        print("   - fastapi==0.104.1 → use anyio>=3.7.1,<4.0.0")
        print("   - celery[redis]==5.3.4 → use redis==4.6.0") 
        print("   - norfair==2.2.* → use rich==12.6.0")
        print("   - runpod==1.6.2 → use aiohttp==3.9.3")
        print("   - Remove: pydantic-v1, py-webrtcvad-wheels, mediapipe-tasks")
        print("   - Replace: pyscenedetect → scenedetect")
    else:
        print("✅ No known conflicts detected!")
        print("   Your requirements should build successfully.")
    
    print("="*60)
    print()
    print("💡 Pro tips to avoid future conflicts:")
    print("   1. Run this script before building Docker images")
    print("   2. Use 'pip-tools' for better dependency resolution:")
    print("      pip install pip-tools")
    print("      pip-compile requirements.in")
    print("   3. Consider using 'pipdeptree' to visualize dependencies:")
    print("      pip install pipdeptree && pipdeptree")
    print("   4. Use virtual environments to test locally first")

if __name__ == "__main__":
    import os
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_file = os.path.join(script_dir, "requirements-runpod.txt")
    analyze_requirements(requirements_file)