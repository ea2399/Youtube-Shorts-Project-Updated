/**
 * Audio Waveform - Phase 4 Essential UI Component
 * Visual waveform representation with Canvas rendering
 */

'use client';

import React, { useRef, useEffect, useCallback, useState } from 'react';
import { TimelineClip, WaveformData } from '@/types';

interface AudioWaveformProps {
  clip?: TimelineClip;
  width: number;
  height?: number;
  pixelsPerSecond: number;
  currentTime: number;
  showPlayhead?: boolean;
  className?: string;
  onTimeClick?: (time: number) => void;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({
  clip,
  width,
  height = 60,
  pixelsPerSecond,
  currentTime,
  showPlayhead = true,
  className = '',
  onTimeClick,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [waveformData, setWaveformData] = useState<WaveformData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Generate mock waveform data (in production, this would come from audio analysis)
  const generateMockWaveform = useCallback((duration: number, sampleRate: number = 44100): WaveformData => {
    const samples = Math.floor(duration * sampleRate / 100); // Reduced resolution for performance
    const peaks = new Float32Array(samples);
    
    for (let i = 0; i < samples; i++) {
      // Generate realistic audio waveform pattern
      const time = (i / samples) * duration;
      const frequency = 0.5 + Math.sin(time * 0.1) * 0.3; // Varying frequency
      const amplitude = 0.3 + Math.sin(time * 0.05) * 0.7; // Varying amplitude
      
      // Add some noise and variation
      const noise = (Math.random() - 0.5) * 0.2;
      peaks[i] = Math.max(0, Math.min(1, amplitude * frequency + noise));
    }
    
    return {
      peaks,
      length: samples,
      sampleRate,
      channelCount: 1,
    };
  }, []);
  
  // Load waveform data
  useEffect(() => {
    if (!clip) return;
    
    setIsLoading(true);
    
    // In production, this would fetch from the backend
    // For now, generate mock data
    setTimeout(() => {
      const mockData = generateMockWaveform(clip.duration);
      setWaveformData(mockData);
      setIsLoading(false);
    }, 100);
  }, [clip, generateMockWaveform]);
  
  // Render waveform
  const renderWaveform = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !waveformData) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas size
    canvas.width = width * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Calculate waveform dimensions
    const centerY = height / 2;
    const maxAmplitude = centerY - 2;
    const samplesPerPixel = waveformData.length / width;
    
    // Render waveform
    ctx.fillStyle = '#6366f1'; // waveform color
    ctx.strokeStyle = '#6366f1';
    
    for (let x = 0; x < width; x++) {
      const sampleIndex = Math.floor(x * samplesPerPixel);
      const peak = waveformData.peaks[sampleIndex] || 0;
      const amplitude = peak * maxAmplitude;
      
      // Draw waveform bar
      const barHeight = Math.max(1, amplitude);
      ctx.fillRect(x, centerY - barHeight / 2, 1, barHeight);
    }
    
    // Render playhead if enabled
    if (showPlayhead && clip) {
      const playheadX = (currentTime - clip.startTime) * pixelsPerSecond;
      
      if (playheadX >= 0 && playheadX <= width) {
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(playheadX, 0);
        ctx.lineTo(playheadX, height);
        ctx.stroke();
      }
    }
    
    // Render quality indicators
    if (clip?.quality) {
      const quality = clip.quality.audio || 0;
      const alpha = Math.max(0.1, quality);
      
      // Overlay quality tint
      ctx.fillStyle = `rgba(16, 185, 129, ${alpha * 0.2})`; // Green tint for good quality
      ctx.fillRect(0, 0, width, height);
    }
  }, [width, height, waveformData, showPlayhead, clip, currentTime, pixelsPerSecond]);
  
  // Re-render when data changes
  useEffect(() => {
    renderWaveform();
  }, [renderWaveform]);
  
  // Handle canvas click
  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onTimeClick || !clip) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const relativeTime = clickX / pixelsPerSecond;
    const absoluteTime = clip.startTime + relativeTime;
    
    onTimeClick(absoluteTime);
  }, [onTimeClick, clip, pixelsPerSecond]);
  
  if (isLoading) {
    return (
      <div 
        className={`waveform-canvas bg-editor-surface border border-editor-border rounded animate-pulse ${className}`}
        style={{ width, height }}
      >
        <div className="flex items-center justify-center h-full text-editor-text-secondary text-sm">
          Loading waveform...
        </div>
      </div>
    );
  }
  
  if (!waveformData) {
    return (
      <div 
        className={`waveform-canvas bg-editor-surface border border-editor-border rounded ${className}`}
        style={{ width, height }}
      >
        <div className="flex items-center justify-center h-full text-editor-text-secondary text-sm">
          No audio data
        </div>
      </div>
    );
  }
  
  return (
    <canvas
      ref={canvasRef}
      className={`waveform-canvas border border-editor-border rounded cursor-pointer ${className}`}
      style={{ width, height }}
      onClick={handleClick}
      role="button"
      aria-label="Audio waveform - click to seek"
      tabIndex={0}
    />
  );
};

// Waveform overview component for track headers
export const WaveformOverview: React.FC<{
  clips: TimelineClip[];
  duration: number;
  width: number;
  height?: number;
  currentTime: number;
}> = ({ clips, duration, width, height = 40, currentTime }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas size
    canvas.width = width * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    const pixelsPerSecond = width / duration;
    const centerY = height / 2;
    
    // Render clips as blocks
    clips.forEach(clip => {
      const startX = clip.startTime * pixelsPerSecond;
      const clipWidth = clip.duration * pixelsPerSecond;
      
      // Clip background
      ctx.fillStyle = '#2563eb';
      ctx.fillRect(startX, centerY - 8, clipWidth, 16);
      
      // Quality indicator
      if (clip.quality) {
        const quality = clip.quality.overall;
        if (quality < 0.6) {
          ctx.fillStyle = '#ef4444';
          ctx.fillRect(startX, centerY - 2, clipWidth, 4);
        }
      }
    });
    
    // Playhead
    const playheadX = currentTime * pixelsPerSecond;
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, height);
    ctx.stroke();
  }, [clips, duration, width, height, currentTime]);
  
  return (
    <canvas
      ref={canvasRef}
      className="waveform-overview border border-editor-border rounded"
      style={{ width, height }}
    />
  );
};