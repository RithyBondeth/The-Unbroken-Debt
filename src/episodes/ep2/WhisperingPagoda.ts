import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Game } from "../../core/Game";
import { loadArea, type Area } from "../../core/AreaLoader";
import type { SaveData } from "../../systems/saves/SaveData";
import { encodeSaveCode } from "../../systems/saves/saveCode";
import { ResolutionView } from "../ep1/resolution/ResolutionView";
import { ShadowFigure } from "../ep1/entities/ShadowFigure";
import { EP1_GRADE } from "../ep1/data/grade";
import { PagodaLights } from "./PagodaLights";
import { PagodaEquipment } from "./PagodaEquipment";
import { PagodaSoundscape } from "./PagodaSoundscape";
import { PagodaApparition } from "./PagodaApparition";
import { buildFarForest } from "./PagodaFarForest";
import { PagodaCinematics } from "./cinematics/PagodaCinematics";
import { CheaHands } from "./cinematics/CheaHands";
import { COLLAPSE_KEEP } from "./cinematics/LibraryCollapse";
import { PAGODA_BALANCE as B, EscapeClock, inKuti, simulationStep } from "./data/balance";
import { PagodaGate } from "./PagodaGate";
import { PagodaProgress } from "./PagodaProgress";
import { PretBrain, Breath } from "./PretBrain";
import {
  ANCESTORS,
  ENTRY,
  KUTI,
  LIBRARY,
  DAWN,
  MEMORY,
  BOUNDS,
  PATROLS,
  MIRROR_TARGETS,
  NOTES,
  type NoteId,
  type Offering,
  type Point,
} from "./data/pagoda";

/** The complete pagoda story loop; same engine, controller, equipment and paper UI as Episode 1. */
export class WhisperingPagoda {
  area!: Area;
  lights!: PagodaLights;
  private apparition!: PagodaApparition;
  equipment!: PagodaEquipment;
  private gate!: PagodaGate;
  readonly progress: PagodaProgress;
  readonly view = new ResolutionView("Episode 2 · The Whispering Pagoda");
  readonly ghosts = PATROLS.map((p, i) => new PretBrain(p, i));
  readonly breath = new Breath();
  readonly sounds: PagodaSoundscape;
  readonly cinematics: PagodaCinematics;
  readonly cheaHands: CheaHands;
  readonly escapeClock = new EscapeClock();
  private contactGrace: number = B.loadGrace;
  private readonly actors: TransformNode[] = [];
  private readonly beams: Mesh[] = [];
  private readonly tendrils: Mesh[] = [];
  private guardian!: ShadowFigure;
  private busy = false;
  private running = false;
  private time = 0;
  private breathClock = 0;
  private catching = false;
  private surface = "dirt";
  private readonly abort = new AbortController();
  private startTime = performance.now();

  constructor(private readonly game: Game) {
    this.progress = new PagodaProgress(game.flags, game.inventory);
    this.sounds = new PagodaSoundscape(game);
    this.cinematics = new PagodaCinematics(game, this.sounds);
    this.cheaHands = new CheaHands(game);
  }
  get active(): boolean {
    return this.running;
  }
  get paused(): boolean {
    const g = this.game;
    return (
      this.busy ||
      g.cutscene ||
      g.satchel.isOpen ||
      !!g.sketchbook?.isVisible ||
      g.notebook.isOpen ||
      document.hidden ||
      !g.input.pointerLocked
    );
  }
  async load(): Promise<void> {
    const g = this.game;
    this.area = await loadArea(g.scene, "ep2", "ep2_area_pagoda", {
      cellSize: 8,
      keep: [
        /^pret_\d+$/,
        /^mirror_disc_/,
        /^bridge_symbol_/,
        "hall_chain",
        /^bridge_plank/,
        ...COLLAPSE_KEEP,
      ],
      beforeBatch: (container) => {
        // The fully authored seated monk replaces the first-pass sculpt.
        for (const mesh of container.meshes)
          if (/^sophal_/.test(mesh.name)) {
            mesh.isVisible = false;
            mesh.setEnabled(false);
          }
      },
      coarse: { pattern: /leaf|leaves|fern|bark|bamboo/, cellSize: 24 },
    });
    g.fallGuard.bounds = BOUNDS;
    // The far forest runs on into the fog in every direction.
    g.camera.maxZ = 130;
    this.lights = new PagodaLights(g, this.area);
    buildFarForest(g.scene, g.wind, g.scene.getMaterialByName("M_ep2_earth"));
    for (let i = 0; i < 5; i++) {
      const actor = this.node("pret_" + i);
      if (!actor) throw new Error("Missing Pret " + i);
      actor.rotationQuaternion = null;
      for (const mesh of actor.getChildMeshes()) mesh.isPickable = false;
      this.actors.push(actor);
    }
    await ShadowFigure.prepare(g.scene);
    this.guardian = new ShadowFigure(g.scene, "pagoda_guardian", 4);
    this.guardian.root.setEnabled(false);
    this.spawn();
    this.equipment = new PagodaEquipment(g, this.lights);
    await this.equipment.load();
    await Promise.all([this.cinematics.load(), this.cheaHands.load()]);
    this.apparition = new PagodaApparition(g, this.sounds, this.lights);
    this.apparition.attach();
    for (const light of [this.lights.sky, this.lights.moon, ...this.lights.flames])
      if (light !== this.lights.lamp)
        light.excludedMeshes.push(...this.equipment.held.meshes, ...g.hands.meshes);
    for (let i = 0; i < 4; i++) this.node("bridge_symbol_" + i)?.setEnabled(false);
    const gateMarker = this.area.level.interactables.find((m) => m.name === "interact_bridge_lock");
    if (!gateMarker) throw new Error("Missing bridge lock marker");
    gateMarker.node.setEnabled(false);
    gateMarker.node.name = "retired_bridge_lock_block";
    this.gate = new PagodaGate(g.scene);
    gateMarker.node = this.gate.root;
    for (const m of this.area.level.interactables) {
      if (m.name.startsWith("interact_stupa_")) {
        // The turned bronze shell is hollow; its solid inner floor must catch the
        // ordinary interaction ray when Sora looks down into the offering bowl.
        const bowl = m.node.getChildMeshes()[0];
        const bronze =
          bowl?.material instanceof PBRMaterial ? bowl.material.clone(m.name + "_bronze") : null;
        if (bronze) for (const part of m.node.getChildMeshes()) part.material = bronze;
        const floor = CreateCylinder(
          m.name + "_inner_floor",
          { diameter: 0.33, height: 0.016, tessellation: 32 },
          g.scene,
        );
        floor.parent = m.node;
        floor.setAbsolutePosition(m.position.add(new Vector3(0, 0.012, 0.05)));
        floor.material = bronze ?? bowl?.material ?? null;
      }
      g.interaction.add(m.name, m.node);
    }
    g.interaction.allow = (id) => this.allowed(id);
    g.bus.on("interact:use", ({ id }) => {
      if (this.busy || g.cutscene || !this.allowed(id)) return;
      void this.use(id).catch((error) => {
        console.error("[Episode 2]", error);
        void g.subtitles.say("Sora", "The page is still here. Try the interaction again.", 4);
      });
    });
    g.bus.on("interact:focus", ({ id }) => this.focus(id));
    g.bus.on("player:step", ({ surface }) => {
      this.surface = surface;
    });
    g.bus.on("noise:made", (event) => {
      if (this.paused || this.progress.stage !== "garden") return;
      const factor =
        event.source === "player"
          ? this.surface === "leaves"
            ? 1.8
            : this.surface === "stone"
              ? 1.15
              : 0.65
          : 1;
      this.hear(event.position, event.loudness * factor);
    });
    window.addEventListener(
      "keydown",
      (e) => {
        if (e.code === "Space" && g.input.pointerLocked) e.preventDefault();
        if (!e.repeat && e.code === "KeyG" && !this.paused) this.throwBowl();
      },
      { signal: this.abort.signal },
    );
    g.scene.onDisposeObservable.addOnce(() => this.abort.abort());
    this.makeBeams();
    this.makeTendrils();
    this.sync();
  }
  private node(name: string): TransformNode | null {
    return this.game.scene.getTransformNodeByName(name) ?? this.game.scene.getMeshByName(name);
  }
  private spawn(): void {
    const stage = this.progress.stage;
    const at =
      stage === "memory"
        ? MEMORY
        : stage === "escape" || stage === "library"
          ? LIBRARY
          : stage === "dawn" || stage === "complete"
            ? DAWN
            : !this.game.flags.get("ep2.started", false) ||
                this.game.resumedSave?.checkpoint === "CP0"
              ? ENTRY
              : KUTI;
    this.game.spawnPlayer(new Vector3(at.x, at.y, at.z), at.yaw);
    this.game.fallGuard.bounds =
      stage === "memory" ? { minX: 69, maxX: 91, minZ: -16, maxZ: 16 } : BOUNDS;
  }
  async begin(): Promise<void> {
    const g = this.game;
    this.lights.begin();
    this.cinematics.begin();
    g.atmosphere.nightSight.excludedMeshes.push(...this.equipment.held.meshes, ...g.hands.meshes);
    g.cutscene = true;
    g.scene.onBeforeRenderObservable.add(() => this.update(g.deltaSeconds));
    if (import.meta.env.DEV) (window as unknown as { pagoda: WhisperingPagoda }).pagoda = this;
    await g.fade.to(1, 0);
    await g.fade.waitForEnter(() => {
      void g.input.lockPointer();
      void g.audio?.unlock();
    });
    await this.sounds.load();
    if (!g.flags.get("ep2.started", false)) {
      g.flags.set("ep2.started", true);
      document.exitPointerLock();
      await g.fade.show({
        title: "The Whispering Pagoda",
        body: "Episode II · The last night of Pchum Ben · 11:45 PM",
        button: "Follow Sok’s map",
      });
      g.fade.hideCard();
      await this.persist("Pagoda · Naga gate");
    }
    this.running = true;
    g.cutscene = false;
    await g.fade.to(0, 2);
    if (this.progress.stage === "complete") {
      await this.persist();
      void this.ending();
      return;
    }
    if (this.progress.stage === "memory") {
      this.memoryLook();
      if (!g.flags.get("ep2.cinematic.harvest", false)) await this.playHarvest();
      else this.cinematics.setMemory("famine");
      this.message("Chea", "No grain left. No medicine. The shrine is ahead.");
    } else if (this.progress.stage === "escape") {
      await this.playCollapse();
      this.startEscape();
    } else if (this.progress.stage === "dawn") this.lights.dawn();
    else
      this.message(
        "Sora",
        this.progress.stage === "arrival"
          ? "The pagoda. A lamp is still burning in the kuti, to the left."
          : "The silver flowers. Four family stupas, four offerings.",
      );
    g.hints.show("ep2.hint.controls", 12);
  }
  private allowed(id: string): boolean {
    const p = this.progress,
      s = p.stage;
    if (!id.startsWith("interact_")) return false;
    if (id === "interact_monk" || id === "interact_supplies" || id === "interact_lore_monk")
      return s === "arrival" || s === "garden";
    if (id === "interact_memory_shrine") return s === "memory";
    if (id.startsWith("interact_stupa_"))
      return s === "garden" || (s === "dawn" && id === "interact_stupa_chea");
    if (id.startsWith("interact_pickup_"))
      return (
        s === "garden" &&
        !this.game.flags.get("ep2.pickup." + id.replace("interact_pickup_", ""), false)
      );
    if (id.startsWith("interact_bell")) return s === "garden";
    if (id.startsWith("interact_lore_hall"))
      return s === "garden" && this.game.flags.get("ep2.hall.open", false);
    if (id.startsWith("interact_lore_library")) return s === "library";
    if (id === "interact_bridge_lock") return s === "garden";
    if (id.startsWith("interact_mirror_") || id === "interact_archive") return s === "library";
    return false;
  }
  private focus(id: string): void {
    const key = id.includes("stupa")
      ? "ep2.hint.stupa"
      : id.includes("mirror")
        ? "ep2.hint.mirror"
        : id.includes("bell_") && id !== "interact_bell_verse"
          ? "ep2.hint.bell"
          : "hint.use";
    this.game.hints.show(key, 4);
  }
  private async use(id: string): Promise<void> {
    const g = this.game,
      p = this.progress;
    if (id === "interact_monk") {
      await this.dialog(async () => {
        if (!g.flags.get("ep2.cinematic.sophal", false)) {
          this.view.hide();
          await this.cinematics.sophal();
          g.flags.set("ep2.cinematic.sophal", true);
        }
        await this.view.show(
          "Venerable Sophal",
          [
            "The white thread lies across his open palm. Four silver flowers mark the family stupas. Oil and matches wait on the table.",
            "His notebook guidance is now copied into mine: C to crouch, Space to hold breath briefly, G to throw an empty bowl. The kuti is safe.",
          ],
          ["Receive the white thread"],
        );
        p.meetMonk();
        g.flags.set("ep2.checkpoint", "CP1");
        await this.persist("Pagoda · Sophal’s kuti");
      });
      this.sync();
      return;
    }
    if (id === "interact_supplies") {
      await this.dialog(async () => {
        g.inventory.add("matches", Math.max(0, 10 - g.inventory.count("matches")));
        g.inventory.add("oil", Math.max(0, 2 - g.inventory.count("oil")));
        await this.view.show(
          "Sophal’s table",
          [
            "A tin of kerosene and a dry matchbox. Take what you need.",
            "F lights or extinguishes the lamp. X slides its shutter without using a match. R refills the tank.",
          ],
          ["Close the matchbox"],
        );
        await this.persist();
      });
      return;
    }
    if (id.startsWith("interact_pickup_")) {
      const item = id.replace("interact_pickup_", "") as Offering | "bowls";
      if (p.collect(item)) {
        this.message(
          "Sora",
          item === "rice"
            ? "Two portions of rice. Chea, and Kanha."
            : item === "lotus"
              ? "A lotus bud. For the one who tended the pond."
              : item === "water"
                ? "Sanctified water. For Chhun."
                : "Empty bowls. I will leave the rice for the dead.",
        );
        await this.saveProgress();
        this.sync();
      }
      return;
    }
    if (id.startsWith("interact_stupa_")) {
      const ancestor = ANCESTORS.find((a) => id === "interact_stupa_" + a.id);
      if (!ancestor) return;
      if (p.stage === "dawn") {
        await this.dawnOffering();
        return;
      }
      await this.dialog(async () => {
        if (p.offered(ancestor.id)) {
          await this.view.show(
            ancestor.name,
            [ancestor.inscription, "The offering rests undisturbed."],
            ["Leave it in peace"],
          );
          return;
        }
        const choice = await this.view.show(
          ancestor.name,
          [
            ancestor.inscription,
            "The silver five-petalled flower matches the emblem in Sok’s journal.",
          ],
          ["Offer rice balls", "Offer a lotus bud", "Offer sanctified water", "Leave the stupa"],
        );
        if (choice === 3) return;
        const result = p.offer(ancestor.id, (["rice", "lotus", "water"] as const)[choice]);
        if (result !== "placed") {
          await this.view.show(
            ancestor.name,
            [
              result === "wrong"
                ? "The inscription remembers a different kindness. I should keep this offering."
                : result === "missing"
                  ? "I have not gathered that offering yet. The trays stand along the garden’s outer paths."
                  : "The offering is already placed.",
            ],
            ["Read the inscription again"],
          );
          return;
        }
        await this.persist("Pagoda · Sophal’s kuti");
        this.hear(ancestor, 0.7);
      });
      this.sync();
      return;
    }
    if (id === "interact_bell_verse") {
      await this.dialog(() =>
        this.view.show(
          "The bell verse",
          [
            "First the deepest voice calls the earth. Then the smallest voice calls the sky. Last the middle voice carries us home.",
            "The bells are large, small, and middle in that order. Their sound will carry across the garden.",
          ],
          ["Remember the verse"],
        ),
      );
      return;
    }
    if (/^interact_bell_[0-2]$/.test(id)) {
      const bell = Number(id.at(-1));
      this.sounds.ring(bell);
      const open = p.ring(bell);
      this.hear({ x: 19.4, z: 9 }, 1.4);
      this.message("Sora", open ? "The chains have fallen." : "The bronze is still ringing.");
      await this.saveProgress();
      this.sync();
      return;
    }
    if (id.startsWith("interact_lore_")) {
      const note = id.replace("interact_lore_", "") as NoteId;
      if (!(note in NOTES)) return;
      await this.dialog(async () => {
        if (!p.read(note)) return;
        await this.view.show(NOTES[note].title, [NOTES[note].text], ["Copy into the sketchbook"]);
        await this.persist();
      });
      return;
    }
    if (id === "interact_bridge_lock") {
      if (p.offerings < 4) {
        this.message(
          "Sora",
          `${p.offerings} of the four flowers answer. The others are still dark.`,
        );
        return;
      }
      await this.dialog(async () => {
        p.openBridge();
        g.flags.set("ep2.checkpoint", "CP2");
        await this.persist("Pagoda · Library bridge");
      });
      this.sync();
      this.message("Sora", "Four offerings. The bronze lock has opened.");
      return;
    }
    if (id.startsWith("interact_mirror_")) {
      const index = Number(id.at(-1));
      const turn = p.rotateMirror(index);
      if (turn < 0) return;
      this.message(
        "Sora",
        `Mirror ${index + 1}: ${turn} quarter turns. ${p.mirrorsAligned ? "The moonlight reaches the silver lock." : "The silver line catches the moonlight."}`,
      );
      await this.saveProgress();
      this.sync();
      return;
    }
    if (id === "interact_archive") {
      if (!p.mirrorsAligned) {
        this.message(
          "Sora",
          "The cabinet stays locked. Three mirrors must carry the moonlight here.",
        );
        return;
      }
      await this.dialog(async () => {
        p.openArchive();
        g.flags.set("ep2.checkpoint", "CP3");
        await this.persist("Memory · The forest shrine");
        await this.view.show(
          "The family record",
          [
            "The silver lock lifts. Inside lie Chea’s record and his betel box, still heavy with earth.",
            "“A harvest. Laughter beside the fire. My children dancing. And then…”",
            "The page smells of smoke. The room is gone.",
          ],
          ["Enter Chea’s memory"],
        );
        await g.fade.to(1, 1);
        g.player.teleport(new Vector3(MEMORY.x, MEMORY.y, MEMORY.z), MEMORY.yaw);
        g.fallGuard.bounds = { minX: 69, maxX: 91, minZ: -16, maxZ: 16 };
        g.fallGuard.reset(g.player.feet);
        this.memoryLook();
        this.sync();
        this.view.hide();
        await this.cinematics.harvest();
        g.flags.set("ep2.cinematic.harvest", true);
        await this.persist("Memory · The forest shrine");
      });
      this.message("Chea", "No grain left. No medicine. The shrine is ahead.");
      return;
    }
    if (id === "interact_memory_shrine") {
      await this.dialog(async () => {
        this.view.hide();
        await this.cinematics.bargain();
        const choice = await this.view.show(
          "What did you ask for?",
          [
            "The box weighs almost nothing in my hands. Behind me, the village is hungry.",
            "A voice like grinding stone: “What do you want, Chea?”",
          ],
          [
            "Take what you will. Only save my children.",
            "Give us land and riches, and our line is yours.",
            "Save my children… and let us never be poor again.",
          ],
        );
        p.remember(choice);
        g.flags.set("ep2.checkpoint", "CP4");
        await this.persist("Pagoda · Library escape");
        await this.view.show(
          "Chea · 1910",
          [
            choice === 2
              ? "The memory holds steady. Both wishes. Both spoken beneath the tree."
              : "The memory flickers. Somewhere between the family’s story and the village’s story, another wish went unspoken.",
            "The silver box grows heavy. When I lift its lid, it is filled with earth.",
          ],
          ["Return to the library"],
        );
        await g.fade.to(1, 1);
        g.atmosphere.setGrade(EP1_GRADE);
        g.atmosphere.mood.memory = false;
        g.player.config.walkSpeed = 1.6;
        g.player.config.hurrySpeed = 3.4;
        g.player.config.crouchSpeed = 0.9;
        g.handsHidden = false;
        this.cheaHands.active = false;
        this.equipment.memory = false;
        this.cinematics.setMemory("hidden");
        g.fallGuard.bounds = BOUNDS;
        g.player.teleport(new Vector3(0, 1.4, -34), 0);
        g.fallGuard.reset(g.player.feet);
        this.view.hide();
        await g.fade.to(0, 1);
        await this.cinematics.breakLibrary();
        g.flags.set("ep2.cinematic.collapse", true);
        await this.persist("Pagoda · Library escape");
        this.startEscape();
      });
      return;
    }
  }
  /** A paper reader owns movement and pointer capture until its final action. */
  private async dialog(action: () => Promise<unknown>): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    const g = this.game;
    g.cutscene = true;
    g.gated.holdStill = true;
    g.stopInspecting();
    g.closeSketchbook();
    g.satchel.close();
    g.hints.hide();
    g.input.clear();
    document.exitPointerLock();
    try {
      await action();
    } finally {
      this.view.hide();
      g.subtitles.hide();
      g.gated.holdStill = false;
      g.cutscene = false;
      this.contactGrace = Math.max(this.contactGrace, B.readingGrace);
      this.busy = false;
    }
  }
  private async saveProgress(location?: string): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    const g = this.game;
    g.cutscene = true;
    g.gated.holdStill = true;
    try {
      await this.persist(location);
    } finally {
      this.view.hide();
      g.cutscene = false;
      g.gated.holdStill = false;
      this.busy = false;
    }
  }
  private message(speaker: string, text: string): void {
    void this.game.subtitles.say(speaker, text, Math.max(4, text.length / 17));
  }
  private hear(at: Point, loudness: number): void {
    this.ghosts.slice(0, this.progress.pretCount).forEach((ghost) => ghost.hear(at, loudness));
  }
  private throwBowl(): void {
    const g = this.game;
    if (this.progress.stage !== "garden" || !g.inventory.remove("clay_bowl")) return;
    g.hands.animate("reach");
    const at = g.player.feet.add(
      new Vector3(Math.sin(g.player.yaw) * B.bowlRange, 0, Math.cos(g.player.yaw) * B.bowlRange),
    );
    // Empty bowls leave the sacred rice intact. The hearing target is clamped to the garden.
    at.x = Math.max(-16, Math.min(16, at.x));
    at.z = Math.max(-16, Math.min(14, at.z));
    this.hear(at, B.bowlLoudness);
    this.sounds.throw(at);
    this.message("Sora", "The empty bowl shatters beyond the stupas.");
    void this.saveProgress();
  }
  private memoryLook(): void {
    const g = this.game;
    g.atmosphere.mood.memory = true;
    g.player.config.walkSpeed = 0.85;
    g.player.config.hurrySpeed = 0.85;
    g.player.config.crouchSpeed = 0.65;
    g.atmosphere.setGrade({
      ...EP1_GRADE,
      saturation: -0.45,
      midtones: { tint: [1, 0.72, 0.43], strength: 0.4 },
    });
    g.handsHidden = true;
    this.cheaHands.active = true;
    this.equipment.memory = true;
  }
  private async playHarvest(): Promise<void> {
    await this.dialog(async () => {
      await this.cinematics.harvest();
      this.game.flags.set("ep2.cinematic.harvest", true);
      await this.persist("Memory · The forest shrine");
    });
  }
  private async playCollapse(): Promise<void> {
    if (this.game.flags.get("ep2.cinematic.collapse", false)) {
      this.cinematics.collapse.restoreBroken();
      return;
    }
    await this.dialog(async () => {
      await this.cinematics.breakLibrary();
      this.game.flags.set("ep2.cinematic.collapse", true);
      await this.persist("Pagoda · Library escape");
    });
  }
  private startEscape(): void {
    this.escapeClock.reset();
    this.cinematics.collapse.restoreBroken();
    this.sync();
    this.message("Sora", "The roof is splitting. Across the bridge. Back to Chea’s stupa.");
    this.game.atmosphere.scare();
  }
  private async dawnOffering(): Promise<void> {
    const g = this.game,
      p = this.progress;
    await this.dialog(async () => {
      if (!g.inventory.has("silver_betel_box")) return;
      if (!g.flags.get("ep2.cinematic.dawn", false)) {
        this.view.hide();
        await this.cinematics.dawn();
        g.flags.set("ep2.cinematic.dawn", true);
        await this.persist("Pagoda · Dawn offering");
      }
      await this.view.show(
        "4:00 AM · Chea’s stupa",
        [
          "The bell travels through the mist. I pour the old earth at the foot of the stupa. Sophal’s incense catches.",
          "Four ancestors. The order is written in the sketchbook: Chea, his wife, Chhun, Kanha.",
        ],
        ["Speak their names"],
      );
      const names: string[] = [];
      for (let i = 0; i < 4; i++) {
        const choices = ANCESTORS.filter((a) => !names.includes(a.id));
        const answer = await this.view.show(
          "The dawn offering",
          [
            `Name ${i + 1} of four. ${names.length ? "Remembered: " + names.map((id) => ANCESTORS.find((a) => a.id === id)!.name).join(", ") : "Begin with the one who made the bargain."}`,
          ],
          choices.map((a) => a.name),
        );
        names.push(choices[answer].id);
      }
      if (!p.finish(names)) {
        await this.view.show(
          "The silver holds",
          [
            "The names have fallen out of order. The inscription and the sketchbook remember them. The earth is still here; I can begin again.",
          ],
          ["Return to the stupa"],
        );
        return;
      }
      g.flags.set("ep2.checkpoint", "CP5");
      await this.persist("Pagoda · Second seal broken");
      this.sync();
    });
    if (p.stage === "complete") void this.ending();
  }
  private async ending(): Promise<void> {
    const g = this.game,
      p = this.progress;
    await this.dialog(async () => {
      this.lights.dawn();
      this.sounds.dawn();
      if (!g.flags.get("ep2.cinematic.photograph", false)) {
        this.view.hide();
        await this.cinematics.photograph();
        g.flags.set("ep2.cinematic.photograph", true);
        await this.persist();
      }
      await this.view.show(
        "The second seal",
        [
          "The silver inlay comes loose in my hand. The hungry spirits withdraw between the ash stupas.",
          "A photograph slips from the box’s lining. Tonle Sap clinic, 1920. Uncle Sok stands in a physician’s white coat. Beside him is my mother. She is pregnant.",
          "Blood seeps from the photograph onto the map. The second mark darkens. I fill the fourth circle.",
        ],
        ["Three nights remain"],
      );
      while (true) {
        const action = await this.view.show(
          "The Unbroken Debt",
          [
            "Episode 2 · The Whispering Pagoda",
            "Second seal broken · Night 4 of 7",
            `Lore found: ${p.lore.length} / 5 · Respect carried forward: ${g.flags.get("series.respect", 0)}`,
            "The silver inlay and Sophal’s white thread are saved for the last night.",
            "Next: Episode 3 · The Drowned Village",
            "Created by Rithy Bondeth. Babylon.js · Havok. Shared Episode 1 materials and CC0 library credits apply.",
          ],
          ["Continue to Episode 3", "Return to title", "Export completion save"],
        );
        if (action === 0) {
          await g.saves.save("episode2", this.capture());
          location.assign(`${import.meta.env.BASE_URL}?episode=3`);
          return;
        }
        if (action === 1) {
          location.assign(import.meta.env.BASE_URL);
          return;
        }
        const code = await encodeSaveCode(this.capture());
        const url = URL.createObjectURL(new Blob([code], { type: "text/plain" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = "boon-sop-episode-2.save.txt";
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    });
  }
  capture(): SaveData {
    const g = this.game,
      stage = this.progress.stage;
    const clock =
      stage === "arrival"
        ? "23:45"
        : stage === "garden"
          ? "00:30"
          : stage === "library"
            ? "02:15"
            : stage === "memory"
              ? "02:45"
              : stage === "escape"
                ? "03:45"
                : "04:00";
    g.flags.set("ep2.clock", clock);
    return {
      saveVersion: 1,
      episode: 2,
      checkpoint: g.flags.get("ep2.checkpoint", "CP0"),
      clock,
      flags: g.flags.toJSON(),
      inventory: g.inventory.toJSON(),
      lamp: this.equipment.lamp.toJSON(),
      playTimeSec: (g.resumedSave?.playTimeSec ?? 0) + (performance.now() - this.startTime) / 1000,
      savedAt: new Date().toISOString(),
    };
  }
  private async persist(location?: string): Promise<void> {
    const g = this.game;
    if (location) g.flags.set("checkpoint.location", location);
    while (true) {
      try {
        const save = this.capture();
        if (location) await g.checkpoints.mark(save, location);
        else await g.saves.save("autosave", save);
        if (this.progress.stage === "complete") await g.saves.save("episode2", this.capture());
        return;
      } catch {
        document.exitPointerLock();
        await this.view.show(
          "The page could not be saved",
          [
            "Your progress is still here. Free browser storage, then retry. Your Episode 1 archive is kept separately.",
          ],
          ["Retry save"],
        );
        this.view.hide();
      }
    }
  }
  private sync(): void {
    const g = this.game,
      p = this.progress;
    const bridge = p.flags.get("ep2.bridge.open", false),
      hall = p.flags.get("ep2.hall.open", false);
    this.gate.sync(p);
    this.node("hall_chain")?.setEnabled(!hall);
    // Runtime bodies use their independent LevelBuilder anchors; remove only the opened gate's body.
    for (const name of ["bridge_lock", "hall_chain"])
      if (name === "bridge_lock" ? bridge : hall) {
        const body = g.scene.getTransformNodeByName("col_" + name + "_body");
        body?.dispose();
      }
    for (const item of ["rice", "lotus", "water", "bowls"]) {
      this.node("interact_pickup_" + item)?.setEnabled(!p.flags.get("ep2.pickup." + item, false));
    }
    for (const a of ANCESTORS) {
      const mat = this.node("interact_stupa_" + a.id)?.getChildMeshes()[0]?.material;
      if (mat instanceof PBRMaterial)
        mat.emissiveColor = p.offered(a.id) ? new Color3(0.08, 0.055, 0.02) : Color3.Black();
    }
    p.mirrors.forEach((turn, i) => {
      const node = this.node("interact_mirror_" + i);
      if (!node) return;
      // Rotate only the mirror disc, so its pedestal stays grounded.
      const disc = node.getChildMeshes().find((m) => m.name.startsWith("mirror_disc_"));
      if (disc) {
        disc.rotationQuaternion = null;
        disc.rotation.y = (turn * Math.PI) / 2;
      }
    });
    this.beams.forEach((beam, i) =>
      beam.setEnabled(
        p.stage === "library" &&
          (i === 0 || p.mirrors.slice(0, i).every((v, k) => v === MIRROR_TARGETS[k])),
      ),
    );
    this.guardian.root.setEnabled(p.stage === "escape");
    for (const t of this.tendrils) t.setEnabled(p.stage === "escape");
    if (g.atmosphere && (p.stage === "dawn" || p.stage === "complete")) this.lights.dawn();
  }
  private makeBeams(): void {
    const g = this.game;
    const material = new StandardMaterial("pagoda_moonbeam", g.scene);
    material.disableLighting = true;
    material.emissiveColor = new Color3(0.4, 0.5, 0.65);
    material.alpha = 0.23;
    const points = [
      new Vector3(-2, 5.6, -29.8),
      new Vector3(-2, 2.45, -29.8),
      new Vector3(1.6, 2.45, -31),
      new Vector3(-1, 2.45, -33),
      new Vector3(0, 2.1, -35),
    ];
    for (let i = 0; i < points.length - 1; i++) {
      const mesh = CreateTube(
        "moonlight_" + i,
        { path: [points[i], points[i + 1]], radius: 0.025, tessellation: 8 },
        g.scene,
      );
      mesh.material = material;
      mesh.isPickable = false;
      this.beams.push(mesh);
    }
  }
  private makeTendrils(): void {
    const g = this.game,
      material = new StandardMaterial("pond_shadow", g.scene);
    material.diffuseColor = new Color3(0.008, 0.009, 0.012);
    material.specularColor = Color3.Black();
    for (let i = 0; i < 6; i++) {
      const side = i % 2 ? -1 : 1,
        z = -19 - i * 1.4;
      const mesh = CreateTube(
        "shadow_tendril_" + i,
        {
          path: [
            new Vector3(side * 2, 0, z),
            new Vector3(side * 1.7, 0.7, z),
            new Vector3(side * 1.5, 1.8, z + 0.6),
            new Vector3(side * 1.8, 2.7, z + 1),
          ],
          radius: 0.055,
          tessellation: 8,
        },
        g.scene,
      );
      mesh.material = material;
      mesh.isPickable = false;
      this.tendrils.push(mesh);
    }
  }
  private update(dt: number): void {
    if (!this.running) return;
    const g = this.game,
      p = this.progress;
    this.time += dt;
    const simDt = simulationStep(dt);
    this.equipment.update(simDt);
    this.cheaHands.update(dt, this.equipment);
    this.cinematics.update(document.hidden || this.cinematics.director.isPaused ? 0 : dt);
    const active = !this.paused;
    if (active) this.contactGrace = Math.max(0, this.contactGrace - simDt);
    this.cinematics.collapse.update(dt, active && p.stage === "escape");
    this.actors.forEach((actor, i) => {
      const visible =
        (p.stage === "garden" && i < p.pretCount) || (p.stage === "arrival" && i === 0);
      actor.setEnabled(visible);
      if (!visible) return;
      const brain = this.ghosts[i];
      if (active && p.stage === "garden") brain.update(simDt);
      actor.setAbsolutePosition(
        new Vector3(brain.position.x, Math.sin(this.time * 1.2 + i) * 0.035, brain.position.z),
      );
      actor.rotation.y = brain.yaw;
      actor.rotation.z = Math.sin(this.time * 0.8 + i) * 0.018;
    });
    this.sounds.update(
      dt,
      this.ghosts.slice(0, p.pretCount).map((b) => b.position),
      active && p.stage === "garden",
      active && p.stage === "escape",
    );
    // The horror layer and the apparition: silent and still in readers, menus and cinematics.
    const feet = g.player.feet;
    const haunting = active && !g.cutscene;
    const nearestPret =
      p.stage === "garden"
        ? Math.min(
            ...this.ghosts
              .slice(0, p.pretCount)
              .map((b) => Math.hypot(b.position.x - feet.x, b.position.z - feet.z)),
          )
        : 99;
    this.sounds.haunt(
      dt,
      {
        x: feet.x,
        z: feet.z,
        yaw: g.player.yaw,
        stage: p.stage,
        safe: inKuti(feet),
        inHall: feet.x > 17.6 && feet.x < 26.4 && feet.z > -8.4 && feet.z < 6.4,
        fear: g.atmosphere.mood.fear,
        moving: g.player.speed > 0.2,
      },
      haunting,
    );
    this.apparition.update(
      dt,
      {
        stage: p.stage,
        feet,
        yaw: g.player.yaw,
        offerings: p.offerings,
        inKuti: inKuti(feet),
        mirrorsTurned: p.mirrors.some((turn) => turn !== 0),
        nearestPret,
      },
      haunting,
    );
    if (!active) return;
    if (p.stage === "garden") {
      if (this.breath.update(simDt, g.input.isHeld("Space"))) {
        this.hear(g.player.feet, 1.3);
        this.sounds.gasp(g.player.feet);
        this.message("Sora", "I held it too long.");
      }
      this.breathClock += simDt;
      if (this.breathClock > B.breathingInterval) {
        this.breathClock = 0;
        if (!this.breath.holding) this.hear(g.player.feet, B.breathingLoudness);
      }
      const nearest = Math.min(
        ...this.ghosts
          .slice(0, p.pretCount)
          .map((b) => Math.hypot(b.position.x - g.player.feet.x, b.position.z - g.player.feet.z)),
      );
      g.threatActive = !inKuti(g.player.feet) && nearest < 5;
      g.atmosphere.mood.fear = inKuti(g.player.feet) ? 0 : Math.max(0, 1 - nearest / 12);
      if (
        !this.catching &&
        this.contactGrace <= 0 &&
        this.ghosts.slice(0, p.pretCount).some((b) => b.catches(g.player.feet))
      ) {
        this.catching = true;
        g.bus.emit("player:caught", { by: "pret" });
        void g.retryFromCheckpoint();
      }
    } else {
      g.threatActive = p.stage === "escape";
      g.atmosphere.mood.fear = p.stage === "escape" ? 0.7 : 0;
    }
    if (p.stage === "escape") {
      for (const warning of this.escapeClock.update(simDt, true)) {
        this.sounds.dawnBell();
        this.message(
          "Sora",
          warning === 12
            ? "It will not hold. Chea’s stupa, on the west side."
            : "The bridge is coming apart behind me. Keep moving.",
        );
      }
      this.guardian.root.position.set(0, 1.32, -35);
      this.guardian.animate(this.time, 0, 1);
      for (const [i, t] of this.tendrils.entries())
        t.scaling.y = 1 + Math.sin(this.time * 2 + i) * 0.12;
      for (const mesh of g.scene.meshes)
        if (
          mesh.name.startsWith("bridge_plank") &&
          g.player.feet.z > mesh.getAbsolutePosition().z + 1
        )
          mesh.rotation.z = Math.sin(this.time * 6 + mesh.uniqueId) * 0.025;
      if (!this.catching && this.escapeClock.expired) {
        this.catching = true;
        void g.retryFromCheckpoint();
        return;
      }
      if (Math.hypot(g.player.feet.x - DAWN.x, g.player.feet.z - DAWN.z) < 3) {
        p.escape();
        g.threatActive = false;
        this.sync();
        this.sounds.dawn();
        void this.dialog(() => this.persist("Pagoda · Dawn offering"));
        this.message("Sora", "The bell. Four o’clock. I must return the earth.");
      }
    }
  }
}
