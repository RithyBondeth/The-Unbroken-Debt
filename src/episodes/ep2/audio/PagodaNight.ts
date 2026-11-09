import type { StreamingSound } from "@babylonjs/core/AudioV2/abstractAudio/streamingSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
import type { PagodaSpace } from "@/audio/acoustics";
import { FRONT_SPEED, GUST_RISE, type Gust } from "@/render/wind";
import { BEDS, PLACED_BEDS, hasRecording, soundUrls } from "./recordings";
import type { ShotBank } from "./ShotBank";
import {
  DISTANCES,
  GAPS,
  approach,
  around,
  between,
  nightDuck,
  pagodaSpace,
  windLevels,
} from "./pagodaMix";

/** Bed levels at full night (each file is -20 LUFS): the insects carry the night, quietly. */
const LEVEL = { insects: 0.68, frogs: 0.5, pond: 0.3 };
/** Gusts, creaks and calls (peak-levelled takes). */
const SHOT_LEVEL = {
  gust: 0.32,
  creakTree: 0.3,
  creakBamboo: 0.34,
  owl: 0.5,
  gecko: 0.42,
  dog: 0.6,
  drum: 0.9,
  gong: 0.75,
  water: 0.35,
};
/** Seconds the night takes to come up at the start, and to drain away at dawn. */
const FADE_IN = 4;
const FADE_OUT = 3.5;

/** The lotus pond, the hall's and the kuti's eaves (runtime X east, Z south). */
const POND = new Vector3(5, 0.3, -23);
const FROGS_WEST = new Vector3(-26, 0.5, 2);
const EAVES = [
  new Vector3(-18, 3, 8.4),
  new Vector3(-14.4, 3, 12),
  new Vector3(22, 4, -8.8),
  new Vector3(17.4, 4, 0),
];

export interface NightListener {
  x: number;
  z: number;
  safe: boolean;
  inHall: boolean;
}

/**
 * The pagoda's night from recordings (Audio Design Document 4, Episode 1's
 * NightLife and WindAudio as the model): insects from three takes that drift
 * from one to another every minute or two, frogs at the pond and in the wet
 * ground, the water's edge; the wind's beds following the shared wind, each
 * gust swelling through the trees as its front passes, trees and bamboo
 * creaking under it; far calls at uneven gaps (an owl, a tokay on the eaves, a
 * village dog, the temple's drum and gong). It comes up slowly, falls silent
 * as a Pret draws near, and drains away at dawn. The room's reverb follows Sora.
 */
export class PagodaNight {
  private insects: (StreamingSound | null)[] = [];
  private readonly insectLevels: number[] = [];
  private current = -1;
  private nextSwap = 0;
  private canopy: StreamingSound | null = null;
  private leaves: StreamingSound | null = null;
  private readonly placed: { sound: StreamingSound; level: number; ducks: boolean }[] = [];
  private readonly wind = { canopy: 0, leaves: 0 };
  private readonly gusts = new Map<
    Gust,
    { sound: ReturnType<ShotBank["play"]>; started: boolean }
  >();
  private master = 0;
  private masterTarget = 1;
  private duck = 0;
  /** Seconds the night holds its breath (the chant's silences). */
  private held = 0;
  private nextCreak = 6;
  private nextCall = 8;
  private lastCall = "";
  private nextWater = 40;
  private space: PagodaSpace | null = null;
  private stopped = false;
  private loaded = false;

  constructor(
    private readonly game: Game,
    private readonly shots: ShotBank,
    private readonly rand: () => number,
  ) {}

  async load(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const stream = async (name: string) =>
      (await hasRecording(soundUrls(name)))
        ? audio.stream("ep2_" + name, soundUrls(name), "ambience", { volume: 0 })
        : null;
    this.insects = await Promise.all(BEDS.insects.map(stream));
    this.insects.forEach(() => this.insectLevels.push(0));
    this.canopy = await stream(BEDS.canopy[0]);
    this.leaves = await stream(BEDS.leaves[0]);
    for (const sound of [this.canopy, this.leaves]) sound?.play({ startOffset: this.rand() * 40 });
    const place = async (name: string, at: Vector3, level: number, near: number, ducks = true) => {
      if (!(await hasRecording(soundUrls(name)))) return;
      const sound = await audio.spatialStream("ep2_" + name, soundUrls(name), "ambience", at, {
        loop: true,
        minDistance: near,
        maxDistance: 90,
        volume: 0,
      });
      sound.play({ startOffset: this.rand() * 25 });
      this.placed.push({ sound, level, ducks });
    };
    await place(PLACED_BEDS.frogsPond, new Vector3(6, 0.2, -23), LEVEL.frogs, 7);
    await place(PLACED_BEDS.frogsWest, FROGS_WEST, LEVEL.frogs * 0.8, 8);
    await place(PLACED_BEDS.pond, POND, LEVEL.pond, 4, false);
    this.swap();
    this.loaded = true;
  }

  /** Whether the recorded night is playing (false without audio or files). */
  get playing(): boolean {
    return this.loaded && !this.stopped && this.insects.some((s) => s !== null);
  }

  /** Drifts to another insect take, starting it somewhere new. */
  private swap(): void {
    const available = this.insects.flatMap((s, i) => (s && i !== this.current ? [i] : []));
    if (!available.length) return;
    const next = available[Math.floor(this.rand() * available.length)];
    // The sound's own volume starts at 0 and is faded by update(); the instance plays at 1.
    this.insects[next]?.play({ startOffset: this.rand() * 80 });
    this.current = next;
    this.nextSwap = between(GAPS.bedSwap, this.rand);
  }

  /**
   * Every frame. `nearestPret` in metres (99 for none); `quiet` holds back the
   * calls and the pond (cinematics, memories).
   */
  update(dt: number, l: NightListener, nearestPret: number, quiet: boolean): void {
    if (!this.loaded || this.stopped) return;
    const audio = this.game.audio;
    this.master = approach(
      this.master,
      this.masterTarget,
      dt,
      (this.masterTarget ? FADE_IN : FADE_OUT) / 3,
    );
    this.held = Math.max(0, this.held - dt);
    const duckTarget = Math.max(
      nightDuck(nearestPret, this.game.threatActive),
      this.held > 0 ? 0.85 : 0,
    );
    // The night stops at once when something comes close, and comes back slowly.
    this.duck = approach(this.duck, duckTarget, dt, duckTarget > this.duck ? 0.6 : 4);
    const life = this.master * (1 - this.duck);

    // Insects: one take at a time, crossfading over ten seconds or so.
    this.nextSwap -= dt;
    if (this.nextSwap <= 0) this.swap();
    this.insects.forEach((sound, i) => {
      if (!sound) return;
      const target = i === this.current ? 1 : 0;
      const level = (this.insectLevels[i] = approach(this.insectLevels[i], target, dt, 3.5));
      sound.volume = level * LEVEL.insects * life;
      if (target === 0 && level < 0.002 && level > 0) {
        this.insectLevels[i] = 0;
        sound.stop();
      }
    });
    for (const p of this.placed) p.sound.volume = p.level * (p.ducks ? life : this.master);

    // The wind, as the trees around Sora feel it.
    const wind = this.game.wind;
    const eye = this.game.camera.globalPosition;
    const amount = wind.at(eye.x, eye.z);
    const target = windLevels(amount);
    this.wind.canopy = approach(this.wind.canopy, target.canopy, dt, 0.5);
    this.wind.leaves = approach(this.wind.leaves, target.leaves, dt, 0.35);
    if (this.canopy) this.canopy.volume = this.wind.canopy * this.master;
    if (this.leaves) this.leaves.volume = this.wind.leaves * this.master;
    this.sweepGusts(eye.x, eye.y, eye.z);

    // Trees and bamboo answering it, never more than now and then.
    this.nextCreak -= dt * (0.4 + Math.min(1.6, amount));
    if (this.nextCreak <= 0 && wind.calm < 0.3) {
      this.nextCreak = between(GAPS.creak, this.rand);
      const kind = this.rand() < 0.35 ? "creakBamboo" : "creakTree";
      const p = around(l.x, l.z, between(DISTANCES.creak, this.rand), this.rand);
      this.shots.play(
        kind,
        new Vector3(p.x, 3 + this.rand() * 4, p.z),
        SHOT_LEVEL[kind] * Math.min(1.3, 0.5 + amount) * this.master,
        { pitch: 0.07 },
      );
    }

    // The far night: calls at uneven gaps, never two of a kind running, none while hushed.
    this.nextCall -= dt;
    if (this.nextCall <= 0) {
      this.nextCall = between(GAPS.call, this.rand);
      if (!quiet && this.duck < 0.15 && this.master > 0.5) this.call(l);
    }
    this.nextWater -= dt;
    if (this.nextWater <= 0) {
      this.nextWater = 35 + this.rand() * 60;
      if (!quiet && Math.hypot(l.x - POND.x, l.z - POND.z) < 28) {
        const p = around(POND.x, POND.z, 2 + this.rand() * 5, this.rand);
        this.shots.play("water", new Vector3(p.x, 0.1, p.z), SHOT_LEVEL.water * life, {
          pitch: 0.08,
        });
      }
    }

    // The room's acoustics follow Sora.
    const space = pagodaSpace(l.x, l.z, l);
    if (audio && space !== this.space) {
      audio.setSpace(space, this.space === null ? 0.1 : 1.5);
      this.space = space;
    }
  }

  private call(l: NightListener): void {
    const kinds: [string, number][] = [
      ["owl", 0.32],
      ["gecko", 0.28],
      ["dog", 0.22],
      ["drum", 0.09],
      ["gong", 0.09],
    ];
    let u = this.rand() * kinds.reduce((sum, [, w]) => sum + w, 0);
    let kind = kinds[0][0];
    for (const [k, w] of kinds) {
      u -= w;
      if (u <= 0) {
        kind = k;
        break;
      }
    }
    if (kind === this.lastCall) kind = kind === "owl" ? "gecko" : "owl";
    this.lastCall = kind;
    let at: Vector3;
    if (kind === "gecko") {
      at = EAVES[Math.floor(this.rand() * EAVES.length)].clone();
    } else {
      const range = kind === "dog" ? DISTANCES.dog : kind === "owl" ? DISTANCES.owl : DISTANCES.far;
      const p = around(l.x, l.z, between(range, this.rand), this.rand);
      at = new Vector3(p.x, kind === "owl" ? 9 + this.rand() * 4 : 1.5, p.z);
    }
    const level = SHOT_LEVEL[kind as keyof typeof SHOT_LEVEL];
    this.shots.play(kind as "owl", at, level * this.master, {
      pitch: kind === "dog" ? 0.06 : 0.04,
    });
  }

  /** Each gust swells through the trees as its front passes Sora (as WindAudio does). */
  private sweepGusts(x: number, y: number, z: number): void {
    const wind = this.game.wind;
    const along = wind.along(x, z);
    for (const gust of wind.gusts) {
      const offset =
        gust.origin + (wind.time - gust.start - GUST_RISE * gust.duration) * FRONT_SPEED - along;
      let slot = this.gusts.get(gust);
      if (!slot) {
        slot = { sound: null, started: false };
        this.gusts.set(gust, slot);
      }
      // Start the take as the front comes within earshot; its swell arrives with it.
      if (!slot.started && offset > -20 && offset < 10) {
        slot.started = true;
        const loud = Math.min(1.4, gust.peak / 0.3) * (1 - wind.calm);
        slot.sound = this.shots.play(
          "gust",
          new Vector3(x, y + 6, z),
          SHOT_LEVEL.gust * loud * this.master,
          { pitch: 0.04 },
        );
      }
      if (slot.sound) {
        const o = Math.max(-30, Math.min(30, offset));
        slot.sound.spatial.position = new Vector3(x + wind.dirX * o, y + 6, z + wind.dirZ * o);
      }
    }
    for (const gust of [...this.gusts.keys()])
      if (!wind.gusts.includes(gust)) this.gusts.delete(gust);
  }

  /** The insects and frogs fall silent for `seconds`, then come back slowly. */
  hush(seconds: number): void {
    this.held = Math.max(this.held, seconds);
  }

  /** Dawn: the night drains away (the birds are the soundscape's). */
  dawn(): void {
    this.masterTarget = 0;
    setTimeout(() => this.stop(), FADE_OUT * 2000);
  }

  stop(): void {
    this.stopped = true;
    for (const sound of [
      ...this.insects,
      this.canopy,
      this.leaves,
      ...this.placed.map((p) => p.sound),
    ])
      sound?.stop();
  }
}
