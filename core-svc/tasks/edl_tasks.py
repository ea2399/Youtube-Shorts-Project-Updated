"""
EDL Celery Tasks - Phase 3
Background tasks for EDL generation and quality validation
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

from .celery_app import celery_app as app
from ..models.database import get_db, Video, EditDecisionList, ClipInstance
from ..services.edl_generator import EDLGenerator, EDLOutput
from ..services.quality_validator import QualityValidator, EDLQualityReport
from ..services.intelligence_coordinator import IntelligenceCoordinator

logger = structlog.get_logger()


@app.task(bind=True, name="generate_edl_task")
def generate_edl_task(self, edl_id: str, video_id: str, generation_params: Dict[str, Any]):
    """
    Celery task for EDL generation with multi-modal fusion
    
    Args:
        edl_id: UUID of the EDL record to update
        video_id: UUID of the source video
        generation_params: Generation parameters from API request
    """
    logger.info("Starting EDL generation task", 
               edl_id=edl_id, 
               video_id=video_id,
               params=generation_params)
    
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'stage': 'loading_data', 'progress': 10})
        
        # Load video and intelligence results
        with next(get_db()) as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video not found: {video_id}")
            
            edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
            if not edl:
                raise ValueError(f"EDL not found: {edl_id}")
            
            # Update EDL status
            edl.status = "processing"
            db.commit()
        
        # Get video file path (this would come from storage service in production)
        # For now, assume videos are stored in a standard location
        video_path = Path(f"/tmp/videos/{video_id}.mp4")
        if not video_path.exists():
            # Try alternative paths or download from storage
            video_path = Path(f"/app/videos/{video_id}.mp4")
        
        self.update_state(state='PROGRESS', meta={'stage': 'loading_intelligence', 'progress': 20})
        
        # Load intelligence results using coordinator
        coordinator = IntelligenceCoordinator()
        intelligence_results = coordinator.load_results_for_video(video_id)
        
        if not intelligence_results:
            raise ValueError(f"Intelligence analysis not found for video: {video_id}")
        
        self.update_state(state='PROGRESS', meta={'stage': 'generating_edl', 'progress': 40})
        
        # Initialize EDL generator
        generator = EDLGenerator()
        
        # Generate EDL with specified parameters
        edl_output = generator.generate_edl(
            video_id=video_id,
            target_duration=generation_params.get("target_duration", 60.0),
            max_clips=generation_params.get("max_clips", 5),
            min_clip_duration=generation_params.get("min_clip_duration", 20.0),
            max_clip_duration=generation_params.get("max_clip_duration", 80.0),
            quality_threshold=generation_params.get("quality_threshold", 7.0),
            strategy=generation_params.get("strategy", "multi_modal")
        )
        
        self.update_state(state='PROGRESS', meta={'stage': 'saving_results', 'progress': 80})
        
        # Save EDL results to database
        _save_edl_results(edl_id, edl_output)
        
        self.update_state(state='PROGRESS', meta={'stage': 'completed', 'progress': 100})
        
        logger.info("EDL generation completed successfully", 
                   edl_id=edl_id,
                   clip_count=len(edl_output.clips),
                   overall_score=edl_output.overall_score)
        
        return {
            "status": "completed",
            "edl_id": edl_id,
            "clip_count": len(edl_output.clips),
            "overall_score": edl_output.overall_score,
            "actual_duration": edl_output.actual_duration,
            "processing_time": edl_output.processing_time
        }
        
    except Exception as e:
        logger.error("EDL generation task failed", 
                    edl_id=edl_id, 
                    error=str(e),
                    exc_info=True)
        
        # Update EDL status to failed
        try:
            with next(get_db()) as db:
                edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
                if edl:
                    edl.status = "failed"
                    db.commit()
        except Exception as db_error:
            logger.error("Failed to update EDL status to failed", error=str(db_error))
        
        # Re-raise the original exception
        raise self.retry(exc=e, countdown=60, max_retries=3)


@app.task(bind=True, name="validate_edl_quality_task")
def validate_edl_quality_task(self, edl_id: str, video_path: str):
    """
    Celery task for EDL quality validation
    
    Args:
        edl_id: UUID of the EDL to validate
        video_path: Path to the source video file
    """
    logger.info("Starting EDL quality validation task", 
               edl_id=edl_id,
               video_path=video_path)
    
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'stage': 'loading_edl', 'progress': 10})
        
        # Load EDL data
        with next(get_db()) as db:
            edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
            if not edl:
                raise ValueError(f"EDL not found: {edl_id}")
            
            if edl.status != "completed":
                raise ValueError(f"EDL not ready for validation. Status: {edl.status}")
        
        self.update_state(state='PROGRESS', meta={'stage': 'loading_intelligence', 'progress': 30})
        
        # Load intelligence results
        coordinator = IntelligenceCoordinator()
        intelligence_results = coordinator.load_results_for_video(str(edl.video_id))
        
        if not intelligence_results:
            raise ValueError(f"Intelligence analysis not found for video: {edl.video_id}")
        
        self.update_state(state='PROGRESS', meta={'stage': 'validating_quality', 'progress': 60})
        
        # Run quality validation
        validator = QualityValidator()
        quality_report = validator.validate_edl(
            edl_id=edl_id,
            video_path=Path(video_path),
            intelligence_results=intelligence_results
        )
        
        self.update_state(state='PROGRESS', meta={'stage': 'saving_report', 'progress': 90})
        
        # Save quality metrics back to EDL
        _save_quality_report(edl_id, quality_report)
        
        self.update_state(state='PROGRESS', meta={'stage': 'completed', 'progress': 100})
        
        logger.info("EDL quality validation completed", 
                   edl_id=edl_id,
                   overall_score=quality_report.overall_quality_score,
                   meets_criteria=quality_report.meets_production_criteria)
        
        return {
            "status": "completed",
            "edl_id": edl_id,
            "overall_quality_score": quality_report.overall_quality_score,
            "meets_production_criteria": quality_report.meets_production_criteria,
            "validation_time": quality_report.validation_time_seconds
        }
        
    except Exception as e:
        logger.error("EDL quality validation task failed", 
                    edl_id=edl_id, 
                    error=str(e),
                    exc_info=True)
        
        # Re-raise for retry logic
        raise self.retry(exc=e, countdown=30, max_retries=2)


@app.task(bind=True, name="regenerate_edl_task")
def regenerate_edl_task(self, original_edl_id: str, regeneration_params: Dict[str, Any]):
    """
    Celery task for regenerating an EDL with different parameters
    
    Args:
        original_edl_id: UUID of the original EDL
        regeneration_params: New generation parameters
    """
    logger.info("Starting EDL regeneration task", 
               original_edl_id=original_edl_id,
               params=regeneration_params)
    
    try:
        # Load original EDL
        with next(get_db()) as db:
            original_edl = db.query(EditDecisionList).filter(
                EditDecisionList.id == original_edl_id
            ).first()
            
            if not original_edl:
                raise ValueError(f"Original EDL not found: {original_edl_id}")
            
            # Create new EDL version
            new_edl = EditDecisionList(
                video_id=original_edl.video_id,
                version=original_edl.version + 1,
                status="processing",
                target_duration=regeneration_params.get("target_duration", original_edl.target_duration),
                generation_strategy=regeneration_params.get("strategy", original_edl.generation_strategy)
            )
            
            db.add(new_edl)
            db.commit()
            db.refresh(new_edl)
            
            new_edl_id = str(new_edl.id)
            video_id = str(original_edl.video_id)
        
        # Use the regular EDL generation task for the actual work
        result = generate_edl_task.apply(
            args=[new_edl_id, video_id, regeneration_params]
        )
        
        return {
            "status": "completed",
            "original_edl_id": original_edl_id,
            "new_edl_id": new_edl_id,
            "generation_result": result.get()
        }
        
    except Exception as e:
        logger.error("EDL regeneration task failed", 
                    original_edl_id=original_edl_id, 
                    error=str(e),
                    exc_info=True)
        
        raise self.retry(exc=e, countdown=60, max_retries=2)


def _save_edl_results(edl_id: str, edl_output: EDLOutput):
    """Save EDL generation results to database"""
    try:
        with next(get_db()) as db:
            # Update EDL record
            edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
            if not edl:
                raise ValueError(f"EDL not found: {edl_id}")
            
            # Update EDL metadata
            edl.status = "completed"
            edl.actual_duration = edl_output.actual_duration
            edl.overall_score = edl_output.overall_score
            edl.cut_smoothness = edl_output.cut_smoothness
            edl.visual_continuity = edl_output.visual_continuity
            edl.semantic_coherence = edl_output.semantic_coherence
            edl.engagement_score = edl_output.engagement_score
            edl.reasoning = {"generation_reasoning": edl_output.reasoning}
            edl.alternative_count = len(edl_output.alternative_edls)
            edl.generation_time_seconds = edl_output.processing_time
            
            # Save clip instances
            for i, clip_data in enumerate(edl_output.clips):
                clip_instance = ClipInstance(
                    edl_id=edl.id,
                    sequence=i + 1,
                    source_start_time=clip_data["source_start"],
                    source_end_time=clip_data["source_end"],
                    source_duration=clip_data["duration"],
                    timeline_start_time=clip_data.get("timeline_start", clip_data["source_start"]),
                    timeline_end_time=clip_data.get("timeline_end", clip_data["source_end"]),
                    timeline_duration=clip_data["duration"],
                    audio_score=clip_data.get("audio_score"),
                    visual_score=clip_data.get("visual_score"),
                    semantic_score=clip_data.get("semantic_score"),
                    engagement_score=clip_data.get("engagement_score"),
                    overall_score=clip_data.get("overall_score"),
                    reasoning=clip_data.get("reasoning"),
                    content_type=clip_data.get("content_type"),
                    language_primary=clip_data.get("language"),
                    transformations=clip_data.get("transformations"),
                    reframing_data=clip_data.get("reframing_data")
                )
                db.add(clip_instance)
            
            db.commit()
            
            logger.info("EDL results saved to database", 
                       edl_id=edl_id,
                       clip_count=len(edl_output.clips))
        
    except Exception as e:
        logger.error("Failed to save EDL results", edl_id=edl_id, error=str(e))
        raise


def _save_quality_report(edl_id: str, quality_report: EDLQualityReport):
    """Save quality validation report to database"""
    try:
        with next(get_db()) as db:
            # Update EDL with quality metrics
            edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
            if not edl:
                raise ValueError(f"EDL not found: {edl_id}")
            
            # Update quality scores if they're better than current
            if quality_report.overall_quality_score > (edl.overall_score or 0):
                edl.overall_score = quality_report.overall_quality_score
                edl.cut_smoothness = quality_report.avg_cut_smoothness
                edl.visual_continuity = quality_report.avg_visual_continuity
                edl.semantic_coherence = quality_report.avg_semantic_coherence
                edl.engagement_score = quality_report.avg_engagement_score
            
            # Add quality report to reasoning
            if edl.reasoning:
                edl.reasoning["quality_validation"] = {
                    "overall_score": quality_report.overall_quality_score,
                    "meets_criteria": quality_report.meets_production_criteria,
                    "validation_time": quality_report.validation_time_seconds,
                    "bottlenecks": quality_report.quality_bottlenecks,
                    "recommendations": quality_report.recommended_adjustments
                }
            else:
                edl.reasoning = {
                    "quality_validation": {
                        "overall_score": quality_report.overall_quality_score,
                        "meets_criteria": quality_report.meets_production_criteria
                    }
                }
            
            db.commit()
            
            logger.info("Quality report saved to database", 
                       edl_id=edl_id,
                       overall_score=quality_report.overall_quality_score)
        
    except Exception as e:
        logger.error("Failed to save quality report", edl_id=edl_id, error=str(e))
        raise