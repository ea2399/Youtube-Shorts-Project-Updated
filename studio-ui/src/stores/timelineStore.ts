/**
 * Timeline Store - Phase 4
 * Zustand store for timeline editor state management with virtualization
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { 
  TimelineState, 
  TimelineClip, 
  TimelineTrack, 
  TimelineMarker, 
  RenderWindow,
  EditOperation,
  QualityMetrics 
} from '@/types';

interface TimelineStore extends TimelineState {
  // Tracks and clips
  tracks: TimelineTrack[];
  clips: TimelineClip[];
  markers: TimelineMarker[];
  
  // Selection and editing
  selectedClips: string[];
  clipboard: TimelineClip[];
  editHistory: EditOperation[];
  editIndex: number;
  
  // Virtualization
  renderWindow: RenderWindow;
  pixelsPerSecond: number;
  containerWidth: number;
  
  // Quality metrics
  qualityMetrics: Record<string, QualityMetrics>;
  
  // Actions - Basic state
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setPlaybackState: (state: 'playing' | 'paused' | 'loading' | 'error') => void;
  setSelectedClip: (clipId: string | null) => void;
  setZoom: (zoom: number) => void;
  setViewport: (start: number, end: number) => void;
  
  // Actions - Timeline management
  addTrack: (track: Omit<TimelineTrack, 'id'>) => void;
  removeTrack: (trackId: string) => void;
  updateTrack: (trackId: string, updates: Partial<TimelineTrack>) => void;
  
  // Actions - Clip management
  addClip: (clip: Omit<TimelineClip, 'id'>) => void;
  removeClip: (clipId: string) => void;
  updateClip: (clipId: string, updates: Partial<TimelineClip>) => void;
  moveClip: (clipId: string, newStartTime: number, newTrackId?: string) => void;
  splitClip: (clipId: string, splitTime: number) => void;
  trimClip: (clipId: string, newStart?: number, newEnd?: number) => void;
  
  // Actions - Selection
  selectClip: (clipId: string, extend?: boolean) => void;
  selectClips: (clipIds: string[]) => void;
  selectAll: () => void;
  clearSelection: () => void;
  
  // Actions - Clipboard
  copySelected: () => void;
  cutSelected: () => void;
  paste: (targetTime: number, targetTrack?: string) => void;
  
  // Actions - Edit history
  pushEdit: (operation: Omit<EditOperation, 'id' | 'timestamp'>) => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  
  // Actions - Virtualization
  updateRenderWindow: (startTime: number, endTime: number) => void;
  setPixelsPerSecond: (pps: number) => void;
  setContainerWidth: (width: number) => void;
  
  // Actions - Markers
  addMarker: (marker: Omit<TimelineMarker, 'id'>) => void;
  removeMarker: (markerId: string) => void;
  getMarkersInRange: (start: number, end: number) => TimelineMarker[];
  
  // Actions - Quality
  updateClipQuality: (clipId: string, quality: QualityMetrics) => void;
  getClipQuality: (clipId: string) => QualityMetrics | null;
  
  // Utility functions
  getClipsInRange: (start: number, end: number) => TimelineClip[];
  getClipAtTime: (time: number, trackId?: string) => TimelineClip | null;
  timeToPixels: (time: number) => number;
  pixelsToTime: (pixels: number) => number;
  snapToGrid: (time: number) => number;
}

const RENDER_WINDOW_PADDING = 30; // seconds of padding around viewport
const MAX_EDIT_HISTORY = 100;
const DEFAULT_PIXELS_PER_SECOND = 100;

export const useTimelineStore = create<TimelineStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      // Initial state
      currentTime: 0,
      duration: 0,
      selectedClip: null,
      playbackState: 'paused',
      zoom: 1,
      viewportStart: 0,
      viewportEnd: 60,
      snapToGrid: true,
      gridInterval: 1,
      
      // Data
      tracks: [],
      clips: [],
      markers: [],
      selectedClips: [],
      clipboard: [],
      editHistory: [],
      editIndex: -1,
      qualityMetrics: {},
      
      // Virtualization
      renderWindow: {
        startTime: 0,
        endTime: 60,
        pixelsPerSecond: DEFAULT_PIXELS_PER_SECOND,
        visibleClips: [],
        visibleMarkers: [],
      },
      pixelsPerSecond: DEFAULT_PIXELS_PER_SECOND,
      containerWidth: 1000,
      
      // Basic setters
      setCurrentTime: (currentTime) => 
        set({ currentTime }, false, 'timeline/setCurrentTime'),
      
      setDuration: (duration) => 
        set({ duration }, false, 'timeline/setDuration'),
      
      setPlaybackState: (playbackState) => 
        set({ playbackState }, false, 'timeline/setPlaybackState'),
      
      setSelectedClip: (selectedClip) => 
        set({ selectedClip }, false, 'timeline/setSelectedClip'),
      
      setZoom: (zoom) => {
        const clampedZoom = Math.max(0.1, Math.min(10, zoom));
        const newPixelsPerSecond = DEFAULT_PIXELS_PER_SECOND * clampedZoom;
        
        set({ 
          zoom: clampedZoom,
          pixelsPerSecond: newPixelsPerSecond 
        }, false, 'timeline/setZoom');
        
        // Update render window
        get().updateRenderWindow(get().viewportStart, get().viewportEnd);
      },
      
      setViewport: (viewportStart, viewportEnd) => {
        set({ viewportStart, viewportEnd }, false, 'timeline/setViewport');
        get().updateRenderWindow(viewportStart, viewportEnd);
      },
      
      // Track management
      addTrack: (trackData) => {
        const id = `track_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const track: TimelineTrack = { id, ...trackData };
        
        set((state) => ({
          tracks: [...state.tracks, track]
        }), false, 'timeline/addTrack');
      },
      
      removeTrack: (trackId) => {
        set((state) => ({
          tracks: state.tracks.filter(t => t.id !== trackId),
          clips: state.clips.filter(c => c.trackId !== trackId)
        }), false, 'timeline/removeTrack');
      },
      
      updateTrack: (trackId, updates) => {
        set((state) => ({
          tracks: state.tracks.map(track => 
            track.id === trackId ? { ...track, ...updates } : track
          )
        }), false, 'timeline/updateTrack');
      },
      
      // Clip management
      addClip: (clipData) => {
        const id = `clip_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const clip: TimelineClip = { 
          id, 
          selected: false,
          locked: false,
          ...clipData 
        };
        
        set((state) => ({
          clips: [...state.clips, clip]
        }), false, 'timeline/addClip');
        
        get().updateRenderWindow(get().viewportStart, get().viewportEnd);
      },
      
      removeClip: (clipId) => {
        set((state) => ({
          clips: state.clips.filter(c => c.id !== clipId),
          selectedClips: state.selectedClips.filter(id => id !== clipId)
        }), false, 'timeline/removeClip');
        
        get().updateRenderWindow(get().viewportStart, get().viewportEnd);
      },
      
      updateClip: (clipId, updates) => {
        set((state) => ({
          clips: state.clips.map(clip => 
            clip.id === clipId ? { ...clip, ...updates } : clip
          )
        }), false, 'timeline/updateClip');
        
        get().updateRenderWindow(get().viewportStart, get().viewportEnd);
      },
      
      moveClip: (clipId, newStartTime, newTrackId) => {
        const { clips, snapToGrid: snap, gridInterval } = get();
        const clip = clips.find(c => c.id === clipId);
        if (!clip) return;
        
        const snappedTime = snap ? get().snapToGrid(newStartTime) : newStartTime;
        const newEndTime = snappedTime + clip.duration;
        
        const updates: Partial<TimelineClip> = {
          startTime: snappedTime,
          endTime: newEndTime,
        };
        
        if (newTrackId) {
          updates.trackId = newTrackId;
        }
        
        get().updateClip(clipId, updates);
        get().pushEdit({
          type: 'move',
          data: { clipId, newStartTime: snappedTime, newTrackId }
        });
      },
      
      splitClip: (clipId, splitTime) => {
        const { clips } = get();
        const clip = clips.find(c => c.id === clipId);
        if (!clip || splitTime <= clip.startTime || splitTime >= clip.endTime) return;
        
        // Create two new clips
        const leftClip: Omit<TimelineClip, 'id'> = {
          ...clip,
          endTime: splitTime,
          duration: splitTime - clip.startTime,
          sourceEndTime: clip.sourceStartTime + (splitTime - clip.startTime)
        };
        
        const rightClip: Omit<TimelineClip, 'id'> = {
          ...clip,
          startTime: splitTime,
          duration: clip.endTime - splitTime,
          sourceStartTime: clip.sourceStartTime + (splitTime - clip.startTime)
        };
        
        // Remove original and add new clips
        get().removeClip(clipId);
        get().addClip(leftClip);
        get().addClip(rightClip);
        
        get().pushEdit({
          type: 'split',
          data: { clipId, splitTime }
        });
      },
      
      trimClip: (clipId, newStart, newEnd) => {
        const { clips } = get();
        const clip = clips.find(c => c.id === clipId);
        if (!clip) return;
        
        const startTime = newStart ?? clip.startTime;
        const endTime = newEnd ?? clip.endTime;
        
        if (startTime >= endTime) return;
        
        const updates: Partial<TimelineClip> = {
          startTime,
          endTime,
          duration: endTime - startTime,
        };
        
        // Update source times proportionally
        if (newStart !== undefined) {
          const startDelta = newStart - clip.startTime;
          updates.sourceStartTime = clip.sourceStartTime + startDelta;
        }
        
        if (newEnd !== undefined) {
          const endDelta = clip.endTime - newEnd;
          updates.sourceEndTime = clip.sourceEndTime - endDelta;
        }
        
        get().updateClip(clipId, updates);
        get().pushEdit({
          type: 'trim',
          data: { clipId, newStartTime: startTime, newEndTime: endTime }
        });
      },
      
      // Selection management
      selectClip: (clipId, extend = false) => {
        set((state) => {
          if (extend) {
            const isSelected = state.selectedClips.includes(clipId);
            return {
              selectedClips: isSelected 
                ? state.selectedClips.filter(id => id !== clipId)
                : [...state.selectedClips, clipId],
              selectedClip: clipId
            };
          } else {
            return {
              selectedClips: [clipId],
              selectedClip: clipId
            };
          }
        }, false, 'timeline/selectClip');
      },
      
      selectClips: (clipIds) => 
        set({ 
          selectedClips: clipIds,
          selectedClip: clipIds[clipIds.length - 1] || null
        }, false, 'timeline/selectClips'),
      
      selectAll: () => {
        const { clips } = get();
        set({
          selectedClips: clips.map(c => c.id),
          selectedClip: clips[clips.length - 1]?.id || null
        }, false, 'timeline/selectAll');
      },
      
      clearSelection: () => 
        set({ 
          selectedClips: [], 
          selectedClip: null 
        }, false, 'timeline/clearSelection'),
      
      // Clipboard operations
      copySelected: () => {
        const { clips, selectedClips } = get();
        const clipsToCopy = clips.filter(c => selectedClips.includes(c.id));
        set({ clipboard: clipsToCopy }, false, 'timeline/copySelected');
      },
      
      cutSelected: () => {
        const { selectedClips } = get();
        get().copySelected();
        selectedClips.forEach(clipId => get().removeClip(clipId));
      },
      
      paste: (targetTime, targetTrack) => {
        const { clipboard } = get();
        if (clipboard.length === 0) return;
        
        // Calculate offset for relative positioning
        const minStartTime = Math.min(...clipboard.map(c => c.startTime));
        const offset = targetTime - minStartTime;
        
        clipboard.forEach(clip => {
          get().addClip({
            ...clip,
            trackId: targetTrack || clip.trackId,
            startTime: clip.startTime + offset,
            endTime: clip.endTime + offset,
          });
        });
      },
      
      // Edit history
      pushEdit: (operationData) => {
        const operation: EditOperation = {
          id: `edit_${Date.now()}`,
          timestamp: Date.now(),
          userId: 'current_user', // TODO: Get from auth
          applied: true,
          ...operationData
        };
        
        set((state) => {
          const newHistory = state.editHistory.slice(0, state.editIndex + 1);
          newHistory.push(operation);
          
          // Limit history size
          if (newHistory.length > MAX_EDIT_HISTORY) {
            newHistory.shift();
          }
          
          return {
            editHistory: newHistory,
            editIndex: newHistory.length - 1
          };
        }, false, 'timeline/pushEdit');
      },
      
      undo: () => {
        const { editHistory, editIndex } = get();
        if (editIndex >= 0) {
          // TODO: Implement actual undo logic
          set({ editIndex: editIndex - 1 }, false, 'timeline/undo');
        }
      },
      
      redo: () => {
        const { editHistory, editIndex } = get();
        if (editIndex < editHistory.length - 1) {
          // TODO: Implement actual redo logic
          set({ editIndex: editIndex + 1 }, false, 'timeline/redo');
        }
      },
      
      canUndo: () => get().editIndex >= 0,
      canRedo: () => get().editIndex < get().editHistory.length - 1,
      
      // Virtualization
      updateRenderWindow: (startTime, endTime) => {
        const { clips, markers, pixelsPerSecond } = get();
        
        const windowStart = Math.max(0, startTime - RENDER_WINDOW_PADDING);
        const windowEnd = endTime + RENDER_WINDOW_PADDING;
        
        const visibleClips = clips.filter(clip =>
          clip.startTime < windowEnd && clip.endTime > windowStart
        );
        
        const visibleMarkers = markers.filter(marker =>
          marker.time >= windowStart && marker.time <= windowEnd
        );
        
        set({
          renderWindow: {
            startTime: windowStart,
            endTime: windowEnd,
            pixelsPerSecond,
            visibleClips,
            visibleMarkers,
          }
        }, false, 'timeline/updateRenderWindow');
      },
      
      setPixelsPerSecond: (pixelsPerSecond) => 
        set({ pixelsPerSecond }, false, 'timeline/setPixelsPerSecond'),
      
      setContainerWidth: (containerWidth) => 
        set({ containerWidth }, false, 'timeline/setContainerWidth'),
      
      // Markers
      addMarker: (markerData) => {
        const id = `marker_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const marker: TimelineMarker = { id, ...markerData };
        
        set((state) => ({
          markers: [...state.markers, marker]
        }), false, 'timeline/addMarker');
      },
      
      removeMarker: (markerId) => {
        set((state) => ({
          markers: state.markers.filter(m => m.id !== markerId)
        }), false, 'timeline/removeMarker');
      },
      
      getMarkersInRange: (start, end) => {
        const { markers } = get();
        return markers.filter(marker => 
          marker.time >= start && marker.time <= end
        );
      },
      
      // Quality metrics
      updateClipQuality: (clipId, quality) => {
        set((state) => ({
          qualityMetrics: {
            ...state.qualityMetrics,
            [clipId]: quality
          }
        }), false, 'timeline/updateClipQuality');
      },
      
      getClipQuality: (clipId) => {
        return get().qualityMetrics[clipId] || null;
      },
      
      // Utility functions
      getClipsInRange: (start, end) => {
        const { clips } = get();
        return clips.filter(clip =>
          clip.startTime < end && clip.endTime > start
        );
      },
      
      getClipAtTime: (time, trackId) => {
        const { clips } = get();
        return clips.find(clip => 
          clip.startTime <= time && 
          clip.endTime > time &&
          (!trackId || clip.trackId === trackId)
        ) || null;
      },
      
      timeToPixels: (time) => {
        const { pixelsPerSecond } = get();
        return time * pixelsPerSecond;
      },
      
      pixelsToTime: (pixels) => {
        const { pixelsPerSecond } = get();
        return pixels / pixelsPerSecond;
      },
      
      snapToGrid: (time) => {
        const { gridInterval } = get();
        return Math.round(time / gridInterval) * gridInterval;
      },
    })),
    {
      name: 'timeline-store',
      version: 1,
    }
  )
);

// Optimized selectors
export const useTimelineTime = () => useTimelineStore((state) => ({
  currentTime: state.currentTime,
  duration: state.duration,
}));

export const useTimelineSelection = () => useTimelineStore((state) => ({
  selectedClip: state.selectedClip,
  selectedClips: state.selectedClips,
}));

export const useTimelineRenderWindow = () => useTimelineStore((state) => state.renderWindow);

export const useTimelineClips = () => useTimelineStore((state) => state.clips);

export const useTimelineTracks = () => useTimelineStore((state) => state.tracks);