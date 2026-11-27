import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { PhysicsShapeBox } from "@babylonjs/core/Physics/v2/physicsShape";
import type { Game } from "@/core/Game";
import type { Vigil } from "../act1/Vigil";
import type { VillageAudio } from "../audio/VillageAudio";
import {
  PUZZLE_SPOTS,
  WARD_STATIONS,
  WellMechanism,
  checkClockDial,
  checkGateCode,
  checkWardStation,
  solvedWardCount,
  type WardOfferingId,
  type WardStationId,
} from "../data/villagePuzzles";
import {
  VillagePuzzleModels,
  type BarberRadioRig,
  type WardStationHandles,
  type WellRigHandles,
} from "./VillagePuzzleModels";
import { VillagePuzzleUi } from "./VillagePuzzleUi";

export interface PuzzleHorrorCallbacks {
  onBarberRadioSilenced?: (shopPos: Vector3) => void;
  onFenceWardSnapped?: (at: Vector3) => void;
  onWellTugStart?: (wellPos: Vector3) => void;
  onWellTugFailed?: (wellPos: Vector3) => void;
  onWardMistake?: (stationPos: Vector3, stationId: WardStationId) => void;
  onClockCursed?: (clockPos: Vector3) => void;
  onMilestoneClock?: (time: string, label: string) => void;
}

/**
 * Physical obstacles & 4 interconnected complex puzzles across Episode 1's village:
 *
 * 1. Roadside Shops -> Sealed Compound Gate (3-dial brass padlock OR risky red-cord fence bypass)
 * 2. Brick Village Well Mechanism (rig stone counterweight + servants'-hut hook -> 4-stage risk haul)
 * 3. Torn Betel Diagram + Four-Direction Ancestral Ward (3 folklore stations: offering + 1 vs 3 incense)
 * 4. Stopped 20:12 Hall Pendulum Clock (fit sunken brass pendulum -> dial deduced vigil hour 01:12)
 */
export class VillagePuzzles {
  readonly well = new WellMechanism();
  private readonly ui = new VillagePuzzleUi();
  private readonly models: VillagePuzzleModels;
  private readonly nodes: TransformNode[] = [];
  private readonly colliders: { node: TransformNode; body: PhysicsBody }[] = [];
  private gateCollider: { node: TransformNode; body: PhysicsBody } | null = null;
  private sideFenceCollider: { node: TransformNode; body: PhysicsBody } | null = null;
  private gateBarNode: TransformNode | null = null;
  private sidePlankNode: TransformNode | null = null;
  private barberRadioSound: StaticSound | null = null;
  private shopBuzzSound: StaticSound | null = null;
  private barberRadioRig: BarberRadioRig | null = null;
  private clockPendulumPivot: TransformNode | null = null;
  private clockHourHand: TransformNode | null = null;
  private clockMinuteHand: TransformNode | null = null;
  private clockTickTimer = 0;
  private radioKnockTimer = -1;
  private radioKnocksLeft = 0;
  private radioKnocksPaused = 0;
  private barberRadioPos = Vector3.Zero();
  private wellPos = Vector3.Zero();
  private clockPos = Vector3.Zero();
  private gateDigits: [number, number, number] = [0, 0, 0];
  private wellSweepAngle = 0;
  private wellRig: WellRigHandles | null = null;
  private wellTugInitial = 4.2;
  private wellShaftBreathTimer = 0;
  private readonly stationVisuals = new Map<WardStationId, WardStationHandles>();
  private time = 0;

  constructor(
    private readonly game: Game,
    private readonly vigil: Vigil,
    private readonly villageAudio: VillageAudio | null,
    private readonly groundAt: (x: number, z: number) => number,
    private readonly saveProgress: () => Promise<unknown>,
    private readonly callbacks: PuzzleHorrorCallbacks = {},
  ) {
    this.models = new VillagePuzzleModels(game.scene);
    this.game.flags.set("ep1.village.puzzlesActive", true);
    this.well.restore(game.flags);
    this.buildPropsAndObstacles();
    game.bus.on("interact:use", ({ id }) => this.use(id));
    game.scene.onDisposeObservable.addOnce(() => this.dispose());
  }

  get uiOpen(): boolean {
    return this.ui.isOpen;
  }

  async makeSounds(): Promise<void> {
    if (!this.villageAudio) return;
    if (!this.game.flags.get("ep1.puzzle.barberRadioOff", false)) {
      this.barberRadioSound = await this.villageAudio.createSpatialLoop(
        "village_barber_radio",
        "amb_ep1_village_radio",
        this.barberRadioPos,
        "sfx",
        { distanceModel: "linear", minDistance: 2.0, maxDistance: 16, volume: 0.62 },
      );
      this.barberRadioSound?.play();
    }
    const [nx, nz] = PUZZLE_SPOTS.noodleClue;
    const ny = 2.6;
    this.shopBuzzSound = await this.villageAudio.createSpatialLoop(
      "village_noodle_buzz",
      "amb_ep1_village_shop_buzz",
      new Vector3(nx, ny, nz),
      "sfx",
      { distanceModel: "linear", minDistance: 1.5, maxDistance: 9.5, volume: 0.22 },
    );
    this.shopBuzzSound?.play();
  }

  update(dt: number): void {
    this.time += dt;
    const g = this.game;

    // Subtle vintage radio dial flicker while static is still playing
    if (this.barberRadioRig) {
      const radioOn = !g.flags.get("ep1.puzzle.barberRadioOff", false);
      if (radioOn) {
        const hum = 0.96 + 0.14 * Math.sin(this.time * 23) + 0.06 * Math.sin(this.time * 57);
        this.barberRadioRig.dialLight.intensity = hum;
      } else {
        this.barberRadioRig.dialLight.intensity = 0;
      }
    }

    // Animate well sweep haul depth, rope stretch & attached mechanical parts smoothly
    if (this.wellRig) {
      this.wellRig.attachedWeightNode.setEnabled(this.well.hasWeight);
      this.wellRig.attachedHookNode.setEnabled(this.well.hasHook);

      const targetProgress =
        this.well.phase === "complete"
          ? 1
          : this.well.phase === "pull3"
            ? 0.72
            : this.well.phase === "tug_danger"
              ? 0.45 + Math.sin(this.time * 19) * 0.045
              : this.well.phase === "pull1"
                ? 0.34
                : 0;
      this.wellSweepAngle += (targetProgress - this.wellSweepAngle) * Math.min(1, dt * 4.5);
      this.wellRig.sweepNode.rotation.x = -0.25 + this.wellSweepAngle * 0.55;
      const bucketY = 0.28 + this.wellSweepAngle * 0.72;
      this.wellRig.bucketNode.position.y = bucketY;

      const ropeTop = 1.65;
      const ropeBot = bucketY + 0.3;
      const ropeLen = Math.max(0.18, ropeTop - ropeBot);
      this.wellRig.ropeMesh.scaling.y = ropeLen / 1.4;
      this.wellRig.ropeMesh.position.y = ropeBot + ropeLen * 0.5;
    }

    // Tick the brick well tug tension window & update diegetic HUD bar
    if (this.well.phase === "tug_danger") {
      const lampOpen = this.vigil.lamp.state === "open";
      const movingFast = g.player.speed > 0.45;
      const progress = Math.max(
        0,
        Math.min(1, 1 - this.well.tugRemaining / Math.max(0.1, this.wellTugInitial)),
      );
      const warning = lampOpen
        ? "Douse the oil lamp (F) — it sees the flame!"
        : movingFast
          ? "Hold still — the rope is straining!"
          : "Keep dark and still — wait for the grip below to release…";
      this.ui.setWellTension(true, progress, warning, lampOpen || movingFast);

      this.wellShaftBreathTimer -= dt;
      if (this.wellShaftBreathTimer <= 0) {
        this.wellShaftBreathTimer = 1.65;
        this.villageAudio?.play(
          Math.random() < 0.55 ? "preayBreath" : "waterStir",
          this.wellPos.add(new Vector3(0, 0.35, 0)),
          0.78,
          0.84,
        );
      }

      if (this.well.update(dt, lampOpen, movingFast) === "released") {
        this.ui.setWellTension(false, 0, "", false);
        this.villageAudio?.play("wellSplash", this.wellPos, 0.72, 0.92);
        void g.subtitles.say(
          "Sora",
          "The weight below let go… pull it up quickly while the lamp stays out.",
          4,
        );
      }
    } else {
      this.ui.setWellTension(false, 0, "", false);
    }

    // Barber shop behind-shutter knock rhythm (4 sharp knocks -> pause -> repeats twice!)
    if (this.radioKnockTimer >= 0) {
      this.radioKnockTimer -= dt;
      if (this.radioKnockTimer <= 0) {
        if (this.radioKnocksLeft > 0) {
          this.villageAudio?.play(
            "knock",
            new Vector3(
              PUZZLE_SPOTS.barberGhost[0],
              this.barberRadioPos.y + 0.35,
              PUZZLE_SPOTS.barberGhost[1],
            ),
            0.95,
          );
          this.radioKnocksLeft--;
          this.radioKnockTimer = 0.42;
        } else if (this.radioKnocksPaused > 0) {
          this.radioKnocksPaused--;
          this.radioKnocksLeft = 4;
          this.radioKnockTimer = 2.4;
        } else {
          this.radioKnockTimer = -1;
        }
      }
    }

    // Animate hall wall clock brass lyre pendulum once fitted
    const fitted = g.flags.get("ep1.puzzle.clock.pendulumFitted", false);
    if (this.clockPendulumPivot) {
      this.clockPendulumPivot.setEnabled(fitted);
      if (fitted) {
        this.clockPendulumPivot.rotation.z = Math.sin(this.time * Math.PI) * 0.16;
        this.clockTickTimer += dt;
        if (this.clockTickTimer >= 1.0) {
          this.clockTickTimer %= 1.0;
          if (Vector3.Distance(g.camera.globalPosition, this.clockPos) < 12) {
            this.villageAudio?.play("clockTick", this.clockPos, 0.52);
          }
        }
      }
    }

    // Candle flicker & solved physical offerings / incense sticks on ward stations
    for (const [id, entry] of this.stationVisuals) {
      const lit = g.flags.get(`ep1.puzzle.ward.${id}`, false);
      entry.flameMesh.setEnabled(lit);
      entry.solvedGroup.setEnabled(lit);
      entry.light.intensity = lit ? 1.45 + 0.25 * Math.sin(this.time * 11 + id.length) : 0;
    }
  }

  private buildPropsAndObstacles(): void {
    const g = this.game;
    const flags = g.flags;

    const addPropAt = (
      id: string,
      x: number,
      y: number,
      z: number,
      yaw: number,
      build: (root: TransformNode) => void,
      enabled = true,
    ): TransformNode => {
      const root = new TransformNode(id, g.scene);
      root.position.set(x, y, z);
      root.rotation.y = yaw;
      build(root);
      this.nodes.push(root);
      root.setEnabled(enabled);
      if (enabled) g.interaction.add(id, root);
      return root;
    };

    // -------------------------------------------------------- 1. Sealed Compound Gate & Roadside Shops
    const gateOpen = flags.get("ep1.puzzle.gate.open", false);
    const [gx, gz] = PUZZLE_SPOTS.gate;
    const gy = this.groundAt(gx, gz);
    this.gateBarNode = addPropAt(
      "interact_village_gate_lock",
      gx,
      gy,
      gz,
      0,
      (root) => this.models.buildGateLock(root),
      !gateOpen,
    );
    if (!gateOpen) {
      this.gateCollider = this.addStaticCollider(
        "col_village_gate_bar",
        new Vector3(gx, gy + 1.1, gz),
        new Vector3(3.8, 2.4, 0.55),
      );
    }

    // Risky alternative obstacle: red-cord-bound loose boards in side fence
    const sideOpen = flags.get("ep1.puzzle.sideFence.open", false);
    const [fx, fz] = PUZZLE_SPOTS.sideFence;
    const fy = this.groundAt(fx, fz);
    this.sidePlankNode = addPropAt(
      "interact_side_fence_ward",
      fx,
      fy,
      fz,
      0,
      (root) => this.models.buildSideFenceWard(root),
      !sideOpen,
    );
    if (!sideOpen) {
      this.sideFenceCollider = this.addStaticCollider(
        "col_side_fence_ward",
        new Vector3(fx, fy + 1.1, fz),
        new Vector3(1.6, 2.4, 0.45),
      );
    }

    // Roadside Shop Clue 1: Noodle Stall 1990s Khmer Calendar on real wooden veranda table (Y = 1.45)
    const [nx, nz] = PUZZLE_SPOTS.noodleClue;
    addPropAt("interact_shop_noodle_clue", nx, 1.45, nz, Math.PI + 0.35, (root) =>
      this.models.buildNoodleCalendar(root),
    );

    // Roadside Shop Clue 2: Barber Shop Vintage Valve Radio on real wooden veranda bench (Y = 0.91)
    const [bx, bz] = PUZZLE_SPOTS.barberRadio;
    const radioOn = !flags.get("ep1.puzzle.barberRadioOff", false);
    this.barberRadioPos = new Vector3(bx, 0.91, bz);
    addPropAt("interact_shop_barber_radio", bx, 0.91, bz, 0.14, (root) => {
      this.barberRadioRig = this.models.buildBarberRadio(root, this.barberRadioPos, radioOn);
    });

    // Roadside Shop Clue 3: Moto Shop Workbench + Open Kerosene Ledger (Digit 2) & Forged Crowbar (Y = 0.48)
    const [mx, mz] = PUZZLE_SPOTS.motoLedger;
    addPropAt("interact_shop_moto_ledger", mx, 0.48, mz, Math.PI - 0.14, (root) =>
      this.models.buildMotoLedgerBench(root),
    );
    const [crx, crz] = PUZZLE_SPOTS.motoCrowbar;
    addPropAt(
      "interact_shop_crowbar",
      crx,
      0.48,
      crz,
      0.4,
      (root) => this.models.buildMotoCrowbar(root),
      !flags.get("ep1.pickup.interact_shop_crowbar", false),
    );

    // -------------------------------------------------------- 2. Brick Village Well Mechanism
    const [wx, wz] = PUZZLE_SPOTS.well;
    this.wellPos = new Vector3(wx, this.groundAt(wx, wz), wz);
    addPropAt("interact_village_well", wx, this.wellPos.y, wz, 0, (root) => {
      this.wellRig = this.models.buildWellRig(root);
    });

    const [wwx, wwz] = PUZZLE_SPOTS.wellWeight;
    addPropAt(
      "interact_well_weight",
      wwx,
      this.groundAt(wwx, wwz),
      wwz,
      0.6,
      (root) => this.models.buildWellWeight(root),
      !flags.get("ep1.pickup.interact_well_weight", false),
    );

    // Servants' hut plank floor verified via Blender raycast at Y = 1.205
    const [whx, whz] = PUZZLE_SPOTS.wellHook;
    addPropAt(
      "interact_well_hook",
      whx,
      1.205,
      whz,
      0.3,
      (root) => this.models.buildWellHook(root),
      !flags.get("ep1.pickup.interact_well_hook", false),
    );

    // -------------------------------------------------------- 3. Torn Betel Half & 3 Ward Stations
    const [tdx, tdz] = PUZZLE_SPOTS.tornDrawing;
    addPropAt(
      "interact_torn_drawing",
      tdx,
      1.205,
      tdz,
      -0.25,
      (root) => this.models.buildTornDrawing(root),
      !flags.get("ep1.pickup.interact_torn_drawing", false),
    );

    // Kitchen house wooden plank floor verified via Blender raycast at Y = 2.505
    const [stx, stz] = PUZZLE_SPOTS.sacredThread;
    addPropAt(
      "interact_sacred_thread_pickup",
      stx,
      2.505,
      stz,
      0.2,
      (root) => this.models.buildSacredThread(root),
      !flags.get("ep1.pickup.interact_sacred_thread_pickup", false),
    );

    const [mgx, mgz] = PUZZLE_SPOTS.wardMarigold;
    addPropAt(
      "interact_ward_marigold_pickup",
      mgx,
      this.groundAt(mgx, mgz) + 0.01,
      mgz,
      0,
      (root) => this.models.buildMarigoldDish(root),
      !flags.get("ep1.pickup.interact_ward_marigold_pickup", false),
    );

    for (const st of WARD_STATIONS) {
      const [sx, sz] = st.position;
      // Stupas terrace apron is elevated masonry at Y = 0.50; Neak Ta & Ruin sit on compound ground
      const sy = st.id === "stupas" ? 0.5 : this.groundAt(sx, sz);
      addPropAt(`interact_ward_${st.id}`, sx, sy, sz, 0, (root) => {
        const handles = this.models.buildWardStation(root, st.id, new Vector3(sx, sy, sz));
        const lit = flags.get(`ep1.puzzle.ward.${st.id}`, false);
        handles.flameMesh.setEnabled(lit);
        handles.solvedGroup.setEnabled(lit);
        this.stationVisuals.set(st.id, handles);
      });
    }

    // -------------------------------------------------------- 4. Stopped 20:12 Hall Pendulum Clock
    // Mounted flush on parlour wainscoting wall (X = -3.00), facing -X into the parlour room
    const [cx, cz] = PUZZLE_SPOTS.hallClock;
    this.clockPos = new Vector3(cx, 4.12, cz);
    addPropAt("interact_hall_clock", cx, 4.12, cz, -Math.PI / 2, (root) => {
      const handles = this.models.buildHallPendulumClock(root);
      this.clockHourHand = handles.hourHand;
      this.clockMinuteHand = handles.minuteHand;
      this.clockPendulumPivot = handles.pendulumPivot;
      const solvedClock = flags.get("ep1.puzzle.clock.solved", false);
      this.setClockHandPose(solvedClock ? 1 : 20, 12);
      this.clockPendulumPivot.setEnabled(flags.get("ep1.puzzle.clock.pendulumFitted", false));
    });
  }

  private setClockHandPose(hour: number, minute: number): void {
    // Facing the +Z clock front in Babylon's left-handed frame, positive Z rotation sweeps clockwise
    const hAngle = (((hour % 12) + minute / 60) / 12) * Math.PI * 2;
    const mAngle = (minute / 60) * Math.PI * 2;
    if (this.clockHourHand) this.clockHourHand.rotation.z = hAngle;
    if (this.clockMinuteHand) this.clockMinuteHand.rotation.z = mAngle;
  }

  private addStaticCollider(
    name: string,
    center: Vector3,
    size: Vector3,
  ): { node: TransformNode; body: PhysicsBody } {
    const node = new TransformNode(name, this.game.scene);
    node.position.copyFrom(center);
    const body = new PhysicsBody(node, PhysicsMotionType.STATIC, false, this.game.scene);
    body.shape = new PhysicsShapeBox(Vector3.Zero(), Quaternion.Identity(), size, this.game.scene);
    const rec = { node, body };
    this.colliders.push(rec);
    return rec;
  }

  private removeCollider(rec: { node: TransformNode; body: PhysicsBody } | null): void {
    if (!rec) return;
    rec.body.shape?.dispose();
    rec.body.dispose();
    rec.node.dispose();
  }

  private enterModal(open: (done: () => void) => void): void {
    const g = this.game;
    g.cutscene = true;
    g.gated.holdStill = true;
    g.gated.holdLook = true;
    g.satchel.close();
    g.sketchbook?.close();
    if (document.pointerLockElement) document.exitPointerLock();
    open(() => {
      g.cutscene = false;
      g.gated.holdStill = false;
      g.gated.holdLook = false;
    });
  }

  private use(id: string): void {
    const g = this.game;
    if (g.cutscene || g.threatActive || g.hiding || this.ui.isOpen) return;

    // ---- Puzzle 1: Roadside Shops & Sealed Compound Gate
    if (id === "interact_shop_noodle_clue") {
      g.flags.set("ep1.clue.noodleCalendar", true);
      this.villageAudio?.play("shrinePlace", g.camera.globalPosition, 0.5);
      void g.subtitles.say(
        "Sora",
        "A red betel ring circles the 7th night of mourning on the noodle stall calendar.",
        5,
      );
      void this.saveProgress();
      return;
    }

    if (id === "interact_shop_barber_radio") {
      const wasOff = g.flags.get("ep1.puzzle.barberRadioOff", false);
      if (!wasOff) {
        g.flags.set("ep1.puzzle.barberRadioOff", true);
        g.flags.set("ep1.clue.barberKnocks", true);
        this.barberRadioSound?.stop();
        if (this.barberRadioRig) {
          this.barberRadioRig.dialLight.intensity = 0;
          this.barberRadioRig.dialMat.emissiveColor.set(0.05, 0.04, 0.03);
        }
        this.villageAudio?.play("lockClick", this.barberRadioPos, 0.9);
        this.villageAudio?.triggerVacuum(4.8, 0.14);
        this.radioKnocksLeft = 4;
        this.radioKnocksPaused = 1;
        this.radioKnockTimer = 0.75;
        this.callbacks.onBarberRadioSilenced?.(this.barberRadioPos);
        void g.subtitles.say(
          "Sora",
          "The static stopped… listen—someone is knocking from inside the barber shop. Four times.",
          5.5,
        );
        void this.saveProgress();
      } else {
        this.radioKnocksLeft = 4;
        this.radioKnocksPaused = 0;
        this.radioKnockTimer = 0.4;
        void g.subtitles.say("Sora", "Four slow knocks echoing inside the barber shop…", 3.5);
      }
      return;
    }

    if (id === "interact_shop_moto_ledger") {
      g.flags.set("ep1.clue.motoLedger", true);
      this.villageAudio?.play("shrinePlace", g.camera.globalPosition, 0.5);
      void g.subtitles.say(
        "Sora",
        "Uncle Sok’s kerosene account: Lot 2. Under it, three marks: Calendar · Knocks · Lot. And a line: “Vigil begins one hour past midnight.”",
        6.5,
      );
      void this.saveProgress();
      return;
    }

    if (id === "interact_shop_crowbar") {
      g.flags.set("ep1.pickup.interact_shop_crowbar", true);
      g.inventory.add("iron_crowbar");
      this.hidePickup(id);
      this.villageAudio?.play("lockOpen", g.camera.globalPosition, 0.65);
      void g.subtitles.say(
        "Sora",
        "A rusted iron pry-bar. Heavy enough to force old fence boards.",
        4,
      );
      void this.saveProgress();
      return;
    }

    if (id === "interact_side_fence_ward") {
      if (!g.inventory.has("iron_crowbar")) {
        void g.subtitles.say(
          "Sora",
          "Loose planks bound with a red spirit cord. I’d need an iron bar to pry it—though breaking a ward feels wrong.",
          5,
        );
        return;
      }
      g.flags.set("ep1.puzzle.sideFence.open", true);
      g.flags.set("ep1.puzzle.gate.open", true);
      g.flags.set("ep1.puzzle.wardSnapped", true);
      this.removeCollider(this.sideFenceCollider);
      this.sideFenceCollider = null;
      this.removeCollider(this.gateCollider);
      this.gateCollider = null;
      this.sidePlankNode?.setEnabled(false);
      this.gateBarNode?.setEnabled(false);
      g.interaction.remove("interact_side_fence_ward");
      g.interaction.remove("interact_village_gate_lock");
      const at = new Vector3(
        PUZZLE_SPOTS.sideFence[0],
        g.player.feet.y + 1,
        PUZZLE_SPOTS.sideFence[1],
      );
      this.villageAudio?.play("preayNeckCrack", at, 1.0, 0.88);
      this.villageAudio?.play("gateOpen", at, 0.9);
      const insideZ = PUZZLE_SPOTS.sideFence[1] - 1.5;
      g.player.teleport(
        new Vector3(
          PUZZLE_SPOTS.sideFence[0],
          this.groundAt(PUZZLE_SPOTS.sideFence[0], insideZ),
          insideZ,
        ),
        Math.PI,
      );
      this.callbacks.onFenceWardSnapped?.(at);
      this.callbacks.onMilestoneClock?.("23:45", "Compound Grounds");
      void g.subtitles.say("Sora", "The red cord snapped… the whole yard just went cold.", 4.5);
      void this.saveProgress();
      return;
    }

    if (id === "interact_village_gate_lock") {
      const clueItems = [
        {
          shop: "Noodle Stall",
          found: g.flags.get("ep1.clue.noodleCalendar", false),
          text: "Calendar circled: 7",
        },
        {
          shop: "Barber Shop",
          found: g.flags.get("ep1.clue.barberKnocks", false),
          text: "Behind shutter: 4 knocks",
        },
        {
          shop: "Moto Shop",
          found: g.flags.get("ep1.clue.motoLedger", false),
          text: "Lot 2 (Calendar · Knocks · Lot)",
        },
      ];
      this.enterModal((done) => {
        this.ui.openGatePadlock({
          initial: this.gateDigits,
          clueItems,
          onTick: () => this.villageAudio?.play("lockClick", g.camera.globalPosition, 0.8),
          onTry: (digits) => {
            this.gateDigits = [...digits] as [number, number, number];
            const res = checkGateCode(digits);
            if (!res.solved) {
              this.villageAudio?.play("woodCreak", g.camera.globalPosition, 0.65);
              return {
                ok: false,
                message:
                  res.matchedCount > 0
                    ? `The shackle jams—${res.matchedCount} of 3 tumblers caught cleanly.`
                    : "The rusted brass shackle refuses to budge.",
              };
            }
            g.flags.set("ep1.puzzle.gate.open", true);
            this.removeCollider(this.gateCollider);
            this.gateCollider = null;
            this.gateBarNode?.setEnabled(false);
            g.interaction.remove("interact_village_gate_lock");
            const at = new Vector3(PUZZLE_SPOTS.gate[0], g.player.feet.y + 1, PUZZLE_SPOTS.gate[1]);
            this.villageAudio?.play("lockOpen", at, 1.0);
            this.villageAudio?.play("gateOpen", at, 0.95);
            this.callbacks.onMilestoneClock?.("23:45", "The Farmstead");
            void g.subtitles.say("Sora", "It opened. The family compound is just ahead.", 4);
            void this.saveProgress();
            return { ok: true, message: "Unlocked." };
          },
          onClose: done,
        });
      });
      return;
    }

    // ---- Puzzle 2: Brick Village Well Mechanism
    if (id === "interact_well_weight") {
      g.flags.set("ep1.pickup.interact_well_weight", true);
      g.inventory.add("well_weight");
      this.hidePickup(id);
      this.villageAudio?.play("shrinePlace", g.camera.globalPosition, 0.85, 0.78);
      void g.subtitles.say(
        "Sora",
        "A lashed laterite counterweight stone—heavy enough for the well sweep.",
        4.5,
      );
      void this.saveProgress();
      return;
    }

    if (id === "interact_well_hook") {
      g.flags.set("ep1.pickup.interact_well_hook", true);
      g.inventory.add("well_hook");
      this.hidePickup(id);
      this.villageAudio?.play("lockOpen", g.camera.globalPosition, 0.65);
      void g.subtitles.say("Sora", "An iron grapple hook and coiled hemp rope.", 4);
      void this.saveProgress();
      return;
    }

    if (id === "interact_village_well") {
      if (this.well.phase === "complete") {
        void g.subtitles.say("Sora", "Nothing left in the bucket but black water and wet hair.", 4);
        return;
      }
      if (this.well.phase === "broken") {
        const res = this.well.attachParts(
          g.inventory.has("well_weight"),
          g.inventory.has("well_hook"),
        );
        if (this.well.hasWeight && g.inventory.has("well_weight")) {
          g.inventory.remove("well_weight");
          g.flags.set("ep1.puzzle.well.weightAttached", true);
        }
        if (this.well.hasHook && g.inventory.has("well_hook")) {
          g.inventory.remove("well_hook");
          g.flags.set("ep1.puzzle.well.hookAttached", true);
        }
        if (res === "rigged") {
          this.villageAudio?.play("wellCreak", this.wellPos, 0.9);
          void g.subtitles.say(
            "Sora",
            "The stone counterweight and iron hook are lashed tight. Now I can haul up whatever sank down there.",
            5,
          );
          void this.saveProgress();
        } else if (res === "need_weight") {
          void g.subtitles.say(
            "Sora",
            "The hook is rigged, but the bamboo pole needs a counterweight stone—check near the buffalo byre.",
            5,
          );
        } else if (res === "need_hook") {
          void g.subtitles.say(
            "Sora",
            "The counterweight is tied, but the bucket line has no hook. Maybe inside the servants’ hut past the kitchen fence.",
            5,
          );
        } else {
          void g.subtitles.say(
            "Sora",
            "The well sweep is stripped—missing both its counterweight stone (by the byre) and its iron bucket hook (servants’ hut).",
            5.5,
          );
        }
        return;
      }

      const lampOpen = this.vigil.lamp.state === "open";
      const pullRes = this.well.pull(lampOpen);
      if (pullRes === "rising") {
        this.villageAudio?.play("wellCreak", this.wellPos, 0.9);
        this.villageAudio?.play("wellSplash", this.wellPos, 0.8);
        void g.subtitles.say(
          "Sora",
          "Heavy… something brass clinked inside the bucket. Pull again.",
          4,
        );
      } else if (pullRes === "tug_started") {
        this.wellTugInitial = this.well.tugRemaining;
        this.villageAudio?.triggerVacuum(4.8, 0.1);
        this.villageAudio?.play("wellTug", this.wellPos, 1.0);
        this.callbacks.onWellTugStart?.(this.wellPos);
        void g.subtitles.say(
          "Sora",
          "Wait—something down the shaft just grabbed the rope! Put out the lamp (F) and hold still until it lets go!",
          5,
        );
      } else if (pullRes === "yanked_back") {
        this.wellTugInitial = Math.max(3.2, this.well.tugRemaining);
        this.villageAudio?.play("wellTug", this.wellPos, 1.1, 0.86);
        this.villageAudio?.play("shockHit", this.wellPos, 0.9);
        this.villageAudio?.play("soraGasp", g.camera.globalPosition, 0.9);
        this.game.atmosphere.scare();
        this.callbacks.onWellTugFailed?.(this.wellPos);
        void g.subtitles.say(
          "Sora",
          "It yanked the bucket right back down! Douse the lamp (F) and wait still when it grabs!",
          5,
        );
      } else if (pullRes === "hauled") {
        g.flags.set("ep1.puzzle.well.complete", true);
        g.inventory.add("clock_pendulum");
        g.inventory.add("well_water");
        this.villageAudio?.play("wellSplash", this.wellPos, 0.95);
        this.villageAudio?.play("lockOpen", this.wellPos, 0.7);
        this.callbacks.onMilestoneClock?.("00:00", "Midnight Watch");
        void g.subtitles.say(
          "Sora",
          "Long wet hair tangled around… Uncle Sok’s brass clock pendulum! And a clay bowl of cold well water.",
          6,
        );
        void this.saveProgress();
      }
      return;
    }

    // ---- Puzzle 3: Torn Betel Half & Ward Offerings / Stations
    if (id === "interact_torn_drawing") {
      g.flags.set("ep1.pickup.interact_torn_drawing", true);
      g.flags.set("ep1.betel.tornHalfFound", true);
      g.inventory.add("torn_drawing_half");
      this.hidePickup(id);
      this.villageAudio?.play("shrinePlace", g.camera.globalPosition, 0.6);
      void g.subtitles.say(
        "Sora",
        "The torn half of Mother’s betel diagram! Right: areca nuts. Front: incense. Now I have the whole tray layout.",
        6,
      );
      void this.saveProgress();
      return;
    }

    if (id === "interact_sacred_thread_pickup") {
      g.flags.set("ep1.pickup.interact_sacred_thread_pickup", true);
      g.inventory.add("sacred_thread");
      this.hidePickup(id);
      this.villageAudio?.play("shrinePlace", g.camera.globalPosition, 0.55);
      void g.subtitles.say("Sora", "Undyed white cotton thread for the ancestral stupas.", 4);
      void this.saveProgress();
      return;
    }

    if (id === "interact_ward_marigold_pickup") {
      g.flags.set("ep1.pickup.interact_ward_marigold_pickup", true);
      g.inventory.add("ward_marigold");
      this.hidePickup(id);
      this.villageAudio?.play("shrinePlace", g.camera.globalPosition, 0.55);
      void g.subtitles.say("Sora", "Fresh marigolds on a brass phan dish.", 3.5);
      void this.saveProgress();
      return;
    }

    if (id.startsWith("interact_ward_")) {
      const stationId = id.replace("interact_ward_", "") as WardStationId;
      if (g.flags.get(`ep1.puzzle.ward.${stationId}`, false)) {
        void g.subtitles.say("Sora", "This offering is already burning steady.", 3.5);
        return;
      }
      const spec = WARD_STATIONS.find((s) => s.id === stationId);
      if (!spec) return;
      const available = (
        ["well_water", "sacred_thread", "ward_marigold"] as WardOfferingId[]
      ).filter((item) => g.inventory.has(item));
      const stPos = new Vector3(
        spec.position[0],
        spec.id === "stupas" ? 0.5 : this.groundAt(spec.position[0], spec.position[1]),
        spec.position[1],
      );

      this.enterModal((done) => {
        this.ui.openWardStation({
          stationId,
          availableOfferings: available,
          solvedCount: solvedWardCount(g.flags),
          onSelectSound: () => this.villageAudio?.play("lockClick", g.camera.globalPosition, 0.55),
          onCommit: (offering, incense) => {
            const verdict = checkWardStation(stationId, offering, incense);
            if (verdict !== "correct") {
              this.villageAudio?.play("preayRattle", stPos, 0.95);
              this.villageAudio?.play("shockHit", stPos, 0.85);
              this.callbacks.onWardMistake?.(stPos, stationId);
              const msg =
                verdict === "wrong_incense"
                  ? "The sticks snap black—wrong number of incense! Something answered from the trees!"
                  : "The offering turns sour at once. That did not belong here.";
              void g.subtitles.say("Sora", msg, 5);
              return { ok: false, closeAfter: true, message: msg };
            }
            g.inventory.remove(offering);
            g.flags.set(`ep1.puzzle.ward.${stationId}`, true);
            this.villageAudio?.play("shrinePlace", stPos, 0.9);
            const total = solvedWardCount(g.flags);
            if (total >= WARD_STATIONS.length) {
              g.flags.set("ep1.clue.stupaTime", true);
              this.villageAudio?.play("clockChime", stPos, 0.72);
              this.callbacks.onMilestoneClock?.("00:30", "The Three Wards");
              void g.subtitles.say(
                "Sora",
                "All three wards hold! Beneath the ashes is carved: “One past midnight, twelve beats after the bell.” 01:12…",
                6.5,
              );
            } else {
              void g.subtitles.say(
                "Sora",
                `The smoke rises straight. (${total} of ${WARD_STATIONS.length} compound wards restored.)`,
                4.5,
              );
            }
            void this.saveProgress();
            return { ok: true, message: "The offering holds." };
          },
          onClose: done,
        });
      });
      return;
    }

    // ---- Puzzle 4: Stopped 20:12 Hall Pendulum Clock
    if (id === "interact_hall_clock") {
      if (g.flags.get("ep1.puzzle.clock.solved", false)) {
        void g.subtitles.say("Sora", "The hall clock ticks steadily past 01:12.", 3.5);
        return;
      }
      if (!g.flags.get("ep1.puzzle.clock.pendulumFitted", false)) {
        if (!g.inventory.has("clock_pendulum")) {
          void g.subtitles.say(
            "Sora",
            "Stopped dead at 20:12—just like Phnom Penh and the taxi. Its brass pendulum is missing; check the brick village well.",
            5.5,
          );
          return;
        }
        g.inventory.remove("clock_pendulum");
        g.flags.set("ep1.puzzle.clock.pendulumFitted", true);
        this.villageAudio?.play("lockOpen", this.clockPos, 0.8);
        this.villageAudio?.play("clockTick", this.clockPos, 0.8);
        void g.subtitles.say(
          "Sora",
          "The brass pendulum catches and begins to swing. Now I need to set the hands to the vigil hour.",
          5,
        );
        void this.saveProgress();
        return;
      }

      const clues = [
        g.flags.get("ep1.clue.motoLedger", false)
          ? "Moto ledger: “Vigil begins one hour past midnight.”"
          : null,
        g.flags.get("ep1.clue.stupaTime", false)
          ? "Stupa ward carving: “One past midnight, twelve beats after the bell.”"
          : null,
        "Studio & taxi clocks both stopped at twelve minutes past the hour (20:12).",
      ].filter((v): v is string => v !== null);

      this.enterModal((done) => {
        this.ui.openHallClock({
          initialHour: 20,
          initialMinute: 12,
          clues,
          onTick: (h, m) => {
            this.setClockHandPose(h, m);
            this.villageAudio?.play("clockTick", this.clockPos, 0.75);
          },
          onConfirm: (hour, minute) => {
            this.setClockHandPose(hour, minute);
            const verdict = checkClockDial(hour, minute);
            if (verdict === "cursed") {
              this.villageAudio?.play("clockChimeLow", this.clockPos, 1.0);
              this.villageAudio?.play("shockHit", this.clockPos, 0.95);
              this.callbacks.onClockCursed?.(this.clockPos);
              void g.subtitles.say(
                "Sora",
                "It struck thirteen times—something is in the hall!",
                4.5,
              );
              return {
                ok: false,
                closeAfter: true,
                message: "Thirteen chimes echo through the dark.",
              };
            }
            if (verdict === "wrong") {
              this.villageAudio?.play("woodCreak", this.clockPos, 0.75);
              return {
                ok: false,
                message: "The gears rattle and slip. That is not the vigil hour.",
              };
            }
            g.flags.set("ep1.puzzle.clock.solved", true);
            this.villageAudio?.play("clockChime", this.clockPos, 0.9);
            this.villageAudio?.play("lockOpen", this.clockPos, 0.85);
            this.callbacks.onMilestoneClock?.("01:00", "The First Watch");
            void g.subtitles.say(
              "Sora",
              "The base compartment sprang open—and the air downstairs shifted. I should return to the coffin.",
              5.5,
            );
            void this.saveProgress();
            return { ok: true, message: "The brass latch clicks open." };
          },
          onClose: done,
        });
      });
    }
  }

  private hidePickup(id: string): void {
    this.game.interaction.remove(id);
    const node = this.nodes.find((n) => n.name === id);
    node?.setEnabled(false);
  }

  dispose(): void {
    this.ui.dispose();
    this.barberRadioSound?.stop();
    this.shopBuzzSound?.stop();
    this.barberRadioRig?.dialLight.dispose();
    for (const c of this.colliders) this.removeCollider(c);
    for (const entry of this.stationVisuals.values()) entry.light.dispose();
    for (const n of this.nodes) n.dispose();
    this.models.dispose();
  }
}
