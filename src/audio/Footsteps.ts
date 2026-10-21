import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { AudioSystem } from "./AudioSystem";
import type { EventBus } from "../core/EventBus";
import type { GameEvents } from "../core/events";
import type { Surface } from "../core/Physics";
import { mudSuction, seededRandom } from "./synth";

/** Recorded takes per surface (tools/audio/make-footsteps.sh). */
const TAKES = 5;
const SETS = ["teak", "stone", "leaves", "dirt", "mud"] as const;
type StepSet = (typeof SETS)[number];
/** Ep 3's shallow water has no takes yet: it borrows the mud. */
const SET_FOR: Record<Surface, StepSet> = {
  teak: "teak",
  dirt: "dirt",
  mud: "mud",
  leaves: "leaves",
  stone: "stone",
  water: "mud",
};
/** Evens out the takes: the grass-based sets are quieter than wood and stone. */
const TRIM: Record<StepSet, number> = { teak: 1, stone: 0.9, leaves: 1.1, dirt: 1.4, mud: 1.5 };
/** Sora walking: her steps sit under the night, never over it. */
const WALK_VOLUME = 0.3;
const SUCTIONS = 4;

/** The URLs of one recorded take, Opus first and AAC as the fallback. */
export function stepUrls(set: StepSet, take: number): string[] {
  const base = `${import.meta.env.BASE_URL}assets/shared/audio/sfx_step_${set}_${String(take).padStart(3, "0")}`;
  return [`${base}.ogg`, `${base}.m4a`];
}

/** A take other than the last one played, so no step sounds twice in a row. */
export function pickTake(count: number, last: number, rand: () => number): number {
  if (count < 2) return 0;
  const k = Math.floor(rand() * (count - 1));
  return k >= last ? k + 1 : k;
}

/**
 * How loud a step is for the noise the player controller reports (walk 0.35,
 * hurry 1, crouch 0.12): crouching is soft but still heard.
 */
export function stepVolume(loudness: number): number {
  return WALK_VOLUME * Math.sqrt(Math.max(0, loudness) / 0.35);
}

/**
 * Sora's footsteps (Audio Design Document 4.1): a recorded take for the surface
 * under her feet each time her stride lands, never the same take twice running,
 * pitched a little either way. In mud a suction rises as her foot comes free.
 */
export class Footsteps {
  private readonly last = new Map<StepSet, number>();
  private lastSuction = 0;
  private readonly rand = seededRandom(711);

  private constructor(
    /** The decoded takes per surface, for others who walk (the follower). */
    readonly buffers: Map<StepSet, AudioBuffer[]>,
    readonly suctionBuffers: AudioBuffer[],
    private readonly sets: Map<StepSet, StaticSound[]>,
    private readonly suctions: StaticSound[],
  ) {}

  static async load(audio: AudioSystem, bus: EventBus<GameEvents>): Promise<Footsteps> {
    const buffers = new Map<StepSet, AudioBuffer[]>();
    const sets = new Map<StepSet, StaticSound[]>();
    for (const set of SETS) {
      const takes = await Promise.all(
        Array.from({ length: TAKES }, (_, k) => audio.load(stepUrls(set, k))),
      );
      const loaded = takes.filter((b): b is AudioBuffer => b !== null);
      buffers.set(set, loaded);
      sets.set(
        set,
        await Promise.all(loaded.map((b, k) => audio.sound(`step_${set}_${k}`, b, "sfx"))),
      );
    }
    const rate = audio.context.sampleRate;
    const suctionBuffers = Array.from({ length: SUCTIONS }, (_, k) =>
      audio.buffer(mudSuction(rate, seededRandom(90 + k)), rate),
    );
    const suctions = await Promise.all(
      suctionBuffers.map((b, k) => audio.sound(`step_suction_${k}`, b, "sfx")),
    );
    const steps = new Footsteps(buffers, suctionBuffers, sets, suctions);
    bus.on("player:step", ({ surface, loudness }) => steps.step(surface as Surface, loudness));
    return steps;
  }

  /** The set a surface sounds like. */
  static setFor(surface: Surface): StepSet {
    return SET_FOR[surface] ?? "dirt";
  }

  private step(surface: Surface, loudness: number): void {
    const set = Footsteps.setFor(surface);
    const takes = this.sets.get(set) ?? [];
    if (takes.length === 0) return;
    const k = pickTake(takes.length, this.last.get(set) ?? -1, this.rand);
    this.last.set(set, k);
    const volume = stepVolume(loudness) * TRIM[set];
    const take = takes[k];
    take.playbackRate = 0.94 + this.rand() * 0.12;
    take.play({ volume: volume * (0.85 + this.rand() * 0.3) });
    if (set === "mud") {
      const s = pickTake(this.suctions.length, this.lastSuction, this.rand);
      this.lastSuction = s;
      const suction = this.suctions[s];
      suction.playbackRate = 0.9 + this.rand() * 0.2;
      // The foot comes free a moment after it lands.
      suction.play({ volume: volume * (0.25 + this.rand() * 0.25), waitTime: 0.06 });
    }
  }
}
