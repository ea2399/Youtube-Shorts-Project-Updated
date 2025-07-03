"""
API Routes - Phase 1-5
Complete REST pipeline with rendering capabilities
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import structlog

from ..models.database import get_db, Video, Clip
from ..models.schemas import VideoCreate, VideoStatus, VideoWithClips, ErrorResponse
from ..tasks.video_processor import process_video_task
from .render_endpoints import router as render_router

logger = structlog.get_logger()
router = APIRouter()

# Include Phase 5 rendering endpoints
router.include_router(render_router)


@router.post("/videos", response_model=VideoStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_video_project(
    video_data: VideoCreate,
    db: Session = Depends(get_db)
):
    """
    Create new video processing project
    Returns immediately with project ID, processing happens in background
    """
    try:
        # Create video record
        video = Video(
            source_url=str(video_data.video_url),
            status="CREATED",
            language=video_data.language,
            num_clips=video_data.num_clips,
            min_duration=video_data.min_duration,
            max_duration=video_data.max_duration,
            progress={"stage": "created", "pct": 0}
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        logger.info("Video project created", video_id=str(video.id), url=video_data.video_url)
        
        # Start background processing
        task = process_video_task.delay(
            video_id=str(video.id),
            video_url=str(video_data.video_url),
            transcript_json=video_data.transcript_json,
            processing_options={
                "language": video_data.language,
                "num_clips": video_data.num_clips,
                "min_duration": video_data.min_duration,
                "max_duration": video_data.max_duration,
                "vertical": video_data.vertical,
                "subtitles": video_data.subtitles
            }
        )
        
        logger.info("Background task started", video_id=str(video.id), task_id=task.id)
        
        return VideoStatus.from_orm(video)
        
    except Exception as e:
        logger.error("Failed to create video project", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create video project: {str(e)}"
        )


@router.get("/videos/{video_id}", response_model=VideoStatus)
async def get_video_status(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Get video processing status
    Returns state enum {CREATED, DOWNLOADING, PROCESSING, DONE, ERROR} + progress %
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video project not found"
        )
    
    return VideoStatus.from_orm(video)


@router.get("/videos/{video_id}/clips", response_model=List[dict])
async def get_video_clips(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Get generated clips for a video
    Only available once processing is DONE
    Returns array of {clip_url, start, end, aspect_ratio}
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video project not found"
        )
    
    if video.status != "DONE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Video processing not complete. Current status: {video.status}"
        )
    
    clips = db.query(Clip).filter(Clip.video_id == video_id).all()
    
    # Format clips for response
    clip_results = []
    for clip in clips:
        clip_data = {
            "id": str(clip.id),
            "start": clip.start,
            "end": clip.end,
            "duration": clip.duration,
            "title": clip.title,
            "text": clip.text,
            "overall_score": clip.overall_score,
            "context_dependency": clip.context_dependency,
            "tags": clip.tags,
            "files": {
                "horizontal": clip.horizontal_path,
                "vertical": clip.vertical_path,
                "subtitle": clip.subtitle_path
            }
        }
        clip_results.append(clip_data)
    
    return clip_results


@router.get("/videos", response_model=List[VideoStatus])
async def list_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all video projects with pagination"""
    videos = db.query(Video).offset(skip).limit(limit).all()
    return [VideoStatus.from_orm(video) for video in videos]


@router.delete("/videos/{video_id}")
async def delete_video_project(
    video_id: str,
    db: Session = Depends(get_db)
):
    """Delete a video project and all associated clips"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video project not found"
        )
    
    # TODO: Also delete actual files from storage
    db.delete(video)
    db.commit()
    
    logger.info("Video project deleted", video_id=video_id)
    
    return {"message": "Video project deleted successfully"}