import { seededRandom } from "./synth";
import { loadDread, type DreadBank, type Stinger } from "./welcomeDread";

/**
 * A wrong funeral chant over faint bells, whispers and creaks under rain, timber
 * and wind, plus stingers cued by the apparitions; gesture-activated.
 */
export class WelcomeAmbience {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private readonly sources: AudioScheduledSourceNode[] = [];
  private readonly cues = new Set<AudioBufferSourceNode>();
  private stingers: Partial<Record<Stinger, AudioBuffer>> = {};
  private disposed = false;
  private visible = true;

  constructor(
    private enabled: boolean,
    private readonly createContext = () => new AudioContext(),
    private readonly loadBank: (rate: number) => Promise<DreadBank> = loadDread,
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

  /**
   * Plays a stinger now; its hit lands STINGER_HIT seconds later. Silent until
   * unlocked and synthesised.
   */
  cue(kind: Stinger): void {
    const context = this.context;
    const buffer = this.stingers[kind];
    if (!context || !this.master || !buffer || !this.started || !this.enabled || !this.visible)
      return;
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.master);
    source.onended = () => this.cues.delete(source);
    this.cues.add(source);
    source.start();
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
    const rainGain = context.createGain();
    rainGain.gain.value = 0.5;
    rain.connect(rainFilter).connect(rainGain).connect(master);
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

    void this.loadBank(Math.min(24000, context.sampleRate)).then((bank) =>
      this.attach(context, master, bank),
    );
  }

  /** The chant, whispers and bells join once synthesised, under the same gain and lifecycle. */
  private attach(context: AudioContext, master: GainNode, bank: DreadBank): void {
    if (this.disposed || this.context !== context) return;
    const loop = (buffer: AudioBuffer, level: number) => {
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.loop = true;
      const gain = context.createGain();
      gain.gain.value = level;
      source.connect(gain).connect(master);
      this.sources.push(source);
      source.start();
    };
    const theme = context.createBuffer(1, bank.theme.length, bank.rate);
    theme.getChannelData(0).set(bank.theme);
    // The bells sit far behind the chant; chant and whispers loop at different lengths.
    loop(theme, 0.45);
    loop(this.stereoBuffer(context, bank.rate, bank.chant), 1);
    loop(this.stereoBuffer(context, bank.rate, bank.bed), 1);
    for (const kind of ["appear", "near", "vanish"] as const)
      this.stingers[kind] = this.stereoBuffer(context, bank.rate, bank.stingers[kind]);
  }

  private stereoBuffer(
    context: AudioContext,
    rate: number,
    [left, right]: [Float32Array, Float32Array],
  ): AudioBuffer {
    const buffer = context.createBuffer(2, left.length, rate);
    buffer.getChannelData(0).set(left);
    buffer.getChannelData(1).set(right);
    return buffer;
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
    for (const source of [...this.sources, ...this.cues]) source.stop(now + 0.24);
    this.sources.length = 0;
    this.cues.clear();
    this.context = null;
    this.master = null;
    setTimeout(() => {
      void context.close().catch(() => undefined);
    }, 280);
  }
}
