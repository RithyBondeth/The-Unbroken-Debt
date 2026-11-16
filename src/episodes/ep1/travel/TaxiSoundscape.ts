import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AudioSystem } from "@/audio/AudioSystem";
import { biquad, seededRandom } from "@/audio/synth";
import { breathOut, cricketsLoop, frogsLoop } from "@/audio/sounds/nightSounds";
import { whispers } from "../audio/vigilSounds";
import { thunder } from "../audio/prologueSounds";
import { taxiMeter } from "../audio/taxiSounds";
import type { DreadScore } from "@/audio/DreadScore";
import {
  brakeSlither,
  driverGasp,
  mudSprint,
  radioStatic,
  windowSlap,
} from "../audio/taxiDreadSounds";
import {
  TAXI_PASSES,
  TAXI_MIRROR,
  TAXI_STANDER,
  TAXI_WINDOW,
  taxiPass,
  taxiPassBeat,
  taxiSpiritAt,
} from "./taxiApparitions";

const ramp = (t: number, from: number, to: number) =>
  Math.max(0, Math.min(1, (t - from) / (to - from)));

/**
 * The night outside and the radio inside, 0–1, from the ride clock. The forest's
 * frogs and insects fall silent as the car comes up on the still form at the
 * verge and stay silent while something is near, come back, then stop again just
 * before the last pass; the
 * radio drifts into static and surges whenever something runs close.
 */
export function taxiNightLevels(t: number): { forest: number; radio: number } {
  const hush = Math.max(
    ramp(t, 22, 27) * (1 - ramp(t, 50, 55)),
    ramp(t, 55.8, 57) * (1 - ramp(t, 61, 67)),
  );
  let radio =
    0.08 + 0.3 * Math.exp(-(((t - 30) / 3.5) ** 2)) + 0.5 * Math.exp(-(((t - 37.8) / 1.6) ** 2));
  for (const beat of [...TAXI_PASSES.map(taxiPassBeat), TAXI_WINDOW.beat, TAXI_MIRROR.lean.beat])
    radio += 0.75 * Math.exp(-(((t - beat) / 0.7) ** 2));
  return { forest: 1 - hush, radio: Math.min(1, radio) };
}

/** The driver lifts off the throttle when something crosses ahead, then drives on harder. */
export function taxiThrottle(t: number): number {
  const s = t - taxiPassBeat(taxiPass("crossing"));
  if (s < 0 || s > 3) return 1;
  return 1 - 0.55 * Math.exp(-s * 1.3) * Math.min(1, s * 8);
}

interface Cue {
  at: number;
  play: () => void;
}

/**
 * The ride's dread layer over the engine, wipers and rain TaxiRide already plays:
 * the forest at night through the body, the dash radio between stations, and the
 * Neak Ta heard truthfully: feet in the mud coming up Sora's side between the
 * flickers, its hands on her window. The score's stings land on those beats.
 * Positions follow the route.
 */
export class TaxiSoundscape {
  private forest: StaticSound[] = [];
  private radio: StaticSound | null = null;
  private meter: StaticSound | null = null;
  private sprint: StaticSound | null = null;
  private readonly cues: Cue[] = [];
  private last = -1;
  private stopped = false;

  constructor(
    private readonly audio: AudioSystem | null,
    private readonly route: TransformNode,
    private readonly score: DreadScore,
    private readonly meterAt = new Vector3(0.27, 1.17, 1.13),
  ) {}

  async load(): Promise<void> {
    const audio = this.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate,
      buffer = (samples: Float32Array | Float32Array[]) => audio.buffer(samples, rate);
    // Heard from inside a closed car: the body takes the top off the night.
    for (const [name, samples, seed] of [
      ["taxi_frogs", frogsLoop, 220],
      ["taxi_crickets", cricketsLoop, 221],
    ] as const) {
      const sound = await audio.sound(
        name,
        buffer(biquad(samples(rate, seededRandom(seed)), rate, "lowpass", 2600, 0.7)),
        "ambience",
        0,
      );
      sound.loop = true;
      this.forest.push(sound);
    }
    this.radio = await audio.spatialSound(
      "taxi_radio_static",
      buffer(radioStatic(rate, seededRandom(222))),
      "sfx",
      new Vector3(0, 0.94, 0.97),
      { minDistance: 0.4, maxDistance: 6, loop: true },
    );
    this.radio.volume = 0;
    this.meter = await audio.spatialSound(
      "taxi_meter_clockwork",
      buffer(taxiMeter(rate, seededRandom(232))),
      "sfx",
      this.meterAt,
      { minDistance: 0.35, maxDistance: 5, loop: true },
    );
    this.meter.volume = 0.5;
    this.sprint = await audio.spatialSound(
      "taxi_sprint",
      buffer(mudSprint(rate, seededRandom(225))),
      "threat",
      Vector3.Zero(),
      { minDistance: 1.5, maxDistance: 30 },
    );
    const oneShot = async (
      name: string,
      samples: Float32Array | Float32Array[],
      bus: "sfx" | "threat" | "voice",
      volume: number,
    ) => audio.sound(name, buffer(samples), bus, volume);
    const brake = await oneShot(
      "taxi_brake_slither",
      brakeSlither(rate, seededRandom(228)),
      "sfx",
      0.8,
    );
    const gasp = await audio.spatialSound(
      "taxi_driver_gasp",
      buffer(driverGasp(rate, seededRandom(229))),
      "voice",
      new Vector3(-0.39, 1.32, 0.05),
      { minDistance: 0.5, maxDistance: 5 },
    );
    const slap = await audio.spatialSound(
      "taxi_window_slap",
      buffer(windowSlap(rate, seededRandom(230))),
      "threat",
      new Vector3(0.86, 1.15, 0.05),
      { minDistance: 0.5, maxDistance: 8 },
    );
    const roll = await oneShot("taxi_far_thunder", thunder(rate, seededRandom(231)), "threat", 0.4);
    // The two other lightning flashes get their thunder too, later for the farther one.
    this.cues.push({ at: 14.6, play: () => ((roll.volume = 0.3), roll.play()) });
    this.cues.push({ at: 56.3, play: () => ((roll.volume = 0.5), roll.play()) });
    const cross = taxiPass("crossing"),
      overtake = taxiPass("overtake");
    const crossBeat = taxiPassBeat(cross);
    this.cues.push({
      at: crossBeat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.95),
    });
    // No rush of air across the beams: it only staggers. The brakes and his breath are the sound.
    this.cues.push({ at: crossBeat + 0.1, play: () => brake.play() });
    this.cues.push({ at: crossBeat + 0.16, play: () => gasp.play() });
    this.cues.push({ at: crossBeat + 0.45, play: () => this.score.ring() });
    this.cues.push({ at: overtake.start, play: () => this.sprint?.play() });
    const slapBeat = taxiPassBeat(overtake);
    this.cues.push({
      at: slapBeat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.8),
    });
    this.cues.push({ at: slapBeat, play: () => slap.play() });
    // The still form at the verge is only a swell under the engine: was that a person?
    this.cues.push({ at: TAXI_STANDER.level - 1.1, play: () => this.score.sting("swell", 0.55) });
    // The face at the window: the hardest hit of the ride, then her ears ringing.
    this.cues.push({
      at: TAXI_WINDOW.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 1),
    });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.05, play: () => ((slap.volume = 0.6), slap.play()) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.12, play: () => gasp.play() });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.4, play: () => this.score.ring() });
    this.cues.push({ at: TAXI_WINDOW.beat + 1.5, play: () => ((roll.volume = 0.6), roll.play()) });
    // The back seat. A slow breath out behind her shoulder while it sits there,
    // then whispering right at her ear as the lightning shows it leaning in.
    const behind = new Vector3(0.3, 1.25, -0.72);
    const breath = await audio.spatialSound(
      "taxi_back_seat_breath",
      buffer(breathOut(rate, seededRandom(232))),
      "threat",
      behind,
      { minDistance: 0.3, maxDistance: 4 },
    );
    const whisper = await audio.spatialSound(
      "taxi_back_seat_whisper",
      buffer(whispers(rate, seededRandom(233))),
      "threat",
      new Vector3(0.24, 1.3, -0.45),
      { minDistance: 0.25, maxDistance: 3 },
    );
    const { seated, lean } = TAXI_MIRROR;
    this.cues.push({ at: seated.from + 0.2, play: () => this.score.sting("swell", 0.5) });
    this.cues.push({ at: seated.from + 0.9, play: () => ((breath.volume = 0.55), breath.play()) });
    this.cues.push({
      at: lean.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.9),
    });
    this.cues.push({ at: lean.from, play: () => ((whisper.volume = 0.8), whisper.play()) });
    this.cues.push({ at: lean.beat + 0.5, play: () => whisper.stop() });
    this.cues.push({ at: lean.beat + 0.35, play: () => this.score.ring() });
  }

  /** Starts the beds. Cues before `t` (a resumed ride) are not replayed. */
  begin(t: number): void {
    this.last = t;
    for (const sound of this.forest) sound.play();
    this.radio?.play();
    this.meter?.play();
    this.apply(t);
  }

  update(t: number): void {
    if (this.stopped || this.last < 0) return;
    for (const cue of this.cues) if (cue.at > this.last && cue.at <= t) cue.play();
    this.last = t;
    this.apply(t);
  }

  private apply(t: number): void {
    const levels = taxiNightLevels(t);
    this.forest.forEach((sound, i) => (sound.volume = levels.forest * [0.42, 0.3][i]));
    if (this.radio) this.radio.volume = levels.radio * 0.55;
    // Feet in the mud between the flickers: it is heard coming up Sora's side, never seen moving.
    const spirit = taxiSpiritAt(t);
    if (this.sprint && spirit?.kind === "overtake")
      this.sprint.spatial.position = this.toWorld(spirit.x, 0.9, spirit.z);
  }

  private toWorld(x: number, y: number, z: number): Vector3 {
    return Vector3.TransformCoordinates(new Vector3(x, y, z), this.route.computeWorldMatrix(true));
  }

  stop(): void {
    this.stopped = true;
    for (const sound of this.forest) sound.stop();
    this.radio?.stop();
    this.meter?.stop();
    this.sprint?.stop();
  }
}
