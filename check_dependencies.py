#!/usr/bin/env python3
"""
Dependency Conflict Checker for RunPod Requirements
Proactively identifies version conflicts before Docker build
"""

import requests
import re
import sys
from typing import Dict, List, Tuple, Optional
from packaging import specifiers, version

def parse_requirement(req_line: str) -> Optional[Tuple[str, str]]:
    """Parse requirement line into package name and version spec"""
    req_line = req_line.strip()
    if not req_line or req_line.startswith('#'):
        return None
    
    # Handle extras like celery[redis]==5.3.4
    if '[' in req_line:
        pkg_with_extra = req_line.split('==')[0].split('>=')[0].split('<=')[0]
        pkg_name = pkg_with_extra.split('[')[0]
        version_spec = req_line.replace(pkg_with_extra, '').lstrip()
    else:
        # Simple package==version format
        for op in ['==', '>=', '<=', '>', '<', '~=']:
            if op in req_line:
                pkg_name, version_spec = req_line.split(op, 1)
                version_spec = op + version_spec
                break
        else:
            pkg_name = req_line
            version_spec = ''
    
    return pkg_name.strip(), version_spec.strip()

def get_package_dependencies(pkg_name: str, pkg_version: str = None) -> Dict[str, str]:
    """Get package dependencies from PyPI"""
    try:
        if pkg_version:
            url = f"https://pypi.org/pypi/{pkg_name}/{pkg_version}/json"
        else:
            url = f"https://pypi.org/pypi/{pkg_name}/json"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        
        data = resp.json()
        
        if pkg_version:
            requires_dist = data.get('info', {}).get('requires_dist', []) or []
        else:
            # Get latest version dependencies
            latest_version = data.get('info', {}).get('version', '')
            return get_package_dependencies(pkg_name, latest_version)
        
        deps = {}
        for req in requires_dist:
            if ';' in req:  # Skip conditional dependencies for now
                req = req.split(';')[0].strip()
            
            parsed = parse_requirement(req)
            if parsed:
                dep_name, dep_version = parsed
                deps[dep_name] = dep_version
        
        return deps
    
    except Exception as e:
        print(f"Warning: Could not fetch dependencies for {pkg_name}: {e}")
        return {}

def check_version_conflict(req_version: str, dep_version: str) -> bool:
    """Check if two version specifications conflict"""
    if not req_version or not dep_version:
        return False
    
    try:
        req_spec = specifiers.SpecifierSet(req_version)
        dep_spec = specifiers.SpecifierSet(dep_version)
        
        # Find a version that satisfies both
        # This is a simplified check - we test with some common versions
        test_versions = ["1.0.0", "2.0.0", "3.0.0", "4.0.0", "5.0.0", 
                        "10.0.0", "11.0.0", "12.0.0", "13.0.0", "14.0.0"]
        
        for test_ver in test_versions:
            try:
                v = version.Version(test_ver)
                if v in req_spec and v in dep_spec:
                    return False  # Found compatible version
            except:
                continue
        
        return True  # No compatible version found
    
    except Exception:
        return False

def analyze_requirements_file(filepath: str):
    """Analyze requirements file for potential conflicts"""
    print(f"🔍 Analyzing {filepath} for dependency conflicts...\n")
    
    # Parse requirements file
    requirements = {}
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            parsed = parse_requirement(line)
            if parsed:
                pkg_name, version_spec = parsed
                requirements[pkg_name] = {
                    'version': version_spec,
                    'line': line_num
                }
    
    print(f"📦 Found {len(requirements)} packages to analyze\n")
    
    # Check for direct conflicts
    conflicts_found = []
    
    for pkg_name, pkg_info in requirements.items():
        print(f"Checking {pkg_name}...")
        
        # Extract version from spec (handle ==, >=, etc.)
        version_spec = pkg_info['version']
        if '==' in version_spec:
            pkg_version = version_spec.replace('==', '')
        elif '>=' in version_spec:
            pkg_version = None  # Use latest for >= specs
        else:
            pkg_version = None
        
        # Get dependencies
        deps = get_package_dependencies(pkg_name, pkg_version)
        
        # Check each dependency against our requirements
        for dep_name, dep_version in deps.items():
            if dep_name in requirements:
                our_version = requirements[dep_name]['version']
                
                if check_version_conflict(our_version, dep_version):
                    conflict = {
                        'package': pkg_name,
                        'dependency': dep_name,
                        'our_version': our_version,
                        'required_version': dep_version,
                        'line': pkg_info['line'],
                        'dep_line': requirements[dep_name]['line']
                    }
                    conflicts_found.append(conflict)
                    print(f"  ⚠️  CONFLICT: {pkg_name} requires {dep_name}{dep_version}, but we have {dep_name}{our_version}")
    
    print(f"\n{'='*60}")
    if conflicts_found:
        print(f"❌ Found {len(conflicts_found)} potential conflicts:")
        print()
        
        for i, conflict in enumerate(conflicts_found, 1):
            print(f"{i}. {conflict['package']} (line {conflict['line']}) vs {conflict['dependency']} (line {conflict['dep_line']})")
            print(f"   Required: {conflict['dependency']}{conflict['required_version']}")
            print(f"   We have:  {conflict['dependency']}{conflict['our_version']}")
            print()
        
        print("🔧 Suggested fixes:")
        for conflict in conflicts_found:
            print(f"   - Update line {conflict['dep_line']}: {conflict['dependency']}{conflict['required_version']}")
        
    else:
        print("✅ No obvious dependency conflicts detected!")
        print("   Note: This doesn't guarantee no conflicts exist,")
        print("   but catches the most common version mismatches.")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    requirements_file = "/mnt/c/Users/User/Youtube short project/requirements-runpod.txt"
    analyze_requirements_file(requirements_file)