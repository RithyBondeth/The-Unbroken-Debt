import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { MirrorTexture } from "@babylonjs/core/Materials/Textures/mirrorTexture";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Plane } from "@babylonjs/core/Maths/math.plane";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Game } from "@/core/Game";
import { LakeWaves, rippleNormals } from "@/render/water";

/** The area's water materials: the lotus pond (and the cups of water) and the Sunken Tank. */
export const WATER_MATERIALS = ["M_ep2_pond_water", "M_ep2_water"];
/** The pond's surface height and centre (runtime), from tools/areas/pagoda_pond.py. */
export const POND = { y: -0.38, x: 0, z: -28.2 };
/** Metres of water per repeat of the ripple map. */
const RIPPLE_TILE = 6;

/**
 * Gives the water meshes planar UVs from their world positions, before batching: the export
 * drops UVs from untextured materials, and the ripple map needs them.
 */
export function waterUvs(container: AssetContainer): void {
  for (const mesh of container.meshes) {
    if (!(mesh instanceof Mesh) || !WATER_MATERIALS.includes(mesh.material?.name ?? "")) continue;
    const positions = mesh.getVerticesData(VertexBuffer.PositionKind);
    if (!positions) continue;
    if (mesh.geometry && mesh.geometry.meshes.length > 1) mesh.makeGeometryUnique();
    const world = mesh.computeWorldMatrix(true);
    const p = new Vector3();
    const uvs = new Float32Array((positions.length / 3) * 2);
    for (let i = 0, j = 0; i < positions.length; i += 3, j += 2) {
      Vector3.TransformCoordinatesFromFloatsToRef(
        positions[i],
        positions[i + 1],
        positions[i + 2],
        world,
        p,
      );
      uvs[j] = p.x / RIPPLE_TILE;
      uvs[j + 1] = p.z / RIPPLE_TILE;
    }
    mesh.setVerticesData(VertexBuffer.UVKind, uvs, false, 2);
  }
}

/** Plant materials whose crowns and trunks show in the pond. */
const REFLECTED =
  /^(M_forest_leaf|M_ep2_bark|M_forest_moss|M_bamboo|M_bamboo_leaves|M_forest_far_cards)$/;

/**
 * The pond and the tank as old, still, tea-black water: a slow swell, ripples drifting across
 * it, and (above the Low preset) the sky, the moon and the black crowns round it mirrored and
 * broken up on the ripples. The flat sheet the area exports read as a painted floor.
 */
export class PagodaWater {
  private readonly waves: LakeWaves[] = [];
  private readonly normal: RawTexture;
  private readonly mirror: MirrorTexture | null = null;
  private time = 0;

  constructor(game: Game) {
    const scene = game.scene;
    this.normal = rippleNormals(scene, 412071);
    this.normal.uScale = this.normal.vScale = 1;
    this.normal.level = 0.32;
    const pond = this.surface("M_ep2_pond_surface", "#16150e", 0.008);
    // The tank lies still: no swell (its lotus pads float a few millimetres up), only ripples.
    const tank = this.surface("M_ep2_tank_surface", "#12140e", 0);
    const pondMeshes: AbstractMesh[] = [];
    for (const mesh of scene.meshes) {
      const name = mesh.material?.name;
      if (name === "M_ep2_pond_water") {
        mesh.material = pond;
        pondMeshes.push(mesh);
      } else if (name === "M_ep2_water") mesh.material = tank;
    }
    if (game.preset.name === "low") return;
    const preset = game.preset.name;
    this.mirror = new MirrorTexture(
      "ep2_pond_reflection",
      preset === "ultra" ? 768 : preset === "medium" ? 256 : 512,
      scene,
      true,
    );
    this.mirror.mirrorPlane = new Plane(0, -1, 0, POND.y);
    const centre = new Vector3(POND.x, POND.y, POND.z);
    // Only what is tall enough to show in the water from the banks: the sky, the moon, the
    // crowns and trunks round the pond, the far forest, and the big buildings nearby.
    // Kept short: every mesh here is drawn again each time the reflection refreshes.
    this.mirror.renderList = scene.meshes.filter((mesh) => {
      if (pondMeshes.includes(mesh) || mesh.name.startsWith("col_") || !mesh.isVisible)
        return false;
      if (/^(pagoda_sky_dome|pagoda_moon_disc|ep2_far_forest)/.test(mesh.name)) return true;
      const sphere = mesh.getBoundingInfo().boundingSphere;
      const distance = Vector3.Distance(sphere.centerWorld, centre);
      // Only what stands tall over the water shows in it: crowns and trunks round the banks,
      // the library on its posts, the bridge; not the stones, offerings and grass.
      if (sphere.centerWorld.y < 1.5) return false;
      if (REFLECTED.test(mesh.material?.name ?? "")) return distance < 32 && sphere.radiusWorld > 3;
      return distance < 18 && sphere.radiusWorld > 2.5;
    });
    this.mirror.refreshRate = preset === "medium" ? 12 : 6;
    this.mirror.level = 0.9;
    pond.reflectionTexture = this.mirror;
    scene.onDisposeObservable.addOnce(() => this.mirror?.dispose());
  }

  private surface(name: string, colour: string, swell: number): PBRMaterial {
    const material = new PBRMaterial(name, this.normal.getScene()!);
    material.albedoColor = Color3.FromHexString(colour).toLinearSpace();
    material.metallic = 0;
    material.roughness = 0.12;
    material.metallicF0Factor = 1;
    material.indexOfRefraction = 1.333;
    material.maxSimultaneousLights = 8;
    material.backFaceCulling = false;
    material.bumpTexture = this.normal;
    const waves = new LakeWaves(material);
    waves.amplitude = swell;
    this.waves.push(waves);
    return material;
  }

  update(dt: number): void {
    this.time += dt;
    for (const waves of this.waves) waves.seconds = this.time * 0.6;
    this.normal.uOffset = this.time * 0.004;
    this.normal.vOffset = this.time * 0.0023;
  }
}
