# YouTube Shorts Editor - Complete Usage Guide

## 🚀 **COMPLETE YOUTUBE SHORTS EDITOR - SETUP & USAGE GUIDE**

### **🔧 1. ENVIRONMENT SETUP**

**Required Prerequisites:**
```bash
# Required for all deployments
- Docker & Docker Compose
- OpenAI API Key
- NVIDIA GPU with Container Toolkit (for optimal performance)
```

**Configure Environment:**
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your API key
nano .env
```

**Essential .env Configuration:**
```bash
# REQUIRED - Get from OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Optional - defaults work fine
DATABASE_URL=postgresql://postgres:shorts_password@localhost:5432/shorts_editor
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO

# GPU Configuration (0 = first GPU)
CUDA_VISIBLE_DEVICES=0
```

---

### **💻 2. LOCAL DEVELOPMENT (Quick Start)**

**Start All Services (Full Stack):**
```bash
# Start all services with GPU support
docker-compose up -d

# Check service health
curl http://localhost:8000/health
curl http://localhost:3000  # Frontend

# View logs
docker-compose logs -f api worker
```

**Frontend Studio Interface:**
- **URL**: http://localhost:3000
- **Features**: Timeline editor, AI transparency, manual controls
- **API Docs**: http://localhost:8000/api/docs

**Quick Video Processing Test:**
```bash
# Test with sample video
curl -X POST "http://localhost:8000/api/v1/videos" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/lecture.mp4",
    "language": "en",
    "num_clips": 3,
    "vertical": true,
    "subtitles": true
  }'
```

---

### **⚙️ 3. PARAMETER CONFIGURATION**

You can customize processing through multiple methods:

#### **3.1 API Parameters (Recommended)**
```json
{
  "video_url": "https://example.com/video.mp4",
  "language": "he",          // "he" for Hebrew, "en" for English
  "num_clips": 5,           // Number of clips to generate (1-10)
  "min_duration": 20,       // Minimum clip length in seconds
  "max_duration": 60,       // Maximum clip length in seconds  
  "vertical": true,         // Convert to 9:16 format
  "subtitles": true,        // Generate SRT files
  "model_size": "large-v2"  // "tiny", "small", "medium", "large-v2"
}
```

#### **3.2 Configuration Files**
Pre-built configurations in `payloads/` directory:

- **Basic Hebrew**: `payloads/torah_lecture_basic.json`
- **Ultimate Quality**: `payloads/chassidish_ultimate_quality.json`  
- **Fast Processing**: `payloads/fast_processing.json`
- **English Lectures**: `payloads/english_shiur_quality.json`

#### **3.3 Command Line (Legacy)**
```bash
# Direct script usage
python main.py --url "https://youtube.com/watch?v=..." \
               --language he \
               --clips 3 \
               --vertical \
               --normalize
```

---

### **🎛️ 4. ADVANCED PARAMETERS**

#### **4.1 Quality Settings**
```json
{
  "render_quality": "high",     // "fast", "balanced", "high"
  "face_tracking": true,        // Enable MediaPipe face detection
  "reframing_interval": 1.0,    // Face detection sample rate
  "gpu_acceleration": true      // Use NVENC/NVDEC
}
```

#### **4.2 AI Analysis Tuning**
```json
{
  "audio_confidence": 0.4,      // Audio scoring weight (0-1)
  "visual_quality": 0.3,        // Visual scoring weight (0-1) 
  "semantic_score": 0.2,        // Content scoring weight (0-1)
  "engagement_proxy": 0.1,      // Engagement scoring weight (0-1)
  "quality_threshold": 8.0      // Minimum clip quality score
}
```

#### **4.3 GPU Resource Management**
```bash
# Environment variables for GPU control
CUDA_VISIBLE_DEVICES=0        # Which GPU to use
MAX_CONCURRENT_RENDERS=3      # Parallel render limit
GPU_MEMORY_FRACTION=0.8       # GPU memory allocation
```

---

### **🏭 5. PRODUCTION DEPLOYMENT**

#### **5.1 Full Production Stack**
```bash
# Use production configuration
docker-compose -f docker-compose.production.yml up -d

# Services included:
# - Core API (FastAPI)
# - GPU Workers (Celery) 
# - CPU Workers (Background tasks)
# - PostgreSQL Database
# - Redis Cache/Queue
# - Prometheus Monitoring
# - Grafana Dashboards
# - Nginx Load Balancer
```

#### **5.2 Monitoring Dashboard**
- **Grafana**: http://localhost:3001 (admin/password from .env)
- **Prometheus**: http://localhost:9090
- **GPU Metrics**: Real-time utilization, temperature, memory
- **Task Queue**: http://localhost:5555 (Flower - Celery monitoring)

#### **5.3 Auto-Scaling**
Production deployment includes intelligent auto-scaling:
- **Scale Up**: When queue > 10 jobs AND wait time > 5min
- **Scale Down**: When queue < 3 jobs AND sufficient idle capacity
- **GPU Health**: Prevents scaling if temp > 80°C or memory > 90%

---

### **☁️ 6. RUNPOD DEPLOYMENT (GPU Cloud) - UPGRADED SYSTEM**

#### **6.1 New RunPod Deployment (Phase 1-5 Complete)**
```bash
# 1. Create RunPod template with new Dockerfile
# Use: Dockerfile.runpod (NOT the legacy version)

# 2. RunPod Configuration:
Docker Image Path: Dockerfile.runpod
Container Start Command: /app/startup.sh
Expose HTTP Ports: 8000, 5555, 5432, 6379

# 3. Environment Variables:
OPENAI_API_KEY=your_openai_api_key_here
RUNPOD_SERVERLESS=true
CUDA_VISIBLE_DEVICES=all
```

#### **6.2 New API Endpoints Available**
```bash
# Health Check
curl https://YOUR_ENDPOINT-8000.proxy.runpod.net/health

# Process Video (New FastAPI)
curl -X POST "https://YOUR_ENDPOINT-8000.proxy.runpod.net/process" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "transcript_json": {...},
    "language": "he",
    "num_clips": 3,
    "vertical": true,
    "use_gpu_rendering": true
  }'

# Legacy Compatibility
curl -X POST "https://YOUR_ENDPOINT-8000.proxy.runpod.net/legacy/process" \
  -H "Content-Type: application/json" \
  -d @payloads/torah_lecture_basic.json

# System Metrics
curl https://YOUR_ENDPOINT-8000.proxy.runpod.net/metrics/system
```

#### **6.3 New RunPod Features Available**
- **✅ FastAPI REST API** (http://your-endpoint:8000/docs)
- **✅ PostgreSQL Database** (persistent project storage)
- **✅ Redis Cache & Queue** (high-performance processing)
- **✅ Celery Task Queue** (background processing)
- **✅ GPU Monitoring** (real-time metrics)
- **✅ Health Checks** (automatic service validation)
- **✅ Flower Dashboard** (http://your-endpoint:5555)
- **✅ Prometheus Metrics** (advanced monitoring)

#### **6.4 Recommended RunPod Specs (Upgraded)**
```yaml
# Enhanced for multi-service architecture:
GPU: RTX4090 or A100 (40GB+ VRAM recommended)
CPU: 32+ cores (for multi-service)
RAM: 128GB (PostgreSQL + Redis + Celery + FastAPI)
Storage: 1TB SSD (model storage + database)
Container Disk: 50GB (for services)
```

---

### **📊 7. MONITORING & PERFORMANCE**

#### **7.1 Performance Metrics**
- **Processing Speed**: 2-3x realtime on GPU
- **Concurrent Users**: Supports 10+ simultaneous requests
- **Auto-scaling**: 1-8 GPU workers based on demand
- **Uptime Target**: 99.9% availability

#### **7.2 Health Checks**
```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:8000/metrics  # Prometheus metrics

# Check GPU status
docker exec -it gpu-worker nvidia-smi

# Check queue status
curl http://localhost:5555/api/queues  # Flower API
```

---

### **🎯 8. QUICK START WORKFLOWS**

#### **8.1 Process Single Video (API)**
```python
import requests

# Submit video for processing
response = requests.post("http://localhost:8000/api/v1/videos", json={
    "video_url": "https://example.com/lecture.mp4",
    "language": "he",
    "num_clips": 3,
    "vertical": true
})

project_id = response.json()["id"]

# Check status
status = requests.get(f"http://localhost:8000/api/v1/videos/{project_id}")

# Get results when complete
clips = requests.get(f"http://localhost:8000/api/v1/videos/{project_id}/clips")
```

#### **8.2 Batch Processing**
```bash
# Process multiple videos
for config in payloads/*.json; do
    curl -X POST "http://localhost:8000/api/v1/videos" \
         -H "Content-Type: application/json" \
         -d @"$config"
done
```

#### **8.3 Manual Editing (Studio UI)**
1. Open http://localhost:3000
2. Upload video + transcript
3. Use timeline editor for manual adjustments
4. Export with platform presets (YouTube Shorts, TikTok, Instagram)

---

### **🔧 9. TROUBLESHOOTING**

#### **Common Issues:**
```bash
# GPU not detected
docker run --rm --gpus all nvidia/cuda:11.8-runtime-ubuntu20.04 nvidia-smi

# Services not starting
docker-compose logs api worker

# Memory issues
docker system prune -af

# API not responding
curl http://localhost:8000/health
```

#### **Performance Optimization:**
- Use SSD storage for video processing
- Allocate sufficient GPU memory (8GB+ recommended)
- Monitor GPU temperature (keep < 80°C)
- Use appropriate model size for your hardware

---

## **🎉 YOU'RE READY TO GO!**

The YouTube Shorts Editor is now fully operational with:
- ✅ **Complete 5-phase implementation**
- ✅ **Professional manual editing interface**
- ✅ **GPU-accelerated processing**
- ✅ **Auto-scaling production deployment**
- ✅ **Real-time monitoring and analytics**

Start with the local development setup and scale to production when ready!

---

## **📞 SUPPORT & RESOURCES**

### **Documentation Links**
- **API Documentation**: http://localhost:8000/api/docs (when running)
- **Frontend Guide**: Open http://localhost:3000 for interactive tutorial
- **Configuration Examples**: `payloads/` directory

### **Performance Tuning**
- **GPU Memory**: Monitor via Grafana dashboard
- **Queue Optimization**: Adjust worker replicas in docker-compose.production.yml
- **Quality vs Speed**: Use different model sizes ("tiny" = fast, "large-v2" = quality)

### **Deployment Options**
1. **Local Development**: `docker-compose up -d`
2. **Production**: `docker-compose -f docker-compose.production.yml up -d`
3. **RunPod Cloud**: Upload production config to RunPod platform
4. **Legacy Scripts**: `python main.py` for direct script usage

### **Scaling Guidelines**
- **Small Videos (<30min)**: 1-2 GPU workers sufficient
- **Large Videos (1-3 hours)**: 4-6 GPU workers recommended
- **High Volume**: Enable auto-scaling and monitor queue depth
- **Enterprise**: Use production stack with monitoring enabled