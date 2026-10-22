import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateDisc } from "@babylonjs/core/Meshes/Builders/discBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import type { LevelMarker } from "../../../core/LevelBuilder";
import { seededRandom } from "../../../audio/synth";
import type { StringKey } from "../../../ui/html/StoryUi";
import { clockStop, pickUp } from "../audio/prologueSounds";
import {
  BETEL_ENTRIES,
  BETEL_LINES,
  BLESSED_MATCHES,
  checkTray,
  JUDGE_DELAY,
  nextOffering,
  OFFERINGS,
  SLOT_OFFSETS,
  SLOTS,
  type Offering,
  type Slot,
  type Tray,
} from "../data/betel";
import type { Line } from "../data/prologue";

/** Within this distance of the tent (m), Yay Mey asks for the offering, or of the altar. */
const ASK_NEAR_TENT = 8;
const ASK_NEAR_ALTAR = 6;
/** How wide each offering may sit on the tray (m): the leaves and sticks are scaled down to fit. */
const FIT: Record<Exclude<Offering, "incense">, number> = {
  betel: 0.09,
  areca: 0.07,
  lime: 0.09,
  candle: 0.05,
};
/**
 * Height of the tray's top above the stand (m) at `r` from its centre: the
 * lacquered round rises from 4 cm in the middle to 5 cm at its 20 cm rim
 * (tools/areas/ep1_area_village.py, hall_betel_tray).
 */
const trayTop = (r: number) => 0.04 + 0.01 * Math.min(1, r / 0.2) + 0.002;
/** The leaves turn black once the tray has been left unwatched this long after the blessing (s). */
const BLACKEN_AFTER = 90;
const BLACKEN_UNSEEN = 20;

/**
 * The betel offering (Beat Sheet A1-06 to A1-09; Episode 1, section 6.1). Yay Mey
 * asks for it as Sora reaches the funeral (standing in for the arrival scenes,
 * A1-03 to A1-06, until Yay Mey is modelled). Kanha's drawing by the ancestral
 * altar shows the layout; Sora gathers the betel leaves and areca nuts (kitchen),
 * the lime pot (hall shelf), a candle and incense (altar) and the empty tray (by
 * the altar), sets the tray on the stand before the altar and arranges it: E on a
 * place on the tray puts an offering there, E again changes it. Yay Mey answers a
 * full tray from behind her door. When it is right she blesses three matches, the
 * ones the ritual in Act III needs. Later, unwatched, the leaves turn black.
 */
export class BetelOffering {
  private readonly tray: Tray = {};
  /** The pickup each offering is copied from to sit on the tray. */
  private readonly sources = new Map<Offering | "betel_tray", TransformNode>();
  private readonly slotDiscs = new Map<Slot, Mesh>();
  private readonly shown = new Map<Slot, TransformNode>();
  private readonly toWrite: string[] = [];
  private readonly sfx = new Map<string, StaticSound>();
  private readonly trayAt: Vector3 | null;
  private readonly tentAt: Vector3 | null;
  private readonly altarAt: Vector3 | null;
  private asked = false;
  private placed = false;
  private done = false;
  private mistakes = 0;
  private judgeAt = -1;
  private blessedAt = -1;
  private unseen = 0;
  private leavesBlack = false;
  private leavesNoticed = false;
  private time = 0;

  constructor(
    private readonly game: Game,
    private readonly area: Area,
  ) {
    const level = area.level;
    this.trayAt = level.markers.get("betel_tray")?.position.clone() ?? null;
    this.tentAt = level.markers.get("yay_mey")?.position.clone() ?? null;
    this.altarAt = this.marker("interact_altar")?.position.clone() ?? null;
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
    if (
      !this.asked &&
      ((this.tentAt && Vector3.Distance(eye, this.tentAt) < ASK_NEAR_TENT) ||
        (this.altarAt && Vector3.Distance(eye, this.altarAt) < ASK_NEAR_ALTAR))
    )
      this.ask();
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
  private ask(): void {
    this.asked = true;
    this.game.flags.set("ep1.betel.asked", true);
    void this.say(BETEL_LINES.request);
    this.toWrite.push(BETEL_ENTRIES.duties, BETEL_ENTRIES.request);
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
      game.interaction.remove(marker.name);
      marker.node.setEnabled(false);
      this.play("pickup");
      game.hints.show(`note.${item === "betel_tray" ? "tray" : item}` as StringKey, 3);
    } else if (action === "examine" && id === "interact_kanha_drawing") {
      game.hints.show("note.drawing", 4);
      game.flags.set("ep1.betel.drawingSeen", true);
      this.toWrite.push(BETEL_ENTRIES.drawing);
    } else if (action === "place" && id === "interact_altar") {
      if (this.placed) return;
      if (game.inventory.has("betel_tray")) this.placeTray();
      else if (this.asked && !this.done) game.hints.show("note.needTray", 3);
    } else if (action === "knock" && id === "interact_door_yaymey") {
      this.play("knock", marker.position);
      setTimeout(() => this.play("knock", marker.position), 260);
      game.hints.show(this.done ? "note.letHerRest" : "note.yayResting", 3);
    }
  }

  /** The empty tray goes on the stand before the altar; its five places become usable. */
  private placeTray(): void {
    const game = this.game;
    const node = this.sources.get("betel_tray");
    if (!node || !this.trayAt) return;
    game.inventory.remove("betel_tray");
    node.setEnabled(true);
    sitOn(node, this.trayAt);
    this.placed = true;
    game.flags.set("ep1.betel.trayPlaced", true);
    this.play("pickup", this.trayAt);
    for (const slot of SLOTS) {
      const disc = CreateDisc(slotId(slot), { radius: 0.04, tessellation: 20 }, game.scene);
      disc.rotation.x = Math.PI / 2;
      disc.position.copyFrom(this.slotPosition(slot, 0.002));
      const mat = new StandardMaterial(`M_${slotId(slot)}`, game.scene);
      // A worn, darker round in the lacquer: something to aim at.
      mat.disableLighting = true;
      mat.diffuseColor = Color3.Black();
      mat.emissiveColor = new Color3(0.05, 0.035, 0.025);
      mat.alpha = 0.5;
      disc.material = mat;
      this.slotDiscs.set(slot, disc);
      game.interaction.add(slotId(slot), [disc]);
    }
    game.hints.show("hint.tray", 8);
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
    const source = offering ? this.sources.get(offering) : undefined;
    if (offering === "incense" && source) {
      // The altar's bundle is long and thin: shrunk to fit, its sticks vanish. Three
      // sticks of the same incense laid side by side instead.
      const sticks = new TransformNode(`tray_${slot}_incense`, game.scene);
      const material = source.getChildMeshes(false)[0]?.material ?? null;
      for (let k = -1; k <= 1; k++) {
        const stick = CreateCylinder(
          `tray_${slot}_incense_${k}`,
          { height: 0.15, diameter: 0.005, tessellation: 6 },
          game.scene,
        );
        stick.rotation.z = Math.PI / 2;
        stick.position.set(0, 0.0025, k * 0.008);
        stick.material = material;
        stick.parent = sticks;
        meshes.push(stick);
      }
      sticks.position.copyFrom(this.slotPosition(slot));
      this.shown.set(slot, sticks);
    } else if (offering && offering !== "incense" && source) {
      const copy = source.clone(`tray_${slot}_${offering}`, source.parent) as TransformNode;
      copy.setEnabled(true);
      sitOn(copy, this.slotPosition(slot), FIT[offering]);
      this.shown.set(slot, copy);
      meshes.push(...copy.getChildMeshes<Mesh>(false));
    }
    // The offering is part of its place, so looking at it still focuses the place.
    game.interaction.add(slotId(slot), meshes);
  }

  /** Yay Mey answers a full tray from behind her door. */
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
    void this.bless();
  }

  /** A1-09: the matches blessed. Flags ep1.betel.done and ep1.betel.firstTry (respect +1). */
  private async bless(): Promise<void> {
    const game = this.game;
    this.done = true;
    for (const slot of SLOTS) game.interaction.remove(slotId(slot));
    for (const disc of this.slotDiscs.values()) disc.isVisible = false;
    game.flags.set("ep1.betel.firstTry", this.mistakes === 0);
    game.flags.set("ep1.betel.done", true);
    await this.say(BETEL_LINES.right);
    await this.say(BETEL_LINES.blessing);
    game.inventory.add("blessed_matches", BLESSED_MATCHES);
    game.hints.show("note.blessed", 4);
    this.blessedAt = this.time;
  }

  /**
   * After the blessing, once the tray has gone unwatched a while, the betel leaves
   * on it are black: the debt does not accept the offering. Sora notices the next
   * time she is close.
   */
  private watchLeaves(dt: number, eye: Vector3): void {
    const leaves = this.shown.get("left");
    if (!leaves || !this.trayAt) return;
    const inView = leaves.getChildMeshes(false).some((m) => this.game.camera.isInFrustum(m));
    if (!this.leavesBlack) {
      if (this.time - this.blessedAt < BLACKEN_AFTER) return;
      this.unseen = inView ? 0 : this.unseen + dt;
      if (this.unseen < BLACKEN_UNSEEN) return;
      this.leavesBlack = true;
      for (const mesh of leaves.getChildMeshes(false)) {
        if (!(mesh.material instanceof PBRMaterial)) continue;
        const black = mesh.material.clone(`${mesh.material.name}_black`);
        black.albedoColor = new Color3(0.03, 0.03, 0.025);
        black.roughness = 0.95;
        mesh.material = black;
      }
      this.game.flags.set("ep1.betel.blackened", true);
    } else if (!this.leavesNoticed && inView && Vector3.Distance(eye, this.trayAt) < 3) {
      this.leavesNoticed = true;
      this.game.hints.show("note.leavesBlack", 4);
    }
  }

  // -------------------------------------------------------------- helpers

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
