/**
 * Confidence Indicator - Phase 4 AI Integration Component
 * Visual confidence indicators for AI decisions and predictions
 */

'use client';

import React, { useRef, useEffect, useCallback } from 'react';

interface ConfidenceIndicatorProps {
  confidence: number;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'circular' | 'linear' | 'arc' | 'gradient';
  showLabel?: boolean;
  showPercentage?: boolean;
  animated?: boolean;
  threshold?: {
    excellent?: number;
    good?: number;
    fair?: number;
    poor?: number;
  };
  className?: string;
}

const DEFAULT_THRESHOLDS = {
  excellent: 0.85,
  good: 0.7,
  fair: 0.5,
  poor: 0.3,
};

export const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({
  confidence,
  size = 'md',
  variant = 'circular',
  showLabel = false,
  showPercentage = false,
  animated = true,
  threshold = DEFAULT_THRESHOLDS,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Get confidence level and color
  const getConfidenceLevel = useCallback(() => {
    if (confidence >= threshold.excellent!) return { level: 'excellent', color: '#10b981' };
    if (confidence >= threshold.good!) return { level: 'good', color: '#3b82f6' };
    if (confidence >= threshold.fair!) return { level: 'fair', color: '#f59e0b' };
    if (confidence >= threshold.poor!) return { level: 'poor', color: '#f97316' };
    return { level: 'low', color: '#ef4444' };
  }, [confidence, threshold]);
  
  // Get size dimensions
  const getSizeDimensions = useCallback(() => {
    switch (size) {
      case 'xs': return { width: 16, height: 16, stroke: 2 };
      case 'sm': return { width: 24, height: 24, stroke: 2 };
      case 'md': return { width: 32, height: 32, stroke: 3 };
      case 'lg': return { width: 48, height: 48, stroke: 4 };
      case 'xl': return { width: 64, height: 64, stroke: 5 };
      default: return { width: 32, height: 32, stroke: 3 };
    }
  }, [size]);
  
  // Render circular indicator
  const renderCircular = useCallback((ctx: CanvasRenderingContext2D, dimensions: any) => {
    const { width, height, stroke } = dimensions;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = (Math.min(width, height) - stroke * 2) / 2;
    const { color } = getConfidenceLevel();
    
    // Background circle
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = stroke;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.stroke();
    
    // Progress arc
    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + (confidence * 2 * Math.PI);
    
    ctx.strokeStyle = color;
    ctx.lineWidth = stroke;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.stroke();
    
    // Center dot (optional)
    if (size !== 'xs') {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(centerX, centerY, 2, 0, 2 * Math.PI);
      ctx.fill();
    }
  }, [confidence, getConfidenceLevel, size]);
  
  // Render linear indicator
  const renderLinear = useCallback((ctx: CanvasRenderingContext2D, dimensions: any) => {
    const { width, height, stroke } = dimensions;
    const { color } = getConfidenceLevel();
    const barHeight = Math.min(height, stroke * 2);
    const y = (height - barHeight) / 2;
    
    // Background bar
    ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.fillRect(0, y, width, barHeight);
    
    // Progress bar
    ctx.fillStyle = color;
    ctx.fillRect(0, y, width * confidence, barHeight);
    
    // Border
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.strokeRect(0, y, width, barHeight);
  }, [confidence, getConfidenceLevel]);
  
  // Render arc indicator
  const renderArc = useCallback((ctx: CanvasRenderingContext2D, dimensions: any) => {
    const { width, height, stroke } = dimensions;
    const centerX = width / 2;
    const centerY = height - 5;
    const radius = Math.min(width, height) / 2 - stroke;
    const { color } = getConfidenceLevel();
    
    // Background arc
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = stroke;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, Math.PI, 0);
    ctx.stroke();
    
    // Progress arc
    const startAngle = Math.PI;
    const endAngle = startAngle + (confidence * Math.PI);
    
    ctx.strokeStyle = color;
    ctx.lineWidth = stroke;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.stroke();
  }, [confidence, getConfidenceLevel]);
  
  // Render gradient indicator
  const renderGradient = useCallback((ctx: CanvasRenderingContext2D, dimensions: any) => {
    const { width, height } = dimensions;
    const { color } = getConfidenceLevel();
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.8)'); // Red
    gradient.addColorStop(0.3, 'rgba(249, 115, 22, 0.8)'); // Orange
    gradient.addColorStop(0.5, 'rgba(245, 158, 11, 0.8)'); // Yellow
    gradient.addColorStop(0.7, 'rgba(59, 130, 246, 0.8)'); // Blue
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.8)'); // Green
    
    // Background
    ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.fillRect(0, 0, width, height);
    
    // Gradient fill
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width * confidence, height);
    
    // Current position indicator
    const x = width * confidence;
    ctx.fillStyle = color;
    ctx.fillRect(x - 2, 0, 4, height);
  }, [confidence, getConfidenceLevel]);
  
  // Render indicator based on variant
  const renderIndicator = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const dimensions = getSizeDimensions();
    
    // Set canvas size with device pixel ratio
    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear canvas
    ctx.clearRect(0, 0, dimensions.width, dimensions.height);
    
    // Render based on variant
    switch (variant) {
      case 'circular':
        renderCircular(ctx, dimensions);
        break;
      case 'linear':
        renderLinear(ctx, dimensions);
        break;
      case 'arc':
        renderArc(ctx, dimensions);
        break;
      case 'gradient':
        renderGradient(ctx, dimensions);
        break;
    }
  }, [variant, getSizeDimensions, renderCircular, renderLinear, renderArc, renderGradient]);
  
  // Re-render when props change
  useEffect(() => {
    if (animated) {
      // Simple animation by gradually updating confidence
      let currentConf = 0;
      const targetConf = confidence;
      const step = targetConf / 20; // 20 frames
      
      const animate = () => {
        currentConf = Math.min(currentConf + step, targetConf);
        renderIndicator();
        
        if (currentConf < targetConf) {
          requestAnimationFrame(animate);
        }
      };
      
      animate();
    } else {
      renderIndicator();
    }
  }, [confidence, animated, renderIndicator]);
  
  const dimensions = getSizeDimensions();
  const { level, color } = getConfidenceLevel();
  
  return (
    <div className={`confidence-indicator flex items-center gap-2 ${className}`}>
      <canvas
        ref={canvasRef}
        style={{ width: dimensions.width, height: dimensions.height }}
        className="confidence-canvas"
      />
      
      {showLabel && (
        <span 
          className="text-sm font-medium capitalize"
          style={{ color }}
        >
          {level}
        </span>
      )}
      
      {showPercentage && (
        <span className="text-sm text-editor-text-secondary">
          {(confidence * 100).toFixed(0)}%
        </span>
      )}
    </div>
  );
};

// Confidence bar with multiple segments
export const ConfidenceBar: React.FC<{
  confidences: Array<{ label: string; value: number; color?: string }>;
  height?: number;
  showLabels?: boolean;
  className?: string;
}> = ({ confidences, height = 20, showLabels = true, className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const width = 200; // Fixed width for now
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw segments
    const segmentWidth = width / confidences.length;
    
    confidences.forEach((conf, index) => {
      const x = index * segmentWidth;
      const barHeight = height * conf.value;
      const y = height - barHeight;
      
      // Default color based on confidence
      let color = conf.color;
      if (!color) {
        if (conf.value >= 0.8) color = '#10b981';
        else if (conf.value >= 0.6) color = '#3b82f6';
        else if (conf.value >= 0.4) color = '#f59e0b';
        else color = '#ef4444';
      }
      
      // Background
      ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.fillRect(x, 0, segmentWidth - 1, height);
      
      // Progress
      ctx.fillStyle = color;
      ctx.fillRect(x, y, segmentWidth - 1, barHeight);
      
      // Label
      if (showLabels) {
        ctx.fillStyle = '#ffffff';
        ctx.font = '10px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(
          conf.label.substr(0, 3),
          x + segmentWidth / 2,
          height + 12
        );
      }
    });
  }, [confidences, height, showLabels]);
  
  return (
    <div className={`confidence-bar ${className}`}>
      <canvas
        ref={canvasRef}
        style={{ width: 200, height: height + (showLabels ? 15 : 0) }}
        className="confidence-bar-canvas"
      />
    </div>
  );
};

// Confidence trend chart
export const ConfidenceTrend: React.FC<{
  dataPoints: Array<{ time: number; confidence: number }>;
  width: number;
  height: number;
  className?: string;
}> = ({ dataPoints, width, height, className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || dataPoints.length === 0) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Calculate scales
    const maxTime = Math.max(...dataPoints.map(p => p.time));
    const minTime = Math.min(...dataPoints.map(p => p.time));
    const timeRange = maxTime - minTime || 1;
    
    // Draw grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    
    // Horizontal grid lines (confidence levels)
    for (let i = 0; i <= 4; i++) {
      const y = (height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    
    // Draw trend line
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    dataPoints.forEach((point, index) => {
      const x = ((point.time - minTime) / timeRange) * width;
      const y = height - (point.confidence * height);
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    
    ctx.stroke();
    
    // Draw confidence threshold lines
    const thresholds = [0.8, 0.6, 0.4];
    const colors = ['#10b981', '#f59e0b', '#ef4444'];
    
    thresholds.forEach((threshold, index) => {
      const y = height - (threshold * height);
      ctx.strokeStyle = colors[index];
      ctx.setLineDash([5, 5]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    });
    
    ctx.setLineDash([]);
  }, [dataPoints, width, height]);
  
  return (
    <canvas
      ref={canvasRef}
      style={{ width, height }}
      className={`confidence-trend ${className}`}
      aria-label="Confidence trend over time"
    />
  );
};

// Simple confidence badge
export const ConfidenceBadge: React.FC<{
  confidence: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}> = ({ confidence, size = 'md', className = '' }) => {
  const getColor = () => {
    if (confidence >= 0.8) return 'bg-editor-success text-white';
    if (confidence >= 0.6) return 'bg-editor-warning text-white';
    return 'bg-editor-error text-white';
  };
  
  const getSize = () => {
    switch (size) {
      case 'sm': return 'text-xs px-1.5 py-0.5';
      case 'md': return 'text-sm px-2 py-1';
      case 'lg': return 'text-base px-3 py-1.5';
      default: return 'text-sm px-2 py-1';
    }
  };
  
  return (
    <span className={`confidence-badge ${getColor()} ${getSize()} rounded-full font-medium ${className}`}>
      {(confidence * 100).toFixed(0)}%
    </span>
  );
};