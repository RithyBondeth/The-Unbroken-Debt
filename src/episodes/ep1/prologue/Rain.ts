import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import "@babylonjs/core/Particles/particleSystemComponent";

const GLASS_PX = { width: 256, height: 512 };
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
  private readonly streaks: ParticleSystem;
  private readonly drops: Drop[] = [];
  private readonly trails: { x: number; y0: number; y1: number; age: number }[] = [];
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
    for (let i = 0; i < 70; i++) this.drops.push(this.newDrop(true));

    // Rain falling past outside: stretched streaks in a box beyond the glass.
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
    this.streaks = new ParticleSystem("rain_outside", 1400, scene);
    this.streaks.particleTexture = streak;
    this.streaks.emitter = new Vector3(centre.x, max.y + 1.5, max.z + 1.6);
    this.streaks.minEmitBox = new Vector3(-(max.x - min.x) / 2 - 1.2, 0, -1.2);
    this.streaks.maxEmitBox = new Vector3((max.x - min.x) / 2 + 1.2, 0, 1.6);
    this.streaks.direction1 = new Vector3(-0.08, -1, 0.04);
    this.streaks.direction2 = new Vector3(-0.02, -1, 0.1);
    this.streaks.minEmitPower = 8;
    this.streaks.maxEmitPower = 10;
    this.streaks.updateSpeed = 1 / 60;
    this.streaks.minLifeTime = 0.45;
    this.streaks.maxLifeTime = 0.6;
    this.streaks.emitRate = 1600;
    this.streaks.minSize = 0.012;
    this.streaks.maxSize = 0.018;
    this.streaks.minScaleY = 14;
    this.streaks.maxScaleY = 22;
    this.streaks.billboardMode = ParticleSystem.BILLBOARDMODE_STRETCHED;
    this.streaks.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    this.streaks.color1 = new Color4(0.55, 0.6, 0.68, 0.22);
    this.streaks.color2 = new Color4(0.5, 0.55, 0.62, 0.15);
    this.streaks.colorDead = new Color4(0.5, 0.55, 0.62, 0);
    this.streaks.preWarmCycles = 60;
    this.streaks.start();
  }

  /** `lightning` is the flash level, 0 to about 1. */
  update(dt: number, lightning: number): void {
    const flash = Math.min(1, lightning);
    this.material.emissiveColor.set(0.05 + flash * 0.9, 0.055 + flash * 0.95, 0.07 + flash);
    const a = 0.2 + flash * 0.6;
    this.streaks.color1.set(0.55 + flash * 0.4, 0.6 + flash * 0.4, 0.68 + flash * 0.3, a);
    this.streaks.color2.set(0.5 + flash * 0.4, 0.55 + flash * 0.4, 0.62 + flash * 0.3, a * 0.7);

    for (const drop of this.drops) {
      if (drop.speed === 0 && this.random() < dt * 0.05 * drop.r) drop.speed = 40 + drop.r * 25;
      drop.y += drop.speed * dt;
      if (drop.speed > 0) {
        drop.x += (this.random() - 0.5) * 12 * dt;
        const trail = this.trails.at(-1);
        if (this.random() < dt * 8)
          this.trails.push({ x: drop.x, y0: drop.y - 6, y1: drop.y, age: 0 });
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
      r: 1.2 + this.random() ** 3 * 4,
      speed: 0,
    };
  }

  private draw(): void {
    const ctx = this.texture.getContext() as CanvasRenderingContext2D;
    ctx.clearRect(0, 0, GLASS_PX.width, GLASS_PX.height);
    ctx.lineCap = "round";
    for (const trail of this.trails) {
      ctx.strokeStyle = `rgba(210,220,235,${0.22 * (1 - trail.age / 6)})`;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(trail.x, trail.y0);
      ctx.lineTo(trail.x, trail.y1);
      ctx.stroke();
    }
    for (const drop of this.drops) {
      const g = ctx.createRadialGradient(
        drop.x - drop.r * 0.3,
        drop.y - drop.r * 0.3,
        0,
        drop.x,
        drop.y,
        drop.r,
      );
      g.addColorStop(0, "rgba(255,255,255,0.75)");
      g.addColorStop(0.5, "rgba(190,205,225,0.25)");
      g.addColorStop(1, "rgba(120,135,160,0.5)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.ellipse(drop.x, drop.y, drop.r, drop.r * (drop.speed > 0 ? 1.3 : 1), 0, 0, Math.PI * 2);
      ctx.fill();
    }
    this.texture.update();
  }
}
