/**
 * Quality Indicators - Phase 4 Essential UI Component
 * Real-time quality visualization for timeline clips
 */

'use client';

import React, { useRef, useEffect, useCallback } from 'react';
import { QualityMetrics, QualityThresholds } from '@/types';

interface QualityIndicatorsProps {
  quality: QualityMetrics;
  width: number;
  height?: number;
  thresholds?: QualityThresholds;
  showLabels?: boolean;
  orientation?: 'horizontal' | 'vertical';
  className?: string;
}

// Default quality thresholds
const DEFAULT_THRESHOLDS: QualityThresholds = {
  excellent: 0.85,
  good: 0.7,
  fair: 0.5,
  poor: 0.3,
};

export const QualityIndicators: React.FC<QualityIndicatorsProps> = ({
  quality,
  width,
  height = 60,
  thresholds = DEFAULT_THRESHOLDS,
  showLabels = true,
  orientation = 'horizontal',
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Get color based on quality score and thresholds
  const getQualityColor = useCallback((score: number): string => {
    if (score >= thresholds.excellent) return '#10b981'; // Green
    if (score >= thresholds.good) return '#3b82f6'; // Blue
    if (score >= thresholds.fair) return '#f59e0b'; // Yellow
    if (score >= thresholds.poor) return '#f97316'; // Orange
    return '#ef4444'; // Red
  }, [thresholds]);
  
  // Get quality rating text
  const getQualityRating = useCallback((score: number): string => {
    if (score >= thresholds.excellent) return 'Excellent';
    if (score >= thresholds.good) return 'Good';
    if (score >= thresholds.fair) return 'Fair';
    if (score >= thresholds.poor) return 'Poor';
    return 'Low';
  }, [thresholds]);
  
  // Render quality indicators
  const renderIndicators = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas size with device pixel ratio
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Quality metrics to display
    const metrics = [
      { label: 'Overall', value: quality.overall },
      { label: 'Audio', value: quality.audio },
      { label: 'Visual', value: quality.visual },
      { label: 'Semantic', value: quality.semantic },
      { label: 'Engagement', value: quality.engagement },
    ];
    
    if (orientation === 'horizontal') {
      renderHorizontalIndicators(ctx, metrics);
    } else {
      renderVerticalIndicators(ctx, metrics);
    }
  }, [width, height, quality, orientation, showLabels]);
  
  // Render horizontal layout
  const renderHorizontalIndicators = (ctx: CanvasRenderingContext2D, metrics: Array<{label: string, value: number}>) => {
    const barHeight = 8;
    const spacing = 12;
    const labelHeight = showLabels ? 10 : 0;
    const startY = labelHeight + 2;
    
    metrics.forEach((metric, index) => {
      const y = startY + index * spacing;
      const barWidth = width - (showLabels ? 60 : 10);
      const progressWidth = barWidth * metric.value;
      
      // Background bar
      ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.fillRect(showLabels ? 50 : 5, y, barWidth, barHeight);
      
      // Progress bar
      ctx.fillStyle = getQualityColor(metric.value);
      ctx.fillRect(showLabels ? 50 : 5, y, progressWidth, barHeight);
      
      // Border
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.lineWidth = 1;
      ctx.strokeRect(showLabels ? 50 : 5, y, barWidth, barHeight);
      
      if (showLabels) {
        // Label
        ctx.fillStyle = '#ffffff';
        ctx.font = '10px Inter';
        ctx.textAlign = 'right';
        ctx.fillText(metric.label, 45, y + 6);
        
        // Value
        ctx.textAlign = 'left';
        ctx.fillText(`${(metric.value * 100).toFixed(0)}%`, showLabels ? 50 : 5 + barWidth + 5, y + 6);
      }
    });
  };
  
  // Render vertical layout
  const renderVerticalIndicators = (ctx: CanvasRenderingContext2D, metrics: Array<{label: string, value: number}>) => {
    const barWidth = Math.floor((width - 10) / metrics.length) - 2;
    const maxBarHeight = height - (showLabels ? 20 : 5);
    
    metrics.forEach((metric, index) => {
      const x = 5 + index * (barWidth + 2);
      const barHeight = maxBarHeight * metric.value;
      const y = height - barHeight - (showLabels ? 15 : 5);
      
      // Background bar
      ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.fillRect(x, height - maxBarHeight - (showLabels ? 15 : 5), barWidth, maxBarHeight);
      
      // Progress bar
      ctx.fillStyle = getQualityColor(metric.value);
      ctx.fillRect(x, y, barWidth, barHeight);
      
      // Border
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.lineWidth = 1;
      ctx.strokeRect(x, height - maxBarHeight - (showLabels ? 15 : 5), barWidth, maxBarHeight);
      
      if (showLabels) {
        // Label
        ctx.fillStyle = '#ffffff';
        ctx.font = '8px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(metric.label.substr(0, 3), x + barWidth / 2, height - 2);
      }
    });
  };
  
  // Re-render when props change
  useEffect(() => {
    renderIndicators();
  }, [renderIndicators]);
  
  return (
    <div className={`quality-indicators ${className}`}>
      <canvas
        ref={canvasRef}
        className="quality-indicators-canvas"
        style={{ width, height }}
        role="img"
        aria-label={`Quality metrics: Overall ${getQualityRating(quality.overall)}`}
      />
      
      {/* Overall quality badge */}
      <div 
        className="absolute top-1 right-1 px-1.5 py-0.5 rounded text-xs font-medium text-white"
        style={{ backgroundColor: getQualityColor(quality.overall) }}
      >
        {getQualityRating(quality.overall)}
      </div>
    </div>
  );
};

// Compact quality indicator for timeline clips
export const CompactQualityIndicator: React.FC<{
  quality: QualityMetrics;
  size?: number;
  className?: string;
}> = ({ quality, size = 20, className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const getQualityColor = (score: number): string => {
    if (score >= 0.85) return '#10b981';
    if (score >= 0.7) return '#3b82f6';
    if (score >= 0.5) return '#f59e0b';
    if (score >= 0.3) return '#f97316';
    return '#ef4444';
  };
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear canvas
    ctx.clearRect(0, 0, size, size);
    
    // Draw circular progress
    const centerX = size / 2;
    const centerY = size / 2;
    const radius = (size - 4) / 2;
    
    // Background circle
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.stroke();
    
    // Progress arc
    const progress = quality.overall * 2 * Math.PI - Math.PI / 2;
    ctx.strokeStyle = getQualityColor(quality.overall);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, progress);
    ctx.stroke();
    
    // Center dot
    ctx.fillStyle = getQualityColor(quality.overall);
    ctx.beginPath();
    ctx.arc(centerX, centerY, 2, 0, 2 * Math.PI);
    ctx.fill();
  }, [quality.overall, size]);
  
  return (
    <canvas
      ref={canvasRef}
      className={`compact-quality-indicator ${className}`}
      style={{ width: size, height: size }}
      title={`Quality: ${(quality.overall * 100).toFixed(0)}%`}
    />
  );
};

// Quality trend chart for showing quality over time
export const QualityTrendChart: React.FC<{
  qualityHistory: QualityMetrics[];
  width: number;
  height: number;
  className?: string;
}> = ({ qualityHistory, width, height, className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || qualityHistory.length === 0) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw trend line for overall quality
    const stepX = width / (qualityHistory.length - 1);
    const maxY = height - 10;
    
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    qualityHistory.forEach((quality, index) => {
      const x = index * stepX;
      const y = maxY - (quality.overall * (maxY - 10));
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    
    ctx.stroke();
    
    // Draw grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    
    // Horizontal grid lines
    for (let i = 0; i <= 4; i++) {
      const y = (maxY / 4) * i + 5;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }, [qualityHistory, width, height]);
  
  return (
    <canvas
      ref={canvasRef}
      className={`quality-trend-chart ${className}`}
      style={{ width, height }}
      aria-label="Quality trend over time"
    />
  );
};