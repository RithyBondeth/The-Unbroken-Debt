import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { MirrorTexture } from "@babylonjs/core/Materials/Textures/mirrorTexture";
import { CreateGround } from "@babylonjs/core/Meshes/Builders/groundBuilder";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { Plane } from "@babylonjs/core/Maths/math.plane";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { LakeWaves, rippleNormals } from "@/render/water";
import type { Game } from "@/core/Game";
import { seededRandom } from "@/audio/synth";

/** Specular water, original tiled normals, GPU waves and a readable expanding threat wake. */
export class VillageWater {
  readonly material: PBRMaterial;
  readonly wards;
  readonly cellar;
  readonly wake;
  private readonly waves: LakeWaves;
  private readonly normal: RawTexture;
  private readonly mirror: MirrorTexture | null;
  private readonly floodWaves: LakeWaves;
  private readonly scum: Mesh;
  private readonly game: Game;
  private time = 0;
  constructor(game: Game) {
    this.game = game;
    const scene = game.scene;
    const material = (this.material = new PBRMaterial("M_ep3_lake_water", scene));
    material.albedoColor = Color3.FromHexString("#25312c").toLinearSpace();
    material.metallic = 0;
    material.roughness = 0.15;
    material.metallicF0Factor = 1;
    material.indexOfRefraction = 1.333;
    material.maxSimultaneousLights = 8;
    material.backFaceCulling = false;
    this.normal = rippleNormals(scene);
    this.normal.uScale = this.normal.vScale = 90;
    material.bumpTexture = this.normal;
    this.normal.level = 0.38;
    this.waves = new LakeWaves(material);
    // Openings beneath wards and cellar let pumping reveal the lower floor.
    const patches = [
      [-208, -12, -150, 150],
      [12, 132, -150, 150],
      [-12, 12, -150, -27.5],
      [-12, 12, 10, 150],
      [-12, 12, -18.5, -11],
      [-12, -7, -27.5, -18.5],
      [7, 12, -27.5, -18.5],
      [-1068, -208, -1000, 1000],
      [132, 1032, -1000, 1000],
      [-208, 132, -1000, -150],
      [-208, 132, 150, 1000],
    ].map(([x0, x1, z0, z1], i) => {
      const patch = CreateGround(
        "lake_patch_" + i,
        {
          width: x1 - x0,
          height: z1 - z0,
          subdivisions: Math.max(4, Math.min(80, Math.ceil(Math.max(x1 - x0, z1 - z0) / 2))),
        },
        scene,
      );
      patch.position.set((x0 + x1) / 2, 0, (z0 + z1) / 2);
      return patch;
    });
    const lake = Mesh.MergeMeshes(patches, true, true)!;
    lake.name = "tonle_sap_surface";
    lake.position.y = -0.08;
    lake.material = material;
    lake.isPickable = false;
    const inner = material.clone("M_ep3_flood_water");
    inner.roughness = 0.21;
    inner.metallicF0Factor = 1;
    inner.albedoColor = Color3.FromHexString("#253029").toLinearSpace();
    this.floodWaves = new LakeWaves(inner);
    this.wards = CreateGround(
      "ward_flood_water",
      { width: 23.7, height: 20.7, subdivisions: 24 },
      scene,
    );
    this.wards.position.set(0, 0.26, -0.5);
    this.wards.material = inner;
    this.wards.isPickable = false;
    this.cellar = CreateGround(
      "cellar_flood_water",
      { width: 13.8, height: 8.8, subdivisions: 12 },
      scene,
    );
    this.cellar.position.set(0, 0.35, -23);
    this.cellar.material = inner;
    this.cellar.isPickable = false;
    this.scum = CreateGround(
      "clinic_water_silt",
      { width: 23.7, height: 20.7, subdivisions: 1 },
      scene,
    );
    this.scum.position.set(0, 0.269, -0.5);
    this.scum.isPickable = false;
    const scumMat = new PBRMaterial("M_ep3_water_silt", scene);
    const scumTex = new DynamicTexture(
      "T_ep3_water_silt",
      { width: 1024, height: 1024 },
      scene,
      false,
    );
    const ctx = scumTex.getContext() as CanvasRenderingContext2D,
      rand = seededRandom(192033);
    ctx.clearRect(0, 0, 1024, 1024);
    for (let i = 0; i < 460; i++) {
      const x = rand() * 1024,
        y = rand() * 1024,
        edge = Math.min(x, 1024 - x, y, 1024 - y);
      if (edge > 140 && rand() > 0.13) continue;
      const radius = 2 + rand() * 22;
      const glow = ctx.createRadialGradient(x, y, 0, x, y, radius);
      glow.addColorStop(0, `rgba(73,66,37,${0.1 + rand() * 0.14})`);
      glow.addColorStop(1, "rgba(52,51,31,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
      ctx.fillStyle = rand() > 0.5 ? "rgba(62,46,25,.55)" : "rgba(107,93,57,.42)";
      ctx.beginPath();
      ctx.ellipse(x, y, 0.8 + rand() * 2.1, 0.3 + rand() * 0.8, rand() * 6.28, 0, 6.28);
      ctx.fill();
    }
    scumTex.hasAlpha = true;
    scumTex.update();
    scumMat.albedoTexture = scumTex;
    scumMat.useAlphaFromAlbedoTexture = true;
    scumMat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    scumMat.metallic = 0;
    scumMat.roughness = 0.94;
    scumMat.maxSimultaneousLights = 8;
    this.scum.material = scumMat;
    this.wake = [0, 1, 2].map((i) => {
      const ring = CreateTorus(
        "kanha_wake_" + i,
        { diameter: 1, thickness: 0.012, tessellation: 48 },
        scene,
      );
      const mat = new PBRMaterial("M_wake_" + i, scene);
      mat.albedoColor.set(0.3, 0.33, 0.28);
      mat.emissiveColor.set(0, 0, 0);
      mat.roughness = 0.55;
      mat.alpha = 0.5;
      ring.material = mat;
      ring.isPickable = false;
      ring.setEnabled(false);
      return ring;
    });
    this.mirror =
      game.preset.name !== "low"
        ? new MirrorTexture(
            "lake_reflection",
            game.preset.name === "ultra" ? 768 : game.preset.name === "medium" ? 256 : 512,
            scene,
            true,
          )
        : null;
    if (this.mirror) {
      this.mirror.mirrorPlane = new Plane(0, -1, 0, -0.08);
      this.mirror.renderList = scene.meshes.filter(
        (mesh) =>
          mesh !== lake &&
          mesh !== this.wards &&
          mesh !== this.cellar &&
          !this.wake.includes(mesh as typeof lake) &&
          mesh !== this.scum &&
          mesh.renderingGroupId === 0 &&
          !mesh.name.startsWith("col_"),
      );
      this.mirror.refreshRate = game.preset.name === "medium" ? 12 : 6;
      this.mirror.level = 1;
      material.reflectionTexture = this.mirror;
      inner.reflectionTexture = this.mirror;
    }
    scene.onDisposeObservable.addOnce(() => this.mirror?.dispose());
  }
  update(dt: number, target: number, wake: { x: number; z: number } | null, storm: boolean): void {
    this.time += dt;
    this.waves.seconds = this.time;
    this.floodWaves.seconds = this.time;
    this.floodWaves.amplitude = 0.006;
    this.waves.amplitude = storm ? 0.1 : 0.055;
    this.normal.uOffset = this.time * 0.0018;
    this.normal.vOffset = this.time * 0.001;
    this.cellar.position.y += (target - this.cellar.position.y) * Math.min(1, dt * 0.6);
    this.scum.position.y = this.wards.position.y + 0.009;
    if (this.mirror) {
      const feet = this.game.player.feet;
      const inside = Math.abs(feet.x) < 12 && feet.z < 10 && feet.z > -28;
      this.mirror.mirrorPlane.d = inside
        ? feet.z < -18.5
          ? this.cellar.position.y
          : this.wards.position.y
        : -0.08;
    }
    this.wake.forEach((ring, i) => {
      ring.setEnabled(wake !== null);
      if (!wake) return;
      const phase = (this.time * 0.35 + i / 3) % 1;
      ring.position.set(wake.x, 0.31, wake.z);
      ring.scaling.setAll(0.6 + phase * 2.4);
      (ring.material as PBRMaterial).alpha = (1 - phase) * 0.6;
    });
  }
}
