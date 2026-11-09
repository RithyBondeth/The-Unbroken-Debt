import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { SoundState } from "@babylonjs/core/AudioV2/soundState";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AudioSystem, BusName } from "@/audio/AudioSystem";
import { SHOTS, TAKE_TRIM, loadShots, type ShotKind } from "./recordings";
import { pickTake, pitchJitter } from "./pagodaMix";

/** Where each kind sits in the mix: its bus, and the distance it is heard in full. */
const PLACEMENT: Record<ShotKind, { bus: BusName; near: number; far?: number }> = {
  bells: { bus: "sfx", near: 4, far: 90 },
  gong: { bus: "ambience", near: 3, far: 120 },
  drum: { bus: "ambience", near: 3, far: 120 },
  knock: { bus: "sfx", near: 1.5, far: 25 },
  splinter: { bus: "sfx", near: 3, far: 50 },
  creakTree: { bus: "ambience", near: 3, far: 50 },
  creakBamboo: { bus: "ambience", near: 3, far: 50 },
  gust: { bus: "ambience", near: 12, far: 90 },
  dog: { bus: "ambience", near: 4, far: 120 },
  owl: { bus: "ambience", near: 3, far: 80 },
  gecko: { bus: "ambience", near: 2.5, far: 50 },
  water: { bus: "ambience", near: 2, far: 40 },
  clay: { bus: "sfx", near: 2, far: 40 },
};

/**
 * The recorded one-shots, one placed sound per take. `play` never repeats the
 * last take of a kind if another is free, and pitches each a few percent off,
 * so a knock or a creak never sounds copied.
 */
export class ShotBank {
  private readonly takes = new Map<ShotKind, { name: string; sound: StaticSound }[]>();
  private readonly last = new Map<ShotKind, number>();

  constructor(private readonly rand: () => number) {}

  async load(audio: AudioSystem): Promise<void> {
    const buffers = await loadShots(audio);
    for (const kind of Object.keys(SHOTS) as ShotKind[]) {
      const place = PLACEMENT[kind];
      const sounds = await Promise.all(
        (buffers.get(kind) ?? []).map(async ({ name, buffer }) => ({
          name,
          sound: await audio.spatialSound("ep2_" + name, buffer, place.bus, Vector3.Zero(), {
            minDistance: place.near,
            maxDistance: place.far ?? 60,
          }),
        })),
      );
      this.takes.set(kind, sounds);
    }
  }

  /** Whether any take of `kind` loaded. */
  has(kind: ShotKind): boolean {
    return (this.takes.get(kind)?.length ?? 0) > 0;
  }

  /**
   * Plays a take of `kind` at `at`. `take` picks one (bells are one take each);
   * `pitch` is the jitter either way (0 for none). Returns the sound, or null.
   */
  play(
    kind: ShotKind,
    at: Vector3,
    volume: number,
    { take, pitch = 0.05, rate = 1 }: { take?: number; pitch?: number; rate?: number } = {},
  ): StaticSound | null {
    const takes = this.takes.get(kind);
    if (!takes?.length) return null;
    let k = take ?? pickTake(takes.length, this.last.get(kind) ?? -1, this.rand);
    // Prefer a take that is not still sounding: moving it would drag its tail along.
    if (take === undefined && takes[k].sound.state === SoundState.Started) {
      const free = takes.findIndex(
        (t, i) => i !== this.last.get(kind) && t.sound.state !== SoundState.Started,
      );
      if (free >= 0) k = free;
    }
    k = Math.max(0, Math.min(takes.length - 1, k));
    this.last.set(kind, k);
    const { name, sound } = takes[k];
    sound.spatial.position = at.clone();
    sound.volume = volume * (TAKE_TRIM[name] ?? 1);
    sound.playbackRate = rate * (pitch > 0 ? pitchJitter(this.rand, pitch) : 1);
    sound.play();
    return sound;
  }

  stop(): void {
    for (const takes of this.takes.values()) for (const t of takes) t.sound.stop();
  }
}
