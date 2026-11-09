import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Game } from "@/core/Game";
import { seededRandom } from "@/audio/synth";
import { krasueLament, krasueShriek, krasueSting } from "@/audio/sounds/krasueSounds";
import { KrasueModel } from "@/shared/entities/KrasueModel";
import type { Point } from "./data/pagoda";

/** Where Sora is and what she is doing, as the Krasue needs it. */
export interface KrasueScene {
  stage: string;
  feet: Point;
  yaw: number;
  offerings: number;
  inKuti: boolean;
  nearestPret: number;
}

/** A flight: from `from` to `to`, curving through `via`, over `seconds`. */
export interface KrasueFlight {
  from: Vector3;
  via: Vector3;
  to: Vector3;
  seconds: number;
  /** The pass overhead: she shrieks as she goes over. */
  close: boolean;
}

/** The pond's middle: the one pass comes over its banks. */
const POND = { x: 0, z: -28.2 };
/** How many times she is seen far off, the first a while into the garden, then apart. */
const SIGHTINGS = 5;
const FIRST = [30, 50] as const;
const GAP = [75, 140] as const;

/** A point on the quadratic curve from `a` through control `b` to `c`. */
export function along(f: KrasueFlight, u: number): Vector3 {
  const v = 1 - u;
  return f.from
    .scale(v * v)
    .addInPlace(f.via.scale(2 * v * u))
    .addInPlace(f.to.scale(u * u));
}

/**
 * A far sighting: she drifts across what Sora faces, high over the trees well off,
 * the head and what hangs from it lit by its own faint glow, and is gone into the canopy.
 */
export function sighting(s: KrasueScene, rand: () => number): KrasueFlight {
  const yaw = s.yaw + (rand() - 0.5) * 0.5;
  const d = 14 + rand() * 6;
  const centre = { x: s.feet.x + Math.sin(yaw) * d, z: s.feet.z + Math.cos(yaw) * d };
  const side = { x: Math.cos(yaw), z: -Math.sin(yaw) };
  const way = rand() < 0.5 ? 1 : -1;
  const half = 10 + rand() * 4;
  const y = 7 + rand() * 3;
  return {
    from: new Vector3(centre.x - side.x * half * way, y, centre.z - side.z * half * way),
    via: new Vector3(centre.x, y - 2.5, centre.z),
    to: new Vector3(centre.x + side.x * half * way, y + 1.5, centre.z + side.z * half * way),
    seconds: 9 + rand() * 3,
    close: false,
  };
}

/**
 * The one pass: out of the trees behind Sora, low over her head (a little over three
 * metres up) and away into the trees in front, shrieking as she goes over.
 */
export function overhead(s: KrasueScene): KrasueFlight {
  const fx = Math.sin(s.yaw),
    fz = Math.cos(s.yaw);
  const side = { x: fz, z: -fx };
  return {
    from: new Vector3(s.feet.x - fx * 28 - side.x * 6, 9, s.feet.z - fz * 28 - side.z * 6),
    // Through a point below ground so the curve bottoms out a little over three metres up.
    via: new Vector3(s.feet.x + side.x * 0.8, -1.6, s.feet.z + side.z * 0.8),
    to: new Vector3(s.feet.x + fx * 30 + side.x * 5, 10, s.feet.z + fz * 30 + side.z * 5),
    seconds: 3.4,
    close: true,
  };
}

/**
 * Episode 1's Krasue, followed Sora here. She never hunts at the pagoda: she is seen far
 * off a few times, drifting over the canopy, and once, by the pond, she comes out of the
 * trees behind and goes low over Sora's head, shrieking. Saved in `ep2.krasue.*`.
 */
export class PagodaKrasue {
  private model: KrasueModel | null = null;
  private flight: KrasueFlight | null = null;
  private t = 0;
  private time = 0;
  private shrieked = false;
  private nextSighting = FIRST[0] + Math.random() * (FIRST[1] - FIRST[0]);
  private lament: StaticSound | null = null;
  private shriek: StaticSound | null = null;
  private sting: StaticSound | null = null;
  private readonly rand = Math.random;
  /** Her viscera's materials, lit from within: strongly far off, faintly close to. */
  private readonly glowing: { emissiveColor: { set(r: number, g: number, b: number): void } }[] =
    [];

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const scene = this.game.scene;
    await KrasueModel.prepare(scene);
    this.model = new KrasueModel(scene);
    // At the pagoda she is seen through the mist from far off: what hangs from her glows
    // faintly, as the village said it did, so she reads as a light moving over the trees.
    for (const mesh of this.model.meshes) {
      const m = mesh.material;
      if (
        m instanceof PBRMaterial &&
        /viscera|liver|vessels/.test(m.name) &&
        !this.glowing.includes(m)
      )
        this.glowing.push(m);
    }
    this.model.light.intensity = 1.6;
    this.model.light.range = 5;
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.lament = await audio.spatialSound(
      "ep2_krasue_lament",
      audio.buffer(krasueLament(rate, seededRandom(1739)), rate),
      "threat",
      Vector3.Zero(),
      { loop: true, minDistance: 4, maxDistance: 60, volume: 0 },
    );
    this.shriek = await audio.spatialSound(
      "ep2_krasue_shriek",
      audio.buffer(krasueShriek(rate, seededRandom(1741)), rate),
      "threat",
      Vector3.Zero(),
      { minDistance: 3, maxDistance: 40, volume: 0.45 },
    );
    this.sting = await audio.spatialSound(
      "ep2_krasue_sting",
      audio.buffer(krasueSting(rate, seededRandom(1743)), rate),
      "threat",
      Vector3.Zero(),
      { minDistance: 30, maxDistance: 60, volume: 0.6 },
    );
    scene.onDisposeObservable.addOnce(() => {
      for (const s of [this.lament, this.shriek, this.sting]) s?.stop();
    });
  }

  /** Whether she is in the air now. */
  get flying(): boolean {
    return this.flight !== null;
  }

  update(dt: number, s: KrasueScene, active: boolean): void {
    const model = this.model;
    if (!model) return;
    this.time += dt;
    if (!active) {
      if (this.flight) this.land();
      return;
    }
    if (!this.flight) {
      this.maybeFly(dt, s);
      return;
    }
    const f = this.flight;
    this.t += dt;
    const u = Math.min(1, this.t / f.seconds);
    // Eased at the ends so she drifts in and out rather than starting like a machine.
    const e = u * u * (3 - 2 * u);
    const at = along(f, f.close ? u : e);
    const ahead = along(f, Math.min(1, (f.close ? u : e) + 0.02));
    const flightDir = ahead.subtract(at);
    const feet = new Vector3(s.feet.x, 1.6, s.feet.z);
    const d = Vector3.Distance(at, feet);
    const shrieking = f.close && d < 9;
    model.root.setEnabled(true);
    model.pose(at, feet, this.time, false, flightDir, shrieking, shrieking ? this.t : -1);
    if (this.lament) {
      this.lament.spatial.position = at;
      // Far off it is barely there; it swells as the pass comes on, then the shriek takes over.
      const target = f.close ? (this.shrieked ? 0 : 0.5) : 0.3 * Math.sin(Math.PI * u);
      this.lament.volume += (target - this.lament.volume) * Math.min(1, dt * 3);
    }
    if (f.close && !this.shrieked && d < 7) {
      this.shrieked = true;
      if (this.shriek) {
        this.shriek.spatial.position = at;
        this.shriek.play();
      }
      if (this.sting) {
        this.sting.spatial.position = at;
        this.sting.play();
      }
      this.game.atmosphere.scare();
    }
    if (this.shriek && this.shrieked) this.shriek.spatial.position = at;
    if (u >= 1) this.land();
  }

  private maybeFly(dt: number, s: KrasueScene): void {
    if (s.inKuti || (s.stage !== "garden" && s.stage !== "library")) return;
    const flags = this.game.flags;
    // The pass: once, at the pond's banks, after the second offering, with no corpse near.
    const toPond = Math.hypot(s.feet.x - POND.x, s.feet.z - POND.z);
    if (
      !flags.get("ep2.krasue.pass", false) &&
      s.offerings >= 2 &&
      toPond > 7 &&
      toPond < 16 &&
      s.nearestPret > 8
    ) {
      flags.set("ep2.krasue.pass", true);
      this.fly(overhead(s));
      return;
    }
    const seen = flags.get("ep2.krasue.seen", 0);
    if (seen >= SIGHTINGS) return;
    this.nextSighting -= dt;
    if (this.nextSighting > 0) return;
    this.nextSighting = GAP[0] + this.rand() * (GAP[1] - GAP[0]);
    flags.set("ep2.krasue.seen", seen + 1);
    this.fly(sighting(s, this.rand));
  }

  private fly(f: KrasueFlight): void {
    this.flight = f;
    const glow = f.close ? 0.18 : 0.6;
    for (const m of this.glowing) m.emissiveColor.set(glow, glow * 0.3, glow * 0.2);
    this.t = 0;
    this.shrieked = false;
    if (this.lament) {
      this.lament.volume = 0;
      this.lament.spatial.position = f.from;
      this.lament.play();
    }
  }

  private land(): void {
    this.flight = null;
    this.model?.root.setEnabled(false);
    this.lament?.stop();
  }
}
