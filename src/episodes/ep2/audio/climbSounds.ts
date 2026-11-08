import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AudioSystem } from "@/audio/AudioSystem";
import { pickTake, pitchJitter } from "./pagodaMix";
import { soundUrls } from "./recordings";

/**
 * The kmaoch that comes down a tree: CC0 recordings (tools/audio/make-ep2-climb.sh,
 * sources in tools/audio/ep2-freesound.json).
 */
export const CLIMB_TAKES = {
  /** Scrambling down bark, fingers raking it. */
  climb: ["sfx_ep2_climb_1", "sfx_ep2_climb_2", "sfx_ep2_climb_3"],
  /** Nails dug into the wood while it waits for her to look. */
  scratch: ["sfx_ep2_scratch_1", "sfx_ep2_scratch_2", "sfx_ep2_scratch_3"],
  /** The body hitting the leaf litter. */
  drop: ["sfx_ep2_drop_1", "sfx_ep2_drop_2", "sfx_ep2_drop_3", "sfx_ep2_drop_4"],
  /** Coming on hands and knees, fast. */
  scuttle: ["sfx_ep2_scuttle_1"],
} as const;

export type ClimbKind = keyof typeof CLIMB_TAKES;

/** Heard in full this close, gone this far (metres). */
const RANGE: Record<ClimbKind, [number, number]> = {
  climb: [3, 35],
  scratch: [2.5, 28],
  drop: [3, 40],
  scuttle: [2, 26],
};

/** One placed sound per take; never the same take twice running. */
export class ClimbSounds {
  private readonly takes = new Map<ClimbKind, StaticSound[]>();
  private readonly last = new Map<ClimbKind, number>();

  constructor(private readonly rand: () => number) {}

  async load(audio: AudioSystem): Promise<void> {
    for (const kind of Object.keys(CLIMB_TAKES) as ClimbKind[]) {
      const sounds: StaticSound[] = [];
      for (const name of CLIMB_TAKES[kind]) {
        const buffer = await audio.load(soundUrls(name));
        if (!buffer) continue;
        const [near, far] = RANGE[kind];
        sounds.push(
          await audio.spatialSound("ep2_" + name, buffer, "threat", Vector3.Zero(), {
            minDistance: near,
            maxDistance: far,
          }),
        );
      }
      this.takes.set(kind, sounds);
    }
  }

  /** Plays a take of `kind` at `at`; returns it so it can follow a moving body. */
  play(kind: ClimbKind, at: Vector3, volume: number, pitch = 0.06): StaticSound | null {
    const takes = this.takes.get(kind);
    if (!takes?.length) return null;
    const k = pickTake(takes.length, this.last.get(kind) ?? -1, this.rand);
    this.last.set(kind, k);
    const sound = takes[k];
    sound.spatial.position = at.clone();
    sound.volume = volume;
    sound.playbackRate = pitchJitter(this.rand, pitch);
    sound.play();
    return sound;
  }

  stop(): void {
    for (const takes of this.takes.values()) for (const s of takes) s.stop();
  }
}
