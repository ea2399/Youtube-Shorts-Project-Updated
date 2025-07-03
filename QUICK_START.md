# YouTube Shorts Generator - Quick Start Guide

Get your Torah lecture shorts generator running on RunPod in 10 minutes!

## 🎯 Prerequisites (2 minutes)

1. **RunPod Account**: Sign up at [runpod.io](https://runpod.io)
2. **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com)
3. **Docker Hub Account**: Sign up at [hub.docker.com](https://hub.docker.com)

## 🚀 Deploy to RunPod (8 minutes)

### Step 1: Build Docker Image (3 minutes)

```bash
# Clone and navigate to project
cd "YouTube short project"

# Build image
docker build -t your-username/youtube-shorts-generator .

# Push to Docker Hub
docker login
docker push your-username/youtube-shorts-generator:latest
```

### Step 2: Create RunPod Template (2 minutes)

1. Go to [RunPod Console](https://www.runpod.io/console) → Templates
2. Click **"New Template"**
3. Fill in:
   - **Name**: `youtube-shorts-generator`
   - **Image**: `your-username/youtube-shorts-generator:latest`
   - **Environment Variables**:
     ```
     OPENAI_API_KEY=your_openai_key_here
     ```

### Step 3: Deploy Endpoint (1 minute)

1. Go to **Endpoints** → **"New Endpoint"**
2. Select your template
3. Choose GPU: **RTX 4090** or better
4. Set **Container Disk**: **50GB+**
5. Click **"Deploy"**

### Step 4: Test Your Deployment (2 minutes)

```powershell
# Get your endpoint ID from RunPod dashboard
$endpointId = "your-endpoint-id-here"

# Test with provided script
.\runpod_test.ps1 -EndpointId $endpointId -ConfigFile "payloads\torah_lecture_basic.json"
```

## 📱 Usage Examples

### Basic Torah Lecture
```json
{
  "input": {
    "video_url": "https://your-video-url.com/lecture.mp4",
    "language": "he",
    "num_clips": 3,
    "min_duration": 20,
    "max_duration": 60,
    "vertical": true,
    "subtitles": true,
    "model_size": "small"
  }
}
```

### English Shiur
```json
{
  "input": {
    "video_url": "https://your-video-url.com/shiur.mp4",
    "language": "en",
    "num_clips": 5,
    "model_size": "medium"
  }
}
```

## 🎬 What You Get

For each video, the system generates:

✅ **Intelligent Segmentation** using pause-based natural boundaries  
✅ **Context-Aware Analysis** with GPT for standalone quality  
✅ **Multiple Formats**: Horizontal + Vertical versions  
✅ **Subtitle Files** for accessibility  
✅ **Quality Scoring** with reasoning for each clip  

## 💰 Cost Estimate

- **GPU Usage**: ~$1-3 per video (5-15 minutes processing)
- **OpenAI API**: ~$0.10-0.50 per video (depends on length)
- **Total**: ~$1.50-4.00 per lecture processed

## 🛠️ Troubleshooting

### Common Issues

**"Handler not found"** → Check Docker image build and push  
**"OpenAI authentication failed"** → Verify API key in environment  
**"CUDA out of memory"** → Use smaller model size or better GPU  
**"Video download failed"** → Check video URL accessibility  

### Getting Help

1. Check [RUNPOD_DEPLOYMENT.md](./RUNPOD_DEPLOYMENT.md) for detailed guide
2. Run local tests with `python test_local.py`
3. Review RunPod logs in dashboard

## 🎯 Next Steps

1. **Test with your content** using real video URLs
2. **Adjust parameters** based on your quality needs
3. **Scale up** by increasing max workers
4. **Monitor costs** through RunPod dashboard

## 📊 Recommended Settings by Use Case

### Development/Testing
- **Model**: `tiny` or `small`
- **GPU**: RTX 4090
- **Clips**: 2-3
- **Cost**: ~$1-2 per video

### Production Quality
- **Model**: `medium`
- **GPU**: A6000
- **Clips**: 3-5
- **Cost**: ~$2-3 per video

### Ultimate Quality
- **Model**: `large-v2`
- **GPU**: A100
- **Clips**: 5-10
- **Cost**: ~$3-5 per video

---

🎉 **You're ready to generate amazing Torah shorts with AI!**

For advanced configuration and troubleshooting, see the full [deployment guide](./RUNPOD_DEPLOYMENT.md).