/**
 * Player Store - Phase 4
 * Zustand store for video player state management
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { PlayerState, VideoSource } from '@/types';

interface PlayerStore extends PlayerState {
  // Actions
  setPlaying: (playing: boolean) => void;
  updateCurrentTime: (time: number) => void;
  updateDuration: (duration: number) => void;
  setVolume: (volume: number) => void;
  setMuted: (muted: boolean) => void;
  setPlaybackRate: (rate: number) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateBuffered: (buffered: Array<{ start: number; end: number }>) => void;
  reset: () => void;
  
  // Video sources
  sources: VideoSource[];
  currentSource: VideoSource | null;
  setSources: (sources: VideoSource[]) => void;
  setCurrentSource: (source: VideoSource) => void;
  
  // Playback control
  seekTo: (time: number) => void;
  seekRelative: (delta: number) => void;
  togglePlayPause: () => void;
  toggleMute: () => void;
  
  // Quality control
  autoQuality: boolean;
  setAutoQuality: (auto: boolean) => void;
}

const initialState: PlayerState = {
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 1,
  muted: false,
  playbackRate: 1,
  buffered: [],
  loading: false,
  error: null,
};

export const usePlayerStore = create<PlayerStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,
      sources: [],
      currentSource: null,
      autoQuality: true,
      
      // Basic setters
      setPlaying: (isPlaying) => 
        set({ isPlaying }, false, 'player/setPlaying'),
      
      updateCurrentTime: (currentTime) => 
        set({ currentTime }, false, 'player/updateCurrentTime'),
      
      updateDuration: (duration) => 
        set({ duration }, false, 'player/updateDuration'),
      
      setVolume: (volume) => {
        const clampedVolume = Math.max(0, Math.min(1, volume));
        set({ volume: clampedVolume }, false, 'player/setVolume');
      },
      
      setMuted: (muted) => 
        set({ muted }, false, 'player/setMuted'),
      
      setPlaybackRate: (playbackRate) => {
        const validRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
        const clampedRate = validRates.find(rate => rate === playbackRate) || 1;
        set({ playbackRate: clampedRate }, false, 'player/setPlaybackRate');
      },
      
      setLoading: (loading) => 
        set({ loading }, false, 'player/setLoading'),
      
      setError: (error) => 
        set({ error }, false, 'player/setError'),
      
      updateBuffered: (buffered) => 
        set({ buffered }, false, 'player/updateBuffered'),
      
      reset: () => 
        set(initialState, false, 'player/reset'),
      
      // Source management
      setSources: (sources) => {
        const currentSource = sources.length > 0 ? sources[0] : null;
        set({ 
          sources, 
          currentSource,
          error: sources.length === 0 ? 'No video sources available' : null
        }, false, 'player/setSources');
      },
      
      setCurrentSource: (source) => {
        const { sources } = get();
        if (sources.includes(source)) {
          set({ currentSource: source }, false, 'player/setCurrentSource');
        }
      },
      
      // Playback control actions
      seekTo: (time) => {
        const { duration } = get();
        const clampedTime = Math.max(0, Math.min(duration, time));
        set({ currentTime: clampedTime }, false, 'player/seekTo');
      },
      
      seekRelative: (delta) => {
        const { currentTime, duration } = get();
        const newTime = Math.max(0, Math.min(duration, currentTime + delta));
        set({ currentTime: newTime }, false, 'player/seekRelative');
      },
      
      togglePlayPause: () => {
        const { isPlaying } = get();
        set({ isPlaying: !isPlaying }, false, 'player/togglePlayPause');
      },
      
      toggleMute: () => {
        const { muted } = get();
        set({ muted: !muted }, false, 'player/toggleMute');
      },
      
      // Quality control
      setAutoQuality: (autoQuality) =>
        set({ autoQuality }, false, 'player/setAutoQuality'),
    })),
    {
      name: 'player-store',
      version: 1,
    }
  )
);

// Selectors for optimized component subscriptions
export const usePlayerTime = () => usePlayerStore((state) => ({
  currentTime: state.currentTime,
  duration: state.duration,
}));

export const usePlayerPlayback = () => usePlayerStore((state) => ({
  isPlaying: state.isPlaying,
  playbackRate: state.playbackRate,
  loading: state.loading,
}));

export const usePlayerAudio = () => usePlayerStore((state) => ({
  volume: state.volume,
  muted: state.muted,
}));

export const usePlayerError = () => usePlayerStore((state) => state.error);

export const usePlayerSources = () => usePlayerStore((state) => ({
  sources: state.sources,
  currentSource: state.currentSource,
  autoQuality: state.autoQuality,
}));

// Action selectors
export const usePlayerActions = () => usePlayerStore((state) => ({
  setPlaying: state.setPlaying,
  seekTo: state.seekTo,
  seekRelative: state.seekRelative,
  togglePlayPause: state.togglePlayPause,
  setVolume: state.setVolume,
  toggleMute: state.toggleMute,
  setPlaybackRate: state.setPlaybackRate,
  setSources: state.setSources,
  setCurrentSource: state.setCurrentSource,
}));

// Subscribe to player time updates for external synchronization
export const subscribeToTimeUpdates = (callback: (time: number) => void) => {
  return usePlayerStore.subscribe(
    (state) => state.currentTime,
    callback,
    {
      equalityFn: (a, b) => Math.abs(a - b) < 0.1, // Only fire if change > 100ms
    }
  );
};