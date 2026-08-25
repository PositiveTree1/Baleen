# Baleen — Official Brand Identity & Design System
**Version 2.0 • Institutional Grade**

---

## 1. Brand Philosophy & Mission

Baleen is an institutional copy-trading engine designed exclusively for prediction markets on Polymarket. We combine algorithmic on-chain discovery, sub-second execution latency, and automated mark-to-market portfolio management to allow investors to mirror verified smart money with absolute transparency.

### Core Brand Pillars:
- **Quiet Confidence**: Understated, premium, and sophisticated. No retail crypto noise or gimmicks.
- **Quantitative Rigor**: Every statistic is verified on-chain, bounded by Wilson confidence intervals and Sharpe ratios.
- **Nordic Precision & Glass Optics**: High-contrast typography, immaculate whitespace, crisp specular light reflections, and real frosted glass optics.

---

## 2. Color Palette & Atmospheric System

```
[ Obsidian ]        [ Glacier Canvas ]     [ Polymarket Emerald ]     [ Gold Sniper ]        [ Liquid Silver ]
  #0A0D12               #F8F9FB                   #10B981                #F59E0B                #BAC0BE
Dark Elements        Page Background          Realized Alpha PnL       Top Tier Whales        Glass Reflections
```

### Primary Spectrum:
- **Obsidian Core (`#0A0D12`)**: Used for primary action buttons, dark CTA cards, and hero elements.
- **Glacier Canvas (`#F8F9FB` / `#FFFFFF`)**: Ultra-clean, distraction-free backdrop.
- **Slate Monolith (`#0F172A` / `#334155` / `#64748B`)**: Body typography, hierarchy scales, and muted subtitles.

### Alpha Telemetry Spectrum:
- **Polymarket Alpha Emerald (`#10B981` / `#ECFDF5`)**: Green gains, positive trajectory curves, and live consensus signals.
- **Gold Sniper Amber (`#F59E0B` / `#FEF3C7`)**: Tier badges for 80%+ win rate prediction whales.
- **Drawdown Rose (`#F43F5E` / `#FFF1F2`)**: Controlled stop-loss metrics and drawdown attribution.

---

## 3. Real Glassmorphism & Light Refraction Tokens

Baleen interfaces employ multi-layered optical physics:

```css
/* True Apple-Level Frosted Glass with Specular Reflection */
.apple-glass {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(28px) saturate(180%);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 
    inset 0 1px 1px 0 rgba(255, 255, 255, 1.0),
    0 2px 8px -2px rgba(15, 23, 42, 0.03),
    0 16px 36px -8px rgba(15, 23, 42, 0.05);
}

/* Subtle Specular Refraction Highlight */
.refraction-border {
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.95);
}
```

---

## 4. Typography Hierarchy

- **Primary Display Font**: Apple System (`-apple-system`, `SF Pro Display`, `Inter`) for razor-sharp legibility and mathematical clarity.
- **Quantitative Monospace**: `SF Mono`, `JetBrains Mono` with `tabular-nums` enabled so numbers never shift or oscillate during live streaming.
- **Tracking & Leading**:
  - Hero Display: `tracking-tight` with `leading-[1.08]`
  - Eyebrows: `text-[11px] font-bold tracking-[0.2em] uppercase font-mono`
  - Body: `text-slate-600 font-normal leading-relaxed`

---

## 5. Asset Registry

Located in `brand-identity/assets/` and `frontend/public/brand/`:
- `LogoTransparent.png`: Clean transparent high-resolution emblem.
- `LogoWhiteBackgroundWithText.png`: Full horizontal logotype.
- `bgImage.jpeg`: Cinematic whale tail rising from misty arctic waters.
- `palette.json`: Machine-readable tokens for IDEs and theme generators.
