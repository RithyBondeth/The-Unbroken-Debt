import type { Game } from "@/core/Game";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Constants } from "@babylonjs/core/Engines/constants";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { SpotLight } from "@babylonjs/core/Lights/spotLight";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { MistPocket } from "@/render/mist";
import { seededRandom } from "@/audio/synth";
import { TAXI_FOREST_START, taxiRoadPoint } from "./taxiMotion";
import { taxiMistLevel } from "./taxiApparitions";

/**
 * Pitch-dark monsoon storm haze: outside the car's twin volumetric headlight cones
 * and lightning flashes, the night drops into deep wet darkness while drifting ground
 * mist coils knee-to-chest high across the ruts and between the trunks.
 */
const HAZE = {
  /** Per metre; dense humid monsoon air that holds twin golden headlight fog beams. */
  density: 0.036,
  /** Pitch-dark storm night ambient (linear RGB): only headlamps & lightning cut through. */
  ambient: [0.0022, 0.0034, 0.0052],
  heightFalloff: 0.22,
  /** Marched past the modelled trees into the far storm horizon. */
  maxDistance: 72,
} as const;

/** How far ahead of the car a mist bank is laid, and how far behind it is recycled (m). */
const AHEAD = 58;
const BEHIND = 14;

/** Soft distant scatter nodes complementing the real directional SpotLight volumetric cones. */
const BEAM_GLOW = [
  [5.2, 0.62, 6.2, 1.8],
  [12.5, 0.72, 10.5, 1.35],
  [21.0, 0.9, 14.5, 0.85],
] as const;

interface Bank extends MistPocket {
  along: number;
  lateral: number;
  drift: number;
}

/** Soft longitudinal/radial gradient texture for Low-preset volumetric headlight fog cones. */
function makeBeamConeTexture(scene: Game["scene"]): DynamicTexture {
  const tex = new DynamicTexture("taxi_beam_cone_alpha", { width: 128, height: 256 }, scene, false);
  const c = tex.getContext() as CanvasRenderingContext2D;
  c.clearRect(0, 0, 128, 256);
  const g = c.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0.0, "rgba(255,214,132,0.0)");
  g.addColorStop(0.14, "rgba(255,214,132,0.22)");
  g.addColorStop(0.55, "rgba(255,204,116,0.11)");
  g.addColorStop(1.0, "rgba(255,196,104,0.0)");
  c.fillStyle = g;
  c.fillRect(0, 0, 128, 256);
  tex.hasAlpha = true;
  tex.update();
  return tex;
}

/**
 * Heavy monsoon storm mist on the road: low swirling banks drift across the flooded ruts
 * and jungle verge, the car's twin headlamps carve real directional volumetric fog cones
 * through the pitch-black rain (with soft additive cone meshes on Low preset), and every
 * lightning strike turns the entire wet mist cold silver-blue.
 */
export class TaxiMist {
  private readonly banks: Bank[] = [];
  private readonly glow: PointLight[] = [];
  private readonly lowCones: { mesh: Mesh; mat: StandardMaterial }[] = [];
  private readonly random = seededRandom(4471);
  private readonly point = new Vector3();

  constructor(
    private readonly game: Game,
    private readonly route: TransformNode,
    private readonly headlamps: readonly SpotLight[] = [],
  ) {
    const scene = game.scene;
    // Fog-only scatter point lights: one hidden mesh keeps them out of surface shading.
    const nothing = new Mesh("taxi_mist_glow_target", scene);
    nothing.isVisible = false;
    for (const [z, y, range] of BEAM_GLOW) {
      const light = new PointLight(`taxi_mist_beam_${z}`, new Vector3(0, y, 2.2 + z), scene);
      light.diffuse.set(1, 0.8, 0.46);
      light.range = range;
      light.includedOnlyMeshes = [nothing];
      light.intensity = 0;
      this.glow.push(light);
    }
    for (let i = 0; i < 6; i++) this.banks.push(this.lay((i / 6) * (AHEAD + BEHIND) - BEHIND, 0));
  }

  /** A new drifting monsoon mist bank `ahead` metres along from the car at `distance`. */
  private lay(ahead: number, distance: number, bank?: Bank): Bank {
    const r = this.random,
      crossRoad = r() < 0.48;
    const next: Bank = bank ?? {
      x: 0,
      z: 0,
      radiusX: 1,
      radiusZ: 1,
      baseY: -0.35,
      height: 1.2,
      density: 0,
      along: 0,
      lateral: 0,
      drift: 0,
    };
    next.along = distance + ahead;
    next.lateral = crossRoad ? (r() - 0.5) * 4.2 : (r() < 0.5 ? -1 : 1) * (4.5 + r() * 9.0);
    next.radiusX = crossRoad ? 5.5 + r() * 4.5 : 5 + r() * 6;
    next.radiusZ = 6 + r() * 7.5;
    next.height = crossRoad ? 0.85 + r() * 0.65 : 1.1 + r() * 1.1;
    next.density = crossRoad ? 0.14 + r() * 0.1 : 0.18 + r() * 0.14;
    next.drift = (r() - 0.5) * 0.85;
    return next;
  }

  configure(): void {
    const fog = this.game.pipeline?.fog;
    if (fog) {
      fog.heightFalloff = HAZE.heightFalloff;
      fog.maxDistance = HAZE.maxDistance;
      fog.setMistPockets(this.banks);
      fog.lights.push(...this.glow);
      fog.spots.length = 0;
      for (const lamp of this.headlamps) fog.spots.push({ light: lamp, scatter: 0.028 });
      return;
    }
    // Low-preset fallback: lightweight additive volumetric fog cones right on the headlamps.
    if (this.lowCones.length === 0 && this.headlamps.length > 0) {
      const scene = this.game.scene;
      const tex = makeBeamConeTexture(scene);
      this.headlamps.forEach((lamp, i) => {
        const length = 19;
        const cone = CreateCylinder(
          `taxi_low_fog_cone_${i}`,
          {
            height: length,
            diameterTop: 6.4,
            diameterBottom: 0.34,
            tessellation: 18,
            hasRings: false,
          },
          scene,
        );
        const mat = new StandardMaterial(`M_taxi_low_fog_cone_${i}`, scene);
        mat.diffuseColor = Color3.Black();
        mat.specularColor = Color3.Black();
        mat.emissiveTexture = tex;
        mat.opacityTexture = tex;
        mat.emissiveColor.set(1, 0.8, 0.46);
        mat.alpha = 0.24;
        mat.alphaMode = Constants.ALPHA_ADD;
        mat.disableLighting = true;
        mat.disableDepthWrite = true;
        mat.backFaceCulling = false;
        cone.material = mat;
        cone.isPickable = false;
        const dir = lamp.direction.normalize();
        cone.position.copyFrom(lamp.position).addInPlace(dir.scale(length * 0.5 + 0.15));
        cone.rotation.x = Math.PI / 2 - Math.asin(dir.y);
        cone.rotation.y = Math.atan2(dir.x, dir.z);
        this.lowCones.push({ mesh: cone, mat });
      });
    }
  }

  /** `beams` is the headlamps' electrical power, 0–1; `flash` the lightning. */
  update(dt: number, t: number, distance: number, beams: number, flash: number): void {
    const g = this.game,
      fog = g.pipeline.fog;
    // Open paddies keep crisp visibility to roadside shops & posters; jungle tunnel thickens into oppressive mist.
    const open = Math.min(1, Math.max(0, (TAXI_FOREST_START - 8 - distance) / 24)),
      level = taxiMistLevel(t) * (1 - 0.32 * open * open * (3 - 2 * open));
    // Storm lightning illuminates every raindrop and drifting mist bank cold silver-blue!
    const lit = flash * 0.085 * level;
    const [r, gr, b] = HAZE.ambient;
    if (fog) {
      fog.density = HAZE.density * level;
      fog.ambient.set(r + lit * 0.78, gr + lit * 0.88, b + lit);
      fog.mistStrength = 0.92 * level;
    } else {
      g.scene.fogDensity = HAZE.density * 0.95 * level;
      g.scene.fogColor.set(r + lit * 0.78, gr + lit * 0.88, b + lit);
    }
    BEAM_GLOW.forEach(([, , , strength], i) => {
      this.glow[i].intensity = strength * beams * (0.75 + 0.35 * level);
    });
    for (const cone of this.lowCones) {
      cone.mesh.isVisible = beams > 0.04;
      cone.mat.alpha = Math.min(0.45, 0.24 * beams * (0.75 + 0.3 * level));
    }
    const matrix = this.route.computeWorldMatrix(true),
      wind = g.wind;
    for (const bank of this.banks) {
      if (bank.along < distance - BEHIND - 25 || bank.along > distance + AHEAD + 25)
        this.lay(this.random() * (AHEAD + BEHIND) - BEHIND, distance, bank);
      else if (bank.along < distance - BEHIND)
        this.lay(AHEAD * (0.85 + this.random() * 0.15), distance, bank);
      bank.lateral += (bank.drift + wind.strength * 0.75) * dt;
      const at = taxiRoadPoint(bank.lateral, bank.along);
      Vector3.TransformCoordinatesFromFloatsToRef(at.x, 0, at.z, matrix, this.point);
      bank.x = this.point.x;
      bank.z = this.point.z;
    }
  }
}
