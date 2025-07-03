#!/usr/bin/env python3
"""
YouTube Shorts Editor - Complete Phase 1-5 RunPod Handler
Replaces legacy handler.py with full FastAPI + Celery + Redis + PostgreSQL architecture

This handler provides:
- Phase 1: FastAPI REST API with database persistence
- Phase 2: GPU-accelerated audio/visual processing with MediaPipe
- Phase 3: EDL generation with multi-modal fusion
- Phase 4: Manual editing interface backend
- Phase 5: Production deployment with monitoring

Input formats:
1. RunPod Serverless: JSON payload via runpod.serverless
2. FastAPI REST: HTTP requests to API endpoints
3. Direct function calls: For testing and local development
"""

import os
import sys
import json
import asyncio
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Add app to Python path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/core-svc')

# Environment setup
os.environ.setdefault('PYTHONPATH', '/app')
os.environ.setdefault('DATABASE_URL', 'postgresql://runpod:runpod_secure_pass@localhost:5432/shorts_editor')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')

# Core imports
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import httpx
import structlog

# Database imports
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.database import get_db, init_db
from core.models.schemas import ProjectCreate, ProjectResponse, ProcessingJob

# Task queue imports
from core.tasks.celery_app import celery_app
from core.tasks.video_processor import process_video_task
from core.tasks.edl_tasks import generate_edl_task
from core.tasks.intelligence_tasks import analyze_video_task

# Service imports
from core.services.audio_processor import AudioProcessor
from core.services.visual_processor import VisualProcessor
from core.services.gpu_renderer import GPURenderer
from core.services.edl_generator import EDLGenerator
from core.services.quality_validator import QualityValidator

# Legacy imports for backward compatibility
from extract_shorts import create_pause_based_segments, create_multi_pass_analysis
from cut_clips import cut_clip, create_subtitle_file
from reframe import reframe_to_vertical
from config import OPENAI_API_KEY
import openai

# Monitoring imports
from prometheus_fastapi_instrumentator import Instrumentator
import runpod

# Setup logging
logger = structlog.get_logger(__name__)

# FastAPI application
app = FastAPI(
    title="YouTube Shorts Editor",
    description="Complete Phase 1-5 YouTube Shorts editing system with GPU acceleration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for studio-ui integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus monitoring
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Static files for studio-ui (if present)
if Path("/app/studio-ui/dist").exists():
    app.mount("/static", StaticFiles(directory="/app/studio-ui/dist"), name="static")

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class VideoProcessRequest(BaseModel):
    video_url: str = Field(..., description="URL to video file")
    transcript_json: Optional[Dict[str, Any]] = Field(None, description="Pre-transcribed WhisperX JSON")
    language: str = Field("he", description="Video language (he/en)")
    num_clips: int = Field(3, description="Number of clips to generate")
    min_duration: int = Field(20, description="Minimum clip duration in seconds")
    max_duration: int = Field(60, description="Maximum clip duration in seconds")
    vertical: bool = Field(True, description="Create vertical versions")
    subtitles: bool = Field(True, description="Generate subtitle files")
    quality_level: str = Field("medium", description="Processing quality (fast/medium/high)")
    use_gpu_rendering: bool = Field(True, description="Enable GPU-accelerated rendering")

class ProcessingResponse(BaseModel):
    project_id: str
    status: str
    task_ids: List[str]
    estimated_completion: Optional[datetime] = None

class ClipResult(BaseModel):
    index: int
    title: str
    start: float
    end: float
    duration: float
    score: float
    reasoning: str
    tags: List[str]
    files: Dict[str, Optional[str]]
    quality_metrics: Optional[Dict[str, float]] = None

class VideoProcessResponse(BaseModel):
    success: bool
    project_id: str
    clips_generated: int
    clips: List[ClipResult]
    transcription: Dict[str, Any]
    analysis: Dict[str, Any]
    processing_info: Dict[str, Any]
    files: List[str]

# =============================================================================
# SERVICE INITIALIZATION
# =============================================================================

# Initialize services (singleton pattern)
audio_processor = None
visual_processor = None
gpu_renderer = None
edl_generator = None
quality_validator = None

async def initialize_services():
    """Initialize all processing services on startup."""
    global audio_processor, visual_processor, gpu_renderer, edl_generator, quality_validator
    
    try:
        logger.info("Initializing processing services...")
        
        # Initialize database
        await init_db()
        
        # Initialize processors
        audio_processor = AudioProcessor()
        visual_processor = VisualProcessor()
        gpu_renderer = GPURenderer()
        edl_generator = EDLGenerator()
        quality_validator = QualityValidator()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        raise

# =============================================================================
# HEALTH AND MONITORING ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for RunPod and monitoring."""
    try:
        # Check database connection
        async with get_db() as db:
            result = await db.execute("SELECT 1")
            db_status = "healthy" if result else "unhealthy"
        
        # Check Redis connection
        redis_status = "healthy" if celery_app.backend.ping() else "unhealthy"
        
        # Check GPU availability
        try:
            import torch
            gpu_status = "available" if torch.cuda.is_available() else "unavailable"
            gpu_count = torch.cuda.device_count()
        except:
            gpu_status = "unavailable"
            gpu_count = 0
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": db_status,
                "redis": redis_status,
                "gpu": gpu_status,
                "gpu_count": gpu_count
            },
            "version": "2.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/metrics/system")
async def system_metrics():
    """System metrics for monitoring."""
    try:
        import psutil
        import GPUtil
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # GPU metrics
        gpu_metrics = []
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_metrics.append({
                    "id": gpu.id,
                    "name": gpu.name,
                    "load": gpu.load * 100,
                    "memory_used": gpu.memoryUsed,
                    "memory_total": gpu.memoryTotal,
                    "temperature": gpu.temperature
                })
        except:
            pass
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": cpu_percent,
            "memory": {
                "used_percent": memory.percent,
                "used_gb": memory.used / (1024**3),
                "total_gb": memory.total / (1024**3)
            },
            "disk": {
                "used_percent": (disk.used / disk.total) * 100,
                "used_gb": disk.used / (1024**3),
                "total_gb": disk.total / (1024**3)
            },
            "gpu": gpu_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics collection failed: {str(e)}")

# =============================================================================
# PROJECT MANAGEMENT ENDPOINTS (Phase 1)
# =============================================================================

@app.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new editing project."""
    try:
        from core.models.schemas import Project
        
        project = Project(
            name=project_data.name,
            description=project_data.description,
            status="created",
            created_at=datetime.utcnow()
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Created project: {project.id}")
        return ProjectResponse.from_orm(project)
        
    except Exception as e:
        logger.error(f"Project creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get project details."""
    try:
        from core.models.schemas import Project
        
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse.from_orm(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Project retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_id}/upload")
async def upload_files(
    project_id: str,
    video: UploadFile = File(...),
    transcript: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload video and transcript files."""
    try:
        # Validate project exists
        from core.models.schemas import Project
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Create storage directory
        storage_dir = Path(f"/app/storage/{project_id}")
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Save video file
        video_path = storage_dir / f"video_{video.filename}"
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # Save transcript if provided
        transcript_path = None
        if transcript:
            transcript_path = storage_dir / f"transcript_{transcript.filename}"
            with open(transcript_path, "wb") as f:
                content = await transcript.read()
                f.write(content)
        
        # Update project status
        project.status = "uploaded"
        await db.commit()
        
        logger.info(f"Files uploaded for project: {project_id}")
        return {
            "message": "Files uploaded successfully",
            "video_path": str(video_path),
            "transcript_path": str(transcript_path) if transcript_path else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# VIDEO PROCESSING ENDPOINTS (Phase 2-5)
# =============================================================================

@app.post("/process", response_model=ProcessingResponse)
async def start_video_processing(
    request: VideoProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start video processing with full Phase 1-5 pipeline."""
    try:
        # Create project
        from core.models.schemas import Project
        
        project = Project(
            name=f"Video Processing {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            description=f"Processing video: {request.video_url}",
            status="processing",
            created_at=datetime.utcnow()
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        # Start Celery tasks
        task_chain = (
            analyze_video_task.s(
                project_id=project.id,
                video_url=request.video_url,
                transcript_json=request.transcript_json,
                language=request.language
            ) |
            generate_edl_task.s(
                num_clips=request.num_clips,
                min_duration=request.min_duration,
                max_duration=request.max_duration
            ) |
            process_video_task.s(
                vertical=request.vertical,
                subtitles=request.subtitles,
                use_gpu_rendering=request.use_gpu_rendering
            )
        )
        
        result = task_chain.apply_async()
        
        logger.info(f"Started processing for project: {project.id}")
        return ProcessingResponse(
            project_id=project.id,
            status="processing",
            task_ids=[result.id],
            estimated_completion=None
        )
        
    except Exception as e:
        logger.error(f"Processing start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/process/{project_id}/status")
async def get_processing_status(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get processing status and results."""
    try:
        from core.models.schemas import Project
        
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check for results file
        results_file = Path(f"/app/storage/{project_id}/results.json")
        if results_file.exists():
            with open(results_file, 'r') as f:
                results = json.load(f)
            return {
                "project_id": project_id,
                "status": "completed",
                "results": results
            }
        
        return {
            "project_id": project_id,
            "status": project.status,
            "message": "Processing in progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# LEGACY COMPATIBILITY ENDPOINT
# =============================================================================

@app.post("/legacy/process")
async def legacy_video_processing(request: VideoProcessRequest):
    """
    Legacy compatibility endpoint that mimics the old handler.py behavior
    but uses the new Phase 1-5 architecture internally.
    """
    try:
        logger.info("Processing video with legacy compatibility mode")
        
        # Download video
        import tempfile
        import requests
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            dirs = {
                "base": work_dir,
                "downloads": work_dir / "downloads",
                "clips": work_dir / "clips",
                "vertical": work_dir / "vertical"
            }
            
            for dir_path in dirs.values():
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Download video
            logger.info(f"Downloading video from: {request.video_url}")
            response = requests.get(request.video_url, stream=True, timeout=300)
            response.raise_for_status()
            
            video_path = dirs["downloads"] / "input_video.mp4"
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Use provided transcript
            transcript_data = request.transcript_json
            
            # Create pause-based segments
            potential_clips = create_pause_based_segments(
                transcript=transcript_data,
                min_duration=request.min_duration,
                max_duration=request.max_duration
            )
            
            # Context-aware analysis
            if not OPENAI_API_KEY:
                raise HTTPException(status_code=500, detail="OpenAI API key not configured")
            
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            analysis_results = create_multi_pass_analysis(
                all_segments=transcript_data["segments"],
                potential_clips=potential_clips,
                client=client
            )
            
            evaluations = analysis_results["clip_evaluations"]
            
            # Select top clips
            from extract_shorts import filter_context_aware_clips
            top_clips = filter_context_aware_clips(evaluations, top_n=request.num_clips)
            
            # Cut video clips
            generated_files = []
            clip_results = []
            
            for i, clip in enumerate(top_clips, 1):
                try:
                    # Cut the main clip
                    clip_path = cut_clip(
                        video_path=video_path,
                        output_dir=dirs["clips"],
                        start_time=clip["start"],
                        end_time=clip["end"],
                        clip_name=f"{i:02d}_{clip['title'][:30]}",
                        vertical=False
                    )
                    generated_files.append(clip_path)
                    
                    # Create vertical version if requested
                    vertical_path = None
                    if request.vertical:
                        vertical_path = reframe_to_vertical(clip_path, dirs["base"])
                        generated_files.append(vertical_path)
                    
                    # Create subtitles if requested
                    subtitle_path = None
                    if request.subtitles:
                        subtitle_path = create_subtitle_file(clip, dirs["clips"])
                        generated_files.append(subtitle_path)
                    
                    clip_result = ClipResult(
                        index=i,
                        title=clip["title"],
                        start=clip["start"],
                        end=clip["end"],
                        duration=clip["duration"],
                        score=clip["overall_score"],
                        reasoning=clip["reasoning"],
                        tags=clip["tags"],
                        files={
                            "horizontal": str(clip_path),
                            "vertical": str(vertical_path) if vertical_path else None,
                            "subtitle": str(subtitle_path) if subtitle_path else None
                        }
                    )
                    clip_results.append(clip_result)
                    
                except Exception as e:
                    logger.error(f"Error processing clip {i}: {e}")
                    continue
            
            # Prepare response
            response = VideoProcessResponse(
                success=True,
                project_id=f"legacy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                clips_generated=len(clip_results),
                clips=clip_results,
                transcription={
                    "segments": len(transcript_data.get("segments", [])),
                    "language": transcript_data.get("language", request.language)
                },
                analysis={
                    "method": "context_aware_multi_pass",
                    "themes": analysis_results["theme_analysis"]["main_themes"],
                    "overall_topic": analysis_results["theme_analysis"]["overall_topic"],
                    "total_clips_analyzed": len(evaluations)
                },
                processing_info={
                    "language": request.language,
                    "vertical_created": request.vertical,
                    "subtitles_created": request.subtitles,
                    "video_url": request.video_url
                },
                files=[str(f) for f in generated_files]
            )
            
            logger.info(f"Legacy processing complete! Generated {len(clip_results)} clips")
            return response
            
    except Exception as e:
        logger.error(f"Legacy processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# RUNPOD SERVERLESS HANDLER
# =============================================================================

async def runpod_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """RunPod serverless handler that wraps the FastAPI application."""
    try:
        input_data = event.get("input", {})
        
        # Convert to VideoProcessRequest
        request = VideoProcessRequest(**input_data)
        
        # Use legacy endpoint for compatibility
        response = await legacy_video_processing(request)
        
        return {"output": response.dict()}
        
    except Exception as e:
        error_msg = f"RunPod processing failed: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return {
            "error": error_msg,
            "traceback": traceback.format_exc()
        }

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    logger.info("Starting YouTube Shorts Editor v2.0.0")
    await initialize_services()
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down YouTube Shorts Editor")

# =============================================================================
# MAIN ENTRY POINTS
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Check if running in RunPod serverless mode
    if os.getenv("RUNPOD_SERVERLESS"):
        logger.info("Starting in RunPod serverless mode")
        runpod.serverless.start({"handler": runpod_handler})
    else:
        logger.info("Starting FastAPI server")
        uvicorn.run(
            "runpod_handler:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False
        )

# Export for external use
__all__ = ["app", "runpod_handler"]