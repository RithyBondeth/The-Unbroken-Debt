import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateGround } from "@babylonjs/core/Meshes/Builders/groundBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateTorusKnot } from "@babylonjs/core/Meshes/Builders/torusKnotBuilder";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { Scene } from "@babylonjs/core/scene";
import { addStaticBox } from "../../core/Physics";
import { makeSurfaceTextures } from "./textures";

export interface Hall {
  /** Meshes that never cast shadows (flames, glass, small detail props). */
  noShadow: Set<Mesh>;
  flamePositions: Vector3[];
  candlePositions: Vector3[];
  spawn: Vector3;
  /** Camera path for the benchmark: eye positions around the coffin. */
  benchPath: Vector3[];
  benchLookAt: Vector3;
}

const W = 12; // hall width (x)
const D = 9; // hall depth (z)
const H = 3.2; // wall height
const MAX_LIGHTS = 8; // lamp + 4 flames + clustered container + moonlight, with headroom

/**
 * A night funeral hall inside a stilt house, sized towards the Development Plan
 * budgets (about 1,000 draw calls and 2–3 million triangles in view): carved
 * wall panels, posts and beams, the coffin under a white canopy, an altar with
 * offerings, candles, incense and a brazier, with the courtyard beyond the door.
 * Shapes are stand-ins; the cost is what matters here.
 */
export function buildHall(scene: Scene, candleCount: number): Hall {
  const noShadow = new Set<Mesh>();
  const wood = makeSurfaceTextures(scene, "wood", 1024, [0.18, 0.1, 0.05], [0.45, 0.28, 0.15]);
  const cloth = makeSurfaceTextures(scene, "cloth", 512, [0.75, 0.73, 0.68], [0.95, 0.94, 0.9]);
  const stone = makeSurfaceTextures(scene, "stone", 1024, [0.25, 0.24, 0.22], [0.5, 0.48, 0.44]);

  const mat = {
    floor: pbr(scene, "M_floor", { tex: wood, roughness: 0.7, uv: [4, 0.5] }),
    wall: pbr(scene, "M_wall", {
      tex: wood,
      roughness: 0.8,
      uv: [1, 2],
      tint: new Color3(0.9, 0.8, 0.7),
    }),
    dark: pbr(scene, "M_darkWood", {
      tex: wood,
      roughness: 0.6,
      uv: [1, 3],
      tint: new Color3(0.5, 0.4, 0.35),
    }),
    cloth: pbr(scene, "M_cloth", { tex: cloth, roughness: 0.95, uv: [4, 4], twoSided: true }),
    saffron: pbr(scene, "M_saffron", {
      tex: cloth,
      roughness: 0.9,
      uv: [3, 3],
      tint: new Color3(0.95, 0.55, 0.15),
      twoSided: true,
    }),
    stone: pbr(scene, "M_stone", { tex: stone, roughness: 0.85, uv: [2, 2] }),
    ground: pbr(scene, "M_ground", {
      tex: stone,
      roughness: 0.95,
      uv: [20, 20],
      tint: new Color3(0.45, 0.38, 0.3),
    }),
    brass: pbr(scene, "M_brass", {
      color: new Color3(0.78, 0.6, 0.3),
      roughness: 0.35,
      metallic: 1,
    }),
    ceramic: pbr(scene, "M_ceramic", { color: new Color3(0.8, 0.78, 0.7), roughness: 0.25 }),
    fruit: pbr(scene, "M_fruit", { color: new Color3(0.8, 0.45, 0.1), roughness: 0.5 }),
    leaf: pbr(scene, "M_leaf", { color: new Color3(0.2, 0.4, 0.12), roughness: 0.6 }),
    wax: pbr(scene, "M_wax", { color: new Color3(0.93, 0.9, 0.82), roughness: 0.4 }),
    flame: pbr(scene, "M_flame", {
      color: Color3.Black(),
      roughness: 1,
      emissive: new Color3(4, 1.8, 0.6),
    }),
  };

  // Small detail props receive shadows but don't cast them: their shadows are
  // barely visible and re-rendering them into six cube faces per light is costly.
  const detail = (mesh: Mesh) => {
    noShadow.add(mesh);
    return mesh;
  };
  const add = (mesh: Mesh, material: PBRMaterial, collide = false) => {
    mesh.material = material;
    mesh.receiveShadows = true;
    mesh.freezeWorldMatrix();
    if (collide) addStaticBox(mesh, "teak");
    return mesh;
  };

  // Floor planks, ceiling boards, beams and posts.
  for (let i = 0, z = -D / 2; z < D / 2 - 0.1; z += 0.15, i++) {
    const plank = CreateBox(`plank_${i}`, { width: W, height: 0.04, depth: 0.14 }, scene);
    plank.position.set(0, -0.02, z + 0.07);
    add(plank, mat.floor);
  }
  const floorCollider = CreateBox("floor_col", { width: W, height: 0.2, depth: D }, scene);
  floorCollider.position.y = -0.1;
  floorCollider.isVisible = false;
  addStaticBox(floorCollider, "teak");

  for (let i = 0, z = -D / 2; z < D / 2; z += 0.3, i++) {
    const board = CreateBox(`ceiling_${i}`, { width: W, height: 0.03, depth: 0.28 }, scene);
    board.position.set(0, H + 0.4, z + 0.15);
    add(board, mat.dark);
  }
  for (let x = -W / 2 + 1; x < W / 2; x += 1) {
    add(
      CreateBox(`rafter_${x}`, { width: 0.12, height: 0.18, depth: D }, scene),
      mat.dark,
    ).position.set(x, H + 0.3, 0);
  }
  for (let z = -D / 2 + 1.5; z < D / 2; z += 1.5) {
    add(
      CreateBox(`beam_${z}`, { width: W, height: 0.22, depth: 0.16 }, scene),
      mat.dark,
    ).position.set(0, H + 0.1, z);
  }
  for (const x of [-4.5, -1.5, 1.5, 4.5]) {
    for (const z of [-2.5, 2.5]) {
      const post = CreateCylinder(
        `post_${x}_${z}`,
        { diameter: 0.3, height: H + 0.4, tessellation: 48 },
        scene,
      );
      post.position.set(x, (H + 0.4) / 2, z);
      add(post, mat.dark);
      const collider = CreateBox(
        `post_col_${x}_${z}`,
        { width: 0.3, height: H, depth: 0.3 },
        scene,
      );
      collider.position.set(x, H / 2, z);
      collider.isVisible = false;
      addStaticBox(collider, "teak");
      // Carved band around each post (dense, like hand-carved teak).
      const band = CreateTorusKnot(
        `carving_${x}_${z}`,
        { radius: 0.2, tube: 0.035, radialSegments: 256, tubularSegments: 48, p: 2, q: 9 },
        scene,
      );
      band.position.set(x, 1.9, z);
      band.rotation.x = Math.PI / 2;
      detail(add(band, mat.brass));
    }
  }

  // Carved wall panels with relief, and invisible wall colliders. Door in the south wall.
  const panelW = 1.5;
  const wallPanel = (name: string, x: number, z: number, rotY: number) => {
    const panel = reliefPanel(scene, name, panelW, H, 112);
    panel.position.set(x, H / 2, z);
    panel.rotation.y = rotY;
    add(panel, mat.wall);
  };
  for (let x = -W / 2 + panelW / 2; x < W / 2; x += panelW) {
    wallPanel(`panel_n_${x}`, x, D / 2, 0);
    if (Math.abs(x) > 1) wallPanel(`panel_s_${x}`, x, -D / 2, Math.PI);
  }
  for (let z = -D / 2 + panelW / 2; z < D / 2; z += panelW) {
    wallPanel(`panel_e_${z}`, W / 2, z, Math.PI / 2);
    wallPanel(`panel_w_${z}`, -W / 2, z, -Math.PI / 2);
  }
  for (const [name, x, z, w, d] of [
    ["wall_n", 0, D / 2 + 0.1, W, 0.2],
    ["wall_s_l", -3.75, -D / 2 - 0.1, 4.5, 0.2],
    ["wall_s_r", 3.75, -D / 2 - 0.1, 4.5, 0.2],
    ["wall_e", W / 2 + 0.1, 0, 0.2, D],
    ["wall_w", -W / 2 - 0.1, 0, 0.2, D],
  ] as const) {
    const wall = CreateBox(name, { width: w, height: H, depth: d }, scene);
    wall.position.set(x, H / 2, z);
    wall.isVisible = false;
    addStaticBox(wall, "teak");
  }

  // The coffin on its stand, with carved ornaments, under a white canopy.
  const stand = add(
    CreateBox("coffin_stand", { width: 1, height: 0.5, depth: 2.4 }, scene),
    mat.dark,
    true,
  );
  stand.position.y = 0.25;
  add(CreateBox("coffin", { width: 0.8, height: 0.6, depth: 2.1 }, scene), mat.dark).position.y =
    0.8;
  add(
    CreateBox("coffin_lid", { width: 0.9, height: 0.12, depth: 2.2 }, scene),
    mat.wall,
  ).position.y = 1.16;
  for (let i = 0; i < 8; i++) {
    const ornament = CreateTorusKnot(
      `coffin_orn_${i}`,
      { radius: 0.09, tube: 0.025, radialSegments: 256, tubularSegments: 32 },
      scene,
    );
    ornament.position.set(i < 4 ? -0.42 : 0.42, 0.85, -0.75 + (i % 4) * 0.5);
    ornament.rotation.z = Math.PI / 2;
    detail(add(ornament, mat.brass));
  }
  for (const [i, y] of [
    [0, 2.6],
    [1, 2.75],
  ]) {
    const canopy = drapedCloth(scene, `canopy_${i}`, 2.6 - i * 0.4, 3.6 - i * 0.4, 96);
    canopy.position.y = y;
    add(canopy, i === 0 ? mat.cloth : mat.saffron);
  }

  // Altar against the north wall: tiers with bowls, fruit, urns and guardian figures.
  for (let tier = 0; tier < 3; tier++) {
    const top = add(
      CreateBox(
        `altar_${tier}`,
        { width: 4 - tier, height: 0.08, depth: 0.7 - tier * 0.15 },
        scene,
      ),
      mat.dark,
    );
    top.position.set(0, 0.8 + tier * 0.35, D / 2 - 0.6 + tier * 0.12);
    const leg = add(
      CreateBox(
        `altar_leg_${tier}`,
        { width: 4 - tier, height: 0.8 + tier * 0.35, depth: 0.08 },
        scene,
      ),
      mat.dark,
    );
    leg.position.set(0, (0.8 + tier * 0.35) / 2, D / 2 - 0.3);
  }
  const altarCollider = CreateBox("altar_col", { width: 4, height: 1.6, depth: 1 }, scene);
  altarCollider.position.set(0, 0.8, D / 2 - 0.5);
  altarCollider.isVisible = false;
  addStaticBox(altarCollider, "teak");
  for (let i = 0; i < 24; i++) {
    const bowl = CreateSphere(`bowl_${i}`, { diameter: 0.16, segments: 48, slice: 0.5 }, scene);
    bowl.rotation.x = Math.PI;
    bowl.position.set(
      -1.8 + (i % 12) * 0.33,
      0.92 + Math.floor(i / 12) * 0.35,
      D / 2 - 0.65 + Math.floor(i / 12) * 0.12,
    );
    detail(add(bowl, mat.brass));
    for (let f = 0; f < 2; f++) {
      const fruit = CreateSphere(`fruit_${i}_${f}`, { diameter: 0.07, segments: 32 }, scene);
      fruit.position.set(
        bowl.position.x - 0.02 + f * 0.04,
        bowl.position.y + 0.04,
        bowl.position.z,
      );
      detail(add(fruit, mat.fruit));
    }
  }
  const urnProfile = [0, 0.05, 0.09, 0.11, 0.1, 0.07, 0.05, 0.06, 0.08, 0.07, 0].map(
    (r, i) => new Vector3(r, i * 0.035, 0),
  );
  for (let i = 0; i < 12; i++) {
    const urn = CreateLathe(`urn_${i}`, { shape: urnProfile, tessellation: 64 }, scene);
    urn.position.set(-1.6 + (i % 6) * 0.64, 1.62, D / 2 - 0.38);
    if (i >= 6) urn.position.set(-5 + (i - 6) * 2, 0, D / 2 - 0.35);
    detail(add(urn, mat.ceramic));
  }
  for (let i = 0; i < 6; i++) {
    const x = -5 + i * 2;
    const base = add(
      CreateCylinder(`guardian_base_${i}`, { diameter: 0.4, height: 0.5, tessellation: 64 }, scene),
      mat.stone,
    );
    base.position.set(x, 0.25, -D / 2 + 0.45);
    if (Math.abs(x) < 1.2) base.position.x = x < 0 ? -1.6 : 1.6;
    const body = add(
      CreateSphere(
        `guardian_body_${i}`,
        { diameterX: 0.36, diameterY: 0.7, diameterZ: 0.3, segments: 64 },
        scene,
      ),
      mat.stone,
    );
    body.position.set(base.position.x, 0.85, base.position.z);
    const head = add(
      CreateTorusKnot(
        `guardian_head_${i}`,
        { radius: 0.1, tube: 0.04, radialSegments: 256, tubularSegments: 48, p: 3, q: 4 },
        scene,
      ),
      mat.stone,
    );
    head.position.set(base.position.x, 1.3, base.position.z);
  }

  // Betel trays, floor mats, cushions and incense.
  for (let i = 0; i < 8; i++) {
    const angle = (i / 8) * Math.PI * 2;
    const x = Math.cos(angle) * 2.6;
    const z = Math.sin(angle) * 2.2;
    detail(
      add(
        CreateCylinder(`tray_${i}`, { diameter: 0.45, height: 0.05, tessellation: 64 }, scene),
        mat.brass,
      ),
    ).position.set(x, 0.03, z);
    for (let l = 0; l < 5; l++) {
      const leaf = CreateCylinder(
        `betel_${i}_${l}`,
        { diameterTop: 0, diameterBottom: 0.08, height: 0.12, tessellation: 24 },
        scene,
      );
      leaf.position.set(x + Math.cos(l * 1.26) * 0.12, 0.1, z + Math.sin(l * 1.26) * 0.12);
      detail(add(leaf, mat.leaf));
    }
  }
  for (let i = 0; i < 6; i++) {
    const m = detail(
      add(CreateBox(`mat_${i}`, { width: 1.8, height: 0.015, depth: 1 }, scene), mat.saffron),
    );
    m.position.set(i < 3 ? -3.2 : 3.2, 0.008, -1.4 + (i % 3) * 1.4);
  }
  for (let i = 0; i < 16; i++) {
    const cushion = CreateSphere(
      `cushion_${i}`,
      { diameterX: 0.5, diameterY: 0.14, diameterZ: 0.35, segments: 32 },
      scene,
    );
    cushion.position.set(
      i < 8 ? -3.8 + (i % 2) * 1.2 : 3.8 - (i % 2) * 1.2,
      0.08,
      -1.6 + (Math.floor(i / 2) % 4) * 1.0,
    );
    detail(add(cushion, mat.cloth));
  }
  for (let i = 0; i < 10; i++) {
    const pot = detail(
      add(
        CreateCylinder(
          `incense_pot_${i}`,
          { diameterTop: 0.18, diameterBottom: 0.12, height: 0.14, tessellation: 48 },
          scene,
        ),
        mat.brass,
      ),
    );
    pot.position.set(-2.25 + i * 0.5, 0.88, D / 2 - 0.95);
    for (let s = 0; s < 3; s++) {
      const stick = CreateCylinder(
        `incense_${i}_${s}`,
        { diameter: 0.006, height: 0.3, tessellation: 6 },
        scene,
      );
      stick.position.set(pot.position.x - 0.03 + s * 0.03, 1.08, pot.position.z);
      stick.rotation.z = (s - 1) * 0.15;
      add(stick, mat.dark);
      noShadow.add(stick);
    }
  }

  // The four shadowed flames: two tall candle stands by the coffin, the altar lamp, a brazier by the door.
  const flamePositions = [
    new Vector3(-1.4, 1.55, -1.3),
    new Vector3(1.4, 1.55, -1.3),
    new Vector3(0, 1.62, D / 2 - 0.9),
    new Vector3(3, 0.95, -D / 2 + 1),
  ];
  for (const [i, p] of flamePositions.entries()) {
    const holderHeight = p.y - 0.12;
    if (i < 2)
      add(
        CreateCylinder(
          `candle_stand_${i}`,
          { diameter: 0.08, height: holderHeight, tessellation: 32 },
          scene,
        ),
        mat.brass,
      ).position.set(p.x, holderHeight / 2, p.z);
    if (i === 3) {
      add(
        CreateCylinder(
          "brazier",
          { diameterTop: 0.6, diameterBottom: 0.3, height: 0.5, tessellation: 64 },
          scene,
        ),
        mat.brass,
      ).position.set(p.x, 0.55, p.z);
      add(
        CreateCylinder("brazier_leg", { diameter: 0.12, height: 0.35, tessellation: 24 }, scene),
        mat.dark,
      ).position.set(p.x, 0.17, p.z);
    }
    noShadow.add(flameMesh(scene, `flame_${i}`, p, i === 3 ? 0.18 : 0.05, mat.flame));
  }

  // Small candles for the clustered lights: along the walls and around the coffin.
  const candlePositions: Vector3[] = [];
  for (let i = 0; i < candleCount; i++) {
    const t = i / candleCount;
    let p: Vector3;
    if (i % 3 === 0) {
      const angle = t * Math.PI * 2 * 3;
      p = new Vector3(Math.cos(angle) * 1.2, 0.02, Math.sin(angle) * 1.8);
    } else {
      const perimeter = 2 * (W - 1 + D - 1);
      let s = (t * perimeter * 1.37) % perimeter;
      if (s < W - 1) p = new Vector3(-W / 2 + 0.5 + s, 0.02, D / 2 - 1.2);
      else if ((s -= W - 1) < D - 1) p = new Vector3(W / 2 - 0.4, 0.02, -D / 2 + 0.5 + s);
      else if ((s -= D - 1) < W - 1) p = new Vector3(W / 2 - 0.5 - s, 0.02, -D / 2 + 0.4);
      else p = new Vector3(-W / 2 + 0.4, 0.02, D / 2 - 0.5 - (s - (W - 1)));
    }
    const candle = detail(
      add(
        CreateCylinder(`candle_${i}`, { diameter: 0.04, height: 0.12, tessellation: 16 }, scene),
        mat.wax,
      ),
    );
    candle.position.set(p.x, 0.06, p.z);
    const flamePos = new Vector3(p.x, 0.15, p.z);
    noShadow.add(flameMesh(scene, `candle_flame_${i}`, flamePos, 0.02, mat.flame));
    candlePositions.push(flamePos.add(new Vector3(0, 0.05, 0)));
  }

  // Courtyard beyond the door: wet ground and the funeral tent posts in the fog.
  const ground = CreateGround("courtyard", { width: 40, height: 30, subdivisions: 256 }, scene);
  ground.position.set(0, -0.6, -D / 2 - 15);
  add(ground, mat.ground);
  for (let i = 0; i < 8; i++) {
    const tentPost = CreateCylinder(
      `tent_post_${i}`,
      { diameter: 0.14, height: 3.5, tessellation: 24 },
      scene,
    );
    tentPost.position.set(-6 + (i % 4) * 4, 1.15, -D / 2 - 6 - Math.floor(i / 4) * 6);
    add(tentPost, mat.dark);
  }

  return {
    noShadow,
    flamePositions,
    candlePositions,
    spawn: new Vector3(0, 0, -D / 2 + 1),
    benchPath: [
      new Vector3(0, 1.58, -3.6),
      new Vector3(-3.6, 1.58, -2.8),
      new Vector3(-4.2, 1.58, 1.2),
      new Vector3(-2, 1.58, 3.2),
      new Vector3(2, 1.58, 3.2),
      new Vector3(4.2, 1.58, 1.2),
      new Vector3(3.6, 1.58, -2.8),
    ],
    benchLookAt: new Vector3(0, 1, 0.5),
  };
}

interface PbrOptions {
  tex?: { albedo: Texture; normal: Texture };
  color?: Color3;
  tint?: Color3;
  roughness: number;
  metallic?: number;
  emissive?: Color3;
  uv?: [number, number];
  /** Cloth seen from both sides (the canopy is viewed from below). */
  twoSided?: boolean;
}

function pbr(scene: Scene, name: string, o: PbrOptions): PBRMaterial {
  const m = new PBRMaterial(name, scene);
  m.maxSimultaneousLights = MAX_LIGHTS;
  m.metallic = o.metallic ?? 0;
  m.roughness = o.roughness;
  m.albedoColor = o.tint ?? o.color ?? Color3.White();
  if (o.tex) {
    const [u, v] = o.uv ?? [1, 1];
    const albedo = o.tex.albedo.clone();
    albedo.uScale = u;
    albedo.vScale = v;
    const normal = o.tex.normal.clone();
    normal.uScale = u;
    normal.vScale = v;
    m.albedoTexture = albedo;
    m.bumpTexture = normal;
  }
  if (o.twoSided) {
    m.backFaceCulling = false;
    m.twoSidedLighting = true;
  }
  if (o.emissive) {
    m.emissiveColor = o.emissive;
    m.disableLighting = true;
  }
  return m;
}

function flameMesh(
  scene: Scene,
  name: string,
  p: Vector3,
  size: number,
  material: PBRMaterial,
): Mesh {
  const flame = CreateSphere(
    name,
    { diameterX: size, diameterY: size * 2.2, diameterZ: size, segments: 8 },
    scene,
  );
  flame.position.copyFrom(p);
  flame.material = material;
  flame.isPickable = false;
  return flame;
}

/** A vertical panel with carved relief, displaced from a subdivided plane. */
function reliefPanel(
  scene: Scene,
  name: string,
  width: number,
  height: number,
  subdivisions: number,
): Mesh {
  const panel = CreateGround(name, { width, height, subdivisions, updatable: true }, scene);
  const positions = panel.getVerticesData(VertexBuffer.PositionKind) as Float32Array;
  for (let i = 0; i < positions.length; i += 3) {
    const x = positions[i] / width + 0.5;
    const z = positions[i + 2] / height + 0.5;
    // Lotus-like repeating carving with a raised frame.
    const frame = Math.min(x, 1 - x, z, 1 - z) < 0.06 ? 0.02 : 0;
    const carving =
      Math.sin(x * Math.PI * 6) *
      Math.sin(z * Math.PI * 10) *
      Math.cos((x + z) * Math.PI * 8) *
      0.012;
    positions[i + 1] = frame + carving;
  }
  const indices = panel.getIndices() ?? [];
  const normals: number[] = [];
  VertexData.ComputeNormals(positions, indices, normals);
  panel.setVerticesData(VertexBuffer.PositionKind, positions);
  panel.setVerticesData(VertexBuffer.NormalKind, normals);
  // Stand the panel up, relief facing into the room (-Z before the caller's rotation).
  panel.rotation.x = -Math.PI / 2;
  panel.bakeCurrentTransformIntoVertices();
  return panel;
}

/** A sagging cloth canopy: a subdivided plane hanging between four corners. */
function drapedCloth(
  scene: Scene,
  name: string,
  width: number,
  depth: number,
  subdivisions: number,
): Mesh {
  const cloth = CreateGround(name, { width, height: depth, subdivisions, updatable: true }, scene);
  const positions = cloth.getVerticesData(VertexBuffer.PositionKind) as Float32Array;
  for (let i = 0; i < positions.length; i += 3) {
    const x = positions[i] / width;
    const z = positions[i + 2] / depth;
    const sag = (0.25 - x * x) * (0.25 - z * z) * 3.2;
    const folds = Math.sin(x * 40) * 0.01 + Math.sin(z * 30) * 0.008;
    positions[i + 1] = -sag + folds;
  }
  const indices = cloth.getIndices() ?? [];
  const normals: number[] = [];
  VertexData.ComputeNormals(positions, indices, normals);
  cloth.setVerticesData(VertexBuffer.PositionKind, positions);
  cloth.setVerticesData(VertexBuffer.NormalKind, normals);
  return cloth;
}
