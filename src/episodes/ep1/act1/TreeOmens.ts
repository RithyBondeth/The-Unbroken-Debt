import type { Scene } from "@babylonjs/core/scene";
import type { Material } from "@babylonjs/core/Materials/material";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Ray } from "@babylonjs/core/Culling/ray";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateDecal } from "@babylonjs/core/Meshes/Builders/decalBuilder";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { PhysicsShapeBox, PhysicsShapeContainer } from "@babylonjs/core/Physics/v2/physicsShape";
import { seededRandom } from "../../../audio/synth";
import { FoliageWind } from "../../../render/FoliageWind";
import { trunkRadius, type PlantSite, type TrunkProfile } from "../../../render/plantHeights";
import type { WindState } from "../../../render/wind";
import { pathDistance } from "../data/forestBorder";
import {
  BOUNDARY_CORD,
  DRESSED_TRUNKS,
  OMEN_FIG,
  type DressedTrunk,
  type ThreadColour,
} from "../data/treeOmens";
import { paintBetel, paintBlood, paintCloth, paintThread } from "./omenTextures";

/** Geometry gathered for one merged mesh; `wind` is uv6: hanging length and phase. */
interface Geo {
  positions: number[];
  normals: number[];
  uvs: number[];
  wind: number[];
  indices: number[];
}

const geo = (): Geo => ({ positions: [], normals: [], uvs: [], wind: [], indices: [] });

/**
 * A tube along `path`: rings carried along it without twisting, `radius(i)`
 * at each point, UVs in metres (× `uScale` round, × `vScale` along), and
 * `hang(i)` written to uv6 for the wind.
 */
export function tube(
  out: Geo,
  path: readonly Vector3[],
  radius: (i: number) => number,
  sides: number,
  hang: (i: number) => number,
  phase: number,
  uScale = 1,
  vScale = 1,
): void {
  const n = path.length;
  if (n < 2) return;
  const tangent = (i: number) =>
    path[Math.min(n - 1, i + 1)].subtract(path[Math.max(0, i - 1)]).normalize();
  let t = tangent(0);
  let normal =
    Math.abs(t.y) < 0.9 ? Vector3.Cross(t, Vector3.Up()) : Vector3.Cross(t, Vector3.Right());
  normal.normalize();
  const base = out.positions.length / 3;
  let along = 0;
  for (let i = 0; i < n; i++) {
    if (i > 0) {
      along += Vector3.Distance(path[i], path[i - 1]);
      t = tangent(i);
      normal = normal.subtract(t.scale(Vector3.Dot(normal, t))).normalize();
    }
    const binormal = Vector3.Cross(t, normal);
    const r = radius(i);
    for (let s = 0; s <= sides; s++) {
      const a = (s / sides) * Math.PI * 2;
      const nx = normal.x * Math.cos(a) + binormal.x * Math.sin(a);
      const ny = normal.y * Math.cos(a) + binormal.y * Math.sin(a);
      const nz = normal.z * Math.cos(a) + binormal.z * Math.sin(a);
      out.positions.push(path[i].x + nx * r, path[i].y + ny * r, path[i].z + nz * r);
      out.normals.push(nx, ny, nz);
      out.uvs.push((s / sides) * uScale * Math.max(0.05, r * Math.PI * 2), along * vScale);
      out.wind.push(hang(i), phase);
    }
  }
  for (let i = 0; i + 1 < n; i++)
    for (let s = 0; s < sides; s++) {
      const a = base + i * (sides + 1) + s,
        b = a + sides + 1;
      out.indices.push(a, b, a + 1, a + 1, b, b + 1);
    }
}

/** A thin cloth tie hanging from `top`: a strip that twists as it falls, hanging length in uv6. */
function ribbon(out: Geo, top: Vector3, length: number, width: number, random: () => number) {
  const base = out.positions.length / 3;
  const twist = random() * Math.PI;
  const segments = 4;
  const phase = random() * Math.PI * 2;
  for (let s = 0; s <= segments; s++) {
    const t = s / segments;
    const a = twist + t * (random() - 0.5) * 1.5;
    const dx = Math.cos(a) * width * 0.5,
      dz = Math.sin(a) * width * 0.5;
    const y = top.y - t * length;
    const cx = top.x + (random() - 0.5) * 0.01,
      cz = top.z + (random() - 0.5) * 0.01;
    out.positions.push(cx - dx, y, cz - dz, cx + dx, y, cz + dz);
    out.normals.push(-Math.sin(a), 0, Math.cos(a), -Math.sin(a), 0, Math.cos(a));
    out.uvs.push(0, t * length * 3, 1, t * length * 3);
    out.wind.push(t * length, phase, t * length, phase);
  }
  for (let s = 0; s < segments; s++) {
    const a = base + s * 2;
    out.indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
  }
}

/**
 * The forest marked by the living (data/treeOmens): cotton thread wound
 * tight round the trunks beside the path, its loose ends fluttering in the
 * gusts; a cord strung across the path between bamboo stakes, hung with
 * ties; blood pressed into the bark and run down it by the rain; and the
 * strangler fig, its roots knotted round a host long dead, wrapped in faded
 * cloth, its aerial roots hanging like hair and swinging in the wind.
 */
export class TreeOmens {
  readonly meshes: Mesh[] = [];
  private readonly materials: Material[] = [];
  private readonly textures: DynamicTexture[] = [];
  private body: PhysicsBody | null = null;
  private anchor: TransformNode | null = null;
  private readonly random = seededRandom(6242090);
  readonly stats = { trunks: 0, decals: 0 };

  constructor(
    private readonly scene: Scene,
    private readonly wind: WindState,
    private readonly groundAt: (x: number, z: number) => number,
  ) {}

  build(sites: readonly PlantSite[]): void {
    const thread = {
      red: this.threadMaterial("M_omen_thread_red", new Color3(0.27, 0.012, 0.009)),
      white: this.threadMaterial("M_omen_thread_white", new Color3(0.46, 0.43, 0.35)),
    };
    const threads = { red: geo(), white: geo() };
    for (const dressed of DRESSED_TRUNKS) {
      const site = sites
        .filter((s) => s.trunk && Math.hypot(s.x - dressed.x, s.z - dressed.z) < 2)
        .sort(
          (a, b) =>
            Math.hypot(a.x - dressed.x, a.z - dressed.z) -
            Math.hypot(b.x - dressed.x, b.z - dressed.z),
        )[0];
      if (!site?.trunk) {
        console.warn(`[TreeOmens] no trunk near ${dressed.x}, ${dressed.z}`);
        continue;
      }
      this.dress(site.trunk, dressed, threads);
    }
    this.boundaryCord(threads);
    this.fig(threads, thread.red);
    for (const colour of ["red", "white"] as const)
      this.mesh(`omen_thread_${colour}`, threads[colour], thread[colour]);
    console.info(
      `[TreeOmens] ${this.stats.trunks} trunks bound, ${this.stats.decals} stains, fig at ${OMEN_FIG.x}, ${OMEN_FIG.z}`,
    );
  }

  dispose(): void {
    for (const mesh of this.meshes) mesh.dispose();
    for (const material of this.materials) material.dispose();
    for (const texture of this.textures) texture.dispose();
    this.body?.dispose();
    this.anchor?.dispose();
  }

  // ------------------------------------------------------------- materials

  private texture(
    name: string,
    w: number,
    h: number,
    paint: (ctx: CanvasRenderingContext2D) => void,
  ) {
    const texture = new DynamicTexture(
      name,
      { width: w, height: h },
      this.scene,
      true,
      Texture.TRILINEAR_SAMPLINGMODE,
    );
    paint(texture.getContext() as unknown as CanvasRenderingContext2D);
    texture.update();
    this.textures.push(texture);
    return texture;
  }

  private threadMaterial(name: string, colour: Color3): PBRMaterial {
    const material = new PBRMaterial(name, this.scene);
    material.albedoTexture = this.texture(`T_${name}`, 64, 64, (ctx) =>
      paintThread(ctx, 64, this.random),
    );
    material.albedoColor = colour;
    material.metallic = 0;
    material.roughness = 0.62;
    material.backFaceCulling = false;
    material.maxSimultaneousLights = 8;
    new FoliageWind(material, this.wind, "cloth");
    this.materials.push(material);
    return material;
  }

  private stainMaterial(
    name: string,
    paint: (ctx: CanvasRenderingContext2D) => void,
    roughness: number,
  ) {
    const material = new PBRMaterial(name, this.scene);
    material.albedoTexture = this.texture(`T_${name}`, 256, 512, paint);
    material.albedoTexture.hasAlpha = true;
    material.useAlphaFromAlbedoTexture = true;
    material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    material.metallic = 0;
    material.roughness = roughness;
    material.zOffset = -2;
    // Decals copy the bark's triangles; mirrored source meshes would leave them facing in.
    material.backFaceCulling = false;
    material.maxSimultaneousLights = 8;
    this.materials.push(material);
    return material;
  }

  private mesh(name: string, data: Geo, material: Material): Mesh | null {
    if (!data.indices.length) return null;
    const mesh = new Mesh(name, this.scene);
    const vertex = new VertexData();
    vertex.positions = data.positions;
    vertex.normals = data.normals;
    vertex.uvs = data.uvs;
    vertex.indices = data.indices;
    vertex.applyToMesh(mesh, false);
    mesh.setVerticesData("uv6", data.wind, false, 2);
    mesh.material = material;
    mesh.isPickable = false;
    mesh.receiveShadows = true;
    mesh.freezeWorldMatrix();
    this.meshes.push(mesh);
    return mesh;
  }

  // ------------------------------------------------------------- thread

  /** Thread wound round a measured trunk, knotted, its two ends left hanging. */
  private windThread(
    out: Geo,
    profile: (a: number) => number,
    centre: Vector3,
    y0: number,
    turns: number,
    pitch: number,
    start: number,
  ): Vector3 {
    const path: Vector3[] = [];
    const steps = Math.round(turns * 28);
    let last = centre;
    for (let k = 0; k <= steps; k++) {
      const t = k / steps;
      const a = start + t * turns * Math.PI * 2;
      // Each turn pulled a little crooked, as a hand winds it.
      const r = profile(a) + 0.004 + 0.0025 * Math.sin(a * 3 + start);
      const y = y0 + t * pitch + 0.012 * Math.sin(a * 0.5 + turns);
      last = new Vector3(centre.x + Math.cos(a) * r, y, centre.z + Math.sin(a) * r);
      path.push(last);
    }
    tube(
      out,
      path,
      () => 0.0028,
      4,
      () => 0,
      0,
      1,
      40,
    );
    return last;
  }

  /** The knot and two loose ends falling from it, swinging in the wind. */
  private tails(out: Geo, knot: Vector3, outward: Vector3, random: () => number): void {
    for (let k = 0; k < 2; k++) {
      const length = 0.18 + random() * 0.5;
      const path: Vector3[] = [];
      const phase = random() * Math.PI * 2;
      for (let s = 0; s <= 8; s++) {
        const t = s / 8;
        path.push(
          knot.add(
            new Vector3(
              outward.x * (0.012 + 0.03 * t) + Math.sin(t * 5 + phase) * 0.012,
              -t * length,
              outward.z * (0.012 + 0.03 * t) + Math.cos(t * 4 + phase) * 0.012,
            ),
          ),
        );
      }
      tube(
        out,
        path,
        () => 0.0026,
        4,
        (i) => (i / 8) * length,
        phase,
        1,
        40,
      );
    }
    tube(
      out,
      [
        knot.add(outward.scale(0.004)),
        knot.add(outward.scale(0.016)).addInPlaceFromFloats(0, -0.006, 0),
      ],
      () => 0.008,
      5,
      () => 0,
      0,
    );
  }

  private dress(
    trunk: TrunkProfile,
    dressed: DressedTrunk,
    threads: Record<ThreadColour, Geo>,
  ): void {
    const random = this.random;
    const centre = new Vector3(trunk.x, 0, trunk.z);
    // The side that faces the path, where the knot is tied and the blood is.
    let facing = 0,
      best = Infinity;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
      const d = pathDistance(trunk.x + Math.cos(a) * 2, trunk.z + Math.sin(a) * 2);
      if (d < best) {
        best = d;
        facing = a;
      }
    }
    const profile = (a: number) => trunkRadius(trunk, a);
    dressed.threads.forEach((colour, k) => {
      const y0 = trunk.from + 0.25 + k * 0.32 + random() * 0.1;
      // Two windings at different pitches, so the turns cross as real wrapping does.
      this.windThread(
        threads[colour],
        profile,
        centre,
        y0,
        3 + random() * 3,
        0.05 + random() * 0.05,
        facing + 0.4,
      );
      const end = this.windThread(
        threads[colour],
        profile,
        centre,
        y0 + 0.02,
        2.4 + random() * 2,
        -0.03,
        facing - 0.3,
      );
      const a = Math.atan2(end.z - trunk.z, end.x - trunk.x);
      this.tails(threads[colour], end, new Vector3(Math.cos(a), 0, Math.sin(a)), random);
    });
    if (dressed.blood) {
      const material = this.stainMaterial(
        `M_omen_blood_${this.stats.trunks}`,
        (ctx) =>
          paintBlood(ctx, 256, 512, dressed.blood!, seededRandom(6242100 + this.stats.trunks)),
        0.28,
      );
      this.stain(trunk, facing, trunk.from + 0.4, new Vector3(0.46, 0.92, 0.6), material);
    }
    this.stats.trunks++;
  }

  /** Projects a stain onto whatever bark is at `a` round the trunk, at height `y`. */
  private stain(
    trunk: TrunkProfile,
    a: number,
    y: number,
    size: Vector3,
    material: Material,
    target?: Mesh,
  ) {
    const dir = new Vector3(-Math.cos(a), 0, -Math.sin(a));
    const from = new Vector3(trunk.x - dir.x * 1.5, y, trunk.z - dir.z * 1.5);
    const hit = this.scene.pickWithRay(new Ray(from, dir, 2), (mesh) =>
      target
        ? mesh === target
        : mesh.material?.name === "M_wet_bark" || mesh.material?.name === "M_wet_bark_dead",
    );
    if (!hit?.hit || !hit.pickedMesh || !hit.pickedPoint) return;
    const normal = hit.getNormal(true, true) ?? dir.scale(-1);
    const decal = CreateDecal(`omen_stain_${this.stats.decals}`, hit.pickedMesh, {
      position: hit.pickedPoint,
      normal,
      size,
    });
    decal.material = material;
    decal.isPickable = false;
    decal.receiveShadows = true;
    this.meshes.push(decal);
    this.stats.decals++;
  }

  // ------------------------------------------------------------- the cord

  /** Bamboo stakes either side of the path, the cord between them sagging, its ties hung along it. */
  private boundaryCord(threads: Record<ThreadColour, Geo>): void {
    const bamboo = this.scene.getMaterialByName("M_bamboo");
    if (!bamboo) return;
    const random = this.random;
    const [ax, az] = BOUNDARY_CORD.from,
      [bx, bz] = BOUNDARY_CORD.to;
    const stakes = geo();
    const tops: Vector3[] = [];
    for (const [x, z] of [
      [ax, az],
      [bx, bz],
    ]) {
      const ground = this.groundAt(x, z);
      const lean = new Vector3((random() - 0.5) * 0.12, 1, (random() - 0.5) * 0.12).normalize();
      const height = BOUNDARY_CORD.height + 0.25;
      const foot = new Vector3(x, ground - 0.2, z);
      tube(
        stakes,
        [foot, foot.add(lean.scale(height + 0.2))],
        () => 0.032,
        7,
        () => 0,
        0,
        1,
        1,
      );
      tops.push(foot.add(lean.scale(BOUNDARY_CORD.height + 0.2)));
    }
    this.mesh("omen_cord_stakes", stakes, bamboo);
    const [a, b] = tops;
    const cord: Vector3[] = [];
    const span = Vector3.Distance(a, b);
    for (let i = 0; i <= 24; i++) {
      const t = i / 24;
      cord.push(Vector3.Lerp(a, b, t).addInPlaceFromFloats(0, -4 * 0.32 * t * (1 - t), 0));
    }
    // The cord swings a little at its middle, where it sags furthest.
    tube(
      threads.white,
      cord,
      () => 0.0035,
      4,
      (i) => 4 * 0.6 * (i / 24) * (1 - i / 24),
      0.7,
      1,
      40,
    );
    const ties = { red: geo(), white: geo() };
    for (let d = 0.35; d < span - 0.3; d += 0.32 + random() * 0.25) {
      const t = d / span;
      const at = Vector3.Lerp(a, b, t).addInPlaceFromFloats(0, -4 * 0.32 * t * (1 - t) - 0.004, 0);
      const colour: ThreadColour = random() < 0.6 ? "red" : "white";
      ribbon(ties[colour], at, 0.12 + random() * 0.26, 0.018 + random() * 0.014, random);
    }
    this.mesh("omen_cord_ties_red", ties.red, this.clothMaterial("M_omen_tie_red", [128, 22, 16]));
    this.mesh(
      "omen_cord_ties_white",
      ties.white,
      this.clothMaterial("M_omen_tie_white", [176, 166, 140]),
    );
  }

  private clothMaterial(name: string, colour: readonly [number, number, number]): PBRMaterial {
    const material = new PBRMaterial(name, this.scene);
    material.albedoTexture = this.texture(`T_${name}`, 256, 128, (ctx) =>
      paintCloth(ctx, 256, 128, colour, this.random),
    );
    material.albedoTexture.hasAlpha = true;
    material.useAlphaFromAlbedoTexture = true;
    material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
    material.alphaCutOff = 0.4;
    material.metallic = 0;
    material.roughness = 0.82;
    material.backFaceCulling = false;
    material.maxSimultaneousLights = 8;
    new FoliageWind(material, this.wind, "cloth");
    this.materials.push(material);
    return material;
  }

  // ------------------------------------------------------------- the fig

  /**
   * A strangler fig: a dozen roots that came down from a seed in the host's
   * crown and have choked it, twisting round one another to a knot of trunk,
   * splaying into bare branches above, aerial roots hanging from them.
   */
  private fig(threads: Record<ThreadColour, Geo>, red: Material): void {
    const random = seededRandom(6242120);
    const bark = this.scene.getMaterialByName("M_wet_bark") ?? red;
    const ground = this.groundAt(OMEN_FIG.x, OMEN_FIG.z);
    const c = new Vector3(OMEN_FIG.x, ground, OMEN_FIG.z);
    const trunk = geo();
    const hangers = geo();
    const tips: Vector3[] = [];
    const roots = 18;
    const height = (y: number) => Math.max(0, y - ground) * 0.45;
    const radii: { a: number; r: (y: number) => number; thick: number }[] = [];
    for (let i = 0; i < roots; i++) {
      const a0 = (i / roots) * Math.PI * 2 + (random() - 0.5) * 0.4;
      const spread = 1 + random() * 2;
      // Roots wound both ways cross into the net that strangles the host.
      const twist = (0.9 + random() * 1.7) * (i % 2 ? -1 : 1);
      const top = 5.5 + random() * 3.5;
      const thick = i % 3 === 1 ? 0.03 + random() * 0.03 : 0.07 + random() * 0.1;
      const splay = i % 3 === 0 ? 1.5 + random() * 2.2 : 0;
      const core = 0.24 + random() * 0.16;
      const path: Vector3[] = [];
      const crawl = 9,
        rise = 20,
        steps = crawl + rise;
      const lift = 0.3;
      // Up the trunk: the roots draw in tight, then splay into branches at the top.
      const radiusAt = (t: number) => {
        const s = Math.min(1, t / 0.15);
        return (
          core * (1 - 0.45 * t) +
          lift * (1 - s * s * (3 - 2 * s)) +
          (t > 0.72 ? (t - 0.72) * 3.6 * splay : 0)
        );
      };
      // Along the ground first, half buried, in low arcs like a hand's tendons.
      for (let k = 0; k < crawl; k++) {
        const u = k / crawl;
        const a = a0 + 0.22 * Math.sin(u * 5 + i);
        const r = spread + (core + lift - spread) * u ** 1.3;
        const y = ground - 0.07 + 0.13 * Math.sin(Math.PI * Math.min(1, u * 1.15)) + 0.3 * u ** 3;
        path.push(new Vector3(c.x + Math.cos(a) * r, y, c.z + Math.sin(a) * r));
      }
      const a1 = a0 + 0.22 * Math.sin(5 + i);
      for (let k = 0; k <= rise; k++) {
        const t = k / rise;
        const a = a1 + twist * t + 0.12 * Math.sin(t * 9 + i);
        const r = radiusAt(t) + 0.04 * Math.sin(t * 13 + i * 2);
        const y = ground + lift - 0.07 + (top - lift) * t ** 1.08;
        path.push(new Vector3(c.x + Math.cos(a) * r, y, c.z + Math.sin(a) * r));
      }
      tube(
        trunk,
        path,
        (k) => thick * (k < crawl ? 0.75 + 0.6 * (k / crawl) : 1.35 - 0.7 * ((k - crawl) / rise)),
        7,
        (k) => height(path[k].y),
        0,
        1,
        1,
      );
      radii.push({
        a: a1,
        thick,
        r: (y) => radiusAt(Math.max(0, (y - ground - lift) / (top - lift))),
      });
      // Bare branches go on from the splaying roots; aerial roots hang from them.
      if (splay > 0) tips.push(...path.slice(steps - 6));
    }
    // The host: a pale trunk long dead inside the net, broken off above it.
    const host = geo();
    const hostPath: Vector3[] = [];
    for (let s = 0; s <= 10; s++)
      hostPath.push(
        c.add(new Vector3(Math.sin(s * 0.7) * 0.05, -0.1 + s * 0.78, Math.cos(s * 0.5) * 0.04)),
      );
    tube(
      host,
      hostPath,
      (s) => 0.24 - s * 0.012,
      9,
      (s) => height(hostPath[s].y),
      0,
      1,
      1,
    );
    for (let k = 0; k < 8; k++) {
      const a = random() * Math.PI * 2;
      const from = c.add(new Vector3(Math.cos(a) * 0.2, 5 + random() * 1.5, Math.sin(a) * 0.2));
      const path: Vector3[] = [from];
      let dir = new Vector3(Math.cos(a), 0.6 + random() * 0.5, Math.sin(a)).normalize();
      for (let s = 1; s <= 8; s++) {
        dir = dir
          .add(new Vector3((random() - 0.5) * 0.5, (random() - 0.45) * 0.4, (random() - 0.5) * 0.5))
          .normalize();
        path.push(path[s - 1].add(dir.scale(0.45 + random() * 0.2)));
      }
      tube(
        trunk,
        path,
        (s) => 0.07 * (1 - s / 10),
        6,
        (s) => height(path[s].y),
        0,
        1,
        1,
      );
      tips.push(...path.slice(2));
    }
    // Curtains of aerial roots, thickest over the path side, like hair let down.
    const pathSide = Math.atan2(29 - c.z, 2.5 - c.x);
    const facing = tips.filter((p) => Math.cos(Math.atan2(p.z - c.z, p.x - c.x) - pathSide) > 0.2);
    for (let k = 0; k < 110 && tips.length; k++) {
      const pool = k % 5 < 2 && facing.length ? facing : tips;
      const from = pool[Math.floor(random() * pool.length)];
      const length = Math.min(from.y - ground - 0.05, 1.2 + random() * 5);
      const phase = random() * Math.PI * 2;
      const drift = new Vector3((random() - 0.5) * 0.3, 0, (random() - 0.5) * 0.3);
      const path: Vector3[] = [];
      for (let s = 0; s <= 10; s++) {
        const t = s / 10;
        path.push(
          from
            .add(drift.scale(t * t))
            .addInPlaceFromFloats(Math.sin(t * 6 + phase) * 0.03, -t * length, 0),
        );
      }
      const r = 0.008 + random() * 0.014;
      tube(
        hangers,
        path,
        (s) => r * (1 - s / 14),
        4,
        (s) => (s / 10) * length,
        phase,
        1,
        1,
      );
    }
    const trunkMesh = this.mesh("omen_fig_trunk", trunk, bark);
    this.mesh("omen_fig_host", host, this.scene.getMaterialByName("M_wet_bark_dead") ?? bark);
    const rootMaterial = bark.clone("M_omen_fig_aerial_roots");
    if (rootMaterial) {
      rootMaterial.pluginManager?.getPlugin("FoliageWind")?.dispose();
      new FoliageWind(rootMaterial, this.wind, "hanging");
      this.materials.push(rootMaterial);
      this.mesh("omen_fig_hanging_roots", hangers, rootMaterial);
    }

    // Two bands of faded cloth tied round the knot of trunk, and thread over them.
    const outline = (y: number, a: number) => {
      let r = 0.2;
      for (const root of radii) {
        const diff = Math.abs(Math.atan2(Math.sin(a - root.a), Math.cos(a - root.a)));
        if (diff < 0.9) r = Math.max(r, root.r(y) * Math.cos(diff) + root.thick * 1.3);
      }
      return r;
    };
    const bands = geo();
    const whiteBands = geo();
    for (const [y, out] of [
      [ground + 1.15, bands],
      [ground + 1.5, whiteBands],
    ] as const) {
      const sides = 36,
        h = 0.2;
      const base = out.positions.length / 3;
      for (let row = 0; row <= 1; row++)
        for (let s = 0; s <= sides; s++) {
          const a = (s / sides) * Math.PI * 2;
          const r = outline(y + row * h, a) + 0.025 + 0.012 * Math.sin(a * 7 + y);
          out.positions.push(
            c.x + Math.cos(a) * r,
            y + row * h - 0.03 * Math.sin(a * 2) ** 2,
            c.z + Math.sin(a) * r,
          );
          out.normals.push(Math.cos(a), 0, Math.sin(a));
          out.uvs.push((s / sides) * 4, 1 - row);
          out.wind.push(row === 0 ? 0.05 : 0, 0);
        }
      for (let s = 0; s < sides; s++) {
        const a = base + s,
          b = a + sides + 1;
        out.indices.push(a, a + 1, b, a + 1, b + 1, b);
      }
      const centre = new Vector3(c.x, 0, c.z);
      const knot = this.windThread(
        threads.red,
        (a) => outline(y + 0.1, a) + 0.03,
        centre,
        y + 0.04,
        3.5,
        0.08,
        random() * 6,
      );
      const a = Math.atan2(knot.z - c.z, knot.x - c.x);
      this.tails(threads.red, knot, new Vector3(Math.cos(a), 0, Math.sin(a)), random);
    }
    this.mesh("omen_fig_cloth_red", bands, this.clothMaterial("M_omen_cloth_red", [112, 30, 22]));
    this.mesh(
      "omen_fig_cloth_white",
      whiteBands,
      this.clothMaterial("M_omen_cloth_white", [168, 158, 132]),
    );

    // At its roots: a clay pot, incense burnt down to the sticks, betel spat on the bark.
    this.offerings(c, random);
    if (trunkMesh) {
      trunkMesh.isPickable = true;
      const towards = Math.atan2(29 - c.z, 2.5 - c.x);
      const profile: TrunkProfile = { x: c.x, z: c.z, from: ground, to: ground + 2, radii: [] };
      const blood = this.stainMaterial(
        "M_omen_fig_blood",
        (ctx) => paintBlood(ctx, 256, 512, "hand", seededRandom(6242130)),
        0.28,
      );
      this.stain(profile, towards, ground + 1.0, new Vector3(0.4, 0.8, 1.2), blood, trunkMesh);
      const betel = this.stainMaterial(
        "M_omen_betel",
        (ctx) => paintBetel(ctx, 256, 512, seededRandom(6242131)),
        0.7,
      );
      this.stain(
        profile,
        towards + 0.9,
        ground + 0.35,
        new Vector3(0.5, 0.6, 1.4),
        betel,
        trunkMesh,
      );
      trunkMesh.isPickable = false;
    }
    this.collider(c, 1.1);
  }

  private offerings(c: Vector3, random: () => number): void {
    const a = Math.atan2(29 - c.z, 2.5 - c.x);
    const at = new Vector3(c.x + Math.cos(a) * 1.05, 0, c.z + Math.sin(a) * 1.05);
    at.y = this.groundAt(at.x, at.z) - 0.02;
    const clay = new PBRMaterial("M_omen_clay_pot", this.scene);
    clay.albedoColor = new Color3(0.13, 0.055, 0.03);
    clay.metallic = 0;
    clay.roughness = 0.8;
    clay.maxSimultaneousLights = 8;
    this.materials.push(clay);
    const profile = [
      [0, 0],
      [0.07, 0],
      [0.1, 0.04],
      [0.11, 0.09],
      [0.085, 0.14],
      [0.07, 0.155],
      [0.08, 0.17],
    ].map(([r, y]) => new Vector3(r, y, 0));
    const pot = CreateLathe(
      "omen_clay_pot",
      { shape: profile, tessellation: 18, sideOrientation: Mesh.DOUBLESIDE },
      this.scene,
    );
    pot.position.copyFrom(at);
    pot.rotationQuaternion = Quaternion.RotationYawPitchRoll(random(), 0.08, 0.05);
    pot.material = clay;
    pot.isPickable = false;
    this.meshes.push(pot);
    const incense = geo();
    for (let k = 0; k < 7; k++) {
      const x = at.x + 0.2 + (random() - 0.5) * 0.12,
        z = at.z + (random() - 0.5) * 0.14;
      const y = this.groundAt(x, z);
      const lean = new Vector3((random() - 0.5) * 0.25, 1, (random() - 0.5) * 0.25).normalize();
      const length = 0.06 + random() * 0.16;
      tube(
        incense,
        [new Vector3(x, y - 0.03, z), new Vector3(x, y - 0.03, z).add(lean.scale(length))],
        () => 0.0018,
        3,
        () => 0,
        0,
      );
    }
    const sticks = new PBRMaterial("M_omen_incense", this.scene);
    sticks.albedoColor = new Color3(0.2, 0.035, 0.025);
    sticks.metallic = 0;
    sticks.roughness = 0.9;
    this.materials.push(sticks);
    this.mesh("omen_incense", incense, sticks);
  }

  private collider(c: Vector3, half: number): void {
    const anchor = new TransformNode("omen_fig_body", this.scene);
    anchor.metadata = { surface: "leaves" };
    const body = new PhysicsBody(anchor, PhysicsMotionType.STATIC, false, this.scene);
    const shape = new PhysicsShapeContainer(this.scene);
    shape.addChild(
      new PhysicsShapeBox(
        new Vector3(c.x, c.y + 2, c.z),
        Quaternion.Identity(),
        new Vector3(half * 2, 4.5, half * 2),
        this.scene,
      ),
    );
    body.shape = shape;
    this.body = body;
    this.anchor = anchor;
  }
}
