/**
 * Video Player Component - Phase 4
 * Professional video player with Canvas overlay following expert recommendations
 */

'use client';

import React, { useRef, useEffect, useCallback, useState } from 'react';
import { usePlayerStore } from '@/stores/playerStore';
import { useTimelineStore } from '@/stores/timelineStore';
import { VideoSource, ReframingFrame } from '@/types';

// Hooks
import { useVideoPlayer } from '@/hooks/useVideoPlayer';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

// Components
import { VideoOverlay } from './VideoOverlay';
import { PlayerControls } from './PlayerControls';
import { QualitySelector } from './QualitySelector';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface VideoPlayerProps {
  sources: VideoSource[];
  reframingFrames?: ReframingFrame[];
  className?: string;
  onTimeUpdate?: (time: number) => void;
  onDurationChange?: (duration: number) => void;
  onLoadStart?: () => void;
  onLoadComplete?: () => void;
  onError?: (error: string) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  sources,
  reframingFrames = [],
  className = '',
  onTimeUpdate,
  onDurationChange,
  onLoadStart,
  onLoadComplete,
  onError,
}) => {
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // State
  const [isInitialized, setIsInitialized] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 1920, height: 1080 });
  
  // Store state
  const { 
    isPlaying, 
    currentTime, 
    duration, 
    volume, 
    muted,
    playbackRate,
    loading,
    error,
    updateCurrentTime,
    updateDuration,
    setPlaying,
    setLoading,
    setError
  } = usePlayerStore();
  
  const { selectedClip } = useTimelineStore();
  
  // Custom hooks
  const {
    play,
    pause,
    seek,
    setVolume,
    setMuted,
    setPlaybackRate,
    seekToFrame,
  } = useVideoPlayer(videoRef);
  
  // Initialize video player
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !sources.length) return;
    
    const handleLoadStart = () => {
      setLoading(true);
      onLoadStart?.();
    };
    
    const handleLoadedData = () => {
      setIsInitialized(true);
      setLoading(false);
      updateDuration(video.duration);
      setDimensions({
        width: video.videoWidth,
        height: video.videoHeight,
      });
      onLoadComplete?.();
      onDurationChange?.(video.duration);
    };
    
    const handleTimeUpdate = () => {
      const time = video.currentTime;
      updateCurrentTime(time);
      onTimeUpdate?.(time);
    };
    
    const handleError = () => {
      const errorMessage = video.error?.message || 'Video playback error';
      setError(errorMessage);
      setLoading(false);
      onError?.(errorMessage);
    };
    
    const handlePlay = () => setPlaying(true);
    const handlePause = () => setPlaying(false);
    
    // Event listeners
    video.addEventListener('loadstart', handleLoadStart);
    video.addEventListener('loadeddata', handleLoadedData);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('error', handleError);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    
    // Set initial source
    if (sources[0]) {
      video.src = sources[0].url;
    }
    
    return () => {
      video.removeEventListener('loadstart', handleLoadStart);
      video.removeEventListener('loadeddata', handleLoadedData);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('error', handleError);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, [sources, updateCurrentTime, updateDuration, setPlaying, setLoading, setError, onTimeUpdate, onDurationChange, onLoadStart, onLoadComplete, onError]);
  
  // Canvas overlay rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    if (!canvas || !video || !isInitialized) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    let animationId: number;
    
    const render = () => {
      // Set canvas size to match video
      canvas.width = dimensions.width;
      canvas.height = dimensions.height;
      
      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Render overlay elements based on current time
      renderOverlayElements(ctx, currentTime);
      
      // Continue animation loop
      animationId = requestAnimationFrame(render);
    };
    
    // Start render loop
    render();
    
    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [isInitialized, dimensions, currentTime, reframingFrames, selectedClip]);
  
  // Render overlay elements on canvas
  const renderOverlayElements = useCallback((ctx: CanvasRenderingContext2D, time: number) => {
    // Render reframing guides
    if (reframingFrames.length > 0) {
      const currentFrame = findFrameAtTime(reframingFrames, time);
      if (currentFrame) {
        renderReframingGuide(ctx, currentFrame);
      }
    }
    
    // Render selected clip highlight
    if (selectedClip) {
      renderSelectionOverlay(ctx);
    }
    
    // Render quality indicators
    renderQualityIndicators(ctx, time);
    
    // Render timeline markers
    renderTimelineMarkers(ctx, time);
  }, [reframingFrames, selectedClip]);
  
  // Find reframing frame at specific time
  const findFrameAtTime = (frames: ReframingFrame[], time: number): ReframingFrame | null => {
    return frames.find(frame => 
      Math.abs(frame.timestamp - time) < 0.1 // 100ms tolerance
    ) || null;
  };
  
  // Render reframing guide overlay
  const renderReframingGuide = (ctx: CanvasRenderingContext2D, frame: ReframingFrame) => {
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    
    // Draw crop rectangle
    ctx.strokeRect(
      frame.cropX,
      frame.cropY,
      frame.cropWidth,
      frame.cropHeight
    );
    
    // Draw face center point if available
    if (frame.faceCenter) {
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.arc(frame.faceCenter.x, frame.faceCenter.y, 4, 0, 2 * Math.PI);
      ctx.fill();
    }
    
    ctx.setLineDash([]);
  };
  
  // Render selection overlay
  const renderSelectionOverlay = (ctx: CanvasRenderingContext2D) => {
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 3;
    ctx.strokeRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  };
  
  // Render quality indicators
  const renderQualityIndicators = (ctx: CanvasRenderingContext2D, time: number) => {
    // This would integrate with quality metrics from the backend
    // For now, show placeholder
    ctx.fillStyle = 'rgba(16, 185, 129, 0.8)';
    ctx.fillRect(10, 10, 100, 30);
    ctx.fillStyle = 'white';
    ctx.font = '12px Inter';
    ctx.fillText('Quality: 8.5/10', 15, 28);
  };
  
  // Render timeline markers
  const renderTimelineMarkers = (ctx: CanvasRenderingContext2D, time: number) => {
    // This would show markers for scene changes, filler words, etc.
    // Implementation would depend on marker data from timeline store
  };
  
  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: ' ',
      action: 'playPause',
      description: 'Play/Pause',
      handler: () => isPlaying ? pause() : play(),
    },
    {
      key: 'ArrowLeft',
      action: 'seekBackward',
      description: 'Seek backward 5s',
      handler: () => seek(Math.max(0, currentTime - 5)),
    },
    {
      key: 'ArrowRight', 
      action: 'seekForward',
      description: 'Seek forward 5s',
      handler: () => seek(Math.min(duration, currentTime + 5)),
    },
    {
      key: 'j',
      action: 'seekBackwardFrame',
      description: 'Previous frame',
      handler: () => seekToFrame(-1),
    },
    {
      key: 'k',
      action: 'playPause',
      description: 'Play/Pause',
      handler: () => isPlaying ? pause() : play(),
    },
    {
      key: 'l',
      action: 'seekForwardFrame', 
      description: 'Next frame',
      handler: () => seekToFrame(1),
    },
  ]);
  
  if (error) {
    return (
      <div className={`video-player-container flex items-center justify-center bg-red-900/20 ${className}`}>
        <div className="text-center">
          <div className="text-red-400 mb-2">⚠️ Video Error</div>
          <div className="text-sm text-editor-text-secondary">{error}</div>
        </div>
      </div>
    );
  }
  
  return (
    <div 
      ref={containerRef}
      className={`video-player-container relative ${className}`}
      role="application"
      aria-label="Video Player"
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        className="w-full h-full object-contain bg-black"
        crossOrigin="anonymous"
        preload="metadata"
        playsInline
        volume={volume}
        muted={muted}
        onVolumeChange={(e) => setVolume((e.target as HTMLVideoElement).volume)}
        style={{ 
          display: isInitialized ? 'block' : 'none'
        }}
      />
      
      {/* Canvas Overlay */}
      <canvas
        ref={canvasRef}
        className="video-player-overlay absolute inset-0 pointer-events-none"
        style={{
          display: isInitialized ? 'block' : 'none'
        }}
      />
      
      {/* Loading State */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <LoadingSpinner className="w-8 h-8 text-white" />
          <span className="ml-3 text-white">Loading video...</span>
        </div>
      )}
      
      {/* Video Overlay Components */}
      {isInitialized && (
        <VideoOverlay
          currentTime={currentTime}
          duration={duration}
          onSeek={seek}
        />
      )}
      
      {/* Player Controls */}
      {isInitialized && (
        <PlayerControls
          isPlaying={isPlaying}
          currentTime={currentTime}
          duration={duration}
          volume={volume}
          muted={muted}
          playbackRate={playbackRate}
          onPlay={play}
          onPause={pause}
          onSeek={seek}
          onVolumeChange={setVolume}
          onMutedChange={setMuted}
          onPlaybackRateChange={setPlaybackRate}
        />
      )}
      
      {/* Quality Selector */}
      {sources.length > 1 && (
        <QualitySelector
          sources={sources}
          onSourceChange={(source) => {
            if (videoRef.current) {
              const currentTime = videoRef.current.currentTime;
              videoRef.current.src = source.url;
              videoRef.current.currentTime = currentTime;
            }
          }}
        />
      )}
    </div>
  );
};