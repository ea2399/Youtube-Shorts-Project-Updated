/**
 * Theme Provider - Phase 4
 * Theme management and dark/light mode support
 */

'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeMode, ColorPalette } from '@/types';

interface ThemeContextType {
  mode: ThemeMode;
  effectiveMode: 'light' | 'dark';
  palette: ColorPalette;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Theme palettes
const DARK_PALETTE: ColorPalette = {
  primary: '#3b82f6',
  secondary: '#6366f1',
  accent: '#8b5cf6',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  background: '#0a0a0a',
  surface: '#1a1a1a',
  text: {
    primary: '#ffffff',
    secondary: '#a1a1aa',
    muted: '#71717a',
  },
};

const LIGHT_PALETTE: ColorPalette = {
  primary: '#2563eb',
  secondary: '#4f46e5',
  accent: '#7c3aed',
  success: '#059669',
  warning: '#d97706',
  error: '#dc2626',
  background: '#ffffff',
  surface: '#f9fafb',
  text: {
    primary: '#111827',
    secondary: '#4b5563',
    muted: '#6b7280',
  },
};

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultMode?: ThemeMode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  defaultMode = 'dark', // Default to dark mode for video editor
}) => {
  const [mode, setModeState] = useState<ThemeMode>(defaultMode);
  
  // Load saved theme from localStorage on mount
  useEffect(() => {
    const savedMode = localStorage.getItem('theme-mode') as ThemeMode;
    if (savedMode && ['light', 'dark', 'auto'].includes(savedMode)) {
      setModeState(savedMode);
    }
  }, []);
  
  // Determine effective mode (resolve 'auto' to 'light' or 'dark')
  const effectiveMode: 'light' | 'dark' = React.useMemo(() => {
    if (mode === 'auto') {
      // Use system preference
      if (typeof window !== 'undefined') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return 'dark'; // Default fallback
    }
    return mode;
  }, [mode]);
  
  // Get current palette
  const palette = effectiveMode === 'dark' ? DARK_PALETTE : LIGHT_PALETTE;
  
  // Set mode and save to localStorage
  const setMode = (newMode: ThemeMode) => {
    setModeState(newMode);
    localStorage.setItem('theme-mode', newMode);
  };
  
  // Toggle between light and dark (ignoring auto)
  const toggleMode = () => {
    const newMode = effectiveMode === 'dark' ? 'light' : 'dark';
    setMode(newMode);
  };
  
  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light', 'dark');
    
    // Add current theme class
    root.classList.add(effectiveMode);
    
    // Update CSS custom properties
    root.style.setProperty('--color-primary', palette.primary);
    root.style.setProperty('--color-secondary', palette.secondary);
    root.style.setProperty('--color-accent', palette.accent);
    root.style.setProperty('--color-success', palette.success);
    root.style.setProperty('--color-warning', palette.warning);
    root.style.setProperty('--color-error', palette.error);
    root.style.setProperty('--color-background', palette.background);
    root.style.setProperty('--color-surface', palette.surface);
    root.style.setProperty('--color-text-primary', palette.text.primary);
    root.style.setProperty('--color-text-secondary', palette.text.secondary);
    root.style.setProperty('--color-text-muted', palette.text.muted);
    
    // Update meta theme-color
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', palette.background);
    }
  }, [effectiveMode, palette]);
  
  // Listen for system theme changes when in auto mode
  useEffect(() => {
    if (mode !== 'auto') return;
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      // Force re-render to update effectiveMode
      setModeState('auto');
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [mode]);
  
  const value: ThemeContextType = {
    mode,
    effectiveMode,
    palette,
    setMode,
    toggleMode,
  };
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

// Hook to use theme context
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Theme toggle component
export const ThemeToggle: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { mode, effectiveMode, setMode, toggleMode } = useTheme();
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Mode selector */}
      <select
        value={mode}
        onChange={(e) => setMode(e.target.value as ThemeMode)}
        className="form-input text-sm"
      >
        <option value="light">Light</option>
        <option value="dark">Dark</option>
        <option value="auto">Auto</option>
      </select>
      
      {/* Quick toggle button */}
      <button
        onClick={toggleMode}
        className="w-8 h-8 rounded-full bg-editor-surface border border-editor-border flex items-center justify-center hover:bg-editor-border transition-colors"
        title={`Switch to ${effectiveMode === 'dark' ? 'light' : 'dark'} mode`}
      >
        {effectiveMode === 'dark' ? '🌙' : '☀️'}
      </button>
    </div>
  );
};