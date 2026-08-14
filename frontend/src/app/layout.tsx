import type { Metadata } from 'next'
import { Inter, Space_Grotesk, Syne } from 'next/font/google'
import { Providers } from './providers'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], variable: '--font-space' })
const syne = Syne({ subsets: ['latin'], variable: '--font-syne' })

export const metadata: Metadata = {
  title: 'Baleen — Mirror the Top 1% Polymarket Traders',
  description: 'An automated Polymarket whale-index copy-trading engine. Turn $20 into an automated prediction market portfolio by mirroring hyper-consistent, verified whales.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${spaceGrotesk.variable} ${syne.variable} font-sans antialiased bg-[#F8F9FB] text-slate-900 min-h-screen flex flex-col`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
