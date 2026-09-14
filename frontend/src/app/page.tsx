'use client';

import Link from 'next/link';
import { useRef } from 'react';
import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight, BarChart3, Layers3, Radar, ShieldCheck, Sparkles } from 'lucide-react';
import { BrandLogo } from '@/components/ui/BrandLogo';

export default function LandingPage() {
  const heroRef = useRef<HTMLElement>(null);
  const prefersReducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  });
  const imageY = useTransform(scrollYProgress, [0, 1], ['0%', prefersReducedMotion ? '0%' : '14%']);
  const imageScale = useTransform(scrollYProgress, [0, 1], [1.035, prefersReducedMotion ? 1.035 : 1.11]);
  const contentY = useTransform(scrollYProgress, [0, 1], [0, prefersReducedMotion ? 0 : -54]);

  return (
    <main className="baleen-landing">
      <header className="landing-header">
        <nav className="landing-nav" aria-label="Primary navigation">
          <BrandLogo size="md" />
          <div className="landing-nav-links">
            <a href="#platform">Platform</a>
            <a href="#how-it-works">How it works</a>
            <a href="#security">Risk model</a>
          </div>
          <div className="landing-nav-actions">
            <Link href="/auth/login" className="nav-sign-in">Sign in</Link>
            <Link href="/dashboard" className="button button-primary button-small">Open app</Link>
          </div>
        </nav>
      </header>

      <section ref={heroRef} className="landing-hero" aria-labelledby="hero-title">
        <motion.div className="hero-image" style={{ y: imageY, scale: imageScale }} aria-hidden="true" />
        <div className="hero-wash" aria-hidden="true" />
        <motion.div className="hero-content" style={{ y: contentY }}>
          <div className="eyebrow"><Sparkles size={14} /> Prediction intelligence, simplified</div>
          <h1 id="hero-title">Follow conviction.<br />Protect your capital.</h1>
          <p>Discover consistent prediction-market traders and test their strategies in a paper portfolio built around isolated risk.</p>
          <div className="hero-actions">
            <Link href="/auth/login" className="button button-primary">Explore the live demo <ArrowRight size={18} /></Link>
            <a href="#platform" className="button button-secondary">See how it works</a>
          </div>
          <div className="hero-proof" aria-label="Platform highlights">
            <span><ShieldCheck size={17} /> Paper funds only</span>
            <span><Radar size={17} /> Live market signals</span>
          </div>
        </motion.div>
      </section>

      <section id="platform" className="section shell">
        <div className="section-heading">
          <span className="section-label">One clear workspace</span>
          <h2>Signal without the noise.</h2>
          <p>Baleen turns a dense market stream into a focused view of the traders, positions and outcomes that matter.</p>
        </div>
        <div className="feature-grid">
          <article className="feature-card feature-card-wide">
            <div>
              <div className="feature-icon"><Radar size={22} /></div>
              <h3>Find durable signals</h3>
              <p>Rank traders by repeatable performance, not one lucky outcome. See conviction, consistency and risk in context.</p>
            </div>
            <div className="signal-preview" aria-hidden="true">
              <div className="signal-topline"><span>Signal quality</span><strong>High</strong></div>
              <div className="signal-chart"><i /><i /><i /><i /><i /><i /><i /></div>
              <div className="signal-meta"><span>Consistency</span><b>91%</b><span>Drawdown</span><b>3.8%</b></div>
            </div>
          </article>
          <article className="feature-card">
            <div className="feature-icon"><Layers3 size={22} /></div>
            <h3>Isolate every strategy</h3>
            <p>Each trader gets a separate capital sleeve, so a weak signal cannot spill into the rest of your portfolio.</p>
          </article>
          <article className="feature-card">
            <div className="feature-icon"><BarChart3 size={22} /></div>
            <h3>Understand every result</h3>
            <p>Clear performance, exposure and trade history make every simulated decision easy to inspect.</p>
          </article>
        </div>
      </section>

      <section id="how-it-works" className="section process-section">
        <div className="shell process-layout">
          <div className="section-heading section-heading-left">
            <span className="section-label">Built for deliberate decisions</span>
            <h2>From market move to measured strategy.</h2>
          </div>
          <ol className="process-list">
            <li><span>01</span><div><h3>Observe</h3><p>Live market activity is distilled into a focused trader signal.</p></div></li>
            <li><span>02</span><div><h3>Validate</h3><p>Performance and risk filters separate repeatable behaviour from noise.</p></div></li>
            <li><span>03</span><div><h3>Simulate</h3><p>A paper portfolio mirrors eligible trades within your chosen limits.</p></div></li>
          </ol>
        </div>
      </section>

      <section id="security" className="section shell">
        <div className="closing-card">
          <div>
            <span className="section-label">Explore safely</span>
            <h2>Build conviction before committing capital.</h2>
            <p>Baleen is a non-custodial paper-trading sandbox. Real-money execution is unavailable.</p>
          </div>
          <Link href="/auth/signup" className="button button-light">Create a free sandbox <ArrowRight size={18} /></Link>
        </div>
      </section>

      <footer className="landing-footer shell">
        <BrandLogo size="sm" />
        <p>© {new Date().getFullYear()} Baleen. Prediction-market research, made clearer.</p>
        <div><Link href="/auth/login">Sign in</Link><Link href="/dashboard">Dashboard</Link></div>
      </footer>
    </main>
  );
}
