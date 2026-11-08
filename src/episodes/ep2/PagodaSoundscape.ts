import type { AbstractSound } from "@babylonjs/core/AudioV2/abstractAudio/abstractSound";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { SoundState } from "@babylonjs/core/AudioV2/soundState";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
import { modal, normalise, noise, seededRandom, rattlingBreath } from "@/audio/synth";
import { dawnBirds, breathOut } from "@/audio/sounds/nightSounds";
import { foliageMovement } from "@/audio/sounds/atmosphereSounds";
import { DreadScore } from "@/audio/DreadScore";
import { harvestMusic } from "./cinematics/harvestMusic";
import {
  distantSob,
  ghostScream,
  ghostWhisper,
  heartbeat as heartbeatLoop,
  monkChant,
  stoneGrind,
  kuntilanakLaugh,
  boneCrack,
  vanishBreath,
  pocongThud,
  pocongGroan,
  stepsBehind,
  woodKnocks,
} from "./audio/pagodaHorror";
import { ShotBank } from "./audio/ShotBank";
import { PagodaNight } from "./audio/PagodaNight";
import { SMOT, hasRecording, soundUrls } from "./audio/recordings";
import {
  DISTANCES,
  GAPS,
  approach,
  around,
  behind as behindPoint,
  between,
  breathVoices,
  heartbeat,
  pitchJitter,
} from "./audio/pagodaMix";

/** Where the player is, as the horror layer needs it. */
export interface HorrorListener {
  x: number;
  z: number;
  /** Camera heading, radians: sounds are placed behind and beside it. */
  yaw: number;
  stage: string;
  safe: boolean;
  inHall: boolean;
  fear: number;
  moving: boolean;
}

/** The hall altar, runtime coordinates (X east, Z south). */
const ALTAR = new Vector3(22, 1.6, -5.5);
/** The bell rack in its pavilion: bell 0 is the smallest, 2 the largest. */
const BELL_AT = (i: number) => new Vector3(18.4 + i, 2, 9);
/** The recitation's level at the hall door: heard across the yard, under the night. */
const CHANT_LEVEL = 0.35;
/** The Pret's breathing, each from its own body. */
const BREATH_LEVEL = 0.16;
/** Seconds for a Pret's breath to fade in or out (a pause, a reader, a save). */
const BREATH_FADE = 0.6;

/**
 * Episode 2's sound. The night itself is recorded (audio/PagodaNight: insects,
 * frogs, the pond, the wind and the far calls; bells, knocks, splintering
 * timber and the bowl from audio/ShotBank); the monks' recitation is the real
 * smot heard in Episode 1. The horror layer stays original synthesis: whispers
 * well away behind the player, bare steps that follow, a heartbeat only with a
 * Pret close, a sob far off in the trees, the apparition's voice and body, the
 * corpses' feet and groans. Every repeat is another take a little off pitch,
 * at an uneven gap; everything fades in and out rather than snapping.
 */
export class PagodaSoundscape {
  private chant: AbstractSound | null = null;
  private heart: StaticSound | null = null;
  private readonly whispers: StaticSound[] = [];
  private sob: StaticSound | null = null;
  private knock: StaticSound | null = null;
  private steps: StaticSound | null = null;
  private readonly followSteps: StaticSound[] = [];
  private scream: StaticSound | null = null;
  private grindSound: StaticSound | null = null;
  private laughSound: StaticSound | null = null;
  private crackSound: StaticSound | null = null;
  private vanishSound: StaticSound | null = null;
  /** One thud and one groan per corpse, so their footfalls overlap naturally. */
  private readonly thuds: StaticSound[] = [];
  private readonly groans: StaticSound[] = [];
  private chantLevel = 0;
  private chantMax = CHANT_LEVEL;
  private hushed = 0;
  private stillFor = 0;
  private nextWhisper = 45;
  private nextFar = 50;
  private nextKnock = 110;
  private nextSteps = 40;
  private nextSnap = 6;
  private lastCrack = -10;
  private readonly rand = seededRandom(Math.floor(Math.random() * 1e9));
  private readonly breaths: StaticSound[] = [];
  private readonly breathLevels: number[] = [];
  private readonly fallbackBells: StaticSound[] = [];
  private bowl: StaticSound | null = null;
  private birds: StaticSound | null = null;
  private birdsLevel = 0;
  private harvest: StaticSound | null = null;
  private gaspSound: StaticSound | null = null;
  private score = new DreadScore(null);
  private memoryMode: "hidden" | "harvest" | "famine" = "hidden";
  private mutedCinematic = false;
  private readonly shots = new ShotBank(this.rand);
  private readonly night: PagodaNight;
  /** The Pret this frame (from `update`) and whether they are hunting. */
  private pret: readonly { x: number; z: number }[] = [];
  private pretActive = false;
  private heartLevel = 0;
  private heartRate = 1;
  private listener: HorrorListener | null = null;
  private time = 0;
  private dawned = false;

  constructor(private readonly game: Game) {
    this.night = new PagodaNight(game, this.shots, this.rand);
    game.scene.onDisposeObservable.addOnce(() => {
      this.night.stop();
      this.shots.stop();
      for (const sound of [
        ...this.breaths,
        ...this.fallbackBells,
        this.harvest,
        this.birds,
        this.bowl,
        this.gaspSound,
        this.chant,
        this.heart,
        ...this.whispers,
        this.sob,
        this.knock,
        this.steps,
        ...this.followSteps,
        this.scream,
        this.grindSound,
        this.laughSound,
        this.crackSound,
        this.vanishSound,
        ...this.thuds,
        ...this.groans,
      ])
        sound?.stop();
      this.score.stop();
    });
  }

  async load(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const spatial = async (
      name: string,
      samples: Float32Array,
      at: Vector3,
      volume: number,
      bus: "ambience" | "sfx" | "threat" = "threat",
      minDistance = 2,
      maxDistance = 40,
    ) =>
      audio.spatialSound("ep2_" + name, audio.buffer(samples, rate), bus, at, {
        volume,
        minDistance,
        maxDistance,
      });
    await this.shots.load(audio);
    await this.night.load();
    if (!this.shots.has("bells"))
      for (let i = 0; i < 3; i++)
        this.fallbackBells.push(
          await spatial("bell_" + i, synthBell(rate, i), BELL_AT(i), 0.5, "sfx", 4, 60),
        );
    if (!this.shots.has("clay"))
      this.bowl = await spatial(
        "bowl",
        foliageMovement(rate, seededRandom(205)),
        Vector3.Zero(),
        0.65,
        "sfx",
      );
    // Each Pret breathes at its own pace from its own point in the loop.
    const breaths = [0, 1, 2, 3, 4].map((i) => rattlingBreath(rate, seededRandom(210 + i)));
    const voices = breathVoices(breaths.length, breaths[0].length / rate, this.rand);
    for (const [i, samples] of breaths.entries()) {
      const sound = await spatial("pret_" + i, samples, Vector3.Zero(), 0, "threat", 2.5, 30);
      sound.loop = true;
      sound.playbackRate = voices[i].rate;
      sound.play({ startOffset: voices[i].offset });
      this.breaths.push(sound);
      this.breathLevels.push(0);
    }
    this.birds = await spatial(
      "birds",
      dawnBirds(rate, seededRandom(230)),
      new Vector3(-20, 5, 0),
      0,
      "ambience",
      6,
      60,
    );
    this.birds.loop = true;
    this.gaspSound = await audio.sound(
      "ep2_player_gasp",
      audio.buffer(breathOut(rate, seededRandom(231)), rate),
      "sfx",
      0.4,
    );
    this.harvest = await audio.sound(
      "ep2_harvest_instrumental",
      audio.buffer(harvestMusic(24000), 24000),
      "music",
      0,
    );
    this.harvest.loop = true;
    this.score = new DreadScore(audio);
    await this.score.load();
    // The monks' recitation from the hall: the recording if there, else a quiet stand-in.
    const smot = soundUrls(SMOT);
    const options = { loop: true, minDistance: 10, maxDistance: 120, volume: 0 };
    if (await hasRecording(smot)) {
      this.chant = await audio.spatialStream("ep2_smot", smot, "ambience", ALTAR, options);
    } else {
      this.chant = await spatial(
        "chant",
        monkChant(rate, seededRandom(240)),
        ALTAR,
        0,
        "ambience",
        10,
        120,
      );
      (this.chant as StaticSound).loop = true;
      this.chantMax = 0.25;
    }
    this.chant.play();
    this.heart = await audio.sound(
      "ep2_heartbeat",
      audio.buffer(heartbeatLoop(rate), rate),
      "threat",
      0,
    );
    this.heart.loop = true;
    this.heart.play();
    for (let i = 0; i < 3; i++)
      this.whispers.push(
        await spatial(
          "whisper_" + i,
          ghostWhisper(rate, seededRandom(250 + i)),
          Vector3.Zero(),
          0.55,
          "threat",
          1.5,
          30,
        ),
      );
    this.sob = await spatial(
      "sob",
      distantSob(rate, seededRandom(262)),
      Vector3.Zero(),
      0.6,
      "ambience",
      3,
      120,
    );
    if (!this.shots.has("knock"))
      this.knock = await spatial(
        "knock",
        woodKnocks(rate, seededRandom(263)),
        Vector3.Zero(),
        0.4,
        "sfx",
        1.5,
        25,
      );
    // Bare steps that follow: Sora's own leaf takes (Kenney, CC0), else the stand-in.
    const leaves = this.game.footsteps?.buffers.get("leaves") ?? [];
    for (const [k, buffer] of leaves.entries())
      this.followSteps.push(
        await audio.spatialSound("ep2_follow_step_" + k, buffer, "threat", Vector3.Zero(), {
          minDistance: 1.5,
          maxDistance: 25,
        }),
      );
    if (!this.followSteps.length)
      this.steps = await spatial(
        "steps",
        stepsBehind(rate, seededRandom(264)),
        Vector3.Zero(),
        0.4,
        "threat",
        1.5,
        25,
      );
    // The apparition's voice and body, placed where she is.
    this.laughSound = await spatial(
      "kunti_laugh",
      kuntilanakLaugh(rate, seededRandom(267)),
      Vector3.Zero(),
      0.75,
      "threat",
      5,
      60,
    );
    this.crackSound = await spatial(
      "bone_crack",
      boneCrack(rate, seededRandom(268)),
      Vector3.Zero(),
      0.55,
      "sfx",
      2.5,
      30,
    );
    this.vanishSound = await spatial(
      "vanish",
      vanishBreath(rate, seededRandom(269)),
      Vector3.Zero(),
      0.65,
      "threat",
      3,
      30,
    );
    for (let i = 0; i < 5; i++) {
      this.thuds.push(
        await spatial(
          "pocong_thud_" + i,
          pocongThud(rate, seededRandom(270 + i)),
          Vector3.Zero(),
          0.5,
          "sfx",
          3,
          32,
        ),
      );
      if (i < 2)
        this.groans.push(
          await spatial(
            "pocong_groan_" + i,
            pocongGroan(rate, seededRandom(280 + i)),
            Vector3.Zero(),
            0.5,
            "threat",
            3.5,
            30,
          ),
        );
    }
    this.grindSound = await spatial(
      "stone_grind",
      stoneGrind(rate, seededRandom(266)),
      Vector3.Zero(),
      0.6,
      "sfx",
      5,
      45,
    );
    this.scream = await audio.sound(
      "ep2_apparition_scream",
      audio.buffer(ghostScream(rate, seededRandom(265)), rate),
      "threat",
      0.5,
    );
  }

  /** A point `distance` metres from the listener, `angle` radians off straight behind. */
  private around(l: HorrorListener, distance: number, angle: number, y = 1.6): Vector3 {
    const p = behindPoint(l.x, l.z, l.yaw, distance, angle);
    return new Vector3(p.x, y, p.z);
  }

  /** The horror layer and the night, every frame. Quiet in cinematics and memories. */
  haunt(dt: number, l: HorrorListener, enabled: boolean): void {
    this.listener = l;
    const shown = this.memoryMode === "hidden" && !this.mutedCinematic;
    const live = enabled && shown;
    const ended = this.dawned || l.stage === "dawn" || l.stage === "complete";
    const nearest = this.nearestPret(l);
    this.night.update(dt, l, nearest, !shown);

    // The recitation carries on through readers and saves; it falls away only when Sora
    // steps into the hall (and returns a while after she leaves), and in memories.
    const chantStage = ["arrival", "garden", "library"].includes(l.stage);
    this.hushed = l.inHall ? 6 : Math.max(0, this.hushed - dt);
    const chantTarget = shown && chantStage && !ended && this.hushed === 0 ? this.chantMax : 0;
    this.chantLevel = approach(
      this.chantLevel,
      chantTarget,
      dt,
      chantTarget < this.chantLevel ? 0.9 : 3,
    );
    if (this.chant) this.chant.volume = this.chantLevel * (enabled ? 1 : 0.8);

    // The heart only beats in the ears with a Pret within about eight metres.
    const beat = heartbeat(live && this.pretActive && !ended ? nearest : 99);
    this.heartLevel = approach(
      this.heartLevel,
      beat.level,
      dt,
      beat.level > this.heartLevel ? 0.8 : 1.6,
    );
    this.heartRate = approach(this.heartRate, beat.rate, dt, 1.5);
    if (this.heart) {
      this.heart.volume = this.heartLevel;
      this.heart.playbackRate = this.heartRate;
    }
    if (this.birds) {
      this.birdsLevel = approach(this.birdsLevel, this.dawned ? 0.14 : 0, dt, 2.5);
      this.birds.volume = this.birdsLevel;
    }
    if (!live || ended) return;

    this.stillFor = l.moving ? 0 : this.stillFor + dt;
    // The kuti is safe: nothing counts down inside it, and it gives a breath after.
    if (l.safe) {
      this.nextWhisper = Math.max(this.nextWhisper, 20 + this.rand() * 20);
      this.nextSteps = Math.max(this.nextSteps, 20);
    } else {
      this.nextWhisper -= dt;
      this.nextSteps -= dt;
    }
    this.nextFar -= dt;
    this.nextKnock -= dt;
    if (this.nextWhisper <= 0) {
      this.nextWhisper = between(GAPS.whisper, this.rand);
      const w = this.whispers[Math.floor(this.rand() * this.whispers.length)];
      if (w) {
        w.spatial.position = this.around(
          l,
          between(DISTANCES.whisper, this.rand),
          (this.rand() - 0.5) * 2,
        );
        w.playbackRate = pitchJitter(this.rand, 0.06);
        w.play();
      }
    }
    if (this.stillFor > 6 && this.nextSteps <= 0) {
      this.nextSteps = between(GAPS.steps, this.rand);
      this.stillFor = 0;
      this.follow(
        this.around(l, between(DISTANCES.steps, this.rand), (this.rand() - 0.5) * 0.8, 0.1),
        l,
      );
    }
    if (this.nextFar <= 0 && this.sob) {
      this.nextFar = between(GAPS.far, this.rand);
      const p = around(l.x, l.z, between(DISTANCES.far, this.rand), this.rand);
      this.sob.spatial.position = new Vector3(p.x, 1.5, p.z);
      this.sob.playbackRate = pitchJitter(this.rand, 0.04);
      this.sob.play();
    }
    if (this.nextKnock <= 0 && (l.safe || l.inHall)) {
      this.nextKnock = between(GAPS.knock, this.rand);
      const at = this.around(
        l,
        between(DISTANCES.knock, this.rand),
        (this.rand() - 0.5) * 2.4,
        1.3,
      );
      if (!this.shots.play("knock", at, 0.35)) this.at(this.knock, at, 0.4, 0.05);
    }
  }

  /** The nearest hunting Pret, metres (99 if none). */
  private nearestPret(l: { x: number; z: number }): number {
    if (!this.pretActive) return 99;
    let d = 99;
    for (const p of this.pret)
      if (p?.x !== undefined) d = Math.min(d, Math.hypot(p.x - l.x, p.z - l.z));
    return d;
  }

  /** Two to four bare steps closing in on `at`, each a different take. */
  private follow(at: Vector3, l: { x: number; z: number }): void {
    if (!this.followSteps.length) {
      this.at(this.steps, at, 0.4, 0.05);
      return;
    }
    const count = 2 + Math.floor(this.rand() * 3);
    let wait = 0;
    for (let k = 0; k < count; k++) {
      const step = this.followSteps[(k + Math.floor(this.rand() * 5)) % this.followSteps.length];
      // Each step a little nearer than the last.
      const u = (count - k) / count;
      step.spatial.position = new Vector3(
        l.x + (at.x - l.x) * (0.75 + 0.25 * u),
        0.1,
        l.z + (at.z - l.z) * (0.75 + 0.25 * u),
      );
      step.volume = 0.22 + 0.05 * k;
      step.playbackRate = pitchJitter(this.rand, 0.06);
      step.play({ waitTime: wait });
      wait += 0.55 + this.rand() * 0.2;
    }
  }

  /** Something just behind the player: bare steps and a whisper at `at`. */
  behind(at: Vector3): void {
    const l = this.listener ?? { x: at.x, z: at.z };
    this.follow(new Vector3(at.x, 0.1, at.z), l);
    const w = this.whispers[Math.floor(this.rand() * this.whispers.length)];
    if (w) {
      w.spatial.position = new Vector3(at.x, 1.6, at.z);
      w.playbackRate = pitchJitter(this.rand, 0.06);
      w.play();
    }
  }

  /** The kuntilanak's laugh from where she stands (or stood). */
  laugh(at: Vector3, volume = 1): void {
    this.at(this.laughSound, at, 0.75 * volume, 0.03);
  }

  /** Her neck snapping over (or a corpse's): never twice within two seconds. */
  crack(at: Vector3): void {
    if (this.time - this.lastCrack < 2) return;
    this.lastCrack = this.time;
    this.at(this.crackSound, at, 0.45 + this.rand() * 0.15, 0.07);
  }

  /** She is gone: a breath sucked in where she was, cut off dead. */
  vanish(at: Vector3): void {
    this.at(this.vanishSound, at, undefined, 0.04);
  }

  /** Corpse `i`'s foot coming down. */
  thud(i: number, at: Vector3, volume = 0.5): void {
    this.at(this.thuds[i % Math.max(1, this.thuds.length)], at, volume, 0.06);
  }

  /** Corpse `i` moaning under its cloth. */
  groan(i: number, at: Vector3): void {
    const g = this.groans[i % Math.max(1, this.groans.length)];
    if (g && g.state !== SoundState.Started) this.at(g, at, undefined, 0.04);
  }

  private at(sound: StaticSound | null | undefined, at: Vector3, volume?: number, pitch = 0): void {
    if (!sound) return;
    sound.spatial.position = at.clone();
    if (volume !== undefined) sound.volume = volume;
    sound.playbackRate = pitch > 0 ? pitchJitter(this.rand, pitch) : 1;
    sound.play();
  }

  /** A stone image has moved where the player could not see it. */
  grind(at: Vector3): void {
    this.at(this.grindSound, at, undefined, 0.05);
  }

  /** A glimpse, not a shock: the score rises and the ears start to ring. */
  unease(): void {
    this.score.sting("rise", 0.6);
  }

  /** The apparition's scream and the shock sting together; the master limiter holds the peak. */
  scare(volume = 1): void {
    if (this.scream) {
      this.scream.volume = 0.5 * volume;
      this.scream.playbackRate = pitchJitter(this.rand, 0.03);
      this.scream.play();
    }
    this.score.sting("shock", 0.5 * volume);
  }

  update(
    dt: number,
    positions: readonly { x: number; z: number }[],
    active: boolean,
    escape: boolean,
  ): void {
    this.time += dt;
    const hidden = this.memoryMode === "hidden" && !this.mutedCinematic;
    if (this.harvest)
      this.harvest.volume = this.memoryMode === "harvest" && !this.mutedCinematic ? 0.22 : 0;
    this.score.pressure(!hidden || this.dawned ? 0 : escape ? 0.45 : active ? 0.1 : 0);
    this.score.update(dt);
    this.pret = positions;
    this.pretActive = active && hidden && !this.dawned;
    // Each Pret's breath fades in and out over a moment, never snaps.
    this.breaths.forEach((sound, i) => {
      const p = positions[i];
      const target = this.pretActive && p?.x !== undefined ? BREATH_LEVEL : 0;
      this.breathLevels[i] = approach(this.breathLevels[i], target, dt, BREATH_FADE / 3);
      sound.volume = this.breathLevels[i];
      if (p) sound.spatial.position = new Vector3(p.x, 1.8, p.z);
    });
    // The library coming apart behind Sora: old timber splitting at uneven gaps.
    if (escape && hidden && !this.dawned) {
      this.nextSnap -= dt;
      if (this.nextSnap <= 0) {
        this.nextSnap = between(GAPS.escapeSnap, this.rand);
        const l = this.listener;
        const at = l
          ? this.around(l, 6 + this.rand() * 8, (this.rand() - 0.5) * 1.6, 1.2)
          : new Vector3(0, 2, -32);
        this.shots.play(this.rand() < 0.75 ? "splinter" : "creakTree", at, 0.5, { pitch: 0.07 });
      }
    }
  }

  ring(index: number): void {
    if (!this.shots.play("bells", BELL_AT(index), 0.65, { take: index, pitch: 0 }))
      this.fallbackBells[index]?.play();
  }

  /** The empty clay bowl shattering where it lands. */
  throw(at: Vector3): void {
    if (this.shots.play("clay", new Vector3(at.x, 0.1, at.z), 0.75, { pitch: 0.06 })) return;
    this.at(this.bowl, at);
  }

  gasp(_at: Vector3): void {
    this.gaspSound?.play();
  }

  memory(mode: "hidden" | "harvest" | "famine"): void {
    this.memoryMode = mode;
    if (mode === "harvest") this.harvest?.play();
    else this.harvest?.stop();
  }

  cinematicPause(paused: boolean): void {
    this.mutedCinematic = paused;
  }

  /** The library giving way. */
  crash(): void {
    const l = this.listener;
    const at = l ? this.around(l, 5, 0.3, 2) : new Vector3(0, 2, -32);
    this.shots.play("splinter", at, 0.8, { pitch: 0.05, rate: 0.85 });
    this.score.sting("shock", 0.45);
  }

  /** The largest bell, rung at four o'clock. */
  dawnBell(): void {
    this.ring(2);
  }

  /** Dawn: the night, the chant, the breathing and the heart drain away; birds come in. */
  dawn(): void {
    if (this.dawned) return;
    this.dawned = true;
    this.harvest?.stop();
    this.score.stop();
    this.night.dawn();
    this.birds?.play();
    setTimeout(() => {
      for (const s of [...this.breaths, this.chant, this.heart]) s?.stop();
    }, 6000);
  }
}

/** A bronze bell for when the recordings are missing (index 0 smallest, 2 largest). */
function synthBell(rate: number, index: number): Float32Array {
  const hit = noise(rate * 5, seededRandom(220 + index));
  for (let n = 0; n < hit.length; n++) hit[n] *= Math.exp(-n / (rate * 0.006));
  const fundamental = [520, 360, 220][index];
  return normalise(
    modal(hit, rate, [
      [fundamental, 2.8, 1],
      [fundamental * 2.76, 1.8, 0.6],
      [fundamental * 5.4, 1, 0.24],
    ]),
    0.7,
  );
}
