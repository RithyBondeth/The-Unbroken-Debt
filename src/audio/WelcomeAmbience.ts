import { seededRandom } from "./synth";

/** Quiet rain, a low beating drone and a slowly breathing wind; no downloaded audio. */
export class WelcomeAmbience {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private readonly sources: AudioScheduledSourceNode[] = [];
  private disposed = false;
  private visible = true;

  constructor(
    private enabled: boolean,
    private readonly createContext = () => new AudioContext(),
  ) {}

  get started(): boolean {
    return this.context?.state === "running" && !this.disposed;
  }

  /** Call directly from a player gesture so browser autoplay rules are respected. */
  async unlock(): Promise<boolean> {
    if (this.disposed || !this.enabled || !this.visible) return false;
    try {
      if (!this.context) this.build();
      const context = this.context!;
      await context.resume();
      if (this.disposed || this.context !== context) return false;
      this.updateGain();
      return context.state === "running";
    } catch {
      // The game remains playable when a browser or output device denies audio.
      return false;
    }
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.updateGain();
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.updateGain();
  }

  private updateGain(): void {
    if (!this.context || !this.master || this.disposed) return;
    const now = this.context.currentTime;
    this.master.gain.cancelScheduledValues(now);
    // Hide/mute immediately; fade gently back in to avoid a sudden drone onset.
    if (!this.enabled || !this.visible) this.master.gain.setValueAtTime(0, now);
    else this.master.gain.setTargetAtTime(0.32, now, 0.8);
  }

  private build(): void {
    const context = this.createContext();
    this.context = context;
    const master = context.createGain();
    this.master = master;
    master.gain.value = 0;
    master.connect(context.destination);

    const buffer = context.createBuffer(2, context.sampleRate * 8, context.sampleRate);
    const rand = seededRandom(1932);
    for (let channel = 0; channel < 2; channel++) {
      const data = buffer.getChannelData(channel);
      for (let i = 0; i < data.length; i++) data[i] = (rand() * 2 - 1) * 0.28;
    }
    const rain = context.createBufferSource();
    rain.buffer = buffer;
    rain.loop = true;
    const rainFilter = context.createBiquadFilter();
    rainFilter.type = "lowpass";
    rainFilter.frequency.value = 1800;
    rainFilter.Q.value = 0.45;
    rain.connect(rainFilter).connect(master);
    this.sources.push(rain);
    rain.start();

    // Close pitches beat slowly against one another, like distant resonant timber.
    for (const [frequency, level] of [
      [55, 0.035],
      [55.23, 0.025],
      [82.4, 0.009],
    ]) {
      const tone = context.createOscillator();
      tone.type = "sine";
      tone.frequency.value = frequency;
      const gain = context.createGain();
      gain.gain.value = level;
      tone.connect(gain).connect(master);
      this.sources.push(tone);
      tone.start();
    }

    const wind = context.createBiquadFilter();
    wind.type = "bandpass";
    wind.frequency.value = 370;
    wind.Q.value = 3.5;
    const windGain = context.createGain();
    windGain.gain.value = 0.12;
    rain.connect(wind).connect(windGain).connect(master);
    const breath = context.createOscillator();
    breath.frequency.value = 0.067;
    const depth = context.createGain();
    depth.gain.value = 0.09;
    breath.connect(depth).connect(windGain.gain);
    this.sources.push(breath);
    breath.start();
  }

  /** Fade away before gameplay and release the menu's entire audio graph. */
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    const context = this.context;
    if (!context) return;
    const now = context.currentTime;
    this.master?.gain.cancelScheduledValues(now);
    this.master?.gain.setValueAtTime(this.master.gain.value, now);
    this.master?.gain.linearRampToValueAtTime(0, now + 0.22);
    for (const source of this.sources) source.stop(now + 0.24);
    this.sources.length = 0;
    this.context = null;
    this.master = null;
    setTimeout(() => {
      void context.close().catch(() => undefined);
    }, 280);
  }
}
