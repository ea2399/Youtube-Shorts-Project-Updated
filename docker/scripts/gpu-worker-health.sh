#!/bin/bash
# GPU Worker Health Check Script - Phase 5B

set -e

echo "=== GPU Worker Health Check ==="

# Check if GPU is accessible
echo "Checking GPU availability..."
python3 -c "
import pynvml
try:
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    name = pynvml.nvmlDeviceGetName(handle)
    print(f'GPU detected: {name}')
except Exception as e:
    print(f'GPU check failed: {e}')
    exit(1)
"

# Check FFmpeg with NVIDIA codec support
echo "Checking FFmpeg NVENC support..."
ffmpeg -hide_banner -encoders 2>/dev/null | grep nvenc > /dev/null || {
    echo "ERROR: FFmpeg NVENC encoder not available"
    exit 1
}

echo "FFmpeg NVENC support: OK"

# Check if Celery worker can connect to broker
echo "Checking Celery broker connection..."
timeout 10 python3 -c "
from celery import Celery
import os

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
app = Celery('health_check', broker=redis_url)

try:
    # Test broker connection
    inspect = app.control.inspect()
    inspect.ping()
    print('Celery broker connection: OK')
except Exception as e:
    print(f'Celery broker connection failed: {e}')
    exit(1)
" || {
    echo "ERROR: Celery broker connection failed"
    exit 1
}

# Check GPU memory usage
echo "Checking GPU memory..."
python3 -c "
import pynvml

pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)
mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

memory_used_mb = mem_info.used // 1024 // 1024
memory_total_mb = mem_info.total // 1024 // 1024
memory_free_mb = mem_info.free // 1024 // 1024
memory_usage_pct = (memory_used_mb / memory_total_mb) * 100

print(f'GPU Memory: {memory_used_mb}MB / {memory_total_mb}MB ({memory_usage_pct:.1f}%)')

# Alert if GPU memory usage is too high
if memory_usage_pct > 90:
    print('WARNING: GPU memory usage is very high')
    exit(1)

if memory_free_mb < 1024:  # Less than 1GB free
    print('WARNING: Low GPU memory available')
    exit(1)
"

# Check system memory
echo "Checking system memory..."
python3 -c "
import psutil

memory = psutil.virtual_memory()
memory_usage_pct = memory.percent

print(f'System Memory: {memory_usage_pct:.1f}% used')

if memory_usage_pct > 90:
    print('WARNING: System memory usage is very high')
    exit(1)
"

# Check disk space
echo "Checking disk space..."
df -h /app/storage 2>/dev/null || df -h /tmp | tail -1 | awk '{
    usage = $5
    gsub(/%/, "", usage)
    if (usage > 85) {
        print "WARNING: Disk usage is high: " usage "%"
        exit 1
    }
    print "Disk usage: " usage "%"
}'

# Test basic MediaPipe functionality if available
echo "Testing MediaPipe..."
python3 -c "
try:
    import mediapipe as mp
    print('MediaPipe: OK')
except ImportError:
    print('MediaPipe: Not available (optional)')
except Exception as e:
    print(f'MediaPipe: Error - {e}')
" || true

echo "=== Health Check Complete ==="
echo "GPU Worker is healthy ✓"