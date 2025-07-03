/**
 * Keyboard Shortcuts Hook - Phase 4
 * Custom hook for handling keyboard shortcuts in video editor
 */

import { useEffect, useCallback } from 'react';
import { KeyboardShortcut } from '@/types';

export interface UseKeyboardShortcutsOptions {
  enabled?: boolean;
  preventDefault?: boolean;
  stopPropagation?: boolean;
}

export const useKeyboardShortcuts = (
  shortcuts: KeyboardShortcut[],
  options: UseKeyboardShortcutsOptions = {}
) => {
  const {
    enabled = true,
    preventDefault = true,
    stopPropagation = false,
  } = options;
  
  // Check if key combination matches shortcut
  const matchesShortcut = useCallback((event: KeyboardEvent, shortcut: KeyboardShortcut): boolean => {
    // Check main key
    if (event.key !== shortcut.key && event.code !== shortcut.key) {
      return false;
    }
    
    // Check modifier keys
    if (!!event.metaKey !== !!shortcut.metaKey) return false;
    if (!!event.ctrlKey !== !!shortcut.ctrlKey) return false;
    if (!!event.shiftKey !== !!shortcut.shiftKey) return false;
    if (!!event.altKey !== !!shortcut.altKey) return false;
    
    return true;
  }, []);
  
  // Handle keyboard events
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;
    
    // Don't trigger shortcuts when typing in inputs
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.contentEditable === 'true'
    ) {
      return;
    }
    
    // Find matching shortcut
    const matchingShortcut = shortcuts.find(shortcut => matchesShortcut(event, shortcut));
    
    if (matchingShortcut) {
      if (preventDefault) {
        event.preventDefault();
      }
      
      if (stopPropagation) {
        event.stopPropagation();
      }
      
      // Execute shortcut handler
      try {
        matchingShortcut.handler();
      } catch (error) {
        console.error('Error executing keyboard shortcut:', error);
      }
    }
  }, [enabled, shortcuts, matchesShortcut, preventDefault, stopPropagation]);
  
  // Add/remove event listeners
  useEffect(() => {
    if (!enabled || shortcuts.length === 0) return;
    
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, shortcuts, handleKeyDown]);
  
  // Return utility functions for managing shortcuts
  return {
    // Check if a key combination is already bound
    isKeyBound: useCallback((key: string, modifiers: Partial<Pick<KeyboardShortcut, 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey'>> = {}): boolean => {
      return shortcuts.some(shortcut => 
        shortcut.key === key &&
        !!shortcut.metaKey === !!modifiers.metaKey &&
        !!shortcut.ctrlKey === !!modifiers.ctrlKey &&
        !!shortcut.shiftKey === !!modifiers.shiftKey &&
        !!shortcut.altKey === !!modifiers.altKey
      );
    }, [shortcuts]),
    
    // Get shortcut description for help/documentation
    getShortcutDescription: useCallback((action: string): string | undefined => {
      const shortcut = shortcuts.find(s => s.action === action);
      return shortcut?.description;
    }, [shortcuts]),
    
    // Format shortcut key combination for display
    formatShortcut: useCallback((shortcut: KeyboardShortcut): string => {
      const parts: string[] = [];
      
      if (shortcut.metaKey) parts.push('⌘');
      if (shortcut.ctrlKey) parts.push('Ctrl');
      if (shortcut.altKey) parts.push('Alt');
      if (shortcut.shiftKey) parts.push('Shift');
      
      // Format key for display
      let keyDisplay = shortcut.key;
      switch (shortcut.key) {
        case ' ':
          keyDisplay = 'Space';
          break;
        case 'ArrowLeft':
          keyDisplay = '←';
          break;
        case 'ArrowRight':
          keyDisplay = '→';
          break;
        case 'ArrowUp':
          keyDisplay = '↑';
          break;
        case 'ArrowDown':
          keyDisplay = '↓';
          break;
        default:
          keyDisplay = shortcut.key.toUpperCase();
      }
      
      parts.push(keyDisplay);
      return parts.join(' + ');
    }, []),
  };
};

// Common keyboard shortcuts for video editors
export const COMMON_SHORTCUTS: KeyboardShortcut[] = [
  {
    key: ' ',
    action: 'playPause',
    description: 'Play/Pause',
    handler: () => {}, // Will be overridden
  },
  {
    key: 'j',
    action: 'previousFrame',
    description: 'Previous frame',
    handler: () => {},
  },
  {
    key: 'k', 
    action: 'playPause',
    description: 'Play/Pause',
    handler: () => {},
  },
  {
    key: 'l',
    action: 'nextFrame',
    description: 'Next frame',
    handler: () => {},
  },
  {
    key: 'ArrowLeft',
    action: 'seekBackward',
    description: 'Seek backward 5s',
    handler: () => {},
  },
  {
    key: 'ArrowRight',
    action: 'seekForward',
    description: 'Seek forward 5s',
    handler: () => {},
  },
  {
    key: 'Home',
    action: 'seekStart',
    description: 'Go to start',
    handler: () => {},
  },
  {
    key: 'End',
    action: 'seekEnd',
    description: 'Go to end',
    handler: () => {},
  },
  {
    key: 'z',
    ctrlKey: true,
    action: 'undo',
    description: 'Undo',
    handler: () => {},
  },
  {
    key: 'y',
    ctrlKey: true,
    action: 'redo',
    description: 'Redo',
    handler: () => {},
  },
  {
    key: 'a',
    ctrlKey: true,
    action: 'selectAll',
    description: 'Select all clips',
    handler: () => {},
  },
  {
    key: 'c',
    ctrlKey: true,
    action: 'copy',
    description: 'Copy selected clips',
    handler: () => {},
  },
  {
    key: 'v',
    ctrlKey: true,
    action: 'paste',
    description: 'Paste clips',
    handler: () => {},
  },
  {
    key: 'x',
    ctrlKey: true,
    action: 'cut',
    description: 'Cut selected clips',
    handler: () => {},
  },
  {
    key: 'Delete',
    action: 'delete',
    description: 'Delete selected clips',
    handler: () => {},
  },
  {
    key: 'Escape',
    action: 'clearSelection',
    description: 'Clear selection',
    handler: () => {},
  },
];