/**
 * React Query Provider - Phase 4
 * TanStack Query setup for server state management
 */

'use client';

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

// Create query client with optimized settings for video editing
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time for different data types
      staleTime: 5 * 60 * 1000, // 5 minutes default
      gcTime: 10 * 60 * 1000, // 10 minutes garbage collection
      
      // Retry configuration
      retry: (failureCount, error: any) => {
        // Don't retry 4xx errors except 429 (rate limit)
        if (error?.status >= 400 && error?.status < 500 && error?.status !== 429) {
          return false;
        }
        return failureCount < 3;
      },
      
      // Background refetch settings
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      refetchInterval: false,
      
      // Error handling
      throwOnError: false,
    },
    mutations: {
      // Retry mutations once on network errors
      retry: (failureCount, error: any) => {
        if (error?.name === 'NetworkError' || error?.status >= 500) {
          return failureCount < 1;
        }
        return false;
      },
      
      // Mutation error handling
      throwOnError: false,
    },
  },
});

// Custom error handling
queryClient.setMutationDefaults(['edl', 'create'], {
  mutationFn: async (variables: any) => {
    // Custom EDL creation with optimistic updates
    return variables;
  },
});

// Query key factories for consistent cache management
export const queryKeys = {
  // Videos
  videos: ['videos'] as const,
  video: (id: string) => ['videos', id] as const,
  videoClips: (id: string) => ['videos', id, 'clips'] as const,
  videoStatus: (id: string) => ['videos', id, 'status'] as const,
  
  // EDLs
  edls: ['edls'] as const,
  edl: (id: string) => ['edls', id] as const,
  videoEdls: (videoId: string) => ['edls', 'video', videoId] as const,
  edlCandidates: (edlId: string) => ['edls', edlId, 'candidates'] as const,
  
  // Quality reports
  qualityReports: ['quality-reports'] as const,
  qualityReport: (edlId: string) => ['quality-reports', edlId] as const,
  
  // User data
  user: ['user'] as const,
  userProjects: ['user', 'projects'] as const,
};

// Prefetch strategies for different routes
export const prefetchStrategies = {
  // Prefetch user projects on app load
  userProjects: () => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.userProjects,
      staleTime: 2 * 60 * 1000, // 2 minutes
    });
  },
  
  // Prefetch video data when opening editor
  videoEditor: (videoId: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.video(videoId),
      staleTime: 30 * 1000, // 30 seconds
    });
    
    queryClient.prefetchQuery({
      queryKey: queryKeys.videoEdls(videoId),
      staleTime: 60 * 1000, // 1 minute
    });
  },
  
  // Prefetch EDL details when hovering over EDL list item
  edlDetails: (edlId: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.edl(edlId),
      staleTime: 30 * 1000,
    });
  },
};

// Cache invalidation utilities
export const invalidateQueries = {
  // Invalidate all video-related data
  video: (videoId: string) => {
    queryClient.invalidateQueries({
      queryKey: ['videos', videoId],
    });
  },
  
  // Invalidate EDL data after updates
  edl: (edlId: string) => {
    queryClient.invalidateQueries({
      queryKey: ['edls', edlId],
    });
  },
  
  // Invalidate all user data
  user: () => {
    queryClient.invalidateQueries({
      queryKey: ['user'],
    });
  },
};

// Background sync for real-time updates
export const backgroundSync = {
  startEdlSync: (edlId: string) => {
    return queryClient.fetchQuery({
      queryKey: queryKeys.edl(edlId),
      refetchInterval: 5000, // 5 seconds
    });
  },
  
  stopSync: (queryKey: string[]) => {
    queryClient.cancelQueries({ queryKey });
  },
};

interface QueryProviderProps {
  children: React.ReactNode;
}

export const QueryProvider: React.FC<QueryProviderProps> = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools 
          initialIsOpen={false}
          position="bottom-right"
        />
      )}
    </QueryClientProvider>
  );
};

export { queryClient };