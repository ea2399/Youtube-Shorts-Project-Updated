#!/bin/bash

# YouTube Shorts Editor - Health Check Script
# Validates all services are running properly

set -e

echo "=== YouTube Shorts Editor Health Check ==="

# Function to check if service is responding
check_service() {
    local service_name=$1
    local check_command=$2
    local expected_output=$3
    
    echo -n "Checking $service_name... "
    
    if eval "$check_command" &>/dev/null; then
        echo "✓ OK"
        return 0
    else
        echo "✗ FAILED"
        return 1
    fi
}

# Function to check HTTP endpoint
check_http() {
    local service_name=$1
    local url=$2
    local expected_status=$3
    
    echo -n "Checking $service_name HTTP... "
    
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    
    if [ "$status_code" = "$expected_status" ]; then
        echo "✓ OK ($status_code)"
        return 0
    else
        echo "✗ FAILED ($status_code, expected $expected_status)"
        return 1
    fi
}

# Track overall health
overall_health=0

# Check PostgreSQL
if check_service "PostgreSQL" "pg_isready -h localhost -p 5432"; then
    if check_service "PostgreSQL Connection" "psql -h localhost -U runpod -d shorts_editor -c 'SELECT 1;'"; then
        echo "  ✓ PostgreSQL fully operational"
    else
        echo "  ⚠ PostgreSQL running but database connection failed"
        overall_health=1
    fi
else
    echo "  ✗ PostgreSQL not responding"
    overall_health=1
fi

# Check Redis
if check_service "Redis" "redis-cli -h localhost -p 6379 ping"; then
    echo "  ✓ Redis operational"
else
    echo "  ✗ Redis not responding"
    overall_health=1
fi

# Check FastAPI
if check_http "FastAPI" "http://localhost:8000/health" "200"; then
    echo "  ✓ FastAPI operational"
else
    echo "  ✗ FastAPI not responding"
    overall_health=1
fi

# Check Celery Worker
if check_service "Celery Worker" "celery -A core.tasks.celery_app inspect ping"; then
    echo "  ✓ Celery Worker operational"
else
    echo "  ✗ Celery Worker not responding"
    overall_health=1
fi

# Check Celery Flower (monitoring)
if check_http "Celery Flower" "http://localhost:5555" "200"; then
    echo "  ✓ Celery Flower operational"
else
    echo "  ⚠ Celery Flower not responding (non-critical)"
fi

# Check GPU availability
echo -n "Checking GPU availability... "
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &>/dev/null; then
        gpu_count=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits | head -1)
        echo "✓ OK ($gpu_count GPU(s) detected)"
    else
        echo "⚠ nvidia-smi failed"
        overall_health=1
    fi
else
    echo "⚠ nvidia-smi not available"
fi

# Check disk space
echo -n "Checking disk space... "
disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 90 ]; then
    echo "✓ OK (${disk_usage}% used)"
else
    echo "⚠ WARNING (${disk_usage}% used)"
    overall_health=1
fi

# Check memory usage
echo -n "Checking memory usage... "
memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$memory_usage" -lt 90 ]; then
    echo "✓ OK (${memory_usage}% used)"
else
    echo "⚠ WARNING (${memory_usage}% used)"
fi

# Final health status
echo "=================================="
if [ $overall_health -eq 0 ]; then
    echo "✓ Overall Health: HEALTHY"
    echo "All critical services operational"
    exit 0
else
    echo "✗ Overall Health: UNHEALTHY"
    echo "One or more critical services failed"
    exit 1
fi