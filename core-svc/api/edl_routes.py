"""
EDL API Routes - Phase 3
REST endpoints for Edit Decision List generation and management
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pathlib import Path
import structlog
from uuid import UUID

from ..models.database import get_db, Video, EditDecisionList, ClipInstance, CutCandidate
from ..services.edl_generator import EDLGenerator, EDLOutput
from ..services.quality_validator import QualityValidator, EDLQualityReport
from ..services.intelligence_coordinator import IntelligenceCoordinator
from ..tasks.edl_tasks import generate_edl_task, validate_edl_quality_task

logger = structlog.get_logger()

# Create router for EDL endpoints
router = APIRouter(prefix="/edl", tags=["Edit Decision Lists"])


# Pydantic models for request/response
from pydantic import BaseModel, Field


class EDLGenerationRequest(BaseModel):
    """Request model for EDL generation"""
    video_id: UUID = Field(..., description="Video ID to generate EDL for")
    target_duration: float = Field(60.0, ge=20.0, le=300.0, description="Target EDL duration in seconds")
    strategy: str = Field("multi_modal", description="Generation strategy: silence_based, scene_based, multi_modal")
    max_clips: int = Field(5, ge=1, le=20, description="Maximum number of clips in EDL")
    min_clip_duration: float = Field(20.0, ge=10.0, le=120.0, description="Minimum clip duration")
    max_clip_duration: float = Field(80.0, ge=30.0, le=180.0, description="Maximum clip duration")
    quality_threshold: float = Field(7.0, ge=0.0, le=10.0, description="Minimum quality threshold")
    generate_alternatives: bool = Field(True, description="Generate alternative EDL options")


class EDLResponse(BaseModel):
    """Response model for EDL operations"""
    edl_id: UUID
    video_id: UUID
    version: int
    status: str
    target_duration: float
    actual_duration: Optional[float]
    overall_score: Optional[float]
    clip_count: int
    generation_strategy: Optional[str]
    created_at: str
    

class ClipInstanceResponse(BaseModel):
    """Response model for clip instances"""
    id: UUID
    sequence: int
    source_start_time: float
    source_end_time: float
    source_duration: float
    timeline_start_time: float
    timeline_end_time: float
    timeline_duration: float
    audio_score: Optional[float]
    visual_score: Optional[float]
    semantic_score: Optional[float]
    engagement_score: Optional[float]
    overall_score: Optional[float]
    reasoning: Optional[str]


class EDLDetailResponse(BaseModel):
    """Detailed EDL response with clips"""
    edl: EDLResponse
    clips: List[ClipInstanceResponse]
    alternative_edls: List[EDLResponse]


class QualityReportResponse(BaseModel):
    """Response model for quality reports"""
    edl_id: UUID
    overall_quality_score: float
    avg_cut_smoothness: float
    avg_visual_continuity: float
    avg_semantic_coherence: float
    avg_engagement_score: float
    cuts_meeting_smoothness: int
    cuts_meeting_visual: int
    cuts_meeting_duration: int
    high_quality_clips: int
    medium_quality_clips: int
    low_quality_clips: int
    meets_production_criteria: bool
    validation_time_seconds: float
    recommended_adjustments: List[Dict[str, Any]]
    quality_bottlenecks: List[str]


@router.post("/generate", response_model=EDLResponse)
async def generate_edl(
    request: EDLGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate a new Edit Decision List for a video
    
    This endpoint initiates EDL generation using multi-modal fusion analysis.
    The process runs asynchronously and updates the EDL status when complete.
    """
    logger.info("EDL generation requested", 
               video_id=str(request.video_id),
               target_duration=request.target_duration,
               strategy=request.strategy)
    
    # Verify video exists and has required analysis
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != "DONE":
        raise HTTPException(
            status_code=400, 
            detail=f"Video processing not complete. Current status: {video.status}"
        )
    
    # Check if audio and visual analysis exist
    if not hasattr(video, 'audio_analysis') or not video.audio_analysis:
        raise HTTPException(
            status_code=400, 
            detail="Video requires audio analysis before EDL generation"
        )
    
    if not hasattr(video, 'visual_analysis') or not video.visual_analysis:
        raise HTTPException(
            status_code=400, 
            detail="Video requires visual analysis before EDL generation"
        )
    
    try:
        # Create new EDL record
        edl = EditDecisionList(
            video_id=request.video_id,
            version=1,  # TODO: Implement versioning logic
            status="processing",
            target_duration=request.target_duration,
            generation_strategy=request.strategy
        )
        db.add(edl)
        db.commit()
        db.refresh(edl)
        
        # Queue EDL generation Celery task
        task = generate_edl_task.delay(
            str(edl.id),
            str(request.video_id),
            request.dict()
        )
        
        logger.info("EDL generation queued", 
                   edl_id=str(edl.id),
                   video_id=str(request.video_id),
                   task_id=task.id)
        
        return EDLResponse(
            edl_id=edl.id,
            video_id=edl.video_id,
            version=edl.version,
            status=edl.status,
            target_duration=edl.target_duration,
            actual_duration=edl.actual_duration,
            overall_score=edl.overall_score,
            clip_count=0,  # Will be updated when processing completes
            generation_strategy=edl.generation_strategy,
            created_at=edl.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error("EDL generation request failed", error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail="EDL generation failed")


@router.get("/{edl_id}", response_model=EDLDetailResponse)
async def get_edl(edl_id: UUID, db: Session = Depends(get_db)):
    """
    Get detailed EDL information including clips and alternatives
    """
    edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
    if not edl:
        raise HTTPException(status_code=404, detail="EDL not found")
    
    # Get clips for this EDL
    clips = db.query(ClipInstance).filter(
        ClipInstance.edl_id == edl_id
    ).order_by(ClipInstance.sequence).all()
    
    # Get alternative EDLs (same video, different versions)
    alternative_edls = db.query(EditDecisionList).filter(
        EditDecisionList.video_id == edl.video_id,
        EditDecisionList.id != edl_id
    ).all()
    
    return EDLDetailResponse(
        edl=EDLResponse(
            edl_id=edl.id,
            video_id=edl.video_id,
            version=edl.version,
            status=edl.status,
            target_duration=edl.target_duration,
            actual_duration=edl.actual_duration,
            overall_score=edl.overall_score,
            clip_count=len(clips),
            generation_strategy=edl.generation_strategy,
            created_at=edl.created_at.isoformat()
        ),
        clips=[
            ClipInstanceResponse(
                id=clip.id,
                sequence=clip.sequence,
                source_start_time=clip.source_start_time,
                source_end_time=clip.source_end_time,
                source_duration=clip.source_duration,
                timeline_start_time=clip.timeline_start_time,
                timeline_end_time=clip.timeline_end_time,
                timeline_duration=clip.timeline_duration,
                audio_score=clip.audio_score,
                visual_score=clip.visual_score,
                semantic_score=clip.semantic_score,
                engagement_score=clip.engagement_score,
                overall_score=clip.overall_score,
                reasoning=clip.reasoning
            ) for clip in clips
        ],
        alternative_edls=[
            EDLResponse(
                edl_id=alt.id,
                video_id=alt.video_id,
                version=alt.version,
                status=alt.status,
                target_duration=alt.target_duration,
                actual_duration=alt.actual_duration,
                overall_score=alt.overall_score,
                clip_count=len(alt.clip_instances) if alt.clip_instances else 0,
                generation_strategy=alt.generation_strategy,
                created_at=alt.created_at.isoformat()
            ) for alt in alternative_edls
        ]
    )


@router.get("/video/{video_id}", response_model=List[EDLResponse])
async def get_video_edls(video_id: UUID, db: Session = Depends(get_db)):
    """
    Get all EDLs for a specific video
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    edls = db.query(EditDecisionList).filter(
        EditDecisionList.video_id == video_id
    ).order_by(EditDecisionList.created_at.desc()).all()
    
    return [
        EDLResponse(
            edl_id=edl.id,
            video_id=edl.video_id,
            version=edl.version,
            status=edl.status,
            target_duration=edl.target_duration,
            actual_duration=edl.actual_duration,
            overall_score=edl.overall_score,
            clip_count=len(edl.clip_instances) if edl.clip_instances else 0,
            generation_strategy=edl.generation_strategy,
            created_at=edl.created_at.isoformat()
        ) for edl in edls
    ]


@router.post("/{edl_id}/validate", response_model=QualityReportResponse)
async def validate_edl_quality(
    edl_id: UUID, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Validate EDL quality and generate comprehensive quality report
    """
    edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
    if not edl:
        raise HTTPException(status_code=404, detail="EDL not found")
    
    if edl.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"EDL not ready for validation. Current status: {edl.status}"
        )
    
    try:
        # Get video for validation
        video = db.query(Video).filter(Video.id == edl.video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Associated video not found")
        
        # TODO: Get video file path from storage service
        video_path = Path(f"/tmp/videos/{video.id}.mp4")  # Placeholder
        
        # Queue EDL validation Celery task
        task = validate_edl_quality_task.delay(
            str(edl_id),
            str(video_path)
        )
        
        # Return placeholder response - in production this would be async
        return QualityReportResponse(
            edl_id=edl_id,
            overall_quality_score=0.0,
            avg_cut_smoothness=0.0,
            avg_visual_continuity=0.0,
            avg_semantic_coherence=0.0,
            avg_engagement_score=0.0,
            cuts_meeting_smoothness=0,
            cuts_meeting_visual=0,
            cuts_meeting_duration=0,
            high_quality_clips=0,
            medium_quality_clips=0,
            low_quality_clips=0,
            meets_production_criteria=False,
            validation_time_seconds=0.0,
            recommended_adjustments=[],
            quality_bottlenecks=[]
        )
        
    except Exception as e:
        logger.error("EDL validation failed", error=str(e), edl_id=str(edl_id))
        raise HTTPException(status_code=500, detail="EDL validation failed")


@router.delete("/{edl_id}")
async def delete_edl(edl_id: UUID, db: Session = Depends(get_db)):
    """
    Delete an EDL and all associated clips
    """
    edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
    if not edl:
        raise HTTPException(status_code=404, detail="EDL not found")
    
    try:
        # Delete associated clips (cascade should handle this)
        db.delete(edl)
        db.commit()
        
        logger.info("EDL deleted", edl_id=str(edl_id))
        return {"message": "EDL deleted successfully"}
        
    except Exception as e:
        logger.error("EDL deletion failed", error=str(e), edl_id=str(edl_id))
        db.rollback()
        raise HTTPException(status_code=500, detail="EDL deletion failed")


@router.get("/{edl_id}/candidates", response_model=List[Dict[str, Any]])
async def get_edl_candidates(edl_id: UUID, db: Session = Depends(get_db)):
    """
    Get cut candidates used during EDL generation for analysis
    """
    edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
    if not edl:
        raise HTTPException(status_code=404, detail="EDL not found")
    
    # Get cut candidates for this EDL's generation session
    # This would require storing the generation_id during EDL creation
    candidates = db.query(CutCandidate).filter(
        CutCandidate.video_id == edl.video_id
        # Add generation session filter when implemented
    ).order_by(CutCandidate.overall_score.desc()).all()
    
    return [
        {
            "id": str(candidate.id),
            "start_time": candidate.start_time,
            "end_time": candidate.end_time,
            "duration": candidate.duration,
            "overall_score": candidate.overall_score,
            "audio_score": candidate.audio_score,
            "visual_score": candidate.visual_score,
            "semantic_score": candidate.semantic_score,
            "engagement_score": candidate.engagement_score,
            "selected_for_edl": candidate.selected_for_edl,
            "selection_rank": candidate.selection_rank,
            "exclusion_reason": candidate.exclusion_reason
        } for candidate in candidates
    ]


@router.put("/{edl_id}/clips/{clip_id}")
async def update_clip(
    edl_id: UUID, 
    clip_id: UUID,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Update a specific clip in an EDL (for manual editing)
    """
    # Verify EDL exists
    edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
    if not edl:
        raise HTTPException(status_code=404, detail="EDL not found")
    
    # Get clip
    clip = db.query(ClipInstance).filter(
        ClipInstance.id == clip_id,
        ClipInstance.edl_id == edl_id
    ).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    try:
        # Update allowed fields
        allowed_fields = {
            'source_start_time', 'source_end_time', 'timeline_start_time', 
            'timeline_end_time', 'reasoning', 'transformations'
        }
        
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(clip, field):
                setattr(clip, field, value)
        
        # Recalculate derived fields
        if 'source_start_time' in update_data or 'source_end_time' in update_data:
            clip.source_duration = clip.source_end_time - clip.source_start_time
        
        if 'timeline_start_time' in update_data or 'timeline_end_time' in update_data:
            clip.timeline_duration = clip.timeline_end_time - clip.timeline_start_time
        
        db.commit()
        db.refresh(clip)
        
        logger.info("Clip updated", clip_id=str(clip_id), edl_id=str(edl_id))
        
        return ClipInstanceResponse(
            id=clip.id,
            sequence=clip.sequence,
            source_start_time=clip.source_start_time,
            source_end_time=clip.source_end_time,
            source_duration=clip.source_duration,
            timeline_start_time=clip.timeline_start_time,
            timeline_end_time=clip.timeline_end_time,
            timeline_duration=clip.timeline_duration,
            audio_score=clip.audio_score,
            visual_score=clip.visual_score,
            semantic_score=clip.semantic_score,
            engagement_score=clip.engagement_score,
            overall_score=clip.overall_score,
            reasoning=clip.reasoning
        )
        
    except Exception as e:
        logger.error("Clip update failed", error=str(e), clip_id=str(clip_id))
        db.rollback()
        raise HTTPException(status_code=500, detail="Clip update failed")


