import { creak, hall, knock, whisper } from "./dread";
import { entryBed, entryBreath, entryThud } from "./entryDread";
import { seededRandom } from "./synth";

/** Seconds a whisper takes to cross from the left ear to the right. */
export const WHISPER_SECONDS = 2.2;

/**
 * The listening screen's soundscape: a held-breath bed, whispers crossing the head
 * left to right, knocks and creaks behind, then a breath and a thud when the player
 * presses Enter. It only starts after an earlier gesture (the title menu), since
 * browsers refuse sound before one; otherwise the screen stays silent.
 */
export class EntryAmbience {
  private context: AudioContext | null = null;
  private bed: GainNode | null = null;
  private master: GainNode | null = null;
  private readonly sources = new Set<AudioScheduledSourceNode>();
  private timer: ReturnType<typeof setTimeout> | undefined;
  private disposed = false;
  private readonly rand = seededRandom(1935);

  constructor(
    private readonly onWhisper: (seconds: number) => void = () => undefined,
    private readonly createContext = () => new AudioContext(),
    private readonly hasGesture = () =>
      (navigator as Navigator & { userActivation?: { hasBeenActive: boolean } }).userActivation
        ?.hasBeenActive ?? false,
  ) {}

  get started(): boolean {
    return this.context !== null && !this.disposed;
  }

  start(enabled: boolean): void {
    if (this.disposed || this.context || !enabled || !this.hasGesture()) return;
    try {
      const context = this.createContext();
      this.context = context;
      this.master = context.createGain();
      this.master.gain.value = 0;
      this.master.connect(context.destination);
      this.master.gain.setTargetAtTime(0.5, context.currentTime, 0.9);
      this.bed = context.createGain();
      this.bed.connect(this.master);
      const rate = this.rate;
      const loop = this.play(this.stereo(entryBed(rate)), this.bed);
      loop.loop = true;
      void context.resume().catch(() => undefined);
      this.schedule(2.2);
    } catch {
      // Without audio the screen still works; it is only atmosphere.
      this.context = null;
    }
  }

  setVisible(visible: boolean): void {
    const context = this.context;
    if (!context || !this.master || this.disposed) return;
    const now = context.currentTime;
    this.master.gain.cancelScheduledValues(now);
    if (visible) this.master.gain.setTargetAtTime(0.5, now, 0.6);
    else this.master.gain.setValueAtTime(0, now);
  }

  /** Cuts everything off under a breath at the ear and a heavy thud, then lets go. */
  enter(): void {
    const context = this.context;
    if (!context || !this.bed || !this.master || this.disposed) return;
    clearTimeout(this.timer);
    const now = context.currentTime;
    this.bed.gain.setValueAtTime(this.bed.gain.value, now);
    this.bed.gain.linearRampToValueAtTime(0, now + 0.08);
    const rate = this.rate;
    this.pan(this.mono(entryBreath(rate)), -0.3, -0.2, 0, 1);
    this.pan(this.mono(entryThud(rate)), 0, 0, 0.38, 1);
    this.pan(this.mono(hall(knock(rate), rate, 0.35)), 0, 0, 0.38, 1.4);
    setTimeout(() => this.dispose(), 2000);
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    clearTimeout(this.timer);
    const context = this.context;
    if (!context) return;
    const now = context.currentTime;
    this.master?.gain.cancelScheduledValues(now);
    this.master?.gain.setValueAtTime(this.master.gain.value, now);
    this.master?.gain.linearRampToValueAtTime(0, now + 0.2);
    for (const source of this.sources) source.stop(now + 0.22);
    this.sources.clear();
    this.context = null;
    setTimeout(() => void context.close().catch(() => undefined), 260);
  }

  private get rate(): number {
    return Math.min(24000, this.context!.sampleRate);
  }

  /** Whispers every few seconds, each a little closer; a knock or a creak between some. */
  private schedule(delay: number, count = 0): void {
    this.timer = setTimeout(() => {
      if (this.disposed || !this.context) return;
      const rate = this.rate;
      const closer = Math.min(1, 0.65 + count * 0.15);
      this.pan(
        this.mono(hall(whisper(rate, this.rand, WHISPER_SECONDS), rate, 0.25)),
        -1,
        1,
        0,
        0.75 * closer,
      );
      this.onWhisper(WHISPER_SECONDS);
      if (this.rand() < 0.6) {
        const later = WHISPER_SECONDS + 1 + this.rand() * 1.5;
        if (this.rand() < 0.5) {
          const blow = this.mono(hall(knock(rate), rate, 0.4));
          this.pan(blow, 0.7, 0.7, later, 0.9);
          this.pan(blow, 0.7, 0.7, later + 0.35, 0.6);
        } else
          this.pan(
            this.mono(hall(creak(rate, this.rand, 1.2), rate, 0.3)),
            -0.75,
            -0.6,
            later,
            0.55,
          );
      }
      this.schedule(5.5 + this.rand() * 2, count + 1);
    }, delay * 1000);
  }

  /** Plays `buffer` from `from` to `to` across the stereo field, starting `at` seconds from now. */
  private pan(buffer: AudioBuffer, from: number, to: number, at: number, gain: number): void {
    const context = this.context!;
    const start = context.currentTime + at;
    const panner = context.createStereoPanner();
    panner.pan.setValueAtTime(from, start);
    panner.pan.linearRampToValueAtTime(to, start + buffer.duration);
    const level = context.createGain();
    level.gain.value = gain;
    level.connect(panner).connect(this.master!);
    this.play(buffer, level, start);
  }

  private play(buffer: AudioBuffer, target: AudioNode, when = 0): AudioBufferSourceNode {
    const source = this.context!.createBufferSource();
    source.buffer = buffer;
    source.connect(target);
    source.onended = () => this.sources.delete(source);
    this.sources.add(source);
    source.start(when);
    return source;
  }

  private mono(data: Float32Array): AudioBuffer {
    const buffer = this.context!.createBuffer(1, data.length, this.rate);
    buffer.getChannelData(0).set(data);
    return buffer;
  }

  private stereo([left, right]: [Float32Array, Float32Array]): AudioBuffer {
    const buffer = this.context!.createBuffer(2, left.length, this.rate);
    buffer.getChannelData(0).set(left);
    buffer.getChannelData(1).set(right);
    return buffer;
  }
}
