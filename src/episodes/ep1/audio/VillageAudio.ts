import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AudioSystem, BusName, SpatialOptions } from "@/audio/AudioSystem";
import { seededRandom } from "@/audio/synth";
import { heartbeat } from "./houseSounds";

export type VillageSfxKind =
  | "thunder"
  | "preaySob"
  | "preayRattle"
  | "preayNeckCrack"
  | "preayBreath"
  | "preayWhisper"
  | "preayClaw"
  | "preayStep"
  | "shockHit"
  | "stingerLow"
  | "krasueAlert"
  | "lockClick"
  | "lockOpen"
  | "gateOpen"
  | "wellCreak"
  | "wellSplash"
  | "wellTug"
  | "clockTick"
  | "clockChime"
  | "clockChimeLow"
  | "shrinePlace"
  | "knock"
  | "doorSlam"
  | "doorCreak"
  | "bulbFlicker"
  | "woodCreak"
  | "waterStir"
  | "soraGasp";

interface SoundPool {
  voices: StaticSound[];
  baseVolume: number;
  lastIndex: number;
}

interface PoolSpec {
  clips: readonly string[];
  bus: BusName;
  copies: number;
  options: SpatialOptions;
}

function ep1Urls(name: string): string[] {
  const base = `${import.meta.env.BASE_URL}assets/ep1/audio/${name}`;
  return [`${base}.ogg`, `${base}.m4a`];
}

export function ep2AudioUrls(name: string): string[] {
  const base = `${import.meta.env.BASE_URL}assets/ep2/audio/${name}`;
  return [`${base}.ogg`, `${base}.m4a`];
}

export function ep1AudioUrls(name: string): string[] {
  return ep1Urls(name);
}

const POOLS: Record<VillageSfxKind, PoolSpec> = {
  // Routed to "sfx" (never "ambience") so pre-scare sound-vacuum ducking never silences lightning thunder!
  thunder: {
    clips: ["sfx_ep1_taxi_thunder_1", "sfx_ep1_taxi_thunder_2", "sfx_ep1_taxi_thunder_3"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 36, maxDistance: 140, rolloffFactor: 0.7, volume: 0.92 },
  },
  preaySob: {
    clips: ["sfx_ep1_preay_sob_1", "sfx_ep1_preay_sob_2"],
    bus: "threat",
    copies: 1,
    options: {
      panning: "HRTF",
      minDistance: 4.5,
      maxDistance: 36,
      rolloffFactor: 0.9,
      volume: 0.92,
    },
  },
  preayRattle: {
    clips: ["sfx_ep1_preay_rattle"],
    bus: "threat",
    copies: 2,
    options: {
      panning: "HRTF",
      minDistance: 4.0,
      maxDistance: 32,
      rolloffFactor: 0.85,
      volume: 0.98,
    },
  },
  preayNeckCrack: {
    clips: ["sfx_ep1_preay_neck_1", "sfx_ep1_preay_neck_2"],
    bus: "threat",
    copies: 2,
    options: {
      panning: "HRTF",
      minDistance: 4.2,
      maxDistance: 30,
      rolloffFactor: 0.85,
      volume: 1.0,
    },
  },
  preayBreath: {
    clips: ["sfx_ep1_preay_breath_1", "sfx_ep1_preay_breath_2", "sfx_ep1_taxi_neck_breath"],
    bus: "threat",
    copies: 2,
    options: {
      panning: "HRTF",
      minDistance: 2.2,
      maxDistance: 22,
      rolloffFactor: 0.95,
      volume: 0.98,
    },
  },
  preayWhisper: {
    clips: [
      "sfx_ep1_preay_whisper_1",
      "sfx_ep1_preay_whisper_2",
      "sfx_ep1_taxi_whisper_1",
      "sfx_ep1_taxi_whisper_2",
    ],
    bus: "threat",
    copies: 2,
    options: {
      panning: "HRTF",
      minDistance: 2.8,
      maxDistance: 26,
      rolloffFactor: 0.9,
      volume: 0.96,
    },
  },
  preayClaw: {
    clips: ["sfx_ep1_preay_claw_1", "sfx_ep1_preay_claw_2"],
    bus: "threat",
    copies: 1,
    options: {
      panning: "HRTF",
      minDistance: 3.0,
      maxDistance: 26,
      rolloffFactor: 0.95,
      volume: 0.92,
    },
  },
  preayStep: {
    clips: [
      "sfx_ep1_preay_step_1",
      "sfx_ep1_preay_step_2",
      "sfx_ep1_taxi_mud_splash_1",
      "sfx_ep1_taxi_mud_splash_2",
    ],
    bus: "threat",
    copies: 2,
    options: {
      panning: "HRTF",
      minDistance: 2.8,
      maxDistance: 24,
      rolloffFactor: 0.95,
      volume: 0.96,
    },
  },
  shockHit: {
    clips: ["sfx_ep1_village_shock"],
    bus: "threat",
    copies: 2,
    options: { minDistance: 32, maxDistance: 120, rolloffFactor: 0.5, volume: 1.0 },
  },
  stingerLow: {
    clips: ["sfx_ep1_village_stinger_low"],
    bus: "threat",
    copies: 1,
    options: { minDistance: 28, maxDistance: 100, rolloffFactor: 0.5, volume: 0.84 },
  },
  krasueAlert: {
    clips: ["sfx_ep1_krasue_alert"],
    bus: "threat",
    copies: 1,
    options: {
      panning: "HRTF",
      minDistance: 10,
      maxDistance: 72,
      rolloffFactor: 0.85,
      volume: 0.94,
    },
  },
  lockClick: {
    clips: ["sfx_ep1_village_lock_click"],
    bus: "sfx",
    copies: 2,
    options: { minDistance: 2.0, maxDistance: 12, volume: 0.78 },
  },
  lockOpen: {
    clips: ["sfx_ep1_village_lock_open"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 2.5, maxDistance: 20, volume: 0.9 },
  },
  gateOpen: {
    clips: ["sfx_ep1_village_gate_open"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 3.0, maxDistance: 28, volume: 0.92 },
  },
  wellCreak: {
    clips: ["sfx_ep1_well_creak"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 2.4, maxDistance: 22, volume: 0.88 },
  },
  wellSplash: {
    clips: ["sfx_ep1_well_splash"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 2.6, maxDistance: 24, volume: 0.92 },
  },
  wellTug: {
    clips: ["sfx_ep1_well_tug"],
    bus: "threat",
    copies: 1,
    options: { panning: "HRTF", minDistance: 3.0, maxDistance: 26, volume: 0.98 },
  },
  clockTick: {
    clips: ["sfx_ep1_clock_tick"],
    bus: "sfx",
    copies: 2,
    options: { distanceModel: "linear", minDistance: 1.5, maxDistance: 12, volume: 0.48 },
  },
  clockChime: {
    clips: ["sfx_ep1_clock_chime"],
    bus: "sfx",
    copies: 2,
    options: { minDistance: 8, maxDistance: 64, volume: 0.74 },
  },
  clockChimeLow: {
    clips: ["sfx_ep1_clock_chime_low"],
    bus: "threat",
    copies: 2,
    options: { minDistance: 10, maxDistance: 72, volume: 0.86 },
  },
  shrinePlace: {
    clips: ["sfx_ep1_shrine_place"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 2.0, maxDistance: 14, volume: 0.8 },
  },
  knock: {
    clips: ["sfx_ep1_studio_knock_1", "sfx_ep1_studio_knock_2", "sfx_ep1_studio_knock_3"],
    bus: "threat",
    copies: 2,
    options: {
      panning: "HRTF",
      minDistance: 3.8,
      maxDistance: 28,
      rolloffFactor: 0.85,
      volume: 0.96,
    },
  },
  doorSlam: {
    clips: ["sfx_ep1_studio_door_slam"],
    bus: "threat",
    copies: 2,
    options: {
      panning: "HRTF",
      minDistance: 4.0,
      maxDistance: 34,
      rolloffFactor: 0.85,
      volume: 0.98,
    },
  },
  doorCreak: {
    clips: ["sfx_ep1_studio_door_creak_1", "sfx_ep1_studio_door_creak_2"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 2.5, maxDistance: 22, volume: 0.84 },
  },
  bulbFlicker: {
    clips: ["sfx_ep1_studio_bulb_flicker", "sfx_ep1_taxi_elec_flicker"],
    bus: "sfx",
    copies: 2,
    options: { minDistance: 3.0, maxDistance: 22, volume: 0.84 },
  },
  woodCreak: {
    clips: ["sfx_ep1_studio_creak_1", "sfx_ep1_studio_creak_2", "sfx_ep1_studio_creak_3"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 3.0, maxDistance: 22, volume: 0.78 },
  },
  waterStir: {
    clips: ["sfx_ep1_studio_water_stir"],
    bus: "sfx",
    copies: 1,
    options: { minDistance: 2.4, maxDistance: 20, volume: 0.88 },
  },
  soraGasp: {
    clips: ["sfx_ep1_taxi_sora_gasp_1", "sfx_ep1_taxi_sora_gasp_2"],
    bus: "voice",
    copies: 1,
    options: { minDistance: 2.5, maxDistance: 10, volume: 0.86 },
  },
};

/**
 * Cinema-grade Episode 1 Village horror sound bank:
 * - Immediate PannerNode position sync before playback (zero (0,0,0) frame lag)
 * - Calibrated HRTF minDistance & rolloff so distant whispers, sobs, and cracks cut cleanly
 * - Dedicated continuous spatial weeping loop + physiological dread heartbeat
 * - Listener-relative close-ear HRTF helper (`playNearEar`) for intimate behind-the-ear scares
 */
export class VillageAudio {
  private readonly pools = new Map<VillageSfxKind, SoundPool>();
  private readonly loops = new Map<string, StaticSound>();
  private weepingLoop: StaticSound | null = null;
  private weepingActive = false;
  private heartSound: StaticSound | null = null;
  private heartPlaying = false;
  private heartLevel = 0;
  private heartTarget = 0;
  private vacuumTimer = 0;
  private vacuumActive = false;

  constructor(private readonly audio: AudioSystem | null) {}

  async load(): Promise<void> {
    const audio = this.audio;
    if (!audio) return;
    await Promise.all([
      ...(Object.entries(POOLS) as [VillageSfxKind, PoolSpec][]).map(async ([kind, spec]) => {
        const buffers = (await Promise.all(spec.clips.map((c) => audio.load(ep1Urls(c))))).filter(
          (b): b is AudioBuffer => b !== null,
        );
        if (!buffers.length) return;
        const voices: StaticSound[] = [];
        for (let b = 0; b < buffers.length; b++) {
          for (let c = 0; c < spec.copies; c++) {
            voices.push(
              await audio.spatialSound(
                `village_${kind}_${b}_${c}`,
                buffers[b],
                spec.bus,
                Vector3.Zero(),
                spec.options,
              ),
            );
          }
        }
        this.pools.set(kind, {
          voices,
          baseVolume: spec.options.volume ?? 0.8,
          lastIndex: -1,
        });
      }),
      (async () => {
        const weepBuf = await audio.load(ep1Urls("amb_ep1_preay_weeping"));
        if (weepBuf) {
          this.weepingLoop = await audio.spatialSound(
            "village_preay_weeping_loop",
            weepBuf,
            "threat",
            Vector3.Zero(),
            {
              panning: "HRTF",
              loop: true,
              minDistance: 4.5,
              maxDistance: 36,
              rolloffFactor: 0.9,
              volume: 0.92,
            },
          );
        }
        const rate = audio.context.sampleRate;
        this.heartSound = await audio.sound(
          "village_sora_heartbeat",
          audio.buffer(heartbeat(rate, seededRandom(7731)), rate),
          "threat",
          0,
        );
        this.heartSound.loop = true;
      })(),
    ]);
  }

  /** Creates and registers a spatialized looping sound from a mastered ep1 clip. */
  async createSpatialLoop(
    id: string,
    clipName: string,
    position: Vector3,
    bus: BusName,
    options: SpatialOptions = {},
  ): Promise<StaticSound | null> {
    const audio = this.audio;
    if (!audio) return null;
    const buffer = await audio.load(ep1Urls(clipName));
    if (!buffer) return null;
    const sound = await audio.spatialSound(id, buffer, bus, position, {
      ...options,
      loop: true,
    });
    sound.spatial.update();
    this.loops.set(id, sound);
    return sound;
  }

  /** Plays a non-repeating spatial voice from `kind` at `position` with instant PannerNode sync. */
  play(
    kind: VillageSfxKind,
    position: Vector3,
    volumeScale = 1,
    rateScale = 1,
  ): StaticSound | null {
    const pool = this.pools.get(kind);
    if (!pool || !pool.voices.length) return null;
    const count = pool.voices.length;
    let idx = Math.floor(Math.random() * count);
    if (count > 1 && idx === pool.lastIndex) idx = (idx + 1) % count;
    pool.lastIndex = idx;
    const voice = pool.voices[idx];
    voice.spatial.position = position.clone();
    voice.spatial.update();
    voice.volume = Math.max(0, Math.min(1.25, pool.baseVolume * volumeScale));
    voice.playbackRate = Math.max(0.5, Math.min(1.6, rateScale * (0.97 + Math.random() * 0.06)));
    voice.play();
    return voice;
  }

  /**
   * Plays an intimate HRTF cue directly behind Sora's left (`side = -1`) or right (`side = +1`) ear.
   * Gives razor-sharp directional chills for whispers, cold breath, and blackout dart-past steps.
   */
  playNearEar(
    kind: VillageSfxKind,
    eye: Vector3,
    forward: Vector3,
    side: -1 | 1,
    distance = 0.65,
    volumeScale = 1,
    rateScale = 1,
  ): StaticSound | null {
    const fx = forward.x;
    const fz = forward.z;
    const fl = Math.hypot(fx, fz) || 1;
    const nx = fx / fl;
    const nz = fz / fl;
    // Right vector in Babylon left-handed space (+Y up, +Z forward -> +X right = (nz, 0, -nx))
    const rx = nz * side;
    const rz = -nx * side;
    const pos = new Vector3(
      eye.x + rx * distance - nx * distance * 0.55,
      eye.y - 0.04,
      eye.z + rz * distance - nz * distance * 0.55,
    );
    return this.play(kind, pos, volumeScale, rateScale);
  }

  /** Starts the continuous spatial weeping loop at `position` (cuts dead via `stopWeeping()`). */
  startWeeping(position: Vector3, volume = 0.92): void {
    const w = this.weepingLoop;
    if (!w) {
      this.play("preaySob", position, volume);
      return;
    }
    w.spatial.position = position.clone();
    w.spatial.update();
    w.volume = volume;
    if (!this.weepingActive) {
      w.play();
      this.weepingActive = true;
    }
  }

  /** Cuts Preay's weeping STONE DEAD mid-breath for maximum Asian-horror silence shock. */
  stopWeeping(): void {
    if (this.weepingLoop && this.weepingActive) {
      this.weepingLoop.stop();
      this.weepingActive = false;
    }
    this.stopKind("preaySob");
  }

  /** Sets Sora's physiological dread heartbeat pressure (0 calm -> 1 pounding panic). */
  setHeartbeat(intensity: number): void {
    this.heartTarget = Math.max(0, Math.min(1, intensity));
  }

  /** Stops all active voices of a given pool. */
  stopKind(kind: VillageSfxKind): void {
    const pool = this.pools.get(kind);
    if (!pool) return;
    for (const voice of pool.voices) voice.stop();
  }

  /**
   * Triggers an Asian-horror sound vacuum (rain, frogs, insects drop into eerie stillness
   * right before an apparition reveals itself; thunder & threat audio cut straight through).
   */
  triggerVacuum(durationSeconds: number, duckTo = 0.08): void {
    this.vacuumTimer = Math.max(this.vacuumTimer, durationSeconds);
    if (!this.vacuumActive) {
      this.vacuumActive = true;
      this.audio?.duckAmbience(duckTo, 0.32);
    }
  }

  update(dt: number): void {
    if (this.vacuumActive) {
      this.vacuumTimer -= dt;
      if (this.vacuumTimer <= 0) {
        this.vacuumActive = false;
        this.vacuumTimer = 0;
        this.audio?.duckAmbience(1, 0.95);
      }
    }

    // Smooth physiological heartbeat intensity & BPM ramp with dread
    if (this.heartSound) {
      const rate = this.heartTarget > this.heartLevel ? 3.2 : 1.1;
      this.heartLevel += (this.heartTarget - this.heartLevel) * Math.min(1, dt * rate);
      if (this.heartLevel > 0.04) {
        if (!this.heartPlaying) {
          this.heartSound.play();
          this.heartPlaying = true;
        }
        this.heartSound.volume = this.heartLevel * 0.42;
        this.heartSound.playbackRate = 0.88 + this.heartLevel * 0.56;
      } else if (this.heartPlaying) {
        this.heartSound.stop();
        this.heartPlaying = false;
      }
    }
  }

  /** Current 0–1 silence factor for ambient wildlife & wind listeners. */
  get silence(): number {
    return this.vacuumActive ? 0.92 : 0;
  }

  stopAll(): void {
    this.vacuumActive = false;
    this.vacuumTimer = 0;
    this.heartTarget = 0;
    this.heartLevel = 0;
    if (this.heartPlaying) {
      this.heartSound?.stop();
      this.heartPlaying = false;
    }
    this.stopWeeping();
    this.audio?.duckAmbience(1, 0.3);
    for (const pool of this.pools.values()) for (const v of pool.voices) v.stop();
    for (const loop of this.loops.values()) loop.stop();
  }
}
