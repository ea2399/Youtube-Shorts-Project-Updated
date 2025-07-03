"""
Celery Tasks for Video Processing - Phase 1
Single process_video task wrapping existing pipeline
"""

from typing import Dict, Any
import traceback
from sqlalchemy.orm import sessionmaker
import structlog

from .celery_app import celery_app
from ..models.database import engine, Video, Clip
from ..services.video_processor import VideoProcessingService

logger = structlog.get_logger()

# Create database session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def update_video_progress(video_id: str, stage: str, pct: float, message: str = None):
    """Update video processing progress in database"""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.progress = {"stage": stage, "pct": pct, "message": message}
            if stage == "error":
                video.status = "ERROR"
                video.error_message = message
            elif pct >= 100:
                video.status = "DONE"
            else:
                video.status = "PROCESSING"
            db.commit()
            logger.info("Progress updated", video_id=video_id, stage=stage, pct=pct)
    except Exception as e:
        logger.error("Failed to update progress", video_id=video_id, error=str(e))
    finally:
        db.close()


def save_clips_to_database(video_id: str, clip_results: list):
    """Save generated clips to database"""
    db = SessionLocal()
    try:
        for clip_data in clip_results:
            if "error" in clip_data:
                continue  # Skip failed clips
                
            clip = Clip(
                video_id=video_id,
                start=clip_data["start"],
                end=clip_data["end"],
                duration=clip_data["duration"],
                title=clip_data["title"],
                text=clip_data.get("text", ""),
                overall_score=clip_data.get("score"),
                context_dependency=clip_data.get("context_dependency"),
                reasoning=clip_data.get("reasoning"),
                tags=clip_data.get("tags"),
                horizontal_path=clip_data["files"].get("horizontal"),
                vertical_path=clip_data["files"].get("vertical"),
                subtitle_path=clip_data["files"].get("subtitle")
            )
            db.add(clip)
        
        db.commit()
        logger.info("Clips saved to database", video_id=video_id, count=len(clip_results))
        
    except Exception as e:
        logger.error("Failed to save clips", video_id=video_id, error=str(e))
        db.rollback()
    finally:
        db.close()


@celery_app.task(bind=True, name="core_svc.tasks.process_video")
def process_video_task(self, video_id: str, video_url: str, transcript_json: Dict[str, Any], 
                      processing_options: Dict[str, Any]):
    """
    Single high-level video processing task
    Wraps existing pipeline with progress tracking and error handling
    """
    
    logger.info("Starting video processing task", 
               video_id=video_id, 
               task_id=self.request.id,
               url=video_url)
    
    try:
        # Initialize service
        service = VideoProcessingService()
        
        # Step 1: Download (0-20%)
        update_video_progress(video_id, "downloading", 5, "Starting download")
        
        # Step 2: Create segments (20-30%)
        update_video_progress(video_id, "segmenting", 20, "Creating natural segments")
        
        # Step 3: GPT analysis (30-60%)
        update_video_progress(video_id, "analyzing", 30, "Analyzing clips with GPT")
        
        # Step 4: Select clips (60-70%)
        update_video_progress(video_id, "selecting", 60, "Selecting top clips")
        
        # Step 5: Cut videos (70-90%)
        update_video_progress(video_id, "cutting", 70, "Cutting video clips")
        
        # Process video using existing pipeline
        result = service.process_video_complete(
            video_url=video_url,
            transcript_json=transcript_json,
            processing_options=processing_options
        )
        
        # Step 6: Save results (90-100%)
        update_video_progress(video_id, "saving", 90, "Saving clips to database")
        
        # Save clips to database
        save_clips_to_database(video_id, result["clips"])
        
        # Mark as complete
        update_video_progress(video_id, "completed", 100, "Processing complete")
        
        logger.info("Video processing task completed successfully", 
                   video_id=video_id,
                   clips_generated=result["clips_generated"])
        
        return {
            "success": True,
            "video_id": video_id,
            "clips_generated": result["clips_generated"]
        }
        
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        logger.error("Video processing task failed", 
                    video_id=video_id, 
                    error=error_msg,
                    traceback=traceback.format_exc())
        
        # Update database with error
        update_video_progress(video_id, "error", 0, error_msg)
        
        # Re-raise exception for Celery to handle
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(name="core_svc.tasks.health_check")
def health_check_task():
    """Simple health check task for monitoring"""
    logger.info("Health check task executed")
    return {"status": "healthy", "timestamp": "now"}