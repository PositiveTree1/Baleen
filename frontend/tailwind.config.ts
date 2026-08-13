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
          obsidian: '#0B0E14',
          charcoal: '#161B22',
          slate: '#1F2633',
          cyan: '#00F2FE',
          blue: '#4FACFE',
          green: '#10B981',
          red: '#EF4444',
          white: '#F9FAFB',
          muted: '#9CA3AF',
        }
      },
      fontFamily: {
        sans: ['var(--font-inter)'],
      },
      backgroundImage: {
        'gradient-cyan': 'linear-gradient(to right, #00F2FE, #4FACFE)',
      },
    },
  },
  plugins: [],
}
export default config
