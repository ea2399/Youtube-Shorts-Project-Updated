/**
 * Timeline Ruler - Phase 4 Core Component
 * Time markings and ruler for timeline navigation
 */

'use client';

import React, { useMemo } from 'react';

interface TimelineRulerProps {
  width: number;
  pixelsPerSecond: number;
  currentTime: number;
  duration: number;
  snapToGrid: boolean;
}

export const TimelineRuler: React.FC<TimelineRulerProps> = ({
  width,
  pixelsPerSecond,
  currentTime,
  duration,
  snapToGrid,
}) => {
  // Calculate tick intervals based on zoom level
  const tickIntervals = useMemo(() => {
    const pixelsPerMinute = pixelsPerSecond * 60;
    
    if (pixelsPerMinute > 300) {
      // Very zoomed in - show 1 second intervals
      return { major: 10, minor: 1 }; // Major every 10s, minor every 1s
    } else if (pixelsPerMinute > 150) {
      // Moderately zoomed in - show 5 second intervals
      return { major: 30, minor: 5 }; // Major every 30s, minor every 5s
    } else if (pixelsPerMinute > 60) {
      // Normal zoom - show 10 second intervals
      return { major: 60, minor: 10 }; // Major every 1min, minor every 10s
    } else {
      // Zoomed out - show 30 second intervals
      return { major: 300, minor: 30 }; // Major every 5min, minor every 30s
    }
  }, [pixelsPerSecond]);
  
  // Generate tick marks
  const ticks = useMemo(() => {
    const ticks: Array<{ time: number; type: 'major' | 'minor'; label?: string }> = [];
    
    // Add minor ticks
    for (let time = 0; time <= duration; time += tickIntervals.minor) {
      const isMajor = time % tickIntervals.major === 0;
      
      ticks.push({
        time,
        type: isMajor ? 'major' : 'minor',
        label: isMajor ? formatTime(time) : undefined,
      });
    }
    
    return ticks;
  }, [duration, tickIntervals]);
  
  // Handle ruler click to seek
  const handleRulerClick = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickTime = clickX / pixelsPerSecond;
    
    // Update timeline time
    const timelineStore = require('@/stores/timelineStore').useTimelineStore;
    const playerStore = require('@/stores/playerStore').usePlayerStore;
    
    timelineStore.getState().setCurrentTime(clickTime);
    playerStore.getState().seekTo(clickTime);
  };
  
  return (
    <div 
      className="timeline-ruler relative h-8 bg-editor-surface border-b border-editor-border cursor-pointer select-none"
      style={{ width: `${width}px` }}
      onClick={handleRulerClick}
    >
      {/* Ruler background */}
      <div className="absolute inset-0" />
      
      {/* Time ticks */}
      {ticks.map(({ time, type, label }) => {
        const x = time * pixelsPerSecond;
        const isMajor = type === 'major';
        
        return (
          <div key={time} className="absolute top-0 bottom-0 flex flex-col">
            {/* Tick line */}
            <div
              className={`bg-editor-text-secondary ${
                isMajor ? 'w-px h-6' : 'w-px h-3'
              }`}
              style={{ left: `${x}px` }}
            />
            
            {/* Time label */}
            {label && (
              <div
                className="absolute top-6 text-xs text-editor-text-secondary transform -translate-x-1/2 whitespace-nowrap"
                style={{ left: `${x}px` }}
              >
                {label}
              </div>
            )}
          </div>
        );
      })}
      
      {/* Current time indicator */}
      <div
        className="absolute top-0 bottom-0 w-px bg-timeline-playhead z-10"
        style={{ left: `${currentTime * pixelsPerSecond}px` }}
      />
      
      {/* Grid lines indicator */}
      {snapToGrid && (
        <div className="absolute top-0 right-2 text-xs text-editor-text-secondary bg-editor-bg px-1 rounded">
          Grid: {tickIntervals.minor}s
        </div>
      )}
    </div>
  );
};

// Helper function to format time for ruler labels
function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  } else {
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
}