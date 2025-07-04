# 🧪 Testing Your RunPod YouTube Shorts Generator

Your RunPod build completed! Here's how to test the output:

## 🎯 Quick Test (Recommended)

### Step 1: Get Your RunPod Endpoint
1. Go to your RunPod dashboard
2. Find your deployed endpoint
3. Copy the endpoint URL (format: `https://abc123.runpod.ai`)

### Step 2: Run Simple Test
```bash
python test_sample_data.py
```
- Uses your existing test payloads from `payloads/` directory
- Tests health check + shorts generation
- No external video URLs needed

## 🔧 Advanced Testing

### Full Test Suite
```bash
python test_runpod_output.py
```
- Comprehensive Phase 1-5 testing
- Tests all API endpoints
- Requires manual endpoint configuration

### Manual API Testing

#### 1. Health Check
```bash
curl https://YOUR-ENDPOINT.runpod.ai/health
```
**Expected**: `{"status": "healthy", "services": {...}}`

#### 2. System Metrics
```bash
curl https://YOUR-ENDPOINT.runpod.ai/metrics/system
```
**Expected**: GPU info, memory usage, service status

#### 3. Generate Shorts (Legacy Endpoint)
```bash
curl -X POST https://YOUR-ENDPOINT.runpod.ai/legacy/process \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "YOUR_VIDEO_URL",
    "num_clips": 3,
    "language": "he",
    "vertical": true,
    "subtitles": true
  }'
```

## 📊 What to Expect

### ✅ Success Indicators:
- Health check returns status "healthy"
- System metrics show GPU information
- Processing returns clips array with:
  - `duration`, `source_start`, `source_end`
  - `reasoning` with AI confidence scores
  - `quality_metrics` with overall scores

### 📹 Output Structure:
```json
{
  "clips": [
    {
      "id": "clip_001",
      "duration": 45.2,
      "source_start": 120.5,
      "source_end": 165.7,
      "reasoning": {
        "audio_confidence": 0.92,
        "visual_quality": 0.88,
        "explanation": "High engagement segment with..."
      }
    }
  ],
  "quality_metrics": {
    "overall_score": 8.7,
    "cut_smoothness": 0.94,
    "visual_continuity": 0.89
  },
  "metadata": {
    "duration": 1800.5,
    "language": "mixed",
    "processing_time": 45.2
  }
}
```

## 🚨 Troubleshooting

### If Health Check Fails:
- Wait 2-3 minutes after deployment (services need time to start)
- Check RunPod logs for startup errors
- Verify all services (PostgreSQL, Redis, Celery) are running

### If Processing Fails:
- Check if video URL is accessible
- Verify the request format matches examples
- Look for timeout errors (processing can take 5-10 minutes)

### Common Issues:
1. **Service Unavailable**: Container still starting up
2. **Timeout**: Large videos need more processing time
3. **Memory Error**: Video too large for current instance
4. **GPU Error**: CUDA/MediaPipe initialization issue

## 🎉 Success Criteria

Your Phase 1-5 implementation is working if:
- ✅ Health check passes
- ✅ System metrics show GPU availability
- ✅ Processing completes without errors
- ✅ Returns valid clips with quality metrics
- ✅ All 5 phases operational (API, Intelligence, EDL, Manual Interface Backend, Production)

## 🚀 Next Steps After Testing

1. **If successful**: You have a fully operational YouTube Shorts Editor!
2. **Upload test videos**: Try with different content types
3. **Frontend integration**: Connect the studio-ui frontend
4. **Production deployment**: Scale up for real usage

Your legacy single-file handler has been successfully upgraded to a modern Phase 1-5 architecture! 🎯