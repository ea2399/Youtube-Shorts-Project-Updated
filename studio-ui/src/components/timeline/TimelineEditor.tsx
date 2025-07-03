/**
 * Timeline Editor - Phase 4 Core Component
 * Main timeline editing interface with virtualization and performance optimization
 */

'use client';

import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useTimelineStore, useTimelineRenderWindow } from '@/stores/timelineStore';
import { usePlayerStore } from '@/stores/playerStore';
import { TimelineTrack } from './TimelineTrack';
import { TimelinePlayhead } from './TimelinePlayhead';
import { TimelineRuler } from './TimelineRuler';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

interface TimelineEditorProps {
  className?: string;
  height?: number;
}

export const TimelineEditor: React.FC<TimelineEditorProps> = ({
  className = '',
  height = 300,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(1000);
  
  // Store state
  const {
    tracks,
    currentTime,
    duration,
    zoom,
    pixelsPerSecond,
    snapToGrid,
    setContainerWidth: setStoreContainerWidth,
    updateRenderWindow,
    timeToPixels,
    pixelsToTime,
  } = useTimelineStore();
  
  const renderWindow = useTimelineRenderWindow();
  const { isPlaying, setPlaying } = usePlayerStore();
  
  // Update container width on resize
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const width = containerRef.current.clientWidth;
        setContainerWidth(width);
        setStoreContainerWidth(width);
      }
    };
    
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, [setStoreContainerWidth]);
  
  // Update render window when scrolling or zooming
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const scrollLeft = e.currentTarget.scrollLeft;
    const viewportWidth = e.currentTarget.clientWidth;
    
    const startTime = pixelsToTime(scrollLeft);
    const endTime = pixelsToTime(scrollLeft + viewportWidth);
    
    updateRenderWindow(startTime, endTime);
  }, [pixelsToTime, updateRenderWindow]);
  
  // Timeline click to seek
  const handleTimelineClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left + containerRef.current.scrollLeft;
    const clickTime = pixelsToTime(clickX);
    
    // Update player time and timeline current time
    usePlayerStore.getState().seekTo(clickTime);
    useTimelineStore.getState().setCurrentTime(clickTime);
  }, [pixelsToTime]);
  
  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: ' ',
      action: 'playPause',
      description: 'Play/Pause',
      handler: () => setPlaying(!isPlaying),
    },
    {
      key: 'Home',
      action: 'seekStart',
      description: 'Seek to start',
      handler: () => {
        usePlayerStore.getState().seekTo(0);
        useTimelineStore.getState().setCurrentTime(0);
      },
    },
    {
      key: 'End',
      action: 'seekEnd',
      description: 'Seek to end',
      handler: () => {
        usePlayerStore.getState().seekTo(duration);
        useTimelineStore.getState().setCurrentTime(duration);
      },
    },
  ]);
  
  // Calculate timeline width based on duration and zoom
  const timelineWidth = Math.max(containerWidth, timeToPixels(duration));
  
  return (
    <div className={`timeline-editor ${className}`}>
      {/* Timeline Ruler */}
      <TimelineRuler 
        width={timelineWidth}
        pixelsPerSecond={pixelsPerSecond}
        currentTime={currentTime}
        duration={duration}
        snapToGrid={snapToGrid}
      />
      
      {/* Main Timeline Container */}
      <div 
        ref={containerRef}
        className="timeline-container"
        style={{ height: `${height}px` }}
        onScroll={handleScroll}
        onClick={handleTimelineClick}
        role="application"
        aria-label="Video Timeline Editor"
        tabIndex={0}
      >
        {/* Timeline Content */}
        <div 
          className="timeline-content"
          style={{ 
            width: `${timelineWidth}px`,
            position: 'relative',
            height: '100%'
          }}
        >
          {/* Playhead */}
          <TimelinePlayhead 
            currentTime={currentTime}
            pixelsPerSecond={pixelsPerSecond}
            height={height}
          />
          
          {/* Tracks */}
          <div className="timeline-tracks">
            {tracks.map((track, index) => (
              <TimelineTrack
                key={track.id}
                track={track}
                index={index}
                pixelsPerSecond={pixelsPerSecond}
                renderWindow={renderWindow}
              />
            ))}
          </div>
          
          {/* Grid Lines (if snap to grid is enabled) */}
          {snapToGrid && (
            <div className="timeline-grid">
              {Array.from({ length: Math.ceil(duration) }, (_, i) => {
                const x = timeToPixels(i);
                return (
                  <div
                    key={i}
                    className="timeline-grid-line"
                    style={{
                      position: 'absolute',
                      left: `${x}px`,
                      top: 0,
                      bottom: 0,
                      width: '1px',
                      backgroundColor: 'rgba(255, 255, 255, 0.1)',
                      pointerEvents: 'none',
                    }}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
      
      {/* Timeline Controls */}
      <div className="timeline-controls flex items-center gap-4 p-2 bg-editor-surface border-t border-editor-border">
        <div className="flex items-center gap-2">
          <span className="text-sm text-editor-text-secondary">Zoom:</span>
          <input
            type="range"
            min="0.1"
            max="5"
            step="0.1"
            value={zoom}
            onChange={(e) => useTimelineStore.getState().setZoom(parseFloat(e.target.value))}
            className="w-24"
          />
          <span className="text-sm text-editor-text-secondary">{zoom.toFixed(1)}x</span>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-sm text-editor-text-secondary">Time:</span>
          <span className="text-sm font-mono text-editor-text-primary">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-sm text-editor-text-secondary">
            <input
              type="checkbox"
              checked={snapToGrid}
              onChange={(e) => useTimelineStore.getState().setSnapToGrid(e.target.checked)}
              className="w-4 h-4"
            />
            Snap to Grid
          </label>
        </div>
      </div>
    </div>
  );
};

// Helper function to format time in MM:SS format
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}