import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import "@babylonjs/core/Particles/particleSystemComponent";

/** About 340 px per metre over the studio window: a 3 mm drop is a pixel across. */
const GLASS_PX = { width: 512, height: 1024 };
/** The glass texture redraws this often: slow drops don't need every frame. */
const REDRAW_SECONDS = 1 / 15;

interface Drop {
  x: number;
  y: number;
  r: number;
  /** Pixels per second; 0 while the drop clings to the glass. */
  speed: number;
}

/**
 * The monsoon outside the studio window (Beat Sheet 3.1, P01: "Rain on the
 * window"): drops gathering and running down the inside of the view, and
 * streaks of rain falling past the shutters. Lightning lights both.
 */
export class Rain {
  private readonly texture: DynamicTexture;
  private readonly material: PBRMaterial;
  private readonly streaks: RainStreaks;
  private readonly drops: Drop[] = [];
  private readonly trails: { x: number; y0: number; y1: number; age: number }[] = [];
  /** Fine beads that cling and never run, drawn once and copied under each redraw. */
  private readonly mist: HTMLCanvasElement | OffscreenCanvas;
  private sinceDraw = 0;

  constructor(
    scene: Scene,
    glass: AbstractMesh,
    private readonly random: () => number = Math.random,
  ) {
    const box = glass.getBoundingInfo().boundingBox;
    const min = box.minimumWorld;
    const max = box.maximumWorld;
    const centre = box.centerWorld;

    // Water on the glass: a plane a few millimetres inside it, facing the room.
    const sheet = CreatePlane(
      "rain_on_glass",
      { width: max.x - min.x, height: max.y - min.y, sideOrientation: 2 },
      scene,
    );
    sheet.position.set(centre.x, centre.y, min.z - 0.006);
    sheet.isPickable = false;
    this.texture = new DynamicTexture("T_rain_on_glass", GLASS_PX, scene, false);
    this.texture.hasAlpha = true;
    this.material = new PBRMaterial("M_rain_on_glass", scene);
    this.material.albedoTexture = this.texture;
    this.material.useAlphaFromAlbedoTexture = true;
    this.material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    this.material.albedoColor = new Color3(0.75, 0.8, 0.85);
    this.material.emissiveTexture = this.texture;
    this.material.roughness = 0.05;
    this.material.metallic = 0;
    this.material.backFaceCulling = false;
    sheet.material = this.material;
    for (let i = 0; i < 140; i++) this.drops.push(this.newDrop(true));
    this.mist = this.paintMist();

    // Rain falling past outside: stretched streaks in a box beyond the glass.
    this.streaks = new RainStreaks(scene, 1400, 1600);
    this.streaks.system.emitter = new Vector3(centre.x, max.y + 1.5, max.z + 1.6);
    this.streaks.system.minEmitBox = new Vector3(-(max.x - min.x) / 2 - 1.2, 0, -1.2);
    this.streaks.system.maxEmitBox = new Vector3((max.x - min.x) / 2 + 1.2, 0, 1.6);
  }

  /** `lightning` is the flash level, 0 to about 1. */
  update(dt: number, lightning: number): void {
    const flash = Math.min(1, lightning);
    this.material.emissiveColor.set(0.05 + flash * 0.9, 0.055 + flash * 0.95, 0.07 + flash);
    this.streaks.light(flash);

    for (const drop of this.drops) {
      // Only the larger drops grow heavy enough to run.
      if (drop.speed === 0 && drop.r > 1.8 && this.random() < dt * 0.03 * drop.r)
        drop.speed = 60 + drop.r * 40;
      drop.y += drop.speed * dt;
      if (drop.speed > 0) {
        drop.x += (this.random() - 0.5) * 20 * dt;
        const trail = this.trails.at(-1);
        if (this.random() < dt * 8)
          this.trails.push({ x: drop.x, y0: drop.y - 10, y1: drop.y, age: 0 });
        else if (trail && Math.abs(trail.x - drop.x) < 2) trail.y1 = drop.y;
      }
    }
    for (let i = this.drops.length - 1; i >= 0; i--) {
      if (this.drops[i].y > GLASS_PX.height + 10) this.drops[i] = this.newDrop(false);
    }
    for (const trail of this.trails) trail.age += dt;
    while (this.trails.length && this.trails[0].age > 6) this.trails.shift();

    this.sinceDraw += dt;
    if (this.sinceDraw >= REDRAW_SECONDS) {
      this.sinceDraw = 0;
      this.draw();
    }
  }

  dispose(): void {
    this.streaks.dispose();
    this.texture.dispose();
    this.material.dispose();
  }

  private newDrop(anywhere: boolean): Drop {
    return {
      x: this.random() * GLASS_PX.width,
      y: anywhere ? this.random() * GLASS_PX.height : -10 - this.random() * 40,
      // 2–8 mm: mostly small, a few heavy enough to run.
      r: 0.7 + this.random() ** 3 * 2.2,
      speed: 0,
    };
  }

  /**
   * Water on glass at night is nearly invisible: each bead shows as a pin of
   * reflected light on its upper side and a faint dark rim below, where it bends
   * the dark street. No outline, or the drops read as bubbles.
   */
  private bead(
    ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
    x: number,
    y: number,
    r: number,
    stretch = 1,
  ): void {
    ctx.fillStyle = "rgba(8,10,16,0.32)";
    ctx.beginPath();
    ctx.ellipse(x, y + r * 0.25, r, r * stretch, 0, 0, Math.PI);
    ctx.fill();
    ctx.fillStyle = "rgba(150,165,190,0.16)";
    ctx.beginPath();
    ctx.ellipse(x, y, r * 0.95, r * 0.95 * stretch, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(235,242,255,0.7)";
    ctx.beginPath();
    ctx.arc(x - r * 0.35, y - r * 0.4 * stretch, Math.max(0.45, r * 0.28), 0, Math.PI * 2);
    ctx.fill();
  }

  private paintMist(): HTMLCanvasElement | OffscreenCanvas {
    const canvas =
      typeof OffscreenCanvas !== "undefined"
        ? new OffscreenCanvas(GLASS_PX.width, GLASS_PX.height)
        : Object.assign(document.createElement("canvas"), GLASS_PX);
    const ctx = canvas.getContext("2d") as CanvasRenderingContext2D;
    // Denser towards the bottom, where water gathers on the frame.
    for (let i = 0; i < 2600; i++) {
      const y = GLASS_PX.height * Math.sqrt(this.random());
      this.bead(ctx, this.random() * GLASS_PX.width, y, 0.35 + this.random() ** 2 * 0.7);
    }
    return canvas;
  }

  private draw(): void {
    const ctx = this.texture.getContext() as CanvasRenderingContext2D;
    ctx.clearRect(0, 0, GLASS_PX.width, GLASS_PX.height);
    ctx.drawImage(this.mist, 0, 0);
    ctx.lineCap = "round";
    // A running drop leaves a clear path through the mist, edged by a wet line.
    ctx.globalCompositeOperation = "destination-out";
    ctx.strokeStyle = "rgba(0,0,0,0.9)";
    ctx.lineWidth = 3;
    for (const trail of this.trails) {
      ctx.beginPath();
      ctx.moveTo(trail.x, trail.y0);
      ctx.lineTo(trail.x, trail.y1);
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
    for (const trail of this.trails) {
      ctx.strokeStyle = `rgba(200,212,230,${0.14 * (1 - trail.age / 6)})`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(trail.x, trail.y0);
      ctx.lineTo(trail.x, trail.y1);
      ctx.stroke();
    }
    for (const drop of this.drops)
      this.bead(ctx, drop.x, drop.y, drop.r, drop.speed > 0 ? 1.35 : 1);
    this.texture.update();
  }
}

/**
 * Falling rain as stretched streaks (S7 look): place the emitter box, and call
 * `light` with the lightning level so the rain flashes white with the sky.
 */
export class RainStreaks {
  readonly system: ParticleSystem;

  constructor(scene: Scene, capacity: number, perSecond: number) {
    const streak = new DynamicTexture("T_rain_streak", { width: 8, height: 64 }, scene, false);
    const ctx = streak.getContext();
    const gradient = ctx.createLinearGradient(0, 0, 0, 64);
    gradient.addColorStop(0, "rgba(255,255,255,0)");
    gradient.addColorStop(0.5, "rgba(255,255,255,0.9)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(3, 0, 2, 64);
    streak.hasAlpha = true;
    streak.update();
    const ps = new ParticleSystem("rain_streaks", capacity, scene);
    ps.particleTexture = streak;
    ps.direction1 = new Vector3(-0.08, -1, 0.04);
    ps.direction2 = new Vector3(-0.02, -1, 0.1);
    ps.minEmitPower = 8;
    ps.maxEmitPower = 10;
    ps.updateSpeed = 1 / 60;
    ps.minLifeTime = 0.45;
    ps.maxLifeTime = 0.6;
    ps.emitRate = perSecond;
    ps.minSize = 0.012;
    ps.maxSize = 0.018;
    ps.minScaleY = 14;
    ps.maxScaleY = 22;
    ps.billboardMode = ParticleSystem.BILLBOARDMODE_STRETCHED;
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.color1 = new Color4(0.55, 0.6, 0.68, 0.22);
    ps.color2 = new Color4(0.5, 0.55, 0.62, 0.15);
    ps.colorDead = new Color4(0.5, 0.55, 0.62, 0);
    ps.preWarmCycles = 60;
    ps.start();
    this.system = ps;
  }

  /**
   * The streaks are unlit, so their colour stands for the light on them: `flash`
   * (lightning, 0 to 1) and `warm` (a flame close by, 0 to 1) over a `base` level
   * (1 behind a lit window; lower out in a dark night).
   */
  light(flash: number, warm = 0, base = 1): void {
    const a = 0.2 * Math.min(1, base * 1.2) + flash * 0.6 + warm * 0.3;
    this.system.color1.set(
      0.55 * base + flash * 0.4 + warm * 0.75,
      0.6 * base + flash * 0.4 + warm * 0.48,
      0.68 * base + flash * 0.3 + warm * 0.2,
      a,
    );
    this.system.color2.set(
      0.5 * base + flash * 0.4 + warm * 0.65,
      0.55 * base + flash * 0.4 + warm * 0.4,
      0.62 * base + flash * 0.3 + warm * 0.16,
      a * 0.7,
    );
  }

  dispose(): void {
    this.system.dispose();
  }
}
