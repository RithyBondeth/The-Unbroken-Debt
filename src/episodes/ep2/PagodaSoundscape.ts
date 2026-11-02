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

/** Original synthesis in the same audio space as Episode 1; no invented ceremonial speech. */
export class PagodaSoundscape {
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
    ) => {
      const sound = await audio.spatialSound("ep2_" + name, audio.buffer(samples, rate), bus, at, {
        volume,
        loop,
        minDistance: 5,
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
    for (const s of [...this.loops, ...this.breaths]) s.stop();
    this.birds?.play();
  }
}
