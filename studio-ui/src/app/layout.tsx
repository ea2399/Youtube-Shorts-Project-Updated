/**
 * Root Layout - Phase 4
 * Next.js 14 App Router root layout with providers
 */

import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

// Providers
import { QueryProvider } from '@/providers/QueryProvider';
import { AuthProvider } from '@/providers/AuthProvider';
import { ThemeProvider } from '@/providers/ThemeProvider';
import { ToastProvider } from '@/providers/ToastProvider';

// Fonts
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'YouTube Shorts Studio',
  description: 'Professional video editing interface for YouTube Shorts creation',
  keywords: ['video editing', 'youtube shorts', 'ai editing', 'timeline editor'],
  authors: [{ name: 'YouTube Shorts Editor Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0a' },
  ],
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body className="bg-editor-bg text-editor-text-primary antialiased">
        <ThemeProvider>
          <AuthProvider>
            <QueryProvider>
              <ToastProvider>
                <div id="app-root" className="min-h-screen">
                  {children}
                </div>
                
                {/* Portal containers */}
                <div id="modal-root" />
                <div id="tooltip-root" />
                <div id="dropdown-root" />
              </ToastProvider>
            </QueryProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}