import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import type { SpaceName } from "../../../audio/acoustics";
import { seededRandom } from "../../../audio/synth";
import { floorDrips, houseSettle, roofRain, shutterWind } from "../audio/houseSounds";
import { inHunt } from "../data/hunt";

/** The upper floor of the house, its boards at 2.5 m. */
const inHouse = (feet: Vector3) =>
  feet.y > 1.9 && Math.abs(feet.x) < 6.3 && feet.z < -9.3 && feet.z > -18.7;
/** Under the funeral pavilion's cloth. */
const inTent = (feet: Vector3) =>
  Math.abs(feet.x) < 3.8 && feet.z < -1 && feet.z > -7 && feet.y < 0.5;

/** Which space Sora is in, for its acoustics and its ambience (Audio Design Document, section 3). */
export function spaceAt(feet: Vector3): SpaceName {
  if (inHunt(feet)) return "underHouse";
  if (inHouse(feet)) return "house";
  if (inTent(feet)) return "tent";
  return "outdoors";
}

/** The zone layers' levels in each space: [roof rain, shutter wind, drips]. */
const LAYERS: Record<SpaceName, [number, number, number]> = {
  house: [0.3, 0.2, 0],
  wardrobe: [0.15, 0.06, 0],
  underHouse: [0.06, 0, 0.35],
  tent: [0, 0, 0],
  outdoors: [0, 0, 0],
  studio: [0, 0, 0],
};

/**
 * Where Sora is decides how the night sounds: the acoustics of the space
 * (`AudioSystem.setSpace`) and the layers that belong to it. Upstairs, rain on
 * the roof tiles overhead and the wind in the shutters, while the old house
 * ticks and settles; underneath, water dripping through the boards. Layers
 * crossfade over about 2.5 s; the settling stops whenever the night falls
 * silent for a threat.
 */
export class Soundscape {
  private roof: StaticSound | null = null;
  private wind: StaticSound | null = null;
  private drips: StaticSound | null = null;
  private readonly settles: StaticSound[] = [];
  private readonly levels = [0, 0, 0];
  private nextSettle = 10;
  private stopped = false;
  private readonly rand = seededRandom(2501);

  constructor(
    private readonly game: Game,
    /** 0–1: how far the night has fallen silent for a threat (NightLife). */
    private readonly silence: () => number,
  ) {}

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const bed = async (name: string, samples: Float32Array | Float32Array[]) => {
      const sound = await audio.sound(name, audio.buffer(samples, rate), "room", 0);
      sound.loop = true;
      sound.play();
      return sound;
    };
    this.roof = await bed("roof_rain", [
      roofRain(rate, seededRandom(2511)),
      roofRain(rate, seededRandom(2512)),
    ]);
    this.wind = await bed("shutter_wind", shutterWind(rate, seededRandom(2513)));
    this.drips = await bed("floor_drips", floorDrips(rate, seededRandom(2514)));
    for (let k = 0; k < 4; k++)
      this.settles.push(
        await audio.spatialSound(
          `house_settle_${k}`,
          audio.buffer(houseSettle(rate, seededRandom(2520 + k)), rate),
          "sfx",
          Vector3.Zero(),
          { minDistance: 2, volume: 0.35 },
        ),
      );
  }

  update(dt: number): void {
    if (this.stopped) return;
    const g = this.game;
    const feet = g.player.feet;
    const where = spaceAt(feet);
    const space = where === "house" && g.hiding ? "wardrobe" : where;
    g.audio?.setSpace(space, space === "wardrobe" || where === "house" ? 0.6 : 2.5);
    const target = LAYERS[space];
    const k = Math.min(1, dt / 0.8);
    [this.roof, this.wind, this.drips].forEach((sound, i) => {
      this.levels[i] += (target[i] - this.levels[i]) * k;
      if (sound) sound.volume = this.levels[i];
    });
    this.nextSettle -= dt;
    const quiet =
      this.silence() > 0 || g.threatActive || !!g.hiding || g.cutscene || space === "outdoors";
    if (this.nextSettle <= 0) {
      this.nextSettle = 12 + this.rand() * 26;
      const sound = this.settles[Math.floor(this.rand() * this.settles.length)];
      if (sound && !quiet && (space === "house" || space === "underHouse")) {
        // Somewhere in the walls, the rafters or (from below) the boards overhead.
        const a = this.rand() * Math.PI * 2,
          r = 2 + this.rand() * 2.5;
        const up = space === "underHouse" ? 1.3 : 0.6 + this.rand() * 1.8;
        sound.spatial.position = new Vector3(
          feet.x + Math.cos(a) * r,
          feet.y + up,
          feet.z + Math.sin(a) * r,
        );
        sound.play();
      }
    }
  }

  /** Dawn: the rain is over and the house is quiet. */
  stop(): void {
    this.stopped = true;
    for (const sound of [this.roof, this.wind, this.drips, ...this.settles]) sound?.stop();
    this.game.audio?.setSpace("outdoors");
  }
}
