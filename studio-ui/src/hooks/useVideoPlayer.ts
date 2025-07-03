/**
 * Video Player Hook - Phase 4
 * Custom hook for video player interactions and controls
 */

import { useCallback, useRef, useEffect } from 'react';
import { usePlayerStore } from '@/stores/playerStore';

export interface UseVideoPlayerReturn {
  play: () => Promise<void>;
  pause: () => void;
  seek: (time: number) => void;
  setVolume: (volume: number) => void;
  setMuted: (muted: boolean) => void;
  setPlaybackRate: (rate: number) => void;
  seekToFrame: (frameOffset: number) => void;
  getCurrentFrame: () => number;
  getTotalFrames: () => number;
}

export const useVideoPlayer = (videoRef: React.RefObject<HTMLVideoElement>): UseVideoPlayerReturn => {
  const frameRate = useRef(30); // Default frame rate, will be updated when video loads
  
  const {
    setPlaying,
    setError,
    updateCurrentTime,
    updateDuration,
  } = usePlayerStore();
  
  // Update frame rate when video loads
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    
    const updateVideoInfo = () => {
      // Try to detect frame rate from video metadata
      // This is a simplified approach - in production you might need more sophisticated detection
      frameRate.current = 30; // Default to 30fps
      updateDuration(video.duration);
    };
    
    video.addEventListener('loadedmetadata', updateVideoInfo);
    return () => video.removeEventListener('loadedmetadata', updateVideoInfo);
  }, [updateDuration]);
  
  // Play video
  const play = useCallback(async (): Promise<void> => {
    const video = videoRef.current;
    if (!video) return;
    
    try {
      await video.play();
      setPlaying(true);
      setError(null);
    } catch (error) {
      console.error('Video play failed:', error);
      setError('Failed to play video');
      setPlaying(false);
    }
  }, [setPlaying, setError]);
  
  // Pause video
  const pause = useCallback((): void => {
    const video = videoRef.current;
    if (!video) return;
    
    video.pause();
    setPlaying(false);
  }, [setPlaying]);
  
  // Seek to specific time
  const seek = useCallback((time: number): void => {
    const video = videoRef.current;
    if (!video) return;
    
    const clampedTime = Math.max(0, Math.min(video.duration || 0, time));
    video.currentTime = clampedTime;
    updateCurrentTime(clampedTime);
  }, [updateCurrentTime]);
  
  // Set volume
  const setVolume = useCallback((volume: number): void => {
    const video = videoRef.current;
    if (!video) return;
    
    const clampedVolume = Math.max(0, Math.min(1, volume));
    video.volume = clampedVolume;
    usePlayerStore.getState().setVolume(clampedVolume);
  }, []);
  
  // Set muted state
  const setMuted = useCallback((muted: boolean): void => {
    const video = videoRef.current;
    if (!video) return;
    
    video.muted = muted;
    usePlayerStore.getState().setMuted(muted);
  }, []);
  
  // Set playback rate
  const setPlaybackRate = useCallback((rate: number): void => {
    const video = videoRef.current;
    if (!video) return;
    
    const validRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
    const clampedRate = validRates.find(r => r === rate) || 1;
    video.playbackRate = clampedRate;
    usePlayerStore.getState().setPlaybackRate(clampedRate);
  }, []);
  
  // Seek by frame offset
  const seekToFrame = useCallback((frameOffset: number): void => {
    const video = videoRef.current;
    if (!video) return;
    
    const currentFrame = Math.round(video.currentTime * frameRate.current);
    const newFrame = Math.max(0, currentFrame + frameOffset);
    const newTime = newFrame / frameRate.current;
    
    seek(newTime);
  }, [seek]);
  
  // Get current frame number
  const getCurrentFrame = useCallback((): number => {
    const video = videoRef.current;
    if (!video) return 0;
    
    return Math.round(video.currentTime * frameRate.current);
  }, []);
  
  // Get total frame count
  const getTotalFrames = useCallback((): number => {
    const video = videoRef.current;
    if (!video) return 0;
    
    return Math.round(video.duration * frameRate.current);
  }, []);
  
  return {
    play,
    pause,
    seek,
    setVolume,
    setMuted,
    setPlaybackRate,
    seekToFrame,
    getCurrentFrame,
    getTotalFrames,
  };
};