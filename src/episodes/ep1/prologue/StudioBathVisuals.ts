import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Scene } from "@babylonjs/core/scene";
import { seededRandom } from "@/audio/synth";
import { runtime } from "../data/studioScares";

interface RippleRing {
  mesh: Mesh;
  age: number;
  delay: number;
  active: boolean;
}

function featherRectEdges(c: CanvasRenderingContext2D, w: number, h: number, margin = 18): void {
  // Erase only a soft border along each of the 4 rectangular frame edges using destination-out
  // (never wipes the interior like chained destination-in!).
  c.save();
  c.globalCompositeOperation = "destination-out";
  const strips: [number, number, number, number, number, number, number, number][] = [
    [0, 0, margin, 0, 0, 0, margin, h],
    [w, 0, w - margin, 0, w - margin, 0, margin, h],
    [0, 0, 0, margin, 0, 0, w, margin],
    [0, h, 0, h - margin, 0, h - margin, w, margin],
  ];
  for (const [x0, y0, x1, y1, rx, ry, rw, rh] of strips) {
    const g = c.createLinearGradient(x0, y0, x1, y1);
    g.addColorStop(0, "rgba(0,0,0,1)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    c.fillStyle = g;
    c.fillRect(rx, ry, rw, rh);
  }
  c.restore();
}

/**
 * Draws an anatomically proportioned human forearm, wrist, palm, thumb, and four
 * jointed slender fingers into a 2D canvas path so both the dark creeping arm shadow
 * and the damp condensation handprint read like a real human arm and hand (never blobs).
 */
function traceHumanArmAndHand(
  c: CanvasRenderingContext2D,
  ox: number,
  oy: number,
  scale: number,
  angle: number,
): void {
  c.save();
  c.translate(ox, oy);
  c.rotate(angle);
  c.scale(scale, scale);

  // Forearm emerging cleanly past the lower-left frame edge tapering into a narrow human wrist
  c.beginPath();
  c.moveTo(-210, 340);
  c.bezierCurveTo(-132, 208, -68, 118, -32, 48);
  c.bezierCurveTo(-40, 22, -48, -12, -46, -42); // outer ulnar edge of palm
  // Pinky finger
  c.bezierCurveTo(-56, -78, -64, -112, -59, -126);
  c.bezierCurveTo(-55, -135, -45, -134, -42, -122);
  c.bezierCurveTo(-38, -104, -33, -76, -28, -56);
  // Ring finger
  c.bezierCurveTo(-30, -96, -34, -142, -28, -162);
  c.bezierCurveTo(-24, -172, -12, -172, -10, -158);
  c.bezierCurveTo(-8, -134, -8, -88, -6, -64);
  // Middle finger (longest)
  c.bezierCurveTo(-4, -108, -2, -164, 4, -184);
  c.bezierCurveTo(9, -196, 22, -195, 24, -180);
  c.bezierCurveTo(25, -154, 21, -102, 19, -66);
  // Index finger (slightly splayed)
  c.bezierCurveTo(28, -106, 38, -150, 48, -166);
  c.bezierCurveTo(54, -175, 65, -171, 64, -156);
  c.bezierCurveTo(60, -132, 47, -86, 39, -52);
  // Web of thumb -> thumb angling naturally outward
  c.bezierCurveTo(47, -34, 58, -38, 76, -54);
  c.bezierCurveTo(96, -72, 114, -76, 122, -67);
  c.bezierCurveTo(128, -59, 122, -46, 106, -32);
  c.bezierCurveTo(86, -14, 64, 4, 52, 24);
  // Heel of palm (thenar) -> inner wrist -> forearm past lower edge
  c.bezierCurveTo(44, 48, 32, 66, 22, 82);
  c.bezierCurveTo(6, 140, -38, 240, -108, 360);
  c.closePath();
  c.restore();
}

/**
 * Photorealistic runtime visual effects for the 1932 Phnom Penh bathroom and its
 * psychological haunts: running cold tap water, expanding dark cistern ripples,
 * a realistic human arm & hand shadow creeping across the foxed antique mirror,
 * a lingering damp anatomical handprint in the mist, and wet bare footprints
 * leading out toward the studio after Yay Mey's call.
 */
export class StudioBathVisuals {
  readonly mirrorSteam: Mesh;
  readonly mirrorFigure: Mesh;
  private readonly mirrorFigureMat: PBRMaterial;
  readonly mirrorHandprint: Mesh;
  private readonly mirrorHandprintMat: PBRMaterial;
  private readonly mirrorBasePos: { x: number; y: number; z: number };
  private readonly faucetStream: Mesh;
  private readonly faucetSplash: Mesh;
  private readonly faucetMat: PBRMaterial;
  private readonly ripples: RippleRing[] = [];
  private readonly footprints: Mesh[] = [];
  private faucetRunning = false;
  private figureAlpha = 0;
  private armSlideT = -1;
  private handprintTarget = 0;
  private handprintAlpha = 0;
  private clock = 0;

  constructor(
    private readonly scene: Scene,
    anchors: {
      mirrorAt: Vector3;
      faucetAt: Vector3;
      tankAt: Vector3;
    },
  ) {
    this.mirrorBasePos = {
      x: anchors.mirrorAt.x,
      y: anchors.mirrorAt.y,
      z: anchors.mirrorAt.z + 0.002,
    };

    // 0. Subtle humid antique mercury-glass condensation veil so the mirror catches room light
    //    and gives real optical contrast behind the creeping human arm shadow & handprint.
    this.mirrorSteam = CreatePlane("bath_mirror_steam", { width: 0.52, height: 0.68 }, scene);
    this.mirrorSteam.position.set(
      anchors.mirrorAt.x,
      anchors.mirrorAt.y,
      anchors.mirrorAt.z + 0.001,
    );
    this.mirrorSteam.rotation.y = Math.PI;
    this.mirrorSteam.material = this.makeMirrorSteamMaterial();
    this.mirrorSteam.isPickable = false;

    // 1. Realistic human arm & hand shadow creeping across the misted antique mirror glass
    this.mirrorFigureMat = this.makeMirrorArmShadowMaterial();
    this.mirrorFigure = CreatePlane("bath_mirror_apparition", { width: 0.51, height: 0.67 }, scene);
    this.mirrorFigure.position.set(
      this.mirrorBasePos.x,
      this.mirrorBasePos.y,
      this.mirrorBasePos.z + 0.0015,
    );
    this.mirrorFigure.rotation.y = Math.PI;
    this.mirrorFigure.material = this.mirrorFigureMat;
    this.mirrorFigure.isPickable = false;
    this.mirrorFigure.isVisible = false;

    // 2. Anatomically realistic steamed-glass condensation handprint & dragged fingertip trails
    this.mirrorHandprintMat = this.makeHandprintMaterial();
    this.mirrorHandprint = CreatePlane(
      "bath_mirror_handprint",
      { width: 0.51, height: 0.67 },
      scene,
    );
    this.mirrorHandprint.position.set(
      anchors.mirrorAt.x,
      anchors.mirrorAt.y,
      anchors.mirrorAt.z + 0.005,
    );
    this.mirrorHandprint.rotation.y = Math.PI;
    this.mirrorHandprint.material = this.mirrorHandprintMat;
    this.mirrorHandprint.isPickable = false;
    this.mirrorHandprint.isVisible = false;

    // 3. Running cold water stream from left brass faucet into porcelain basin
    this.faucetMat = new PBRMaterial("M_bath_faucet_stream", scene);
    this.faucetMat.albedoColor = new Color3(0.76, 0.84, 0.86);
    this.faucetMat.emissiveColor = new Color3(0.06, 0.08, 0.09);
    this.faucetMat.metallic = 0;
    this.faucetMat.roughness = 0.06;
    this.faucetMat.alpha = 0.44;
    this.faucetMat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    this.faucetMat.disableDepthWrite = true;

    const streamLen = 0.175;
    this.faucetStream = CreateCylinder(
      "bath_faucet_stream",
      { diameterTop: 0.0065, diameterBottom: 0.0095, height: streamLen, tessellation: 10 },
      scene,
    );
    this.faucetStream.position.set(
      anchors.faucetAt.x,
      anchors.faucetAt.y - streamLen / 2,
      anchors.faucetAt.z,
    );
    this.faucetStream.material = this.faucetMat;
    this.faucetStream.isPickable = false;
    this.faucetStream.isVisible = false;

    this.faucetSplash = CreatePlane("bath_faucet_splash", { size: 0.055 }, scene);
    this.faucetSplash.position.set(
      anchors.faucetAt.x,
      anchors.faucetAt.y - streamLen + 0.005,
      anchors.faucetAt.z,
    );
    this.faucetSplash.rotation.x = Math.PI / 2;
    this.faucetSplash.material = this.makeRippleMaterial("M_bath_faucet_splash", 0.36);
    this.faucetSplash.isPickable = false;
    this.faucetSplash.isVisible = false;

    // 4. Concentric ripples on the dark tiled water cistern (1 shared material + mesh.visibility!)
    const sharedRippleMat = this.makeRippleMaterial("M_bath_tank_ripple", 1);
    for (let i = 0; i < 3; i++) {
      const mesh = CreatePlane(`bath_tank_ripple_${i}`, { size: 0.68 }, scene);
      mesh.position.set(anchors.tankAt.x, anchors.tankAt.y + 0.003 + i * 0.0004, anchors.tankAt.z);
      mesh.rotation.x = Math.PI / 2;
      mesh.material = sharedRippleMat;
      mesh.isPickable = false;
      mesh.isVisible = false;
      mesh.visibility = 0;
      this.ripples.push({ mesh, age: 0, delay: i * 0.48, active: false });
    }

    // 5. Wet bare footprints leading from the bathroom doorway across the back room
    this.buildFootprints();
  }

  /** Meshes to reveal momentarily during scene warmup so shaders never compile mid-scare. */
  warmupMeshes(): AbstractMesh[] {
    return [
      this.mirrorSteam,
      this.mirrorFigure,
      this.mirrorHandprint,
      this.faucetStream,
      this.faucetSplash,
      ...this.ripples.map((r) => r.mesh),
      ...this.footprints,
    ];
  }

  setFaucetRunning(on: boolean): void {
    this.faucetRunning = on;
    this.faucetStream.isVisible = on;
    this.faucetSplash.isVisible = on;
  }

  setMirrorFigureAlpha(alpha: number): void {
    this.figureAlpha = Math.max(0, Math.min(1, alpha));
    this.mirrorFigureMat.alpha = this.figureAlpha;
    this.mirrorFigure.isVisible = this.figureAlpha > 0.01;
  }

  /** Plays the eerie arm-shadow creep & downward glass-drag animation across the mirror. */
  startMirrorArmCreep(): void {
    this.armSlideT = 0;
    this.mirrorFigure.isVisible = true;
  }

  revealHandprint(immediate = false): void {
    this.handprintTarget = 0.86;
    if (immediate) {
      this.handprintAlpha = this.handprintTarget;
      this.mirrorHandprintMat.alpha = this.handprintAlpha;
      this.mirrorHandprint.isVisible = true;
    }
  }

  triggerTankRipples(): void {
    for (const r of this.ripples) {
      r.age = -r.delay;
      r.active = true;
      r.mesh.scaling.set(0.14, 0.14, 1);
      r.mesh.visibility = 0;
      r.mesh.isVisible = false;
    }
  }

  showWetFootprints(visible: boolean): void {
    for (const fp of this.footprints) fp.isVisible = visible;
  }

  update(dt: number): void {
    this.clock += dt;
    if (this.faucetRunning) {
      const pulse = 0.88 + 0.12 * Math.sin(this.clock * 31) + 0.06 * Math.sin(this.clock * 53);
      this.faucetStream.scaling.set(pulse, 1, 2 - pulse);
      this.faucetMat.alpha = 0.38 + 0.08 * Math.sin(this.clock * 41);
      const sp = 0.82 + 0.28 * Math.abs(Math.sin(this.clock * 23));
      this.faucetSplash.scaling.set(sp, sp, 1);
      this.faucetSplash.rotation.y = this.clock * 2.4;
    }

    // Animate the human arm shadow creeping up/across the misted mirror, trembling, then dragging down
    if (this.armSlideT >= 0) {
      this.armSlideT += dt;
      const t = this.armSlideT;
      if (t < 0.42) {
        // Reaches up smoothly from the lower-left glass edge
        const k = 1 - (1 - t / 0.42) ** 3;
        this.mirrorFigure.position.set(
          this.mirrorBasePos.x + (1 - k) * 0.05,
          this.mirrorBasePos.y - (1 - k) * 0.045,
          this.mirrorBasePos.z + 0.0015,
        );
        this.setMirrorFigureAlpha(0.95 * k);
      } else if (t < 1.32) {
        // Pressed flat and trembling subtly against the steamed glass behind Sora
        const tremble = Math.sin(t * 36) * 0.0018;
        this.mirrorFigure.position.set(
          this.mirrorBasePos.x + tremble,
          this.mirrorBasePos.y + tremble * 0.5,
          this.mirrorBasePos.z + 0.0015,
        );
        this.setMirrorFigureAlpha(0.96);
      } else if (t < 1.85) {
        // Drags slowly downward and vanishes into the lingering steamed handprint
        const k = (t - 1.32) / 0.53;
        this.mirrorFigure.position.set(
          this.mirrorBasePos.x,
          this.mirrorBasePos.y - k * 0.06,
          this.mirrorBasePos.z + 0.0015,
        );
        this.setMirrorFigureAlpha(0.96 * (1 - k));
      } else {
        this.armSlideT = -1;
        this.setMirrorFigureAlpha(0);
        this.mirrorFigure.position.set(
          this.mirrorBasePos.x,
          this.mirrorBasePos.y,
          this.mirrorBasePos.z + 0.0015,
        );
      }
    }

    if (this.handprintAlpha < this.handprintTarget) {
      this.handprintAlpha = Math.min(this.handprintTarget, this.handprintAlpha + dt * 0.48);
      this.mirrorHandprintMat.alpha = this.handprintAlpha;
      this.mirrorHandprint.isVisible = this.handprintAlpha > 0.01;
    }

    for (const r of this.ripples) {
      if (!r.active) continue;
      r.age += dt;
      if (r.age < 0) continue;
      const life = 2.1;
      const p = r.age / life;
      if (p >= 1) {
        r.active = false;
        r.mesh.isVisible = false;
        r.mesh.visibility = 0;
        continue;
      }
      r.mesh.isVisible = true;
      const scale = 0.12 + 0.92 * Math.pow(p, 0.72);
      r.mesh.scaling.set(scale, scale, 1);
      r.mesh.visibility = Math.sin(p * Math.PI) * (1 - p) * 0.42;
    }
  }

  // ------------------------------------------------ photorealistic mirror steam, arm shadow & handprint

  /** Soft antique silvered-glass reflection & monsoon humidity mist so the mirror reads as
   *  real damp lit glass (giving crisp realistic contrast for the creeping human arm shadow). */
  private makeMirrorSteamMaterial(): PBRMaterial {
    const tex = new DynamicTexture(
      "T_bath_mirror_steam",
      { width: 512, height: 640 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    const rand = seededRandom(19325);
    c.clearRect(0, 0, 512, 640);

    // Warm-cool overhead bulb bounce diffused across the humid mercury glass
    const sheen = c.createRadialGradient(256, 235, 30, 256, 290, 340);
    sheen.addColorStop(0, "rgba(176, 186, 178, 0.34)");
    sheen.addColorStop(0.55, "rgba(132, 144, 138, 0.20)");
    sheen.addColorStop(1, "rgba(65, 76, 72, 0.06)");
    c.fillStyle = sheen;
    c.fillRect(0, 0, 512, 640);

    // Subtle organic mottled bathroom steam patches
    for (let i = 0; i < 42; i++) {
      const x = 60 + rand() * 392;
      const y = 70 + rand() * 500;
      const r = 38 + rand() * 88;
      const g = c.createRadialGradient(x, y, 4, x, y, r);
      g.addColorStop(0, `rgba(195, 206, 200, ${0.04 + rand() * 0.05})`);
      g.addColorStop(1, "rgba(180, 192, 186, 0)");
      c.fillStyle = g;
      c.beginPath();
      c.arc(x, y, r, 0, Math.PI * 2);
      c.fill();
    }

    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial("M_bath_mirror_steam", this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveTexture = tex;
    mat.emissiveColor = new Color3(0.55, 0.58, 0.56);
    mat.disableLighting = true;
    mat.alpha = 0.85;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.backFaceCulling = false;
    mat.zOffset = -1;
    return mat;
  }

  private makeMirrorArmShadowMaterial(): PBRMaterial {
    const tex = new DynamicTexture(
      "T_bath_mirror_arm_shadow",
      { width: 512, height: 640 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    const rand = seededRandom(19329);
    c.clearRect(0, 0, 512, 640);

    // Subtle warm-cool mist diffusion behind the shadow (organic, non-circular)
    for (let i = 0; i < 18; i++) {
      const gx = 120 + rand() * 280;
      const gy = 170 + rand() * 300;
      const gr = 70 + rand() * 115;
      const g = c.createRadialGradient(gx, gy, 8, gx, gy, gr);
      g.addColorStop(0, `rgba(170, 178, 172, ${0.04 + rand() * 0.04})`);
      g.addColorStop(1, "rgba(120, 130, 126, 0)");
      c.fillStyle = g;
      c.beginPath();
      c.arc(gx, gy, gr, 0, Math.PI * 2);
      c.fill();
    }

    // Photorealistic multi-pass optical shadow penumbra (ZERO white cutout outline!):
    // wide diffuse ambient occlusion -> medium optical penumbra -> soft shadow umbra
    const passes: [blur: number, alpha: number, ox: number, oy: number, s: number][] = [
      [34, 0.32, 246, 418, 1.1],
      [20, 0.44, 252, 412, 1.07],
      [10, 0.62, 256, 408, 1.05],
      [4.5, 0.72, 258, 406, 1.04],
    ];
    for (const [blur, alpha, ox, oy, s] of passes) {
      c.save();
      c.filter = `blur(${blur}px)`;
      traceHumanArmAndHand(c, ox, oy, s, 0.22);
      c.fillStyle = `rgba(4, 6, 7, ${alpha})`;
      c.fill();
      c.restore();
    }

    // Fine tarnished mirror grain over the shadow so it sits INSIDE the antique glass
    for (let i = 0; i < 450; i++) {
      c.fillStyle = `rgba(18, 22, 20, ${0.04 + rand() * 0.06})`;
      c.fillRect(rand() * 512, rand() * 640, 2 + rand() * 4, 2 + rand() * 4);
    }

    // Soft 20px frame-edge feather ONLY (keeps the full human forearm & hand 100% intact!)
    featherRectEdges(c, 512, 640, 20);

    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial("M_bath_mirror_arm_shadow", this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveTexture = tex;
    mat.emissiveColor = new Color3(0.55, 0.58, 0.56);
    mat.disableLighting = true;
    mat.alpha = 0;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.backFaceCulling = false;
    mat.zOffset = -2;
    return mat;
  }

  private makeHandprintMaterial(): PBRMaterial {
    const tex = new DynamicTexture(
      "T_bath_mirror_handprint",
      { width: 512, height: 640 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    const rand = seededRandom(19331);
    c.clearRect(0, 0, 512, 640);

    // 1. Irregular, organic mottled monsoon steam patches across the cold antique glass (never a hard spotlight circle!)
    for (let i = 0; i < 34; i++) {
      const fx = 110 + rand() * 300;
      const fy = 150 + rand() * 340;
      const fr = 65 + rand() * 115;
      const g = c.createRadialGradient(fx, fy, 10, fx, fy, fr);
      g.addColorStop(0, `rgba(182, 194, 188, ${0.05 + rand() * 0.055})`);
      g.addColorStop(0.65, `rgba(158, 170, 166, ${0.02 + rand() * 0.025})`);
      g.addColorStop(1, "rgba(145, 158, 155, 0)");
      c.fillStyle = g;
      c.beginPath();
      c.arc(fx, fy, fr, 0, Math.PI * 2);
      c.fill();
    }

    // 2. Softly diffused, organic human arm & hand shadow lingering in the mist (no cutout border!)
    for (const [blur, alpha, ox, oy, s] of [
      [28, 0.34, 248, 416, 1.07],
      [15, 0.48, 253, 410, 1.05],
      [6.5, 0.64, 256, 406, 1.03],
    ]) {
      c.save();
      c.filter = `blur(${blur}px)`;
      traceHumanArmAndHand(c, ox, oy, s, 0.22);
      c.fillStyle = `rgba(6, 9, 10, ${alpha})`;
      c.fill();
      c.restore();
    }

    // 3. Natural damp skin-print breakup across the palm & fingers so it feels touched, not painted
    for (let i = 0; i < 45; i++) {
      const mx = 175 + rand() * 185;
      const my = 225 + rand() * 220;
      const mr = 8 + rand() * 20;
      const g = c.createRadialGradient(mx, my, 1, mx, my, mr);
      g.addColorStop(0, `rgba(145, 156, 152, ${0.04 + rand() * 0.05})`);
      g.addColorStop(1, "rgba(145, 156, 152, 0)");
      c.fillStyle = g;
      c.beginPath();
      c.arc(mx, my, mr, 0, Math.PI * 2);
      c.fill();
    }

    // 4. Subtle dark wet finger-drag streaks wiped downward through the steam from the fingertips
    c.save();
    c.filter = "blur(3px)";
    for (const [fx, fy, len] of [
      [212, 266, 78],
      [248, 232, 96],
      [290, 220, 108],
      [330, 246, 86],
    ]) {
      const grad = c.createLinearGradient(fx, fy, fx - 8, fy + len);
      grad.addColorStop(0, "rgba(8, 12, 13, 0.56)");
      grad.addColorStop(0.55, "rgba(16, 22, 22, 0.26)");
      grad.addColorStop(1, "rgba(28, 36, 36, 0)");
      c.strokeStyle = grad;
      c.lineWidth = 10;
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(fx, fy);
      c.lineTo(fx - 7, fy + len);
      c.stroke();
    }
    c.restore();

    // Soft 22px frame-edge feather so the forearm blends naturally into the dark wooden frame
    featherRectEdges(c, 512, 640, 22);

    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial("M_bath_mirror_handprint", this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveTexture = tex;
    mat.emissiveColor = new Color3(0.58, 0.62, 0.6);
    mat.disableLighting = true;
    mat.alpha = 0;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.backFaceCulling = false;
    mat.zOffset = -3;
    return mat;
  }

  private makeRippleMaterial(name: string, alpha: number): PBRMaterial {
    const tex = new DynamicTexture(`T_${name}`, 256, this.scene, true);
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    c.clearRect(0, 0, 256, 256);
    const g = c.createRadialGradient(128, 128, 72, 128, 128, 122);
    g.addColorStop(0, "rgba(180, 205, 200, 0)");
    g.addColorStop(0.55, "rgba(195, 218, 212, 0.72)");
    g.addColorStop(0.72, "rgba(225, 238, 232, 0.92)");
    g.addColorStop(0.86, "rgba(160, 184, 180, 0.35)");
    g.addColorStop(1, "rgba(140, 165, 162, 0)");
    c.fillStyle = g;
    c.fillRect(0, 0, 256, 256);
    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial(name, this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveColor = new Color3(0.28, 0.34, 0.34);
    mat.disableLighting = true;
    mat.alpha = alpha;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.zOffset = -2;
    return mat;
  }

  private buildFootprints(): void {
    const tex = new DynamicTexture(
      "T_bath_wet_footprint",
      { width: 128, height: 256 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    c.clearRect(0, 0, 128, 256);
    const wet = (x: number, y: number, rx: number, ry: number, rot = 0, a = 0.72) => {
      c.save();
      c.translate(x, y);
      c.rotate(rot);
      const g = c.createRadialGradient(0, 0, 2, 0, 0, Math.max(rx, ry));
      g.addColorStop(0, `rgba(14, 15, 16, ${a})`);
      g.addColorStop(0.7, `rgba(18, 20, 21, ${a * 0.65})`);
      g.addColorStop(1, "rgba(18, 20, 21, 0)");
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
      c.fill();
      c.restore();
    };
    wet(64, 198, 23, 32, 0, 0.74);
    wet(76, 152, 13, 30, -0.1, 0.56);
    wet(62, 102, 28, 30, 0.08, 0.78);
    wet(39, 54, 10, 14, -0.08, 0.72);
    wet(56, 48, 7.5, 12, 0, 0.68);
    wet(70, 52, 7, 11, 0.06, 0.64);
    wet(82, 60, 6.5, 10, 0.12, 0.58);
    wet(92, 72, 5.5, 8.5, 0.18, 0.5);
    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial("M_bath_wet_footprint", this.scene);
    mat.albedoColor = new Color3(0.04, 0.045, 0.05);
    mat.opacityTexture = tex;
    mat.metallic = 0;
    mat.roughness = 0.07;
    mat.alpha = 0.68;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.zOffset = -2;

    const steps: [x: number, y: number, yaw: number, mirrorX: number][] = [
      [2.44, 13.78, 0.36, 1],
      [2.18, 13.24, 0.42, -1],
      [1.96, 12.66, 0.34, 1],
      [1.68, 12.06, 0.38, -1],
      [1.46, 11.42, 0.32, 1],
      [1.18, 10.72, 0.35, -1],
      [0.98, 10.05, 0.25, 1],
    ];
    steps.forEach(([bx, by, yaw, flip], i) => {
      const fp = CreatePlane(`bath_wet_footprint_${i}`, { width: 0.12, height: 0.25 }, this.scene);
      const pos = runtime(bx, by, 0.004);
      fp.position.copyFrom(pos);
      fp.rotation.set(Math.PI / 2, yaw, 0);
      fp.scaling.x = flip;
      fp.material = mat;
      fp.isPickable = false;
      fp.isVisible = false;
      this.footprints.push(fp);
    });
  }
}
