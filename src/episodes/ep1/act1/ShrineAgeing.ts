import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Scene } from "@babylonjs/core/scene";
import { seededRandom } from "../../../audio/synth";
import type { RelicCraft } from "../act3/RelicCraft";

type XYZ = [number, number, number];

/** Photographed weathered timber, with linear normal and packed AO/roughness maps. */
export function agedShrineTimber(scene: Scene): PBRMaterial {
  const material = new PBRMaterial("M_phra_phum_weathered_teak", scene);
  const base = `${import.meta.env.BASE_URL}assets/ep1/phra-phum/aged-timber`;
  material.albedoTexture = new Texture(`${base}-BC.jpg`, scene);
  const normal = new Texture(`${base}-N.jpg`, scene);
  normal.gammaSpace = false;
  normal.level = 0.8;
  material.bumpTexture = normal;
  // Poly Haven OpenGL normals, matching the glTF loader's left-handed convention.
  material.invertNormalMapX = !scene.useRightHandedSystem;
  material.invertNormalMapY = scene.useRightHandedSystem;
  const orm = new Texture(`${base}-ORM.jpg`, scene);
  orm.gammaSpace = false;
  material.metallicTexture = orm;
  material.useAmbientOcclusionFromMetallicTextureRed = true;
  material.useRoughnessFromMetallicTextureAlpha = false;
  material.useRoughnessFromMetallicTextureGreen = true;
  material.useMetallnessFromMetallicTextureBlue = true;
  material.albedoColor.set(0.65, 0.57, 0.48);
  material.metallic = 0;
  material.roughness = 1;
  material.maxSimultaneousLights = 8;
  material.backFaceCulling = false;
  material.twoSidedLighting = true;
  material.enableSpecularAntiAliasing = true;
  return material;
}

/** Metric grain along the longest dimension of each separate piece, before
 * static merging. A post gets upright grain; a rail gets lengthwise grain.
 * No shared house texture or texture transform is modified. */
export function mapShrineGrain(mesh: Mesh, seed: number): void {
  const positions = mesh.getVerticesData("position"),
    normals = mesh.getVerticesData("normal");
  if (!positions || !normals) return;
  const extent = mesh.getBoundingInfo().boundingBox.extendSize;
  const grain = extent.y > extent.x && extent.y > extent.z ? 1 : extent.z > extent.x ? 2 : 0;
  const centre = mesh.getBoundingInfo().boundingBox.center.asArray();
  const uvs: number[] = [];
  const offset = seededRandom(seed)();
  const otherAxes = [0, 1, 2].filter((axis) => axis !== grain);
  for (let i = 0; i < positions.length; i += 3) {
    // Project each face onto its visible cross-grain axis, including end grain.
    const across =
      Math.abs(normals[i + otherAxes[0]]) < Math.abs(normals[i + otherAxes[1]])
        ? otherAxes[0]
        : otherAxes[1];
    const along =
      Math.abs(normals[i + grain]) > 0.85 ? otherAxes.find((a) => a !== across)! : grain;
    uvs.push(
      (positions[i + along] - centre[along]) / 0.9 + offset,
      (positions[i + across] - centre[across]) / 0.9 + offset * 0.37,
    );
  }
  mesh.setVerticesData("uv", uvs);
}

/** Physical wear and joinery, kept in the shrine's existing material batches. */
export class ShrineAgeing {
  constructor(
    private readonly c: RelicCraft,
    private readonly root: TransformNode,
  ) {}

  pedestal(wood: PBRMaterial, relief: PBRMaterial, dark: PBRMaterial): void {
    const c = this.c;
    c.box(this.root, "phra_phum_hewn_support_post", [0.24, 0.94, 0.24], [0, 0.55, 0], wood);
    for (const side of [-1, 1]) {
      const brace = c.box(
        this.root,
        "phra_phum_plain_support_brace",
        [0.045, 0.34, 0.055],
        [side * 0.19, 0.9, 0],
        wood,
      );
      brace.rotation.z = -side * 0.85;
      c.tube(
        this.root,
        "phra_phum_post_seasoning_split",
        [
          [side * 0.055, 0.19, 0.122],
          [side * 0.05, 0.38, 0.123],
          [side * 0.06, 0.61, 0.122],
        ],
        0.0015,
        dark,
      );
    }
    // A small replacement strip suggests a household maintaining what it owns.
    c.box(
      this.root,
      "phra_phum_post_repair_strip",
      [0.065, 0.2, 0.018],
      [0.067, 0.45, 0.131],
      relief,
    );
  }

  dress(
    wood: PBRMaterial,
    dark: PBRMaterial,
    moss: PBRMaterial,
    wax: PBRMaterial,
    silk: PBRMaterial,
  ): void {
    const c = this.c,
      random = seededRandom(1907);
    // Small seasoning cracks follow the plain jambs.
    for (const side of [-1, 1]) {
      for (let k = 0; k < 4; k++) {
        const x = side * (0.24 + random() * 0.016),
          y = 1.33 + random() * 0.38;
        c.tube(
          this.root,
          "phra_phum_split_door_timber",
          [
            [x, y, 0.313],
            [x + side * 0.004, y + 0.055, 0.314],
            [x - side * 0.002, y + 0.12, 0.313],
          ],
          0.0011,
          dark,
        );
      }
      // Uneven hanging fibres below the cornice, rather than evenly spaced teeth.
      for (let k = 0; k < 8; k++) {
        const x = side * (0.13 + random() * 0.48),
          y = 1.98 + 0.39 * (1 - Math.abs(x) / 0.61);
        c.tube(
          this.root,
          "phra_phum_frayed_eave_fibre",
          [
            [x, y, 0.539],
            [x + 0.003, y - 0.018 - random() * 0.035, 0.542],
          ],
          0.001 + random() * 0.001,
          wood,
        );
      }
      for (let k = 0; k < 3; k++) {
        const x = side * 0.44 + (random() - 0.5) * 0.08;
        c.tube(
          this.root,
          "phra_phum_wax_overflow",
          [
            [x, 1.157, 0.35],
            [x + 0.012, 1.157, 0.52],
            [x + 0.015, 1.1 - random() * 0.095, 0.533],
          ],
          0.002 + random() * 0.002,
          wax,
        );
      }
    }
    // Sparse lichen sits at damp joints, leaving the majority of the wood exposed.
    for (let k = 0; k < 16; k++) {
      const low = k < 8,
        x = (random() - 0.5) * (low ? 0.22 : 1.1),
        y = low ? 0.17 + random() * 0.16 : 1.98 + 0.39 * (1 - Math.abs(x) / 0.61) - 0.015;
      const patch = c.finish(
        CreateSphere("phra_phum_joint_lichen", { diameter: 1, segments: 2 }, c.scene),
        this.root,
        [x, y, low ? 0.123 : 0.54],
        moss,
      );
      patch.scaling.set(0.012 + random() * 0.018, 0.006 + random() * 0.011, 0.004);
      patch.rotation.z = random() * Math.PI;
    }
    // Corner webs: sagging radial threads with incomplete cross threads. These
    // occupy the eaves/jamb corners and leave the actual interaction ray clear.
    for (const side of [-1]) {
      const anchor: XYZ = [side * 0.352, 1.964, 0.345];
      const ends: XYZ[] = [
        [side * 0.14, 1.956, 0.35],
        [side * 0.22, 1.81, 0.35],
        [side * 0.34, 1.69, 0.35],
        [side * 0.55, 1.97, 0.53],
      ];
      for (const end of ends)
        c.tube(
          this.root,
          "phra_phum_cobweb_radial",
          [
            anchor,
            [(anchor[0] + end[0]) / 2, (anchor[1] + end[1]) / 2 - 0.016, (anchor[2] + end[2]) / 2],
            end,
          ],
          0.00055,
          silk,
        );
      for (let row = 1; row < 5; row++) {
        const t = row / 5;
        const path: XYZ[] = ends
          .slice(0, 3)
          .map((end) => [
            anchor[0] + (end[0] - anchor[0]) * t,
            anchor[1] + (end[1] - anchor[1]) * t - 0.012,
            anchor[2] + (end[2] - anchor[2]) * t,
          ]);
        c.tube(this.root, "phra_phum_cobweb_cross_thread", path, 0.0004, silk);
      }
    }
  }
}
