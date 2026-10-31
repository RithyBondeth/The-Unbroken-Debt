import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import { seededRandom } from "../../../audio/synth";
import type { PlantSite, TreeVoice } from "../../../render/plantHeights";
import { FRONT_SPEED, GUST_RISE, type Gust, type WindState } from "../../../render/wind";
import type { Sting } from "./dreadSounds";
import {
  GUST_SECONDS,
  bambooKnock,
  carBuffet,
  crownRustle,
  frondClatter,
  gustSwell,
  leafHiss,
  trunkGroan,
  windRoar,
} from "./windSounds";

/** A sound a tree can make in the wind. */
export type TreeSound = "rustle" | "bamboo" | "fronds" | "groan";

export interface WindAudioOptions {
  /** Trees to draw rustles, knocks and groans from. */
  sites?: readonly PlantSite[];
  /** Tree sounds that may play at once (fewer on the Low preset). */
  voices?: number;
  /** Riding in the taxi: the beds heard through the body, which the gusts buffet. */
  vehicle?: boolean;
}

/** Bed levels for the wind's strength at the listener (`amount`, 0 to about 2). */
export function bedLevels(amount: number, vehicle = false): { roar: number; hiss: number } {
  const a = Math.max(0, Math.min(2, amount));
  const k = vehicle ? 0.45 : 1;
  return { roar: 0.16 * a ** 1.3 * k, hiss: 0.09 * a ** 1.1 * (vehicle ? 0.25 : 1) };
}

/** What a tree says to the wind; trunks groan only when a gust really leans on them. */
export function treeSound(voice: TreeVoice, amount: number, random: () => number): TreeSound {
  if (voice === "bamboo") return "bamboo";
  if (voice === "palm") return "fronds";
  if (voice === "dead") return "groan";
  return amount > 0.95 && random() < 0.35 ? "groan" : "rustle";
}

/**
 * A tree heard from where Sora stands: not underfoot, not out of earshot, and
 * most likely one the wind is hitting hardest right now.
 */
export function pickTree(
  sites: readonly PlantSite[],
  x: number,
  z: number,
  windAt: (x: number, z: number) => number,
  random: () => number,
  near = 5,
  far = 24,
): PlantSite | null {
  let total = 0;
  const weights: number[] = [];
  const candidates: PlantSite[] = [];
  for (const site of sites) {
    const d = Math.hypot(site.x - x, site.z - z);
    if (d < near || d > far) continue;
    const w = windAt(site.x, site.z) ** 2 * (1 - ((d - near) / (far - near)) * 0.6);
    if (w <= 0) continue;
    candidates.push(site);
    weights.push(w);
    total += w;
  }
  let u = random() * total;
  for (let i = 0; i < candidates.length; i++) {
    u -= weights[i];
    if (u <= 0) return candidates[i];
  }
  return candidates.at(-1) ?? null;
}

/**
 * A scare's hit lands with a gust: a front sent so its height reaches the
 * listener as the sting's hit does (`lead` seconds after it starts).
 */
export function stingGust(wind: WindState, kind: Sting, volume: number, lead: number): void {
  const peak = { shock: 1.05, rise: 0.75, swell: 0.5, drop: 0 }[kind] * volume;
  if (peak <= 0) return;
  const duration = kind === "shock" ? 2.6 : 4.5;
  wind.surge(peak, Math.max(3, (lead - GUST_RISE * duration) * FRONT_SPEED), duration);
}

/** Where along the wind a gust's height has reached, relative to the listener's own `along`. */
export function gustOffset(gust: Gust, time: number, along: number): number {
  return gust.origin + (time - gust.start - GUST_RISE * gust.duration) * FRONT_SPEED - along;
}

interface Voice {
  sound: StaticSound;
  kind: TreeSound;
  busyUntil: number;
}

/**
 * The wind made audible from the same WindState the foliage bends to: a
 * roar and a leaf hiss that rise and fall with its strength at Sora, each
 * gust swelling as its front passes and sweeping on downwind, and the trees
 * answering it: crowns thrashing, bamboo knocking, fronds clattering, trunks
 * groaning when a gust leans hard. All on the ambience bus, so walls muffle
 * it. When the night hushes, the wind drops, and so does all of this.
 */
export class WindAudio {
  private roar: StaticSound | null = null;
  private hiss: StaticSound | null = null;
  private readonly gusts: { sound: StaticSound; gust: Gust | null }[] = [];
  private buffet: StaticSound | null = null;
  private readonly voices: Voice[] = [];
  private readonly pending: { gust: Gust; at: number }[] = [];
  private readonly levels = { roar: 0, hiss: 0 };
  private readonly random = seededRandom(7411);
  private nextTree = 3;
  private stopped = false;
  private readonly position = new Vector3();

  constructor(
    private readonly game: Game,
    private readonly wind: WindState,
    private readonly options: WindAudioOptions = {},
  ) {}

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const bed = async (name: string, samples: Float32Array[]) => {
      const sound = await audio.sound(name, audio.buffer(samples, rate), "ambience", 0);
      sound.loop = true;
      sound.play();
      return sound;
    };
    this.roar = await bed("wind_roar", [
      windRoar(rate, seededRandom(7401)),
      windRoar(rate, seededRandom(7402)),
    ]);
    this.hiss = await bed("wind_leaves", [
      leafHiss(rate, seededRandom(7403)),
      leafHiss(rate, seededRandom(7404)),
    ]);
    for (let k = 0; k < 2; k++)
      this.gusts.push({
        sound: await audio.spatialSound(
          `wind_gust_${k}`,
          audio.buffer(gustSwell(rate, seededRandom(7405 + k)), rate),
          "ambience",
          Vector3.Zero(),
          { minDistance: 14, maxDistance: 120 },
        ),
        gust: null,
      });
    if (this.options.vehicle)
      this.buffet = await audio.sound(
        "wind_buffet",
        audio.buffer(carBuffet(rate, seededRandom(7409)), rate),
        "sfx",
        0,
      );
    const kinds: [TreeSound, (rate: number, random: () => number) => Float32Array][] = [
      ["rustle", crownRustle],
      ["bamboo", bambooKnock],
      ["fronds", frondClatter],
      ["groan", trunkGroan],
    ];
    if (this.options.sites?.length)
      for (const [kind, make] of kinds)
        for (let k = 0; k < 2; k++)
          this.voices.push({
            kind,
            busyUntil: 0,
            sound: await audio.spatialSound(
              `wind_${kind}_${k}`,
              audio.buffer(make(rate, seededRandom(7420 + this.voices.length)), rate),
              "ambience",
              Vector3.Zero(),
              { minDistance: 4, maxDistance: 40 },
            ),
          });
    // The swell's height lands as the front's height reaches the listener.
    this.wind.onGust = (gust, arrivesIn) =>
      this.pending.push({ gust, at: this.wind.time + arrivesIn - GUST_RISE * GUST_SECONDS });
  }

  update(dt: number): void {
    if (this.stopped || !this.roar) return;
    const wind = this.wind;
    const eye = this.game.camera.globalPosition;
    const amount = wind.at(eye.x, eye.z);
    const target = bedLevels(amount, this.options.vehicle);
    const k = 1 - Math.exp(-Math.max(0, dt) / 0.35);
    this.levels.roar += (target.roar - this.levels.roar) * k;
    this.levels.hiss += (target.hiss - this.levels.hiss) * k;
    this.roar.volume = this.levels.roar;
    this.roar.playbackRate = 0.92 + 0.08 * Math.min(1.5, amount);
    if (this.hiss) this.hiss.volume = this.levels.hiss;

    const along = wind.along(eye.x, eye.z);
    for (let i = this.pending.length - 1; i >= 0; i--) {
      const { gust, at } = this.pending[i];
      if (wind.time < at) continue;
      this.pending.splice(i, 1);
      const slot = this.gusts.find((g) => g.gust === null) ?? this.gusts[0];
      if (!slot) continue;
      slot.gust = gust;
      const loud = Math.min(1.4, gust.peak) * (1 - wind.calm);
      slot.sound.volume = loud * (this.options.vehicle ? 0.18 : 0.5);
      slot.sound.play({ startOffset: Math.min(GUST_SECONDS - 0.5, wind.time - at) });
      if (this.buffet) {
        this.buffet.volume = loud * 0.55;
        this.buffet.play();
      }
    }
    for (const slot of this.gusts) {
      const gust = slot.gust;
      if (!gust) continue;
      if (!wind.gusts.includes(gust)) {
        // The night hushed, or the gust has blown through: let it go quietly.
        slot.sound.volume *= 1 - k;
        if (slot.sound.volume < 0.005) {
          slot.sound.stop();
          slot.gust = null;
        }
        continue;
      }
      // The swell sweeps from upwind, over Sora and on through the trees beyond.
      const offset = Math.max(-30, Math.min(30, gustOffset(gust, wind.time, along)));
      slot.sound.spatial.position = this.position.set(
        eye.x + wind.dirX * offset,
        eye.y + 6,
        eye.z + wind.dirZ * offset,
      );
    }

    this.nextTree -= dt;
    const sites = this.options.sites;
    if (this.nextTree > 0 || !sites?.length || wind.calm > 0.3) return;
    this.nextTree = (0.6 + this.random() * 1.8) / (0.25 + Math.min(1.6, amount));
    const now = wind.time;
    const busy = this.voices.filter((v) => v.busyUntil > now).length;
    if (busy >= (this.options.voices ?? 4)) return;
    const site = pickTree(sites, eye.x, eye.z, (x, z) => wind.at(x, z), this.random);
    if (!site) return;
    const there = wind.at(site.x, site.z);
    if (there < 0.25) return;
    const kind = treeSound(site.voice, there, this.random);
    const voice = this.voices.find((v) => v.kind === kind && v.busyUntil <= now);
    if (!voice) return;
    voice.busyUntil = now + (voice.sound.buffer?.duration ?? 3);
    voice.sound.spatial.position = new Vector3(
      site.x,
      site.y + (kind === "groan" ? 2.5 : Math.min(9, site.height * 0.7)),
      site.z,
    );
    const loud = { rustle: 0.32, bamboo: 0.42, fronds: 0.34, groan: 0.5 }[kind];
    voice.sound.volume = loud * Math.min(1.3, there);
    voice.sound.playbackRate = 0.9 + this.random() * 0.2;
    voice.sound.play();
  }

  stop(): void {
    this.stopped = true;
    this.wind.onGust = null;
    for (const sound of [
      this.roar,
      this.hiss,
      this.buffet,
      ...this.gusts.map((g) => g.sound),
      ...this.voices.map((v) => v.sound),
    ])
      sound?.stop();
  }
}
