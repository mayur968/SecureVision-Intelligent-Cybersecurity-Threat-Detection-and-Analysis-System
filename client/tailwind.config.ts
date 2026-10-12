import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Base surfaces — charcoal/navy spectrum
        surface: {
          base:    '#0b0f1a',   // page background
          raised:  '#111827',   // card background
          overlay: '#1a2236',   // elevated card / modal
          border:  '#1f2d45',   // subtle border
          muted:   '#243044',   // secondary border / divider
        },
        // Primary accent — cyan-blue
        accent: {
          DEFAULT: '#2563eb',   // CTA buttons
          hover:   '#3b82f6',
          muted:   '#1d4ed8',
          glow:    '#60a5fa',
          subtle:  '#1e3a5f',   // accent tint backgrounds
        },
        // Semantic severity
        sev: {
          critical: '#ef4444',   // critical / PHISHING
          high:     '#f97316',   // high / MALICIOUS
          medium:   '#f59e0b',   // medium / SUSPICIOUS
          low:      '#22c55e',   // low / SAFE
          info:     '#38bdf8',   // informational
          none:     '#64748b',   // unknown / neutral
          // bg tints (12% opacity equivalents)
          'critical-bg': '#450a0a',
          'high-bg':     '#431407',
          'medium-bg':   '#451a03',
          'low-bg':      '#052e16',
          'info-bg':     '#082f49',
        },
        // Text hierarchy
        content: {
          primary:   '#f1f5f9',
          secondary: '#94a3b8',
          muted:     '#475569',
          disabled:  '#334155',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        card:    '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'card-md': '0 4px 12px rgba(0,0,0,0.5)',
        glow:    '0 0 20px rgba(37,99,235,0.25)',
        'glow-sm':'0 0 8px rgba(37,99,235,0.2)',
      },
      borderRadius: {
        DEFAULT: '0.5rem',
        card:    '0.75rem',
        pill:    '9999px',
      },
      animation: {
        'fade-in':   'fadeIn 0.2s ease-out',
        'slide-up':  'slideUp 0.25s ease-out',
        'pulse-dot': 'pulseDot 1.8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:   { from: { opacity: '0' },                   to: { opacity: '1' } },
        slideUp:  { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        pulseDot: { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.4' } },
      },
    },
  },
  plugins: [],
};

export default config;
