import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Axis } from "@babylonjs/core/Maths/math.axis";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateDisc } from "@babylonjs/core/Meshes/Builders/discBuilder";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { DreadScore } from "@/audio/DreadScore";
import type { Game } from "@/core/Game";
import { realiseInstances } from "@/core/areaLoader";
import type { VillageLights } from "../act1/VillageLights";
import type { VillageAudio } from "../audio/VillageAudio";
import { COFFIN, HALL, inFuneralRoom } from "../data/funeral";
import { PUZZLE_SPOTS } from "../data/villagePuzzles";
import {
  CORPSE_SPOT,
  ROADSIDE_PEEK_RETREAT,
  ROADSIDE_PEEK_SPOT,
  SHOP_CROSSING_PATH,
  VillageHauntPacer,
  WEEPING_SPOT,
  type VillageHauntId,
} from "../data/villageHaunts";
import { Preay } from "../entities/Preay";

const BEHIND_COFFIN_BANNER = -20.8;
const HEADLESS_SCALE = 1.14;

interface ActiveSequence {
  id: VillageHauntId;
  elapsed: number;
  /** Returns true when finished. */
  step: (t: number, dt: number) => boolean;
  end: () => void;
}

/**
 * Cinema-grade Asian psychological horror director for Episode 1 Village.
 *
 * No static mannequins popping in and out in broad lamplight:
 * - Preay physically walks, stalks, hurries behind cover when caught by lamplight, crosses dark
 *   shop doorways in silhouette, twists her neck 115° while her continuous weeping cuts dead, and
 *   lurches forward before a pitch-black lamp blackout cut + close-ear barefoot rush.
 * - Headless Ghost waits in dark shop interiors until Sora actually looks in, glides forward with
 *   unnatural headless torso sway, or rises slowly from behind the brick well rim before cutting
 *   the lamp to black and rushing past Sora's ear.
 * - Two-stage Rear-Presence whisper/footstep behind Sora's neck that rewards (and punishes) spinning
 *   around to check behind you.
 * - Subtle grounded spatial ambient cues (shop knocks, upstairs barefoot pacing, distant wood claws)
 *   keep the village alive and haunted between major encounters.
 */
export class VillageHorrorDirector {
  readonly pacer = new VillageHauntPacer();
  score: DreadScore | null = null;
  /** Hook invoked during peak anomalies to glitch the Episode 1 clock to `20:12`. */
  onClockGlitch: ((seconds: number) => void) | null = null;

  private readonly preay: Preay;
  private readonly shade: Preay;
  private readonly shadeLayer: TransformNode;
  private headlessRoot: TransformNode | null = null;
  private headlessMeshes: AbstractMesh[] = [];
  private corpseRoot: TransformNode | null = null;
  private corpseSeen = false;
  private corpseVanished = false;
  private readonly footprints: Mesh[] = [];
  private footprintMat: StandardMaterial | null = null;
  private activeSeq: ActiveSequence | null = null;
  private fright = 0;
  private clock = 0;

  // Extra-footstep / rear-presence tracker
  private wasMoving = false;
  private moveStreak = 0;
  private ambientCueTimer = 14;

  private readonly eye = new Vector3();
  private readonly forward = new Vector3();

  constructor(
    private readonly game: Game,
    private readonly lights: VillageLights,
    private readonly villageAudio: VillageAudio | null,
    preayAsset: AssetContainer,
    private readonly groundAt: (x: number, z: number) => number,
  ) {
    const scene = game.scene;
    this.preay = new Preay(preayAsset, "village_preay", 0.9);
    this.preay.ground = groundAt;
    this.preay.onStep = (at) => this.villageAudio?.play("preayStep", at, 0.82);
    this.preay.setEnabled(false);

    // Shadow-only Preay silhouette projected along the funeral banner during lightning
    this.shadeLayer = new TransformNode("village_preay_shadow_layer", scene);
    this.shadeLayer.scaling.set(1, 1, 0.02);
    this.shade = new Preay(preayAsset, "village_preay_shadow", 2.0);
    this.shade.root.parent = this.shadeLayer;
    this.shade.silhouette(0.62);
    this.shadeLayer.setEnabled(false);

    const fpMat = new StandardMaterial("M_wet_mud_footprint", scene);
    fpMat.diffuseColor = new Color3(0.04, 0.028, 0.02);
    fpMat.specularColor = new Color3(0.22, 0.2, 0.18);
    fpMat.alpha = 0.78;
    this.footprintMat = fpMat;

    scene.onDisposeObservable.addOnce(() => this.dispose());
  }

  /** Loads the prepared Khmer Headless Ghost & Shrouded Corpse GLBs cleanly. */
  async load(): Promise<void> {
    const scene = this.game.scene;
    const base = import.meta.env.BASE_URL;
    const tryLoad = async (file: string): Promise<AssetContainer | null> => {
      try {
        const container = await LoadAssetContainerAsync(`${base}assets/ep1/${file}`, scene);
        realiseInstances(container);
        container.addAllToScene();
        for (const mat of container.materials) {
          if (mat instanceof PBRMaterial) {
            mat.maxSimultaneousLights = 8;
            mat.environmentIntensity = 0.58;
            mat.enableSpecularAntiAliasing = true;
            mat.emissiveColor = Color3.Black();
            if (mat.name.includes("hair_cards")) {
              mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
              mat.alphaCutOff = 0.34;
              mat.backFaceCulling = false;
            }
          }
        }
        return container;
      } catch (err) {
        console.warn(`[VillageHorrorDirector] optional model ${file} unavailable`, err);
        return null;
      }
    };

    const [headless, corpse] = await Promise.all([
      tryLoad("headless_ghost.glb"),
      tryLoad("shrouded_corpse.glb"),
    ]);

    if (headless) {
      const root = new TransformNode("village_headless_ghost", scene);
      for (const n of [...headless.transformNodes, ...headless.meshes]) {
        if (!n.parent) n.parent = root;
      }
      this.headlessMeshes = headless.meshes.filter((m) => m.getTotalVertices() > 0);
      for (const m of this.headlessMeshes) {
        m.isPickable = false;
        m.alwaysSelectAsActiveMesh = true;
      }
      root.scaling.setAll(HEADLESS_SCALE);
      root.setEnabled(false);
      this.headlessRoot = root;
    }

    if (corpse) {
      const root = new TransformNode("village_shrouded_corpse", scene);
      for (const n of [...corpse.transformNodes, ...corpse.meshes]) {
        if (!n.parent) n.parent = root;
      }
      for (const m of corpse.meshes) m.isPickable = false;
      const cy = this.groundAt(CORPSE_SPOT.x, CORPSE_SPOT.z);
      root.position.set(CORPSE_SPOT.x, cy + 0.02, CORPSE_SPOT.z);
      root.rotation.y = CORPSE_SPOT.yaw;
      this.corpseVanished = this.game.flags.get("ep1.haunt.corpseVanished", false);
      root.setEnabled(!this.corpseVanished);
      this.corpseRoot = root;
    }
  }

  get active(): boolean {
    return this.activeSeq !== null;
  }

  /** 0–1 horror dread pressure for DreadScore, fear vignette, heartbeat & handheld tremor. */
  get dread(): number {
    return Math.max(this.fright, this.activeSeq ? 0.62 : 0, this.preayChill * 0.85);
  }

  /** 0–1 cold lamp-choking aura when Preay, Headless Ghost, or the Shrouded Corpse is near Sora. */
  get preayChill(): number {
    const eye = this.game.camera.globalPosition;
    let chill = this.preay.proximityChill(eye);
    if (this.headlessRoot?.isEnabled()) {
      const d = Vector3.Distance(this.headlessRoot.position, eye);
      if (d < 9.0) {
        const k = 1 - d / 9.0;
        chill = Math.max(chill, k * k);
      }
    }
    if (this.corpseRoot?.isEnabled() && !this.corpseVanished) {
      const d = Vector3.Distance(this.corpseRoot.position, eye);
      if (d < 6.5) {
        const k = 1 - d / 6.5;
        chill = Math.max(chill, k * k * 0.45);
      }
    }
    return chill;
  }

  /**
   * Development review helper: stages any village haunted scene deterministically for
   * visual inspection & screenshot capture without affecting normal gameplay pacing.
   */
  stagePreview(
    beat:
      | "clear"
      | "roadsidePeeker"
      | "barberHeadless"
      | "corpse"
      | "wellHeadless"
      | "weepingTwist"
      | "strobeCloser"
      | "shadowBanner"
      | "provokedAmbush",
    eye: Vector3,
  ): void {
    this.cancelActive();
    this.preay.release();
    this.preay.setEnabled(false);
    this.shadeLayer.setEnabled(false);
    this.resetHeadlessPose();
    this.headlessRoot?.setEnabled(false);
    if (this.corpseRoot) this.corpseRoot.setEnabled(beat === "corpse");
    if (beat === "clear") return;

    if (beat === "roadsidePeeker") {
      const at = new Vector3(
        ROADSIDE_PEEK_SPOT.x,
        Math.max(this.groundAt(ROADSIDE_PEEK_SPOT.x, ROADSIDE_PEEK_SPOT.z), 0.12),
        ROADSIDE_PEEK_SPOT.z,
      );
      this.preay.place(at, Math.atan2(eye.x - at.x, eye.z - at.z));
      this.preay.watch(eye);
      this.preay.setHorror({ neckTilt: 0.42, overShoulder: 0, hunch: 0.24 });
      this.preay.setEnabled(true);
      this.preay.standStill(0.45);
      return;
    }

    if (beat === "barberHeadless" && this.headlessRoot) {
      const [gx, gz] = PUZZLE_SPOTS.barberGhost;
      this.headlessRoot.position.set(gx, 0.46, gz);
      this.headlessRoot.rotation.set(0, Math.atan2(eye.x - gx, eye.z - gz), 0);
      this.headlessRoot.setEnabled(true);
      return;
    }

    if (beat === "corpse" && this.corpseRoot) {
      const cy = this.groundAt(CORPSE_SPOT.x, CORPSE_SPOT.z);
      this.corpseRoot.position.set(CORPSE_SPOT.x, cy + 0.02, CORPSE_SPOT.z);
      this.corpseRoot.rotation.y = CORPSE_SPOT.yaw;
      this.corpseRoot.setEnabled(true);
      if (this.footprints.length === 0) {
        this.spawnWetFootprints(this.corpseRoot.position, CORPSE_SPOT.yaw + 0.8);
      }
      return;
    }

    if (beat === "wellHeadless" && this.headlessRoot) {
      const [wx, wz] = PUZZLE_SPOTS.well;
      const pos = new Vector3(wx - 0.55, this.groundAt(wx - 0.55, wz - 1.15), wz - 1.15);
      this.headlessRoot.position.copyFrom(pos);
      this.headlessRoot.rotation.set(0, Math.atan2(eye.x - pos.x, eye.z - pos.z), 0);
      this.headlessRoot.setEnabled(true);
      return;
    }

    if (beat === "weepingTwist") {
      const at = new Vector3(
        WEEPING_SPOT.x,
        this.groundAt(WEEPING_SPOT.x, WEEPING_SPOT.z),
        WEEPING_SPOT.z,
      );
      const awayYaw = Math.atan2(at.x - eye.x, at.z - eye.z);
      this.preay.place(at, awayYaw);
      this.preay.watch(null);
      this.preay.setHorror({ neckTilt: -0.44, overShoulder: 2.0, hunch: 0.34 });
      this.preay.setEnabled(true);
      this.preay.standStill(0.55);
      return;
    }

    if (beat === "strobeCloser") {
      const pos = new Vector3(0.35, this.groundAt(0.35, 18.2), 18.2);
      this.preay.strobePose(pos, Math.atan2(eye.x - pos.x, eye.z - pos.z), 0.44, "stand", 1.3);
      this.preay.setHorror({ hunch: 0.32 });
      this.preay.watch(eye);
      this.preay.standStill(0.45);
      return;
    }

    if (beat === "shadowBanner") {
      this.shadeLayer.position.set(COFFIN.x - 1.45, HALL.floor + 0.1, BEHIND_COFFIN_BANNER + 0.4);
      this.shade.place(new Vector3(0, 0, 0), Math.PI / 2);
      this.shadeLayer.setEnabled(true);
      this.shade.standStill(0.016);
      return;
    }

    if (beat === "provokedAmbush") {
      const pos = new Vector3(-1.8, 2.5, -15.6);
      this.preay.strobePose(pos, Math.atan2(eye.x - pos.x, eye.z - pos.z), -0.46, "stand", 2.1);
      this.preay.setHorror({ hunch: 0.36 });
      this.preay.watch(eye);
      this.preay.standStill(0.45);
    }
  }

  // ------------------------------------------------------------------ Puzzle-Triggered Haunts

  /**
   * Barber Shop Radio Silenced -> Headless Ghost waits deep inside the dark walkable shop
   * until Sora turns toward the doorway, then glides forward between the two red chairs,
   * chills the lamp, and cuts to pitch black as wet footsteps rush past Sora's ear.
   */
  triggerBarberHeadless(): void {
    if (!this.headlessRoot || this.pacer.hasDone("roadsideHeadless")) return;
    this.cancelActive();
    this.pacer.markTriggered("roadsideHeadless");
    const [gx] = PUZZLE_SPOTS.barberGhost;
    const root = this.headlessRoot;
    const startZ = 42.65;
    const endZ = 44.55;
    this.resetHeadlessPose();
    root.position.set(gx, 0.46, startZ);
    root.setEnabled(false);

    // Let all 4 radio knocks land (0.75..2.01s), then spawn deep inside the dark Barber Shop
    let spawned = false;
    let spottedAt = -1;
    let blackoutAt = -1;
    let stepTimer = 0;

    this.startSeq(
      "roadsideHeadless",
      (t, dt) => {
        if (t >= 2.25 && !spawned) {
          spawned = true;
          root.setEnabled(true);
          this.villageAudio?.triggerVacuum(4.8, 0.08);
          this.villageAudio?.play("woodCreak", root.position, 0.85);
          this.lights.flickerBurst(1.1);
        }
        if (!spawned) return false;

        // Continuously orient toward Sora with unsettling headless torso heave & tilt
        const yaw = Math.atan2(this.eye.x - root.position.x, this.eye.z - root.position.z);
        this.animateHeadlessLiving(root, yaw, t, spottedAt >= 0 ? 1.5 : 0.7);

        const targetHead = root.position.add(new Vector3(0, 1.35, 0));
        const dist = Vector3.Distance(this.eye, root.position);
        const looking = this.isLookingAt(targetHead, 0.76);

        // Wait patiently until Sora actually looks into the Barber Shop doorway (or steps inside)
        if (spottedAt < 0 && ((looking && dist < 11.5) || dist < 4.2)) {
          spottedAt = t;
          this.lights.storm.strike();
          this.villageAudio?.play("stingerLow", root.position, 0.95);
          this.villageAudio?.play("preayWhisper", root.position, 0.95);
          this.villageAudio?.play("soraGasp", this.eye, 0.82);
          this.game.player.jolt(0.62, -1);
          this.game.atmosphere.scare();
          this.fright = 0.92;
          this.onClockGlitch?.(7);
        }

        if (spottedAt >= 0 && blackoutAt < 0) {
          const since = t - spottedAt;
          // Slowly glides/steps forward between the two barber chairs toward the doorway
          const move = Math.min(1, since / 1.55);
          root.position.z = startZ + (endZ - startZ) * move;
          root.position.x = gx + Math.sin(since * 5.2) * 0.06;
          stepTimer += dt;
          if (stepTimer >= 0.42) {
            stepTimer = 0;
            this.villageAudio?.play("preayStep", root.position, 0.88);
          }

          if (since >= 1.65 || Vector3.Distance(this.eye, root.position) < 2.2) {
            blackoutAt = t;
            this.lights.blackout(0.48);
            this.villageAudio?.play("shockHit", this.eye, 0.96);
            this.villageAudio?.playNearEar("preayBreath", this.eye, this.forward, -1, 0.55, 1.05);
            this.villageAudio?.playNearEar("preayStep", this.eye, this.forward, -1, 0.85, 1.0);
            this.game.player.jolt(0.95, 1);
            this.game.atmosphere.scare();
            this.fright = 1.0;
          }
        }

        if (blackoutAt >= 0) {
          const sinceCut = t - blackoutAt;
          if (sinceCut >= 0.16 && root.isEnabled()) {
            root.setEnabled(false);
            this.spawnWetFootprints(new Vector3(gx, 0.46, endZ), 0);
          }
          if (sinceCut >= 0.55) return true;
        }

        // If Sora walks away without ever looking back in, vanish cleanly out of sight
        if (spottedAt < 0 && (t >= 17 || dist > 16)) {
          root.setEnabled(false);
          return true;
        }
        return false;
      },
      () => {
        this.resetHeadlessPose();
        root.setEnabled(false);
      },
    );
  }

  /**
   * Brick Well Haul Tug Failed -> Headless Ghost rises smoothly from behind the dark brick well
   * rim in a lightning flash, leans forward with drowned breath, cuts the lamp to pitch black,
   * and plunges back down into the shaft with a deep echoing splash.
   */
  triggerWellHeadless(wellPos: Vector3): void {
    if (!this.headlessRoot) return;
    this.cancelActive();
    this.pacer.markTriggered("wellHeadless", true);
    const root = this.headlessRoot;
    const away = wellPos.subtract(this.eye);
    away.y = 0;
    if (away.lengthSquared() < 0.01) away.set(0, 0, -1);
    away.normalize();
    const standPos = wellPos.add(away.scale(1.18));
    const groundY = this.groundAt(standPos.x, standPos.z);

    this.resetHeadlessPose();
    root.position.set(standPos.x, groundY - 0.62, standPos.z);
    root.setEnabled(true);

    this.villageAudio?.triggerVacuum(3.2, 0.08);
    this.lights.storm.strike();
    this.villageAudio?.play("wellSplash", wellPos, 0.95, 0.84);
    this.villageAudio?.play("preayBreath", standPos.add(new Vector3(0, 1.2, 0)), 1.0);
    this.villageAudio?.play("soraGasp", this.eye, 0.9);
    this.game.player.jolt(0.88, -1);
    this.game.atmosphere.scare();
    this.fright = 1;
    this.onClockGlitch?.(8);

    let cutDone = false;
    this.startSeq(
      "wellHeadless",
      (t) => {
        const yaw = Math.atan2(this.eye.x - root.position.x, this.eye.z - root.position.z);
        if (t < 0.48) {
          // Smooth eerie rise from behind the dark brick rim
          const rise = 1 - (1 - t / 0.48) ** 3;
          root.position.y = groundY - 0.62 + rise * 0.62;
        } else if (t < 1.15) {
          // Leans forward toward Sora over the brick curb
          const lunge = Math.min(1, (t - 0.48) / 0.62);
          root.position.x = standPos.x - away.x * lunge * 0.45;
          root.position.z = standPos.z - away.z * lunge * 0.45;
          root.position.y = groundY;
        }
        this.animateHeadlessLiving(root, yaw, t, 1.9);

        if (t >= 1.05 && !cutDone) {
          cutDone = true;
          this.lights.blackout(0.46);
          this.villageAudio?.play("shockHit", this.eye, 0.92);
          this.villageAudio?.playNearEar("preayBreath", this.eye, this.forward, 1, 0.55, 1.0);
          this.game.player.jolt(0.95, 1);
        }
        if (t >= 1.24 && root.isEnabled()) {
          root.setEnabled(false);
          this.villageAudio?.play("wellSplash", wellPos, 1.0, 0.72);
        }
        return t >= 1.55;
      },
      () => {
        this.resetHeadlessPose();
        root.setEnabled(false);
      },
    );
  }

  /**
   * Provoked Preay response (snapped red fence cord, wrong 1-vs-3 shrine incense, or cursed
   * 00:00/03:00/20:12 hall clock): sound vacuum + neck crack + rapid stumbling lunge toward Sora
   * -> pitch-black lamp blackout cut + close-ear rush past.
   */
  triggerProvokedPreay(origin: Vector3): void {
    this.cancelActive();
    this.pacer.aggravate(1);
    this.pacer.markTriggered("provokedPreay", true);
    const feet = this.game.player.feet;
    const lookFlat = new Vector3(this.forward.x, 0, this.forward.z);
    if (lookFlat.lengthSquared() < 0.04) {
      lookFlat.copyFrom(origin.subtract(feet));
      lookFlat.y = 0;
    }
    if (lookFlat.lengthSquared() < 0.04) lookFlat.set(0, 0, -1);
    lookFlat.normalize();

    const indoors = feet.y > 1.8;
    const spawnDist = indoors ? 3.5 : 4.8;
    const at = feet.add(lookFlat.scale(spawnDist));
    at.y = indoors ? 2.5 : this.groundAt(at.x, at.z);

    this.preay.place(at, Math.atan2(this.eye.x - at.x, this.eye.z - at.z));
    this.preay.watch(this.eye);
    this.preay.setHorror({ neckTilt: 0.52, overShoulder: 0, hunch: 0.42 });
    this.preay.triggerTwitch(0.9, 0.55);
    this.preay.setEnabled(true);

    this.lights.storm.strike();
    this.villageAudio?.triggerVacuum(3.6, 0.06);
    this.villageAudio?.play("preayNeckCrack", at, 1.0);
    this.villageAudio?.play("preayRattle", at, 1.0);
    this.villageAudio?.play("stingerLow", this.eye, 0.9);
    this.score?.sting("shock", 0.85);
    this.game.player.jolt(0.75, -1);
    this.game.atmosphere.scare();
    this.fright = 1;
    this.onClockGlitch?.(10);

    let lungeStarted = false;
    let blackoutDone = false;
    const rushTarget = new Vector3();

    this.startSeq(
      "provokedPreay",
      (t, dt) => {
        this.preay.watch(this.eye);
        if (t < 0.55) {
          this.preay.standStill(dt);
        } else if (!blackoutDone) {
          if (!lungeStarted) {
            lungeStarted = true;
            this.preay.setHorror({ neckTilt: -0.64, hunch: 0.68 });
            this.preay.triggerTwitch(1.0, 0.45);
            this.lights.storm.strike();
            this.villageAudio?.play("preayNeckCrack", this.preay.position, 1.0, 1.14);
          }
          // Physically hurry straight toward Sora!
          rushTarget.set(this.game.player.feet.x, at.y, this.game.player.feet.z);
          this.preay.walkTowards(dt, rushTarget, 1.55);

          const dist = Math.hypot(
            this.preay.position.x - this.game.player.feet.x,
            this.preay.position.z - this.game.player.feet.z,
          );
          if (dist <= 2.15 || t >= 1.85) {
            blackoutDone = true;
            this.lights.blackout(0.48);
            this.villageAudio?.play("shockHit", this.eye, 1.0);
            this.villageAudio?.play("soraGasp", this.eye, 0.95);
            this.villageAudio?.playNearEar("preayBreath", this.eye, this.forward, 1, 0.52, 1.08);
            this.villageAudio?.playNearEar("preayStep", this.eye, this.forward, 1, 0.8, 1.0);
            this.game.player.jolt(1.05, 1);
            this.game.atmosphere.scare();
          }
        } else {
          this.preay.standStill(dt);
          if (t >= 2.02 && this.preay.isEnabled()) {
            this.spawnWetFootprints(this.preay.position, this.preay.heading);
            this.preay.release();
            this.preay.setEnabled(false);
          }
          if (t >= 2.38) return true;
        }
        return false;
      },
      () => {
        this.preay.release();
        this.preay.setEnabled(false);
      },
    );
  }

  // ------------------------------------------------------------------ Frame Update

  update(dt: number, suppressed: boolean): void {
    const g = this.game;
    this.clock += dt;
    this.eye.copyFrom(g.camera.globalPosition);
    g.camera.getDirectionToRef(Axis.Z, this.forward);
    this.fright = Math.max(0, this.fright - dt * 0.24);

    if (suppressed || g.cutscene || g.threatActive || g.hiding) {
      if (this.activeSeq) this.cancelActive();
      return;
    }

    // Update active choreography sequence
    if (this.activeSeq) {
      this.activeSeq.elapsed += dt;
      if (this.activeSeq.step(this.activeSeq.elapsed, dt)) {
        this.activeSeq.end();
        this.activeSeq = null;
      }
      return;
    }

    this.pacer.tick(dt, false);
    this.updateCorpseGaslight();
    this.updateRearPresenceTrigger(dt);
    this.updateAmbientHauntAudio(dt);

    const feet = g.player.feet;

    // Beat 1: Roadside Corner-Peeker Preay (leans out, then physically hurries behind shop corner!)
    if (
      this.pacer.canTriggerAutonomous("roadsidePeeker", false) &&
      feet.z > 43 &&
      feet.z < 56 &&
      Math.hypot(feet.x - ROADSIDE_PEEK_SPOT.x, feet.z - ROADSIDE_PEEK_SPOT.z) < 13.5 &&
      Math.hypot(feet.x - ROADSIDE_PEEK_SPOT.x, feet.z - ROADSIDE_PEEK_SPOT.z) > 4.2
    ) {
      this.startRoadsidePeeker();
      return;
    }

    // Beat 2: Peripheral Shop-Doorway Crossing (walks silently across open Moto Shop interior!)
    if (
      this.pacer.canTriggerAutonomous("shopDoorCrossing", false) &&
      feet.z > 48 &&
      feet.z < 57.5 &&
      feet.x > 4 &&
      feet.x < 17 &&
      this.forward.z > 0.35
    ) {
      this.startShopDoorCrossing();
      return;
    }

    // Beat 3: Back-Turned Weeping Preay (continuous weeping cuts DEAD -> 115° twist -> rush -> blackout)
    if (
      this.pacer.canTriggerAutonomous("weepingBackTurned", false) &&
      g.flags.get("ep1.puzzle.gate.open", false) &&
      Math.hypot(feet.x - WEEPING_SPOT.x, feet.z - WEEPING_SPOT.z) < 16 &&
      Math.hypot(feet.x - WEEPING_SPOT.x, feet.z - WEEPING_SPOT.z) > 4.5
    ) {
      this.startWeepingBackTurned();
      return;
    }

    // Beat 4: Strobe-Stalker Preay on the mud path once well or 1+ ward is active
    if (
      this.pacer.canTriggerAutonomous("strobeCloser", false) &&
      (g.flags.get("ep1.puzzle.well.complete", false) ||
        g.flags.get("ep1.puzzle.wardSnapped", false)) &&
      feet.y < 1.2 &&
      feet.z > 8 &&
      feet.z < 28 &&
      this.forward.z < -0.5
    ) {
      this.startStrobeCloser();
      return;
    }

    // Beat 5: Shadow-Only Silhouette along the funeral banner under the house
    if (
      this.pacer.canTriggerAutonomous("shadowBanner", false) &&
      inFuneralRoom(feet) &&
      this.lights.flashing
    ) {
      this.startShadowBanner();
    }
  }

  // ------------------------------------------------------------------ Autonomous Asian Horror Choreography

  /**
   * Beat 1 — Corner-Peeker: leans out from the west roadside shop shoulder staring at Sora;
   * the instant Sora's lamp catches her, her neck cracks and she physically turns & hurries
   * behind the dark shop corner out of sight (NEVER pops out in plain lamplight!).
   */
  private startRoadsidePeeker(): void {
    this.pacer.markTriggered("roadsidePeeker");
    const at = new Vector3(
      ROADSIDE_PEEK_SPOT.x,
      Math.max(this.groundAt(ROADSIDE_PEEK_SPOT.x, ROADSIDE_PEEK_SPOT.z), 0.12),
      ROADSIDE_PEEK_SPOT.z,
    );
    const retreat = new Vector3(
      ROADSIDE_PEEK_RETREAT.x,
      Math.max(this.groundAt(ROADSIDE_PEEK_RETREAT.x, ROADSIDE_PEEK_RETREAT.z), 0.12),
      ROADSIDE_PEEK_RETREAT.z,
    );
    const toEye = Math.atan2(this.eye.x - at.x, this.eye.z - at.z);
    this.preay.place(at, toEye);
    this.preay.watch(this.eye);
    this.preay.setHorror({ neckTilt: 0.72, overShoulder: 0, hunch: 0.36 });
    this.preay.setEnabled(true);
    this.villageAudio?.triggerVacuum(3.6, 0.14);
    this.villageAudio?.play("preayWhisper", at, 0.9);
    this.lights.flickerBurst(0.65);

    let seenTime = 0;
    let retreating = false;
    let retreatTime = 0;

    this.startSeq(
      "roadsidePeeker",
      (t, dt) => {
        if (!retreating) {
          this.preay.watch(this.eye);
          this.preay.standStill(dt);
          const dist = Vector3.Distance(this.eye, at);
          const looking = this.isLookingAt(at.add(new Vector3(0, 1.45, 0)), 0.82);
          if (looking || dist < 6.0) seenTime += dt;
          if (seenTime >= 0.36) {
            retreating = true;
            this.preay.triggerTwitch(1, 0.32);
            this.preay.setHorror({ neckTilt: -0.45, hunch: 0.55 });
            this.villageAudio?.play("preayNeckCrack", at, 0.98);
            this.villageAudio?.play("stingerLow", at, 0.75);
            this.game.player.jolt(0.45, -1);
            this.fright = 0.78;
            this.spawnWetFootprints(at, Math.atan2(retreat.x - at.x, retreat.z - at.z));
          }
          if (t >= 10.0) {
            retreating = true;
          }
        } else {
          retreatTime += dt;
          this.preay.watch(null);
          const arrived = this.preay.walkTowards(dt, retreat, 1.5);
          if (arrived || retreatTime >= 2.4) {
            this.preay.setEnabled(false);
            return true;
          }
        }
        return false;
      },
      () => this.preay.setEnabled(false),
    );
  }

  /**
   * Beat 2 — Peripheral Shop Doorway Crossing: Preay silently walks straight across the open
   * Moto Shop doorway in silhouette while the shop light stutters, disappearing behind the right
   * interior wall — rewarding players who walk inside the shop with wet footprints & a whisper!
   */
  private startShopDoorCrossing(): void {
    this.pacer.markTriggered("shopDoorCrossing");
    const from = new Vector3(
      SHOP_CROSSING_PATH.from.x,
      SHOP_CROSSING_PATH.from.y,
      SHOP_CROSSING_PATH.from.z,
    );
    const to = new Vector3(
      SHOP_CROSSING_PATH.to.x,
      SHOP_CROSSING_PATH.to.y,
      SHOP_CROSSING_PATH.to.z,
    );
    this.preay.place(from, Math.atan2(to.x - from.x, to.z - from.z));
    this.preay.watch(this.eye);
    this.preay.setHorror({ neckTilt: 0.45, overShoulder: 0.85, hunch: 0.34 });
    this.preay.setEnabled(true);
    this.lights.flickerBurst(1.4);
    this.villageAudio?.play("bulbFlicker", from, 0.9);
    this.villageAudio?.play("woodCreak", from, 0.85);
    this.fright = 0.62;

    let whispered = false;
    this.startSeq(
      "shopDoorCrossing",
      (t, dt) => {
        this.preay.watch(this.eye);
        const done = this.preay.walkTowards(dt, to, 1.05);
        if (!whispered && t >= 1.2) {
          whispered = true;
          this.villageAudio?.play("preayWhisper", this.preay.position, 0.82);
          this.spawnWetFootprints(
            new Vector3(12.2, 0.47, 60.4),
            Math.atan2(to.x - from.x, to.z - from.z),
          );
        }
        if (done || t >= 3.8) {
          this.preay.setEnabled(false);
          return true;
        }
        return false;
      },
      () => this.preay.setEnabled(false),
    );
  }

  /**
   * Beat 3 — Back-Turned Weeping Preay:
   * Audible continuous spatial weeping down the dark yard lane. The moment Sora shines her lamp
   * or steps closer: weeping cuts STONE DEAD -> 115° grotesque over-shoulder neck twist ->
   * snaps around and hurries 3 terrifying steps straight at Sora -> pitch-black blackout cut!
   */
  private startWeepingBackTurned(): void {
    this.pacer.markTriggered("weepingBackTurned");
    const at = new Vector3(
      WEEPING_SPOT.x,
      this.groundAt(WEEPING_SPOT.x, WEEPING_SPOT.z),
      WEEPING_SPOT.z,
    );
    const awayYaw = Math.atan2(at.x - this.eye.x, at.z - this.eye.z);
    this.preay.place(at, awayYaw);
    this.preay.watch(null);
    this.preay.setHorror({ neckTilt: 0.14, overShoulder: 0, hunch: 0.58 });
    this.preay.setEnabled(true);
    this.villageAudio?.startWeeping(at, 0.95);

    let disturbedAt = -1;
    let rushing = false;
    let blackoutAt = -1;

    this.startSeq(
      "weepingBackTurned",
      (t, dt) => {
        const dist = Vector3.Distance(this.eye, at);
        const looking = this.isLookingAt(at.add(new Vector3(0, 1.4, 0)), 0.8);

        if (disturbedAt < 0) {
          this.preay.standStill(dt);
          if ((looking && dist < 11.5) || dist < 5.5) {
            disturbedAt = t;
            // Weeping cuts STONE DEAD into vacuum silence
            this.villageAudio?.stopWeeping();
            this.villageAudio?.triggerVacuum(4.5, 0.06);
            this.preay.setHorror({ neckTilt: -0.62, overShoulder: 1.95, hunch: 0.72 });
            this.villageAudio?.play("preayNeckCrack", at, 1.0, 0.86);
            this.villageAudio?.play("stingerLow", at, 0.9);
            this.fright = 0.88;
            this.onClockGlitch?.(8);
          }
          if (t >= 16) {
            this.villageAudio?.stopWeeping();
            this.preay.setEnabled(false);
            return true;
          }
          return false;
        }

        const since = t - disturbedAt;
        if (since < 1.15) {
          this.preay.standStill(dt);
          return false;
        }

        if (blackoutAt < 0) {
          if (!rushing) {
            rushing = true;
            this.preay.setHorror({ neckTilt: 0.58, overShoulder: 0, hunch: 0.65 });
            this.preay.triggerTwitch(1.0, 0.55);
            this.preay.watch(this.eye);
            this.villageAudio?.play("preayRattle", this.preay.position, 1.0);
            this.lights.storm.strike();
            this.game.player.jolt(0.65, -1);
          }
          const goal = new Vector3(
            this.game.player.feet.x,
            this.groundAt(this.game.player.feet.x, this.game.player.feet.z),
            this.game.player.feet.z,
          );
          this.preay.walkTowards(dt, goal, 1.55);
          const curDist = Math.hypot(
            this.preay.position.x - this.game.player.feet.x,
            this.preay.position.z - this.game.player.feet.z,
          );
          if (curDist <= 2.3 || since >= 2.35) {
            blackoutAt = t;
            this.lights.blackout(0.48);
            this.villageAudio?.play("shockHit", this.eye, 1.0);
            this.villageAudio?.play("soraGasp", this.eye, 0.95);
            this.villageAudio?.playNearEar("preayBreath", this.eye, this.forward, 1, 0.55, 1.05);
            this.villageAudio?.playNearEar("preayStep", this.eye, this.forward, 1, 0.8, 1.0);
            this.game.player.jolt(1.05, 1);
            this.game.atmosphere.scare();
            this.fright = 1.0;
          }
          return false;
        }

        this.preay.standStill(dt);
        const sinceCut = t - blackoutAt;
        if (sinceCut >= 0.16 && this.preay.isEnabled()) {
          this.spawnWetFootprints(this.preay.position, this.preay.heading);
          this.preay.setEnabled(false);
        }
        return sinceCut >= 0.55;
      },
      () => {
        this.villageAudio?.stopWeeping();
        this.preay.setEnabled(false);
      },
    );
  }

  /**
   * Beat 4 — Lightning Strobe-Stalker:
   * Advances silently in the pitch-dark gaps between 3 lightning flashes along Sora's live view
   * (`12.5 m -> 7.2 m -> 3.6 m`), then lurches forward before a blackout cut + close-ear rush.
   */
  private startStrobeCloser(): void {
    this.pacer.markTriggered("strobeCloser");
    const distances = [12.5, 7.2, 3.6];
    const tilts = [0.36, -0.62, 0.78];
    const sideOffsets = [0.7, -0.55, 0.15];
    let stage = -1;
    let blackoutAt = -1;

    this.villageAudio?.triggerVacuum(5.2, 0.08);
    this.villageAudio?.play("stingerLow", this.eye, 0.85);
    this.fright = 0.82;
    this.onClockGlitch?.(8);

    this.startSeq(
      "strobeCloser",
      (t, dt) => {
        if (blackoutAt >= 0) {
          this.preay.standStill(dt);
          if (t - blackoutAt >= 0.16 && this.preay.isEnabled()) {
            this.spawnWetFootprints(this.preay.position, this.preay.heading);
            this.preay.release();
            this.preay.setEnabled(false);
          }
          return t - blackoutAt >= 0.52;
        }

        const wantStage = t < 1.15 ? 0 : t < 2.25 ? 1 : 2;
        if (wantStage !== stage) {
          stage = wantStage;
          const flat = new Vector3(this.forward.x, 0, this.forward.z);
          if (flat.lengthSquared() < 0.04) flat.set(0, 0, -1);
          flat.normalize();
          const right = new Vector3(flat.z, 0, -flat.x);
          const pos = this.game.player.feet
            .add(flat.scale(distances[stage]))
            .add(right.scale(sideOffsets[stage]));
          pos.y = this.groundAt(pos.x, pos.z);
          const yaw = Math.atan2(this.eye.x - pos.x, this.eye.z - pos.z);
          this.preay.strobePose(pos, yaw, tilts[stage], "stand", 0.9 + stage * 0.7);
          this.preay.setHorror({ hunch: 0.22 + stage * 0.18 });
          this.preay.watch(this.eye);
          if (stage >= 1) this.preay.triggerTwitch(0.9, 0.4);
          this.lights.storm.strike();
          this.villageAudio?.play(
            stage === 2 ? "preayRattle" : "preayNeckCrack",
            pos,
            0.9 + stage * 0.08,
          );
          if (stage === 2) {
            this.preay.release();
            this.score?.sting("drop", 0.85);
            this.game.player.jolt(0.65, -1);
          }
        }

        if (stage === 2) {
          const goal = new Vector3(
            this.game.player.feet.x,
            this.groundAt(this.game.player.feet.x, this.game.player.feet.z),
            this.game.player.feet.z,
          );
          this.preay.walkTowards(dt, goal, 1.5);
          if (t >= 3.15 || Vector3.Distance(this.preay.position, goal) < 2.15) {
            blackoutAt = t;
            this.lights.blackout(0.46);
            this.villageAudio?.play("shockHit", this.eye, 0.98);
            this.villageAudio?.play("soraGasp", this.eye, 0.9);
            this.villageAudio?.playNearEar("preayBreath", this.eye, this.forward, -1, 0.55, 1.05);
            this.villageAudio?.playNearEar("preayStep", this.eye, this.forward, -1, 0.85, 0.95);
            this.game.player.jolt(1.0, 1);
            this.game.atmosphere.scare();
          }
        } else {
          this.preay.standStill(dt);
        }
        return false;
      },
      () => {
        this.preay.release();
        this.preay.setEnabled(false);
      },
    );
  }

  /**
   * Beat 5 — Rear-Presence Whisper & Turn-Around Scare (*P.T.* / *Shutter*):
   * Rain drops hushed; a bare footstep splashes behind Sora + an intimate HRTF whisper brushes
   * her left or right ear. Preay waits silently 3.5m behind her — if Sora spins around to check,
   * she snaps her neck and cuts the lamp to pitch black!
   */
  private startRearPresence(): void {
    this.pacer.markTriggered("extraFootstep", true);
    const feet = this.game.player.feet;
    const flat = new Vector3(this.forward.x, 0, this.forward.z);
    if (flat.lengthSquared() < 0.04) flat.set(0, 0, -1);
    flat.normalize();

    const behind = feet.subtract(flat.scale(3.4));
    behind.y = feet.y > 1.8 ? 2.5 : this.groundAt(behind.x, behind.z);
    const earSide: -1 | 1 = Math.random() < 0.5 ? -1 : 1;

    this.preay.place(behind, Math.atan2(this.eye.x - behind.x, this.eye.z - behind.z));
    this.preay.watch(this.eye);
    this.preay.setHorror({ neckTilt: 0.65 * earSide, overShoulder: 0, hunch: 0.45 });
    this.preay.setEnabled(true);

    this.villageAudio?.triggerVacuum(3.6, 0.12);
    this.fright = 0.65;

    let stepFired = false;
    let spottedAt = -1;
    let blackoutDone = false;

    this.startSeq(
      "extraFootstep",
      (t, dt) => {
        this.preay.watch(this.eye);
        this.preay.standStill(dt);

        if (t >= 0.42 && !stepFired) {
          stepFired = true;
          this.villageAudio?.play("preayStep", behind, 0.95);
          this.villageAudio?.playNearEar(
            "preayWhisper",
            this.eye,
            this.forward,
            earSide,
            0.58,
            1.0,
          );
          this.lights.flickerBurst(0.75);
        }

        const lookingBack = this.isLookingAt(behind.add(new Vector3(0, 1.45, 0)), 0.78);
        if (stepFired && spottedAt < 0 && lookingBack) {
          spottedAt = t;
          this.preay.triggerTwitch(1.0, 0.35);
          this.lights.storm.strike();
          this.villageAudio?.play("preayNeckCrack", behind, 1.0);
          this.villageAudio?.play("soraGasp", this.eye, 0.88);
          this.game.player.jolt(0.82, earSide);
          this.game.atmosphere.scare();
          this.fright = 0.96;
          this.onClockGlitch?.(6);
        }

        if (spottedAt >= 0) {
          const since = t - spottedAt;
          if (since >= 0.4 && !blackoutDone) {
            blackoutDone = true;
            this.lights.blackout(0.42);
            this.villageAudio?.play("shockHit", this.eye, 0.9);
            this.villageAudio?.playNearEar(
              "preayBreath",
              this.eye,
              this.forward,
              earSide,
              0.52,
              1.0,
            );
            this.game.player.jolt(0.9, -earSide as -1 | 1);
          }
          if (since >= 0.56 && this.preay.isEnabled()) {
            this.spawnWetFootprints(behind, this.preay.heading);
            this.preay.setEnabled(false);
          }
          return since >= 0.85;
        }

        // If Sora keeps facing forward and doesn't turn around within 3.6s, slip silently away while still unseen
        if (t >= 3.6 && !lookingBack) {
          this.preay.setEnabled(false);
          return true;
        }
        return t >= 5.0;
      },
      () => this.preay.setEnabled(false),
    );
  }

  /** Shadow-Only Banner Silhouette under the house (zero physical body when turning around). */
  private startShadowBanner(): void {
    this.pacer.markTriggered("shadowBanner");
    const side = Math.random() < 0.5 ? -1 : 1;
    this.shadeLayer.position.set(COFFIN.x, HALL.floor, BEHIND_COFFIN_BANNER);
    const from = new Vector3(side * 1.35, 0, 0);
    const to = new Vector3(-side * 1.35, 0, 0);
    this.shade.place(from, Math.atan2(to.x - from.x, 0));
    this.shadeLayer.setEnabled(true);
    this.lights.storm.strike();
    this.villageAudio?.play("preayWhisper", new Vector3(COFFIN.x, 1.5, BEHIND_COFFIN_BANNER), 0.92);
    this.fright = 0.72;

    this.startSeq(
      "shadowBanner",
      (t, dt) => {
        const done = this.shade.walkTowards(dt, to, 0.88);
        if (done || t >= 3.8) {
          this.shadeLayer.setEnabled(false);
          return true;
        }
        return false;
      },
      () => this.shadeLayer.setEnabled(false),
    );
  }

  /**
   * Shrouded Corpse Gaslight: eerie hush on discovery; once Sora walks away and turns back,
   * the corpse has vanished — leaving wet footprints leading toward the yard & a muffled sob.
   */
  private updateCorpseGaslight(): void {
    if (!this.corpseRoot || this.corpseVanished) return;
    const pos = this.corpseRoot.position;
    const dist = Vector3.Distance(this.eye, pos);
    const looking = this.isLookingAt(pos.add(new Vector3(0, 0.25, 0)), 0.72);
    if (!this.corpseSeen && dist < 11 && looking) {
      this.corpseSeen = true;
      this.villageAudio?.triggerVacuum(2.8, 0.16);
      this.villageAudio?.play("preayBreath", pos.add(new Vector3(0, 0.5, 0)), 0.85, 0.85);
      this.fright = Math.max(this.fright, 0.55);
      return;
    }
    if (this.corpseSeen && !looking && dist > 8.5 && dist < 24) {
      this.corpseVanished = true;
      this.game.flags.set("ep1.haunt.corpseVanished", true);
      this.corpseRoot.setEnabled(false);
      this.spawnWetFootprints(pos, CORPSE_SPOT.yaw);
      this.villageAudio?.play("preaySob", pos, 0.9);
      this.villageAudio?.play("preayStep", pos, 0.85);
    }
  }

  /** Tracks sustained walking so stopping can trigger the 2-stage Rear-Presence whisper/turn-around. */
  private updateRearPresenceTrigger(dt: number): void {
    const feet = this.game.player.feet;
    const moving = this.game.player.speed > 0.7 && feet.y < 0.8 && feet.z > 2 && feet.z < 52;
    if (moving) {
      this.moveStreak += dt;
      this.wasMoving = true;
    } else if (this.wasMoving) {
      this.wasMoving = false;
      if (this.moveStreak >= 3.5 && this.pacer.canTriggerAutonomous("extraFootstep", false)) {
        this.moveStreak = 0;
        this.startRearPresence();
        return;
      }
      this.moveStreak = 0;
    }
  }

  /**
   * Subtle spatialized environmental haunt cues between major set-piece encounters so the
   * village never feels lifeless: distant shop knocks, upstairs footsteps, wet wood claws,
   * or a faint muffled sob drifting across the rain.
   */
  private updateAmbientHauntAudio(dt: number): void {
    this.ambientCueTimer -= dt;
    if (this.ambientCueTimer > 0) return;
    this.ambientCueTimer = 17 + Math.random() * 14;
    const feet = this.game.player.feet;

    if (feet.z > 40) {
      // Roadside shops zone: hollow knock inside a dark shop or distant whisper in the alley
      const side = Math.random() < 0.5 ? -1 : 1;
      const at = new Vector3(
        feet.x + side * (7 + Math.random() * 5),
        1.4,
        feet.z + (Math.random() - 0.5) * 10,
      );
      const roll = Math.random();
      if (roll < 0.4) {
        this.villageAudio?.play("knock", at, 0.65, 0.9);
        this.lights.flickerBurst(0.45);
      } else if (roll < 0.72) {
        this.villageAudio?.play("doorCreak", at, 0.65);
      } else {
        this.villageAudio?.play("preayWhisper", at, 0.62);
      }
    } else if (feet.z < 4 && feet.y < 1.5) {
      // Courtyard / under-house: slow bare footsteps pacing on the upstairs teak planks!
      const overhead = new Vector3(feet.x + (Math.random() - 0.5) * 4, 2.7, feet.z - 2);
      this.villageAudio?.play("preayStep", overhead, 0.72, 0.85);
      this.villageAudio?.play("woodCreak", overhead, 0.75);
    } else {
      // Track / compound yard: distant wood clawing or faint ghostly sob in the palms
      const a = Math.random() * Math.PI * 2;
      const dist = 10 + Math.random() * 8;
      const at = new Vector3(feet.x + Math.cos(a) * dist, 1.5, feet.z + Math.sin(a) * dist);
      this.villageAudio?.play(Math.random() < 0.55 ? "preayClaw" : "preaySob", at, 0.68);
    }
  }

  /** Applies unsettling living headless torso sway, uneven breath heave, and subtle jitter. */
  private animateHeadlessLiving(
    root: TransformNode,
    targetYaw: number,
    t: number,
    intensity: number,
  ): void {
    const sway = Math.sin(t * 2.1) * 0.045 * intensity + Math.sin(t * 7.3) * 0.012 * intensity;
    const pitchLean = 0.04 * intensity + Math.sin(t * 1.45) * 0.025 * intensity;
    const breathHeave = 1 + Math.sin(t * 2.6) * 0.014 * intensity;
    root.rotation.set(pitchLean, targetYaw, sway);
    root.scaling.set(HEADLESS_SCALE, HEADLESS_SCALE * breathHeave, HEADLESS_SCALE);
  }

  private resetHeadlessPose(): void {
    if (!this.headlessRoot) return;
    this.headlessRoot.rotation.set(0, 0, 0);
    this.headlessRoot.scaling.setAll(HEADLESS_SCALE);
  }

  /** Leaves 4 wet dark footprints leading away from a vanished apparition. */
  private spawnWetFootprints(origin: Vector3, yaw: number): void {
    if (!this.footprintMat) return;
    const scene = this.game.scene;
    for (let i = 0; i < 4; i++) {
      const side = i % 2 === 0 ? -0.14 : 0.14;
      const dist = 0.35 + i * 0.55;
      const px = origin.x + Math.sin(yaw) * dist + Math.cos(yaw) * side;
      const pz = origin.z + Math.cos(yaw) * dist - Math.sin(yaw) * side;
      const py =
        origin.y > 0.35 && origin.y < 1.0 ? origin.y + 0.012 : this.groundAt(px, pz) + 0.015;
      const print = CreateDisc(
        `wet_fp_${this.footprints.length}`,
        { radius: 0.11, tessellation: 12 },
        scene,
      );
      print.rotation.x = Math.PI / 2;
      print.scaling.set(0.62, 1.45, 1);
      print.rotation.y = yaw;
      print.position.set(px, py, pz);
      print.material = this.footprintMat;
      print.isPickable = false;
      this.footprints.push(print);
    }
  }

  private isLookingAt(target: Vector3, dotThreshold: number): boolean {
    const to = target.subtract(this.eye);
    const len = to.length();
    if (len < 0.05) return true;
    return Vector3.Dot(this.forward, to.scale(1 / len)) >= dotThreshold;
  }

  private startSeq(
    id: VillageHauntId,
    step: (t: number, dt: number) => boolean,
    end: () => void,
  ): void {
    this.activeSeq = { id, elapsed: 0, step, end };
  }

  private cancelActive(): void {
    if (!this.activeSeq) return;
    this.activeSeq.end();
    this.activeSeq = null;
  }

  dispose(): void {
    this.cancelActive();
    this.villageAudio?.stopWeeping();
    this.preay.dispose();
    this.shade.dispose();
    this.shadeLayer.dispose();
    this.headlessRoot?.dispose();
    this.corpseRoot?.dispose();
    for (const fp of this.footprints) fp.dispose();
    this.footprints.length = 0;
    this.footprintMat?.dispose();
  }
}
