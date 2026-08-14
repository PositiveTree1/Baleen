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
    <section id="features" className="py-24 px-6 lg:px-20 border-t border-black/[0.06] bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold text-slate-900 tracking-tight mb-4">Industrial Grade Infrastructure</h2>
          <p className="text-slate-600 text-base max-w-xl mx-auto font-normal">Engineered on Next.js, FastAPI, and Envio HyperSync for sub-second execution accuracy.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((feature, i) => (
            <div 
              key={i} 
              className="p-8 rounded-3xl bg-[#FBFBFD] border border-black/[0.08] hover:border-black/[0.15] hover:bg-white transition-all duration-200 shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_6px_rgba(0,0,0,0.03),0_12px_24px_-4px_rgba(0,0,0,0.04)] group"
            >
              <div className="w-12 h-12 rounded-2xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_1px_3px_rgba(0,0,0,0.05)] flex items-center justify-center text-slate-900 mb-6 group-hover:scale-105 transition-transform">
                <feature.icon size={22} className="text-slate-800" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2 tracking-tight">{feature.title}</h3>
              <p className="text-slate-600 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
