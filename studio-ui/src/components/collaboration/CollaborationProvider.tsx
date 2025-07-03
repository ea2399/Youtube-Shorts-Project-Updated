/**
 * Collaboration Provider - Phase 4B
 * React context provider for real-time collaborative editing
 */

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { 
  CollaborationManager, 
  CollaborationConfig, 
  CollaborationUser, 
  ConnectionState,
  useCollaboration 
} from '@/lib/collaboration';
import { 
  UserCursor, 
  UserSelection, 
  EditOperation 
} from '@/types';

interface CollaborationContextValue {
  // Connection state
  isConnected: boolean;
  connectionState: ConnectionState;
  users: CollaborationUser[];
  
  // User interactions
  updateCursor: (position: { x: number; y: number }) => void;
  updateSelection: (clipIds: string[], currentTime: number) => void;
  applyOperation: (operation: Omit<EditOperation, 'id' | 'timestamp' | 'userId'>) => string;
  
  // Collaboration state
  userCursors: Map<string, UserCursor>;
  userSelections: Map<string, UserSelection>;
  pendingOperations: EditOperation[];
  
  // Connection control
  connect: () => Promise<void>;
  disconnect: () => void;
}

const CollaborationContext = createContext<CollaborationContextValue | null>(null);

interface CollaborationProviderProps {
  children: React.ReactNode;
  config: CollaborationConfig;
  enabled?: boolean;
}

export const CollaborationProvider: React.FC<CollaborationProviderProps> = ({
  children,
  config,
  enabled = true,
}) => {
  const [userCursors, setUserCursors] = useState<Map<string, UserCursor>>(new Map());
  const [userSelections, setUserSelections] = useState<Map<string, UserSelection>>(new Map());
  const [pendingOperations, setPendingOperations] = useState<EditOperation[]>([]);

  // Collaboration callbacks
  const handleUserJoined = useCallback((user: CollaborationUser) => {
    console.log('User joined:', user.name);
  }, []);

  const handleUserLeft = useCallback((userId: string) => {
    console.log('User left:', userId);
    setUserCursors(prev => {
      const next = new Map(prev);
      next.delete(userId);
      return next;
    });
    setUserSelections(prev => {
      const next = new Map(prev);
      next.delete(userId);
      return next;
    });
  }, []);

  const handleCursorMoved = useCallback((cursor: UserCursor) => {
    setUserCursors(prev => new Map(prev).set(cursor.userId, cursor));
  }, []);

  const handleSelectionChanged = useCallback((selection: UserSelection) => {
    setUserSelections(prev => new Map(prev).set(selection.userId, selection));
  }, []);

  const handleEditOperation = useCallback((operation: EditOperation) => {
    setPendingOperations(prev => [...prev, operation]);
  }, []);

  const handleConnectionStateChanged = useCallback((state: ConnectionState) => {
    console.log('Connection state changed:', state);
  }, []);

  const handleError = useCallback((error: Error) => {
    console.error('Collaboration error:', error);
  }, []);

  // Initialize collaboration hook
  const {
    manager,
    connectionState,
    users,
    connect,
    disconnect,
    updateCursor,
    updateSelection,
    applyOperation,
  } = useCollaboration(config, {
    onUserJoined: handleUserJoined,
    onUserLeft: handleUserLeft,
    onCursorMoved: handleCursorMoved,
    onSelectionChanged: handleSelectionChanged,
    onEditOperation: handleEditOperation,
    onConnectionStateChanged: handleConnectionStateChanged,
    onError: handleError,
  });

  // Auto-connect when enabled
  useEffect(() => {
    if (enabled && connectionState === 'disconnected') {
      connect().catch(console.error);
    }

    return () => {
      if (connectionState === 'connected') {
        disconnect();
      }
    };
  }, [enabled, connectionState, connect, disconnect]);

  // Process pending operations
  useEffect(() => {
    if (pendingOperations.length > 0) {
      // Process operations in order
      pendingOperations.forEach(operation => {
        // Apply operation to local state
        console.log('Processing operation:', operation);
      });
      
      // Clear processed operations after a delay
      const timeout = setTimeout(() => {
        setPendingOperations([]);
      }, 1000);
      
      return () => clearTimeout(timeout);
    }
  }, [pendingOperations]);

  const contextValue: CollaborationContextValue = {
    isConnected: connectionState === 'connected',
    connectionState,
    users,
    updateCursor,
    updateSelection,
    applyOperation,
    userCursors,
    userSelections,
    pendingOperations,
    connect,
    disconnect,
  };

  return (
    <CollaborationContext.Provider value={contextValue}>
      {children}
    </CollaborationContext.Provider>
  );
};

/**
 * Hook to use collaboration context
 */
export const useCollaborationContext = (): CollaborationContextValue => {
  const context = useContext(CollaborationContext);
  if (!context) {
    throw new Error('useCollaborationContext must be used within a CollaborationProvider');
  }
  return context;
};

/**
 * HOC to add collaboration to components
 */
export function withCollaboration<P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> {
  return function CollaborativeComponent(props: P) {
    const collaboration = useCollaborationContext();
    
    return (
      <Component 
        {...props} 
        collaboration={collaboration}
      />
    );
  };
}