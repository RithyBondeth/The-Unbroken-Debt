import { Constants } from "@babylonjs/core/Engines/constants";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Scene } from "@babylonjs/core/scene";
import { seededRandom } from "@/audio/synth";
import { FLAME_COLOR } from "@/render/renderSetup";

export type FlameGroup = "shelf" | "desk" | "altar" | "tea";

interface CandleEmitter {
  group: FlameGroup;
  anchor: Vector3;
  node: TransformNode | null;
  flame: Mesh;
  halo: Mesh;
  scale: number;
  phase: number;
  lit: boolean;
  /** Seconds left of curling grey extinguished-wick smoke right after snuffing out. */
  snuffSmokeLeft: number;
  smokeAcc: number;
}

interface IncenseEmitter {
  group: FlameGroup;
  anchor: Vector3;
  node: TransformNode | null;
  emberHalo: Mesh;
  phase: number;
  lit: boolean;
  smokeAcc: number;
}

interface SmokeWisp {
  mesh: Mesh;
  active: boolean;
  age: number;
  life: number;
  origin: Vector3;
  driftX: number;
  driftZ: number;
  curlFreq: number;
  curlAmp: number;
  phase: number;
  riseSpeed: number;
  baseSize: number;
  endSize: number;
  peakAlpha: number;
  spin: number;
}

/**
 * Photorealistic animated candle flames, warm glow halos, pulsing incense embers,
 * and continuous curling smoke plumes across the entire Studio scene:
 * - Every candle (shelf, writing desk, 3 altar candles) has a teardrop textured
 *   flame tongue + additive warm corona + subtle heat wisp, bending in cold
 *   ghostly draughts and releasing a thick grey smoke trail when snuffed out.
 * - Every Khmer incense stick (2 on front shelf + 5 on back altar) has a
 *   breathing glowing red-orange ember halo + sinuous rising smoke ribbons.
 */
export class StudioFlamesAndSmoke {
  private readonly candles: CandleEmitter[] = [];
  private readonly incenses: IncenseEmitter[] = [];
  private readonly wisps: SmokeWisp[] = [];
  private readonly flameMat: PBRMaterial;
  private readonly haloMat: PBRMaterial;
  private readonly emberMat: PBRMaterial;
  private readonly smokeMat: PBRMaterial;
  private readonly smokeTex: DynamicTexture;
  private readonly altarCandleLight: PointLight | null = null;
  private readonly altarIncenseLight: PointLight | null = null;
  private readonly studioIncenseLight: PointLight | null = null;
  private altarCandleBase = 0.72;
  private altarIncenseBase = 0.16;
  private studioIncenseBase = 0.11;
  private altarLit = true;
  private shelfLit = true;
  private power = 1;
  private draught = 0;
  private draughtX = 0.6;
  private draughtZ = 0.8;
  /** Unnatural spirit-omen pull on the altar incense smoke (pulls horizontally toward Sora/doorway). */
  private omenSmoke = 0;
  private omenDirX = 0.7;
  private omenDirZ = 0.7;
  private time = 0;

  constructor(private readonly scene: Scene) {
    this.flameMat = this.makeFlameMaterial();
    this.haloMat = this.makeHaloMaterial("M_studio_flame_halo", "255, 168, 66", 0.58);
    this.emberMat = this.makeHaloMaterial("M_studio_ember_halo", "255, 86, 24", 0.75);
    this.smokeTex = this.makeSmokeTexture();

    // 1. Discover candle markers (shelf, desk, 3 altar candles)
    const addCandle = (
      name: string,
      group: FlameGroup,
      node: TransformNode | null,
      pos: Vector3,
      scale: number,
      phase: number,
    ) => {
      const flame = CreatePlane(
        `vfx_flame_${name}`,
        { width: 0.022 * scale, height: 0.044 * scale },
        scene,
      );
      flame.position.copyFrom(pos).addInPlaceFromFloats(0, 0.008 * scale, 0);
      flame.billboardMode = Mesh.BILLBOARDMODE_Y;
      flame.material = this.flameMat;
      flame.isPickable = false;

      const halo = CreatePlane(`vfx_halo_${name}`, { size: 0.11 * scale }, scene);
      halo.position.copyFrom(pos).addInPlaceFromFloats(0, 0.01 * scale, 0);
      halo.billboardMode = Mesh.BILLBOARDMODE_ALL;
      halo.material = this.haloMat;
      halo.isPickable = false;

      this.candles.push({
        group,
        anchor: pos.clone(),
        node,
        flame,
        halo,
        scale,
        phase,
        lit: true,
        snuffSmokeLeft: 0,
        smokeAcc: Math.random() * 0.4,
      });
    };

    const findNode = (n: string) =>
      scene.getTransformNodeByName(n) ?? scene.getMeshByName(n) ?? null;

    const shelfNode = findNode("light_flame_candle");
    if (shelfNode) {
      shelfNode.computeWorldMatrix(true);
      addCandle("shelf", "shelf", shelfNode, shelfNode.getAbsolutePosition(), 1.05, 0.4);
    }
    const deskNode = findNode("light_flame_desk_candle");
    if (deskNode) {
      deskNode.computeWorldMatrix(true);
      addCandle("desk", "desk", deskNode, deskNode.getAbsolutePosition(), 0.88, 2.1);
    }

    const altarCandlePositions: Vector3[] = [];
    for (let k = 0; k < 3; k++) {
      const mk = findNode(`marker_altar_candle_${k}`);
      if (!mk) continue;
      mk.computeWorldMatrix(true);
      const p = mk.getAbsolutePosition();
      altarCandlePositions.push(p.clone());
      addCandle(`altar_${k}`, "altar", mk, p, 0.84, 3.2 + k * 1.9);
    }

    // Dedicated warm flicker light shared by the 3 altar candles (goes out when altar falls!)
    if (altarCandlePositions.length) {
      const center = altarCandlePositions
        .reduce((acc, p) => acc.add(p), Vector3.Zero())
        .scale(1 / altarCandlePositions.length);
      const light = new PointLight(
        "altar_candles_glow",
        center.add(new Vector3(0, 0.03, 0.06)),
        scene,
      );
      light.diffuse = FLAME_COLOR.clone();
      light.intensity = this.altarCandleBase;
      light.range = 2.6;
      light.shadowEnabled = false;
      this.altarCandleLight = light;
    }

    // 2. Discover incense tip markers (2 on front studio shelf + 5 on back bedroom altar)
    const addIncense = (name: string, group: FlameGroup, mk: TransformNode, phase: number) => {
      mk.computeWorldMatrix(true);
      const pos = mk.getAbsolutePosition();
      const emberHalo = CreatePlane(`vfx_ember_${name}`, { size: 0.024 }, scene);
      emberHalo.position.copyFrom(pos);
      emberHalo.billboardMode = Mesh.BILLBOARDMODE_ALL;
      emberHalo.material = this.emberMat;
      emberHalo.isPickable = false;
      this.incenses.push({
        group,
        anchor: pos.clone(),
        node: mk,
        emberHalo,
        phase,
        lit: true,
        smokeAcc: Math.random() * 0.22,
      });
    };

    const studioIncensePositions: Vector3[] = [];
    for (let k = 0; k < 2; k++) {
      const mk = findNode(`marker_studio_incense_${k}`);
      if (!mk) continue;
      mk.computeWorldMatrix(true);
      studioIncensePositions.push(mk.getAbsolutePosition().clone());
      addIncense(`studio_${k}`, "shelf", mk, 0.7 + k * 2.3);
    }
    if (studioIncensePositions.length) {
      const center = studioIncensePositions
        .reduce((acc, p) => acc.add(p), Vector3.Zero())
        .scale(1 / studioIncensePositions.length);
      const glow = new PointLight(
        "studio_incense_glow",
        center.add(new Vector3(0, 0.02, 0.03)),
        scene,
      );
      glow.diffuse = new Color3(1, 0.44, 0.14);
      glow.intensity = this.studioIncenseBase;
      glow.range = 0.65;
      glow.shadowEnabled = false;
      this.studioIncenseLight = glow;
    }
    const altarIncensePositions: Vector3[] = [];
    for (let k = 0; k < 5; k++) {
      const mk = findNode(`marker_altar_incense_${k}`);
      if (!mk) continue;
      mk.computeWorldMatrix(true);
      altarIncensePositions.push(mk.getAbsolutePosition().clone());
      addIncense(`altar_${k}`, "altar", mk, 1.4 + k * 1.3);
    }

    // Subtle warm ember micro-glow right above the altar incense bowl
    if (altarIncensePositions.length) {
      const center = altarIncensePositions
        .reduce((acc, p) => acc.add(p), Vector3.Zero())
        .scale(1 / altarIncensePositions.length);
      const glow = new PointLight(
        "altar_incense_glow",
        center.add(new Vector3(0, 0.02, 0.03)),
        scene,
      );
      glow.diffuse = new Color3(1, 0.45, 0.14);
      glow.intensity = this.altarIncenseBase;
      glow.range = 0.85;
      glow.shadowEnabled = false;
      this.altarIncenseLight = glow;
    }

    // 3. Lightweight pooled curling smoke wisps sharing ONE single WebGPU material (mesh.visibility fades each wisp!)
    this.smokeMat = new PBRMaterial("M_studio_smoke", scene);
    this.smokeMat.albedoTexture = this.smokeTex;
    this.smokeMat.opacityTexture = this.smokeTex;
    this.smokeMat.emissiveTexture = this.smokeTex;
    this.smokeMat.emissiveColor = new Color3(0.32, 0.33, 0.35);
    this.smokeMat.disableLighting = true;
    this.smokeMat.alpha = 1;
    this.smokeMat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    this.smokeMat.disableDepthWrite = true;
    this.smokeMat.zOffset = -1;

    const poolSize = 84;
    for (let i = 0; i < poolSize; i++) {
      const mesh = CreatePlane(`vfx_smoke_${i}`, { size: 1 }, scene);
      mesh.billboardMode = Mesh.BILLBOARDMODE_ALL;
      mesh.material = this.smokeMat;
      mesh.isPickable = false;
      mesh.isVisible = false;
      mesh.visibility = 0;
      this.wisps.push({
        mesh,
        active: false,
        age: 0,
        life: 3,
        origin: Vector3.Zero(),
        driftX: 0,
        driftZ: 0,
        curlFreq: 2,
        curlAmp: 0.03,
        phase: 0,
        riseSpeed: 0.16,
        baseSize: 0.02,
        endSize: 0.15,
        peakAlpha: 0.24,
        spin: 0,
      });
    }

    // Pre-seed gentle rising smoke plumes above every lit incense stick so frame 1 already looks alive!
    for (const inc of this.incenses) {
      for (let step = 0; step < 5; step++) {
        this.spawnWisp(
          inc.anchor.add(new Vector3(0, 0.004, 0)),
          {
            life: 3.4,
            rise: 0.15,
            baseSize: 0.015,
            endSize: 0.13,
            alpha: 0.24,
            curlAmp: 0.032,
          },
          step * 0.55,
        );
      }
    }
  }

  /** Meshes to reveal briefly during warmup so smoke/flame shaders never compile mid-scare. */
  warmupMeshes(): AbstractMesh[] {
    return [
      ...this.candles.flatMap((c) => [c.flame, c.halo]),
      ...this.incenses.map((inc) => inc.emberHalo),
      ...this.wisps.slice(0, 2).map((w) => w.mesh),
    ];
  }

  /** Sets house power factor (0 during blackout, 1 normal) so desk/altar flames dim cleanly. */
  setPower(power: number): void {
    this.power = Math.max(0, Math.min(1, power));
  }

  /** Applies a temporary cold ghostly draught (or open balcony wind) that bends flames & smoke. */
  pulseDraught(strength: number, dirX = 0.6, dirZ = 0.8): void {
    this.draught = Math.max(this.draught, Math.min(1, strength));
    this.draughtX = dirX;
    this.draughtZ = dirZ;
  }

  /**
   * Asian folk omen: pulls the altar incense smoke unnaturally sideways/horizontally
   * toward a spirit or the doorway instead of rising straight up.
   */
  setAltarOmenSmoke(strength: number, dirX = 0.7, dirZ = 0.7): void {
    this.omenSmoke = Math.max(0, Math.min(1, strength));
    const len = Math.hypot(dirX, dirZ) || 1;
    this.omenDirX = dirX / len;
    this.omenDirZ = dirZ / len;
  }

  /** Snuffs out a single altar candle by index (0, 1, or 2) with curling grey wick smoke. */
  extinguishAltarCandle(index: number, emitSnuffSmoke = true): void {
    const altarCandles = this.candles.filter((c) => c.group === "altar");
    const target = altarCandles[index];
    if (!target || !target.lit) return;
    target.lit = false;
    target.flame.isVisible = false;
    target.halo.isVisible = false;
    if (emitSnuffSmoke) target.snuffSmokeLeft = 4.6;
    const remaining = altarCandles.filter((c) => c.lit).length;
    if (remaining === 0) {
      this.altarLit = false;
      if (this.altarCandleLight) this.altarCandleLight.intensity = 0;
    } else if (this.altarCandleLight) {
      this.altarCandleBase = 0.72 * (remaining / Math.max(1, altarCandles.length));
    }
  }

  /** Snuffs out a candle/incense group with a realistic burst of curling extinguished-wick smoke. */
  extinguish(group: FlameGroup, emitSnuffSmoke = true): void {
    for (const c of this.candles) {
      if (c.group !== group || !c.lit) continue;
      c.lit = false;
      c.flame.isVisible = false;
      c.halo.isVisible = false;
      if (emitSnuffSmoke) c.snuffSmokeLeft = 4.8;
    }
    for (const inc of this.incenses) {
      if (inc.group !== group || !inc.lit) continue;
      inc.lit = false;
      inc.emberHalo.isVisible = false;
    }
    if (group === "altar") {
      this.altarLit = false;
      if (this.altarCandleLight) this.altarCandleLight.intensity = 0;
      if (this.altarIncenseLight) this.altarIncenseLight.intensity = 0;
    }
    if (group === "shelf") {
      this.shelfLit = false;
      if (this.studioIncenseLight) this.studioIncenseLight.intensity = 0;
    }
  }

  update(dt: number, balconyOpenFactor = 0): void {
    this.time += dt;
    const t = this.time;
    this.draught = Math.max(0, this.draught - dt * 0.48);
    const wind = Math.max(this.draught, balconyOpenFactor * 0.65);

    // 1. Animate candle flames, warm coronas, and extinguished-wick smoke trails
    for (const c of this.candles) {
      const visible = c.lit && this.power > 0.35;
      c.flame.isVisible = visible;
      c.halo.isVisible = visible;
      if (c.node && !c.node.isDisposed()) {
        c.node.computeWorldMatrix(true);
        c.anchor.copyFrom(c.node.getAbsolutePosition());
      }
      if (visible) {
        const flick =
          0.9 +
          0.11 * Math.sin(t * 11.4 + c.phase) +
          0.07 * Math.sin(t * 23.7 + c.phase * 2.1) +
          wind * 0.22 * Math.sin(t * 33 + c.phase);
        const sway = (0.003 + wind * 0.011) * Math.sin(t * (7.5 + wind * 14) + c.phase);
        c.flame.position.set(
          c.anchor.x + sway + wind * this.draughtX * 0.008,
          c.anchor.y + 0.008 * c.scale,
          c.anchor.z + wind * this.draughtZ * 0.008,
        );
        c.flame.scaling.set(0.92 + (1 - flick) * 0.35, flick, 1);
        c.halo.position.copyFrom(c.flame.position);
        const hScale = 0.88 + 0.18 * flick;
        c.halo.scaling.set(hScale, hScale, 1);

        // Gentle hot heat wisp rising occasionally from lit candles
        c.smokeAcc += dt;
        if (c.smokeAcc >= 0.48) {
          c.smokeAcc = 0;
          this.spawnWisp(c.anchor.add(new Vector3(0, 0.028, 0)), {
            life: 2.0,
            rise: 0.15,
            baseSize: 0.015,
            endSize: 0.085,
            alpha: 0.095,
            curlAmp: 0.02,
          });
        }
      } else if (c.snuffSmokeLeft > 0) {
        c.snuffSmokeLeft = Math.max(0, c.snuffSmokeLeft - dt);
        c.smokeAcc += dt;
        const interval = 0.095 + (1 - c.snuffSmokeLeft / 4.8) * 0.14;
        if (c.smokeAcc >= interval) {
          c.smokeAcc = 0;
          this.spawnWisp(c.anchor, {
            life: 2.8,
            rise: 0.17,
            baseSize: 0.016,
            endSize: 0.135,
            alpha: 0.26 * Math.min(1, c.snuffSmokeLeft / 1.4),
            curlAmp: 0.036,
          });
        }
      }
    }

    // 2. Animate altar candle & incense micro-lights
    if (this.altarLit) {
      const f = 0.84 + 0.11 * Math.sin(t * 8.3 + 1.1) + 0.05 * Math.sin(t * 19.2);
      if (this.altarCandleLight) {
        this.altarCandleLight.intensity = this.altarCandleBase * f * this.power;
      }
      if (this.altarIncenseLight) {
        this.altarIncenseLight.intensity =
          this.altarIncenseBase * (0.85 + 0.15 * Math.sin(t * 3.1)) * this.power;
      }
    }
    if (this.shelfLit && this.studioIncenseLight) {
      this.studioIncenseLight.intensity =
        this.studioIncenseBase * (0.85 + 0.15 * Math.sin(t * 3.4 + 1.2)) * this.power;
    }

    // 3. Animate glowing incense embers & continuous sinuous curling incense smoke!
    for (const inc of this.incenses) {
      const active = inc.lit && this.power > 0.2;
      inc.emberHalo.isVisible = active;
      if (!active) continue;
      if (inc.node && !inc.node.isDisposed()) {
        inc.node.computeWorldMatrix(true);
        inc.anchor.copyFrom(inc.node.getAbsolutePosition());
        inc.emberHalo.position.copyFrom(inc.anchor);
      }
      const breath =
        0.78 + 0.28 * Math.sin(t * 2.8 + inc.phase) + 0.1 * Math.sin(t * 7.1 + inc.phase);
      inc.emberHalo.scaling.set(breath, breath, 1);

      inc.smokeAcc += dt;
      if (inc.smokeAcc >= (inc.group === "altar" && this.omenSmoke > 0.2 ? 0.13 : 0.18)) {
        inc.smokeAcc = 0;
        const omen = inc.group === "altar" ? this.omenSmoke : 0;
        this.spawnWisp(inc.anchor.add(new Vector3(0, 0.004, 0)), {
          life: omen > 0.2 ? 2.8 : 3.4,
          rise: 0.15 * (1 - omen * 0.72),
          baseSize: 0.015,
          endSize: 0.135,
          alpha: omen > 0.2 ? 0.3 : 0.24,
          curlAmp: 0.032 * (1 - omen * 0.65),
          driftX: omen > 0.05 ? this.omenDirX * 0.26 * omen : undefined,
          driftZ: omen > 0.05 ? this.omenDirZ * 0.26 * omen : undefined,
        });
      }
    }

    // 4. Advance all pooled smoke wisps in sinuous helical upward curls
    for (const w of this.wisps) {
      if (!w.active) continue;
      w.age += dt;
      const p = w.age / w.life;
      if (p >= 1) {
        w.active = false;
        w.mesh.isVisible = false;
        w.mesh.visibility = 0;
        continue;
      }
      const y = w.origin.y + w.age * w.riseSpeed;
      const curl = w.curlAmp * Math.pow(p, 0.75);
      const sx =
        Math.sin(w.age * w.curlFreq + w.phase) * curl +
        (w.driftX + wind * this.draughtX * 0.22) * w.age;
      const sz =
        Math.cos(w.age * w.curlFreq * 0.85 + w.phase * 1.3) * curl +
        (w.driftZ + wind * this.draughtZ * 0.22) * w.age;
      w.mesh.position.set(w.origin.x + sx, y, w.origin.z + sz);
      const szNow = w.baseSize + (w.endSize - w.baseSize) * Math.pow(p, 0.85);
      w.mesh.scaling.set(szNow, szNow * (1.1 + 0.35 * p), 1);
      // Smooth bell fade-in and gossamer fade-out
      const fadeIn = Math.min(1, p / 0.16);
      const fadeOut = Math.pow(1 - p, 1.35);
      w.mesh.visibility = w.peakAlpha * fadeIn * fadeOut;
    }
  }

  private spawnWisp(
    at: Vector3,
    opts: {
      life: number;
      rise: number;
      baseSize: number;
      endSize: number;
      alpha: number;
      curlAmp: number;
      driftX?: number;
      driftZ?: number;
    },
    initialAge = 0,
  ): void {
    const slot = this.wisps.find((w) => !w.active);
    if (!slot) return;
    slot.active = true;
    slot.age = initialAge;
    slot.life = opts.life * (0.85 + Math.random() * 0.3);
    slot.origin.copyFrom(at);
    slot.riseSpeed = opts.rise * (0.88 + Math.random() * 0.24);
    slot.baseSize = opts.baseSize;
    slot.endSize = opts.endSize * (0.85 + Math.random() * 0.3);
    slot.peakAlpha = opts.alpha;
    slot.curlAmp = opts.curlAmp * (0.8 + Math.random() * 0.45);
    slot.curlFreq = 1.8 + Math.random() * 1.5;
    slot.phase = Math.random() * Math.PI * 2;
    slot.driftX = opts.driftX ?? (Math.random() - 0.5) * 0.022;
    slot.driftZ = opts.driftZ ?? (Math.random() - 0.5) * 0.022;
    slot.spin = (Math.random() - 0.5) * 0.6;
    slot.mesh.position.copyFrom(at);
    slot.mesh.scaling.set(opts.baseSize, opts.baseSize, 1);
    slot.mesh.isVisible = true;
    slot.mesh.visibility = 0;
  }

  // ------------------------------------------------ procedural photorealistic textures

  private makeFlameMaterial(): PBRMaterial {
    const tex = new DynamicTexture(
      "T_studio_candle_flame",
      { width: 128, height: 256 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    c.clearRect(0, 0, 128, 256);

    // Outer soft orange-amber teardrop flame aura
    const outer = c.createRadialGradient(64, 154, 6, 64, 146, 56);
    outer.addColorStop(0, "rgba(255, 224, 130, 0.98)");
    outer.addColorStop(0.35, "rgba(255, 142, 34, 0.85)");
    outer.addColorStop(0.7, "rgba(215, 72, 12, 0.32)");
    outer.addColorStop(1, "rgba(180, 40, 0, 0)");
    c.save();
    c.beginPath();
    c.moveTo(64, 24);
    c.bezierCurveTo(96, 86, 108, 152, 92, 198);
    c.bezierCurveTo(80, 226, 48, 226, 36, 198);
    c.bezierCurveTo(20, 152, 32, 86, 64, 24);
    c.closePath();
    c.fillStyle = outer;
    c.fill();
    c.restore();

    // Inner incandescent white-yellow teardrop core
    const core = c.createRadialGradient(64, 168, 3, 64, 155, 26);
    core.addColorStop(0, "rgba(255, 255, 246, 1)");
    core.addColorStop(0.55, "rgba(255, 232, 165, 0.9)");
    core.addColorStop(1, "rgba(255, 165, 60, 0)");
    c.fillStyle = core;
    c.beginPath();
    c.ellipse(64, 156, 18, 46, 0, 0, Math.PI * 2);
    c.fill();

    // Realistic faint blue oxygenation collar right at the charred wick base
    const blue = c.createRadialGradient(64, 206, 2, 64, 206, 18);
    blue.addColorStop(0, "rgba(92, 152, 255, 0.65)");
    blue.addColorStop(1, "rgba(60, 110, 255, 0)");
    c.fillStyle = blue;
    c.beginPath();
    c.ellipse(64, 206, 16, 12, 0, 0, Math.PI * 2);
    c.fill();

    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial("M_studio_candle_flame_vfx", this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveTexture = tex;
    mat.emissiveColor = new Color3(1.5, 1.3, 1.0);
    mat.disableLighting = true;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.alphaMode = Constants.ALPHA_ADD;
    mat.disableDepthWrite = true;
    return mat;
  }

  private makeHaloMaterial(name: string, rgb: string, peak: number): PBRMaterial {
    const tex = new DynamicTexture(`T_${name}`, 128, this.scene, true);
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    const g = c.createRadialGradient(64, 64, 2, 64, 64, 62);
    g.addColorStop(0, `rgba(${rgb}, ${peak})`);
    g.addColorStop(0.32, `rgba(${rgb}, ${peak * 0.42})`);
    g.addColorStop(0.68, `rgba(${rgb}, ${peak * 0.1})`);
    g.addColorStop(1, `rgba(${rgb}, 0)`);
    c.fillStyle = g;
    c.fillRect(0, 0, 128, 128);
    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial(name, this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveTexture = tex;
    mat.emissiveColor = Color3.White();
    mat.disableLighting = true;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.alphaMode = Constants.ALPHA_ADD;
    mat.disableDepthWrite = true;
    return mat;
  }

  private makeSmokeTexture(): DynamicTexture {
    const tex = new DynamicTexture("T_studio_smoke_wisp", 128, this.scene, true);
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    const rand = seededRandom(5107);
    c.clearRect(0, 0, 128, 128);
    // Soft multi-lobe turbulent smoke cloud (never a hard circular dot!)
    for (let i = 0; i < 14; i++) {
      const x = 64 + (rand() - 0.5) * 44;
      const y = 64 + (rand() - 0.5) * 48;
      const r = 18 + rand() * 24;
      const g = c.createRadialGradient(x, y, 2, x, y, r);
      g.addColorStop(0, `rgba(205, 212, 214, ${0.14 + rand() * 0.12})`);
      g.addColorStop(0.6, `rgba(182, 190, 194, ${0.06 + rand() * 0.05})`);
      g.addColorStop(1, "rgba(170, 178, 182, 0)");
      c.fillStyle = g;
      c.beginPath();
      c.arc(x, y, r, 0, Math.PI * 2);
      c.fill();
    }
    tex.hasAlpha = true;
    tex.update();
    return tex;
  }
}
