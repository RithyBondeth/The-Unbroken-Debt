import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AudioSystem } from "@/audio/AudioSystem";
import { pitchJitter } from "./pagodaMix";

/** How each way of moving sounds: the step's pitch, and how the cloth or foot drags after. */
export const CORPSE_GAITS = {
  /** Patrol: a slow, heavy bare foot, and the bad one dragged through the litter. */
  walk: { rate: 0.74, drag: 0.5, dragAfter: 0.14, every: 2 },
  /** Hurrying: heavier, no time to drag. */
  lurch: { rate: 0.7, drag: 0, dragAfter: 0, every: 0 },
  /** Hands and knees: lighter knocks and the shroud scraping along under it. */
  crawl: { rate: 0.95, drag: 0.42, dragAfter: 0.05, every: 1 },
} as const;

export type CorpseGait = keyof typeof CORPSE_GAITS;

/**
 * The dead's feet, from real recordings: Sora's own bare-dirt steps (Kenney, CC0) pitched
 * down and slowed into a heavier body, with her leaf steps slowed further into a foot or a
 * shroud dragged over the ground. Nothing else of theirs sounds all the time: no breath,
 * no moan. What the player hears is something walking that should not be.
 */
export class CorpseSteps {
  private readonly steps: StaticSound[] = [];
  private readonly drags: StaticSound[] = [];
  private nextStep = 0;
  private nextDrag = 0;
  private count = 0;

  constructor(private readonly rand: () => number) {}

  async load(audio: AudioSystem, dirt: AudioBuffer[], leaves: AudioBuffer[]): Promise<void> {
    const place = (name: string, buffer: AudioBuffer) =>
      audio.spatialSound(name, buffer, "threat", Vector3.Zero(), {
        minDistance: 2,
        maxDistance: 24,
      });
    // Two of each take, so the dead's feet overlap without cutting each other off.
    for (const copy of [0, 1]) {
      for (const [k, b] of dirt.entries())
        this.steps.push(await place(`ep2_corpse_step_${copy}_${k}`, b));
      for (const [k, b] of leaves.entries())
        this.drags.push(await place(`ep2_corpse_drag_${copy}_${k}`, b));
    }
  }

  /** Whether the recordings loaded (else the stand-in thud plays). */
  get loaded(): boolean {
    return this.steps.length > 0;
  }

  /** A foot (or a hand) coming down at `at`. */
  step(at: Vector3, volume: number, gait: CorpseGait): void {
    if (!this.steps.length) return;
    const g = CORPSE_GAITS[gait];
    const s = this.steps[this.nextStep++ % this.steps.length];
    s.spatial.position = new Vector3(at.x, 0.1, at.z);
    s.volume = volume;
    s.playbackRate = g.rate * pitchJitter(this.rand, 0.06);
    s.play();
    this.count++;
    if (!g.every || this.count % g.every || !this.drags.length) return;
    const d = this.drags[this.nextDrag++ % this.drags.length];
    d.spatial.position = new Vector3(at.x, 0.05, at.z);
    d.volume = volume * 0.8;
    d.playbackRate = g.drag * pitchJitter(this.rand, 0.08);
    d.play({ waitTime: g.dragAfter });
  }

  stop(): void {
    for (const s of [...this.steps, ...this.drags]) s.stop();
  }
}
