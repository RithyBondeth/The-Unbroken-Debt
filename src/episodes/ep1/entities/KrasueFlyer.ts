import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { realiseInstances } from "@/core/areaLoader";
import { krasueScreamMouth } from "@/shared/entities/krasueExpression";
import { KrasueGlide, STRAND_STEP, Strand, type StrandSpec } from "./krasueMotion";

const assets = new WeakMap<Scene, AssetContainer>();

/** Each lock of hair: wet and heavy, stiff at the scalp, looser at the tips, combed by the air. */
const HAIR: Omit<StrandSpec, "seed"> = {
  stiffness: [0, 95, 62, 42, 30, 22],
  drag: 2.4,
  gravity: 1.1,
  wind: 1.6,
  slack: [0, 0.07, 0.16, 0.26, 0.36, 0.45],
  slackRatio: 0.22,
};
/** The viscera: heavy, hanging, a pendulum that swings long after the head has stopped. */
const GUT: Omit<StrandSpec, "seed"> = {
  stiffness: [0, 16, 13, 11, 10, 9],
  drag: 1.25,
  gravity: 0,
  wind: 0.35,
  slack: [0, 0.1, 0.22, 0.34, 0.46, 0.55],
  slackRatio: 0.6,
};

interface Chain {
  nodes: TransformNode[];
  /** Each joint's rest rotation and its child's offset in the joint's own frame. */
  rest: Quaternion[];
  child: Vector3[];
  /** What carries the chain's rest shape: the head (hair) or the throat (viscera). */
  anchor: TransformNode;
  restInAnchor: Vector3[];
  targets: Vector3[];
  strand: Strand;
  gut: boolean;
}

const smoothstep = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/**
 * Episode 1's Krasue: the user's model (tools/characters/build-krasue.py), every joint
 * moved here, with no clips. Its flight is the brain's, smoothed into something with
 * weight (KrasueGlide): it leans into a swoop, banks round a turn, bobs as it hangs in
 * the air. The head turns on the neck to find Sora and tilts as it watches; the jaw works;
 * the hair streams behind and lifts in the gusts; the viscera hang and swing under it and
 * settle late; the heart beats and the lungs fill. A pale glow travels with it and lights
 * the window frames as it comes.
 */
export class KrasueFlyer {
  readonly root: TransformNode;
  readonly meshes: AbstractMesh[];
  readonly ready = true;
  /** The light that travels with it (the world around the windows, and itself). */
  readonly glow: PointLight;
  mouthOpen = 0;
  private readonly glide = new KrasueGlide();
  private readonly chains: Chain[] = [];
  private readonly head: TransformNode;
  private readonly jaw: TransformNode;
  private readonly heart: TransformNode | null;
  private readonly lungs: TransformNode[];
  private readonly headRest: Quaternion;
  private readonly jawRest: Quaternion;
  /** Armature-space rest rotations of the head's and the jaw's parents. */
  private readonly headFrame: Quaternion;
  private readonly jawFrame: Quaternion;
  private readonly throat: TransformNode;
  private readonly materials: PBRMaterial[] = [];
  private readonly gutOffsets: Vector3[] = [];
  private readonly forward = new Vector3(0, 0, 1);
  private readonly up = new Vector3(0, 1, 0);
  private readonly look = Quaternion.Identity();
  private yaw = 0;
  private yawSpeed = 0;
  private lastTime = -1;
  private wasEnabled = false;
  private accumulator = 0;
  private visible = 0;
  private watch = 0;
  /** The wall it hovers at: its body never drifts nearer than the brain's point. */
  private readonly wall = { centre: new Vector3(), normal: new Vector3(), set: false };

  static async prepare(scene: Scene): Promise<void> {
    if (assets.has(scene)) return;
    const container = await LoadAssetContainerAsync(
      `${import.meta.env.BASE_URL}assets/ep1/krasue.glb`,
      scene,
    );
    realiseInstances(container);
    assets.set(scene, container);
    scene.onDisposeObservable.addOnce(() => container.dispose());
  }

  constructor(scene: Scene) {
    const asset = assets.get(scene);
    if (!asset) throw new Error("Prepare the Krasue GLB before constructing its encounter");
    this.root = new TransformNode("krasue", scene);
    this.root.rotationQuaternion = Quaternion.Identity();
    asset.addAllToScene();
    // The model faces glTF +Z, which the loader's root keeps as +Z here.
    for (const node of [...asset.transformNodes, ...asset.meshes])
      if (!node.parent) node.parent = this.root;
    this.meshes = asset.meshes.filter((m) => m.getTotalVertices() > 0);
    for (const mesh of this.meshes) {
      mesh.isPickable = false;
      // A skinned mesh keeps its bind-pose bounds: never cull the streaming hair.
      mesh.alwaysSelectAsActiveMesh = true;
    }
    for (const material of asset.materials) {
      if (!(material instanceof PBRMaterial)) continue;
      material.maxSimultaneousLights = 8;
      material.useAlphaFromAlbedoTexture = false;
      material.transparencyMode = PBRMaterial.PBRMATERIAL_OPAQUE;
      material.enableSpecularAntiAliasing = true;
      material.emissiveIntensity = 0.3;
      this.materials.push(material);
    }
    const byName = new Map(asset.transformNodes.map((n) => [n.name, n]));
    const node = (name: string) => {
      const found = byName.get(name);
      if (!found) throw new Error(`The Krasue GLB has no joint ${name}`);
      if (!found.rotationQuaternion)
        found.rotationQuaternion = Quaternion.FromEulerVector(found.rotation);
      return found;
    };
    this.head = node("krasue_head");
    this.jaw = node("krasue_jaw");
    this.throat = node("krasue_root");
    this.heart = byName.get("krasue_heart") ?? null;
    this.lungs = ["krasue_lung_L", "krasue_lung_R"].flatMap((n) => byName.get(n) ?? []);
    this.headRest = this.head.rotationQuaternion!.clone();
    this.jawRest = this.jaw.rotationQuaternion!.clone();
    this.headFrame = armatureRotation(this.head.parent as TransformNode);
    this.jawFrame = armatureRotation(this.head);
    this.refresh(this.root);

    const chain = (names: string[], anchor: TransformNode, gut: boolean, seed: number) => {
      const nodes = names.map(node);
      const spec = { ...(gut ? GUT : HAIR), seed };
      const restInAnchor = nodes.map((n) =>
        Vector3.TransformCoordinates(
          n.getAbsolutePosition(),
          Matrix.Invert(anchor.getWorldMatrix()),
        ),
      );
      this.chains.push({
        nodes,
        rest: nodes.map((n) => n.rotationQuaternion!.clone()),
        child: nodes.map((_, i) => (nodes[i + 1] ? nodes[i + 1].position.clone() : Vector3.Zero())),
        anchor,
        restInAnchor,
        targets: nodes.map(() => new Vector3()),
        strand: new Strand(nodes.length, spec),
        gut,
      });
    };
    // Strands by their bearing round the head (short hair by the face has none).
    for (const k of [...byName.keys()]
      .map((n) => /^krasue_hair_(\d+)_0$/.exec(n)?.[1])
      .filter((k): k is string => k !== undefined)
      .sort((a, b) => Number(a) - Number(b))) {
      const names: string[] = [];
      for (let j = 0; byName.has(`krasue_hair_${k}_${j}`); j++) names.push(`krasue_hair_${k}_${j}`);
      names.push(`krasue_hair_${k}_end`);
      chain(names, this.head, false, Number(k) * 1.37);
    }
    const gut: string[] = [];
    for (let j = 0; byName.has(`krasue_gut_${j}`); j++) gut.push(`krasue_gut_${j}`);
    gut.push("krasue_gut_end");
    chain(gut, this.throat, true, 7.1);
    // The viscera hang from the throat whatever the head does: their rest places are
    // kept relative to it, turned only with the heading.
    const top = this.throat.getAbsolutePosition();
    for (const n of gut.map(node)) this.gutOffsets.push(n.getAbsolutePosition().subtract(top));

    // Moonlight caught on the face from the side, and a cold rim behind it: its own.
    const key = new PointLight("krasue_moonlit_face", new Vector3(-0.45, 0.5, 0.95), scene);
    key.parent = this.root;
    key.diffuse.set(0.55, 0.65, 0.61);
    key.specular.set(0.12, 0.14, 0.13);
    key.intensity = 1.0;
    key.range = 3.4;
    key.renderPriority = 10;
    key.includedOnlyMeshes = this.meshes;
    const rim = new PointLight("krasue_moon_rim", new Vector3(0.5, -0.3, -0.8), scene);
    rim.parent = this.root;
    rim.diffuse.set(0.33, 0.43, 0.46);
    rim.specular.set(0.28, 0.34, 0.36);
    rim.intensity = 0.75;
    rim.range = 3.2;
    rim.renderPriority = 10;
    rim.includedOnlyMeshes = this.meshes;
    // The glow it carries: never disabled (that would rebuild every lit material's
    // shader), only dimmed to nothing while it is away.
    this.glow = new PointLight("krasue_glow", Vector3.Zero(), scene);
    this.glow.diffuse.set(0.48, 0.72, 0.58);
    this.glow.specular.set(0.3, 0.42, 0.34);
    this.glow.intensity = 0;
    this.glow.range = 5.5;
    this.glow.renderPriority = 2;
    this.glow.shadowEnabled = false;
    this.glow.includedOnlyMeshes = [...this.meshes];
    scene.onBeforeRenderObservable.add(() => {
      if (!this.root.isEnabled()) this.glow.intensity = 0;
    });
    this.root.setEnabled(false);
  }

  /**
   * The window it comes to. Braking from its swoop, the smoothed body would sail on
   * toward the glass; it may drift sideways and back, but never nearer the wall than
   * the brain's own point (less a hand's breadth).
   */
  keepOutside(centre: Vector3, normal: Vector3): void {
    this.wall.centre.copyFrom(centre);
    this.wall.normal.copyFrom(normal);
    this.wall.set = true;
  }

  private keepOff(brain: Vector3): void {
    if (!this.wall.set) return;
    const { centre, normal } = this.wall;
    const g = this.glide;
    const least = Vector3.Dot(brain.subtract(centre), normal) - 0.1;
    const depth = Vector3.Dot(g.position.subtract(centre), normal);
    if (depth >= least) return;
    g.position.addInPlace(normal.scale(least - depth));
    const toward = Vector3.Dot(g.velocity, normal);
    if (toward < 0) g.velocity.subtractInPlace(normal.scale(toward));
  }

  /** The glow lights these too (the walls and frames round the windows). */
  lightAround(meshes: readonly AbstractMesh[]): void {
    this.glow.includedOnlyMeshes = [...this.meshes, ...meshes];
  }

  /** Flight heading reveals cheeks and profile; an alerted head turns toward Sora. */
  pose(
    position: Vector3,
    target: Vector3,
    time: number,
    attack: boolean,
    flight?: Vector3,
    watching = false,
    screamAge = -1,
  ): void {
    const gap = this.lastTime < 0 || time < this.lastTime ? 1 : time - this.lastTime;
    const dt = Math.min(0.1, gap);
    this.lastTime = time;
    // Away over the fields it is neither drawn nor moved; it starts afresh when it comes.
    if (!this.root.isEnabled()) {
      this.wasEnabled = false;
      this.glow.intensity = 0;
      return;
    }
    const fresh = !this.wasEnabled || gap > 0.5;
    this.wasEnabled = true;
    if (fresh) {
      this.glide.reset(position);
      this.visible = 0;
    } else {
      this.glide.update(dt, position, attack ? 13 : 7);
      this.keepOff(position);
    }
    this.mouthOpen = krasueScreamMouth(screamAge);
    this.watch += ((watching || attack ? 1 : 0) - this.watch) * (1 - Math.exp(-dt * 4));

    this.flight(fresh ? 0 : dt, time, target, attack, watching, flight);
    this.refresh(this.root);
    this.lookAt(dt, time, target, attack);
    this.workJaw(time);
    this.refresh(this.head);
    this.simulate(dt, time, fresh);
    this.breathe(time, attack);

    // The glow comes up as it nears out of the dark, and breathes; the eyes burn
    // brighter while it watches and flare as it shrieks.
    this.visible = Math.min(1, this.visible + dt * 1.8);
    const flicker =
      0.9 + 0.07 * Math.sin(time * 2.3) + 0.03 * Math.sin(time * 5.9 + 1.3 * Math.sin(time * 0.7));
    this.glow.intensity = this.visible * (0.7 + 0.3 * this.watch) * flicker;
    Vector3.TransformCoordinatesFromFloatsToRef(
      0,
      -0.62,
      0.12,
      this.root.getWorldMatrix(),
      this.glow.position,
    );
    const eyes = 0.28 + 0.6 * this.watch + 0.9 * this.mouthOpen;
    for (const material of this.materials) material.emissiveIntensity = eyes;
  }

  /** Where it is and how it holds itself in the air. */
  private flight(
    dt: number,
    time: number,
    target: Vector3,
    attack: boolean,
    watching: boolean,
    flight?: Vector3,
  ): void {
    const g = this.glide;
    const speed = Math.hypot(g.velocity.x, g.velocity.z);
    // It hangs in the air the way nothing that flies can: a slow, uneven bob, strongest
    // when it is all but still.
    const hover = 1 - smoothstep(0.6, 3.5, speed);
    this.root.position.copyFrom(g.position);
    this.root.position.y +=
      hover * (0.045 * Math.sin(time * 1.55) + 0.018 * Math.sin(time * 2.71 + 1.1));
    this.root.position.x += hover * 0.02 * Math.sin(time * 0.93 + 0.4);
    // Facing: down its flight when it travels fast, at the house (or at Sora) as it hangs
    // there, so its drifting side to side never spins it round.
    const toTarget = target.subtract(g.position);
    toTarget.y = 0;
    const along =
      speed > 0.3
        ? new Vector3(g.velocity.x, 0, g.velocity.z)
        : flight
          ? new Vector3(flight.x, 0, flight.z)
          : toTarget.clone();
    const face = attack || watching ? 1 : 1 - smoothstep(1.2, 5, speed);
    const want = along
      .normalizeToNew()
      .scaleInPlace(1 - face)
      .addInPlace(toTarget.normalizeToNew().scaleInPlace(face));
    if (want.lengthSquared() > 1e-6) {
      const desired = Math.atan2(want.x, want.z);
      if (dt === 0) {
        // A first sight: already on its heading, level, its head forward.
        this.yaw = desired;
        this.yawSpeed = 0;
        this.up.set(0, 1, 0);
        this.look.set(0, 0, 0, 1);
      }
      const w = attack ? 9 : 3.2;
      const error = Math.atan2(Math.sin(desired - this.yaw), Math.cos(desired - this.yaw));
      this.yawSpeed += (w * w * error - 2 * w * this.yawSpeed) * dt;
      this.yaw += this.yawSpeed * dt;
    }
    this.forward.set(Math.sin(this.yaw), 0, Math.cos(this.yaw));
    // Lean into the acceleration, as a body hung from nothing would: forward into a
    // swoop, back as it brakes, into the turn as it banks. At most about 28 degrees.
    const lean = g.acceleration.scale(0.5);
    lean.y = Math.max(-4, Math.min(4, lean.y)) + 9.81;
    const tilt = lean.normalize();
    const cos = Vector3.Dot(tilt, Vector3.UpReadOnly);
    if (cos < 0.88) {
      const side = new Vector3(tilt.x, 0, tilt.z).normalize().scaleInPlace(0.475);
      tilt.copyFrom(side).addInPlaceFromFloats(0, 0.88, 0).normalize();
    }
    // A living thing never quite holds still.
    tilt.x += 0.025 * Math.sin(time * 0.71 + 0.3);
    tilt.z += 0.02 * Math.sin(time * 0.53 + 2.1);
    this.up.addInPlace(
      tilt
        .normalize()
        .subtractInPlace(this.up)
        .scaleInPlace(1 - Math.exp(-dt * 5)),
    );
    this.up.normalize();
    const f = this.forward.subtract(this.up.scale(Vector3.Dot(this.forward, this.up))).normalize();
    Quaternion.FromLookDirectionLHToRef(f, this.up, this.root.rotationQuaternion!);
  }

  /** The head on its neck: finds Sora when it has seen her, tilts, shudders as it shrieks. */
  private lookAt(dt: number, time: number, target: Vector3, attack: boolean): void {
    const neck = this.head.parent as TransformNode;
    const local = Vector3.TransformCoordinates(target, Matrix.Invert(neck.getWorldMatrix()))
      .subtractInPlace(this.head.position)
      .rotateByQuaternionToRef(this.headFrame, new Vector3());
    // In the model's own frame: +Z is her face, +Y up, +X her left.
    let yaw = Math.atan2(local.x, local.z),
      pitch = Math.atan2(local.y, Math.hypot(local.x, local.z));
    const reach = 0.35 + 0.35 * this.watch;
    yaw = Math.max(-reach, Math.min(reach, yaw * (0.4 + 0.6 * this.watch)));
    pitch = Math.max(-0.4, Math.min(0.35, pitch * (0.4 + 0.6 * this.watch)));
    // Idle, it looks about; watching, it holds still and cocks its head.
    yaw += (1 - this.watch) * 0.12 * Math.sin(time * 0.37 + 0.8);
    pitch += (1 - this.watch) * 0.05 * Math.sin(time * 0.29);
    let roll = 0.06 * Math.sin(time * 0.43) + this.watch * (0.24 + 0.05 * Math.sin(time * 0.31));
    const shake = this.mouthOpen * 0.05 * Math.sin(time * 57);
    yaw += shake;
    pitch -= this.mouthOpen * 0.14;
    roll -= this.mouthOpen * 0.1;
    const want = Quaternion.RotationAxis(Vector3.UpReadOnly, yaw)
      .multiplyInPlace(Quaternion.RotationAxis(Vector3.RightReadOnly, -pitch))
      .multiplyInPlace(Quaternion.RotationAxis(Vector3.Forward(false), roll));
    Quaternion.SlerpToRef(this.look, want, 1 - Math.exp(-dt * (attack ? 14 : 5)), this.look);
    inFrame(this.headFrame, this.look, this.headRest, this.head.rotationQuaternion!);
  }

  private workJaw(time: number): void {
    // It breathes through the open mouth; watching, the jaw trembles; shrieking, it gapes.
    const open =
      0.035 * (0.5 + 0.5 * Math.sin(time * 1.9)) +
      this.watch * 0.022 * Math.sin(time * 23) * (0.6 + 0.4 * Math.sin(time * 3.1)) +
      this.mouthOpen * 0.2;
    inFrame(
      this.jawFrame,
      Quaternion.RotationAxis(Vector3.RightReadOnly, open),
      this.jawRest,
      this.jaw.rotationQuaternion!,
    );
  }

  private simulate(dt: number, time: number, fresh: boolean): void {
    const yaw = Quaternion.RotationAxis(Vector3.UpReadOnly, this.yaw);
    const top = this.throat.getAbsolutePosition();
    for (const c of this.chains) {
      if (c.gut) gutTargets(c, this.gutOffsets, top, yaw);
      else
        for (let i = 0; i < c.nodes.length; i++)
          Vector3.TransformCoordinatesToRef(
            c.restInAnchor[i],
            c.anchor.getWorldMatrix(),
            c.targets[i],
          );
      // The root of each chain is where its joint is now.
      c.targets[0].copyFrom(c.nodes[0].getAbsolutePosition());
      if (fresh) c.strand.reset(c.targets);
    }
    if (fresh) this.accumulator = 0;
    else {
      this.accumulator = Math.min(this.accumulator + dt, STRAND_STEP * 10);
      while (this.accumulator >= STRAND_STEP) {
        this.accumulator -= STRAND_STEP;
        for (const c of this.chains) c.strand.advance(STRAND_STEP, time, c.targets);
      }
    }
    for (const c of this.chains) aim(c);
  }

  private breathe(time: number, attack: boolean): void {
    // Lub-dub: a double beat, quicker once it has seen her.
    const rate = 1.15 + 0.9 * this.watch + (attack ? 0.4 : 0);
    const phase = (time * rate) % 1;
    const beat =
      Math.exp(-(((phase - 0.08) / 0.045) ** 2)) + 0.6 * Math.exp(-(((phase - 0.28) / 0.05) ** 2));
    this.heart?.scaling.setAll(1 + 0.075 * beat);
    const breath = 1 + 0.045 * Math.sin(time * 1.7) * (1 - this.mouthOpen) - 0.05 * this.mouthOpen;
    for (const lung of this.lungs) lung.scaling.setAll(breath);
  }

  /** World matrices from `node` down (the glTF bones read their nodes'). */
  private refresh(node: TransformNode): void {
    node.computeWorldMatrix(true);
    for (const child of node.getChildTransformNodes(true)) this.refresh(child);
  }
}

/** Rest places of the viscera: hung from the throat, turned only with the heading. */
function gutTargets(c: Chain, offsets: readonly Vector3[], top: Vector3, yaw: Quaternion): void {
  for (let i = 0; i < c.targets.length; i++)
    offsets[i].rotateByQuaternionToRef(yaw, c.targets[i]).addInPlace(top);
}

const MAX_SWING = (22 * Math.PI) / 180;

/** Turns each joint of a chain so it points at the next simulated point. */
function aim(c: Chain): void {
  const pts = c.strand.points;
  const toChild = new Vector3(),
    restDir = new Vector3(),
    swing = new Quaternion();
  for (let i = 0; i < c.nodes.length - 1; i++) {
    const n = c.nodes[i];
    const parent = n.parent as TransformNode;
    const inverse = Matrix.Invert(parent.getWorldMatrix());
    const head = Vector3.TransformCoordinates(n.position, parent.getWorldMatrix());
    Vector3.TransformNormalToRef(pts[i + 1].subtract(head), inverse, toChild);
    c.child[i].rotateByQuaternionToRef(c.rest[i], restDir);
    if (toChild.lengthSquared() < 1e-10 || restDir.lengthSquared() < 1e-10) continue;
    Quaternion.FromUnitVectorsToRef(restDir.normalize(), toChild.normalize(), swing);
    // However hard the air pulls, a joint turns at most MAX_SWING from its rest.
    const angle = 2 * Math.acos(Math.min(1, Math.abs(swing.w)));
    if (angle > MAX_SWING)
      Quaternion.SlerpToRef(Quaternion.Identity(), swing, MAX_SWING / angle, swing);
    swing.multiplyToRef(c.rest[i], n.rotationQuaternion!);
    n.computeWorldMatrix(true);
  }
  const last = c.nodes[c.nodes.length - 1];
  last.computeWorldMatrix(true);
}

/** A rotation `q` given in a parent's rest frame `frame`, applied to a joint at `rest`. */
function inFrame(frame: Quaternion, q: Quaternion, rest: Quaternion, out: Quaternion): void {
  Quaternion.InverseToRef(frame, out);
  out.multiplyInPlace(q).multiplyInPlace(frame).multiplyInPlace(rest);
}

/** A node's rotation in the model's own (glTF) frame: its rotations up to the loader's root. */
function armatureRotation(node: TransformNode): Quaternion {
  const q = Quaternion.Identity();
  for (
    let n: TransformNode | null = node;
    n && n.name !== "__root__";
    n = n.parent as TransformNode | null
  )
    q.copyFrom((n.rotationQuaternion ?? Quaternion.FromEulerVector(n.rotation)).multiply(q));
  return q;
}
