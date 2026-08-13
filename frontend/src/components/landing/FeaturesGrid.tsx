import { Card } from '../ui/Card';
import { Database, ShieldAlert, Layers, Wallet2 } from 'lucide-react';

export function FeaturesGrid() {
  const features = [
    {
      title: 'Real-time Envio Indexing',
      description: 'Lightning-fast on-chain data ingestion via Envio, capturing Polymarket contract events as they happen.',
      icon: Database,
    },
    {
      title: 'Automated Risk & Slippage',
      description: 'Built-in protection against front-running and excessive slippage. Your trades execute safely or not at all.',
      icon: ShieldAlert,
    },
    {
      title: 'Dynamic Basket Sizing',
      description: 'Proportional position sizing based on your risk profile and the target whale\'s conviction level.',
      icon: Layers,
    },
    {
      title: 'Non-Custodial Sandbox',
      description: 'Test strategies with paper trading before risking real capital. We never hold your funds.',
      icon: Wallet2,
    },
  ];

  return (
    <section id="features" className="py-24 px-6 lg:px-20">
      <div className="text-center mb-16">
        <h2 className="text-3xl md:text-4xl font-bold text-baleen-white mb-4">Industrial Grade Infrastructure</h2>
        <p className="text-baleen-muted max-w-2xl mx-auto">Built on Next.js, FastAPI, and Envio indexers to deliver sub-second execution speeds.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
        {features.map((feature, i) => (
          <Card key={i} variant="interactive" className="group">
            <div className="w-12 h-12 rounded-lg bg-baleen-cyan/10 flex items-center justify-center text-baleen-cyan mb-6 group-hover:bg-baleen-cyan group-hover:text-baleen-obsidian transition-colors">
              <feature.icon size={24} />
            </div>
            <h3 className="text-xl font-semibold text-baleen-white mb-3">{feature.title}</h3>
            <p className="text-baleen-muted leading-relaxed">{feature.description}</p>
          </Card>
        ))}
      </div>
    </section>
  );
}
