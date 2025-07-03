/**
 * Editor Type Definitions - Phase 4
 * TypeScript interfaces for timeline editor and video player
 */

// Timeline state types
export interface TimelineState {
  currentTime: number;
  duration: number;
  selectedClip: string | null;
  selectedClips: string[];
  playbackState: 'playing' | 'paused' | 'loading' | 'error';
  zoom: number;
  viewportStart: number;
  viewportEnd: number;
  snapToGrid: boolean;
  gridInterval: number;
}

// Video player types
export interface PlayerState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  muted: boolean;
  playbackRate: number;
  buffered: Array<{ start: number; end: number }>;
  loading: boolean;
  error: string | null;
}

export interface VideoSource {
  url: string;
  type: 'mp4' | 'webm' | 'hls';
  quality: '240p' | '480p' | '720p' | '1080p';
  bitrate: number;
}

// Timeline visualization types
export interface TimelineTrack {
  id: string;
  type: 'video' | 'audio' | 'subtitle' | 'marker';
  name: string;
  height: number;
  visible: boolean;
  locked: boolean;
  data: TimelineClip[] | TimelineMarker[] | WaveformData;
}

export interface TimelineClip {
  id: string;
  trackId: string;
  startTime: number;
  endTime: number;
  duration: number;
  sourceStartTime: number;
  sourceEndTime: number;
  label: string;
  color: string;
  selected: boolean;
  locked: boolean;
  quality?: {
    overall: number;
    audio: number;
    visual: number;
    semantic: number;
    engagement: number;
  };
  reasoning?: string;
  transformations?: {
    volume?: number;
    fadeIn?: number;
    fadeOut?: number;
    crop?: CropSettings;
  };
}

export interface TimelineMarker {
  id: string;
  time: number;
  type: 'scene' | 'filler_word' | 'face_detection' | 'cut_candidate' | 'user';
  label: string;
  color: string;
  data?: any;
}

export interface WaveformData {
  peaks: Float32Array;
  length: number;
  sampleRate: number;
  channelCount: number;
}

// Crop and reframing types
export interface CropSettings {
  x: number;
  y: number;
  width: number;
  height: number;
  aspectRatio: string;
}

export interface ReframingPlan {
  targetWidth: number;
  targetHeight: number;
  method: 'face_centered' | 'safe_zone' | 'center_crop';
  confidence: number;
  frames: ReframingFrame[];
}

export interface ReframingFrame {
  frameIndex: number;
  timestamp: number;
  cropX: number;
  cropY: number;
  cropWidth: number;
  cropHeight: number;
  faceCenter?: { x: number; y: number };
  confidence: number;
}

// Editing operations types
export interface EditOperation {
  id: string;
  type: 'split' | 'trim' | 'move' | 'delete' | 'insert' | 'transform';
  timestamp: number;
  userId: string;
  data: any;
  applied: boolean;
}

export interface SplitOperation {
  clipId: string;
  splitTime: number;
}

export interface TrimOperation {
  clipId: string;
  newStartTime?: number;
  newEndTime?: number;
}

export interface MoveOperation {
  clipId: string;
  newStartTime: number;
  newTrackId?: string;
}

// Quality visualization types
export interface QualityMetrics {
  overall: number;
  audio: number;
  visual: number;
  semantic: number;
  engagement: number;
  cutSmoothness?: number;
  visualContinuity?: number;
  timestamp: number;
}

export interface QualityThresholds {
  excellent: number;
  good: number;
  fair: number;
  poor: number;
}

// AI decision transparency types
export interface AIDecision {
  id: string;
  type: 'cut_suggestion' | 'quality_assessment' | 'reframing' | 'filler_removal';
  confidence: number;
  reasoning: string;
  data: any;
  userOverride?: boolean;
  timestamp: number;
}

export interface CutSuggestion extends AIDecision {
  startTime: number;
  endTime: number;
  score: number;
  reasoning: string;
  alternatives: Array<{
    startTime: number;
    endTime: number;
    score: number;
    reasoning: string;
  }>;
}

// Keyboard shortcuts and hotkeys
export interface KeyboardShortcut {
  key: string;
  metaKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: string;
  description: string;
}

// Export settings
export interface ExportSettings {
  format: 'mp4' | 'webm' | 'mov';
  resolution: '720p' | '1080p' | '4K';
  aspectRatio: '16:9' | '9:16' | '1:1' | '4:5';
  quality: 'high' | 'medium' | 'low';
  preset: 'youtube_shorts' | 'tiktok' | 'instagram_reels' | 'custom';
  includeSubtitles: boolean;
  audioBitrate: number;
  videoBitrate: number;
}

// Collaboration types
export interface UserCursor {
  userId: string;
  userName: string;
  color: string;
  position: { x: number; y: number };
  timestamp: number;
}

export interface UserSelection {
  userId: string;
  userName: string;
  selectedClips: string[];
  currentTime: number;
  color: string;
}

export interface CollaborationSession {
  id: string;
  edlId: string;
  users: Array<{
    id: string;
    name: string;
    role: 'viewer' | 'editor';
    isOnline: boolean;
    cursor?: UserCursor;
    selection?: UserSelection;
  }>;
  createdAt: string;
  lastActivity: string;
}

// Performance optimization types
export interface RenderWindow {
  startTime: number;
  endTime: number;
  pixelsPerSecond: number;
  visibleClips: TimelineClip[];
  visibleMarkers: TimelineMarker[];
}

export interface VirtualScrollState {
  scrollTop: number;
  scrollLeft: number;
  containerWidth: number;
  containerHeight: number;
  itemHeight: number;
  visibleStartIndex: number;
  visibleEndIndex: number;
}

// Error and validation types
export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface EditorError {
  id: string;
  type: 'validation' | 'api' | 'playback' | 'export' | 'collaboration';
  message: string;
  details?: any;
  timestamp: number;
  recoverable: boolean;
}