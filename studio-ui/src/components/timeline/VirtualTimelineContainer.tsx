/**
 * Virtual Timeline Container - Phase 4D
 * Optimized timeline rendering with virtual scrolling
 */

'use client';

import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { 
  useVirtualTimeline, 
  VirtualTimelineConfig, 
  TimelineItem,
  VirtualItem 
} from '@/lib/virtual-timeline';
import { useUndoRedo, UndoRedoManager } from '@/lib/undo-redo';

interface VirtualTimelineContainerProps {
  items: TimelineItem[];
  duration: number;
  className?: string;
  onItemSelect?: (itemId: string) => void;
  onItemMove?: (itemId: string, newStartTime: number) => void;
  onTimelineClick?: (time: number) => void;
}

export const VirtualTimelineContainer: React.FC<VirtualTimelineContainerProps> = ({
  items,
  duration,
  className = '',
  onItemSelect,
  onItemMove,
  onTimelineClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 800, height: 400 });
  const [zoom, setZoom] = useState(50); // pixels per second
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [dragState, setDragState] = useState<{
    isDragging: boolean;
    itemId: string | null;
    startX: number;
    startTime: number;
  }>({ isDragging: false, itemId: null, startX: 0, startTime: 0 });

  // Undo/Redo manager
  const [undoRedoManager] = useState(() => new UndoRedoManager());
  const undoRedo = useUndoRedo(undoRedoManager);

  // Virtual timeline configuration
  const config: VirtualTimelineConfig = useMemo(() => ({
    containerWidth: containerSize.width,
    containerHeight: containerSize.height,
    totalDuration: duration,
    pixelsPerSecond: zoom,
    trackHeight: 80,
    visibleTracks: Math.floor(containerSize.height / 80),
    overscanCount: 2,
  }), [containerSize, duration, zoom]);

  // Virtual timeline hook
  const {
    manager,
    visibleItems,
    tracksInfo,
    viewport,
    totalWidth,
    totalHeight,
    handleScroll,
    timeToPixel,
    pixelToTime,
    getItemAtPosition,
    centerOnTime,
    setZoom: setManagerZoom,
  } = useVirtualTimeline(config, items);

  // Resize observer for container
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setContainerSize({ width, height });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Handle scroll events
  const handleScrollEvent = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    handleScroll(target.scrollLeft, target.scrollTop);
  }, [handleScroll]);

  // Handle mouse down for item selection and dragging
  const handleMouseDown = useCallback((e: React.MouseEvent, item: VirtualItem) => {
    e.preventDefault();
    e.stopPropagation();

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left + (scrollRef.current?.scrollLeft || 0);
    
    setSelectedItems(new Set([item.id]));
    onItemSelect?.(item.id);

    setDragState({
      isDragging: true,
      itemId: item.id,
      startX: x,
      startTime: item.startTime,
    });

    // Prevent text selection
    document.body.style.userSelect = 'none';
  }, [onItemSelect]);

  // Handle mouse move for dragging
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragState.isDragging || !dragState.itemId) return;

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const currentX = e.clientX - rect.left + (scrollRef.current?.scrollLeft || 0);
    const deltaX = currentX - dragState.startX;
    const deltaTime = pixelToTime(deltaX) - pixelToTime(0);
    const newStartTime = Math.max(0, dragState.startTime + deltaTime);

    // Visual feedback during drag (this would update a preview state)
    // For now, we'll just update immediately
    onItemMove?.(dragState.itemId, newStartTime);
  }, [dragState, pixelToTime, onItemMove]);

  // Handle mouse up to finish dragging
  const handleMouseUp = useCallback(() => {
    if (dragState.isDragging && dragState.itemId) {
      // Create undo command for the move operation
      // This would be implemented with actual state management
      console.log('Move operation completed for item:', dragState.itemId);
    }

    setDragState({
      isDragging: false,
      itemId: null,
      startX: 0,
      startTime: 0,
    });

    document.body.style.userSelect = '';
  }, [dragState]);

  // Handle timeline click
  const handleTimelineClick = useCallback((e: React.MouseEvent) => {
    if (dragState.isDragging) return;

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left + (scrollRef.current?.scrollLeft || 0);
    const time = pixelToTime(x);

    onTimelineClick?.(time);
    setSelectedItems(new Set()); // Clear selection
  }, [dragState.isDragging, pixelToTime, onTimelineClick]);

  // Handle zoom
  const handleZoom = useCallback((delta: number, centerX?: number) => {
    const newZoom = Math.max(10, Math.min(500, zoom + delta));
    
    let centerTime: number | undefined;
    if (centerX !== undefined) {
      centerTime = pixelToTime(centerX + (scrollRef.current?.scrollLeft || 0));
    }

    setZoom(newZoom);
    setManagerZoom(newZoom, centerTime);
  }, [zoom, pixelToTime, setManagerZoom]);

  // Handle wheel events for zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const centerX = e.clientX - rect.left;
      const zoomDelta = -e.deltaY * 0.1;
      handleZoom(zoomDelta, centerX);
    }
  }, [handleZoom]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target !== document.body) return;

      switch (e.key) {
        case 'z':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            if (e.shiftKey) {
              undoRedo.redo();
            } else {
              undoRedo.undo();
            }
          }
          break;
        case 'Delete':
        case 'Backspace':
          if (selectedItems.size > 0) {
            e.preventDefault();
            // Delete selected items
            console.log('Delete items:', Array.from(selectedItems));
          }
          break;
        case 'a':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            // Select all items
            setSelectedItems(new Set(items.map(item => item.id)));
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedItems, items, undoRedo]);

  // Global mouse events for dragging
  useEffect(() => {
    if (!dragState.isDragging) return;

    const handleGlobalMouseMove = (e: MouseEvent) => {
      // Convert to React mouse event for consistency
      const syntheticEvent = {
        clientX: e.clientX,
        clientY: e.clientY,
      } as React.MouseEvent;
      handleMouseMove(syntheticEvent);
    };

    const handleGlobalMouseUp = () => {
      handleMouseUp();
    };

    document.addEventListener('mousemove', handleGlobalMouseMove);
    document.addEventListener('mouseup', handleGlobalMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleGlobalMouseMove);
      document.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [dragState.isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div 
      ref={containerRef}
      className={`virtual-timeline-container relative overflow-hidden bg-editor-background border border-editor-border ${className}`}
      onWheel={handleWheel}
    >
      {/* Timeline Header */}
      <div className="timeline-header h-8 bg-editor-surface border-b border-editor-border flex items-center px-4">
        <div className="flex items-center gap-4">
          <span className="text-sm text-editor-text-secondary">
            Zoom: {Math.round(zoom)}px/s
          </span>
          <span className="text-sm text-editor-text-secondary">
            Duration: {Math.round(duration)}s
          </span>
          {undoRedo.canUndo && (
            <button
              onClick={() => undoRedo.undo()}
              className="text-xs px-2 py-1 bg-editor-button hover:bg-editor-button-hover rounded text-editor-text-primary"
              title={`Undo: ${undoRedo.undoDescription}`}
            >
              Undo
            </button>
          )}
          {undoRedo.canRedo && (
            <button
              onClick={() => undoRedo.redo()}
              className="text-xs px-2 py-1 bg-editor-button hover:bg-editor-button-hover rounded text-editor-text-primary"
              title={`Redo: ${undoRedo.redoDescription}`}
            >
              Redo
            </button>
          )}
        </div>
      </div>

      {/* Scrollable Timeline Content */}
      <div
        ref={scrollRef}
        className="timeline-scroll flex-1 overflow-auto"
        style={{ height: 'calc(100% - 2rem)' }}
        onScroll={handleScrollEvent}
        onClick={handleTimelineClick}
      >
        {/* Timeline Content */}
        <div
          className="timeline-content relative"
          style={{
            width: totalWidth,
            height: totalHeight,
            minWidth: containerSize.width,
            minHeight: containerSize.height,
          }}
        >
          {/* Track Backgrounds */}
          {tracksInfo.map((track) => (
            <div
              key={track.id}
              className="track-background absolute w-full border-b border-editor-border/50"
              style={{
                top: track.y,
                height: track.height,
                backgroundColor: track.index % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
              }}
            />
          ))}

          {/* Time Grid */}
          <TimeGrid
            viewport={viewport}
            config={config}
            timeToPixel={timeToPixel}
          />

          {/* Timeline Items */}
          {visibleItems.map((item) => (
            <TimelineItemComponent
              key={item.id}
              item={item}
              isSelected={selectedItems.has(item.id)}
              onMouseDown={(e) => handleMouseDown(e, item)}
            />
          ))}

          {/* Playhead */}
          <Playhead
            currentTime={0} // This would come from player state
            timeToPixel={timeToPixel}
            height={totalHeight}
          />
        </div>
      </div>
    </div>
  );
};

/**
 * Time grid component
 */
const TimeGrid: React.FC<{
  viewport: any;
  config: VirtualTimelineConfig;
  timeToPixel: (time: number) => number;
}> = ({ viewport, config, timeToPixel }) => {
  const gridLines = [];
  const majorInterval = 10; // Major grid lines every 10 seconds
  const minorInterval = 1;  // Minor grid lines every 1 second

  // Major grid lines
  for (let time = 0; time <= config.totalDuration; time += majorInterval) {
    if (time >= viewport.startTime && time <= viewport.endTime) {
      const x = timeToPixel(time);
      gridLines.push(
        <div
          key={`major-${time}`}
          className="absolute top-0 w-px bg-editor-border opacity-60"
          style={{ left: x, height: '100%' }}
        />
      );
      
      // Time label
      gridLines.push(
        <div
          key={`label-${time}`}
          className="absolute top-2 text-xs text-editor-text-muted pointer-events-none"
          style={{ left: x + 4 }}
        >
          {Math.round(time)}s
        </div>
      );
    }
  }

  // Minor grid lines
  for (let time = 0; time <= config.totalDuration; time += minorInterval) {
    if (time % majorInterval !== 0 && time >= viewport.startTime && time <= viewport.endTime) {
      const x = timeToPixel(time);
      gridLines.push(
        <div
          key={`minor-${time}`}
          className="absolute top-0 w-px bg-editor-border opacity-20"
          style={{ left: x, height: '100%' }}
        />
      );
    }
  }

  return <>{gridLines}</>;
};

/**
 * Timeline item component
 */
const TimelineItemComponent: React.FC<{
  item: VirtualItem;
  isSelected: boolean;
  onMouseDown: (e: React.MouseEvent) => void;
}> = ({ item, isSelected, onMouseDown }) => {
  return (
    <div
      className={`absolute cursor-pointer transition-all ${
        isSelected 
          ? 'ring-2 ring-blue-500 bg-blue-500/20' 
          : 'bg-green-500/80 hover:bg-green-500'
      }`}
      style={{
        left: item.x,
        top: item.y + 4,
        width: item.width,
        height: item.height - 8,
        borderRadius: '4px',
        minWidth: '20px',
      }}
      onMouseDown={onMouseDown}
    >
      <div className="p-2 text-xs text-white font-medium truncate">
        Clip {item.id.slice(-4)}
      </div>
      
      {/* Resize handles */}
      <div className="absolute left-0 top-0 w-2 h-full cursor-w-resize bg-transparent hover:bg-white/20" />
      <div className="absolute right-0 top-0 w-2 h-full cursor-e-resize bg-transparent hover:bg-white/20" />
    </div>
  );
};

/**
 * Playhead component
 */
const Playhead: React.FC<{
  currentTime: number;
  timeToPixel: (time: number) => number;
  height: number;
}> = ({ currentTime, timeToPixel, height }) => {
  const x = timeToPixel(currentTime);

  return (
    <div
      className="absolute top-0 pointer-events-none z-10"
      style={{ left: x, height }}
    >
      <div className="w-px bg-red-500 h-full" />
      <div className="absolute -top-1 -left-2 w-4 h-4 bg-red-500 rounded-full border-2 border-white" />
    </div>
  );
};