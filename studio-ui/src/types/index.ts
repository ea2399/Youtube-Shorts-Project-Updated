/**
 * Type Definitions Index - Phase 4
 * Central export for all TypeScript types
 */

// Re-export all types for easy importing
export * from './api';
export * from './editor';

// Global utility types
export type UUID = string;
export type Timestamp = number;
export type Milliseconds = number;
export type Seconds = number;

// Common UI state types
export interface LoadingState {
  isLoading: boolean;
  error: string | null;
  data: any;
}

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// Theme and styling types
export type ThemeMode = 'light' | 'dark' | 'auto';

export interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  success: string;
  warning: string;
  error: string;
  background: string;
  surface: string;
  text: {
    primary: string;
    secondary: string;
    muted: string;
  };
}

// Event handler types for components
export type EventHandler<T = void> = (event?: T) => void;
export type ChangeHandler<T> = (value: T) => void;
export type SelectHandler<T> = (selected: T) => void;

// Async operation types
export type AsyncOperation<T> = Promise<T>;
export type AsyncFunction<T, R> = (arg: T) => Promise<R>;

// Component prop types
export interface BaseComponentProps {
  className?: string;
  id?: string;
  'data-testid'?: string;
}

// Validation and form types
export type ValidationRule<T> = (value: T) => string | undefined;
export type Validator<T> = (value: T) => { isValid: boolean; error?: string };

// Media and file types
export interface MediaFile {
  url: string;
  type: string;
  size: number;
  duration?: number;
  width?: number;
  height?: number;
  thumbnail?: string;
}

// WebGL and canvas types
export interface WebGLContext {
  gl: WebGLRenderingContext | WebGL2RenderingContext;
  canvas: HTMLCanvasElement;
  program?: WebGLProgram;
  buffers?: Record<string, WebGLBuffer>;
  textures?: Record<string, WebGLTexture>;
}

// Audio processing types
export interface AudioContext {
  context: AudioContext;
  analyser: AnalyserNode;
  gainNode: GainNode;
  source?: AudioBufferSourceNode | MediaElementAudioSourceNode;
}

// Performance monitoring types
export interface PerformanceMetrics {
  renderTime: number;
  memoryUsage: number;
  frameRate: number;
  timestamp: number;
}

// Storage and caching types
export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

export interface StorageAdapter {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T, ttl?: number): Promise<void>;
  remove(key: string): Promise<void>;
  clear(): Promise<void>;
}