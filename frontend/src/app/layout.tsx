import type { Metadata, Viewport } from 'next'
import { Manrope, Inter_Tight } from 'next/font/google'
import { Providers } from './providers'
import './globals.css'

const manrope = Manrope({
  subsets: ['latin'], 
  variable: '--font-manrope',
  weight: ['400', '500', '600', '700', '800']
})
const interTight = Inter_Tight({
  subsets: ['latin'],
  variable: '--font-display',
  weight: ['500', '600', '700', '800']
})
export const metadata: Metadata = {
  title: 'Baleen — Smarter prediction market research',
  description: 'Research top prediction-market traders and test copy strategies in a clear, risk-isolated paper portfolio.',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#f7fbff',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${interTight.variable} font-sans antialiased min-h-screen flex flex-col`}>
        <Providers>
          <div className="flex-1 flex flex-col">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  )
}
