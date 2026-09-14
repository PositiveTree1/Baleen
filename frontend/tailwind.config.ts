import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        baleen: {
          canvas: '#F0F7FF',
          surface: '#FFFFFF',
          card: '#FFFFFF',
          border: 'rgba(2, 132, 199, 0.12)',
          text: '#0F172A',
          muted: '#475569',
          subtle: '#64748B',
          green: '#059669',
          red: '#E11D48',
          blue: '#0284C7',
        },
        glacier: {
          white: '#FFFFFF',
          ice: '#F0F7FF',
          frost: '#E0F2FE',
          mist: '#BAE6FD',
          cyan: '#0EA5E9',
          deep: '#0284C7',
          vivid: '#38BDF8',
          navy: '#0F172A',
          slate: '#1E293B',
          muted: '#475569',
          subtle: '#64748B',
          win: '#059669',
          loss: '#E11D48',
        }
      },
      fontFamily: {
        sans: ['var(--font-manrope)', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        display: ['var(--font-display)', 'var(--font-manrope)', 'sans-serif'],
        mono: ['var(--font-manrope)', 'sans-serif'],
      },
      boxShadow: {
        'skeuo': 'inset 0 1px 0 rgba(255, 255, 255, 1), 0 1px 3px rgba(0, 0, 0, 0.05), 0 8px 24px -4px rgba(0, 0, 0, 0.04)',
        'skeuo-card': 'inset 0 1px 0 0 rgba(255, 255, 255, 1), 0 2px 4px -1px rgba(0, 0, 0, 0.04), 0 12px 28px -4px rgba(0, 0, 0, 0.05)',
        'skeuo-btn': 'inset 0 1px 0 rgba(255, 255, 255, 0.9), 0 1px 2px rgba(0, 0, 0, 0.06), 0 2px 6px rgba(0, 0, 0, 0.04)',
        'skeuo-dark': 'inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 2px 6px rgba(0, 0, 0, 0.2), 0 8px 16px -2px rgba(0, 0, 0, 0.15)',
        'pill': 'inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 1px 2px rgba(0, 0, 0, 0.04)',
      }
    },
  },
  plugins: [],
}
export default config
