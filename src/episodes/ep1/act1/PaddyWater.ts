import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { MirrorTexture } from "@babylonjs/core/Materials/Textures/mirrorTexture";
import type { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Plane } from "@babylonjs/core/Maths/math.plane";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Game } from "@/core/Game";
import { seededRandom } from "@/audio/synth";
import { LakeWaves, rippleNormals } from "@/render/water";
import { WaterRipples } from "@/render/waterRipples";
import { wadeSplash } from "../audio/waterSounds";

/** The paddies' water level (village_nature.WATER_Z, Blender z = Babylon y). */
export const PADDY_WATER_Y = -0.1;
/** How far (m, past a mesh's bounds) the water mirrors tall things. */
const REFLECT_RANGE = 55;
/** Water surfaces of the village file and of the forest border past the walls. */
const SURFACES = /^(paddy_water|pond_water|pond_e_water|puddle_\d+|forest_border_(water|puddles))/;

/**
 * The village's standing water (the user, Nov 19: "make the water more detail and
 * realistic, also can be interact with user action"): the flooded paddies, the ponds and
 * the puddles. Dark, silty paddy water under a monsoon night: the palms and the tree
 * line mirrored in it (Medium and up), the wind's ripples drifting over it, every cell
 * of it pocked by rain, and rings running out from Sora's legs as she wades, with each
 * splashing step. Rings also run from anything else told to `disturb` it.
 */
export class PaddyWater {
  readonly material: PBRMaterial;
  private readonly waves: LakeWaves;
  private readonly ripples: WaterRipples;
  private readonly normals: RawTexture;
  private readonly mirror: MirrorTexture | null;
  private readonly splashes: StaticSound[] = [];
  private time = 0;
  private wake = 0;
  private idle = 0;
  private lastX = 0;
  private lastZ = 0;
  private readonly random = seededRandom(6242600);
  private readonly unsubscribe: () => void;
  /** What the mirror may show: the sky and far tree line always, tall things by distance. */
  private readonly always: AbstractMesh[] = [];
  private readonly tall: AbstractMesh[] = [];
  private reflectCount = 0;
  private reflectIn = 0;
  readonly meshes: AbstractMesh[];

  constructor(
    private readonly game: Game,
    private readonly groundAt: (x: number, z: number) => number,
  ) {
    const scene = game.scene;
    const material = (this.material = new PBRMaterial("M_paddy_water_live", scene));
    // Silty, tea-dark field water: almost black where it is deep, the sky in it.
    material.albedoColor = Color3.FromHexString("#1c221c").toLinearSpace();
    material.metallic = 0;
    material.roughness = 0.12;
    material.indexOfRefraction = 1.333;
    material.environmentIntensity = 0.9;
    material.maxSimultaneousLights = 8;
    material.backFaceCulling = false;
    this.normals = rippleNormals(scene, 730221, 512);
    this.normals.uScale = this.normals.vScale = 2.2;
    // Still water (the user, Nov 19: the water moved too much): a faint drift only.
    this.normals.level = 0.1;
    material.bumpTexture = this.normals;
    this.waves = new LakeWaves(material);
    this.waves.amplitude = 0.0015;
    this.ripples = new WaterRipples(material);

    this.meshes = scene.meshes.filter((m) => SURFACES.test(m.name));
    for (const mesh of this.meshes) {
      mesh.material = material;
      mesh.receiveShadows = true;
      mesh.isPickable = false;
    }

    const preset = game.preset.name;
    this.mirror =
      preset !== "low"
        ? new MirrorTexture(
            "paddy_reflection",
            preset === "ultra" ? 768 : preset === "high" ? 512 : 256,
            scene,
            true,
          )
        : null;
    if (this.mirror) {
      this.mirror.mirrorPlane = new Plane(0, -1, 0, PADDY_WATER_Y);
      // Only what stands tall over the fields: palms, trees, bamboo, the house, the
      // far tree line and the sky. Small things never show in it at night.
      for (const mesh of scene.meshes) {
        if (this.meshes.includes(mesh) || mesh.name.startsWith("col_") || !mesh.isVisible) continue;
        const box = mesh.getBoundingInfo().boundingBox;
        if (/sky|storm|far/.test(mesh.name)) this.always.push(mesh);
        else if (box.maximumWorld.y - box.minimumWorld.y > 2.5) this.tall.push(mesh);
      }
      this.reflectCount = preset === "ultra" ? 260 : preset === "high" ? 160 : 90;
      this.reflect();
      this.mirror.refreshRate = preset === "medium" ? 3 : 2;
      this.mirror.level = 0.85;
      material.reflectionTexture = this.mirror;
    }

    this.unsubscribe = game.bus.on("player:step", ({ surface, loudness }) => {
      if (surface !== "water") return;
      const feet = this.game.player.feet;
      this.disturb(feet.x, feet.z, 0.3 + loudness * 0.25);
      this.splash(loudness);
    });
    scene.onDisposeObservable.addOnce(() => this.dispose());
  }

  /** Loads the wading sounds (call once audio is up). */
  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    for (let i = 0; i < 4; i++)
      this.splashes.push(
        await audio.sound(
          `wade_splash_${i}`,
          audio.buffer(wadeSplash(rate, seededRandom(6242610 + i)), rate),
          "sfx",
          0,
        ),
      );
  }

  /** Starts a ring of waves on the water at (x, z). */
  disturb(x: number, z: number, strength = 0.6): void {
    this.ripples.add(x, z, strength);
  }

  /** Is Sora standing in water (her feet under its surface)? */
  wading(): boolean {
    const feet = this.game.player.feet;
    return feet.y < PADDY_WATER_Y - 0.04 && this.groundAt(feet.x, feet.z) < PADDY_WATER_Y - 0.06;
  }

  /** Each frame: waves, rain, and the wake round Sora's legs as she moves through water. */
  update(dt: number, rain: number): void {
    this.time += dt;
    this.waves.seconds = this.time;
    this.ripples.seconds = this.time;
    this.ripples.rain = rain;
    this.normals.uOffset = this.time * 0.0009;
    this.normals.vOffset = this.time * 0.0006;
    this.reflectIn -= dt;
    if (this.reflectIn <= 0) {
      this.reflectIn = 0.6;
      this.reflect();
    }
    const feet = this.game.player.feet;
    const moved = Math.hypot(feet.x - this.lastX, feet.z - this.lastZ);
    this.lastX = feet.x;
    this.lastZ = feet.z;
    if (!this.wading()) return;
    const speed = dt > 0 ? moved / dt : 0;
    this.wake -= dt;
    this.idle -= dt;
    if (speed > 0.25 && this.wake <= 0) {
      // The water piles against her shins and runs off behind as she pushes through.
      this.wake = 0.22;
      this.disturb(feet.x, feet.z, Math.min(0.3, 0.1 + speed * 0.07));
    } else if (speed <= 0.25 && this.idle <= 0) {
      // Standing still, her weight shifts: a slow ring now and then.
      this.idle = 1.3 + this.random() * 1.2;
      this.disturb(feet.x + (this.random() - 0.5) * 0.15, feet.z + (this.random() - 0.5) * 0.15, 0.07);
    }
  }

  /**
   * Picks what the water mirrors: the nearest tall things to the eye (a reflection in
   * paddy water shows only what stands close over it; the far tree line and the sky
   * stand in for the rest). Redrawing every tree in the village cost 8 fps on High.
   */
  private reflect(): void {
    if (!this.mirror) return;
    const eye = this.game.scene.activeCamera?.globalPosition;
    if (!eye) return;
    const near: [number, AbstractMesh][] = [];
    for (const mesh of this.tall) {
      if (!mesh.isEnabled() || !mesh.isVisible) continue;
      const sphere = mesh.getBoundingInfo().boundingSphere;
      const gap = Vector3.Distance(sphere.centerWorld, eye) - sphere.radiusWorld;
      if (gap < REFLECT_RANGE) near.push([gap, mesh]);
    }
    near.sort((a, b) => a[0] - b[0]);
    const list = this.always.slice();
    for (let i = 0; i < near.length && i < this.reflectCount; i++) list.push(near[i][1]);
    this.mirror.renderList = list;
  }

  private splash(loudness: number): void {
    if (!this.splashes.length) return;
    const sound = this.splashes[Math.floor(this.random() * this.splashes.length)];
    sound.volume = 0.16 + 0.32 * Math.min(1, loudness);
    sound.playbackRate = 0.9 + this.random() * 0.2;
    sound.play();
  }

  dispose(): void {
    this.unsubscribe();
    this.mirror?.dispose();
    for (const sound of this.splashes) sound.stop();
  }
}
