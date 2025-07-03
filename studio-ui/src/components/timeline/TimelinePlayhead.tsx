/**
 * Timeline Playhead - Phase 4 Core Component
 * Current time indicator with scrubbing support
 */

'use client';

import React, { useCallback, useState } from 'react';
import { usePlayerStore } from '@/stores/playerStore';
import { useTimelineStore } from '@/stores/timelineStore';

interface TimelinePlayheadProps {
  currentTime: number;
  pixelsPerSecond: number;
  height: number;
}

export const TimelinePlayhead: React.FC<TimelinePlayheadProps> = ({
  currentTime,
  pixelsPerSecond,
  height,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const { seekTo } = usePlayerStore();
  const { setCurrentTime, duration, pixelsToTime } = useTimelineStore();
  
  // Calculate playhead position
  const playheadPosition = currentTime * pixelsPerSecond;
  
  // Handle playhead drag start
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);
  
  // Handle playhead dragging
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    
    // Get timeline container to calculate relative position
    const timelineContainer = document.querySelector('.timeline-container') as HTMLElement;
    if (!timelineContainer) return;
    
    const rect = timelineContainer.getBoundingClientRect();
    const relativeX = e.clientX - rect.left + timelineContainer.scrollLeft;
    const newTime = Math.max(0, Math.min(duration, pixelsToTime(relativeX)));
    
    // Update both player and timeline time
    setCurrentTime(newTime);
    seekTo(newTime);
  }, [isDragging, duration, pixelsToTime, setCurrentTime, seekTo]);
  
  // Handle drag end
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);
  
  // Add global mouse listeners when dragging
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);
  
  return (
    <div
      className="timeline-playhead"
      style={{
        left: `${playheadPosition}px`,
        height: `${height}px`,
        cursor: isDragging ? 'grabbing' : 'grab',
        transform: isDragging ? 'scaleY(1.1)' : 'scaleY(1)',
        transition: isDragging ? 'none' : 'transform 0.1s ease-out',
      }}
      onMouseDown={handleMouseDown}
      role="slider"
      aria-label="Timeline scrubber"
      aria-valuemin={0}
      aria-valuemax={duration}
      aria-valuenow={currentTime}
      tabIndex={0}
    >
      {/* Playhead line */}
      <div className="absolute inset-0 bg-timeline-playhead" />
      
      {/* Playhead handle */}
      <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1">
        <div className="w-3 h-3 bg-timeline-playhead rounded-full border-2 border-editor-bg shadow-lg" />
      </div>
      
      {/* Time tooltip when dragging */}
      {isDragging && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-editor-bg text-editor-text-primary text-xs rounded shadow-lg border border-editor-border whitespace-nowrap">
          {formatTime(currentTime)}
        </div>
      )}
    </div>
  );
};

// Helper function to format time
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}