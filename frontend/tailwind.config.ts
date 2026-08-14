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
          obsidian: '#090A0F',
          charcoal: '#12141A',
          slate: '#1A1D24',
          border: 'rgba(255, 255, 255, 0.08)',
          cyan: '#FFFFFF',
          blue: '#3B82F6',
          green: '#10B981',
          red: '#F43F5E',
          white: '#FFFFFF',
          muted: '#8E95A5',
          subtle: '#525866',
        }
      },
      fontFamily: {
        sans: ['var(--font-inter)', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'apple': '0 4px 24px -1px rgba(0, 0, 0, 0.3)',
        'apple-sm': '0 2px 8px -1px rgba(0, 0, 0, 0.2)',
        'apple-glow': '0 0 20px -2px rgba(255, 255, 255, 0.1)',
      }
    },
  },
  plugins: [],
}
export default config
