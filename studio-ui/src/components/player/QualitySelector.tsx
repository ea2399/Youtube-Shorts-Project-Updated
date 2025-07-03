/**
 * Quality Selector - Phase 4 UI Component
 * Professional video quality selection with adaptive streaming support
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { VideoSource } from '@/types';

interface QualitySelectorProps {
  sources: VideoSource[];
  currentSource?: VideoSource;
  onSourceChange: (source: VideoSource) => void;
  className?: string;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

export const QualitySelector: React.FC<QualitySelectorProps> = ({
  sources,
  currentSource,
  onSourceChange,
  className = '',
  position = 'top-right',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [autoQuality, setAutoQuality] = useState(true);
  const [bandwidthEstimate, setBandwidthEstimate] = useState<number | null>(null);
  const selectorRef = useRef<HTMLDivElement>(null);

  // Sort sources by quality (highest first)
  const sortedSources = [...sources].sort((a, b) => {
    const qualityOrder = { '4K': 4, '1080p': 3, '720p': 2, '480p': 1, '240p': 0 };
    return (qualityOrder[b.quality] || 0) - (qualityOrder[a.quality] || 0);
  });

  // Get current source or auto-select best quality
  const activeSource = currentSource || sortedSources[0];

  // Auto quality selection based on bandwidth
  useEffect(() => {
    if (!autoQuality || !bandwidthEstimate) return;

    // Simple bandwidth-based quality selection
    let selectedSource: VideoSource;
    if (bandwidthEstimate > 5000) {
      selectedSource = sortedSources.find(s => s.quality === '1080p') || sortedSources[0];
    } else if (bandwidthEstimate > 2500) {
      selectedSource = sortedSources.find(s => s.quality === '720p') || sortedSources[0];
    } else if (bandwidthEstimate > 1000) {
      selectedSource = sortedSources.find(s => s.quality === '480p') || sortedSources[0];
    } else {
      selectedSource = sortedSources.find(s => s.quality === '240p') || sortedSources[0];
    }

    if (selectedSource && selectedSource !== activeSource) {
      onSourceChange(selectedSource);
    }
  }, [autoQuality, bandwidthEstimate, sortedSources, activeSource, onSourceChange]);

  // Estimate bandwidth (placeholder implementation)
  useEffect(() => {
    // In a real implementation, this would measure actual network performance
    const estimateBandwidth = () => {
      // Simulate bandwidth estimation
      const estimate = 1000 + Math.random() * 4000; // 1-5 Mbps
      setBandwidthEstimate(estimate);
    };

    const interval = setInterval(estimateBandwidth, 5000);
    estimateBandwidth(); // Initial estimate

    return () => clearInterval(interval);
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Position classes
  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
  };

  // Dropdown position classes
  const dropdownPositions = {
    'top-right': 'top-full mt-2 right-0',
    'top-left': 'top-full mt-2 left-0',
    'bottom-right': 'bottom-full mb-2 right-0',
    'bottom-left': 'bottom-full mb-2 left-0',
  };

  const handleSourceSelect = (source: VideoSource) => {
    setAutoQuality(false);
    onSourceChange(source);
    setIsOpen(false);
  };

  const handleAutoQuality = () => {
    setAutoQuality(true);
    setIsOpen(false);
  };

  // Get quality indicator color
  const getQualityColor = (quality: string) => {
    switch (quality) {
      case '4K': return 'text-purple-400';
      case '1080p': return 'text-blue-400';
      case '720p': return 'text-green-400';
      case '480p': return 'text-yellow-400';
      case '240p': return 'text-orange-400';
      default: return 'text-gray-400';
    }
  };

  // Format bitrate for display
  const formatBitrate = (bitrate: number) => {
    if (bitrate >= 1000) {
      return `${(bitrate / 1000).toFixed(1)}M`;
    }
    return `${bitrate}K`;
  };

  return (
    <div
      ref={selectorRef}
      className={`quality-selector absolute z-30 ${positionClasses[position]} ${className}`}
    >
      {/* Quality Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 bg-black/60 hover:bg-black/80 text-white px-3 py-2 rounded-lg transition-colors backdrop-blur-sm border border-white/10"
        aria-label="Select video quality"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M9 11H7v6h2v-6zm4 2h-2v4h2v-4zm4-4h-2v8h2V9zm2-2H5c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2z"/>
        </svg>
        
        <span className="text-sm font-medium">
          {autoQuality ? 'Auto' : activeSource?.quality}
        </span>
        
        {autoQuality && bandwidthEstimate && (
          <span className="text-xs text-white/60">
            ({formatBitrate(bandwidthEstimate)})
          </span>
        )}
        
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M7 10l5 5 5-5z"/>
        </svg>
      </button>

      {/* Quality Dropdown */}
      {isOpen && (
        <div className={`absolute ${dropdownPositions[position]} bg-black/90 backdrop-blur-sm border border-white/10 rounded-lg overflow-hidden min-w-[200px] shadow-xl`}>
          {/* Auto Quality Option */}
          <button
            onClick={handleAutoQuality}
            className={`w-full flex items-center justify-between px-4 py-3 hover:bg-white/10 transition-colors ${
              autoQuality ? 'bg-blue-500/20 text-blue-300' : 'text-white'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-sm font-medium">Auto</span>
            </div>
            <div className="text-xs text-white/60">
              {bandwidthEstimate ? formatBitrate(bandwidthEstimate) : 'Detecting...'}
            </div>
          </button>

          {/* Divider */}
          <div className="border-t border-white/10" />

          {/* Manual Quality Options */}
          {sortedSources.map((source) => (
            <button
              key={`${source.quality}-${source.bitrate}`}
              onClick={() => handleSourceSelect(source)}
              className={`w-full flex items-center justify-between px-4 py-3 hover:bg-white/10 transition-colors ${
                !autoQuality && source === activeSource ? 'bg-blue-500/20 text-blue-300' : 'text-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${getQualityColor(source.quality)}`} />
                <span className="text-sm font-medium">{source.quality}</span>
              </div>
              
              <div className="flex items-center gap-2 text-xs text-white/60">
                <span>{formatBitrate(source.bitrate)}</span>
                <span className="uppercase text-white/40">{source.type}</span>
              </div>
            </button>
          ))}

          {/* Quality Info Footer */}
          <div className="border-t border-white/10 px-4 py-2 bg-white/5">
            <div className="text-xs text-white/60 flex items-center gap-2">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              <span>Auto adjusts based on connection</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Network quality indicator component
export const NetworkQualityIndicator: React.FC<{
  bandwidth: number | null;
  className?: string;
}> = ({ bandwidth, className = '' }) => {
  if (!bandwidth) return null;

  const getQualityLevel = (bw: number) => {
    if (bw > 5000) return { level: 'excellent', color: 'text-green-400', bars: 4 };
    if (bw > 2500) return { level: 'good', color: 'text-blue-400', bars: 3 };
    if (bw > 1000) return { level: 'fair', color: 'text-yellow-400', bars: 2 };
    return { level: 'poor', color: 'text-red-400', bars: 1 };
  };

  const quality = getQualityLevel(bandwidth);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((bar) => (
          <div
            key={bar}
            className={`w-1 h-3 rounded-sm ${
              bar <= quality.bars ? quality.color : 'text-white/20'
            } bg-current`}
          />
        ))}
      </div>
      <span className={`text-xs ${quality.color}`}>
        {quality.level.toUpperCase()}
      </span>
    </div>
  );
};

// Adaptive quality hint component
export const QualityHint: React.FC<{
  currentQuality: string;
  recommendedQuality: string;
  visible: boolean;
  onAccept?: () => void;
  onDismiss?: () => void;
}> = ({ currentQuality, recommendedQuality, visible, onAccept, onDismiss }) => {
  if (!visible || currentQuality === recommendedQuality) return null;

  return (
    <div className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-black/90 text-white px-4 py-3 rounded-lg border border-white/10 backdrop-blur-sm z-40">
      <div className="flex items-center gap-3">
        <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>
        
        <div className="flex-1">
          <div className="text-sm font-medium">
            Switch to {recommendedQuality} for better experience?
          </div>
          <div className="text-xs text-white/60">
            Network conditions suggest {recommendedQuality} quality
          </div>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={onAccept}
            className="text-xs bg-blue-500 hover:bg-blue-600 px-3 py-1 rounded transition-colors"
          >
            Switch
          </button>
          <button
            onClick={onDismiss}
            className="text-xs text-white/60 hover:text-white px-2 py-1"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};