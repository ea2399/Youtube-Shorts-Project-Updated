#!/bin/bash
set -e

# YouTube Shorts Editor - Complete Service Startup Script
# Initializes PostgreSQL, Redis, and all Phase 1-5 services

echo "=========================================="
echo "YouTube Shorts Editor - Phase 1-5 Startup"
echo "=========================================="

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" &>/dev/null; then
            echo "✓ $service_name is ready!"
            return 0
        fi
        
        echo "  Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    echo "✗ $service_name failed to start within timeout"
    return 1
}

# Function to download MediaPipe models
download_mediapipe_models() {
    echo "Downloading MediaPipe models..."
    
    mkdir -p /models/mediapipe
    
    # Face Detection model
    if [ ! -f "/models/mediapipe/face_detector.tflite" ]; then
        echo "Downloading Face Detector model..."
        wget -O /models/mediapipe/face_detector.tflite \
            "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite" || \
        echo "Warning: Could not download face detector model"
    fi
    
    # Face Landmarker model
    if [ ! -f "/models/mediapipe/face_landmarker.task" ]; then
        echo "Downloading Face Landmarker model..."
        wget -O /models/mediapipe/face_landmarker.task \
            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" || \
        echo "Warning: Could not download face landmarker model"
    fi
    
    echo "✓ MediaPipe models setup complete"
}

# Function to initialize PostgreSQL
init_postgresql() {
    echo "Initializing PostgreSQL..."
    
    # Ensure PostgreSQL data directory exists and has correct permissions
    mkdir -p /var/lib/postgresql/14/main
    chown -R postgres:postgres /var/lib/postgresql/14/main
    chmod 700 /var/lib/postgresql/14/main
    
    # Initialize database if not already done
    if [ ! -f "/var/lib/postgresql/14/main/PG_VERSION" ]; then
        echo "Creating new PostgreSQL database..."
        su - postgres -c "/usr/lib/postgresql/14/bin/initdb -D /var/lib/postgresql/14/main --locale=C.UTF-8 --encoding=UTF8"
    fi
    
    # Ensure PostgreSQL configuration is in place
    cp /etc/postgresql/14/main/postgresql.conf /var/lib/postgresql/14/main/postgresql.conf || true
    
    # Create pg_hba.conf for local connections
    cat > /var/lib/postgresql/14/main/pg_hba.conf << EOF
# Local connections
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
# Allow connections from container
host    all             all             0.0.0.0/0               md5
EOF
    
    chown postgres:postgres /var/lib/postgresql/14/main/pg_hba.conf
    
    echo "✓ PostgreSQL initialization complete"
}

# Function to setup database and user
setup_database() {
    echo "Setting up database and user..."
    
    # Start PostgreSQL temporarily to create database and user
    su - postgres -c "/usr/lib/postgresql/14/bin/pg_ctl -D /var/lib/postgresql/14/main -l /tmp/postgres.log start"
    
    # Wait for PostgreSQL to be ready
    wait_for_service "PostgreSQL" "su - postgres -c 'psql -c \"SELECT 1\"'"
    
    # Create database and user
    su - postgres -c "psql" << EOF
CREATE USER runpod WITH PASSWORD 'runpod_secure_pass';
CREATE DATABASE shorts_editor OWNER runpod;
GRANT ALL PRIVILEGES ON DATABASE shorts_editor TO runpod;
ALTER USER runpod CREATEDB;
\q
EOF
    
    # Stop PostgreSQL (supervisord will restart it)
    su - postgres -c "/usr/lib/postgresql/14/bin/pg_ctl -D /var/lib/postgresql/14/main stop"
    
    echo "✓ Database setup complete"
}

# Function to setup Redis
setup_redis() {
    echo "Setting up Redis..."
    
    # Create Redis user and directories
    useradd -r -s /bin/false redis 2>/dev/null || true
    mkdir -p /var/lib/redis /var/log/redis
    chown redis:redis /var/lib/redis /var/log/redis
    
    echo "✓ Redis setup complete"
}

# Function to setup application directories
setup_app_directories() {
    echo "Setting up application directories..."
    
    mkdir -p /app/storage/uploads
    mkdir -p /app/storage/clips
    mkdir -p /app/storage/vertical
    mkdir -p /app/storage/cache
    mkdir -p /app/logs
    mkdir -p /tmp/runpod
    
    # Set permissions
    chmod 755 /app/storage
    chmod 755 /app/logs
    chmod 755 /tmp/runpod
    
    echo "✓ Application directories setup complete"
}

# Function to validate environment
validate_environment() {
    echo "Validating environment..."
    
    # Check CUDA
    if command -v nvidia-smi &> /dev/null; then
        echo "✓ NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1
    else
        echo "⚠ Warning: NVIDIA GPU not detected"
    fi
    
    # Check FFmpeg NVENC support
    if ffmpeg -encoders 2>/dev/null | grep -q "h264_nvenc\|hevc_nvenc"; then
        echo "✓ FFmpeg NVENC support detected"
    else
        echo "⚠ Warning: FFmpeg NVENC support not detected"
    fi
    
    # Check Python dependencies
    echo "✓ Validating Python dependencies..."
    python -c "
import fastapi, celery, redis, psycopg2, torch, cv2, openai
import mediapipe as mp
print('✓ All core dependencies imported successfully')
" || {
        echo "✗ Python dependency validation failed"
        exit 1
    }
    
    echo "✓ Environment validation complete"
}

# Main startup sequence
main() {
    echo "Starting YouTube Shorts Editor initialization..."
    
    # Phase 1: Environment validation
    validate_environment
    
    # Phase 2: Download models
    download_mediapipe_models
    
    # Phase 3: Service setup
    setup_app_directories
    init_postgresql
    setup_database
    setup_redis
    
    echo "=========================================="
    echo "✓ Initialization complete!"
    echo "Starting supervisord to manage all services..."
    echo "=========================================="
    
    # Start supervisord with all services
    exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
}

# Handle signals for graceful shutdown
trap 'echo "Received shutdown signal, stopping services..."; killall supervisord; exit 0' SIGTERM SIGINT

# Run main startup sequence
main "$@"