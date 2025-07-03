# YouTube Shorts Generator - GitHub to RunPod Deployment

This guide shows how to deploy the YouTube Shorts Generator from GitHub directly to RunPod.

## 🚀 Quick GitHub Deployment (5 minutes)

### Step 1: Push to GitHub Repository (2 minutes)

```bash
# Initialize git repository (if not already done)
cd "Youtube short project"
git init

# Add all files
git add .

# Commit 
git commit -m "Initial commit: YouTube Shorts Generator with pause-based segmentation and context-aware prompting"

# Add GitHub remote (replace with your repository)
git remote add origin https://github.com/your-username/youtube-shorts-generator.git

# Push to GitHub
git push -u origin main
```

### Step 2: Create RunPod Template from GitHub (2 minutes)

1. Go to [RunPod Console](https://www.runpod.io/console) → **Templates**
2. Click **"New Template"**
3. Configure:
   - **Template Name**: `youtube-shorts-generator`
   - **Container Image**: Leave empty (we'll use GitHub)
   - **Container Registry Credentials**: Not needed for GitHub
   - **GitHub Repository**: `https://github.com/your-username/youtube-shorts-generator`
   - **GitHub Branch**: `main` (or your default branch)
   - **GitHub Token**: Your GitHub personal access token (if private repo)

4. **Environment Variables**:
   ```
   OPENAI_API_KEY=your_openai_key_here
   PYTHONUNBUFFERED=1
   ```

5. **Container Configuration**:
   - **Container Start Command**: `python handler.py`
   - **Container Disk**: 50GB+
   - **Expose HTTP Ports**: 8000 (optional)

### Step 3: Deploy Endpoint (1 minute)

1. Go to **Endpoints** → **"New Endpoint"**
2. Select your GitHub template
3. Configure:
   - **GPU**: RTX 4090 or better
   - **Min Workers**: 0
   - **Max Workers**: 3
   - **Idle Timeout**: 300 seconds
   - **Execution Timeout**: 600 seconds

4. Click **"Deploy"**

## 🧪 Testing Your Deployment

### Option 1: Python Script (Recommended)

```bash
# Set your RunPod API key
export RUNPOD_API_KEY="your_runpod_api_key"

# Test with Python script
python test_endpoint.py --endpoint YOUR_ENDPOINT_ID --config payloads/torah_lecture_basic.json

# Or test with direct URL
python test_endpoint.py --endpoint YOUR_ENDPOINT_ID --url "https://example.com/lecture.mp4" --clips 3
```

### Option 2: Bash Script (Linux/macOS)

```bash
# Make script executable
chmod +x test_endpoint.sh

# Test endpoint
./test_endpoint.sh YOUR_ENDPOINT_ID --config payloads/english_shiur_quality.json

# Async test with timeout
./test_endpoint.sh YOUR_ENDPOINT_ID --async --timeout 900
```

### Option 3: PowerShell Script (Windows)

```powershell
# Test endpoint
.\runpod_test.ps1 -EndpointId "YOUR_ENDPOINT_ID" -ConfigFile "payloads\torah_lecture_basic.json"

# Async test
.\runpod_test.ps1 -EndpointId "YOUR_ENDPOINT_ID" -ConfigFile "payloads\chassidish_ultimate_quality.json" -Async
```

### Option 4: Direct curl

```bash
# Set variables
ENDPOINT_ID="your_endpoint_id"
API_KEY="your_runpod_api_key"

# Make request
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @payloads/torah_lecture_basic.json \
  "https://api.runpod.ai/v2/$ENDPOINT_ID/run"
```

## 📋 GitHub Repository Structure

Your repository should have this structure:

```
youtube-shorts-generator/
├── handler.py                 # Main RunPod handler
├── Dockerfile                 # Container configuration
├── requirements-runpod.txt    # Python dependencies
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── README.md                 # Project documentation
├── GITHUB_DEPLOYMENT.md      # This file
├── 
├── # Core processing modules
├── transcribe.py             # WhisperX transcription
├── extract_shorts.py         # Clip extraction with new features
├── cut_clips.py              # Video cutting
├── reframe.py                # Vertical conversion
├── config.py                 # Configuration
├── 
├── # Enhanced features
├── pause_based_segmentation.py    # Natural speech boundaries
├── context_aware_prompting.py     # Better GPT evaluation
├── 
├── # Testing and utilities
├── test_endpoint.py          # Python testing script
├── test_endpoint.sh          # Bash testing script
├── runpod_test.ps1          # PowerShell testing script
├── 
├── # Configuration examples
└── payloads/
    ├── torah_lecture_basic.json
    ├── english_shiur_quality.json
    ├── chassidish_ultimate_quality.json
    └── fast_processing.json
```

## 🔧 GitHub-Specific Configuration

### Dockerfile Optimizations

The Dockerfile is optimized for GitHub deployment:

```dockerfile
# Copy requirements first for better caching
COPY requirements-runpod.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copy entire project
COPY . .

# Pre-download models during build
RUN python -c "import whisperx; ..."
```

### Environment Variables

Set these in your RunPod template:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for GPT analysis |
| `PYTHONUNBUFFERED` | ⚡ Recommended | Better logging output |
| `CUDA_VISIBLE_DEVICES` | 🔧 Optional | GPU device selection |

### .gitignore Configuration

The `.gitignore` excludes:
- Sensitive files (`.env`, API keys)
- Generated outputs (video files, test results)
- Large model files (downloaded at runtime)
- Development artifacts

## 🔄 Continuous Deployment

### Option 1: Manual Updates

```bash
# Make changes to your code
git add .
git commit -m "Update: improved segmentation algorithm"
git push origin main

# RunPod will automatically rebuild from the latest commit
```

### Option 2: GitHub Actions (Advanced)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to RunPod
on:
  push:
    branches: [main]
    
jobs:
  trigger-rebuild:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger RunPod rebuild
        run: |
          curl -X POST \
            -H "Authorization: Bearer ${{ secrets.RUNPOD_API_KEY }}" \
            "https://api.runpod.ai/v2/templates/YOUR_TEMPLATE_ID/rebuild"
```

## 🔐 Security for GitHub Deployment

### Repository Settings

1. **Private Repository**: Recommended for production
2. **Branch Protection**: Protect main branch
3. **GitHub Token**: Use fine-grained personal access token

### Secrets Management

- ✅ **DO**: Use RunPod environment variables for secrets
- ✅ **DO**: Use `.env.example` for documentation
- ❌ **DON'T**: Commit actual API keys
- ❌ **DON'T**: Include sensitive data in repository

### API Key Security

```bash
# Create .env file locally (not committed)
echo "OPENAI_API_KEY=your_key_here" > .env

# Set in RunPod template environment variables
# OPENAI_API_KEY=your_key_here
```

## 📊 Performance Monitoring

### Build Time Optimization

The GitHub deployment includes:
- **Layer Caching**: Requirements installed before code copy
- **Model Pre-baking**: WhisperX models downloaded during build
- **Dependency Optimization**: Minimal requirements for faster builds

### Runtime Performance

| Model Size | Build Time | Cold Start | Processing Time |
|------------|------------|------------|-----------------|
| tiny       | ~5 min     | ~30s       | 1-3 min        |
| small      | ~8 min     | ~45s       | 2-5 min        |
| medium     | ~12 min    | ~60s       | 4-8 min        |
| large-v2   | ~20 min    | ~90s       | 8-15 min       |

## 🚨 Troubleshooting GitHub Deployment

### Common Issues

#### 1. Build Failures
```
Error: Failed to build from GitHub repository
```
**Solutions**:
- Check Dockerfile syntax
- Verify requirements.txt exists
- Ensure repository is accessible

#### 2. Handler Not Found
```
Error: handler function not found
```
**Solutions**:
- Verify `handler.py` exists in repository root
- Check `handler(event)` function is defined
- Ensure proper Python imports

#### 3. Environment Variables
```
Error: OpenAI API key not configured
```
**Solutions**:
- Set `OPENAI_API_KEY` in RunPod template
- Verify environment variable spelling
- Check `.env` file is not committed

#### 4. GitHub Access Issues
```
Error: Unable to access GitHub repository
```
**Solutions**:
- Check repository URL is correct
- Verify repository is public or token is provided
- Ensure branch name is correct

### Debug Steps

1. **Check RunPod Logs**:
   - Go to Endpoint → Logs
   - Look for build and runtime errors

2. **Test Locally**:
   ```bash
   python test_local.py
   python handler.py
   ```

3. **Verify GitHub Repository**:
   - Ensure all required files are committed
   - Check repository is accessible
   - Verify latest commits are pushed

## 🎯 Next Steps

1. **Deploy to GitHub** following steps above
2. **Test with real videos** using test scripts
3. **Monitor performance** through RunPod dashboard
4. **Scale up** based on usage patterns
5. **Implement CI/CD** for automated deployments

---

**🎉 You're ready to deploy from GitHub to RunPod!**

This deployment method ensures your code is version-controlled, easily updatable, and automatically built in the cloud.