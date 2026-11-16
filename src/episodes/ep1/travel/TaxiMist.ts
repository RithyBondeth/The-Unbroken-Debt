import type { Game } from "@/core/Game";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { MistPocket } from "@/render/mist";
import { seededRandom } from "@/audio/synth";
import { taxiRoadPoint } from "./taxiMotion";
import { taxiMistLevel } from "./taxiApparitions";

/**
 * The air as Episode 2's forest has it: a thin grey-green haze, a shade lighter
 * than the trees, so trunk after trunk and crown after crown stand dark against
 * it far into the forest instead of being swallowed by a white wall.
 */
const HAZE = {
  /** Per metre; Episode 2's pagoda is 0.03, the road a little clearer. */
  density: 0.024,
  /**
   * What the haze scatters of the night by itself (linear RGB): Episode 2's
   * grey-teal, a little brighter because there is no lantern to set it off.
   */
  ambient: [0.012, 0.018, 0.021],
  heightFalloff: 0.15,
  /** Marched past the modelled trees into the far tree cards. */
  maxDistance: 75,
} as const;

/** How far ahead of the car a bank is laid, and how far behind it is taken up again (m). */
const AHEAD = 62;
const BEHIND = 14;
/** Headlamp glow hanging in the mist: metres ahead, height, reach and strength. */
const BEAM_GLOW = [
  [3.6, 0.72, 5.5, 3.4],
  [9, 0.8, 9, 2.3],
  [17, 0.95, 13, 1.2],
] as const;

interface Bank extends MistPocket {
  along: number;
  lateral: number;
  drift: number;
}

/**
 * Monsoon haze on the forest road, as thin as Episode 2's forest: low ground mist
 * lies between the trunks and drifts with the wind, the headlamps hang in it as
 * two soft cones, and every lightning flash shows the forest standing in it.
 * On Low (no volumetric pass) the same levels drive the scene's distance fog.
 */
export class TaxiMist {
  private readonly banks: Bank[] = [];
  private readonly glow: PointLight[] = [];
  private readonly random = seededRandom(4471);
  private readonly point = new Vector3();

  constructor(
    private readonly game: Game,
    private readonly route: TransformNode,
  ) {
    const scene = game.scene;
    // Lights that exist only for the fog: they are given one hidden mesh to light.
    const nothing = new Mesh("taxi_mist_glow_target", scene);
    nothing.isVisible = false;
    for (const [z, y, range] of BEAM_GLOW) {
      const light = new PointLight(`taxi_mist_beam_${z}`, new Vector3(0, y, 2.5 + z), scene);
      light.diffuse.set(1, 0.86, 0.62);
      light.range = range;
      light.includedOnlyMeshes = [nothing];
      light.intensity = 0;
      this.glow.push(light);
    }
    for (let i = 0; i < 4; i++) this.banks.push(this.lay((i / 4) * (AHEAD + BEHIND) - BEHIND, 0));
  }

  /** A new bank `ahead` metres along from the car at `distance`. */
  private lay(ahead: number, distance: number, bank?: Bank): Bank {
    const r = this.random,
      wide = r() < 0.2;
    const next: Bank = bank ?? {
      x: 0,
      z: 0,
      radiusX: 1,
      radiusZ: 1,
      baseY: -0.3,
      height: 1,
      density: 0,
      along: 0,
      lateral: 0,
      drift: 0,
    };
    next.along = distance + ahead;
    // Low ground mist lying between the trunks either side; now and then a thin
    // skein of it across the track. Knee to waist high, never a wall.
    next.lateral = wide ? (r() - 0.5) * 3 : (r() < 0.5 ? -1 : 1) * (6 + r() * 10);
    next.radiusX = wide ? 6 + r() * 4 : 5 + r() * 6;
    next.radiusZ = 6 + r() * 7;
    next.height = wide ? 0.6 + r() * 0.4 : 0.9 + r() * 0.8;
    next.density = wide ? 0.08 + r() * 0.06 : 0.12 + r() * 0.12;
    next.drift = (r() - 0.5) * 0.5;
    return next;
  }

  configure(): void {
    const fog = this.game.pipeline.fog;
    if (!fog) return;
    fog.heightFalloff = HAZE.heightFalloff;
    fog.maxDistance = HAZE.maxDistance;
    fog.setMistPockets(this.banks);
    fog.lights.push(...this.glow);
  }

  /** `beams` is the headlamps' electrical power, 0–1; `flash` the lightning. */
  update(dt: number, t: number, distance: number, beams: number, flash: number): void {
    const g = this.game,
      level = taxiMistLevel(t),
      fog = g.pipeline.fog;
    // Lightning is scattered by every droplet at once: the mist becomes the light.
    const lit = flash * 0.05 * level;
    const [r, gr, b] = HAZE.ambient;
    if (fog) {
      fog.density = HAZE.density * level;
      fog.ambient.set(r + lit * 0.82, gr + lit * 0.9, b + lit);
      fog.mistStrength = 0.6 * level;
    } else {
      g.scene.fogDensity = HAZE.density * level;
      g.scene.fogColor.set(r + lit * 0.82, gr + lit * 0.9, b + lit);
    }
    BEAM_GLOW.forEach(([, , , strength], i) => {
      this.glow[i].intensity = strength * beams * (0.7 + 0.3 * level);
    });
    const matrix = this.route.computeWorldMatrix(true),
      wind = g.wind;
    for (const bank of this.banks) {
      // Taken up behind the car and laid again ahead; after a resumed ride or a
      // skip, spread over the whole stretch instead of arriving as one wall.
      if (bank.along < distance - BEHIND - 25 || bank.along > distance + AHEAD + 25)
        this.lay(this.random() * (AHEAD + BEHIND) - BEHIND, distance, bank);
      else if (bank.along < distance - BEHIND)
        this.lay(AHEAD * (0.85 + this.random() * 0.15), distance, bank);
      bank.lateral += (bank.drift + wind.strength * 0.5) * dt;
      const at = taxiRoadPoint(bank.lateral, bank.along);
      Vector3.TransformCoordinatesFromFloatsToRef(at.x, 0, at.z, matrix, this.point);
      bank.x = this.point.x;
      bank.z = this.point.z;
    }
  }
}
