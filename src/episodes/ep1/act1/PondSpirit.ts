import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { Axis } from "@babylonjs/core/Maths/math.axis";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Game } from "@/core/Game";
import type { Area } from "@/core/areaLoader";
import { seededRandom } from "@/audio/synth";
import type { DreadScore } from "@/audio/DreadScore";
import { pondSplash } from "../audio/pondSounds";
import type { VillageLights } from "./VillageLights";
import { Preay } from "../entities/Preay";

/** Where she shows herself from, and when she goes (m, s). */
const SHOW_WITHIN = 34;
const NEAR = 7.5;
const SEEN_FOR = 1.2;
const LOOK_AWAY = 0.9;
/** Watched this long, her head starts to come round towards Sora. */
const TURNS_AFTER = 0.7;

type State = "waiting" | "standing" | "gone";

/**
 * The pond's spirit (village expansion, east pond): the Preay, a woman's ghost in a
 * bloodied white dress, standing at the end of the bathing jetty, her back to the
 * shore, looking out over the black water. She stands where east_pond.py put the
 * static `pond_spirit` (hidden now), breathing; watched long enough, her head comes
 * slowly round towards Sora.
 *
 * She is put there only while Sora is on her way and not looking. Once Sora
 * has seen her she stays as long as she is watched; she is gone the moment
 * Sora looks away, or as Sora comes close (lightning covers it then), and a
 * body goes into the water behind the jetty. Once a night: Act I only.
 */
export class PondSpirit {
  score: DreadScore | null = null;
  private state: State = "waiting";
  private readonly node: TransformNode | null;
  private readonly preay: Preay | null = null;
  private readonly spot = new Vector3();
  private splash: StaticSound | null = null;
  private seen = 0;
  private away = 0;
  private fright = 0;
  private readonly eye = new Vector3();
  private readonly forward = new Vector3();

  constructor(
    private readonly game: Game,
    area: Area,
    private readonly lights: VillageLights,
    asset: AssetContainer,
  ) {
    const nodes = [...area.container.transformNodes, ...area.container.meshes];
    this.node = nodes.find((n): n is TransformNode => n.name === "pond_spirit") ?? null;
    if (!this.node) {
      console.warn("[PondSpirit] no pond_spirit in the village");
      return;
    }
    this.node.computeWorldMatrix(true);
    this.spot.copyFrom(this.node.getAbsolutePosition());
    // The scan faces its own +X (Blender), whatever mirrors the glTF root carries.
    const facing = Vector3.TransformNormal(new Vector3(1, 0, 0), this.node.getWorldMatrix());
    this.node.setEnabled(false);
    this.preay = new Preay(asset, "pond_preay", 1.9);
    this.preay.place(this.spot, Math.atan2(facing.x, facing.z));
    this.preay.standStill(0);
    this.show(false);
  }

  /** 0–1: the fright just after she goes. */
  get dread(): number {
    return this.fright;
  }

  get active(): boolean {
    return this.state === "standing";
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.splash = await audio.spatialSound(
      "pond_splash",
      audio.buffer(pondSplash(rate, seededRandom(1931)), rate),
      "threat",
      this.spot.add(new Vector3(-1.4, -0.3, 0.4)),
      { minDistance: 3, maxDistance: 60 },
    );
  }

  update(dt: number): void {
    this.fright = Math.max(0, this.fright - dt / 5);
    if (!this.node || this.state === "gone") return;
    if (this.game.flags.get("ep1.act2.started", false)) {
      this.leave(false);
      return;
    }
    const camera = this.game.camera;
    this.eye.copyFrom(camera.globalPosition);
    camera.getDirectionToRef(Axis.Z, this.forward);
    const distance = Vector3.Distance(
      new Vector3(this.eye.x, 0, this.eye.z),
      new Vector3(this.spot.x, 0, this.spot.z),
    );
    const inView = !!this.preay?.figure.meshes.some((m) => camera.isInFrustum(m));

    if (this.state === "waiting") {
      // Put there unseen, while Sora is coming down the lane or round the bank.
      if (distance < SHOW_WITHIN && distance > NEAR + 4 && !inView && !this.game.cutscene) {
        this.state = "standing";
        this.show(true);
      }
      return;
    }

    if (inView && distance < SHOW_WITHIN) {
      this.seen += dt;
      this.away = 0;
    } else if (this.seen > 0) {
      this.away += dt;
    }
    // She breathes; watched, her head comes slowly round to Sora, and stays on her.
    this.preay?.watch(this.seen > TURNS_AFTER ? this.eye : null);
    this.preay?.standStill(dt);
    if (distance < NEAR) {
      // Too close: the lightning takes her, and something goes into the water.
      this.lights.storm.strike();
      this.leave(true, 1);
    } else if (this.seen > SEEN_FOR && this.away > LOOK_AWAY) {
      this.leave(true, 0.6);
    } else if (this.seen === 0 && distance > SHOW_WITHIN + 6) {
      // Sora never came near enough to see her: she waits for another time.
      this.state = "waiting";
      this.show(false);
    }
  }

  private leave(heard: boolean, strength = 1): void {
    this.state = "gone";
    this.show(false);
    if (!heard) return;
    setTimeout(() => this.splash?.play(), 120);
    this.score?.sting(strength >= 1 ? "shock" : "drop", 0.85 * strength);
    if (strength >= 1) this.game.atmosphere.scare();
    this.fright = Math.max(this.fright, strength);
  }

  private show(on: boolean): void {
    this.preay?.setEnabled(on);
  }
}
