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
  glassNailScrape,
  mudSprint,
  neckBreathWhisper,
  radioStatic,
  seatSpringCreak,
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

function ep1AudioUrls(name: string): string[] {
  const base = `${import.meta.env.BASE_URL}assets/ep1/audio/${name}`;
  return [`${base}.ogg`, `${base}.m4a`];
}

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
    0.34 * Math.exp(-(((t - 30.2) / 3.2) ** 2)) +
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
 * chest-cavity heartbeat, the infrasonic tension drone, driver/Sora physical tension,
 * and post-processing vignette tightening inside every silence vacuum.
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
 * Cinema-grade spatial HRTF horror soundscape for the 1933 Citroën Rosalie night drive:
 * pairs mastered real CC0 Freesound recordings (thunder pools, layered steel-door & glass
 * slams, wet glass fingernail drag, back-seat weight creak, close-mic breath/whispers,
 * startled female gasp, vintage Edison filament sputter, splintering jungle branch, mud
 * splashes) with physically modelled acoustic synths, real-time HRTF chase tracking,
 * accelerating chest heartbeat, and suffocating pre-scare silence vacuums.
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

    const loadRecorded = async (asset: string, fallback: () => Float32Array | Float32Array[]) =>
      (await audio.load(ep1AudioUrls(asset))) ?? buffer(fallback());

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
    this.meter.volume = 0.44;

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
      buf: AudioBuffer,
      bus: "sfx" | "threat" | "voice",
      volume: number,
    ) => track(await audio.sound(name, buf, bus, volume));
    const spatialShot = async (
      name: string,
      buf: AudioBuffer,
      bus: "sfx" | "threat" | "voice",
      pos: Vector3,
      minDistance = 0.4,
      maxDistance = 12,
    ) =>
      track(
        await audio.spatialSound(name, buf, bus, pos, {
          minDistance,
          maxDistance,
        }),
      );

    // Load real mastered CC0 Freesound clips in parallel (with seamless synth fallbacks!)
    const [
      th1Buf,
      th2Buf,
      th3Buf,
      slamRecBuf,
      scrapeRecBuf,
      neckRecBuf,
      wh1Buf,
      wh2Buf,
      wh3Buf,
      soraGasp1Buf,
      soraGasp2Buf,
      branchRecBuf,
      seatCreakRecBuf,
      elecRecBuf,
      splash1Buf,
      splash2Buf,
    ] = await Promise.all([
      loadRecorded("sfx_ep1_taxi_thunder_1", () => thunder(rate, seededRandom(231))),
      loadRecorded("sfx_ep1_taxi_thunder_2", () => thunder(rate, seededRandom(235))),
      loadRecorded("sfx_ep1_taxi_thunder_3", () => thunderCrack(rate, seededRandom(236))),
      loadRecorded("sfx_ep1_taxi_window_slam", () => windowSlap(rate, seededRandom(230))),
      loadRecorded("sfx_ep1_taxi_glass_scrape", () => glassNailScrape(rate, seededRandom(251))),
      loadRecorded("sfx_ep1_taxi_neck_breath", () => neckBreathWhisper(rate, seededRandom(247))),
      loadRecorded("sfx_ep1_taxi_whisper_1", () => whispers(rate, seededRandom(233))),
      loadRecorded("sfx_ep1_taxi_whisper_2", () => whispers(rate, seededRandom(234))),
      loadRecorded("sfx_ep1_taxi_whisper_3", () => whispers(rate, seededRandom(237))),
      loadRecorded("sfx_ep1_taxi_sora_gasp_1", () => breathOut(rate, seededRandom(252))),
      loadRecorded("sfx_ep1_taxi_sora_gasp_2", () => breathOut(rate, seededRandom(253))),
      loadRecorded("sfx_ep1_taxi_branch_snap", () => branchSnap(rate, seededRandom(242))),
      loadRecorded("sfx_ep1_taxi_seat_creak", () => seatSpringCreak(rate, seededRandom(254))),
      loadRecorded("sfx_ep1_taxi_elec_flicker", () => electricalArcZap(rate, seededRandom(243))),
      loadRecorded("sfx_ep1_taxi_mud_splash_1", () => mudSprint(rate, seededRandom(255))),
      loadRecorded("sfx_ep1_taxi_mud_splash_2", () => mudSprint(rate, seededRandom(256))),
    ]);

    const rush = await oneShot(
      "taxi_ghost_rush",
      buffer(ghostRush(rate, seededRandom(224), -1, 1)),
      "threat",
      0.92,
    );
    const brake = await oneShot(
      "taxi_brake_slither",
      buffer(brakeSlither(rate, seededRandom(228))),
      "sfx",
      0.86,
    );
    const gasp = await spatialShot(
      "taxi_driver_gasp",
      buffer(driverGasp(rate, seededRandom(229))),
      "voice",
      new Vector3(-0.48, 1.06, -0.02),
      0.55,
      5,
    );
    const soraGasp1 = await oneShot("taxi_sora_gasp_1", soraGasp1Buf, "voice", 0.56);
    const soraGasp2 = await oneShot("taxi_sora_gasp_2", soraGasp2Buf, "voice", 0.62);

    // Layered real steel-door/glass slam + physical sub-pressure punch on Sora's right window!
    const slapReal = await spatialShot(
      "taxi_window_slam_real",
      slamRecBuf,
      "threat",
      new Vector3(0.86, 1.12, 0.04),
      0.42,
      10,
    );
    const slapSub = await spatialShot(
      "taxi_window_slap_sub",
      buffer(windowSlap(rate, seededRandom(230))),
      "threat",
      new Vector3(0.86, 1.14, 0.05),
      0.42,
      8,
    );
    // Wet fingernail drag down Sora's right glass in blackout silence!
    const glassScrape = await spatialShot(
      "taxi_glass_nail_scrape",
      scrapeRecBuf,
      "threat",
      new Vector3(0.82, 1.1, 0.02),
      0.35,
      6,
    );
    const glassScrapeSynth = await spatialShot(
      "taxi_glass_nail_scrape_synth",
      buffer(glassNailScrape(rate, seededRandom(251))),
      "threat",
      new Vector3(0.82, 1.1, 0.02),
      0.35,
      6,
    );

    const snap = await spatialShot(
      "taxi_branch_snap",
      branchRecBuf,
      "threat",
      new Vector3(2.9, 1.0, 1.1),
      1.0,
      18,
    );
    const arcZap = await spatialShot(
      "taxi_electrical_arc",
      buffer(electricalArcZap(rate, seededRandom(243))),
      "sfx",
      new Vector3(0, 0.72, 0.55),
      0.35,
      4,
    );
    const elecFlicker = await spatialShot(
      "taxi_elec_flicker_real",
      elecRecBuf,
      "sfx",
      new Vector3(0.02, 1.18, 0.04),
      0.45,
      5,
    );
    const seatCreak = await spatialShot(
      "taxi_back_seat_creak",
      seatCreakRecBuf,
      "threat",
      new Vector3(0.18, 0.72, -0.78),
      0.32,
      4.5,
    );
    const seatCreakSynth = await spatialShot(
      "taxi_back_seat_creak_synth",
      buffer(seatSpringCreak(rate, seededRandom(254))),
      "threat",
      new Vector3(0.18, 0.72, -0.78),
      0.32,
      4.5,
    );
    const screechFront = await spatialShot(
      "taxi_screech_front",
      buffer(ghostScreechSting(rate, seededRandom(244))),
      "threat",
      new Vector3(0.15, 1.05, 1.9),
      0.9,
      16,
    );
    const screechSide = await spatialShot(
      "taxi_screech_side",
      buffer(ghostScreechSting(rate, seededRandom(245))),
      "threat",
      new Vector3(0.88, 1.12, 0.05),
      0.45,
      12,
    );
    const screechRear = await spatialShot(
      "taxi_screech_rear",
      buffer(ghostScreechSting(rate, seededRandom(246))),
      "threat",
      new Vector3(0.24, 1.12, -0.35),
      0.35,
      8,
    );
    // Ultra-close 22 cm binaural behind-ear breath (real close-mic recording + icy synth whisper layer)
    const neckBreathReal = await spatialShot(
      "taxi_neck_breath_real",
      neckRecBuf,
      "threat",
      new Vector3(0.24, 1.1, -0.26),
      0.2,
      3.2,
    );
    const neckBreathSynth = await spatialShot(
      "taxi_neck_breath_synth",
      buffer(neckBreathWhisper(rate, seededRandom(247))),
      "threat",
      new Vector3(0.22, 1.12, -0.3),
      0.22,
      3.5,
    );
    const breathSeated = await spatialShot(
      "taxi_back_seat_breath",
      buffer(breathOut(rate, seededRandom(232))),
      "threat",
      new Vector3(0.28, 1.14, -0.82),
      0.3,
      4,
    );
    const whisper1 = await spatialShot(
      "taxi_whisper_rear_1",
      wh1Buf,
      "threat",
      new Vector3(0.26, 1.16, -0.52),
      0.26,
      3.5,
    );
    const whisper2 = await spatialShot(
      "taxi_whisper_rear_2",
      wh2Buf,
      "threat",
      new Vector3(0.22, 1.14, -0.36),
      0.24,
      3.2,
    );
    const whisper3 = await spatialShot(
      "taxi_whisper_window",
      wh3Buf,
      "threat",
      new Vector3(0.76, 1.12, 0.02),
      0.34,
      4.5,
    );
    const splashLeft = await spatialShot(
      "taxi_mud_splash_l",
      splash1Buf,
      "sfx",
      new Vector3(-0.75, 0.25, 0.9),
      0.7,
      8,
    );
    const splashRight = await spatialShot(
      "taxi_mud_splash_r",
      splash2Buf,
      "sfx",
      new Vector3(0.78, 0.25, 0.85),
      0.7,
      8,
    );
    // Non-repeating thunder pool (3 distinct real recordings + supersonic close crack!)
    const thunderPool = [
      await oneShot("taxi_thunder_real_1", th1Buf, "threat", 0.72),
      await oneShot("taxi_thunder_real_2", th2Buf, "threat", 0.76),
      await oneShot("taxi_thunder_real_3", th3Buf, "threat", 0.78),
    ];
    let thunderIdx = 0;
    const playThunder =
      (vol: number, closeCrack = false) =>
      () => {
        const s = thunderPool[thunderIdx % thunderPool.length];
        thunderIdx++;
        s.volume = vol;
        s.playbackRate = 0.95 + (thunderIdx % 3) * 0.04;
        s.play();
        if (closeCrack) {
          crack.volume = Math.min(1, vol * 0.85);
          crack.play();
        }
      };
    const crack = await oneShot(
      "taxi_thunder_crack",
      buffer(thunderCrack(rate, seededRandom(248))),
      "threat",
      0.85,
    );

    const playAt =
      (sound: StaticSound, vol: number, rateScale = 1) =>
      () => {
        sound.volume = vol;
        sound.playbackRate = rateScale;
        sound.play();
      };

    // Early distant monsoon storm rumbles & real flooded-rut wheel-arch splashes
    this.cues.push({ at: 5.4, play: playAt(splashRight, 0.32, 0.94) });
    this.cues.push({ at: 9.75, play: playThunder(0.42, false) });
    this.cues.push({ at: 14.0, play: playThunder(0.58, false) });
    this.cues.push({ at: 16.8, play: playAt(splashLeft, 0.36, 1.02) });

    // BEAT 1 (17.4..24.0 s): Verge watcher — dread swell, then splintering branch snap + double lightning crack!
    this.cues.push({ at: TAXI_STANDER.level - 1.3, play: () => this.score.sting("swell", 0.56) });
    this.cues.push({ at: TAXI_STANDER.snapAt - 0.03, play: playAt(snap, 0.88) });
    this.cues.push({ at: TAXI_STANDER.snapAt + 0.03, play: playThunder(0.66, true) });
    // Subtle eerie splash/scrape off right rear fender right as cab passes where she stood
    this.cues.push({ at: 23.65, play: playAt(splashRight, 0.44, 0.82) });

    // MICRO-DREAD BEAT (~30.2 s): Subtle distant jungle presence & back-cabin chill bridging Beat 1 -> Beat 2
    this.cues.push({ at: 29.8, play: playAt(splashLeft, 0.32, 0.88) });
    this.cues.push({ at: 30.35, play: playAt(whisper1, 0.36, 0.92) });
    this.cues.push({ at: 32.8, play: playAt(elecFlicker, 0.34, 1.04) });

    // BEAT 2 (37.05..38.03 s, beat 37.78 s): Relay sputter -> suffocating silence -> blistering Doppler sprint!
    const cross = taxiPass("crossing"),
      overtake = taxiPass("overtake");
    const crossBeat = taxiPassBeat(cross);
    this.cues.push({ at: crossBeat - 1.05, play: playAt(arcZap, 0.68) });
    this.cues.push({ at: crossBeat - 1.02, play: playAt(elecFlicker, 0.62) });
    this.cues.push({ at: crossBeat - 0.6, play: playAt(rush, 0.94) });
    this.cues.push({
      at: crossBeat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.98),
    });
    this.cues.push({ at: crossBeat - 0.02, play: playAt(screechFront, 0.72) });
    this.cues.push({ at: crossBeat + 0.01, play: playThunder(0.92, true) });
    this.cues.push({ at: crossBeat + 0.07, play: playAt(brake, 0.9) });
    this.cues.push({ at: crossBeat + 0.14, play: playAt(gasp, 0.95) });
    this.cues.push({ at: crossBeat + 0.24, play: playAt(splashRight, 0.56, 0.9) });
    this.cues.push({ at: crossBeat + 0.44, play: () => this.score.ring() });

    // BEAT 3 (46.0..49.2 s seated -> 52.02..54.15 s snap-lunge):
    // Mirror presence -> back-seat leather/spring weight shift -> 22 cm behind-ear breath (leads visual!) -> lunge!
    const { seated, lean } = TAXI_MIRROR;
    this.cues.push({ at: seated.from + 0.22, play: () => this.score.sting("swell", 0.56) });
    this.cues.push({ at: seated.from + 0.52, play: playAt(breathSeated, 0.66) });
    this.cues.push({ at: seated.from + 1.15, play: playAt(whisper1, 0.44, 0.96) });
    // Pure Shutter / P.T. chill: heavy back-seat spring creak right behind Sora BEFORE the lunge!
    this.cues.push({ at: lean.from - 0.42, play: playAt(seatCreak, 0.78) });
    this.cues.push({ at: lean.from - 0.38, play: playAt(seatCreakSynth, 0.42) });
    this.cues.push({ at: lean.beat - 0.32, play: playAt(arcZap, 0.68) });
    this.cues.push({ at: lean.beat - 0.3, play: playAt(elecFlicker, 0.58) });
    // Audio leads visual by 0.22 s: icy wet breath 22 cm behind Sora's right ear!
    this.cues.push({ at: lean.from - 0.02, play: playAt(neckBreathReal, 0.96) });
    this.cues.push({ at: lean.from, play: playAt(neckBreathSynth, 0.58) });
    this.cues.push({ at: lean.from + 0.06, play: playAt(whisper2, 0.66) });
    this.cues.push({
      at: lean.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.98),
    });
    this.cues.push({ at: lean.beat - 0.02, play: playAt(screechRear, 0.72) });
    this.cues.push({ at: lean.beat + 0.02, play: playThunder(0.86, true) });
    this.cues.push({ at: lean.beat + 0.24, play: playAt(soraGasp1, 0.54) });
    this.cues.push({ at: lean.beat + 0.36, play: () => this.score.ring() });
    this.cues.push({ at: lean.to - 0.12, play: () => whisper2.stop() });

    // BEAT 4a (57.30..57.88 s): Precursor crack -> real-time HRTF mud sprint -> violent right-glass SLAM #1!
    this.cues.push({ at: 55.64, play: playThunder(0.68, true) });
    this.cues.push({ at: overtake.start - 0.22, play: () => this.sprint?.play() });
    const slapBeat = taxiPassBeat(overtake);
    this.cues.push({
      at: slapBeat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.9),
    });
    this.cues.push({ at: slapBeat - 0.015, play: playAt(slapReal, 1.0) });
    this.cues.push({ at: slapBeat - 0.005, play: playAt(slapSub, 0.78) });
    this.cues.push({ at: slapBeat + 0.01, play: playAt(screechSide, 0.62) });

    // BLACKOUT SUSPENSE (58.85..60.2 s): Pitch-dark cab -> wet fingernails dragging slowly across Sora's glass!
    this.cues.push({ at: 58.88, play: playAt(glassScrape, 0.72) });
    this.cues.push({ at: 58.92, play: playAt(glassScrapeSynth, 0.44) });
    this.cues.push({ at: 59.35, play: playAt(whisper3, 0.56, 0.94) });

    // BEAT 4b (60.16..60.96 s, beat 60.56 s): Total blackout -> deepest vacuum -> PEAK eye-level glass impact!
    this.cues.push({ at: TAXI_WINDOW.beat - 0.88, play: playAt(arcZap, 0.78) });
    this.cues.push({ at: TAXI_WINDOW.beat - 0.85, play: playAt(elecFlicker, 0.68) });
    this.cues.push({
      at: TAXI_WINDOW.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 1.0),
    });
    this.cues.push({ at: TAXI_WINDOW.beat - 0.02, play: playAt(screechSide, 0.92) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.005, play: playThunder(1.0, true) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.02, play: playAt(slapReal, 0.88, 0.92) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.04, play: playAt(slapSub, 0.72) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.14, play: playAt(gasp, 0.95) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.24, play: playAt(soraGasp2, 0.6) });
    this.cues.push({ at: TAXI_WINDOW.beat + 0.4, play: () => this.score.ring() });

    // BEAT 5 (65.45..65.72 s, beat 65.56 s): False calm during braking -> sudden zap -> unexpected BONNET flash!
    this.cues.push({ at: TAXI_BONNET.start - 0.16, play: playAt(arcZap, 0.76) });
    this.cues.push({ at: TAXI_BONNET.start - 0.14, play: playAt(elecFlicker, 0.64) });
    this.cues.push({
      at: TAXI_BONNET.beat - this.score.lead("shock"),
      play: () => this.score.sting("shock", 0.96),
    });
    this.cues.push({ at: TAXI_BONNET.beat - 0.02, play: playAt(screechFront, 0.9) });
    this.cues.push({ at: TAXI_BONNET.beat + 0.01, play: playThunder(0.94, true) });
    this.cues.push({ at: TAXI_BONNET.beat + 0.06, play: playAt(brake, 0.84) });
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
    const forestGain = levels.forest * (1 - vacuum * 0.96);
    this.forest.forEach((sound, i) => (sound.volume = forestGain * [0.42, 0.3][i]));

    // Radio swells sharply with paranormal proximity, sputtering slightly in total silence vacuum
    if (this.radio) this.radio.volume = levels.radio * 0.56 * (1 - vacuum * 0.32);

    // Clockwork taximeter ticks eerily clear even when rain & engine drop into dead air
    if (this.meter) this.meter.volume = 0.44 * (1 - vacuum * 0.38);

    // Dynamically accelerating heartbeat: 54 BPM resting → 108 BPM pounding panic in vacuums!
    if (this.heartbeat) {
      this.heartbeat.volume = anxiety > 0.04 ? Math.min(0.84, anxiety * 0.62 + vacuum * 0.4) : 0;
      this.heartbeat.playbackRate = 0.9 + anxiety * 0.9;
    }

    // Infrasonic tension drone fills the suffocating silence vacuum right before each hit!
    if (this.subDrone) {
      this.subDrone.volume = Math.min(0.68, anxiety * 0.24 + vacuum * 0.58);
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
