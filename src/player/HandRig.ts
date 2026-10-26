import type { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { MorphTarget } from "@babylonjs/core/Morph/morphTarget";
import { MorphTargetManager } from "@babylonjs/core/Morph/morphTargetManager";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { BaseTexture } from "@babylonjs/core/Materials/Textures/baseTexture";
import { HAND_GRIPS, type HandAsset, type HandGrip } from "./HandAsset";
export type { HandGrip } from "./HandAsset";

/** A continuous anatomical hand with photo UVs and Blender-authored skin deformations.
 * GPU morphing preserves the actual thumb web, knuckles, fingernails and forearm. */
export class HandRig {
  readonly root: TransformNode;
  readonly meshes: Mesh[] = [];
  skin!: Mesh;
  private manager: MorphTargetManager | null = null;
  private current: HandGrip = "relaxed";
  private readonly weights = HAND_GRIPS.map((_, i) => (i === 0 ? 1 : 0));
  private readonly materials: PBRMaterial[] = [];
  constructor(
    private readonly scene: Scene,
    name: string,
    private readonly side: number,
  ) {
    this.root = new TransformNode(name, scene);
    this.root.scaling.setAll(0.85);
  }
  get grip(): HandGrip {
    return this.current;
  }
  get poseWeights(): readonly number[] {
    return [...this.weights];
  }
  install(
    asset: HandAsset,
    texture: BaseTexture | null,
    normal: BaseTexture | null = null,
    roughness: BaseTexture | null = null,
  ): void {
    if (this.manager) return;
    const mirror = -this.side;
    const mirrored = (array: Float32Array) => {
      const result = array.slice();
      for (let i = 0; i < result.length; i += 3) result[i] *= mirror;
      return result;
    };
    const index = asset.indices.slice();
    if (mirror < 0)
      for (let i = 0; i < index.length; i += 3)
        [index[i + 1], index[i + 2]] = [index[i + 2], index[i + 1]];
    const mesh = new Mesh(`${this.root.name}_skin`, this.scene);
    mesh.parent = this.root;
    const data = new VertexData();
    data.positions = mirrored(asset.poses.relaxed.positions);
    data.normals = mirrored(asset.poses.relaxed.normals);
    data.uvs = asset.uvs;
    data.indices = index;
    data.applyToMesh(mesh);
    const skin = new PBRMaterial(`${this.root.name}_photo_skin`, this.scene);
    skin.albedoTexture = texture;
    skin.bumpTexture = normal;
    skin.invertNormalMapX = true;
    skin.invertNormalMapY = false;
    // The photographic atlas is a light peach; Sora is Khmer. Multiplied (linear) to a
    // warm medium tone, about sRGB #be8c6e on the back of the hand, keeping its detail.
    skin.albedoColor.set(0.69, 0.51, 0.38);
    skin.metallic = 0;
    skin.metallicTexture = roughness;
    skin.useRoughnessFromMetallicTextureGreen = true;
    skin.useRoughnessFromMetallicTextureAlpha = false;
    skin.useMetallnessFromMetallicTextureBlue = false;
    skin.roughness = roughness ? 1 : 0.56;
    skin.maxSimultaneousLights = 8;
    skin.environmentIntensity = 0.12;
    this.materials.push(skin);
    mesh.material = skin;
    const manager = new MorphTargetManager(this.scene);
    manager.areUpdatesFrozen = true;
    manager.useTextureToStoreTargets = true;
    manager.enableUVMorphing = false;
    for (const [i, name] of HAND_GRIPS.entries()) {
      const target = new MorphTarget(name, this.weights[i], this.scene);
      target.setPositions(mirrored(asset.poses[name].positions));
      target.setNormals(mirrored(asset.poses[name].normals));
      manager.addTarget(target);
    }
    manager.areUpdatesFrozen = false;
    mesh.morphTargetManager = manager;
    this.manager = manager;
    this.skin = mesh;
    this.meshes.push(mesh);
    this.makeSleeve(asset, mirror);
  }
  private makeSleeve(asset: HandAsset, mirror: number): void {
    const p: number[] = [],
      indices: number[] = [],
      normals: number[] = [];
    const reference = asset.poses.relaxed.positions;
    const section = (y: number) => {
      let minX = Infinity,
        maxX = -Infinity,
        minZ = Infinity,
        maxZ = -Infinity;
      for (let i = 0; i < reference.length; i += 3)
        if (Math.abs(reference[i + 1] - y) < 0.012) {
          const x = reference[i] * mirror,
            z = reference[i + 2];
          minX = Math.min(minX, x);
          maxX = Math.max(maxX, x);
          minZ = Math.min(minZ, z);
          maxZ = Math.max(maxZ, z);
        }
      if (!Number.isFinite(minX)) return [0, -0.04, 0.035, 0.03];
      return [
        (minX + maxX) / 2,
        (minZ + maxZ) / 2,
        (maxX - minX) / 2 + 0.003,
        (maxZ - minZ) / 2 + 0.003,
      ];
    };
    const rows = [-0.9, -0.5, -0.235, -0.2, -0.175, -0.167];
    for (const y of rows) {
      const [cx, cz, rx, rz] = section(Math.max(-0.22, y));
      for (let i = 0; i <= 32; i++) {
        const a = (i / 32) * Math.PI * 2,
          fold = 1 + 0.025 * Math.sin(i * 2.7 + y * 130);
        p.push(cx + Math.cos(a) * rx * fold, y, cz + Math.sin(a) * rz * fold);
      }
    }
    for (let r = 0; r < rows.length - 1; r++)
      for (let i = 0; i < 32; i++) {
        const a = r * 33 + i;
        indices.push(a, a + 1, a + 33, a + 1, a + 34, a + 33);
      }
    VertexData.ComputeNormals(p, indices, normals);
    const sleeve = new Mesh(`${this.root.name}_sleeve`, this.scene);
    sleeve.parent = this.root;
    const data = new VertexData();
    data.positions = p;
    data.indices = indices;
    data.normals = normals;
    data.applyToMesh(sleeve);
    const cloth = new PBRMaterial(`${this.root.name}_cloth`, this.scene);
    cloth.albedoColor.set(0.22, 0.205, 0.17);
    cloth.metallic = 0;
    cloth.roughness = 0.95;
    cloth.maxSimultaneousLights = 8;
    this.materials.push(cloth);
    sleeve.material = cloth;
    this.meshes.push(sleeve);
  }
  update(dt: number, grip: HandGrip): void {
    this.current = grip;
    const k = 1 - Math.exp(-Math.min(dt, 0.1) * 14);
    for (const [i, name] of HAND_GRIPS.entries()) {
      this.weights[i] += ((name === grip ? 1 : 0) - this.weights[i]) * k;
      if (this.manager) this.manager.getTarget(i).influence = this.weights[i];
    }
  }
  dispose(): void {
    this.root.dispose();
    this.manager?.dispose();
    for (const m of this.materials) m.dispose();
  }
}
