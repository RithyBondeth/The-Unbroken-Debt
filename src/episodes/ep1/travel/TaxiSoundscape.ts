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
  anxiousHeartbeat,
  brakeSlither,
  branchSnap,
  driverGasp,
  electricalArcZap,
  ghostRush,
  ghostScreechSting,
  mudSprint,
  neckBreathWhisper,
  radioStatic,
  subTensionDrone,
  thunderCrack,
  windowSlap,
} from "../audio/taxiDreadSounds";
import {
  TAXI_BONNET,
  TAXI_MIRROR,
  TAXI_PASSES,
  TAXI_STANDER,
  TAXI_WINDOW,
  taxiPass,
  taxiPassBeat,
  taxiSpiritAt,
  taxiVacuumDuck,
} from "./taxiApparitions";

const ramp = (t: number, from: number, to: number) =>
  Math.max(0, Math.min(1, (t - from) / (to - from)));

/**
 * The night outside and the radio inside, 0–1, from the ride clock. The forest's
 * frogs and insects fall silent as the car comes up on the still form at the
 * verge and stay silent while something is near, come back, then stop again just
 * before the overtake; the radio drifts into static and surges on every haunt beat.
 */
export function taxiNightLevels(t: number): { forest: number; radio: number } {
  const hush = Math.max(
    ramp(t, 22, 27) * (1 - ramp(t, 50, 55)),
    ramp(t, 55.8, 57) * (1 - ramp(t, 61, 67)),
  );
  let radio =
    0.08 +
    0.28 * Math.exp(-(((t - TAXI_STANDER.snapAt) / 1.4) ** 2)) +
    0.3 * Math.exp(-(((t - 30) / 3.5) ** 2)) +
    0.5 * Math.exp(-(((t - 37.8) / 1.6) ** 2));
  for (const beat of [
    ...TAXI_PASSES.map(taxiPassBeat),
    TAXI_WINDOW.beat,
    TAXI_MIRROR.lean.beat,
    TAXI_BONNET.beat,
  ])
    radio += 0.75 * Math.exp(-(((t - beat) / 0.7) ** 2));
  return { forest: 1 - hush, radio: Math.min(1, radio) };
}

/**
 * 0–1 psychological anxiety curve across the 72 s drive: drives the accelerating
 * chest-cavity heartbeat and the infrasonic tension drone that swells in every silence vacuum.
 */
export function taxiAnxietyLevel(t: number): number {
  const base =
    ramp(t, 18, 25) * 0.28 +
    ramp(t, 33, 37.5) * 0.42 -
    ramp(t, 41, 45) * 0.25 +
    ramp(t, 46, 52) * 0.35 +
    ramp(t, 56, 60.5) * 0.35 -
    ramp(t, 61.8, 64.6) * 0.62;
  const vacuumBoost = taxiVacuumDuck(t) * 0.55;
  const bonnetSpike = Math.exp(-(((t - TAXI_BONNET.beat) / 1.6) ** 2)) * 0.72;
  return Math.max(0, Math.min(1, base + vacuumBoost + bonnetSpike));
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
 * Cinema-grade 5-beat spatial HRTF horror soundscape for the 1933 Citroën Rosalie ride:
 * vacuum-silence ducking before major hits, dynamically accelerating heartbeat, infrasonic
 * tension drone, 6V dash relay sputters, Doppler road sprint, behind-neck binaural breath,
 * real-time HRTF mud chase, violent glass impact + fingernail drag, and close lightning cracks.
 */
export class TaxiSoundscape {
  private forest: StaticSound[] = [];
  private radio: StaticSound | null = null;
  private meter: StaticSound | null = null;
  private heartbeat: StaticSound | null = null;
  private subDrone: StaticSound | null = null;
  private sprint: StaticSound | null = null;
  private readonly activeOneShots: StaticSound[] = [];
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

    // Forest night beds muffled through closed 1930s sedan glass
    for (const [name, samples, seed] of [
      ["taxi_frogs", frogsLoop, 220],
      ["taxi_crickets", cricketsLoop, 221],
    ] as const) {
      const sound = await audio.sound(
        name,
        buffer(biquad(samples(rate, seededRandom(seed)), rate, "lowpass", 2400, 0.7)),
        "ambience",
        0,
      );
      sound.loop = true;
      this.forest.push(sound);
    }

    // Continuous psychological dread beds: accelerating heartbeat & infrasonic vacuum drone
    this.heartbeat = await audio.sound(
      "taxi_anxious_heartbeat",
      buffer(anxiousHeartbeat(rate, seededRandom(240))),
      "threat",
      0,
    );
    this.heartbeat.loop = true;

    this.subDrone = await audio.sound(
      "taxi_sub_tension_drone",
      buffer(subTensionDrone(rate, seededRandom(241))),
      "music",
      0,
    );
    this.subDrone.loop = true;

    // Dashboard valve radio static & mechanical Phnom Penh clockwork taximeter
    this.radio = await audio.spatialSound(
      "taxi_radio_static",
      buffer(radioStatic(rate, seededRandom(222))),
      "sfx",
      new Vector3(0, 0.76, 0.56),
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
    this.meter.volume = 0.48;

    // Real-time 3D HRTF-tracked barefoot mud sprint during Beat 4a jungle chase
    this.sprint = await audio.spatialSound(
      "taxi_sprint",
      buffer(mudSprint(rate, seededRandom(225))),
      "threat",
      Vector3.Zero(),
      { minDistance: 1.2, maxDistance: 32 },
    );

    const track = (s: StaticSound) => {
      this.activeOneShots.push(s);
      return s;
    };
    const oneShot = async (
      name: string,
      samples: Float32Array | Float32Array[],
      bus: "sfx" | "threat" | "voice",
      volume: number,
    ) => track(await audio.sound(name, buffer(samples), bus, volume));
    const spatialShot = async (
      name: string,
      samples: Float32Array | Float32Array[],
      bus: "sfx" | "threat" | "voice",
      pos: Vector3,
      minDistance = 0.4,
      maxDistance = 12,
    ) =>
      track(
        await audio.spatialSound(name, buffer(samples), bus, pos, {
          minDistance,
          maxDistance,
        }),
      );

    const rush = await oneShot(
      "taxi_ghost_rush",
      ghostRush(rate, seededRandom(224), -1, 1),
      "threat",
      0.92,
    );
    const brake = await oneShot(
      "taxi_brake_slither",
      brakeSlither(rate, seededRandom(228)),
      "sfx",
      0.88,
    );
    const gasp = await spatialShot(
      "taxi_driver_gasp",
      driverGasp(rate, seededRandom(229)),
      "voice",
      new Vector3(-0.39, 1.28, 0.05),
      0.45,
      5,
    );
    const slap = await spatialShot(
      "taxi_window_slap",
      windowSlap(rate, seededRandom(230)),
      "threat",
      new Vector3(0.86, 1.14, 0.05),
      0.4,
      8,
    );
    const snap = await spatialShot(
      "taxi_branch_snap",
      branchSnap(rate, seededRandom(242)),
      "threat",
      new Vector3(3.1, 1.0, 1.2),
      1.0,
      18,
    );
    const arcZap = await spatialShot(
      "taxi_electrical_arc",
      electricalArcZap(rate, seededRandom(243)),
      "sfx",
      new Vector3(0, 0.72, 0.55),
      0.35,
      4,
    );
    const screechFront = await spatialShot(
      "taxi_screech_front",
      ghostScreechSting(rate, seededRandom(244)),
      "threat",
      new Vector3(0.15, 1.05, 1.9),
      0.9,
      16,
    );
    const screechSide = await spatialShot(
      "taxi_screech_side",
      ghostScreechSting(rate, seededRandom(245)),
      "threat",
      new Vector3(0.88, 1.12, 0.05),
      0.45,
      12,
    );
    const screechRear = await spatialShot(
      "taxi_screech_rear",
      ghostScreechSting(rate, seededRandom(246)),
      "threat",
      new Vector3(0.24, 1.12, -0.35),
      0.35,
      8,
    );
    const neckBreath = await spatialShot(
      "taxi_neck_breath",
      neckBreathWhisper(rate, seededRandom(247)),
      "threat",
      new Vector3(0.22, 1.12, -0.3),
      0.22,
      3.5,
    );
    const breath = await spatialShot(
      "taxi_back_seat_breath",
      breathOut(rate, seededRandom(232)),
      "threat",
      new Vector3(0.3, 1.18, -0.75),
      0.3,
      4,
    );
    const whisper = await spatialShot(
      "taxi_back_seat_whisper",
      whispers(rate, seededRandom(233)),
      "threat",
      new Vector3(0.24, 1.24, -0.45),
      0.25,
      3,
    );
    const crack = await oneShot(
      "taxi_thunder_crack",
      thunderCrack(rate, seededRandom(248)),
      "threat",
      0.85,
    );
    const roll = await oneShot(
      "taxi_far_thunder",
      thunder(rate, seededRandom(231)),
      "threat",
      0.45,
    );

    const playAt = (sound: StaticSound, vol: number) => () => {
      sound.volume = vol;
      sound.play();
    };

    // Early distant monsoon storm rumbles over the flooded rice paddies
    this.cues.push({ at: 9.75, play: playAt(roll, 0.28) });
    this.cues.push({ at: 14.0, play: playAt(roll, 0.44) });

    // BEAT 1 (17.4..24.0 s): Verge watcher — subtle swell, then sudden right-verge snap & lightning crack!
    this.cues.push({ at: TAXI_STANDER.level - 1.3, play: () => this.score.sting("swell", 0.58) });
    this.cues.push({ at: TAXI_STANDER.snapAt - 0.03, play: playAt(snap, 0.85) });
    this.cues.push({ at: TAXI_STANDER.snapAt + 0.04, play: playAt(crack, 0.62) });

    // BEAT 2 (37.05..38.03 s, beat 37.78 s): Electrics zap -> vacuum silence -> blistering Doppler sprint!
    const cross = taxiPass("crossing"),
      overtake = taxiPass("overtake");
    const crossBeat = taxiPassBeat(cross);
    this.cues.push({ at: crossBeat - 1.05, play: playAt(arcZap, 0.72) });
    this.cues.push({ at: crossBeat - 0.6, play: playAt(rush, 0.92) });
    this.cues.push({
      at: crossBeat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.98),
    });
    this.cues.push({ at: crossBeat - 0.02, play: playAt(screechFront, 0.76) });
    this.cues.push({ at: crossBeat + 0.02, play: playAt(crack, 0.92) });
    this.cues.push({ at: crossBeat + 0.08, play: playAt(brake, 0.9) });
    this.cues.push({ at: crossBeat + 0.14, play: playAt(gasp, 0.95) });
    this.cues.push({ at: crossBeat + 0.42, play: () => this.score.ring() });

    // BEAT 3 (46.0..49.2 s seated -> 52.02..54.15 s snap-lunge): Back-seat breath -> dead air -> 25 cm ear breath!
    const { seated, lean } = TAXI_MIRROR;
    this.cues.push({ at: seated.from + 0.25, play: () => this.score.sting("swell", 0.56) });
    this.cues.push({ at: seated.from + 0.55, play: playAt(breath, 0.68) });
    this.cues.push({ at: lean.beat - 0.32, play: playAt(arcZap, 0.72) });
    this.cues.push({ at: lean.from, play: playAt(neckBreath, 1.0) });
    this.cues.push({ at: lean.from + 0.04, play: playAt(whisper, 0.76) });
    this.cues.push({
      at: lean.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.98),
    });
    this.cues.push({ at: lean.beat - 0.02, play: playAt(screechRear, 0.74) });
    this.cues.push({ at: lean.beat + 0.02, play: playAt(crack, 0.88) });
    this.cues.push({ at: lean.beat + 0.36, play: () => this.score.ring() });
    this.cues.push({ at: lean.to - 0.12, play: () => whisper.stop() });

    // BEAT 4a (57.30..57.88 s): Precursor crack -> real-time HRTF mud sprint -> violent right-glass SLAM #1!
    this.cues.push({ at: 55.64, play: playAt(crack, 0.66) });
    this.cues.push({ at: overtake.start - 0.22, play: () => this.sprint?.play() });
    const slapBeat = taxiPassBeat(overtake);
    this.cues.push({
      at: slapBeat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.88),
    });
    this.cues.push({ at: slapBeat - 0.01, play: playAt(slap, 0.96) });
    this.cues.push({ at: slapBeat + 0.01, play: playAt(screechSide, 0.64) });

    // BEAT 4b (60.16..60.96 s, beat 60.56 s): Total blackout -> deepest vacuum -> PEAK eye-level glass impact!
    this.cues.push({ at: TAXI_WINDOW.beat - 0.88, play: playAt(arcZap, 0.82) });
    this.cues.push({
      at: TAXI_WINDOW.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 1.0),
    });
    this.cues.push({ at: TAXI_WINDOW.beat - 0.02, play: playAt(screechSide, 0.94) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.01, play: playAt(crack, 1.0) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.04, play: playAt(slap, 0.84) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.12, play: playAt(gasp, 1.0) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.38, play: () => this.score.ring() });

    // BEAT 5 (65.45..65.72 s, beat 65.56 s): False calm during braking -> sudden zap -> unexpected BONNET flash!
    this.cues.push({ at: TAXI_BONNET.start - 0.15, play: playAt(arcZap, 0.78) });
    this.cues.push({
      at: TAXI_BONNET.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.96),
    });
    this.cues.push({ at: TAXI_BONNET.beat - 0.02, play: playAt(screechFront, 0.92) });
    this.cues.push({ at: TAXI_BONNET.beat + 0.01, play: playAt(crack, 0.92) });
    this.cues.push({ at: TAXI_BONNET.beat + 0.06, play: playAt(brake, 0.86) });
    this.cues.push({ at: TAXI_BONNET.beat + 0.36, play: () => this.score.ring() });
  }

  /** Starts the beds. Cues before `t` (a resumed ride) are not replayed. */
  begin(t: number): void {
    this.last = t;
    for (const sound of this.forest) sound.play();
    this.radio?.play();
    this.meter?.play();
    this.heartbeat?.play();
    this.subDrone?.play();
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
    const vacuum = taxiVacuumDuck(t);
    const anxiety = taxiAnxietyLevel(t);

    // Forest crickets & frogs fall silent around haunts AND drop completely inside silence vacuums
    const forestGain = levels.forest * (1 - vacuum * 0.95);
    this.forest.forEach((sound, i) => (sound.volume = forestGain * [0.42, 0.3][i]));

    // Radio swells sharply with paranormal proximity, sputtering slightly in total silence vacuum
    if (this.radio) this.radio.volume = levels.radio * 0.58 * (1 - vacuum * 0.35);

    // Clockwork taximeter ticks eerily clear even when rain & engine drop into dead air
    if (this.meter) this.meter.volume = 0.48 * (1 - vacuum * 0.42);

    // Dynamically accelerating heartbeat: 54 BPM resting → 107 BPM pounding panic in vacuums!
    if (this.heartbeat) {
      this.heartbeat.volume = anxiety > 0.04 ? Math.min(0.82, anxiety * 0.62 + vacuum * 0.38) : 0;
      this.heartbeat.playbackRate = 0.9 + anxiety * 0.88;
    }

    // Infrasonic tension drone fills the suffocating silence vacuum right before each hit!
    if (this.subDrone) {
      this.subDrone.volume = Math.min(0.68, anxiety * 0.24 + vacuum * 0.56);
    }

    // Real-time 3D HRTF tracking of barefoot mud sprint rushing out of the trees onto Sora's glass
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
    this.heartbeat?.stop();
    this.subDrone?.stop();
    this.sprint?.stop();
    for (const sound of this.activeOneShots) sound.stop();
  }
}
