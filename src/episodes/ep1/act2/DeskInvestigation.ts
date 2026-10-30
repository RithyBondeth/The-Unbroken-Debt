import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Axis } from "@babylonjs/core/Maths/math.axis";
import { Ray } from "@babylonjs/core/Culling/ray";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import type { Vigil } from "../act1/Vigil";
import type { VillageLights } from "../act1/VillageLights";
import { DocumentReader } from "../../../ui/html/DocumentReader";
import { DeskProgress } from "./DeskProgress";
import type { DeskModels } from "./DeskModels";
import { JOURNAL_B, FAILING_LAMPS } from "../data/desk";
import { drawerOpen, pickUp } from "../audio/prologueSounds";
import { branchSnap, breathOut } from "../audio/nightSounds";
import { boardCreak, seededRandom } from "../../../audio/synth";

/** Altar key → locked desk → final instructions → ash / portrait → CP4. */
export class DeskInvestigation {
  readonly progress: DeskProgress;
  readonly reader = new DocumentReader(JOURNAL_B);
  private readonly sounds = new Map<string, StaticSound>();
  private readonly entries: string[] = [];
  private savingIn = 10;
  private entryDelay = 0;
  private readonly forward = new Vector3();

  constructor(
    private readonly game: Game,
    private readonly area: Area,
    readonly models: DeskModels,
    private readonly vigil: Vigil,
    private readonly lights: VillageLights,
    private readonly saveProgress: () => Promise<unknown>,
  ) {
    this.progress = new DeskProgress(game.flags, game.inventory);
    const p = this.progress;
    models.restore(p.compartmentOpen, p.drawerOpen, p.portraitAwake, p.actThree);
    this.syncPickups();
    game.interaction.add("interact_altar_key_panel", models.panel);
    game.interaction.add("interact_desk_key", models.key);
    game.interaction.add("interact_sok_desk", models.drawer);
    game.interaction.add("interact_sok_journal_b", models.journal);
    game.interaction.add("interact_portrait", models.portrait);
    const thread = area.level.interactables.find((m) => m.name === "interact_thread");
    if (thread)
      game.interaction.add("interact_thread", [
        ...thread.node.getChildMeshes(),
        ...models.intactThreadMeshes,
        ...models.threadMeshes,
      ]);
    this.updateLamps();
    game.bus.on("interact:use", ({ id }) => this.use(id));
    game.bus.on("interact:focus", ({ id }) => {
      if (!this.handsFree) return;
      if (id === "interact_altar_key_panel" && p.available)
        game.hints.show("hint.altarKeyPanel", 4);
      if (id === "interact_desk_key") game.hints.show("hint.deskKey", 4);
      if (id === "interact_sok_desk")
        game.hints.show(p.drawerOpen ? "hint.deskOpen" : "hint.deskLocked", 4);
      if (id === "interact_sok_journal_b") game.hints.show("hint.journalB", 4);
    });
  }

  private get handsFree(): boolean {
    const g = this.game;
    return (
      !g.cutscene &&
      !g.threatActive &&
      !g.hiding &&
      !g.satchel.isOpen &&
      !g.sketchbook?.isOpen &&
      !g.sketchbook?.isBusy
    );
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    for (const [name, samples, at, volume] of [
      ["panel", boardCreak(rate, seededRandom(1040)), this.models.compartment.position, 0.35],
      ["drawer", drawerOpen(rate, seededRandom(1041)), this.models.desk.position, 0.65],
      ["key", pickUp(rate, seededRandom(1042)), this.models.compartment.position, 0.55],
      ["portrait", breathOut(rate, seededRandom(1043)), this.models.portrait.position, 0.65],
      ["snap", branchSnap(rate, seededRandom(1044)), new Vector3(0, 2.3, -7), 0.85],
    ] as const)
      this.sounds.set(
        name,
        await audio.spatialSound(`desk_${name}`, audio.buffer(samples, rate), "sfx", at, {
          volume,
          minDistance: 2.5,
        }),
      );
  }

  update(dt: number): void {
    const g = this.game,
      p = this.progress;
    this.models.update(dt, p.compartmentOpen, p.drawerOpen, p.portraitAwake);
    const feet = g.player.feet;
    const underTent = Math.abs(feet.x) < 3.8 && feet.z < -1 && feet.z > -7 && feet.y < 0.5;
    const event = p.update(
      dt,
      underTent,
      this.handsFree && !g.inspecting && this.entries.length === 0,
      this.vigil.incense.alive,
    );
    if (event === "portrait") {
      this.vigil.scriptedAsh();
      this.sounds.get("portrait")?.play();
      g.bus.emit("sequence:start", { id: "A2-09" });
      g.hints.show("note.portraitAsh", 7);
      void this.saveProgress();
    } else if (event === "snap") {
      this.models.setBroken(true);
      this.sounds.get("snap")?.play();
      g.bus.emit("sequence:end", { id: "A2-09" });
      g.bus.emit("sequence:start", { id: "A3-01" });
      void g.subtitles.say("Sora", "The thread—", 2.5);
      this.remember("SB-A3-01");
      this.entryDelay = 4;
      g.hints.show("note.threadSnapped", 8);
      // Flags, inventory, incense, and the new checkpoint are captured together.
      // No deferred animation callback can save the old CP3 after this point.
      void this.saveProgress();
    }
    if (p.portraitAwake && this.handsFree && underTent && !g.flags.get("ep1.portrait.seen", false))
      this.noticePortrait();
    if (p.actThree && this.handsFree) {
      g.flags.set("ep1.act3.seconds", g.flags.get("ep1.act3.seconds", 0) + dt);
      this.updateLamps();
    }
    if (p.portraitAwake && this.handsFree) {
      this.savingIn -= dt;
      if (this.savingIn <= 0) {
        this.savingIn = 10;
        void this.saveProgress();
      }
    }
    this.entryDelay = Math.max(0, this.entryDelay - dt);
    if (this.entries.length && this.entryDelay <= 0 && this.handsFree && !g.inspecting) {
      const pending = this.entries.splice(0).filter((id) => !g.sketchbook?.written.has(id));
      // One journal discovery adds both its notes and objective in one opening.
      // A second queued write must not reopen the book over the portrait scare.
      if (pending.length > 1) g.sketchbook?.restore(pending.slice(0, -1));
      const entry = pending.at(-1);
      if (entry) g.sketchbook?.write(entry);
    }
  }

  private syncPickups(): void {
    const p = this.progress;
    this.models.key.setEnabled(p.compartmentOpen && !p.keyTaken);
    this.models.journal.setEnabled(p.drawerOpen);
  }

  private use(id: string): void {
    if (!this.handsFree) return;
    const g = this.game,
      p = this.progress;
    if (id === "interact_altar_key_panel") {
      if (!p.available) return g.hints.show("note.altarKeyQuiet", 4);
      if (!p.openCompartment()) return;
      this.sounds.get("panel")?.play();
      this.syncPickups();
      g.hints.show("note.altarKeyFound", 5);
    } else if (id === "interact_desk_key") {
      if (!p.takeKey()) return;
      this.sounds.get("key")?.play();
      this.syncPickups();
      g.hints.show("note.deskKeyTaken", 5);
    } else if (id === "interact_sok_desk") {
      if (p.drawerOpen) return g.hints.show("hint.deskOpen", 4);
      if (!p.unlockDesk()) return g.hints.show("note.deskNeedsKey", 4);
      this.sounds.get("drawer")?.play();
      this.syncPickups();
      g.hints.show("note.deskOpened", 5);
    } else if (id === "interact_sok_journal_b") {
      if (!p.drawerOpen || !this.models.drawerReady) return;
      this.readJournal();
      return;
    } else if (id === "interact_portrait") {
      g.hints.show(p.portraitAwake ? "note.portraitOpen" : "note.portraitQuiet", 5);
      return;
    } else return;
    void this.saveProgress();
  }

  private readJournal(): void {
    const g = this.game;
    g.stopInspecting();
    g.cutscene = true;
    g.gated.holdStill = true;
    g.gated.holdLook = true;
    g.hints.hide();
    if (document.pointerLockElement) document.exitPointerLock();
    this.reader.show(
      g.flags.get("ep1.journalB.page", 0),
      () => {
        g.cutscene = false;
        g.gated.holdStill = false;
        g.gated.holdLook = false;
        if (this.reader.pageIndex === JOURNAL_B.length - 1 && this.progress.readJournal()) {
          this.remember("SB-06");
          this.remember("SB-A2-07");
          g.hints.show("note.journalBRead", 7);
        }
        void this.saveProgress();
      },
      (page) => {
        g.flags.set("ep1.journalB.page", page);
        void this.saveProgress();
      },
    );
  }

  private remember(id: string): void {
    const g = this.game;
    const written = new Set([
      ...g.flags.get("sketchbook.written", "").split(",").filter(Boolean),
      ...(g.sketchbook?.written ?? []),
      id,
    ]);
    g.flags.set("sketchbook.written", [...written].join(","));
    this.entries.push(id);
  }

  private noticePortrait(): void {
    const g = this.game;
    const eye = g.camera.globalPosition;
    const target = this.models.portrait.position;
    const to = target.subtract(eye),
      distance = to.length();
    if (distance > 4.5 || distance < 0.01) return;
    to.scaleInPlace(1 / distance);
    g.camera.getDirectionToRef(Axis.Z, this.forward);
    if (Vector3.Dot(to, this.forward) < 0.96) return;
    const hit = g.scene.pickWithRay(
      new Ray(eye, to, distance + 0.1),
      (m) => m.isEnabled() && m.isVisible && m.isPickable && m.renderingGroupId === 0,
    );
    if (!hit?.pickedMesh || !this.models.portrait.getChildMeshes().includes(hit.pickedMesh)) return;
    g.flags.set("ep1.portrait.seen", true);
    void g.subtitles.say("Sora", "No. No, no, no.", 3);
    void this.saveProgress();
  }

  private updateLamps(): void {
    if (!this.progress.actThree) return;
    const elapsed = this.game.flags.get("ep1.act3.seconds", 0);
    FAILING_LAMPS.forEach(({ light, mesh }, i) => {
      const level = Math.max(0, Math.min(1, ((i + 1) * 30 - elapsed) / 1.2));
      this.lights.practicalLevels.set(light, level);
      for (const flame of this.area.container.meshes)
        if (mesh.test(flame.name)) flame.visibility = level;
    });
  }
}
