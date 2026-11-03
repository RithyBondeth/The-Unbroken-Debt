import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../core/Game";
import {
  modal,
  normalise,
  noise,
  seededRandom,
  rattlingBreath,
  boardCreak,
} from "../../audio/synth";
import { frogsLoop, cricketsLoop, dawnBirds } from "../ep1/audio/nightSounds";
import { canopyWind, foliageMovement } from "../ep1/audio/atmosphereSounds";
import { spiritShriek } from "../ep1/audio/actThreeSounds";
import { breathOut } from "../ep1/audio/nightSounds";
import { DreadScore } from "../ep1/audio/DreadScore";
import { harvestMusic } from "./cinematics/harvestMusic";
import {
  distantSob,
  ghostScream,
  ghostWhisper,
  heartbeat,
  monkChant,
  stoneGrind,
  stepsBehind,
  templeDrum,
  templeGong,
  woodKnocks,
} from "./audio/pagodaHorror";

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

/**
 * Original synthesis in the same audio space as Episode 1. The horror layer adds the
 * monks' chant from the hall (a formant stand-in for a recorded smot; advisor review),
 * its corrupted double, whispers and steps behind the player, a heartbeat under fear,
 * forest drum, gong and sobs, knocks in the walls and the apparition's scream.
 */
export class PagodaSoundscape {
  private chant: StaticSound | null = null;
  private wrongChant: StaticSound | null = null;
  private heart: StaticSound | null = null;
  private readonly whispers: StaticSound[] = [];
  private readonly far: StaticSound[] = [];
  private knock: StaticSound | null = null;
  private steps: StaticSound | null = null;
  private scream: StaticSound | null = null;
  private grindSound: StaticSound | null = null;
  private chantLevel = 0;
  private hushed = 0;
  private stillFor = 0;
  private nextWhisper = 18;
  private nextFar = 30;
  private nextKnock = 70;
  private rand = Math.random;
  private readonly loops: StaticSound[] = [];
  private readonly breaths: StaticSound[] = [];
  private readonly bells: StaticSound[] = [];
  private snap: StaticSound | null = null;
  private bowl: StaticSound | null = null;
  private shriek: StaticSound | null = null;
  private birds: StaticSound | null = null;
  private time = 0;
  private harvest: StaticSound | null = null;
  private gaspSound: StaticSound | null = null;
  private score = new DreadScore(null);
  private memoryMode: "hidden" | "harvest" | "famine" = "hidden";
  private mutedCinematic = false;
  constructor(private readonly game: Game) {
    game.scene.onDisposeObservable.addOnce(() => {
      for (const sound of [
        ...this.loops,
        ...this.breaths,
        ...this.bells,
        this.harvest,
        this.birds,
        this.snap,
        this.bowl,
        this.shriek,
        this.gaspSound,
        this.chant,
        this.wrongChant,
        this.heart,
        ...this.whispers,
        ...this.far,
        this.knock,
        this.steps,
        this.scream,
        this.grindSound,
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
      loop = false,
      bus: "ambience" | "sfx" | "threat" = "ambience",
      minDistance = 5,
      maxDistance = 40,
    ) => {
      const sound = await audio.spatialSound("ep2_" + name, audio.buffer(samples, rate), bus, at, {
        volume,
        loop,
        minDistance,
        maxDistance,
      });
      if (loop) sound.play();
      return sound;
    };
    this.loops.push(
      await spatial("pond", frogsLoop(rate, seededRandom(200)), new Vector3(6, 0, -23), 0.18, true),
    );
    this.loops.push(
      await spatial(
        "crickets",
        cricketsLoop(rate, seededRandom(202)),
        new Vector3(-25, 2, 0),
        0.1,
        true,
      ),
    );
    this.loops.push(
      await spatial("wind", canopyWind(rate, seededRandom(203)), new Vector3(0, 9, 0), 0.18, true),
    );
    this.snap = await spatial(
      "timber",
      boardCreak(rate, seededRandom(204)),
      new Vector3(0, 3, -32),
      0.35,
      false,
      "threat",
    );
    this.bowl = await spatial(
      "bowl",
      foliageMovement(rate, seededRandom(205)),
      Vector3.Zero(),
      0.65,
      false,
      "sfx",
    );
    this.shriek = await spatial(
      "shriek",
      spiritShriek(rate, seededRandom(206)),
      Vector3.Zero(),
      0.38,
      false,
      "threat",
    );
    for (let i = 0; i < 5; i++)
      this.breaths.push(
        await spatial(
          "pret_" + i,
          rattlingBreath(rate, seededRandom(210 + i)),
          Vector3.Zero(),
          0,
          true,
          "threat",
        ),
      );
    for (let i = 0; i < 3; i++) {
      const hit = noise(rate * 5, seededRandom(220 + i));
      for (let n = 0; n < hit.length; n++) hit[n] *= Math.exp(-n / (rate * 0.006));
      const fundamental = [520, 360, 220][i];
      const bell = normalise(
        modal(hit, rate, [
          [fundamental, 2.8, 1],
          [fundamental * 2.76, 1.8, 0.6],
          [fundamental * 5.4, 1, 0.24],
        ]),
        0.7,
      );
      this.bells.push(
        await spatial("bell_" + i, bell, new Vector3(18.4 + i, 2, -(-9)), 0.5, false, "sfx"),
      );
    }
    this.birds = await spatial(
      "birds",
      dawnBirds(rate, seededRandom(230)),
      new Vector3(-20, 5, 0),
      0.16,
      true,
    );
    this.birds.stop();
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
    // The horror layer. Chants loop at zero and are faded by update().
    // A chant carries: full across the hall's yard, still there at the gate.
    this.chant = await spatial(
      "chant",
      monkChant(rate, seededRandom(240)),
      ALTAR,
      0,
      true,
      "ambience",
      12,
      90,
    );
    this.wrongChant = await audio.sound(
      "ep2_chant_wrong",
      audio.buffer(monkChant(rate, seededRandom(241), true), rate),
      "music",
      0,
    );
    this.wrongChant.loop = true;
    this.wrongChant.play();
    this.heart = await audio.sound(
      "ep2_heartbeat",
      audio.buffer(heartbeat(rate), rate),
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
          0.5,
          false,
          "threat",
        ),
      );
    for (const [name, samples, volume] of [
      ["drum", templeDrum(rate, seededRandom(260)), 0.6],
      ["gong", templeGong(rate, seededRandom(261)), 0.55],
      ["sob", distantSob(rate, seededRandom(262)), 0.5],
    ] as const)
      // Out in the trees, 42 m off: far, but heard.
      this.far.push(
        await spatial(name, samples, Vector3.Zero(), volume, false, "ambience", 30, 90),
      );
    this.knock = await spatial(
      "knock",
      woodKnocks(rate, seededRandom(263)),
      Vector3.Zero(),
      0.6,
      false,
      "sfx",
    );
    this.steps = await spatial(
      "steps",
      stepsBehind(rate, seededRandom(264)),
      Vector3.Zero(),
      0.45,
      false,
      "threat",
    );
    this.grindSound = await spatial(
      "stone_grind",
      stoneGrind(rate, seededRandom(266)),
      Vector3.Zero(),
      0.75,
      false,
      "sfx",
      6,
      45,
    );
    this.scream = await audio.sound(
      "ep2_apparition_scream",
      audio.buffer(ghostScream(rate, seededRandom(265)), rate),
      "threat",
      0.9,
    );
  }

  /** A point `distance` metres from the listener, `angle` radians off straight behind. */
  private around(l: HorrorListener, distance: number, angle: number, y = 1.6): Vector3 {
    const a = l.yaw + Math.PI + angle;
    return new Vector3(l.x + Math.sin(a) * distance, y, l.z + Math.cos(a) * distance);
  }

  /** The horror layer, every frame. Silent in cinematics and memories. */
  haunt(dt: number, l: HorrorListener, enabled: boolean): void {
    const live = enabled && this.memoryMode === "hidden" && !this.mutedCinematic;
    const chantStage = ["arrival", "garden", "library"].includes(l.stage);
    // The chant stops dead when Sora steps into the hall, and returns only after she leaves.
    this.hushed = l.inHall ? 6 : Math.max(0, this.hushed - dt);
    const chantTarget = live && chantStage && this.hushed === 0 ? 0.8 : 0;
    this.chantLevel += (chantTarget - this.chantLevel) * Math.min(1, dt * (chantTarget ? 0.4 : 6));
    if (this.chant) this.chant.volume = this.chantLevel;
    const wrongTarget = live && (l.stage === "escape" || l.stage === "memory") ? 0.45 : 0;
    if (this.wrongChant)
      this.wrongChant.volume += (wrongTarget - this.wrongChant.volume) * Math.min(1, dt);
    if (this.heart)
      this.heart.volume +=
        ((live ? Math.max(0, l.fear - 0.25) * 0.9 : 0) - this.heart.volume) * Math.min(1, dt * 2);
    if (!live || l.stage === "dawn" || l.stage === "complete") return;
    this.stillFor = l.moving ? 0 : this.stillFor + dt;
    this.nextWhisper -= dt;
    this.nextFar -= dt;
    this.nextKnock -= dt;
    if (this.nextWhisper <= 0 && !l.safe) {
      this.nextWhisper = 20 + this.rand() * 35;
      const w = this.whispers[Math.floor(this.rand() * this.whispers.length)];
      if (w) {
        w.spatial.position = this.around(l, 1.2 + this.rand(), (this.rand() - 0.5) * 1.6);
        w.play();
      }
    }
    if (this.stillFor > 4 && !l.safe && this.rand() < dt * 0.05 && this.steps) {
      this.stillFor = -12;
      this.steps.spatial.position = this.around(l, 2.2, (this.rand() - 0.5) * 0.8, 0.1);
      this.steps.play();
    }
    if (this.nextFar <= 0) {
      this.nextFar = 40 + this.rand() * 50;
      const sound = this.far[Math.floor(this.rand() * this.far.length)];
      if (sound) {
        const a = this.rand() * Math.PI * 2;
        sound.spatial.position = new Vector3(Math.cos(a) * 42, 2, Math.sin(a) * 42);
        sound.play();
      }
    }
    if (this.nextKnock <= 0 && (l.safe || l.inHall) && this.knock) {
      this.nextKnock = 80 + this.rand() * 70;
      this.knock.spatial.position = this.around(l, 2.5, (this.rand() - 0.5) * 2.4, 1.3);
      this.knock.play();
    }
  }

  /** Something just behind the player: bare steps and a whisper at `at`. */
  behind(at: Vector3): void {
    if (this.steps) {
      this.steps.spatial.position = new Vector3(at.x, 0.1, at.z);
      this.steps.play();
    }
    const w = this.whispers[0];
    if (w) {
      w.spatial.position = new Vector3(at.x, 1.6, at.z);
      w.play();
    }
  }

  /** A stone image has moved where the player could not see it. */
  grind(at: Vector3): void {
    if (!this.grindSound) return;
    this.grindSound.spatial.position = at.clone();
    this.grindSound.play();
  }

  /** A glimpse, not a shock: the score rises and the ears start to ring. */
  unease(): void {
    this.score.sting("rise", 0.7);
  }

  /** The apparition's scream and the shock sting, together, peaking just under clipping. */
  scare(volume = 1): void {
    if (this.scream) {
      this.scream.volume = 0.6 * volume;
      this.scream.play();
    }
    this.score.sting("shock", 0.55 * volume);
  }
  update(
    dt: number,
    positions: readonly { x: number; z: number }[],
    active: boolean,
    escape: boolean,
  ): void {
    this.time += dt;
    if (this.harvest)
      this.harvest.volume = this.memoryMode === "harvest" && !this.mutedCinematic ? 0.22 : 0;
    this.score.pressure(
      this.memoryMode !== "hidden" || this.mutedCinematic ? 0 : escape ? 0.5 : active ? 0.12 : 0,
    );
    this.score.update(dt);
    this.breaths.forEach((sound, i) => {
      const p = positions[i];
      sound.volume = active && this.memoryMode === "hidden" && p?.x !== undefined ? 0.18 : 0;
      if (p) sound.spatial.position = new Vector3(p.x, 2, p.z);
    });
    if (escape && this.time > 4) {
      this.time = 0;
      this.snap?.play();
    }
  }
  ring(index: number): void {
    this.bells[index]?.play();
  }
  throw(at: Vector3): void {
    if (this.bowl) {
      this.bowl.spatial.position = at;
      this.bowl.play();
    }
  }
  gasp(at: Vector3): void {
    if (this.gaspSound) {
      this.gaspSound.play();
    } else if (this.shriek) {
      this.shriek.spatial.position = at;
      this.shriek.play();
    }
  }
  memory(mode: "hidden" | "harvest" | "famine"): void {
    this.memoryMode = mode;
    if (mode === "harvest") this.harvest?.play();
    else this.harvest?.stop();
  }
  cinematicPause(paused: boolean): void {
    this.mutedCinematic = paused;
  }
  crash(): void {
    this.snap?.play();
    this.score.sting("shock", 0.45);
  }
  dawnBell(): void {
    this.bells[2]?.play();
  }
  dawn(): void {
    this.harvest?.stop();
    this.score.stop();
    for (const s of [...this.loops, ...this.breaths, this.chant, this.wrongChant, this.heart])
      s?.stop();
    this.birds?.play();
  }
}
