/**
 * Player Controls - Phase 4 UI Component
 * Professional video player controls with comprehensive functionality
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { formatTime } from '@/lib/utils';

interface PlayerControlsProps {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  muted: boolean;
  playbackRate: number;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onMutedChange: (muted: boolean) => void;
  onPlaybackRateChange: (rate: number) => void;
  className?: string;
}

export const PlayerControls: React.FC<PlayerControlsProps> = ({
  isPlaying,
  currentTime,
  duration,
  volume,
  muted,
  playbackRate,
  onPlay,
  onPause,
  onSeek,
  onVolumeChange,
  onMutedChange,
  onPlaybackRateChange,
  className = '',
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);
  const [showPlaybackRates, setShowPlaybackRates] = useState(false);
  const progressRef = useRef<HTMLDivElement>(null);
  const volumeRef = useRef<HTMLDivElement>(null);

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  // Playback rate options
  const playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

  // Handle progress bar interaction
  const handleProgressClick = (e: React.MouseEvent) => {
    if (!progressRef.current || duration === 0) return;
    
    const rect = progressRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    const time = percentage * duration;
    
    onSeek(Math.max(0, Math.min(duration, time)));
  };

  const handleProgressMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    handleProgressClick(e);
  };

  const handleProgressMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    handleProgressClick(e);
  };

  const handleProgressMouseUp = () => {
    setIsDragging(false);
  };

  // Handle volume slider interaction
  const handleVolumeClick = (e: React.MouseEvent) => {
    if (!volumeRef.current) return;
    
    const rect = volumeRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    const newVolume = Math.max(0, Math.min(1, percentage));
    
    onVolumeChange(newVolume);
    if (newVolume > 0 && muted) {
      onMutedChange(false);
    }
  };

  // Global mouse event handlers for dragging
  useEffect(() => {
    const handleGlobalMouseMove = (e: MouseEvent) => {
      if (!isDragging || !progressRef.current || duration === 0) return;
      
      const rect = progressRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = x / rect.width;
      const time = percentage * duration;
      
      onSeek(Math.max(0, Math.min(duration, time)));
    };

    const handleGlobalMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleGlobalMouseMove);
      document.addEventListener('mouseup', handleGlobalMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleGlobalMouseMove);
      document.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [isDragging, duration, onSeek]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setShowVolumeSlider(false);
      setShowPlaybackRates(false);
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  return (
    <div className={`player-controls absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 ${className}`}>
      {/* Progress Bar */}
      <div className="mb-4">
        <div
          ref={progressRef}
          className="relative h-2 bg-white/20 rounded-full cursor-pointer group hover:h-3 transition-all"
          onMouseDown={handleProgressMouseDown}
          onMouseMove={handleProgressMouseMove}
          onMouseUp={handleProgressMouseUp}
          onClick={handleProgressClick}
        >
          {/* Progress Fill */}
          <div
            className="absolute top-0 left-0 h-full bg-blue-500 rounded-full transition-all group-hover:bg-blue-400"
            style={{ width: `${progress}%` }}
          />
          
          {/* Progress Handle */}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-blue-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing"
            style={{ left: `calc(${progress}% - 8px)` }}
          />
          
          {/* Buffered Progress (placeholder) */}
          <div
            className="absolute top-0 left-0 h-full bg-white/10 rounded-full"
            style={{ width: `${Math.min(100, progress + 10)}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        {/* Left Controls */}
        <div className="flex items-center gap-3">
          {/* Play/Pause Button */}
          <button
            onClick={isPlaying ? onPause : onPlay}
            className="flex items-center justify-center w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4v16h4V4H6zm8 0v16h4V4h-4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Time Display */}
          <div className="text-white text-sm font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* Volume Control */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowVolumeSlider(!showVolumeSlider);
              }}
              onMouseEnter={() => setShowVolumeSlider(true)}
              className="flex items-center justify-center w-8 h-8 text-white hover:bg-white/10 rounded transition-colors"
              aria-label={muted ? 'Unmute' : 'Mute'}
            >
              {muted || volume === 0 ? (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M3.63 3.63a.996.996 0 000 1.41L7.29 8.7 7 9H4c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1h3l3.29 3.29c.63.63 1.71.18 1.71-.71v-4.17l4.18 4.18c-.49.37-1.02.68-1.6.91-.36.15-.58.53-.58.92 0 .72.73 1.18 1.39.91.8-.33 1.55-.77 2.22-1.31l4.18 4.18a.996.996 0 101.41-1.41L5.05 3.63c-.39-.39-1.02-.39-1.42 0zM19 12c0 .82-.15 1.61-.41 2.34l1.53 1.53c.56-1.17.88-2.48.88-3.87 0-3.83-2.4-7.11-5.78-8.4-.59-.23-1.22.23-1.22.86v.19c0 .38.25.71.61.85C17.18 6.54 19 9.06 19 12zm-8.71-6.29l-.17.17L12 7.76V6.41c0-.89-1.08-1.34-1.71-.71z"/>
                </svg>
              ) : volume < 0.5 ? (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M7 9v6h4l5 5V4l-5 5H7z"/>
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                </svg>
              )}
            </button>

            {/* Volume Slider */}
            {showVolumeSlider && (
              <div 
                className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-black/90 p-3 rounded-lg"
                onMouseLeave={() => setShowVolumeSlider(false)}
              >
                <div className="flex flex-col items-center">
                  <div
                    ref={volumeRef}
                    className="relative w-20 h-2 bg-white/20 rounded-full cursor-pointer mb-2"
                    onClick={handleVolumeClick}
                  >
                    <div
                      className="absolute top-0 left-0 h-full bg-blue-500 rounded-full"
                      style={{ width: `${(muted ? 0 : volume) * 100}%` }}
                    />
                  </div>
                  <button
                    onClick={() => onMutedChange(!muted)}
                    className="text-xs text-white/80 hover:text-white"
                  >
                    {muted ? 'Unmute' : 'Mute'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Playback Speed */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowPlaybackRates(!showPlaybackRates);
              }}
              className="text-white text-sm font-mono hover:bg-white/10 px-2 py-1 rounded transition-colors min-w-[3rem] text-center"
              aria-label="Playback speed"
            >
              {playbackRate}x
            </button>

            {/* Playback Rate Menu */}
            {showPlaybackRates && (
              <div className="absolute bottom-full mb-2 right-0 bg-black/90 rounded-lg overflow-hidden border border-white/10">
                {playbackRates.map((rate) => (
                  <button
                    key={rate}
                    onClick={() => {
                      onPlaybackRateChange(rate);
                      setShowPlaybackRates(false);
                    }}
                    className={`block w-full px-4 py-2 text-left text-sm hover:bg-white/10 transition-colors ${
                      rate === playbackRate ? 'bg-blue-500/30 text-blue-300' : 'text-white'
                    }`}
                  >
                    {rate}x
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Fullscreen Button */}
          <button
            onClick={() => {
              const container = document.querySelector('.video-player-container');
              if (container) {
                if (document.fullscreenElement) {
                  document.exitFullscreen();
                } else {
                  container.requestFullscreen();
                }
              }
            }}
            className="flex items-center justify-center w-8 h-8 text-white hover:bg-white/10 rounded transition-colors"
            aria-label="Toggle fullscreen"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

// Utility component for time scrubbing preview
export const TimePreview: React.FC<{
  time: number;
  visible: boolean;
  position: { x: number; y: number };
}> = ({ time, visible, position }) => {
  if (!visible) return null;

  return (
    <div
      className="fixed bg-black/90 text-white text-xs px-2 py-1 rounded pointer-events-none z-50"
      style={{
        left: position.x,
        top: position.y - 40,
        transform: 'translateX(-50%)',
      }}
    >
      {formatTime(time)}
    </div>
  );
};

// Utility component for volume visualization
export const VolumeIndicator: React.FC<{
  volume: number;
  muted: boolean;
  visible: boolean;
}> = ({ volume, muted, visible }) => {
  if (!visible) return null;

  return (
    <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-black/80 text-white px-4 py-2 rounded-lg z-50">
      <div className="flex items-center gap-3">
        <div className="text-sm">Volume</div>
        <div className="w-20 h-2 bg-white/20 rounded-full">
          <div
            className="h-full bg-white rounded-full transition-all"
            style={{ width: `${(muted ? 0 : volume) * 100}%` }}
          />
        </div>
        <div className="text-sm font-mono min-w-[3ch]">
          {muted ? '0%' : `${Math.round(volume * 100)}%`}
        </div>
      </div>
    </div>
  );
};