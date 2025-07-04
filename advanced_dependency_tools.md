# Advanced Dependency Conflict Detection Tools

## 1. Quick Local Check (Created Above)
```bash
python3 simple_dependency_check.py
```
- **Pros**: No dependencies, fast, catches known issues
- **Cons**: Limited to known patterns
- **Use**: Before every Docker build

## 2. pip-tools (Recommended)
```bash
# Install
pip install pip-tools

# Create requirements.in (simplified input)
echo "fastapi==0.104.1" > requirements.in
echo "celery[redis]==5.3.4" >> requirements.in
echo "runpod==1.6.2" >> requirements.in
# ... add your main packages

# Generate locked requirements.txt with full dependency tree
pip-compile requirements.in

# Check for conflicts
pip-compile --dry-run requirements.in
```
- **Pros**: Industry standard, full dependency resolution
- **Cons**: Requires separate environment setup
- **Use**: For major requirements changes

## 3. pipdeptree
```bash
pip install pipdeptree

# Visualize dependency tree
pipdeptree

# Check for conflicts
pipdeptree --warn conflict

# JSON output for programmatic analysis
pipdeptree --json
```
- **Pros**: Great visualization, conflict detection
- **Cons**: Needs packages already installed
- **Use**: After successful builds to understand dependencies

## 4. Docker Multi-Stage Build for Testing
Add to your Dockerfile:
```dockerfile
# Test stage - fails fast on conflicts
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04 as deps-test
COPY requirements-runpod.txt .
RUN pip install --dry-run -r requirements-runpod.txt

# Main build stage
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04 as main
# ... rest of build
```
- **Pros**: Tests in exact target environment
- **Cons**: Still requires Docker build time
- **Use**: For CI/CD pipelines

## 5. Poetry (Alternative Package Manager)
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Initialize project
poetry init

# Add dependencies (automatically resolves conflicts)
poetry add fastapi==0.104.1 celery[redis]==5.3.4

# Check for issues
poetry check
```
- **Pros**: Modern dependency resolution, lock files
- **Cons**: Requires switching from pip/requirements.txt
- **Use**: For new projects or major refactoring

## 6. Online Dependency Checkers

### PyPI Dependency Graph
Visit: https://pypi.org/project/[package-name]/
- Shows dependencies for any package version
- Manual but reliable for checking specific conflicts

### Libraries.io
Visit: https://libraries.io/pypi/[package-name]
- Dependency analysis and security alerts
- Good for understanding dependency trees

## Recommended Workflow

### Before Making Changes:
1. Run `python3 simple_dependency_check.py` (instant)
2. If adding new packages, check their PyPI pages for conflicting deps

### For Major Updates:
1. Use `pip-tools` to generate clean requirements.txt
2. Test in local virtual environment first
3. Use multi-stage Docker build for validation

### Quick Commands to Add to Your Workflow:
```bash
# Add these to your build script or Makefile
alias dep-check="python3 simple_dependency_check.py"
alias dep-compile="pip-compile --upgrade requirements.in"
alias dep-tree="pipdeptree --warn conflict"

# Pre-build validation
dep-check && echo "✅ Dependencies look good, proceeding with build..."
```

## The 7 Conflicts You Hit (Now Prevented):
1. `py-webrtcvad-wheels` → Caught by invalid package check
2. `pyscenedetect` → Caught by invalid package check  
3. `pydantic-v1` → Caught by invalid package check
4. `anyio>=4.0.0` + `fastapi==0.104.1` → Caught by known conflicts
5. `aiohttp==3.9.1` + `runpod==1.6.2` → Caught by known conflicts
6. `redis==5.0.1` + `celery[redis]==5.3.4` → Caught by known conflicts
7. `rich==13.7.0` + `norfair==2.2.0` → Caught by known conflicts

**Result**: All future conflicts should be caught before Docker build! 🎯