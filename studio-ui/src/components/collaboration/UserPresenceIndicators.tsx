/**
 * User Presence Indicators - Phase 4B
 * Visual indicators for collaborative editing with user cursors and selections
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useCollaborationContext } from './CollaborationProvider';
import { UserCursor, UserSelection } from '@/types';

interface UserPresenceIndicatorsProps {
  containerRef?: React.RefObject<HTMLDivElement>;
  className?: string;
}

export const UserPresenceIndicators: React.FC<UserPresenceIndicatorsProps> = ({
  containerRef,
  className = '',
}) => {
  const { 
    users, 
    userCursors, 
    userSelections, 
    isConnected,
    connectionState 
  } = useCollaborationContext();

  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // Track mouse movements for cursor updates
  useEffect(() => {
    if (!containerRef?.current || !isConnected) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = containerRef.current!.getBoundingClientRect();
      const position = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
      setMousePosition(position);
    };

    const container = containerRef.current;
    container.addEventListener('mousemove', handleMouseMove);

    return () => {
      container.removeEventListener('mousemove', handleMouseMove);
    };
  }, [containerRef, isConnected]);

  if (!isConnected) {
    return null;
  }

  return (
    <div className={`absolute inset-0 pointer-events-none z-20 ${className}`}>
      {/* User Cursors */}
      {Array.from(userCursors.values()).map((cursor) => (
        <UserCursorIndicator key={cursor.userId} cursor={cursor} />
      ))}

      {/* User Selections */}
      {Array.from(userSelections.values()).map((selection) => (
        <UserSelectionIndicator key={selection.userId} selection={selection} />
      ))}

      {/* Connection Status */}
      <ConnectionStatusIndicator state={connectionState} userCount={users.length} />
    </div>
  );
};

/**
 * Individual user cursor indicator
 */
const UserCursorIndicator: React.FC<{ cursor: UserCursor }> = ({ cursor }) => {
  const [isVisible, setIsVisible] = useState(true);

  // Hide cursor after inactivity
  useEffect(() => {
    const timeout = setTimeout(() => {
      const timeSinceUpdate = Date.now() - cursor.timestamp;
      if (timeSinceUpdate > 5000) { // 5 seconds
        setIsVisible(false);
      }
    }, 5000);

    return () => clearTimeout(timeout);
  }, [cursor.timestamp]);

  if (!isVisible) return null;

  return (
    <div
      className="absolute transition-all duration-150 ease-out pointer-events-none"
      style={{
        left: cursor.position.x,
        top: cursor.position.y,
        transform: 'translate(-2px, -2px)',
      }}
    >
      {/* Cursor Arrow */}
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        className="drop-shadow-sm"
        style={{ color: cursor.color }}
      >
        <path
          d="M0 0l4 12 3-2 4 4 2-2-4-4 2-3L0 0z"
          fill="currentColor"
          stroke="white"
          strokeWidth="1"
        />
      </svg>

      {/* User Name Label */}
      <div
        className="absolute top-4 left-2 px-2 py-1 rounded text-xs text-white font-medium whitespace-nowrap shadow-lg"
        style={{ backgroundColor: cursor.color }}
      >
        {cursor.userName}
      </div>
    </div>
  );
};

/**
 * User selection indicator for timeline clips
 */
const UserSelectionIndicator: React.FC<{ selection: UserSelection }> = ({ selection }) => {
  // This would need integration with timeline component to show selected clips
  // For now, we'll show a simple indicator

  return (
    <div className="absolute top-2 right-2 flex items-center gap-2 bg-black/60 backdrop-blur-sm text-white px-2 py-1 rounded-lg text-xs">
      <div
        className="w-3 h-3 rounded-full"
        style={{ backgroundColor: selection.color }}
      />
      <span>{selection.userName}</span>
      <span className="text-white/60">
        {selection.selectedClips.length} clip{selection.selectedClips.length !== 1 ? 's' : ''}
      </span>
    </div>
  );
};

/**
 * Connection status indicator
 */
const ConnectionStatusIndicator: React.FC<{
  state: string;
  userCount: number;
}> = ({ state, userCount }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-400';
      case 'connecting': return 'text-yellow-400';
      case 'disconnected': return 'text-gray-400';
      case 'error': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        );
      case 'connecting':
        return (
          <svg className="w-4 h-4 animate-spin" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  return (
    <div className="absolute top-2 left-2 flex items-center gap-2 bg-black/60 backdrop-blur-sm text-white px-3 py-2 rounded-lg text-sm">
      <div className={`flex items-center gap-2 ${getStatusColor(state)}`}>
        {getStatusIcon(state)}
        <span className="capitalize">{state}</span>
      </div>
      
      {state === 'connected' && userCount > 0 && (
        <>
          <div className="w-px h-4 bg-white/20" />
          <div className="flex items-center gap-1 text-white/80">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
            </svg>
            <span>{userCount}</span>
          </div>
        </>
      )}
    </div>
  );
};

/**
 * User list sidebar component
 */
export const UserListSidebar: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const { users, isConnected } = useCollaborationContext();

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-editor-surface border-l border-editor-border shadow-xl z-50">
      <div className="flex items-center justify-between p-4 border-b border-editor-border">
        <h3 className="text-lg font-semibold text-editor-text-primary">
          Collaboration ({users.length})
        </h3>
        <button
          onClick={onClose}
          className="text-editor-text-secondary hover:text-editor-text-primary transition-colors"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      <div className="p-4">
        {!isConnected ? (
          <div className="text-center text-editor-text-secondary">
            <p>Not connected to collaboration server</p>
          </div>
        ) : users.length === 0 ? (
          <div className="text-center text-editor-text-secondary">
            <p>No other users online</p>
          </div>
        ) : (
          <div className="space-y-3">
            {users.map((user) => (
              <div
                key={user.id}
                className="flex items-center gap-3 p-3 bg-editor-background rounded-lg"
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: user.color }}
                />
                <div className="flex-1">
                  <div className="font-medium text-editor-text-primary">
                    {user.name}
                  </div>
                  <div className="text-sm text-editor-text-secondary capitalize">
                    {user.role} • {user.isOnline ? 'Online' : 'Offline'}
                  </div>
                </div>
                {user.isOnline && (
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};