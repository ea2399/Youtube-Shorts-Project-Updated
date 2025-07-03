#!/bin/bash
# RunPod Startup Script - Phase 5B
# Initialize and start the YouTube Shorts Editor production environment

set -e

echo "=== YouTube Shorts Editor - Production Startup ==="
echo "Starting services on RunPod..."

# Set up working directory
cd /workspace

# Check GPU availability
echo "Checking GPU availability..."
nvidia-smi || {
    echo "ERROR: No NVIDIA GPU detected"
    exit 1
}

# Check CUDA version
echo "CUDA Version:"
nvcc --version || echo "NVCC not available (using runtime only)"

# Set environment variables
export PYTHONPATH=/workspace
export NVIDIA_VISIBLE_DEVICES=all
export NVIDIA_DRIVER_CAPABILITIES=compute,video,utility

# Create necessary directories
mkdir -p storage/videos
mkdir -p storage/rendered  
mkdir -p storage/cache
mkdir -p models/mediapipe
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p logs

# Set permissions
chmod -R 755 storage/
chmod -R 755 models/
chmod -R 755 data/
chmod -R 755 logs/

# Download MediaPipe models if not present
echo "Checking MediaPipe models..."
if [ ! -f models/mediapipe/face_detector.tflite ]; then
    echo "Downloading MediaPipe face detector model..."
    # TODO: Add actual model download URLs
    # wget -O models/mediapipe/face_detector.tflite [URL]
    echo "Model download placeholder - update with actual URLs"
fi

if [ ! -f models/mediapipe/face_landmarker.task ]; then
    echo "Downloading MediaPipe face landmarker model..."
    # TODO: Add actual model download URLs  
    # wget -O models/mediapipe/face_landmarker.task [URL]
    echo "Model download placeholder - update with actual URLs"
fi

# Generate default passwords if not provided
if [ -z "$POSTGRES_PASSWORD" ]; then
    export POSTGRES_PASSWORD=$(openssl rand -base64 32)
    echo "Generated PostgreSQL password"
fi

if [ -z "$GRAFANA_PASSWORD" ]; then
    export GRAFANA_PASSWORD=$(openssl rand -base64 16)
    echo "Generated Grafana password: $GRAFANA_PASSWORD"
fi

if [ -z "$FLOWER_PASSWORD" ]; then
    export FLOWER_PASSWORD=$(openssl rand -base64 16)
    echo "Generated Flower password: $FLOWER_PASSWORD"
fi

# Start Docker Compose services
echo "Starting production services..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Check service health
echo "Checking service health..."

# Check database
echo "Checking PostgreSQL..."
docker-compose -f docker-compose.production.yml exec -T postgres pg_isready -U postgres || {
    echo "PostgreSQL not ready, waiting..."
    sleep 15
}

# Check Redis
echo "Checking Redis..."
docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping || {
    echo "Redis not ready, waiting..."
    sleep 10
}

# Check API
echo "Checking Core API..."
timeout 30 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done' || {
    echo "WARNING: Core API health check failed"
}

# Check GPU workers
echo "Checking GPU workers..."
docker-compose -f docker-compose.production.yml exec -T gpu-worker /app/health-check.sh || {
    echo "WARNING: GPU worker health check failed"
}

# Display service URLs
echo ""
echo "=== Service URLs ==="
echo "Core API: http://localhost:8000"
echo "Studio UI: http://localhost:3000"
echo "Flower (Celery): http://localhost:5555"
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3001"
echo ""

# Display credentials
echo "=== Credentials ==="
echo "Grafana: admin / $GRAFANA_PASSWORD"
echo "Flower: $FLOWER_USER / $FLOWER_PASSWORD"
echo ""

# Display GPU information
echo "=== GPU Information ==="
nvidia-smi --query-gpu=name,memory.total,utilization.gpu --format=csv,noheader,nounits

# Show running services
echo ""
echo "=== Running Services ==="
docker-compose -f docker-compose.production.yml ps

# Monitor logs
echo ""
echo "=== Starting log monitoring ==="
echo "Use 'docker-compose -f docker-compose.production.yml logs -f [service]' to view logs"

# Keep container running and show logs
echo "Production environment started successfully!"
echo "Tailing core API logs..."
docker-compose -f docker-compose.production.yml logs -f core-api