# 🧪 RunPod Serverless Testing Commands

## 🎯 Quick Test (Recommended)

```cmd
python test_runpod_serverless.py
```

## 🔑 Get Your RunPod API Key
1. Go to: https://runpod.ai/console/user/settings
2. Copy your API key from the "API Keys" section
3. Use it in the test script above

## 🌐 Manual Testing with curl

### Test 1: Basic Endpoint Check
```bash
curl -X POST https://api.runpod.ai/v2/nmj1bq1l8kvikn/run \
  -H "Content-Type: application/json" \
  -d '{"input": {"test": true}}'
```
**Expected**: 401 error (means endpoint exists but needs auth)

### Test 2: With Authentication
```bash
curl -X POST https://api.runpod.ai/v2/nmj1bq1l8kvikn/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -d '{
    "input": {
      "video_url": "https://example.com/test.mp4",
      "num_clips": 3,
      "language": "he",
      "vertical": true,
      "subtitles": true
    }
  }'
```

### Test 3: Job Status Check
If you get a job ID from the above request:
```bash
curl -X GET https://api.runpod.ai/v2/nmj1bq1l8kvikn/status/JOB_ID_HERE \
  -H "Authorization: Bearer YOUR_API_KEY_HERE"
```

## 🎯 PowerShell Version (Windows)

### Test with PowerShell:
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer YOUR_API_KEY_HERE"
}

$body = @{
    input = @{
        video_url = "https://example.com/test.mp4"
        num_clips = 3
        language = "he"
        vertical = $true
        subtitles = $true
    }
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://api.runpod.ai/v2/nmj1bq1l8kvikn/run" -Method POST -Headers $headers -Body $body
```

## 📊 Expected Responses

### Success Response:
```json
{
  "id": "job-abc123",
  "status": "IN_QUEUE"
}
```

### Completed Job:
```json
{
  "id": "job-abc123", 
  "status": "COMPLETED",
  "output": {
    "clips": [...],
    "quality_metrics": {...},
    "metadata": {...}
  }
}
```

### Error Response:
```json
{
  "error": "Authentication required",
  "message": "Missing or invalid API key"
}
```

## 🚨 Troubleshooting

### 401 Unauthorized:
- ✅ **Good news**: Endpoint exists and is working
- 🔑 **Solution**: Add your RunPod API key

### 404 Not Found:
- ❌ **Issue**: Endpoint ID might be wrong
- 🔧 **Solution**: Check RunPod dashboard for correct ID

### 500 Internal Server Error:
- ⚠️ **Issue**: Your application has an error
- 📋 **Solution**: Check RunPod logs for details

### Timeout:
- ⏳ **Normal**: Video processing takes time (5-10 minutes)
- 🔄 **Solution**: Use job polling to check status

## 🎉 Success Indicators

Your YouTube Shorts Generator is working if you get:
- ✅ Job ID returned from `/run` endpoint
- ✅ Status progresses: `IN_QUEUE` → `IN_PROGRESS` → `COMPLETED` 
- ✅ Output contains `clips` array with video segments
- ✅ Quality metrics and metadata included

**You've successfully upgraded from legacy to Phase 1-5 architecture!** 🚀