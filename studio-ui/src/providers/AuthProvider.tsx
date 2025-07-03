/**
 * Auth Provider - Phase 4
 * Authentication context and JWT token management
 */

'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '@/lib/api';
import { AuthUser, AuthTokens } from '@/types';

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (user: Partial<AuthUser>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const isAuthenticated = !!user;
  
  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (token) {
          // Verify token and get user info
          const userData = await authApi.getUser();
          setUser(userData);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        // Token is invalid, clear it
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
      } finally {
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, []);
  
  // Login function
  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await authApi.login(email, password);
      
      // Store tokens
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      
      // Set user
      setUser(response.user);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  // Logout function
  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with logout even if API call fails
    } finally {
      // Clear local state
      setUser(null);
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      setIsLoading(false);
    }
  }, []);
  
  // Refresh token function
  const refreshToken = useCallback(async () => {
    try {
      const refreshTokenValue = localStorage.getItem('refresh_token');
      if (!refreshTokenValue) {
        throw new Error('No refresh token available');
      }
      
      const response = await authApi.refresh(refreshTokenValue);
      localStorage.setItem('auth_token', response.access_token);
      
      // Optionally refresh user data
      const userData = await authApi.getUser();
      setUser(userData);
    } catch (error) {
      console.error('Token refresh failed:', error);
      // Force logout on refresh failure
      await logout();
      throw error;
    }
  }, [logout]);
  
  // Update user function
  const updateUser = useCallback((updates: Partial<AuthUser>) => {
    setUser(prevUser => prevUser ? { ...prevUser, ...updates } : null);
  }, []);
  
  // Auto refresh token before expiry
  useEffect(() => {
    if (!isAuthenticated) return;
    
    // Set up token refresh interval (refresh every 45 minutes if token expires in 1 hour)
    const refreshInterval = setInterval(() => {
      refreshToken().catch(error => {
        console.error('Auto token refresh failed:', error);
      });
    }, 45 * 60 * 1000); // 45 minutes
    
    return () => clearInterval(refreshInterval);
  }, [isAuthenticated, refreshToken]);
  
  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    refreshToken,
    updateUser,
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// HOC for protected routes
export const withAuth = <P extends object>(Component: React.ComponentType<P>) => {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading } = useAuth();
    
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="loading-spinner" />
          <span className="ml-3 text-editor-text-secondary">Loading...</span>
        </div>
      );
    }
    
    if (!isAuthenticated) {
      // Redirect to login or show login form
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h2 className="text-xl text-editor-text-primary mb-4">Authentication Required</h2>
            <p className="text-editor-text-secondary">Please log in to access this page.</p>
          </div>
        </div>
      );
    }
    
    return <Component {...props} />;
  };
};