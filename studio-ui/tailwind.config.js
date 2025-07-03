/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette for video editor
        editor: {
          bg: '#0a0a0a',
          surface: '#1a1a1a',
          border: '#333333',
          accent: '#3b82f6',
          success: '#10b981',
          warning: '#f59e0b',
          error: '#ef4444',
          text: {
            primary: '#ffffff',
            secondary: '#a1a1aa',
            muted: '#71717a',
          }
        },
        timeline: {
          bg: '#111111',
          track: '#1f1f1f',
          clip: '#2563eb',
          clipSelected: '#3b82f6',
          waveform: '#6366f1',
          marker: '#f59e0b',
          playhead: '#ef4444',
        },
        quality: {
          excellent: '#10b981',
          good: '#22c55e',
          fair: '#f59e0b',
          poor: '#ef4444',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace'],
      },
      animation: {
        'playhead': 'playhead 0.1s ease-out',
        'clip-select': 'clip-select 0.2s ease-out',
        'quality-pulse': 'quality-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        playhead: {
          '0%': { transform: 'scaleY(0.95)' },
          '100%': { transform: 'scaleY(1)' }
        },
        'clip-select': {
          '0%': { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(59, 130, 246, 0.5)' },
          '100%': { transform: 'scale(1.02)', boxShadow: '0 0 0 4px rgba(59, 130, 246, 0.2)' }
        },
        'quality-pulse': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.7 }
        }
      },
      spacing: {
        'timeline-height': '120px',
        'player-controls': '60px',
        'sidebar-width': '320px',
      },
      zIndex: {
        'timeline': 10,
        'player': 20,
        'modal': 50,
        'tooltip': 60,
        'playhead': 100,
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}