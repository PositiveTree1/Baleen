'use client';
import { motion, useMotionValue, useTransform } from 'framer-motion';
import { Button } from '../ui/Button';
import Link from 'next/link';

export function Hero() {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-100, 100], [10, -10]);
  const rotateY = useTransform(x, [-100, 100], [-10, 10]);

  function handleMouse(event: React.MouseEvent<HTMLDivElement, MouseEvent>) {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set(event.clientX - rect.left - rect.width / 2);
    y.set(event.clientY - rect.top - rect.height / 2);
  }

  function handleMouseLeave() {
    x.set(0);
    y.set(0);
  }

  return (
    <section className="min-h-[80vh] flex flex-col lg:flex-row items-center justify-between px-6 lg:px-20 py-20 gap-12 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-96 h-96 bg-baleen-cyan/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full lg:w-1/2 flex flex-col items-start gap-6 z-10">
        <div className="px-3 py-1 text-xs font-semibold tracking-wider text-baleen-cyan border border-baleen-cyan/20 rounded-full bg-baleen-cyan/5">
          AI-POWERED POLYMARKET COPY ENGINE
        </div>
        <h1 className="text-5xl lg:text-7xl font-bold tracking-tight text-baleen-white">
          Mirror the Top <span className="text-transparent bg-clip-text bg-gradient-cyan">1%</span>
        </h1>
        <p className="text-lg text-baleen-muted max-w-xl leading-relaxed">
          Baleen automates Polymarket whale-index copy-trading. Discover elite wallets, match their trades instantly, and build your automated portfolio.
        </p>
        <div className="flex items-center gap-4 mt-4">
          <Link href="/auth/signup">
            <Button variant="primary" className="px-8 py-3 text-lg">Start Mirroring</Button>
          </Link>
          <Link href="#features">
            <Button variant="secondary" className="px-8 py-3 text-lg">Explore Engine</Button>
          </Link>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex justify-center perspective-[1000px] z-10" onMouseMove={handleMouse} onMouseLeave={handleMouseLeave}>
        <motion.div
          style={{ rotateX, rotateY }}
          className="glass-card w-full max-w-md p-6 rounded-2xl border border-white/10 shadow-2xl relative overflow-hidden"
        >
          {/* Mock data strictly prohibited, but structural placeholder for live execution data */}
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-sm font-medium text-baleen-muted uppercase tracking-wider">Live Execution Protocol</h3>
            <div className="w-2 h-2 rounded-full bg-baleen-green animate-pulse"></div>
          </div>
          
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-black/40 border border-white/5">
              <div className="text-xs text-baleen-muted mb-1">Latest Target Acquired</div>
              <div className="font-mono text-sm text-baleen-white flex justify-between">
                <span>Waiting for signal...</span>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-black/40 border border-white/5">
                <div className="text-xs text-baleen-muted mb-1">Basket Size</div>
                <div className="text-xl font-semibold text-baleen-white">--</div>
              </div>
              <div className="p-4 rounded-lg bg-black/40 border border-white/5">
                <div className="text-xs text-baleen-muted mb-1">Engine Latency</div>
                <div className="text-xl font-semibold text-baleen-white">--</div>
              </div>
            </div>

            <div className="h-20 rounded-lg bg-black/40 border border-white/5 flex items-center justify-center text-xs text-baleen-muted italic">
              Data stream initializing...
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
