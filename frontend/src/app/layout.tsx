import type { Metadata, Viewport } from 'next'
import { Plus_Jakarta_Sans, Space_Grotesk, Inter, Outfit, Cinzel } from 'next/font/google'
import { Providers } from './providers'
import './globals.css'

const jakarta = Plus_Jakarta_Sans({ 
  subsets: ['latin'], 
  variable: '--font-jakarta',
  weight: ['400', '500', '600', '700', '800']
})
const outfit = Outfit({
  subsets: ['latin'],
  variable: '--font-outfit',
  weight: ['400', '500', '600', '700', '800', '900']
})
const cinzel = Cinzel({
  subsets: ['latin'],
  variable: '--font-cinzel',
  weight: ['700', '800', '900']
})
const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], variable: '--font-space' })
const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Baleen — Polymarket Paper Copy Trading',
  description: 'Research Polymarket traders and explore simulated copying in a paper portfolio. Experimental results; real-money execution is unavailable.',
}

import { LiquidParallaxBackground } from '@/components/landing/LiquidParallaxBackground'

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#020b18',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${jakarta.variable} ${outfit.variable} ${cinzel.variable} ${inter.variable} ${spaceGrotesk.variable} font-sans antialiased bg-[#020b18] text-white min-h-screen flex flex-col selection:bg-[#00D09C] selection:text-black`}>
        <Providers>
          <LiquidParallaxBackground />
          <div className="relative z-10 flex-1 flex flex-col">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  )
}
