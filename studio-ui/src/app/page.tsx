/**
 * Home Page - Phase 4
 * Main application entry point with project selection
 */

import { Suspense } from 'react';
import Link from 'next/link';

// Components
import { ProjectList } from '@/components/projects/ProjectList';
import { CreateProjectButton } from '@/components/projects/CreateProjectButton';
import { Header } from '@/components/layout/Header';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-editor-bg">
      <Header />
      
      <main className="container mx-auto px-6 py-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-editor-text-primary mb-4">
            YouTube Shorts Studio
          </h1>
          <p className="text-lg text-editor-text-secondary max-w-2xl mx-auto mb-8">
            Professional video editing interface with AI-powered cutting decisions and real-time collaboration
          </p>
          
          <div className="flex gap-4 justify-center">
            <CreateProjectButton />
            <Link
              href="/editor/demo"
              className="btn btn-secondary"
            >
              Try Demo
            </Link>
          </div>
        </div>
        
        {/* Projects Section */}
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-semibold text-editor-text-primary">
              Recent Projects
            </h2>
            <div className="flex gap-2">
              <button className="btn btn-ghost text-sm">
                All Projects
              </button>
              <button className="btn btn-ghost text-sm">
                Shared with Me
              </button>
            </div>
          </div>
          
          <Suspense 
            fallback={
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner className="w-8 h-8" />
                <span className="ml-3 text-editor-text-secondary">
                  Loading projects...
                </span>
              </div>
            }
          >
            <ProjectList />
          </Suspense>
        </div>
        
        {/* Features Highlight */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="text-center p-6 bg-editor-surface rounded-lg border border-editor-border">
            <div className="w-12 h-12 bg-editor-accent rounded-lg mx-auto mb-4 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-editor-text-primary mb-2">
              AI-Powered Editing
            </h3>
            <p className="text-editor-text-secondary">
              Intelligent cutting decisions with multi-modal fusion scoring and quality validation
            </p>
          </div>
          
          <div className="text-center p-6 bg-editor-surface rounded-lg border border-editor-border">
            <div className="w-12 h-12 bg-editor-success rounded-lg mx-auto mb-4 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-editor-text-primary mb-2">
              Frame-Accurate Timeline
            </h3>
            <p className="text-editor-text-secondary">
              Professional timeline editor with &lt;100ms response times and word-level precision
            </p>
          </div>
          
          <div className="text-center p-6 bg-editor-surface rounded-lg border border-editor-border">
            <div className="w-12 h-12 bg-editor-warning rounded-lg mx-auto mb-4 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-editor-text-primary mb-2">
              Real-Time Collaboration
            </h3>
            <p className="text-editor-text-secondary">
              Multi-user editing with live cursors, conflict resolution, and version history
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}