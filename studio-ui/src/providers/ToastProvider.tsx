/**
 * Toast Provider - Phase 4
 * Toast notification system for user feedback
 */

'use client';

import React, { createContext, useContext, useState, useCallback, useId } from 'react';
import { createPortal } from 'react-dom';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
  success: (title: string, message?: string, options?: Partial<Toast>) => string;
  error: (title: string, message?: string, options?: Partial<Toast>) => string;
  warning: (title: string, message?: string, options?: Partial<Toast>) => string;
  info: (title: string, message?: string, options?: Partial<Toast>) => string;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

interface ToastProviderProps {
  children: React.ReactNode;
  maxToasts?: number;
  defaultDuration?: number;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({
  children,
  maxToasts = 5,
  defaultDuration = 5000,
}) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  // Add toast
  const addToast = useCallback((toast: Omit<Toast, 'id'>): string => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? defaultDuration,
    };
    
    setToasts(prevToasts => {
      const newToasts = [newToast, ...prevToasts];
      // Limit number of toasts
      return newToasts.slice(0, maxToasts);
    });
    
    // Auto-remove toast after duration
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, newToast.duration);
    }
    
    return id;
  }, [defaultDuration, maxToasts]);
  
  // Remove toast
  const removeToast = useCallback((id: string) => {
    setToasts(prevToasts => prevToasts.filter(toast => toast.id !== id));
  }, []);
  
  // Clear all toasts
  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);
  
  // Convenience methods
  const success = useCallback((title: string, message?: string, options?: Partial<Toast>): string => {
    return addToast({ ...options, type: 'success', title, message });
  }, [addToast]);
  
  const error = useCallback((title: string, message?: string, options?: Partial<Toast>): string => {
    return addToast({ ...options, type: 'error', title, message, duration: options?.duration ?? 0 }); // Errors persist by default
  }, [addToast]);
  
  const warning = useCallback((title: string, message?: string, options?: Partial<Toast>): string => {
    return addToast({ ...options, type: 'warning', title, message });
  }, [addToast]);
  
  const info = useCallback((title: string, message?: string, options?: Partial<Toast>): string => {
    return addToast({ ...options, type: 'info', title, message });
  }, [addToast]);
  
  const value: ToastContextType = {
    toasts,
    addToast,
    removeToast,
    clearAll,
    success,
    error,
    warning,
    info,
  };
  
  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

// Toast container component
const ToastContainer: React.FC<{
  toasts: Toast[];
  onRemove: (id: string) => void;
}> = ({ toasts, onRemove }) => {
  // Render toasts in portal
  if (typeof window === 'undefined') return null;
  
  return createPortal(
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {toasts.map((toast) => (
        <ToastComponent key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>,
    document.body
  );
};

// Individual toast component
const ToastComponent: React.FC<{
  toast: Toast;
  onRemove: (id: string) => void;
}> = ({ toast, onRemove }) => {
  const getToastStyles = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-editor-success border-editor-success text-white';
      case 'error':
        return 'bg-editor-error border-editor-error text-white';
      case 'warning':
        return 'bg-editor-warning border-editor-warning text-white';
      case 'info':
        return 'bg-editor-accent border-editor-accent text-white';
      default:
        return 'bg-editor-surface border-editor-border text-editor-text-primary';
    }
  };
  
  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return '✓';
      case 'error':
        return '✕';
      case 'warning':
        return '⚠';
      case 'info':
        return 'ℹ';
      default:
        return '';
    }
  };
  
  return (
    <div
      className={`
        ${getToastStyles()}
        p-4 rounded-lg border shadow-lg min-w-0 max-w-sm
        animate-slide-down transform transition-all duration-300
      `}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
          {getIcon()}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm">{toast.title}</div>
          {toast.message && (
            <div className="text-sm opacity-90 mt-1">{toast.message}</div>
          )}
          
          {/* Action button */}
          {toast.action && (
            <button
              onClick={toast.action.onClick}
              className="mt-2 text-sm underline hover:no-underline"
            >
              {toast.action.label}
            </button>
          )}
        </div>
        
        {/* Close button */}
        <button
          onClick={() => onRemove(toast.id)}
          className="flex-shrink-0 w-5 h-5 flex items-center justify-center opacity-70 hover:opacity-100 transition-opacity"
          aria-label="Close notification"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

// Hook to use toast context
export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};