/**
 * Video Overlay - Phase 4 Essential UI Component
 * Canvas overlay for video player with reframing guides and markers
 */

'use client';

import React, { useRef, useEffect, useCallback } from 'react';
import { ReframingFrame, TimelineMarker } from '@/types';

interface VideoOverlayProps {
  width?: number;
  height?: number;
  currentTime: number;
  duration: number;
  reframingFrames?: ReframingFrame[];
  markers?: TimelineMarker[];
  showReframingGuide?: boolean;
  showMarkers?: boolean;
  onSeek?: (time: number) => void;
  className?: string;
}

export const VideoOverlay: React.FC<VideoOverlayProps> = ({
  width = 1920,
  height = 1080,
  currentTime,
  duration,
  reframingFrames = [],
  markers = [],
  showReframingGuide = true,
  showMarkers = true,
  onSeek,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Find reframing frame at current time
  const findFrameAtTime = useCallback((frames: ReframingFrame[], time: number): ReframingFrame | null => {
    return frames.find(frame => 
      Math.abs(frame.timestamp - time) < 0.1 // 100ms tolerance
    ) || null;
  }, []);
  
  // Render overlay elements
  const renderOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas size
    canvas.width = width;
    canvas.height = height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Render reframing guide
    if (showReframingGuide && reframingFrames.length > 0) {
      const currentFrame = findFrameAtTime(reframingFrames, currentTime);
      if (currentFrame) {
        renderReframingGuide(ctx, currentFrame);
      }
    }
    
    // Render markers
    if (showMarkers && markers.length > 0) {
      renderMarkers(ctx);
    }
    
    // Render timeline progress
    renderTimelineProgress(ctx);
    
    // Render quality indicators
    renderQualityIndicators(ctx);
    
    // Render safe zones
    renderSafeZones(ctx);
  }, [width, height, currentTime, reframingFrames, markers, showReframingGuide, showMarkers, findFrameAtTime]);
  
  // Render reframing guide
  const renderReframingGuide = (ctx: CanvasRenderingContext2D, frame: ReframingFrame) => {
    ctx.save();
    
    // Reframing rectangle
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 3;
    ctx.setLineDash([10, 5]);
    
    // Calculate 9:16 aspect ratio crop
    const cropWidth = frame.cropWidth;
    const cropHeight = frame.cropHeight;
    const cropX = frame.cropX;
    const cropY = frame.cropY;
    
    ctx.strokeRect(cropX, cropY, cropWidth, cropHeight);
    
    // Face center point
    if (frame.faceCenter) {
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.arc(frame.faceCenter.x, frame.faceCenter.y, 6, 0, 2 * Math.PI);
      ctx.fill();
      
      // Crosshair
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(frame.faceCenter.x - 20, frame.faceCenter.y);
      ctx.lineTo(frame.faceCenter.x + 20, frame.faceCenter.y);
      ctx.moveTo(frame.faceCenter.x, frame.faceCenter.y - 20);
      ctx.lineTo(frame.faceCenter.x, frame.faceCenter.y + 20);
      ctx.stroke();
    }
    
    // Confidence indicator
    const confidenceColor = frame.confidence > 0.8 ? '#10b981' : frame.confidence > 0.6 ? '#f59e0b' : '#ef4444';
    ctx.fillStyle = confidenceColor;
    ctx.fillRect(cropX + 10, cropY + 10, 100, 20);
    ctx.fillStyle = 'white';
    ctx.font = '12px Inter';
    ctx.fillText(`Confidence: ${(frame.confidence * 100).toFixed(0)}%`, cropX + 15, cropY + 23);
    
    ctx.restore();
  };
  
  // Render timeline markers
  const renderMarkers = (ctx: CanvasRenderingContext2D) => {
    markers.forEach(marker => {
      const markerTime = marker.time;
      const isCurrentMarker = Math.abs(markerTime - currentTime) < 0.5;
      
      let color = '#f59e0b'; // Default marker color
      switch (marker.type) {
        case 'scene':
          color = '#3b82f6';
          break;
        case 'filler_word':
          color = '#ef4444';
          break;
        case 'face_detection':
          color = '#10b981';
          break;
        case 'cut_candidate':
          color = '#8b5cf6';
          break;
      }
      
      if (isCurrentMarker) {
        // Highlight current marker
        ctx.fillStyle = color;
        ctx.fillRect(20, 20, 200, 30);
        ctx.fillStyle = 'white';
        ctx.font = '14px Inter';
        ctx.fillText(marker.label, 25, 40);
      }
    });
  };
  
  // Render timeline progress
  const renderTimelineProgress = (ctx: CanvasRenderingContext2D) => {
    const progressWidth = 200;
    const progressHeight = 6;
    const x = width - progressWidth - 20;
    const y = height - 40;
    
    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(x, y, progressWidth, progressHeight);
    
    // Progress
    const progress = duration > 0 ? currentTime / duration : 0;
    ctx.fillStyle = '#3b82f6';
    ctx.fillRect(x, y, progressWidth * progress, progressHeight);
    
    // Time display
    ctx.fillStyle = 'white';
    ctx.font = '12px monospace';
    ctx.textAlign = 'right';
    ctx.fillText(formatTime(currentTime), x + progressWidth, y - 5);
    ctx.fillText(formatTime(duration), x + progressWidth, y + progressHeight + 15);
    ctx.textAlign = 'left';
  };
  
  // Render quality indicators
  const renderQualityIndicators = (ctx: CanvasRenderingContext2D) => {
    // Mock quality data - in production this would come from the backend
    const qualities = [
      { label: 'Audio', value: 0.85, color: '#10b981' },
      { label: 'Visual', value: 0.92, color: '#3b82f6' },
      { label: 'Overall', value: 0.88, color: '#8b5cf6' },
    ];
    
    qualities.forEach((quality, index) => {
      const x = 20;
      const y = 60 + index * 25;
      
      // Background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.fillRect(x, y, 100, 20);
      
      // Quality bar
      ctx.fillStyle = quality.color;
      ctx.fillRect(x + 2, y + 2, (100 - 4) * quality.value, 16);
      
      // Label
      ctx.fillStyle = 'white';
      ctx.font = '11px Inter';
      ctx.fillText(`${quality.label}: ${(quality.value * 100).toFixed(0)}%`, x + 5, y + 13);
    });
  };
  
  // Render safe zones
  const renderSafeZones = (ctx: CanvasRenderingContext2D) => {
    ctx.save();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);
    
    // Title safe zone (90% of frame)
    const titleSafeMargin = 0.05;
    const titleSafeX = width * titleSafeMargin;
    const titleSafeY = height * titleSafeMargin;
    const titleSafeWidth = width * (1 - titleSafeMargin * 2);
    const titleSafeHeight = height * (1 - titleSafeMargin * 2);
    
    ctx.strokeRect(titleSafeX, titleSafeY, titleSafeWidth, titleSafeHeight);
    
    // Action safe zone (80% of frame)
    const actionSafeMargin = 0.1;
    const actionSafeX = width * actionSafeMargin;
    const actionSafeY = height * actionSafeMargin;
    const actionSafeWidth = width * (1 - actionSafeMargin * 2);
    const actionSafeHeight = height * (1 - actionSafeMargin * 2);
    
    ctx.strokeRect(actionSafeX, actionSafeY, actionSafeWidth, actionSafeHeight);
    
    // Center lines
    ctx.beginPath();
    ctx.moveTo(width / 2, 0);
    ctx.lineTo(width / 2, height);
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
    
    ctx.restore();
  };
  
  // Handle canvas click for seeking
  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onSeek) return;
    
    // Check if click is on progress bar
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    const progressX = width - 220;
    const progressY = height - 40;
    const progressWidth = 200;
    const progressHeight = 6;
    
    // Scale click coordinates to canvas size
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    const canvasX = clickX * scaleX;
    const canvasY = clickY * scaleY;
    
    if (canvasX >= progressX && canvasX <= progressX + progressWidth &&
        canvasY >= progressY && canvasY <= progressY + progressHeight) {
      // Click on progress bar
      const progress = (canvasX - progressX) / progressWidth;
      const seekTime = Math.max(0, Math.min(duration, progress * duration));
      onSeek(seekTime);
    }
  }, [onSeek, width, height, duration]);
  
  // Re-render when props change
  useEffect(() => {
    renderOverlay();
  }, [renderOverlay]);
  
  return (
    <canvas
      ref={canvasRef}
      className={`video-player-overlay ${className}`}
      style={{ width: '100%', height: '100%' }}
      onClick={handleClick}
    />
  );
};

// Helper function to format time
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}