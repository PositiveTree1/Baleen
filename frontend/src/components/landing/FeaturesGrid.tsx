import { Card } from '../ui/Card';
import { Database, ShieldAlert, Layers, Wallet2 } from 'lucide-react';

export function FeaturesGrid() {
  const features = [
    {
      title: 'Real-time Envio Indexing',
      description: 'Zero-delay contract event streaming straight from Polygon CTF contracts with sub-second detection.',
      icon: Database,
    },
    {
      title: 'Automated Risk & Slippage Engine',
      description: 'Dynamic order cancellation if execution price deviates beyond strict regime tolerances. No front-running.',
      icon: ShieldAlert,
    },
    {
      title: 'Dynamic Per-Trade Sizing',
      description: 'Equal weighting scaled by active non-dormant whales and whale conviction without manual rebalancing.',
      icon: Layers,
    },
    {
      title: 'Non-Custodial Paper Sandbox',
      description: 'Test strategies with $10,000 in virtual funds mirroring real live fills before connecting any wallet.',
      icon: Wallet2,
    },
  ];

  return (
    <section id="features" className="py-24 px-6 lg:px-20 border-t border-white/[0.06] bg-zinc-950/40">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight mb-4">Industrial Grade Infrastructure</h2>
          <p className="text-zinc-400 text-base max-w-xl mx-auto font-normal">Built on Next.js, FastAPI, and Envio HyperSync for uncompromising execution accuracy.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((feature, i) => (
            <div 
              key={i} 
              className="p-8 rounded-3xl bg-zinc-900/40 border border-white/[0.08] hover:border-white/[0.18] hover:bg-zinc-900/70 transition-all duration-300 backdrop-blur-xl group"
            >
              <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/[0.08] flex items-center justify-center text-white mb-6 group-hover:scale-105 transition-transform">
                <feature.icon size={22} className="text-zinc-300" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2 tracking-tight">{feature.title}</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
