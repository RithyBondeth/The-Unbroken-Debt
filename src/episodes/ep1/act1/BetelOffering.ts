import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateDisc } from "@babylonjs/core/Meshes/Builders/discBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import type { LevelMarker } from "../../../core/LevelBuilder";
import { seededRandom } from "../../../audio/synth";
import type { StringKey } from "../../../ui/html/StoryUi";
import { clockStop, pickUp } from "../audio/prologueSounds";
import {
  BETEL_ENTRIES,
  BETEL_LINES,
  checkTray,
  JUDGE_DELAY,
  KANHA_LAYOUT,
  nextOffering,
  OFFERINGS,
  SLOT_OFFSETS,
  SLOTS,
  type Offering,
  type Slot,
  type Tray,
} from "../data/betel";
import type { Line } from "../data/prologue";
import type { OfferingModels } from "./OfferingModels";

/** Surface of the turned lacquer tray, from OfferingModels.tray. */
const trayTop = (r: number) => 0.018 + 0.014 * Math.min(1, r / 0.2) ** 5 + 0.001;
/** The leaves turn black once the tray has been left unwatched this long after completion (s). */
const BLACKEN_AFTER = 90;
const BLACKEN_UNSEEN = 20;

/** Sora follows Kanha’s drawing after Mak Yey’s phone instructions.
 * The prepared blessed matches are a separate, persistent pickup at the altar.
 */
export class BetelOffering {
  private readonly tray: Tray = {};
  /** The pickup each offering is copied from to sit on the tray. */
  private readonly sources = new Map<Offering | "betel_tray", TransformNode>();
  private readonly slotDiscs = new Map<Slot, Mesh>();
  private readonly shown = new Map<Slot, TransformNode>();
  private readonly toWrite: string[] = [];
  private readonly sfx = new Map<string, StaticSound>();
  private readonly ring: DynamicTexture;
  private readonly trayAt: Vector3 | null;
  private asked = false;
  private placed = false;
  private done = false;
  private mistakes = 0;
  private judgeAt = -1;
  private completedAt = -1;
  private unseen = 0;
  private leavesBlack = false;
  private leavesNoticed = false;
  private time = 0;

  constructor(
    private readonly game: Game,
    private readonly area: Area,
    private readonly models: OfferingModels,
  ) {
    const level = area.level;
    this.ring = new DynamicTexture("T_offering_focus_ring", 128, game.scene, true);
    const ctx = this.ring.getContext();
    ctx.clearRect(0, 0, 128, 128);
    ctx.strokeStyle = "#d5bea1";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(64, 64, 59, 0, Math.PI * 2);
    ctx.stroke();
    this.ring.hasAlpha = true;
    this.ring.update();
    this.trayAt = level.markers.get("betel_tray")?.position.clone() ?? null;
    for (const m of level.interactables) {
      const item = m.extras.item as Offering | "betel_tray" | undefined;
      if (
        m.extras.action === "pickup" &&
        item &&
        (item === "betel_tray" || OFFERINGS.includes(item))
      )
        if (!this.sources.has(item)) this.sources.set(item, m.node);
    }
    game.bus.on("interact:use", ({ id }) => this.use(id));
    this.asked = game.flags.get("ep1.betel.asked", false);
    this.mistakes = game.flags.get("ep1.betel.mistakes", 0);
    // Restore consumed offerings as well as the empty stand after any Act I autosave.
    if (game.flags.get("ep1.betel.trayPlaced", false) && !game.flags.get("ep1.betel.done", false)) {
      this.placeTray(true);
      for (const slot of SLOTS) {
        const offering = game.flags.get(`ep1.betel.slot.${slot}`, "");
        if (OFFERINGS.includes(offering as Offering)) {
          this.tray[slot] = offering as Offering;
          this.show(slot, offering as Offering);
        }
      }
      if (checkTray(this.tray).complete) this.judgeAt = JUDGE_DELAY;
    }
    // CP2 resumes with a completed offering.
    if (game.flags.get("ep1.betel.done", false)) {
      this.placeTray(true);
      for (const slot of SLOTS) {
        this.tray[slot] = KANHA_LAYOUT[slot];
        this.show(slot, KANHA_LAYOUT[slot]);
      }
      this.done = true;
      this.finishTray();
      this.completedAt = 0;
      if (game.flags.get("ep1.betel.blackened", false)) this.blackenLeaves();
    }
  }

  get pendingEntries(): readonly string[] {
    return this.toWrite;
  }

  saveState(): void {
    for (const slot of SLOTS) this.game.flags.set(`ep1.betel.slot.${slot}`, this.tray[slot] ?? "");
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const make = async (name: string, samples: Float32Array) =>
      this.sfx.set(
        name,
        await audio.spatialSound(name, audio.buffer(samples, rate), "sfx", Vector3.Zero(), {
          minDistance: 2,
        }),
      );
    await make("pickup", pickUp(rate, seededRandom(81)));
    await make("knock", clockStop(rate, seededRandom(82)));
  }

  update(dt: number): void {
    this.time += dt;
    const game = this.game;
    const eye = game.camera.globalPosition;
    for (const [slot, disc] of this.slotDiscs) {
      if (disc.material) disc.material.alpha = game.interaction.focus === slotId(slot) ? 0.5 : 0;
    }
    // One entry at a time: the book turns to each and Sora's hand writes it in.
    const book = game.sketchbook;
    if (this.toWrite.length && book && !book.isBusy && !game.cutscene) {
      const id = this.toWrite.shift() as string;
      if (!book.written.has(id)) book.write(id);
    }
    if (this.judgeAt >= 0 && this.time >= this.judgeAt) {
      this.judgeAt = -1;
      this.judge();
    }
    if (this.done) this.watchLeaves(dt, eye);
  }

  // ------------------------------------------------------------ the beats

  /** A1-05 and A1-06: the duties and the offering, as Yay Mey gives them. */
  async ask(repeat = false): Promise<void> {
    if (this.asked && !repeat) return;
    this.asked = true;
    this.game.flags.set("ep1.betel.asked", true);
    this.toWrite.push(BETEL_ENTRIES.duties, BETEL_ENTRIES.request);
    await this.say(BETEL_LINES.request);
  }

  private use(id: string): void {
    const game = this.game;
    const slot = SLOTS.find((s) => id === slotId(s));
    if (slot) return this.cycle(slot);
    const marker = this.marker(id);
    if (!marker) return;
    const action = marker.extras.action;
    const item = typeof marker.extras.item === "string" ? marker.extras.item : "";
    if (
      action === "pickup" &&
      (item === "betel_tray" || (item !== "incense" && OFFERINGS.includes(item as Offering)))
    ) {
      // The altar's incense is the vigil's (it can be taken again); everything else is taken once.
      game.inventory.add(item);
      game.flags.set(`ep1.pickup.${id}`, true);
      game.interaction.remove(marker.name);
      marker.node.setEnabled(false);
      this.play("pickup");
      game.hints.show(`note.${item === "betel_tray" ? "tray" : item}` as StringKey, 3);
    } else if (action === "examine" && id === "interact_kanha_drawing") {
      game.hints.show("note.drawing", 4);
      game.flags.set("ep1.betel.drawingSeen", true);
      this.toWrite.push(BETEL_ENTRIES.drawing);
    } else if (action === "place" && id === "interact_altar") {
      if (this.placed) return this.inspectTray();
      if (!this.asked) return game.hints.show("note.yayWaiting", 4);
      if (game.inventory.has("betel_tray")) this.placeTray();
      else if (this.asked && !this.done) game.hints.show("note.needTray", 3);
    } else if (action === "knock" && id === "interact_door_yaymey") {
      this.play("knock", marker.position);
      setTimeout(() => this.play("knock", marker.position), 260);
      game.hints.show(this.done ? "note.letHerRest" : "note.yayResting", 3);
    }
  }

  /** The empty tray goes on the stand before the altar; its five places become usable. */
  private placeTray(restoring = false): void {
    const game = this.game;
    const node = this.sources.get("betel_tray");
    if (!node || !this.trayAt) return;
    if (!restoring) game.inventory.remove("betel_tray");
    node.setEnabled(true);
    sitOn(node, this.trayAt);
    this.placed = true;
    game.flags.set("ep1.betel.trayPlaced", true);
    if (!restoring) this.play("pickup", this.trayAt);
    for (const slot of SLOTS) {
      const disc = CreateDisc(slotId(slot), { radius: 0.04, tessellation: 20 }, game.scene);
      disc.rotation.x = Math.PI / 2;
      disc.position.copyFrom(this.slotPosition(slot, 0.002));
      const mat = new StandardMaterial(`M_${slotId(slot)}`, game.scene);
      // Invisible interaction patches: the lacquer stays a real, unmarked object.
      mat.disableLighting = true;
      mat.diffuseTexture = this.ring;
      mat.useAlphaFromDiffuseTexture = true;
      mat.diffuseColor = Color3.Black();
      mat.emissiveColor = new Color3(0.05, 0.035, 0.025);
      mat.alpha = 0;
      disc.material = mat;
      this.slotDiscs.set(slot, disc);
      game.interaction.add(slotId(slot), [disc], { outline: false });
    }
    if (!restoring) game.hints.show("hint.tray", 8);
    if (!restoring) this.inspectTray();
  }

  private inspectTray(): void {
    if (this.trayAt) this.game.inspectObject(this.trayAt.add(new Vector3(0, 0.035, 0)));
  }

  /** E on a place: the next offering Sora has goes there; after the last, the place is cleared. */
  private cycle(slot: Slot): void {
    const game = this.game;
    if (this.done) return;
    const current = this.tray[slot];
    const next = nextOffering(this.tray, slot, (o) => game.inventory.has(o));
    if (!current && !next) return game.hints.show("note.trayEmpty", 3);
    if (current) game.inventory.add(current);
    if (next) {
      game.inventory.remove(next);
      this.tray[slot] = next;
      game.hints.show(`note.${next}` as StringKey, 2);
    } else delete this.tray[slot];
    this.show(slot, next);
    this.play("pickup", this.slotPosition(slot));
    game.hints.performed("hint.tray");
    this.judgeAt = this.time + JUDGE_DELAY;
  }

  /** Puts a copy of the offering on its place on the tray (or clears it). */
  private show(slot: Slot, offering: Offering | null): void {
    const game = this.game;
    this.shown.get(slot)?.dispose();
    this.shown.delete(slot);
    const disc = this.slotDiscs.get(slot);
    const meshes: Mesh[] = disc ? [disc] : [];
    if (offering) {
      const model = this.models.make(offering);
      model.position.copyFrom(this.slotPosition(slot));
      this.shown.set(slot, model);
      meshes.push(...model.getChildMeshes<Mesh>(false));
      // Fixed flame lights have mesh whitelists built when the area loads.
      // New tray contents need to join the nearby lights, too.
      for (const id of this.area.level.flames.keys()) {
        const light = game.scene.getLightByName(id);
        if (!(light instanceof PointLight)) continue;
        const list = light.includedOnlyMeshes.filter((m) => !m.isDisposed());
        if (Vector3.Distance(light.getAbsolutePosition(), model.position) < light.range + 0.1)
          list.push(...model.getChildMeshes<Mesh>(false));
        light.includedOnlyMeshes = list;
      }
    }
    // The offering is part of its place, so looking at it still focuses the place.
    game.interaction.add(slotId(slot), meshes, { outline: false });
  }

  /** Sora checks a full tray against Kanha’s drawing. */
  private judge(): void {
    const game = this.game;
    const { complete, wrong } = checkTray(this.tray);
    if (!complete) return;
    if (wrong.length) {
      // Each offering out of place is a small mark against respect (section 6.1).
      this.mistakes += wrong.length;
      game.flags.set("ep1.betel.mistakes", this.mistakes);
      void this.say(BETEL_LINES.wrong);
      return;
    }
    void this.completeOffering();
  }

  /** A1-09: offering completed. Flags ep1.betel.done and ep1.betel.firstTry (respect +1). */
  private async completeOffering(): Promise<void> {
    const game = this.game;
    this.done = true;
    this.finishTray();
    game.flags.set("ep1.betel.firstTry", this.mistakes === 0);
    await this.say(BETEL_LINES.right);
    await this.say(BETEL_LINES.preparedMatches);
    game.flags.set("ep1.betel.done", true);
    game.stopInspecting();

    this.completedAt = this.time;
  }

  /**
   * After completion, once the tray has gone unwatched a while, the betel leaves
   * on it are black: the debt does not accept the offering. Sora notices the next
   * time she is close.
   */
  private watchLeaves(dt: number, eye: Vector3): void {
    if (this.completedAt < 0) return;
    const leaves = this.shown.get("left");
    if (!leaves || !this.trayAt) return;
    const inView = leaves.getChildMeshes(false).some((m) => this.game.camera.isInFrustum(m));
    if (!this.leavesBlack) {
      if (this.time - this.completedAt < BLACKEN_AFTER) return;
      this.unseen = inView ? 0 : this.unseen + dt;
      if (this.unseen < BLACKEN_UNSEEN) return;
      this.blackenLeaves();
      this.game.flags.set("ep1.betel.blackened", true);
    } else if (!this.leavesNoticed && inView && Vector3.Distance(eye, this.trayAt) < 3) {
      this.leavesNoticed = true;
      this.game.hints.show("note.leavesBlack", 4);
    }
  }

  // -------------------------------------------------------------- helpers

  private finishTray(): void {
    for (const slot of SLOTS) this.game.interaction.remove(slotId(slot));
    for (const disc of this.slotDiscs.values()) disc.isVisible = false;
    // The completed objects stay inspectable even after their puzzle slots are retired.
    const altar = this.marker("interact_altar")?.node.getChildMeshes<Mesh>(false) ?? [];
    const tray = this.sources.get("betel_tray")?.getChildMeshes<Mesh>(false) ?? [];
    const offerings = [...this.shown.values()].flatMap((node) => node.getChildMeshes<Mesh>(false));
    this.game.interaction.add("interact_altar", [...altar, ...tray, ...offerings], {
      outline: false,
    });
  }

  private blackenLeaves(): void {
    this.leavesBlack = true;
    for (const mesh of this.shown.get("left")?.getChildMeshes(false) ?? []) {
      if (!(mesh.material instanceof PBRMaterial)) continue;
      const black = mesh.material.clone(`${mesh.material.name}_black`);
      black.albedoColor = new Color3(0.03, 0.03, 0.025);
      black.roughness = 0.95;
      mesh.material = black;
    }
  }

  private marker(name: string): LevelMarker | undefined {
    return this.area.level.interactables.find((m) => m.name === name);
  }

  /** A place on the tray, `lift` metres above its surface. */
  private slotPosition(slot: Slot, lift = 0): Vector3 {
    const [dx, dy] = SLOT_OFFSETS[slot];
    // Blender (x east, y north) to Babylon (x west, z south).
    const top = trayTop(Math.hypot(dx, dy));
    return (this.trayAt ?? Vector3.Zero()).add(new Vector3(-dx, top + lift, -dy));
  }

  private say(line: Line): Promise<void> {
    return this.game.subtitles.say(line.speaker, line.text, line.seconds);
  }

  private play(name: string, at = this.game.camera.globalPosition): void {
    const sound = this.sfx.get(name);
    if (!sound) return;
    sound.spatial.position = at.clone();
    sound.play();
  }

  dispose(): void {
    for (const node of this.shown.values()) node.dispose();
    for (const disc of this.slotDiscs.values()) disc.dispose();
  }
}

const slotId = (slot: Slot) => `betel_slot_${slot}`;

/**
 * Moves `node` so the middle of its underside rests on `at`, first scaling it
 * down (never up) so it is no wider than `width` metres.
 */
function sitOn(node: TransformNode, at: Vector3, width = Infinity): void {
  node.computeWorldMatrix(true);
  let { min, max } = node.getHierarchyBoundingVectors(true);
  const across = Math.max(max.x - min.x, max.z - min.z);
  if (across > width) {
    node.scaling.scaleInPlace(width / across);
    node.computeWorldMatrix(true);
    ({ min, max } = node.getHierarchyBoundingVectors(true));
  }
  const base = new Vector3((min.x + max.x) / 2, min.y, (min.z + max.z) / 2);
  node.setAbsolutePosition(node.getAbsolutePosition().add(at.subtract(base)));
}
