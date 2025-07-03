/**
 * Timeline Clip - Phase 4 Core Component
 * Individual clip rendering with drag, resize, and selection support
 */

'use client';

import React, { useState, useRef, useCallback } from 'react';
import { TimelineClip } from '@/types';
import { useTimelineStore } from '@/stores/timelineStore';

interface TimelineClipProps {
  clip: TimelineClip;
  trackHeight: number;
  pixelsPerSecond: number;
  isTrackLocked: boolean;
}

export const TimelineClipComponent: React.FC<TimelineClipProps> = ({
  clip,
  trackHeight,
  pixelsPerSecond,
  isTrackLocked,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState<'start' | 'end' | null>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0, startTime: 0 });
  const clipRef = useRef<HTMLDivElement>(null);
  
  const {
    selectedClips,
    selectClip,
    moveClip,
    trimClip,
    snapToGrid,
    snapToGrid: snapTime,
    getClipQuality,
  } = useTimelineStore();
  
  // Calculate clip dimensions and position
  const clipWidth = clip.duration * pixelsPerSecond;
  const clipLeft = clip.startTime * pixelsPerSecond;
  const isSelected = selectedClips.includes(clip.id);
  
  // Get quality metrics for visual indicators
  const quality = getClipQuality(clip.id);
  
  // Handle clip selection
  const handleClipClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (e.shiftKey) {
      // Multi-select
      selectClip(clip.id, true);
    } else {
      // Single select
      selectClip(clip.id, false);
    }
  }, [clip.id, selectClip]);
  
  // Handle drag start
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isTrackLocked) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    setIsDragging(true);
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      startTime: clip.startTime,
    });
    
    // Select clip if not already selected
    if (!selectedClips.includes(clip.id)) {
      selectClip(clip.id, false);
    }
  }, [clip.id, clip.startTime, isTrackLocked, selectedClips, selectClip]);
  
  // Handle resize start
  const handleResizeStart = useCallback((e: React.MouseEvent, direction: 'start' | 'end') => {
    if (isTrackLocked) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    setIsResizing(direction);
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      startTime: clip.startTime,
    });
  }, [clip.startTime, isTrackLocked]);
  
  // Handle mouse move (drag/resize)
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging && !isResizing) return;
    
    const deltaX = e.clientX - dragStart.x;
    const deltaTime = deltaX / pixelsPerSecond;
    
    if (isDragging) {
      // Move clip
      const newStartTime = Math.max(0, dragStart.startTime + deltaTime);
      const snappedTime = snapToGrid ? snapTime(newStartTime) : newStartTime;
      
      // Update clip position optimistically
      moveClip(clip.id, snappedTime);
    } else if (isResizing) {
      // Resize clip
      if (isResizing === 'start') {
        const newStartTime = Math.max(0, Math.min(clip.endTime - 0.1, dragStart.startTime + deltaTime));
        trimClip(clip.id, newStartTime, clip.endTime);
      } else {
        const newEndTime = Math.max(clip.startTime + 0.1, clip.startTime + clip.duration + deltaTime);
        trimClip(clip.id, clip.startTime, newEndTime);
      }
    }
  }, [
    isDragging,
    isResizing,
    dragStart,
    pixelsPerSecond,
    clip.id,
    clip.startTime,
    clip.endTime,
    clip.duration,
    snapToGrid,
    snapTime,
    moveClip,
    trimClip,
  ]);
  
  // Handle mouse up (end drag/resize)
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setIsResizing(null);
  }, []);
  
  // Add global mouse move/up listeners
  React.useEffect(() => {
    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, isResizing, handleMouseMove, handleMouseUp]);
  
  // Get quality color
  const getQualityColor = () => {
    if (!quality) return '';
    
    if (quality.overall >= 0.8) return 'border-l-quality-excellent';
    if (quality.overall >= 0.6) return 'border-l-quality-good';
    if (quality.overall >= 0.4) return 'border-l-quality-fair';
    return 'border-l-quality-poor';
  };
  
  return (
    <div
      ref={clipRef}
      className={`timeline-clip ${isSelected ? 'selected' : ''} ${getQualityColor()}`}
      style={{
        left: `${clipLeft}px`,
        width: `${clipWidth}px`,
        height: `${trackHeight - 4}px`,
        top: '2px',
        cursor: isDragging ? 'grabbing' : 'grab',
        opacity: isTrackLocked ? 0.5 : 1,
        zIndex: isSelected ? 10 : 1,
      }}
      onMouseDown={handleMouseDown}
      onClick={handleClipClick}
      data-clip-id={clip.id}
      title={`${clip.label} (${clip.duration.toFixed(2)}s)`}
    >
      {/* Clip Content */}
      <div className="clip-content relative w-full h-full overflow-hidden">
        {/* Clip Label */}
        <div className="clip-label absolute top-1 left-2 text-xs text-white font-medium truncate max-w-full">
          {clip.label}
        </div>
        
        {/* Quality Indicator */}
        {quality && (
          <div className="absolute top-1 right-2 flex items-center gap-1">
            <div className={`quality-indicator ${getQualityColor().replace('border-l-', 'bg-')}`} />
            <span className="text-xs text-white opacity-75">
              {(quality.overall * 10).toFixed(1)}
            </span>
          </div>
        )}
        
        {/* Clip Waveform Preview (for audio clips) */}
        {clip.transformations && (
          <div className="absolute bottom-1 left-2 right-2 h-4 bg-black bg-opacity-20 rounded">
            {/* TODO: Add mini waveform */}
          </div>
        )}
      </div>
      
      {/* Resize Handles */}
      {isSelected && !isTrackLocked && (
        <>
          {/* Start resize handle */}
          <div
            className="resize-handle resize-handle-start absolute left-0 top-0 bottom-0 w-2 bg-editor-accent cursor-ew-resize opacity-0 hover:opacity-100 transition-opacity"
            onMouseDown={(e) => handleResizeStart(e, 'start')}
          />
          
          {/* End resize handle */}
          <div
            className="resize-handle resize-handle-end absolute right-0 top-0 bottom-0 w-2 bg-editor-accent cursor-ew-resize opacity-0 hover:opacity-100 transition-opacity"
            onMouseDown={(e) => handleResizeStart(e, 'end')}
          />
        </>
      )}
      
      {/* Selection Outline */}
      {isSelected && (
        <div className="absolute inset-0 border-2 border-editor-accent rounded pointer-events-none" />
      )}
    </div>
  );
};