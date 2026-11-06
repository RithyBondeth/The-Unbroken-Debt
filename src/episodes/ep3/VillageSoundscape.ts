import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../core/Game";
import {
  seededRandom,
  brown,
  normalise,
  boardCreak,
  wetStep,
  rattlingBreath,
} from "../../audio/synth";
import { villageRain, dawnBirds, branchSnap } from "../../audio/sounds/nightSounds";
import { DreadScore } from "../../audio/DreadScore";
import type { VillageStage } from "./VillageProgress";

/** Positioned water, breathing under the boards, tin rain and timber failure share the series mix. */
export class VillageSoundscape {
  private water: StaticSound | null = null;
  private rain: StaticSound | null = null;
  private birds: StaticSound | null = null;
  private breath: StaticSound | null = null;
  private creak: StaticSound | null = null;
  private snap: StaticSound | null = null;
  private stroke: StaticSound | null = null;
  private pump: StaticSound | null = null;
  private lullaby: StaticSound | null = null;
  private readonly score: DreadScore;
  private time = 0;
  constructor(private readonly game: Game) {
    this.score = new DreadScore(game.audio);
    game.scene.onDisposeObservable.addOnce(() => this.dispose());
  }
  async load(): Promise<void> {
    const a = this.game.audio;
    if (!a) return;
    const rate = a.context.sampleRate;
    const water = brown(rate * 12, seededRandom(315));
    for (let i = 0; i < water.length; i++)
      water[i] *= 0.35 + 0.25 * Math.sin((i / rate) * 2.3) ** 2;
    this.water = await a.sound(
      "ep3_water",
      a.buffer(normalise(water, 0.65), rate),
      "ambience",
      0.16,
    );
    this.water.loop = true;
    this.water.play();
    this.rain = await a.sound(
      "ep3_tin_rain",
      a.buffer(villageRain(rate, seededRandom(316)), rate),
      "room",
      0,
    );
    this.rain.loop = true;
    this.rain.play();
    this.birds = await a.sound(
      "ep3_market_birds",
      a.buffer(dawnBirds(rate, seededRandom(317)), rate),
      "ambience",
      0.12,
    );
    this.birds.loop = true;
    this.birds.play();
    this.breath = await a.spatialSound(
      "ep3_underwater_breath",
      a.buffer(rattlingBreath(rate, seededRandom(318)), rate),
      "threat",
      new Vector3(4, 0.1, -4),
      { volume: 0, loop: true, minDistance: 2, maxDistance: 18 },
    );
    this.breath.play();
    this.creak = await a.spatialSound(
      "ep3_timber_strain",
      a.buffer(boardCreak(rate, seededRandom(319)), rate),
      "threat",
      new Vector3(0, 2, -5),
      { volume: 0.35, minDistance: 3 },
    );
    this.snap = await a.spatialSound(
      "ep3_breaking_piles",
      a.buffer(branchSnap(rate, seededRandom(320)), rate),
      "threat",
      new Vector3(-10, -1, -4),
      { volume: 0.5, minDistance: 5 },
    );
    this.stroke = await a.sound(
      "ep3_oar_stroke",
      a.buffer(wetStep(rate, seededRandom(321)), rate),
      "sfx",
      0.3,
    );
    const diesel = new Float32Array(rate * 4);
    for (let i = 0; i < diesel.length; i++) {
      const t = i / rate;
      diesel[i] =
        (Math.sin(t * 2 * Math.PI * 42) * 0.3 + Math.sin(t * 2 * Math.PI * 84) * 0.12) *
        (0.5 + 0.5 * Math.cos(t * 2 * Math.PI * 7) ** 4);
    }
    this.pump = await a.spatialSound(
      "ep3_drainage_pump",
      a.buffer(diesel, rate),
      "sfx",
      new Vector3(7, 0.8, -8),
      { volume: 0, loop: true, minDistance: 2, maxDistance: 25 },
    );
    this.pump.play();
    // An original, wordless four-note fragment. No simulated Khmer dialogue or ceremonial recording.
    const melody = new Float32Array(rate * 10),
      notes = [196, 220, 174.61, 146.83];
    for (let i = 0; i < melody.length; i++) {
      const t = i / rate,
        k = Math.floor(t / 2.5),
        phase = t % 2.5;
      melody[i] =
        Math.sin(t * Math.PI * 2 * notes[k] + 0.018 * Math.sin(t * 29)) *
        Math.sin((Math.PI * phase) / 2.5) ** 2 *
        0.22;
    }
    this.lullaby = await a.spatialSound(
      "ep3_kanha_lullaby",
      a.buffer(melody, rate),
      "threat",
      new Vector3(0, 0.2, -4),
      { volume: 0, loop: true, minDistance: 2, maxDistance: 18 },
    );
    this.lullaby.play();
    await this.score.load();
  }
  oar(): void {
    this.stroke?.play();
  }
  update(
    dt: number,
    stage: VillageStage,
    at: { x: number; z: number },
    danger: number,
    pumping: boolean,
  ): void {
    this.time += dt;
    const storm = !["market", "memory", "dawn", "complete"].includes(stage);
    if (this.rain) this.rain.volume = storm ? 0.24 : stage === "market" ? 0.14 : 0;
    if (this.birds)
      this.birds.volume =
        stage === "market" ? 0.025 : stage === "dawn" || stage === "complete" ? 0.08 : 0;
    if (this.breath) {
      this.breath.volume = danger * 0.18;
      this.breath.spatial.position = new Vector3(at.x, 0.1, at.z);
    }
    if (this.lullaby) {
      this.lullaby.volume = stage === "purification" ? 0.1 : danger * 0.07;
      this.lullaby.spatial.position = new Vector3(at.x, 0.2, at.z);
    }
    if (this.pump) this.pump.volume = pumping && storm ? 0.18 : 0;
    this.score.pressure(stage === "escape" ? 0.6 : danger * 0.4);
    this.score.update(dt);
    if (this.time > (stage === "escape" ? 4 : 18)) {
      this.time = 0;
      if (storm) this.creak?.play();
      if (stage === "escape" || stage === "purification") this.snap?.play();
    }
  }
  private dispose(): void {
    for (const s of [
      this.water,
      this.rain,
      this.birds,
      this.breath,
      this.creak,
      this.snap,
      this.stroke,
      this.pump,
      this.lullaby,
    ])
      s?.stop();
    this.score.stop();
  }
}
