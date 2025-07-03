/**
 * API Type Definitions - Phase 4
 * TypeScript interfaces for backend API integration
 */

// Base API response types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

// Video and Project types (Phase 1)
export interface Video {
  id: string;
  source_url: string;
  status: VideoStatus;
  language: string;
  num_clips: number;
  min_duration: number;
  max_duration: number;
  progress: {
    stage: string;
    pct: number;
  };
  created_at: string;
  updated_at: string;
}

export type VideoStatus = 'CREATED' | 'DOWNLOADING' | 'PROCESSING' | 'DONE' | 'ERROR';

export interface Clip {
  id: string;
  start: number;
  end: number;
  duration: number;
  title: string;
  text: string;
  overall_score: number;
  context_dependency: number;
  tags: string[];
  files: {
    horizontal: string;
    vertical: string;
    subtitle: string;
  };
}

// EDL types (Phase 3)
export interface EDL {
  edl_id: string;
  video_id: string;
  version: number;
  status: string;
  target_duration: number;
  actual_duration?: number;
  overall_score?: number;
  clip_count: number;
  generation_strategy?: string;
  created_at: string;
}

export interface ClipInstance {
  id: string;
  sequence: number;
  source_start_time: number;
  source_end_time: number;
  source_duration: number;
  timeline_start_time: number;
  timeline_end_time: number;
  timeline_duration: number;
  audio_score?: number;
  visual_score?: number;
  semantic_score?: number;
  engagement_score?: number;
  overall_score?: number;
  reasoning?: string;
}

export interface EDLDetail {
  edl: EDL;
  clips: ClipInstance[];
  alternative_edls: EDL[];
}

// Quality metrics types
export interface QualityReport {
  edl_id: string;
  overall_quality_score: number;
  avg_cut_smoothness: number;
  avg_visual_continuity: number;
  avg_semantic_coherence: number;
  avg_engagement_score: number;
  cuts_meeting_smoothness: number;
  cuts_meeting_visual: number;
  cuts_meeting_duration: number;
  high_quality_clips: number;
  medium_quality_clips: number;
  low_quality_clips: number;
  meets_production_criteria: boolean;
  validation_time_seconds: number;
  recommended_adjustments: Array<{
    type: string;
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
  }>;
  quality_bottlenecks: string[];
}

// Cut candidate types for AI transparency
export interface CutCandidate {
  id: string;
  start_time: number;
  end_time: number;
  duration: number;
  overall_score: number;
  audio_score: number;
  visual_score: number;
  semantic_score: number;
  engagement_score: number;
  selected_for_edl: boolean;
  selection_rank?: number;
  exclusion_reason?: string;
}

// Request types for API calls
export interface EDLGenerationRequest {
  video_id: string;
  target_duration: number;
  strategy: 'silence_based' | 'scene_based' | 'multi_modal';
  max_clips: number;
  min_clip_duration: number;
  max_clip_duration: number;
  quality_threshold: number;
  generate_alternatives: boolean;
}

export interface ClipUpdateRequest {
  source_start_time?: number;
  source_end_time?: number;
  timeline_start_time?: number;
  timeline_end_time?: number;
  reasoning?: string;
  transformations?: Record<string, any>;
}

// WebSocket message types for real-time collaboration
export interface WebSocketMessage {
  type: 'edl_update' | 'quality_metrics' | 'collaboration' | 'user_action';
  data: any;
  timestamp: number;
  user_id: string;
  session_id?: string;
}

export interface CollaborationEvent {
  event_type: 'user_joined' | 'user_left' | 'cursor_moved' | 'selection_changed' | 'edit_applied';
  user_id: string;
  user_name: string;
  data?: any;
}

// Authentication types
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: 'viewer' | 'editor' | 'admin';
  avatar?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: 'Bearer';
}

// Error types
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}