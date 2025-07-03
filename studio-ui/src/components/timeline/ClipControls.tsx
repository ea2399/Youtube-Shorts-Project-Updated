/**
 * Clip Controls - Phase 4 Essential UI Component
 * Interactive manipulation handles and tools for timeline clips
 */

'use client';

import React, { useState, useCallback } from 'react';
import { TimelineClip } from '@/types';
import { useTimelineStore } from '@/stores/timelineStore';

interface ClipControlsProps {
  clip: TimelineClip;
  isSelected: boolean;
  isVisible: boolean;
  trackHeight: number;
  pixelsPerSecond: number;
  isTrackLocked: boolean;
  onSplit?: (time: number) => void;
  onDelete?: () => void;
  onDuplicate?: () => void;
  className?: string;
}

export const ClipControls: React.FC<ClipControlsProps> = ({
  clip,
  isSelected,
  isVisible,
  trackHeight,
  pixelsPerSecond,
  isTrackLocked,
  onSplit,
  onDelete,
  onDuplicate,
  className = '',
}) => {
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 });
  
  const {
    splitClip,
    deleteClip,
    duplicateClip,
    setCurrentTime,
    snapToGrid,
  } = useTimelineStore();
  
  // Calculate clip dimensions
  const clipWidth = clip.duration * pixelsPerSecond;
  const clipLeft = clip.startTime * pixelsPerSecond;
  
  // Handle resize start indicator
  const handleResizeStart = useCallback((e: React.MouseEvent, direction: 'start' | 'end') => {
    e.stopPropagation();
    // Resize logic is handled by parent TimelineClip component
  }, []);
  
  // Handle split at current playhead
  const handleSplit = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (isTrackLocked) return;
    
    // Calculate split time from mouse position
    const rect = e.currentTarget.getBoundingClientRect();
    const relativeX = e.clientX - rect.left;
    const relativeTime = relativeX / pixelsPerSecond;
    const splitTime = clip.startTime + relativeTime;
    
    // Snap to grid if enabled
    const snappedTime = snapToGrid ? Math.round(splitTime * 10) / 10 : splitTime;
    
    if (snappedTime > clip.startTime && snappedTime < clip.endTime) {
      if (onSplit) {
        onSplit(snappedTime);
      } else {
        splitClip(clip.id, snappedTime);
      }
    }
  }, [clip, isTrackLocked, pixelsPerSecond, snapToGrid, onSplit, splitClip]);
  
  // Handle delete
  const handleDelete = useCallback(() => {
    if (isTrackLocked) return;
    
    if (onDelete) {
      onDelete();
    } else {
      deleteClip(clip.id);
    }
    setShowContextMenu(false);
  }, [clip.id, isTrackLocked, onDelete, deleteClip]);
  
  // Handle duplicate
  const handleDuplicate = useCallback(() => {
    if (isTrackLocked) return;
    
    if (onDuplicate) {
      onDuplicate();
    } else {
      duplicateClip(clip.id);
    }
    setShowContextMenu(false);
  }, [clip.id, isTrackLocked, onDuplicate, duplicateClip]);
  
  // Handle context menu
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setContextMenuPosition({ x: e.clientX, y: e.clientY });
    setShowContextMenu(true);
  }, []);
  
  // Handle set playhead to clip start
  const handleGoToStart = useCallback(() => {
    setCurrentTime(clip.startTime);
    setShowContextMenu(false);
  }, [clip.startTime, setCurrentTime]);
  
  // Handle set playhead to clip end
  const handleGoToEnd = useCallback(() => {
    setCurrentTime(clip.endTime);
    setShowContextMenu(false);
  }, [clip.endTime, setCurrentTime]);
  
  // Don't render if not visible or selected
  if (!isVisible || !isSelected) {
    return null;
  }
  
  return (
    <>
      {/* Resize handles */}
      <div className={`clip-controls absolute inset-0 pointer-events-none ${className}`}>
        {/* Left resize handle */}
        <div
          className={`
            absolute left-0 top-0 w-2 h-full bg-editor-accent cursor-ew-resize pointer-events-auto
            hover:bg-editor-accent-hover transition-colors
            ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
          `}
          onMouseDown={(e) => handleResizeStart(e, 'start')}
          title="Resize clip start"
        >
          <div className="absolute left-0.5 top-1/2 transform -translate-y-1/2 w-1 h-4 bg-white rounded-sm opacity-70" />
        </div>
        
        {/* Right resize handle */}
        <div
          className={`
            absolute right-0 top-0 w-2 h-full bg-editor-accent cursor-ew-resize pointer-events-auto
            hover:bg-editor-accent-hover transition-colors
            ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
          `}
          onMouseDown={(e) => handleResizeStart(e, 'end')}
          title="Resize clip end"
        >
          <div className="absolute right-0.5 top-1/2 transform -translate-y-1/2 w-1 h-4 bg-white rounded-sm opacity-70" />
        </div>
        
        {/* Split handle (center) */}
        <div
          className={`
            absolute left-1/2 top-0 transform -translate-x-1/2 w-1 h-full bg-editor-warning cursor-col-resize pointer-events-auto
            hover:bg-editor-warning-hover transition-colors opacity-0 hover:opacity-100
            ${isTrackLocked ? 'cursor-not-allowed' : ''}
          `}
          onClick={handleSplit}
          title="Split clip at this position"
        >
          <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-editor-warning rounded-full border border-white" />
        </div>
        
        {/* Clip actions toolbar */}
        <div className="absolute -top-8 left-0 flex items-center gap-1 pointer-events-auto">
          {/* Split button */}
          <button
            className={`
              w-6 h-6 bg-editor-surface border border-editor-border rounded text-xs text-editor-text-primary
              hover:bg-editor-border transition-colors flex items-center justify-center
              ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
            `}
            onClick={handleSplit}
            disabled={isTrackLocked}
            title="Split clip"
          >
            ✂
          </button>
          
          {/* Delete button */}
          <button
            className={`
              w-6 h-6 bg-editor-surface border border-editor-border rounded text-xs text-editor-error
              hover:bg-editor-error hover:text-white transition-colors flex items-center justify-center
              ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
            `}
            onClick={handleDelete}
            disabled={isTrackLocked}
            title="Delete clip"
          >
            ✕
          </button>
          
          {/* Duplicate button */}
          <button
            className={`
              w-6 h-6 bg-editor-surface border border-editor-border rounded text-xs text-editor-text-primary
              hover:bg-editor-border transition-colors flex items-center justify-center
              ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
            `}
            onClick={handleDuplicate}
            disabled={isTrackLocked}
            title="Duplicate clip"
          >
            ⧉
          </button>
          
          {/* More options button */}
          <button
            className="w-6 h-6 bg-editor-surface border border-editor-border rounded text-xs text-editor-text-primary hover:bg-editor-border transition-colors flex items-center justify-center"
            onContextMenu={handleContextMenu}
            onClick={handleContextMenu}
            title="More options"
          >
            ⋯
          </button>
        </div>
        
        {/* Selection outline */}
        <div className="absolute inset-0 border-2 border-editor-accent rounded pointer-events-none" />
      </div>
      
      {/* Context menu */}
      {showContextMenu && (
        <>
          {/* Backdrop to close menu */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowContextMenu(false)}
          />
          
          {/* Menu */}
          <div
            className="fixed z-50 bg-editor-surface border border-editor-border rounded-lg shadow-lg py-1 min-w-32"
            style={{
              left: contextMenuPosition.x,
              top: contextMenuPosition.y,
            }}
          >
            <button
              className="w-full px-3 py-2 text-left text-sm text-editor-text-primary hover:bg-editor-border transition-colors"
              onClick={handleGoToStart}
            >
              Go to Start
            </button>
            
            <button
              className="w-full px-3 py-2 text-left text-sm text-editor-text-primary hover:bg-editor-border transition-colors"
              onClick={handleGoToEnd}
            >
              Go to End
            </button>
            
            <hr className="my-1 border-editor-border" />
            
            <button
              className={`
                w-full px-3 py-2 text-left text-sm text-editor-text-primary hover:bg-editor-border transition-colors
                ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
              `}
              onClick={handleSplit}
              disabled={isTrackLocked}
            >
              Split Clip
            </button>
            
            <button
              className={`
                w-full px-3 py-2 text-left text-sm text-editor-text-primary hover:bg-editor-border transition-colors
                ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
              `}
              onClick={handleDuplicate}
              disabled={isTrackLocked}
            >
              Duplicate Clip
            </button>
            
            <hr className="my-1 border-editor-border" />
            
            <button
              className={`
                w-full px-3 py-2 text-left text-sm text-editor-error hover:bg-editor-error hover:text-white transition-colors
                ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
              `}
              onClick={handleDelete}
              disabled={isTrackLocked}
            >
              Delete Clip
            </button>
          </div>
        </>
      )}
    </>
  );
};

// Simplified clip control for small clips
export const MiniClipControls: React.FC<{
  clip: TimelineClip;
  isSelected: boolean;
  isTrackLocked: boolean;
  onSplit?: () => void;
  onDelete?: () => void;
}> = ({ clip, isSelected, isTrackLocked, onSplit, onDelete }) => {
  const { splitClip, deleteClip } = useTimelineStore();
  
  const handleSplit = useCallback(() => {
    if (isTrackLocked) return;
    if (onSplit) {
      onSplit();
    } else {
      splitClip(clip.id, clip.startTime + clip.duration / 2);
    }
  }, [clip, isTrackLocked, onSplit, splitClip]);
  
  const handleDelete = useCallback(() => {
    if (isTrackLocked) return;
    if (onDelete) {
      onDelete();
    } else {
      deleteClip(clip.id);
    }
  }, [clip.id, isTrackLocked, onDelete, deleteClip]);
  
  if (!isSelected) return null;
  
  return (
    <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 flex items-center gap-1">
      <button
        className={`
          w-5 h-5 bg-editor-surface border border-editor-border rounded text-xs text-editor-text-primary
          hover:bg-editor-border transition-colors flex items-center justify-center
          ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
        `}
        onClick={handleSplit}
        disabled={isTrackLocked}
        title="Split"
      >
        ✂
      </button>
      
      <button
        className={`
          w-5 h-5 bg-editor-surface border border-editor-border rounded text-xs text-editor-error
          hover:bg-editor-error hover:text-white transition-colors flex items-center justify-center
          ${isTrackLocked ? 'cursor-not-allowed opacity-50' : ''}
        `}
        onClick={handleDelete}
        disabled={isTrackLocked}
        title="Delete"
      >
        ✕
      </button>
    </div>
  );
};

// Keyboard shortcut help overlay
export const ClipControlsHelp: React.FC<{ isVisible: boolean; onClose: () => void }> = ({
  isVisible,
  onClose,
}) => {
  if (!isVisible) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-editor-surface border border-editor-border rounded-lg p-6 max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-editor-text-primary">Clip Controls</h3>
          <button
            onClick={onClose}
            className="text-editor-text-secondary hover:text-editor-text-primary"
          >
            ✕
          </button>
        </div>
        
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">Click clip</span>
            <span className="text-editor-text-primary">Select</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">Shift + Click</span>
            <span className="text-editor-text-primary">Multi-select</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">Drag edges</span>
            <span className="text-editor-text-primary">Resize</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">Drag center</span>
            <span className="text-editor-text-primary">Move</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">Right click</span>
            <span className="text-editor-text-primary">Context menu</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">S key</span>
            <span className="text-editor-text-primary">Split at playhead</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">Delete key</span>
            <span className="text-editor-text-primary">Delete selected</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-editor-text-secondary">Ctrl + D</span>
            <span className="text-editor-text-primary">Duplicate</span>
          </div>
        </div>
      </div>
    </div>
  );
};