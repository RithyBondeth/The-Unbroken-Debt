import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
import type { SpaceName } from "@/audio/acoustics";
import { seededRandom } from "@/audio/synth";
import { floorDrips, houseSettle, roofRain, shutterWind } from "../audio/houseSounds";
import { inHunt } from "../data/hunt";
import { ROOFS } from "../data/farmLayout";
import { ep1AudioUrls, ep2AudioUrls } from "../audio/VillageAudio";

/** Under the house's footprint (its two blocks and the veranda), off the floor above. */
const underFootprint = (feet: Vector3) => Math.abs(feet.x) < 8.3 && feet.z < -9.6 && feet.z > -34.3;

/** On a floor at 2.5 m: the house's (and its veranda's), or the kitchen house's. */
const inHouse = (feet: Vector3) =>
  feet.y > 1.9 &&
  (underFootprint(feet) || (feet.x > 19.9 && feet.x < 28.1 && feet.z < -15.6 && feet.z > -22.7));

/** Under one of the farm's own roofs (barn, kitchen, tool shed, servants' hut, shops...). */
export const underHutRoof = (feet: Vector3) =>
  ROOFS.slice(1).some(
    (r) =>
      feet.x > r.minX &&
      feet.x < r.maxX &&
      feet.z > r.minZ &&
      feet.z < r.maxZ &&
      feet.y < r.top - 1.6,
  );

/** Which space Sora is in, for its acoustics and room ambience. */
export function spaceAt(feet: Vector3): SpaceName {
  if (underHutRoof(feet) && !underFootprint(feet)) return "house";
  if (inHunt(feet) || (feet.y < 0.9 && underFootprint(feet))) return "underHouse";
  if (inHouse(feet) || underHutRoof(feet)) return "house";
  return "outdoors";
}

/** [Roof rain, shutter wind, drips, canopy wind]. Canopy wind lives in WindAudio (no duplicate bed). */
const LAYERS: Record<SpaceName, [number, number, number, number]> = {
  house: [0.58, 0.14, 0, 0],
  wardrobe: [0.22, 0.04, 0, 0],
  underHouse: [0.14, 0, 0.46, 0],
  tent: [0.26, 0.06, 0, 0],
  outdoors: [0, 0, 0, 0],
  studio: [0, 0, 0, 0],
};

/**
 * Spatial acoustics & room beds for the redesigned Episode 1 Village: backed by real
 * mastered CC0 roof-rain, water-drip, canopy-wind, and timber-creak recordings with
 * clean procedural fallback if offline.
 */
export class Soundscape {
  private roof: StaticSound | null = null;
  private wind: StaticSound | null = null;
  private drips: StaticSound | null = null;
  private canopy: StaticSound | null = null;
  private readonly settles: StaticSound[] = [];
  private readonly levels = [0, 0, 0, 0];
  private nextSettle = 11;
  private stopped = false;
  private readonly rand = seededRandom(2501);

  constructor(
    private readonly game: Game,
    private readonly silence: () => number,
  ) {}

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;

    const loadOrSynth = async (
      name: string,
      urls: string[],
      fallback: () => Float32Array | Float32Array[],
    ) => {
      const recorded = await audio.load(urls);
      const sound = await audio.sound(name, recorded ?? audio.buffer(fallback(), rate), "room", 0);
      sound.loop = true;
      sound.play();
      return sound;
    };

    this.roof = await loadOrSynth(
      "village_roof_rain",
      ep1AudioUrls("amb_ep1_village_roof_rain"),
      () => [roofRain(rate, seededRandom(2511)), roofRain(rate, seededRandom(2512))],
    );
    this.wind = await loadOrSynth("village_shutter_wind", ep2AudioUrls("amb_ep2_wind_leaves"), () =>
      shutterWind(rate, seededRandom(2513)),
    );
    this.drips = await loadOrSynth(
      "village_floor_drips",
      ep1AudioUrls("amb_ep1_village_under_drips"),
      () => floorDrips(rate, seededRandom(2514)),
    );
    // Canopy wind is handled directly by WindAudio (no redundant looping bed)
    this.canopy = null;

    const creakClips = [
      "sfx_ep1_studio_creak_1",
      "sfx_ep1_studio_creak_2",
      "sfx_ep1_studio_creak_3",
    ];
    for (let k = 0; k < creakClips.length; k++) {
      const rec = await audio.load(ep1AudioUrls(creakClips[k]));
      this.settles.push(
        await audio.spatialSound(
          `house_settle_${k}`,
          rec ?? audio.buffer(houseSettle(rate, seededRandom(2520 + k)), rate),
          "sfx",
          Vector3.Zero(),
          { minDistance: 2, maxDistance: 18, volume: 0.36 },
        ),
      );
    }
  }

  update(dt: number): void {
    if (this.stopped) return;
    const g = this.game;
    const feet = g.player.feet;
    const where = spaceAt(feet);
    const space = where === "house" && g.hiding ? "wardrobe" : where;
    g.audio?.setSpace(space, space === "wardrobe" || where === "house" ? 0.6 : 2.2);
    const target = LAYERS[space];
    const thatch = where === "house" && !inHouse(feet) ? 0.58 : 1;
    const k = Math.min(1, dt / 0.8);
    const gusts = 0.45 + 0.7 * Math.min(1.6, g.wind.at(feet.x, feet.z));
    [this.roof, this.wind, this.drips, this.canopy].forEach((sound, i) => {
      const level =
        target[i] *
        (i >= 3 ? 1 - this.silence() * 0.8 : 1) *
        (i === 1 || i >= 3 ? gusts : 1) *
        (i === 0 ? thatch : 1);
      this.levels[i] += (level - this.levels[i]) * k;
      if (sound) sound.volume = this.levels[i];
    });

    this.nextSettle -= dt;
    const quiet =
      this.silence() > 0 || g.threatActive || !!g.hiding || g.cutscene || space === "outdoors";
    if (this.nextSettle <= 0) {
      this.nextSettle = 12 + this.rand() * 24;
      const sound = this.settles[Math.floor(this.rand() * this.settles.length)];
      if (sound && !quiet && (space === "house" || space === "underHouse")) {
        const a = this.rand() * Math.PI * 2;
        const r = 2 + this.rand() * 2.5;
        const up = space === "underHouse" ? 1.3 : 0.6 + this.rand() * 1.8;
        sound.spatial.position = new Vector3(
          feet.x + Math.cos(a) * r,
          feet.y + up,
          feet.z + Math.sin(a) * r,
        );
        sound.playbackRate = 0.92 + this.rand() * 0.16;
        sound.play();
      }
    }
  }

  stop(): void {
    this.stopped = true;
    for (const sound of [this.roof, this.wind, this.drips, this.canopy, ...this.settles])
      sound?.stop();
    this.game.audio?.setSpace("outdoors");
  }
}
