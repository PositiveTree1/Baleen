// Web Audio API & BentoMotion Liquid Glass Audio Engine
class SoundEngine {
  private ctx: AudioContext | null = null;
  private enabled: boolean = false;
  private audioCache: Map<string, HTMLAudioElement> = new Map();

  constructor() {
    // Lazy initialized on first user interaction
  }

  private getContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
    return this.ctx;
  }

  public toggleSound(): boolean {
    this.enabled = !this.enabled;
    if (this.enabled) {
      this.playTap();
    }
    return this.enabled;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public playGlassAudio(type: 'tap' | 'slider' | 'whoosh' | 'transition') {
    if (!this.enabled) return;
    if (typeof window === 'undefined') return;

    const fileMap: Record<string, string> = {
      tap: '/sounds/glass-tap.wav',
      slider: '/sounds/glass-slider.wav',
      whoosh: '/sounds/glass-whoosh.wav',
      transition: '/sounds/glass-transition.wav',
    };

    const src = fileMap[type];
    if (!src) return;

    try {
      let audio = this.audioCache.get(src);
      if (!audio) {
        audio = new Audio(src);
        audio.preload = 'auto';
        this.audioCache.set(src, audio);
      }
      audio.currentTime = 0;
      audio.volume = type === 'tap' ? 0.35 : 0.25;
      audio.play().catch(() => {
        // Fallback to Web Audio oscillator if audio element play is blocked
        this.playChime(type === 'slider' ? 'click' : 'fill');
      });
    } catch {
      this.playChime('click');
    }
  }

  public playTap() {
    this.playGlassAudio('tap');
  }

  public playSlider() {
    this.playGlassAudio('slider');
  }

  public playWhoosh() {
    this.playGlassAudio('whoosh');
  }

  public playTransition() {
    this.playGlassAudio('transition');
  }

  public playChime(type: 'fill' | 'consensus' | 'success' | 'click' = 'fill') {
    if (!this.enabled && type !== 'success') return;
    try {
      const ctx = this.getContext();
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      const now = ctx.currentTime;

      if (type === 'fill') {
        // High-precision clean metallic tick (Hyperliquid style)
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(1760, now + 0.08);
        gain.gain.setValueAtTime(0.06, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        osc.start(now);
        osc.stop(now + 0.08);
      } else if (type === 'consensus') {
        // Multi-frequency harmonic resonance for major whale consensus
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.setValueAtTime(659.25, now + 0.06); // E5
        osc.frequency.setValueAtTime(783.99, now + 0.12); // G5
        osc.frequency.setValueAtTime(1046.50, now + 0.18); // C6
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (type === 'success') {
        // Soft affirmative ping
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.12); // A5
        gain.gain.setValueAtTime(0.05, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
        osc.start(now);
        osc.stop(now + 0.15);
      } else if (type === 'click') {
        // Subtle haptic-feel micro-tick
        osc.type = 'sine';
        osc.frequency.setValueAtTime(1200, now);
        gain.gain.setValueAtTime(0.02, now);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.03);
        osc.start(now);
        osc.stop(now + 0.03);
      }
    } catch (e) {
      // AudioContext blocked by browser autoplay policy until user gesture
    }
  }
}

export const soundFx = new SoundEngine();
