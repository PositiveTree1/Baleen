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

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#F0F7FF',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${jakarta.variable} ${outfit.variable} ${cinzel.variable} ${inter.variable} ${spaceGrotesk.variable} font-sans antialiased bg-[#F0F7FF] text-slate-900 min-h-screen flex flex-col transition-colors duration-150`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
