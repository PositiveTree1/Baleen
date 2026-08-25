import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        baleen: {
          canvas: '#F8F9FB',
          surface: '#FFFFFF',
          card: '#FFFFFF',
          border: 'rgba(0, 0, 0, 0.08)',
          text: '#0F172A',
          muted: '#64748B',
          subtle: '#94A3B8',
          green: '#059669',
          red: '#E11D48',
          blue: '#2563EB',
        }
      },
      fontFamily: {
        sans: ['var(--font-jakarta)', 'var(--font-inter)', '-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['var(--font-jakarta)', 'var(--font-space)', 'sans-serif'],
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
