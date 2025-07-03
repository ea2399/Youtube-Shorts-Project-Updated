/**
 * Timeline Track - Phase 4 Core Component
 * Individual track rendering with clips and drag-and-drop support
 */

'use client';

import React, { useMemo } from 'react';
import { TimelineTrack as TimelineTrackType, TimelineClip, RenderWindow } from '@/types';
import { useTimelineStore } from '@/stores/timelineStore';
import { TimelineClipComponent } from './TimelineClip';

interface TimelineTrackProps {
  track: TimelineTrackType;
  index: number;
  pixelsPerSecond: number;
  renderWindow: RenderWindow;
}

export const TimelineTrack: React.FC<TimelineTrackProps> = ({
  track,
  index,
  pixelsPerSecond,
  renderWindow,
}) => {
  const { clips } = useTimelineStore();
  
  // Filter clips for this track within render window (virtualization)
  const visibleClips = useMemo(() => {
    return clips.filter(clip => 
      clip.trackId === track.id &&
      clip.startTime < renderWindow.endTime &&
      clip.endTime > renderWindow.startTime
    );
  }, [clips, track.id, renderWindow]);
  
  // Handle track click for adding clips or seeking
  const handleTrackClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Prevent clicks on clips from bubbling up
    if (e.target !== e.currentTarget) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickTime = clickX / pixelsPerSecond;
    
    // If holding shift, create new clip at click position
    if (e.shiftKey) {
      // TODO: Implement add clip functionality
      console.log('Add clip at', clickTime);
    }
  };
  
  // Get track type specific styling
  const getTrackTypeClasses = () => {
    switch (track.type) {
      case 'video':
        return 'border-l-4 border-l-blue-500';
      case 'audio':
        return 'border-l-4 border-l-green-500';
      case 'subtitle':
        return 'border-l-4 border-l-yellow-500';
      case 'marker':
        return 'border-l-4 border-l-purple-500';
      default:
        return 'border-l-4 border-l-gray-500';
    }
  };
  
  return (
    <div 
      className={`timeline-track ${getTrackTypeClasses()} ${!track.visible ? 'opacity-50' : ''}`}
      style={{ 
        height: `${track.height}px`,
        minHeight: '40px'
      }}
      onClick={handleTrackClick}
      data-track-id={track.id}
      data-track-type={track.type}
    >
      {/* Track Header */}
      <div className="track-header absolute left-0 top-0 bottom-0 w-32 bg-editor-surface border-r border-editor-border flex items-center px-3 z-10">
        <div className="flex items-center gap-2 w-full">
          {/* Track Visibility Toggle */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              useTimelineStore.getState().updateTrack(track.id, { visible: !track.visible });
            }}
            className="w-4 h-4 flex items-center justify-center text-editor-text-secondary hover:text-editor-text-primary"
            title={track.visible ? 'Hide track' : 'Show track'}
          >
            {track.visible ? '👁' : '👁‍🗨'}
          </button>
          
          {/* Track Name */}
          <span className="text-sm text-editor-text-primary truncate flex-1">
            {track.name}
          </span>
          
          {/* Track Lock Toggle */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              useTimelineStore.getState().updateTrack(track.id, { locked: !track.locked });
            }}
            className="w-4 h-4 flex items-center justify-center text-editor-text-secondary hover:text-editor-text-primary"
            title={track.locked ? 'Unlock track' : 'Lock track'}
          >
            {track.locked ? '🔒' : '🔓'}
          </span>
        </div>
      </div>
      
      {/* Track Content Area */}
      <div 
        className="track-content relative ml-32 h-full"
        style={{ pointerEvents: track.locked ? 'none' : 'auto' }}
      >
        {/* Clips */}
        {visibleClips.map((clip) => (
          <TimelineClipComponent
            key={clip.id}
            clip={clip}
            trackHeight={track.height}
            pixelsPerSecond={pixelsPerSecond}
            isTrackLocked={track.locked}
          />
        ))}
        
        {/* Track Type Specific Content */}
        {track.type === 'audio' && (
          <div className="track-waveform absolute inset-0 pointer-events-none">
            {/* TODO: Add waveform visualization */}
          </div>
        )}
        
        {track.type === 'marker' && (
          <div className="track-markers absolute inset-0 pointer-events-none">
            {/* TODO: Add marker visualization */}
          </div>
        )}
      </div>
      
      {/* Drop Zone Indicator */}
      <div className="absolute inset-0 pointer-events-none opacity-0 bg-editor-accent transition-opacity duration-200" />
    </div>
  );
};