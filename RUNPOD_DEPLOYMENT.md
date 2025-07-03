# YouTube Shorts Generator - RunPod Deployment Guide

This guide walks you through deploying the YouTube Shorts Generator to RunPod for GPU-accelerated processing.

## 🚀 Quick Start

### Prerequisites
- RunPod account with API access
- Docker Hub account (for image storage)
- OpenAI API key
- Basic familiarity with Docker and RunPod

### 1. Environment Setup

Create a `.env` file with your API keys:
```bash
OPENAI_API_KEY=your_openai_key_here
RUNPOD_API_KEY=your_runpod_key_here
```

### 2. Build and Push Docker Image

```bash
# Build the image
docker build -t your-username/youtube-shorts-generator .

# Tag for different versions
docker tag your-username/youtube-shorts-generator your-username/youtube-shorts-generator:latest
docker tag your-username/youtube-shorts-generator your-username/youtube-shorts-generator:v1.0

# Push to Docker Hub
docker push your-username/youtube-shorts-generator:latest
docker push your-username/youtube-shorts-generator:v1.0
```

### 3. Create RunPod Template

1. Go to [RunPod Console](https://www.runpod.io/console) → Templates
2. Click "New Template"
3. Configure:
   - **Template Name**: `youtube-shorts-generator`
   - **Container Image**: `your-username/youtube-shorts-generator:latest`
   - **Container Registry Credentials**: Your Docker Hub credentials (if private)
   - **Expose HTTP Ports**: `8000` (optional)
   - **Container Start Command**: Leave default (uses Dockerfile CMD)

### 4. Environment Variables

Set in template or pod:
- `OPENAI_API_KEY`: Your OpenAI API key for GPT analysis
- `RUNPOD_API_KEY`: For logging/metrics (optional)

### 5. Resource Configuration

Recommended specifications:
- **GPU**: RTX 4090, A6000, or A100 (for WhisperX performance)
- **Container Disk**: 50GB+ (for models and processing)
- **Volume**: Optional persistent storage for outputs

### 6. Deploy and Test

```powershell
# Test with PowerShell script
.\runpod_test.ps1 -EndpointId "your-endpoint-id" -ConfigFile "payloads\torah_lecture_basic.json"
```

## 📋 Detailed Configuration

### Docker Image Features

Our Docker image includes:
- **Pre-downloaded WhisperX models** (tiny, base, small, medium)
- **Pre-downloaded alignment models** for Hebrew and English
- **FFmpeg** for video processing
- **All Python dependencies** pre-installed
- **GPU optimization** with CUDA 11.8

### Handler API

#### Input Format
```json
{
  "input": {
    "video_url": "https://example.com/video.mp4",
    "language": "he",           // "he" or "en"
    "num_clips": 3,            // Number of clips to generate
    "min_duration": 20,        // Minimum clip duration (seconds)
    "max_duration": 60,        // Maximum clip duration (seconds)
    "vertical": true,          // Create vertical versions
    "subtitles": true,         // Generate subtitle files
    "model_size": "small"      // WhisperX model size
  }
}
```

#### Output Format
```json
{
  "output": {
    "success": true,
    "clips_generated": 3,
    "clips": [
      {
        "index": 1,
        "title": "The Sacred Power of God's Names",
        "start": 0.0,
        "end": 31.4,
        "duration": 31.4,
        "score": 8.2,
        "context_dependency": "Low",
        "reasoning": "Complete teaching unit...",
        "tags": ["Divine Names", "Torah Wisdom"],
        "files": {
          "horizontal": "/path/to/clip1.mp4",
          "vertical": "/path/to/clip1_vertical.mp4",
          "subtitle": "/path/to/clip1.srt"
        }
      }
    ],
    "transcription": {
      "segments": 56,
      "language": "he",
      "file": "/path/to/transcript.srt"
    },
    "analysis": {
      "method": "context_aware_multi_pass",
      "themes": ["Divine Names", "Spiritual Practice"],
      "overall_topic": "Torah teaching about divine names"
    },
    "processing_info": {
      "model_size": "small",
      "language": "he",
      "vertical_created": true,
      "subtitles_created": true
    }
  }
}
```

### Model Performance Guide

| Model Size | VRAM Usage | Processing Speed | Accuracy | Recommended Use |
|------------|------------|------------------|----------|-----------------|
| tiny       | ~1 GB      | Very Fast        | Basic    | Quick testing |
| base       | ~1 GB      | Fast             | Good     | Development |
| small      | ~2 GB      | Medium           | Very Good| Production |
| medium     | ~5 GB      | Slow             | Excellent| High quality |
| large-v2   | ~10 GB     | Very Slow        | Best     | Ultimate quality |

### Test Configurations

We provide several test configurations:

#### 1. Basic Testing (`torah_lecture_basic.json`)
- Hebrew lecture
- 3 clips, 20-60 seconds
- Small model for balance

#### 2. English Quality (`english_shiur_quality.json`)
- English lecture
- 5 clips, 25-45 seconds
- Medium model for accuracy

#### 3. Ultimate Quality (`chassidish_ultimate_quality.json`)
- Hebrew chassidish content
- 10 clips, 30-90 seconds
- Large model for best results

#### 4. Fast Processing (`fast_processing.json`)
- Quick testing
- 2 clips, 15-30 seconds
- Tiny model for speed

## 🛠️ Deployment Process

### Step 1: Local Testing

```bash
# Test dependencies
python test_local.py

# Test handler function
python -c "
from handler import handler
import json

test_event = {
    'input': {
        'video_url': 'https://example.com/test.mp4',
        'language': 'en',
        'num_clips': 1,
        'model_size': 'tiny'
    }
}

result = handler(test_event)
print(json.dumps(result, indent=2))
"
```

### Step 2: Build Docker Image

```bash
# Build with progress output
docker build -t youtube-shorts-generator . --progress=plain

# Test locally
docker run --rm --gpus all -e OPENAI_API_KEY=$OPENAI_API_KEY youtube-shorts-generator python test_local.py
```

### Step 3: Push to Registry

```bash
# Login to Docker Hub
docker login

# Push image
docker push your-username/youtube-shorts-generator:latest
```

### Step 4: Create RunPod Template

1. **Template Configuration**:
   - Name: `youtube-shorts-generator`
   - Image: `your-username/youtube-shorts-generator:latest`
   - Start Command: Default

2. **Environment Variables**:
   ```
   OPENAI_API_KEY=your_key_here
   PYTHONUNBUFFERED=1
   CUDA_VISIBLE_DEVICES=0
   ```

3. **Resource Requirements**:
   - **Minimum**: RTX 4090, 16GB RAM, 50GB disk
   - **Recommended**: A6000, 32GB RAM, 100GB disk
   - **Ultimate**: A100, 64GB RAM, 200GB disk

### Step 5: Deploy Endpoint

1. Go to Endpoints → New Endpoint
2. Select your template
3. Configure:
   - **Min Workers**: 0 (for cost efficiency)
   - **Max Workers**: 5 (adjust based on usage)
   - **Idle Timeout**: 300 seconds
   - **Execution Timeout**: 600 seconds (for long videos)

### Step 6: Test Deployment

```powershell
# Basic test
.\runpod_test.ps1 -EndpointId "your-endpoint-id" -ConfigFile "payloads\fast_processing.json"

# Quality test
.\runpod_test.ps1 -EndpointId "your-endpoint-id" -ConfigFile "payloads\torah_lecture_basic.json"
```

## 📊 Performance Optimization

### Cold Start Optimization

Our Docker image pre-downloads models to minimize cold start time:
- WhisperX models: tiny, base, small, medium
- Alignment models: English and Hebrew
- Result: ~30 seconds faster startup

### GPU Memory Management

```python
# Automatic memory management in handler
import torch

# Clear cache between requests
torch.cuda.empty_cache()

# Monitor GPU memory
if torch.cuda.is_available():
    memory_used = torch.cuda.memory_allocated() / 1024**3
    print(f"GPU memory used: {memory_used:.2f} GB")
```

### Batch Processing

For multiple videos, use async endpoints:
```bash
# Submit multiple jobs
for config in payloads/*.json; do
    .\runpod_test.ps1 -EndpointId "your-endpoint-id" -ConfigFile "$config" -Async
done
```

## 🔐 Security Best Practices

### API Key Management

1. **Never commit API keys** to Git
2. **Use environment variables** in RunPod
3. **Rotate keys regularly**
4. **Monitor API usage**

### Network Security

```dockerfile
# Dockerfile includes minimal attack surface
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Only install required packages
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
```

### Error Handling

The handler includes comprehensive error handling:
- Input validation
- Graceful degradation
- Detailed error messages
- No sensitive data in logs

## 📈 Monitoring and Logging

### Tracking Performance

```python
# Built into handler
import time

start_time = time.time()
# ... processing ...
processing_time = time.time() - start_time

print(f"Processing completed in {processing_time:.2f} seconds")
```

### Cost Monitoring

- **GPU costs**: ~$0.50-2.00 per hour depending on GPU
- **Processing time**: 2-10 minutes per video depending on length/quality
- **Storage**: Minimal for processed outputs

### Usage Analytics

Monitor through RunPod dashboard:
- Request volume
- Processing times
- Error rates
- GPU utilization

## 🚨 Troubleshooting

### Common Issues

#### 1. Memory Errors
```
RuntimeError: CUDA out of memory
```
**Solution**: Use smaller model size or reduce batch processing

#### 2. Model Download Failures
```
Failed to download alignment model
```
**Solution**: Check internet connectivity, rebuild image

#### 3. FFmpeg Errors
```
FFmpeg command failed
```
**Solution**: Ensure video URL is accessible and format is supported

#### 4. OpenAI API Errors
```
Authentication failed
```
**Solution**: Verify API key is set correctly

### Debug Commands

```bash
# Check GPU availability
nvidia-smi

# Test WhisperX
python -c "import whisperx; print('WhisperX available')"

# Test OpenAI
python -c "import openai; print('OpenAI available')"

# Check disk space
df -h
```

## 📚 Additional Resources

- [RunPod Documentation](https://docs.runpod.io/)
- [WhisperX GitHub](https://github.com/m-bain/whisperX)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)

## 🎯 Next Steps

1. **Deploy to staging** environment first
2. **Test with real videos** from your corpus
3. **Monitor performance** and costs
4. **Scale up** based on usage patterns
5. **Implement CI/CD** for updates

## 📞 Support

For issues with this deployment:
1. Check the troubleshooting section
2. Review RunPod logs
3. Test locally first
4. Create detailed issue reports

---

*This deployment guide follows the proven methodology from the WhisperX project, ensuring reliable and scalable GPU processing for Torah lecture shorts generation.*