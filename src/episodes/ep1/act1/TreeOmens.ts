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
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { PhysicsShapeBox, PhysicsShapeContainer } from "@babylonjs/core/Physics/v2/physicsShape";
import { seededRandom } from "@/audio/synth";
import { FoliageWind, type FoliageKind } from "@/render/FoliageWind";
import { trunkRadius, type PlantSite, type TrunkProfile } from "@/render/plantHeights";
import type { WindState } from "@/render/wind";
import { oldRoadDistance } from "../data/forestBorder";
import { CORD_WEB, DRESSED_TRUNKS, type DressedTrunk, type ThreadColour } from "../data/treeOmens";
import { paintBlood, paintCloth, paintThread } from "./omenTextures";

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

/** A tuft of black hair knotted to a cord: a dozen strands that fall and swing. */
function tassel(out: Geo, at: Vector3, random: () => number): void {
  const strands = 10 + Math.floor(random() * 7);
  const length = 0.16 + random() * 0.28;
  const phase = random() * Math.PI * 2;
  for (let k = 0; k < strands; k++) {
    const a = random() * Math.PI * 2,
      splay = 0.01 + random() * 0.035;
    const l = length * (0.7 + 0.3 * random());
    const path: Vector3[] = [];
    for (let s = 0; s <= 5; s++) {
      const t = s / 5;
      path.push(
        at.add(
          new Vector3(
            Math.cos(a) * splay * t + Math.sin(t * 7 + k) * 0.004,
            -t * l,
            Math.sin(a) * splay * t,
          ),
        ),
      );
    }
    tube(
      out,
      path,
      (s) => 0.0016 * (1 - s / 7),
      3,
      (s) => (s / 5) * l,
      phase,
      1,
      1,
    );
  }
  tube(
    out,
    [at.add(new Vector3(0, 0.012, 0)), at.add(new Vector3(0, -0.02, 0))],
    () => 0.009,
    6,
    () => 0,
    phase,
  );
}

/**
 * A cloth effigy hung by its head below `neck`: a bound bundle of a body, a
 * round head, arms raised and legs hanging, as the title screen's figures.
 * Every vertex carries how far below the tie it hangs, so it swings whole.
 */
export function effigy(
  out: Geo,
  neck: Vector3,
  drop: number,
  scale: number,
  random: () => number,
): void {
  const yaw = random() * Math.PI * 2;
  const phase = random() * Math.PI * 2;
  const p = (x: number, y: number) =>
    neck.add(new Vector3(Math.cos(yaw) * x * scale, y * scale, Math.sin(yaw) * x * scale));
  const hang = (v: Vector3) => drop + (neck.y - v.y);
  const limb = (path: Vector3[], r: (i: number) => number, sides = 5) =>
    tube(out, path, r, sides, (i) => hang(path[i]), phase, 1, 2);
  const head: Vector3[] = [];
  for (let k = 0; k <= 6; k++) head.push(p(0, -0.01 + (k / 6) * 0.1));
  limb(head, (k) => 0.004 + 0.044 * Math.sqrt(Math.sin((Math.PI * k) / 6)), 8);
  const body: Vector3[] = [];
  for (let k = 0; k <= 6; k++) body.push(p(Math.sin(k * 0.8) * 0.006, -0.03 - (k / 6) * 0.27));
  limb(body, (k) => 0.03 + 0.022 * Math.sin((Math.PI * k) / 6), 8);
  for (const side of [-1, 1]) {
    const lift = 0.04 + random() * 0.05;
    limb(
      [p(side * 0.03, -0.07), p(side * 0.09, -0.02 + lift * 0.5), p(side * 0.14, 0.03 + lift)],
      () => 0.012,
    );
    limb(
      [p(side * 0.02, -0.28), p(side * 0.035, -0.37), p(side * 0.04, -0.45)],
      (k) => 0.015 - k * 0.002,
    );
  }
}

/** The omens' materials, made once and shared by the web, the trunks and the fig. */
interface Kit {
  cord: Geo;
  hair: Geo;
  effigy: Geo;
  tieRed: Material;
  tieWhite: Material;
  blood: Material;
}

/**
 * The forest marked by the living (data/treeOmens): undyed cotton thread
 * wound tight round the trunks beside the path and knotted flat against the
 * bark (nothing red, and nothing left hanging off a tree); a cord strung
 * across the path between bamboo stakes, hung with
 * ties; blood pressed into the bark and run down it by the rain; and the
 * strangler fig, its roots knotted round a host long dead, wrapped in faded
 * cloth, its aerial roots hanging like hair and swinging in the wind.
 */
export class TreeOmens {
  readonly meshes: Mesh[] = [];
  private readonly materials: Material[] = [];
  private readonly textures: DynamicTexture[] = [];
  private body: PhysicsBody | null = null;
  /** Static boxes for the fig and the web's poles: [centre, size]. */
  private readonly boxes: [Vector3, Vector3][] = [];
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
      white: this.threadMaterial("M_omen_thread_white", new Color3(0.46, 0.43, 0.35)),
    };
    const threads: Record<ThreadColour, Geo> = { white: geo() };
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
    const kit: Kit = {
      cord: geo(),
      hair: geo(),
      effigy: geo(),
      tieRed: this.clothMaterial("M_omen_tie_red", [128, 22, 16]),
      tieWhite: this.clothMaterial("M_omen_tie_white", [176, 166, 140]),
      blood: this.stainMaterial(
        "M_omen_web_blood",
        (ctx) => paintBlood(ctx, 256, 512, "hand", seededRandom(6242140)),
        0.28,
      ),
    };
    this.cordWeb(kit);
    // No strangler fig on its dead host any more: the user wants no leafless trees in
    // the village (November 19, 2026). The threads stay on the living trunks.
    for (const colour of ["white"] as const)
      this.mesh(`omen_thread_${colour}`, threads[colour], thread[colour]);
    this.mesh(
      "omen_cords",
      kit.cord,
      this.threadMaterial("M_omen_cord", new Color3(0.15, 0.009, 0.007)),
    );
    const hair = this.threadMaterial("M_omen_hair", new Color3(0.013, 0.01, 0.009));
    hair.roughness = 0.42;
    this.mesh("omen_hair", kit.hair, hair);
    this.mesh(
      "omen_effigies",
      kit.effigy,
      this.clothMaterial("M_omen_effigy", [150, 138, 112], "effigy", false),
    );
    this.buildColliders();
    console.info(`[TreeOmens] ${this.stats.trunks} trunks bound, ${this.stats.decals} stains`);
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
    thickness = 0.0042,
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
      () => thickness,
      4,
      () => 0,
      0,
      1,
      40,
    );
    return last;
  }

  /**
   * The knot, pulled tight against the bark. The ends are tucked under the
   * winding: nothing is left hanging loose in the air off a tree.
   */
  private knot(out: Geo, knot: Vector3, outward: Vector3): void {
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
      const d = oldRoadDistance(trunk.x + Math.cos(a) * 2, trunk.z + Math.sin(a) * 2);
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
      this.knot(threads[colour], end, new Vector3(Math.cos(a), 0, Math.sin(a)));
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

  // ------------------------------------------------------------- the web

  /**
   * The web over the path (data/treeOmens): bamboo poles lashed with cord,
   * dark-red cords sagging between them overhead, hair tassels and red and
   * white ties along them, cloth effigies hung below, and a bloody hand on the
   * pole Sora passes first. The title screen's cords, in the forest.
   */
  private cordWeb(kit: Kit): void {
    const bamboo = this.scene.getMaterialByName("M_bamboo");
    if (!bamboo) return;
    const random = this.random;
    const poles = geo();
    const feet: Vector3[] = [];
    const leans: Vector3[] = [];
    for (const [x, z, height] of CORD_WEB.poles) {
      const foot = new Vector3(x, this.groundAt(x, z) - 0.25, z);
      const lean = new Vector3((random() - 0.5) * 0.1, 1, (random() - 0.5) * 0.1).normalize();
      feet.push(foot);
      leans.push(lean);
      tube(
        poles,
        [foot, foot.add(lean.scale(height + 0.25))],
        (i) => 0.045 - i * 0.012,
        8,
        () => 0,
        0,
        1,
        1,
      );
      this.boxes.push([foot.add(lean.scale(1.2)), new Vector3(0.16, 2.4, 0.16)]);
    }
    const poleMesh = this.mesh("omen_web_poles", poles, bamboo);
    const at = (pole: number, height: number) => feet[pole].add(leans[pole].scale(height + 0.25));
    const spans = CORD_WEB.spans.map(([p, hp, q, hq, sag]) => {
      const a = at(p, hp),
        b = at(q, hq);
      const points: Vector3[] = [];
      for (let i = 0; i <= 28; i++) {
        const t = i / 28;
        points.push(Vector3.Lerp(a, b, t).addInPlaceFromFloats(0, -4 * sag * t * (1 - t), 0));
      }
      // Lashing where it is tied to each pole.
      for (const [pole, end] of [
        [p, a],
        [q, b],
      ] as const)
        this.windThread(
          kit.cord,
          () => 0.05,
          feet[pole].add(new Vector3(0, 0, 0)),
          end.y - 0.03,
          2.5,
          0.06,
          random() * 6,
          0.004,
        );
      // The middle of a long cord swings furthest.
      tube(
        kit.cord,
        points,
        () => 0.006,
        5,
        (i) => 4 * sag * 1.4 * (i / 28) * (1 - i / 28),
        random() * 6,
        1,
        30,
      );
      return { points, length: Vector3.Distance(a, b), sag };
    });
    const ties = { red: geo(), white: geo() };
    for (const span of spans) {
      const along = (d: number) => span.points[Math.min(28, Math.round((d / span.length) * 28))];
      for (let d = 0.6 + random() * 0.6; d < span.length - 0.5; d += 0.9 + random() * 0.8)
        tassel(kit.hair, along(d).addInPlaceFromFloats(0, -0.008, 0), random);
      for (let d = 0.3 + random() * 0.3; d < span.length - 0.3; d += 0.45 + random() * 0.35) {
        const colour: "red" | "white" = random() < 0.65 ? "red" : "white";
        ribbon(
          ties[colour],
          along(d).addInPlaceFromFloats(0, -0.006, 0),
          0.18 + random() * 0.32,
          0.026 + random() * 0.02,
          random,
        );
      }
    }
    for (const [index, t, drop] of CORD_WEB.effigies) {
      const span = spans[index];
      const from = span.points[Math.round(t * 28)];
      tube(
        kit.cord,
        [from, from.add(new Vector3(0, -drop, 0))],
        () => 0.003,
        4,
        (i) => i * drop,
        0,
        1,
        30,
      );
      effigy(kit.effigy, from.add(new Vector3(0, -drop, 0)), drop, 1, random);
    }
    this.mesh("omen_web_ties_red", ties.red, kit.tieRed);
    this.mesh("omen_web_ties_white", ties.white, kit.tieWhite);
    // A hand pressed to the first pole, at the height of a hand, facing the path.
    if (poleMesh) {
      poleMesh.isPickable = true;
      const [x, z] = CORD_WEB.poles[0];
      const towards = Math.atan2(55.6 - z, -1.9 - x);
      const profile: TrunkProfile = { x, z, from: 0, to: 2, radii: [] };
      this.stain(
        profile,
        towards,
        feet[0].y + 1.55,
        new Vector3(0.22, 0.6, 0.4),
        kit.blood,
        poleMesh,
      );
      poleMesh.isPickable = false;
    }
  }

  private clothMaterial(
    name: string,
    colour: readonly [number, number, number],
    kind: FoliageKind = "cloth",
    frayed = true,
  ): PBRMaterial {
    const material = new PBRMaterial(name, this.scene);
    material.albedoTexture = this.texture(`T_${name}`, 256, 128, (ctx) =>
      paintCloth(ctx, 256, 128, colour, this.random),
    );
    if (frayed) {
      material.albedoTexture.hasAlpha = true;
      material.useAlphaFromAlbedoTexture = true;
      material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
      material.alphaCutOff = 0.4;
    }
    material.metallic = 0;
    material.roughness = 0.82;
    material.backFaceCulling = false;
    material.maxSimultaneousLights = 8;
    new FoliageWind(material, this.wind, kind);
    this.materials.push(material);
    return material;
  }

  private buildColliders(): void {
    if (!this.boxes.length) return;
    const anchor = new TransformNode("omen_body", this.scene);
    anchor.metadata = { surface: "leaves" };
    const body = new PhysicsBody(anchor, PhysicsMotionType.STATIC, false, this.scene);
    const shape = new PhysicsShapeContainer(this.scene);
    for (const [centre, size] of this.boxes)
      shape.addChild(new PhysicsShapeBox(centre, Quaternion.Identity(), size, this.scene));
    body.shape = shape;
    this.body = body;
    this.anchor = anchor;
  }
}
