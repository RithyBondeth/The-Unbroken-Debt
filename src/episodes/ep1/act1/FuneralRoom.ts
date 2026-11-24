import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import "@babylonjs/core/Particles/particleSystemComponent";
import type { Area } from "@/core/areaLoader";
import { seededRandom } from "@/audio/synth";
import { TENT_FLAME_MESH } from "../data/arrival";
import { HALL, WREATH_INCENSE } from "../data/funeral";

/**
 * The candle and lamp flames that waver: the funeral's (under the house; its many
 * candles drawn as one instanced mesh, below), the hall altar's lamp, the rooms' candles.
 */
const FLAMES = new RegExp(
  `${TENT_FLAME_MESH.source}|^hall_altar_lamp_flame$|^house_flame_[\\d_]+$`,
);
/** The funeral's candle flames under the house: about seventy, drawn in one call. */
const FUNERAL_CANDLE = /^fu_flame_\d+$/;

/** One flame of an instanced set: where it stands and how it moves. */
interface Wick {
  /** Its own world matrix relative to the set's mesh (the set draws it there). */
  base: Matrix;
  /** The foot of the flame, in world space: it wavers about it. */
  foot: Vector3;
  phase: number;
  rate: number;
}

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
  /** The funeral's candles, one thin-instanced mesh, and each wick's flame. */
  private candles: Mesh | null = null;
  private readonly wicks: Wick[] = [];
  private wickMatrices: Float32Array | null = null;
  private sourceWorld = Matrix.Identity();
  private sourceInverse = Matrix.Identity();
  private readonly columns: ParticleSystem[] = [];
  private readonly haze: ParticleSystem;
  private readonly texture: DynamicTexture;
  private time = 0;

  constructor(scene: Scene, area: Area, low: boolean) {
    const random = seededRandom(6242801);
    this.instanceCandles(area, random);
    for (const mesh of area.container.meshes) {
      if (!FLAMES.test(mesh.name) || mesh === this.candles) continue;
      // Waver from the wick: the pivot at the bottom of the flame, not its middle.
      const box = mesh.getBoundingInfo().boundingBox;
      mesh.setPivotPoint(
        new Vector3(
          (box.minimum.x + box.maximum.x) / 2,
          box.minimum.y,
          (box.minimum.z + box.maximum.z) / 2,
        ),
      );
      const turn = mesh.rotationQuaternion?.clone() ?? Quaternion.FromEulerVector(mesh.rotation);
      mesh.rotationQuaternion = turn.clone();
      this.flames.push({
        mesh,
        base: mesh.scaling.clone(),
        turn,
        phase: random() * 100,
        rate: 0.8 + random() * 0.5,
      });
    }

    this.texture = wisp(scene);
    // Smoke from the burner on the offering table and the two pots before the wreath.
    const sources: Vector3[] = [];
    const burner = area.level.markers.get("main_burner");
    if (burner) sources.push(burner.position.add(new Vector3(0, 0.12, 0)));
    sources.push(...WREATH_INCENSE.map((p) => p.clone()));
    for (const [i, at] of sources.entries())
      this.columns.push(this.column(scene, `hall_incense_${i}`, at, low));
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
    // Particles take no light: the smoke is coloured as the candles light it in the dark
    // under the house (the approved previews' threads are faint and warm), not white.
    ps.addColorGradient(0, new Color4(0.3, 0.24, 0.18, 0), new Color4(0.26, 0.21, 0.16, 0));
    ps.addColorGradient(
      0.08,
      new Color4(0.3, 0.24, 0.18, 0.11),
      new Color4(0.26, 0.21, 0.16, 0.08),
    );
    ps.addColorGradient(0.6, new Color4(0.24, 0.2, 0.16, 0.05), new Color4(0.22, 0.18, 0.15, 0.04));
    ps.addColorGradient(1, new Color4(0.22, 0.19, 0.16, 0), new Color4(0.2, 0.17, 0.14, 0));
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
    // Under the floor joists (2.32 m up), thickest just below them, as the previews'
    // haze was (rising from the ground to 2.3 m).
    const centre = new Vector3(
      (HALL.minX + HALL.maxX) / 2,
      HALL.floor + 1.75,
      (HALL.minZ + HALL.maxZ) / 2,
    );
    ps.emitter = centre;
    const hx = (HALL.maxX - HALL.minX) / 2 - 0.6,
      hz = (HALL.maxZ - HALL.minZ) / 2 - 0.8;
    ps.minEmitBox.set(-hx, -0.55, -hz);
    ps.maxEmitBox.set(hx, 0.3, hz);
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
    ps.addColorGradient(0, new Color4(0.2, 0.16, 0.13, 0));
    ps.addColorGradient(0.25, new Color4(0.2, 0.16, 0.13, 0.07));
    ps.addColorGradient(0.75, new Color4(0.18, 0.15, 0.12, 0.055));
    ps.addColorGradient(1, new Color4(0.18, 0.15, 0.12, 0));
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.emitRate = low ? 1.2 : 3;
    ps.preWarmCycles = 600;
    ps.preWarmStepOffset = 10;
    ps.start();
    return ps;
  }

  /**
   * The funeral's candles as one mesh: the first flame draws all of them as thin
   * instances, each at its own wick; the others go (and leave the area's list, so the
   * story's snuffing and relighting find the one that remains).
   */
  private instanceCandles(area: Area, random: () => number): void {
    const meshes = area.container.meshes.filter(
      (m): m is Mesh => FUNERAL_CANDLE.test(m.name) && "thinInstanceSetBuffer" in m,
    );
    if (meshes.length < 2) return;
    const source = meshes[0];
    for (const m of meshes) m.computeWorldMatrix(true);
    const inverse = source.getWorldMatrix().clone().invert();
    for (const m of meshes) {
      const box = m.getBoundingInfo().boundingBox;
      this.wicks.push({
        base: m.getWorldMatrix().multiply(inverse),
        foot: new Vector3(box.centerWorld.x, box.minimumWorld.y, box.centerWorld.z),
        phase: random() * 100,
        rate: 0.8 + random() * 0.5,
      });
    }
    this.wickMatrices = new Float32Array(16 * this.wicks.length);
    this.wicks.forEach((w, i) => w.base.copyToArray(this.wickMatrices!, i * 16));
    source.thinInstanceSetBuffer("matrix", this.wickMatrices, 16, false);
    source.thinInstanceRefreshBoundingInfo(false);
    this.sourceWorld = source.getWorldMatrix().clone();
    this.sourceInverse = inverse;
    for (const m of meshes.slice(1)) {
      area.container.meshes.splice(area.container.meshes.indexOf(m), 1);
      m.dispose(false, false);
    }
    this.candles = source;
  }

  private readonly wickA = new Matrix();
  private readonly wickB = new Matrix();
  private readonly wickTurn = new Quaternion();
  private readonly wickScale = new Vector3();

  /** Each candle wavers on its wick as the hall's flames do, out of step with the rest. */
  private updateCandles(t: number): void {
    const buffer = this.wickMatrices;
    if (!this.candles || !buffer || !this.candles.isEnabled()) return;
    const a = this.wickA,
      b = this.wickB;
    this.wicks.forEach((w, i) => {
      const p = w.phase,
        r = w.rate;
      const swell = 0.5 * Math.sin(t * 2.1 * r + p) + 0.3 * Math.sin(t * 4.7 * r + p * 1.7);
      const tremor = 0.12 * Math.sin(t * 23 * r + p * 3.1) * Math.sin(t * 7.3 + p);
      const gutter = Math.max(0, Math.sin(t * 0.37 * r + p * 0.5) - 0.92) * 6;
      const stretch = Math.max(0.45, 1 + 0.16 * swell + tremor - 0.35 * gutter);
      this.wickScale.set(1 - 0.07 * swell, stretch, 1 - 0.07 * swell);
      Quaternion.RotationYawPitchRollToRef(
        0,
        0.04 * Math.sin(t * 1.1 * r + p * 2.3),
        0.06 * Math.sin(t * 1.3 * r + p) + 0.1 * gutter,
        this.wickTurn,
      );
      // About the foot, in world axes: base, then shift to the foot, turn and stretch, back.
      Matrix.ComposeToRef(this.wickScale, this.wickTurn, Vector3.ZeroReadOnly, a);
      Matrix.TranslationToRef(-w.foot.x, -w.foot.y, -w.foot.z, b);
      b.multiplyToRef(a, a);
      a.addTranslationFromFloats(w.foot.x, w.foot.y, w.foot.z);
      // The instance matrices are relative to the source mesh: world_i * inverse(source).
      // The wavering is applied in world space before that.
      w.base.multiplyToRef(this.sourceWorld, b);
      b.multiplyToRef(a, b);
      b.multiplyToRef(this.sourceInverse, b);
      b.copyToArray(buffer, i * 16);
    });
    this.candles.thinInstanceBufferUpdated("matrix");
  }

  /** `level` is the room's light (1 full, falling as the corner incense burns down). */
  update(dt: number, level: number): void {
    this.time += dt;
    const t = this.time;
    this.updateCandles(t);
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
  const texture = new DynamicTexture(
    "T_hall_incense_wisp",
    { width: size, height: size },
    scene,
    false,
  );
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
