import type { Metadata } from 'next'
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
      <body className={`${jakarta.variable} ${outfit.variable} ${cinzel.variable} ${inter.variable} ${spaceGrotesk.variable} font-sans antialiased bg-[#000000] text-white min-h-screen flex flex-col`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
