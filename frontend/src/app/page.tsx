'use client';

import Link from 'next/link';
import { useRef, useState, MouseEvent } from 'react';
import { motion, useMotionValue, useSpring, useTransform, useScroll, useReducedMotion } from 'framer-motion';
import {
  ArrowRight,
  BarChart3,
  Layers3,
  Radar,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { BrandLogo } from '@/components/ui/BrandLogo';

export default function LandingPage() {
  const heroRef = useRef<HTMLElement>(null);
  const prefersReducedMotion = useReducedMotion();

  // Pointer tracking for organic 3D tilt
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springConfig = { damping: 26, stiffness: 120, mass: 0.6 };
  const smoothMouseX = useSpring(mouseX, springConfig);
  const smoothMouseY = useSpring(mouseY, springConfig);

  // Background 3D & offset transforms
  const bgTiltX = useTransform(smoothMouseY, [-0.5, 0.5], [2.2, -2.2]);
  const bgTiltY = useTransform(smoothMouseX, [-0.5, 0.5], [-3, 3]);
  const bgShiftX = useTransform(smoothMouseX, [-0.5, 0.5], [-16, 16]);
  const bgShiftY = useTransform(smoothMouseY, [-0.5, 0.5], [-10, 10]);

  // Floating card 3D tilt transforms
  const cardTiltX = useTransform(smoothMouseY, [-0.5, 0.5], [7, -7]);
  const cardTiltY = useTransform(smoothMouseX, [-0.5, 0.5], [-9, 9]);
  const cardShiftX = useTransform(smoothMouseX, [-0.5, 0.5], [14, -14]);

  // Scroll Parallax Engine
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  });

  const imageScrollY = useTransform(scrollYProgress, [0, 1], ['0%', prefersReducedMotion ? '0%' : '18%']);
  const imageScale = useTransform(scrollYProgress, [0, 1], [1.02, prefersReducedMotion ? 1.02 : 1.13]);
  const contentScrollY = useTransform(scrollYProgress, [0, 1], [0, prefersReducedMotion ? 0 : -64]);
  const floatingCardScrollY = useTransform(scrollYProgress, [0, 1], [0, prefersReducedMotion ? 0 : -100]);
  const atmosphereScrollY = useTransform(scrollYProgress, [0, 1], ['0%', prefersReducedMotion ? '0%' : '8%']);

  const handleMouseMove = (e: MouseEvent<HTMLElement>) => {
    if (prefersReducedMotion || !heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    mouseX.set(x);
    mouseY.set(y);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  // State for interactive card specular highlight
  const [cardMouse, setCardMouse] = useState<{ [key: string]: { x: number; y: number } }>({});

  const handleCardMouseMove = (id: string, e: MouseEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setCardMouse((prev) => ({ ...prev, [id]: { x, y } }));
  };

  return (
    <main className="baleen-landing">
      {/* Precision Floating Glass Navigation */}
      <header className="landing-header">
        <nav className="landing-nav" aria-label="Primary navigation">
          <BrandLogo size="md" />
          <div className="landing-nav-links">
            <a href="#platform">Platform</a>
            <a href="#how-it-works">How it works</a>
            <a href="#security">Risk model</a>
          </div>
          <div className="landing-nav-actions">
            <Link href="/auth/login" className="nav-sign-in">
              Sign in
            </Link>
            <Link href="/dashboard" className="button button-primary button-small">
              Open app
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Stage with Multi-Plane Parallax */}
      <section
        ref={heroRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="landing-hero"
        aria-labelledby="hero-title"
      >
        {/* Layer 0: 3D Damped Whale Background Image */}
        <motion.div
          className="hero-parallax-stage"
          style={{
            rotateX: prefersReducedMotion ? 0 : bgTiltX,
            rotateY: prefersReducedMotion ? 0 : bgTiltY,
            x: prefersReducedMotion ? 0 : bgShiftX,
            y: prefersReducedMotion ? 0 : bgShiftY,
          }}
          aria-hidden="true"
        >
          <motion.div
            className="hero-image"
            style={{
              y: imageScrollY,
              scale: imageScale,
            }}
          />
        </motion.div>

        {/* Layer 1: Water Caustic Shimmer & Atmospheric Mist */}
        <motion.div
          className="hero-water-caustic"
          style={{ y: atmosphereScrollY }}
          aria-hidden="true"
        />
        <div className="hero-mist-light" aria-hidden="true" />
        <div className="hero-wash" aria-hidden="true" />

        {/* Layer 2 & 3: Hero Content & Floating Telemetry Lens */}
        <motion.div
          className="hero-content"
          style={{ y: contentScrollY }}
        >
          <div className="hero-grid">
            {/* Left Column: Typography & CTAs */}
            <div className="hero-left-col">
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="eyebrow"
              >
                <Sparkles size={13} className="text-blue-600" />
                <span>Prediction Intelligence Sandbox</span>
              </motion.div>

              <motion.h1
                id="hero-title"
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.08 }}
              >
                Follow conviction.
                <br />
                Protect your capital.
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.16 }}
              >
                Discover consistent prediction-market traders and test their strategies in a paper
                portfolio engineered around strictly segregated risk sleeves.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.24 }}
                className="hero-actions"
              >
                <Link href="/auth/login" className="button button-primary">
                  <span>Explore the live demo</span>
                  <ArrowRight size={17} />
                </Link>
                <a href="#platform" className="button button-secondary">
                  <span>See how it works</span>
                </a>
              </motion.div>

              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.35 }}
                className="hero-proof"
                aria-label="Platform highlights"
              >
                <span>
                  <ShieldCheck size={16} className="text-emerald-600" /> 100% Paper sandbox
                </span>
                <span>
                  <Radar size={16} className="text-sky-600" /> Live market signals
                </span>
              </motion.div>
            </div>

            {/* Right Column: Interactive Floating Live Telemetry Lens */}
            <motion.div
              style={{
                y: floatingCardScrollY,
                rotateX: prefersReducedMotion ? 0 : cardTiltX,
                rotateY: prefersReducedMotion ? 0 : cardTiltY,
                x: prefersReducedMotion ? 0 : cardShiftX,
              }}
              className="hidden lg:block"
            >
              <div className="hero-floating-card">
                <div className="floating-telemetry-header">
                  <div className="pulse-beacon">
                    <span className="pulse-dot" />
                    <span>Real-time Telemetry</span>
                  </div>
                  <span className="telemetry-tag font-mono">Whale 0x7a3...9b2</span>
                </div>

                <div className="telemetry-row">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                      Simulated Strategy PnL
                    </div>
                    <div className="telemetry-metric-large mt-1">+$184,290</div>
                  </div>
                  <div className="telemetry-pill-positive font-mono flex items-center gap-1">
                    <TrendingUp size={13} />
                    <span>+42.8%</span>
                  </div>
                </div>

                <div className="telemetry-bars" aria-hidden="true">
                  <div className="telemetry-bar" style={{ height: '35%' }} />
                  <div className="telemetry-bar" style={{ height: '52%' }} />
                  <div className="telemetry-bar" style={{ height: '44%' }} />
                  <div className="telemetry-bar" style={{ height: '68%' }} />
                  <div className="telemetry-bar" style={{ height: '78%' }} />
                  <div className="telemetry-bar" style={{ height: '62%' }} />
                  <div className="telemetry-bar highlight" style={{ height: '94%' }} />
                </div>

                <div className="telemetry-footer-stats">
                  <span>
                    Consistency: <b>91.4%</b>
                  </span>
                  <span>
                    Max Drawdown: <b>3.2%</b>
                  </span>
                  <span>
                    Sleeve: <b>Isolated</b>
                  </span>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </section>

      {/* Platform Bento Section */}
      <section id="platform" className="section shell">
        <div className="section-heading">
          <span className="section-label">One clear workspace</span>
          <h2>Signal without the noise.</h2>
          <p>
            Baleen turns a dense market stream into a focused view of the traders, positions and
            outcomes that matter.
          </p>
        </div>

        <div className="feature-grid">
          {/* Main Wide Feature Card */}
          <article
            className="feature-card feature-card-wide"
            onMouseMove={(e) => handleCardMouseMove('wide', e)}
            style={{
              background: cardMouse['wide']
                ? `radial-gradient(500px circle at ${cardMouse['wide'].x}% ${cardMouse['wide'].y}%, rgba(255,255,255,0.98), rgba(255,255,255,0.82) 50%)`
                : undefined,
            }}
          >
            <div>
              <div className="feature-icon">
                <Radar size={24} />
              </div>
              <h3>Find durable signals</h3>
              <p>
                Rank traders by repeatable performance, not one lucky outcome. See conviction,
                consistency, and risk in context with sub-second live indexing.
              </p>
            </div>
            <div className="signal-preview" aria-hidden="true">
              <div className="signal-topline">
                <span className="font-semibold">Conviction Stream</span>
                <strong>High Alpha</strong>
              </div>
              <div className="signal-chart">
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
              </div>
              <div className="signal-meta">
                <span>Consistency</span>
                <b>91.4%</b>
                <span>Max Drawdown</span>
                <b>3.8%</b>
              </div>
            </div>
          </article>

          {/* Feature Card 2 */}
          <article
            className="feature-card"
            onMouseMove={(e) => handleCardMouseMove('sleeve', e)}
            style={{
              background: cardMouse['sleeve']
                ? `radial-gradient(400px circle at ${cardMouse['sleeve'].x}% ${cardMouse['sleeve'].y}%, rgba(255,255,255,0.98), rgba(255,255,255,0.82) 50%)`
                : undefined,
            }}
          >
            <div className="feature-icon">
              <Layers3 size={24} />
            </div>
            <h3>Isolate every strategy</h3>
            <p>
              Each trader gets a dedicated capital sleeve, ensuring an unexpected market shift in
              one market cannot spill into the rest of your sandbox bankroll.
            </p>
          </article>

          {/* Feature Card 3 */}
          <article
            className="feature-card"
            onMouseMove={(e) => handleCardMouseMove('analytics', e)}
            style={{
              background: cardMouse['analytics']
                ? `radial-gradient(400px circle at ${cardMouse['analytics'].x}% ${cardMouse['analytics'].y}%, rgba(255,255,255,0.98), rgba(255,255,255,0.82) 50%)`
                : undefined,
            }}
          >
            <div className="feature-icon">
              <BarChart3 size={24} />
            </div>
            <h3>Understand every result</h3>
            <p>
              Clear performance attribution, exposure breakdown, and trade log telemetry make
              every simulated decision completely transparent to inspect.
            </p>
          </article>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="section process-section">
        <div className="shell process-layout">
          <div className="section-heading section-heading-left">
            <span className="section-label">Built for deliberate decisions</span>
            <h2>From market move to measured strategy.</h2>
          </div>
          <ol className="process-list">
            <li>
              <span>01</span>
              <div>
                <h3>Observe</h3>
                <p>
                  Polygon CTF contract events and Polymarket order flow are ingested with sub-120ms
                  latency to extract raw trader signals.
                </p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <h3>Validate</h3>
                <p>
                  Statistical consistency algorithms and drawdown filters automatically separate
                  repeatable trade conviction from short-term luck.
                </p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <h3>Simulate</h3>
                <p>
                  Your sandbox paper portfolio mirrors qualifying trades proportionally within
                  custom risk parameters and automated slippage limits.
                </p>
              </div>
            </li>
          </ol>
        </div>
      </section>

      {/* Security & Sandbox CTA Card */}
      <section id="security" className="section shell">
        <div className="closing-card">
          <div>
            <span className="section-label">Explore safely</span>
            <h2>Build conviction before committing capital.</h2>
            <p>
              Baleen is a non-custodial paper-trading and strategy sandbox. Real-money execution is
              disabled, allowing safe, repeatable research.
            </p>
          </div>
          <Link href="/auth/signup" className="button button-light">
            <span>Create a free sandbox</span>
            <ArrowRight size={17} />
          </Link>
        </div>
      </section>

      {/* Institutional Footer */}
      <footer className="landing-footer shell">
        <BrandLogo size="sm" />
        <p>© {new Date().getFullYear()} Baleen. Prediction-market research, made clearer.</p>
        <div>
          <Link href="/auth/login">Sign in</Link>
          <Link href="/dashboard">Dashboard</Link>
        </div>
      </footer>
    </main>
  );
}
