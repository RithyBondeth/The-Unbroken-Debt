import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import "@babylonjs/core/Particles/particleSystemComponent";
import type { Area } from "@/core/areaLoader";
import { seededRandom } from "@/audio/synth";
import { TENT_FLAME_MESH } from "../data/arrival";
import { HALL } from "../data/funeral";

/** The candle and lamp flames of the hall, the family altar's lamp among them. */
const FLAMES = new RegExp(`${TENT_FLAME_MESH.source}|^hall_altar_lamp_flame$`);

interface Flame {
  mesh: AbstractMesh;
  base: Vector3;
  turn: Quaternion;
  phase: number;
  rate: number;
}

/**
 * The hall Sok lies in, alive in its small way (the user, Nov 19, 2026: "make the house
 * feel scary and pressure the smoke of incense and light of candle should be animate").
 *
 * - Every flame wavers on its wick: it stretches and shrinks, narrows as it rises and
 *   leans with the draught, never two in step.
 * - Incense smoke climbs from the altar's pot and the main burner in thin columns that
 *   slow, widen and curl as they rise.
 * - Under the ceiling the smoke has nowhere to go: it gathers in a slow, low haze that
 *   turns over above Sora's head, thickest in the corners the lamps don't reach.
 *
 * The four corner sticks smoke from the vigil (Vigil.ts); their burning down dims all of
 * this with the room's lights (`level`, VillageLights.tentLevel).
 */
export class FuneralRoom {
  private readonly flames: Flame[] = [];
  private readonly columns: ParticleSystem[] = [];
  private readonly haze: ParticleSystem;
  private readonly texture: DynamicTexture;
  private time = 0;

  constructor(scene: Scene, area: Area, low: boolean) {
    const random = seededRandom(6242801);
    for (const mesh of area.container.meshes) {
      if (!FLAMES.test(mesh.name)) continue;
      // Waver from the wick: the pivot at the bottom of the flame, not its middle.
      const box = mesh.getBoundingInfo().boundingBox;
      mesh.setPivotPoint(
        new Vector3((box.minimum.x + box.maximum.x) / 2, box.minimum.y, (box.minimum.z + box.maximum.z) / 2),
      );
      const turn = mesh.rotationQuaternion?.clone() ?? Quaternion.FromEulerVector(mesh.rotation);
      mesh.rotationQuaternion = turn.clone();
      this.flames.push({ mesh, base: mesh.scaling.clone(), turn, phase: random() * 100, rate: 0.8 + random() * 0.5 });
    }

    this.texture = wisp(scene);
    const altar = [area.level.flames.get("altar_0"), area.level.flames.get("altar_1")].filter((f) => !!f);
    const sources: Vector3[] = [];
    const burner = area.level.markers.get("main_burner");
    if (burner) sources.push(burner.position.add(new Vector3(0, 0.12, 0)));
    if (altar.length === 2)
      // The altar's incense pot stands between its two candles, a little lower.
      sources.push(altar[0].position.add(altar[1].position).scale(0.5).add(new Vector3(0, -0.06, -0.12)));
    for (const [i, at] of sources.entries()) this.columns.push(this.column(scene, `hall_incense_${i}`, at, low));
    this.haze = this.ceilingHaze(scene, low);
  }

  /** A thin column of incense smoke rising from `at`. */
  private column(scene: Scene, name: string, at: Vector3, low: boolean): ParticleSystem {
    const ps = new ParticleSystem(name, low ? 50 : 110, scene);
    ps.particleTexture = this.texture;
    ps.emitter = at;
    ps.minEmitBox.set(-0.015, 0, -0.015);
    ps.maxEmitBox.set(0.015, 0.02, 0.015);
    ps.direction1 = new Vector3(-0.07, 1, -0.07);
    ps.direction2 = new Vector3(0.07, 1, 0.07);
    ps.minEmitPower = 0.14;
    ps.maxEmitPower = 0.24;
    // Quick off the stick, then slowing and spreading as the heat goes out of it.
    ps.addVelocityGradient(0, 1);
    ps.addVelocityGradient(0.4, 0.45);
    ps.addVelocityGradient(1, 0.15);
    ps.minLifeTime = 6;
    ps.maxLifeTime = 9;
    // A thread of smoke off the sticks, only opening out well above the altar.
    ps.addSizeGradient(0, 0.012);
    ps.addSizeGradient(0.35, 0.05);
    ps.addSizeGradient(1, 0.45);
    ps.minAngularSpeed = -0.5;
    ps.maxAngularSpeed = 0.5;
    ps.minInitialRotation = 0;
    ps.maxInitialRotation = Math.PI * 2;
    ps.addColorGradient(0, new Color4(0.78, 0.76, 0.72, 0), new Color4(0.7, 0.68, 0.66, 0));
    ps.addColorGradient(0.08, new Color4(0.78, 0.76, 0.72, 0.13), new Color4(0.7, 0.68, 0.66, 0.1));
    ps.addColorGradient(0.6, new Color4(0.72, 0.7, 0.68, 0.07), new Color4(0.66, 0.64, 0.62, 0.05));
    ps.addColorGradient(1, new Color4(0.7, 0.7, 0.7, 0), new Color4(0.66, 0.64, 0.62, 0));
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.emitRate = low ? 8 : 16;
    ps.preWarmCycles = 200;
    ps.preWarmStepOffset = 4;
    ps.start();
    return ps;
  }

  /** The smoke that has risen and spread under the ceiling, turning over slowly. */
  private ceilingHaze(scene: Scene, low: boolean): ParticleSystem {
    const ps = new ParticleSystem("hall_incense_haze", low ? 24 : 60, scene);
    ps.particleTexture = this.texture;
    const centre = new Vector3((HALL.minX + HALL.maxX) / 2, HALL.floor + 2.2, (HALL.minZ + HALL.maxZ) / 2);
    ps.emitter = centre;
    const hx = (HALL.maxX - HALL.minX) / 2 - 0.6,
      hz = (HALL.maxZ - HALL.minZ) / 2 - 0.8;
    ps.minEmitBox.set(-hx, -0.25, -hz);
    ps.maxEmitBox.set(hx, 0.2, hz);
    ps.direction1 = new Vector3(-0.3, -0.04, -0.3);
    ps.direction2 = new Vector3(0.3, 0.05, 0.3);
    ps.minEmitPower = 0.02;
    ps.maxEmitPower = 0.07;
    ps.minLifeTime = 16;
    ps.maxLifeTime = 26;
    ps.minSize = 1.3;
    ps.maxSize = 2.6;
    ps.addSizeGradient(0, 0.9);
    ps.addSizeGradient(1, 2.4);
    ps.minAngularSpeed = -0.08;
    ps.maxAngularSpeed = 0.08;
    ps.minInitialRotation = 0;
    ps.maxInitialRotation = Math.PI * 2;
    ps.addColorGradient(0, new Color4(0.62, 0.6, 0.57, 0));
    ps.addColorGradient(0.25, new Color4(0.62, 0.6, 0.57, 0.075));
    ps.addColorGradient(0.75, new Color4(0.58, 0.57, 0.55, 0.06));
    ps.addColorGradient(1, new Color4(0.58, 0.57, 0.55, 0));
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.emitRate = low ? 1.2 : 3;
    ps.preWarmCycles = 600;
    ps.preWarmStepOffset = 10;
    ps.start();
    return ps;
  }

  /** `level` is the room's light (1 full, falling as the corner incense burns down). */
  update(dt: number, level: number): void {
    this.time += dt;
    const t = this.time;
    for (const f of this.flames) {
      if (!f.mesh.isEnabled()) continue;
      const p = f.phase,
        r = f.rate;
      // Two slow swells, a quick tremor and, now and then, a gutter.
      const swell = 0.5 * Math.sin(t * 2.1 * r + p) + 0.3 * Math.sin(t * 4.7 * r + p * 1.7);
      const tremor = 0.12 * Math.sin(t * 23 * r + p * 3.1) * Math.sin(t * 7.3 + p);
      const gutter = Math.max(0, Math.sin(t * 0.37 * r + p * 0.5) - 0.92) * 6;
      const stretch = 1 + 0.16 * swell + tremor - 0.35 * gutter;
      f.mesh.scaling.set(
        f.base.x * (1 - 0.07 * swell),
        f.base.y * Math.max(0.45, stretch),
        f.base.z * (1 - 0.07 * swell),
      );
      // The draught from the door and the windows leans it this way and that.
      const lean = Quaternion.RotationYawPitchRoll(
        0,
        0.04 * Math.sin(t * 1.1 * r + p * 2.3),
        0.06 * Math.sin(t * 1.3 * r + p) + 0.1 * gutter,
      );
      f.turn.multiplyToRef(lean, f.mesh.rotationQuaternion!);
    }
    const smoke = Math.max(0.25, level);
    for (const ps of this.columns) ps.emitRate = (ps.getCapacity() > 60 ? 16 : 8) * smoke;
  }

  dispose(): void {
    for (const ps of this.columns) ps.dispose();
    this.haze.dispose();
    this.texture.dispose();
  }
}

/** A soft, ragged wisp: smoke, not a ball. */
function wisp(scene: Scene): DynamicTexture {
  const size = 128;
  const texture = new DynamicTexture("T_hall_incense_wisp", { width: size, height: size }, scene, false);
  const ctx = texture.getContext();
  ctx.clearRect(0, 0, size, size);
  const random = seededRandom(6242802);
  for (let i = 0; i < 14; i++) {
    const x = size / 2 + (random() - 0.5) * size * 0.45;
    const y = size / 2 + (random() - 0.5) * size * 0.45;
    const r = size * (0.14 + random() * 0.22);
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    const a = 0.1 + random() * 0.14;
    g.addColorStop(0, `rgba(255,255,255,${a})`);
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
  }
  texture.hasAlpha = true;
  texture.update();
  return texture;
}
