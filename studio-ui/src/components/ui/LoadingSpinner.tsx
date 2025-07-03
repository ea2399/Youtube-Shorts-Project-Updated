/**
 * Loading Spinner - Phase 4 UI Component
 * Reusable loading indicator with multiple sizes and variants
 */

'use client';

import React from 'react';

interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'spinner' | 'dots' | 'bars' | 'pulse';
  color?: string;
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  variant = 'spinner',
  color = 'currentColor',
  className = '',
  label = 'Loading...',
}) => {
  const getSizeClasses = () => {
    switch (size) {
      case 'xs': return 'w-3 h-3';
      case 'sm': return 'w-4 h-4';
      case 'md': return 'w-6 h-6';
      case 'lg': return 'w-8 h-8';
      case 'xl': return 'w-12 h-12';
      default: return 'w-6 h-6';
    }
  };

  const renderSpinner = () => {
    switch (variant) {
      case 'spinner':
        return (
          <svg
            className={`${getSizeClasses()} animate-spin ${className}`}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            style={{ color }}
            role="status"
            aria-label={label}
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        );

      case 'dots':
        return (
          <div className={`flex space-x-1 ${className}`} role="status" aria-label={label}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={`${getSizeClasses()} rounded-full animate-bounce`}
                style={{ 
                  backgroundColor: color,
                  animationDelay: `${i * 0.1}s`
                }}
              />
            ))}
          </div>
        );

      case 'bars':
        return (
          <div className={`flex space-x-1 ${className}`} role="status" aria-label={label}>
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className={`w-1 animate-pulse`}
                style={{ 
                  height: size === 'xs' ? '12px' : size === 'sm' ? '16px' : size === 'md' ? '24px' : size === 'lg' ? '32px' : '48px',
                  backgroundColor: color,
                  animationDelay: `${i * 0.1}s`
                }}
              />
            ))}
          </div>
        );

      case 'pulse':
        return (
          <div
            className={`${getSizeClasses()} rounded-full animate-pulse ${className}`}
            style={{ backgroundColor: color }}
            role="status"
            aria-label={label}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="inline-flex items-center justify-center">
      {renderSpinner()}
      <span className="sr-only">{label}</span>
    </div>
  );
};

// Loading overlay component for full-screen loading
export const LoadingOverlay: React.FC<{
  isVisible: boolean;
  message?: string;
  className?: string;
}> = ({ isVisible, message = 'Loading...', className = '' }) => {
  if (!isVisible) return null;

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 ${className}`}>
      <div className="bg-editor-surface p-6 rounded-lg border border-editor-border flex flex-col items-center gap-4">
        <LoadingSpinner size="lg" />
        <p className="text-editor-text-primary text-sm">{message}</p>
      </div>
    </div>
  );
};

// Loading skeleton component
export const LoadingSkeleton: React.FC<{
  width?: string | number;
  height?: string | number;
  className?: string;
}> = ({ width = '100%', height = '20px', className = '' }) => {
  return (
    <div
      className={`animate-pulse bg-editor-border rounded ${className}`}
      style={{ width, height }}
      role="status"
      aria-label="Loading content..."
    />
  );
};