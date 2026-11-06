import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateRibbon } from "@babylonjs/core/Meshes/Builders/ribbonBuilder";
import { CreateGround } from "@babylonjs/core/Meshes/Builders/groundBuilder";
import type { Game } from "../../core/Game";
import { loadArea, type Area } from "../../core/areaLoader";
import type { SaveData } from "../../systems/saves/SaveData";
import { encodeSaveCode } from "../../systems/saves/saveCode";
import { ResolutionView } from "../../ui/html/ResolutionView";
import { RelicCraft } from "../../shared/RelicCraft";
import { ShadowFigure } from "../../shared/entities/ShadowFigure";
import { LanternEquipment } from "../../systems/lamp/LanternEquipment";
import { CheaHands } from "../../player/CheaHands";
import { VillageLights } from "./VillageLights";
import { VillageWater } from "./VillageWater";
import { VillageSoundscape } from "./VillageSoundscape";
import { VillageProgress } from "./VillageProgress";
import { WaterSurvival } from "./WaterSurvival";
import { DrownedBrain } from "./DrownedBrain";
import { VillageCinematics } from "./VillageCinematics";
import { VillageSafe } from "./VillageSafe";
import { VillageDetailMotion } from "./VillageDetailMotion";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import {
  BOUNDS,
  VILLAGE,
  NOTES,
  KHMER_DIGITS,
  FUSE_IDS,
  LEAK_IDS,
  RITUAL_FIGURES,
  type NoteId,
} from "./data/village";
import "./village.css";

/** EP3: an afternoon among the living, followed by one complete night in the flooded clinic. */
export class DrownedVillage {
  area!: Area;
  lights!: VillageLights;
  water!: VillageWater;
  equipment!: LanternEquipment;
  readonly progress: VillageProgress;
  readonly survival = new WaterSurvival();
  readonly spirit = new DrownedBrain();
  readonly view = new ResolutionView("Episode 3 · The Drowned Village");
  readonly sounds: VillageSoundscape;
  readonly memoryHands: CheaHands;
  readonly cinematics: VillageCinematics;
  private writtenName!: TransformNode;
  private pen!: TransformNode;
  private readonly looseBeams: TransformNode[] = [];
  private safeDials!: VillageSafe;
  private guardian!: ShadowFigure;
  private details!: VillageDetailMotion;
  private kanha!: TransformNode;
  private pich!: TransformNode;
  private boat!: TransformNode;
  private readonly oars: TransformNode[] = [];
  private readonly wetEdge = document.createElement("div");
  private readonly abort = new AbortController();
  private readonly unsubscribe: (() => void)[] = [];
  private running = false;
  private busy = false;
  private catching = false;
  private time = 0;
  private activeSeconds = 0;
  private escapeSeconds = 0;
  private grace = 7;
  private flood = 0.26;
  private stroke = "";
  private strokeAge = 0;
  private crossing = 0;
  private warnedCold = false;
  private warnedWake = false;
  private readonly startTime = performance.now();

  constructor(private readonly game: Game) {
    this.progress = new VillageProgress(game.flags, game.inventory);
    this.sounds = new VillageSoundscape(game);
    this.memoryHands = new CheaHands(game);
    this.cinematics = new VillageCinematics(game);
    this.wetEdge.className = "village-wet-edge";
    this.wetEdge.setAttribute("aria-hidden", "true");
    document.body.append(this.wetEdge);
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
  private node(name: string): TransformNode | null {
    return this.game.scene.getTransformNodeByName(name) ?? this.game.scene.getMeshByName(name);
  }
  async load(): Promise<void> {
    const g = this.game;
    this.area = await loadArea(g.scene, "ep3", "ep3_area_village", {
      cellSize: 10,
      beforeBatch: (container) => {
        // The scanned vessel replaces the small first-pass bowl. Keep its
        // visible surface in the same production interaction before batching.
        const vessel = container.transformNodes.find(
          (n) => n.name === "ep3_finish_ritual_water_vessel",
        );
        const target = container.transformNodes.find((n) => n.name === "interact_purify");
        if (vessel && target) vessel.setParent(target, true);
      },
      keep: [
        "kanha",
        "pich",
        /^npc_/,
        /^market_resident_/,
        /^patch_/,
        /^ritual_flame_/,
        /^sora_moored_boat/,
        "debt_name",
        /^collapse_beam_/,
        /^generator_flywheel/,
        /^curtain_motion_/,
      ],
    });
    g.camera.maxZ = 4000;
    g.fallGuard.bounds = BOUNDS;
    this.lights = new VillageLights(g, this.area);
    this.details = new VillageDetailMotion(g);
    this.kanha = this.node("kanha")!;
    this.pich = this.node("pich")!;
    if (!this.kanha || !this.pich) throw new Error("Episode 3 spirit anatomy missing");
    for (const root of [this.kanha, this.pich]) {
      root.rotationQuaternion = null;
      for (const mesh of root.getChildMeshes()) mesh.isPickable = false;
    }
    this.spawn();
    this.equipment = new LanternEquipment(
      g,
      this.lights,
      "No dry matches. Pa Lok left a matchbox beside the attic stove.",
    );
    await Promise.all([this.equipment.load(), this.memoryHands.load()]);
    this.lights.lightEquipment([...this.equipment.held.meshes, ...g.hands.meshes]);
    this.water = new VillageWater(g);
    this.makeBoat();
    this.makeMemoryTools();
    await ShadowFigure.prepare(g.scene);
    this.guardian = new ShadowFigure(g.scene, "clinic_guardian", 7);
    this.guardian.root.position.set(10, -0.5, -8);
    this.guardian.root.setEnabled(false);
    await document.fonts.load('76px "Preah Vihear"');
    this.safeDials = new VillageSafe(g);
    this.node("safe_numerals")?.setEnabled(false);
    for (let i = 0; i < 3; i++) {
      const beam = this.node("collapse_beam_" + i);
      if (beam) {
        beam.rotationQuaternion = null;
        this.looseBeams.push(beam);
      }
    }
    for (const m of this.area.level.interactables) g.interaction.add(m.name, m.node);
    g.interaction.allow = (id) => this.allowed(id);
    this.unsubscribe.push(
      g.bus.on("interact:use", ({ id }) => {
        if (this.busy || g.cutscene || !this.allowed(id)) return;
        void this.use(id).catch((error) => {
          console.error("[Episode 3]", error);
          void g.subtitles.say("Sora", "The page is still here. Try again.", 3);
        });
      }),
      g.bus.on("interact:focus", ({ id }) => {
        if (id)
          g.hints.show(
            id.includes("fuse")
              ? "ep3.hint.fuse"
              : id.includes("seal_")
                ? "ep3.hint.seal"
                : "hint.use",
            4,
          );
      }),
    );
    window.addEventListener(
      "keydown",
      (event) => {
        if (
          event.repeat ||
          this.paused ||
          this.progress.stage !== "crossing" ||
          !["KeyA", "KeyD"].includes(event.code)
        )
          return;
        if (this.stroke !== event.code && this.strokeAge > 0.22) {
          this.stroke = event.code;
          this.strokeAge = 0;
          this.crossing = Math.min(1, this.crossing + 0.043);
          this.sounds.oar();
        }
      },
      { signal: this.abort.signal },
    );
    g.scene.onDisposeObservable.addOnce(() => {
      this.abort.abort();
      for (const stop of this.unsubscribe) stop();
      this.wetEdge.remove();
      this.view.panel.remove();
    });
    this.sync();
  }
  private spawn(): void {
    const stage = this.progress.stage;
    const at =
      stage === "market" || stage === "crossing"
        ? VILLAGE.market
        : stage === "vault" || stage === "memory"
          ? VILLAGE.vault
          : stage === "purification" || stage === "escape"
            ? VILLAGE.ritual
            : stage === "dawn" || stage === "complete"
              ? VILLAGE.rescue
              : VILLAGE.clinic;
    const f = this.game.flags;
    const saved = stage !== "crossing" && f.has("ep3.spawn.x");
    this.game.spawnPlayer(
      saved
        ? new Vector3(
            f.get("ep3.spawn.x", at.x),
            f.get("ep3.spawn.y", at.y),
            f.get("ep3.spawn.z", at.z),
          )
        : new Vector3(at.x, at.y, at.z),
      at.yaw,
    );
  }
  async begin(): Promise<void> {
    const g = this.game;
    this.lights.begin();
    this.sync();
    g.atmosphere.nightSight.excludedMeshes.push(...this.equipment.held.meshes, ...g.hands.meshes);
    g.cutscene = true;
    g.scene.onBeforeRenderObservable.add(() => this.update(g.deltaSeconds));
    if (import.meta.env.DEV) (window as unknown as { village: DrownedVillage }).village = this;
    await g.fade.to(1, 0);
    await g.fade.waitForEnter(() => {
      void g.input.lockPointer();
      void g.audio?.unlock();
    });
    await this.sounds.load();
    if (!g.flags.get("ep3.started", false)) {
      document.exitPointerLock();
      await g.fade.show({
        title: "The Drowned Village",
        body: "Episode III · Tonle Sap · Night 5 of 7 · 4:30 PM",
        button: "Step onto the floating market",
      });
      g.fade.hideCard();
      g.flags.set("ep3.started", true);
      await this.persist("Tonle Sap · Floating market");
    }
    this.running = true;
    g.cutscene = false;
    await g.fade.to(0, 2);
    if (this.progress.stage === "complete") void this.ending();
    else if (this.progress.stage === "dawn") void this.rescue();
    else
      this.message(
        "Sora",
        this.progress.stage === "market"
          ? "The photograph said Tonle Sap. Someone here must remember the clinic."
          : this.progress.stage === "memory"
            ? "These are not my hands. Uncle Sok. This room, before the water."
            : "The clinic. Stay on the boards. Listen beneath them.",
      );
    g.hints.show("ep3.hint.controls", 12);
  }
  allowed(id: string): boolean {
    const s = this.progress.stage,
      f = this.game.flags;
    if (!id.startsWith("interact_")) return false;
    if (["interact_seller", "interact_vuthy", "interact_lok", "interact_boat"].includes(id))
      return s === "market";
    if (id.startsWith("interact_fuse_"))
      return s === "clinic" && !f.get("ep3.fuse." + id.replace("interact_fuse_", ""), false);
    if (id.startsWith("interact_seal_"))
      return s === "clinic" && !f.get("ep3.sealed." + id.replace("interact_seal_", ""), false);
    if (id === "interact_generator") return s === "clinic" || s === "vault";
    if (id === "interact_safe") return s === "vault";
    if (id === "interact_jar") return s === "vault" && f.get("ep3.safe.open", false);
    if (id === "interact_scrape") return s === "memory" && !f.get("ep3.memory.scraped", false);
    if (id === "interact_write") return s === "memory" && f.get("ep3.memory.scraped", false);
    if (id === "interact_purify") return s === "purification" && !f.get("ep3.ritual.water", false);
    if (id.startsWith("interact_candle_"))
      return (
        s === "purification" &&
        f.get("ep3.ritual.water", false) &&
        !f.get("ep3.candle." + id.slice(-1), false)
      );
    if (id === "interact_mother_choice") return s === "purification" && this.progress.candles === 3;
    if (id === "interact_rescue") return s === "escape" || s === "dawn";
    if (id === "interact_stove") return ["clinic", "vault"].includes(s);
    if (id === "interact_calendar_key") return ["clinic", "vault"].includes(s);
    if (id.startsWith("interact_note_"))
      return (
        ["clinic", "vault", "purification"].includes(s) &&
        (id !== "interact_note_letter" || f.get("ep3.safe.open", false))
      );
    return false;
  }
  /** Public production interaction path also used by the isolated journey fixture. */
  async use(id: string): Promise<void> {
    if (!this.allowed(id)) return;
    const g = this.game,
      p = this.progress;
    if (["interact_seller", "interact_vuthy", "interact_lok"].includes(id)) {
      await this.dialog(async () => {
        const who = id.replace("interact_", "") as "seller" | "vuthy" | "lok";
        const text =
          who === "seller"
            ? [
                "The noodle seller sets down her bowl. When she sees the photograph, the smile leaves her face.",
                "Pa Lok. The old man on the raft past the south-west walkway. He rowed a woman there once. Wait until the boy in the town suit has said his piece; he has been asking after you.",
              ]
            : who === "vuthy"
              ? [
                  g.flags.get("ep1.journal.shared", false)
                    ? "You showed me that journal, Sora. I know what you are trying to break. Grandmother told me whose name came first."
                    : "Grandmother told me something. Please, Sora, leave it alone. Let it end the way it was written.",
                  "His cuffs are dry. He keeps looking at the boats. ‘Come home with me. Please.’ I tell him I have to know what happened here.",
                ]
              : [
                  "He looks from the photograph to my face. ‘Kanha’s eyes. I rowed her there in 1920. The baby came before the flood. I did not get them home.’",
                  "‘The water remembers. Stay dry and keep the light bright. If you hear a child walking where there is no child, follow the boards beneath him.’",
                  "He wraps four yellow candles, sanctified water, dry planks and a tarpaulin for the crossing. ‘Say their names if you can: Kanha. Pich. The water has held you long enough.’",
                ];
        if (!g.flags.get("ep3.cinematic." + who, false)) {
          const spoken =
            who === "lok"
              ? [
                  "Kanha’s eyes. I rowed her here in 1920. I did not get her home.",
                  "The water remembers. Keep to dry boards and bright lamps. Say their names: Kanha. Pich. The water has held you long enough.",
                ]
              : who === "vuthy"
                ? [
                    g.flags.get("ep1.journal.shared", false)
                      ? "You showed me the journal. Grandmother told me whose name came first. Please, Sora. Come home."
                      : "Grandmother told me something. Please, Sora, leave it alone. Let it end the way it was written.",
                  ]
                : [
                    "Pa Lok. The old man on the raft past the south-west walkway. He rowed a woman there once.",
                  ];
          await this.cinematics.conversation(who, spoken);
          g.flags.set("ep3.cinematic." + who, true);
        }
        await this.view.show(
          who === "seller" ? "The noodle seller" : who === "vuthy" ? "Vuthy" : "Grandfather Pa Lok",
          text,
          ["Remember his warning"],
        );
        p.meet(who);
        await this.persist();
      });
      this.sync();
      return;
    }
    if (id === "interact_boat") {
      await this.dialog(async () => {
        if (!p.borrowBoat()) {
          await this.view.show(
            "Pa Lok’s boat",
            ["Speak to Pa Lok on the raft and to Vuthy on the main walkway before leaving."],
            ["Step back"],
          );
          return;
        }
        await this.view.show(
          "11:00 PM · The crossing",
          [
            "By dusk, the stalls have closed. Beyond the last mooring, lightning shows the roof of the abandoned clinic.",
            "Alternate A and D to pull the left and right oars. The amber lamp marks the landing.",
          ],
          ["Take the oars"],
        );
        this.crossing = 0;
        this.stroke = "";
        await this.persist("Tonle Sap · Pa Lok’s boat");
      });
      this.sync();
      return;
    }
    const fuse = FUSE_IDS.find((f) => id === "interact_fuse_" + f);
    if (fuse && p.collectFuse(fuse)) {
      this.message("Sora", `The seal stayed dry. ${p.fuses} of three brass fuses.`);
      await this.persist();
      this.sync();
      return;
    }
    const leak = LEAK_IDS.find((l) => id === "interact_seal_" + l);
    if (leak && p.seal(leak)) {
      g.hands.animate("reach");
      this.message("Sora", "Boards across the frame. The tarpaulin is holding back the rain.");
      await this.persist();
      this.sync();
      return;
    }
    if (id === "interact_generator") {
      await this.dialog(async () => {
        if (!p.startPump()) {
          await this.view.show(
            "The drainage pump",
            [
              p.stage === "vault"
                ? "The diesel is running. The cellar is draining."
                : `Three dry fuses and both windows sealed. I have ${p.fuses} fuses and ${p.sealed} sealed windows. The pump cannot keep up with the open leaks.`,
            ],
            ["Close the panel"],
          );
          return;
        }
        await this.view.show(
          "The engine catches",
          [
            "Three brass fuses seat in the porcelain sockets. The crank fights my hand, then the diesel catches. Black water begins to pull through the drainage pipe.",
            "A ramp descends beyond the north-east ward. Below it, an iron safe is coming out of the water.",
          ],
          ["Find the vault"],
        );
        g.flags.set("ep3.checkpoint", "CP2");
        await this.persist("Clinic · Pump running");
      });
      this.sync();
      return;
    }
    if (id.startsWith("interact_note_") || id === "interact_calendar_key") {
      const note = (
        id === "interact_calendar_key" ? "calendar" : id.replace("interact_note_", "")
      ) as NoteId;
      if (!(note in NOTES)) return;
      await this.dialog(async () => {
        await this.view.show(NOTES[note].title, NOTES[note].text.split("\n\n"), [
          "Copy into the sketchbook",
        ]);
        p.read(note);
        await this.persist();
      });
      return;
    }
    if (id === "interact_stove") {
      await this.dialog(async () => {
        await this.view.show(
          "The doctor’s charcoal stove",
          [
            "A little charcoal is still dry inside the sealed tin. Heat seeps through my fingers. Pa Lok left oil and a matchbox beside it.",
            "The child’s footprints end beside the small medical tin. He wanted me to find the dry fuse.",
          ],
          ["Dry your clothes"],
        );
        this.survival.warmth = 1;
        this.survival.wetness = 0;
        this.warnedCold = false;
        g.inventory.add("matches", Math.max(0, 12 - g.inventory.count("matches")));
        g.inventory.add("oil", Math.max(0, 3 - g.inventory.count("oil")));
        await this.persist("Clinic · Attic stove");
      });
      return;
    }
    if (id === "interact_safe") {
      await this.safe();
      this.sync();
      return;
    }
    if (id === "interact_jar") {
      if (!p.takeJar()) return;
      await this.transition(
        VILLAGE.vault,
        "1931 · The name in the earth",
        "The room is dry. My hands are older. Sok’s breathing catches in my throat.",
      );
      g.flags.set("ep3.checkpoint", "CP3");
      await this.persist("Memory · The fourth name");
      this.sync();
      return;
    }
    if (id === "interact_scrape" && p.scrapeName()) {
      g.hands.animate("reach");
      this.message("Sok", "Vuthy. My son. I cannot let it take you.");
      await this.persist();
      this.sync();
      return;
    }
    if (id === "interact_write" && p.writeName()) {
      await this.dialog(async () => {
        await this.view.show(
          "Sora",
          [
            "The stylus stops trembling only when the last stroke is done. Vuthy’s name is gone. Mine lies in its place.",
            "Sok whispers: ‘Forgive me, Kanha. She is yours. Let her be yours, and let my boy live.’",
            "The water returns. A woman stands where his shadow was. Through the wet hair I know my mother’s face. Behind her, a small hand reaches for hers.",
          ],
          ["Let go of the stylus"],
        );
      });
      await this.transition(
        VILLAGE.vault,
        "2:45 AM · The clinic shifts",
        "The stilts are cracking. The upper deck, up the west stair. I have to clean the jar there.",
      );
      g.flags.set("ep3.checkpoint", "CP4");
      await this.persist("Clinic · The mother in the water");
      this.sync();
      return;
    }
    if (id === "interact_purify" && p.pourWater()) {
      g.hands.animate("pour");
      this.message(
        "Sora",
        "Sanctified water, over the shrine earth. Now the three candles, under the eave.",
      );
      await this.persist("Clinic · Upper deck purification");
      this.sync();
      return;
    }
    if (id.startsWith("interact_candle_") && p.lightCandle(Number(id.slice(-1)))) {
      g.hands.animate("strike");
      this.message(
        "Sora",
        p.candles === 3
          ? "The third seal is breaking. Mother is still here."
          : "Shield the wick. Keep it alight.",
      );
      await this.persist();
      this.sync();
      return;
    }
    if (id === "interact_mother_choice") {
      await this.dialog(async () => {
        const choice = await this.view.show(
          "Kanha",
          [
            "The jar is clean. The woman below the rail is still waiting. A little boy holds the hem of her wet cloth.",
            "Pa Lok gave me one more candle. I remember the words: Kanha, I know your name. Pich, take your mother’s hand. The water has held you long enough.",
          ],
          ["Stay · Call their names and free them", "Break the seal and run"],
        );
        if (!p.release(choice === 0)) return;
        this.view.hide();
        await this.cinematics.release(this.kanha, this.pich, choice === 0);
        await this.view.show(
          choice === 0 ? "The water lets go" : "The third seal",
          choice === 0
            ? [
                "For a moment she is Kanha, warm-faced in the light. Her fingers touch my cheek. Pich takes her hand. Neither looks back as the water becomes light.",
                "A sound like a tree splitting comes from beneath the clinic. The landing is empty. My boat’s rope has been cut.",
              ]
            : [
                "The flash tears her into mist. The small footsteps follow her into the water.",
                "The clinic lurches. My boat is gone. On the landing, the cut rope ends in a clean white face.",
              ],
          ["Find the roof route"],
        );
        this.escapeSeconds = 0;
        g.flags.set("ep3.checkpoint", "CP5");
        await this.persist("Clinic · Rooftop escape");
      });
      this.sync();
      return;
    }
    if (id === "interact_rescue" && p.escape()) {
      g.threatActive = false;
      await this.persist("Tonle Sap · Last standing stilt");
      this.sync();
      await this.rescue();
    }
  }
  private async safe(): Promise<void> {
    await this.dialog(async () => {
      while (this.progress.stage === "vault" && !this.game.flags.get("ep3.safe.open", false)) {
        const dials = this.progress.dials;
        this.safeDials.sync(dials);
        const choice = await this.view.show(
          "The iron safe · " + dials.map((v) => KHMER_DIGITS[v]).join("  "),
          [
            "Four brass dials. Each advances through the Khmer numerals. Sok copied the four marks into the admission register and the torn calendar key.",
            "Numerals: " + [...KHMER_DIGITS].map((v, i) => `${v}=${i}`).join("  "),
          ],
          [
            ...dials.map((v, i) => `Turn dial ${i + 1} · ${KHMER_DIGITS[v]}`),
            "Try the handle",
            "Leave the safe",
          ],
        );
        if (choice === 5) break;
        if (choice < 4) this.progress.turnDial(choice);
        else if (!this.progress.openSafe())
          await this.view.show(
            "The handle stops",
            ["The bolt has not moved. Check the copied marks in the notebook."],
            ["Try the dials again"],
          );
      }
      if (this.game.flags.get("ep3.safe.open", false))
        await this.view.show(
          "Inside the safe",
          [
            "A terracotta jar sealed with old earth. Beside it, letters addressed to Vuthy and never sent. The jar is warm in the cold room.",
            "Take the jar from the open safe when you are ready.",
          ],
          ["Open the door"],
        );
      await this.persist();
    });
  }
  private async dialog(action: () => Promise<unknown>): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    const g = this.game;
    g.cutscene = true;
    g.gated.holdStill = true;
    g.closeSketchbook();
    g.satchel.close();
    g.hints.hide();
    g.input.clear();
    document.exitPointerLock();
    try {
      await action();
    } finally {
      this.view.hide();
      g.gated.holdStill = this.progress.stage === "crossing";
      g.cutscene = false;
      this.grace = 5;
      this.busy = false;
    }
  }
  private async transition(
    at: { x: number; y: number; z: number; yaw: number },
    title: string,
    body: string,
  ): Promise<void> {
    await this.dialog(async () => {
      await this.game.fade.to(1, 0.6);
      this.sync();
      this.game.player.teleport(new Vector3(at.x, at.y, at.z), at.yaw);
      this.game.fallGuard.reset(this.game.player.feet);
      await this.game.fade.show({ title, body, button: "Keep going" });
      this.game.fade.hideCard();
      await this.game.fade.to(0, 1.2);
    });
  }
  private message(who: string, text: string): void {
    void this.game.subtitles.say(who, text, 5);
  }
  capture(): SaveData {
    const p = this.progress,
      g = this.game;
    const clock = {
      market: "16:30",
      crossing: "23:00",
      clinic: "23:30",
      vault: "02:30",
      memory: "02:35",
      purification: "03:30",
      escape: "04:30",
      dawn: "05:00",
      complete: "05:00",
    }[p.stage];
    g.flags.set("ep3.clock", clock);
    return {
      saveVersion: 1,
      episode: 3,
      checkpoint: g.flags.get("ep3.checkpoint", "CP0"),
      clock,
      flags: g.flags.toJSON(),
      inventory: g.inventory.toJSON(),
      lamp: this.equipment.lamp.toJSON(),
      playTimeSec: (g.resumedSave?.playTimeSec ?? 0) + (performance.now() - this.startTime) / 1000,
      savedAt: new Date().toISOString(),
    };
  }
  private async persist(location?: string): Promise<void> {
    if (location) {
      this.game.flags.set("checkpoint.location", location);
      const at = this.game.player.feet;
      this.game.flags.set("ep3.spawn.x", at.x);
      this.game.flags.set("ep3.spawn.y", at.y + 0.05);
      this.game.flags.set("ep3.spawn.z", at.z);
    }
    while (true) {
      try {
        const save = this.capture();
        if (location) await this.game.checkpoints.mark(save, location);
        else await this.game.saves.save("autosave", save);
        if (this.progress.stage === "complete") await this.game.saves.save("episode3", save);
        return;
      } catch {
        document.exitPointerLock();
        await this.view.show(
          "The page could not be saved",
          [
            "Your progress is still here. Free browser storage and try again. Your earlier episode archives are kept separately.",
          ],
          ["Retry save"],
        );
        this.view.hide();
      }
    }
  }
  private sync(): void {
    const g = this.game,
      p = this.progress,
      s = p.stage;
    this.lights.setStage(s);
    this.guardian?.root.setEnabled(s === "escape");
    this.safeDials?.sync(p.dials);
    this.equipment.memory = s === "memory";
    this.memoryHands.active = s === "memory";
    g.handsHidden = s === "memory";
    g.gated.holdStill = s === "crossing";
    for (const id of FUSE_IDS)
      this.node("interact_fuse_" + id)?.setEnabled(!g.flags.get("ep3.fuse." + id, false));
    for (const id of LEAK_IDS)
      for (let i = 0; i < 3; i++)
        this.node(`patch_${id}_${i}`)?.setEnabled(g.flags.get(`ep3.sealed.${id}`, false));
    for (let i = 0; i < 3; i++)
      this.node("ritual_flame_" + i)?.setEnabled(g.flags.get(`ep3.candle.${i}`, false));
    this.node("interact_jar")?.setEnabled(s === "vault" && g.flags.get("ep3.safe.open", false));
    this.node("interact_scrape")?.setEnabled(s === "memory");
    this.node("interact_write")?.setEnabled(s === "memory");
    this.node("debt_name")?.setEnabled(s === "memory" && !g.flags.get("ep3.memory.scraped", false));
    for (const m of g.scene.meshes)
      if (m.name.startsWith("sora_moored_boat"))
        m.setEnabled(!["escape", "dawn", "complete"].includes(s));
    this.boat?.setEnabled(s === "crossing");
    this.writtenName?.setEnabled(s === "memory" && g.flags.get("ep3.memory.written", false));
    if (s === "market" || s === "crossing") {
      g.fallGuard.bounds = BOUNDS;
    } else g.fallGuard.bounds = { minX: -30, maxX: 24, minZ: -34, maxZ: 24 };
    this.kanha.setEnabled(s === "purification");
    if (s === "purification") {
      this.kanha.setAbsolutePosition(Vector3.FromArray(RITUAL_FIGURES.mother));
      this.pich.setAbsolutePosition(Vector3.FromArray(RITUAL_FIGURES.child));
      this.kanha.rotation.y = Math.atan2(g.player.feet.x + 13.05, g.player.feet.z - 2.7);
      this.pich.rotation.y = Math.atan2(g.player.feet.x + 12.2, g.player.feet.z - 3.1);
    }
    this.pich.setEnabled(s === "clinic" || s === "purification");
    if (s === "clinic") this.pich.setAbsolutePosition(new Vector3(-10, 3.35, -3));
    this.water?.cellar.position.set(0, g.flags.get("ep3.pump.running", false) ? -1.8 : 0.35, -23);
  }
  private makeBoat(): void {
    const c = new RelicCraft(this.game.scene),
      authored = this.game.scene.getMaterialByName("M_ep3_wood"),
      wood =
        authored instanceof PBRMaterial ? authored : c.surface("rowboat_timber", "#483d2e", "wood");
    this.boat = c.root("rowing_boat", [0, 0, 0]);
    const paths = [-1, -0.55, 0, 0.55, 1].map((side) =>
      Array.from({ length: 25 }, (_, i) => {
        const t = i / 24;
        return new Vector3(
          side * (0.7 * Math.sin(t * Math.PI) ** 0.45 + 0.03),
          Math.abs(side) * 0.4 - 0.1,
          t * 4.8 - 2.4,
        );
      }),
    );
    const hull = CreateRibbon(
      "rowing_boat_hull",
      { pathArray: paths, sideOrientation: 2 },
      this.game.scene,
    );
    hull.material = wood;
    hull.parent = this.boat;
    hull.isPickable = false;
    const inner = CreateRibbon(
      "rowing_boat_inner_planking",
      {
        pathArray: paths.map((path) => path.map((p) => new Vector3(p.x * 0.95, p.y + 0.028, p.z))),
        sideOrientation: 2,
      },
      this.game.scene,
    );
    inner.material = wood;
    inner.parent = this.boat;
    for (const side of [-1, 1]) {
      c.tube(
        this.boat,
        "rounded_gunwale",
        paths[side < 0 ? 0 : 4].map((p) => [p.x, p.y, p.z]),
        0.032,
        wood,
      );
    }
    for (const t of [0.16, 0.3, 0.48, 0.66, 0.82]) {
      const w = 0.7 * Math.sin(t * Math.PI) ** 0.45 + 0.03;
      c.tube(
        this.boat,
        "bent_timber_rib",
        [
          [-w * 0.94, 0.29, t * 4.8 - 2.4],
          [-w * 0.51, 0.11, t * 4.8 - 2.4],
          [0, -0.06, t * 4.8 - 2.4],
          [w * 0.51, 0.11, t * 4.8 - 2.4],
          [w * 0.94, 0.29, t * 4.8 - 2.4],
        ],
        0.019,
        wood,
      );
    }
    for (const z of [-0.9, 0, 1.15])
      c.box(this.boat, "rowing_thwart", [z === 0 ? 1.25 : 1.04, 0.055, 0.24], [0, 0.18, z], wood);
    c.tube(
      this.boat,
      "boat_keel",
      [
        [0, -0.06, -2.2],
        [0, -0.06, 2.2],
      ],
      0.025,
      wood,
    );
    for (const side of [-1, 1]) {
      const oar = c.root("rowing_oar", [side * 0.65, 0.35, 0], this.boat);
      c.tube(
        oar,
        "oar_shaft",
        [
          [0, 0, 0],
          [side * 1.8, -0.15, 0.6],
        ],
        0.025,
        wood,
      );
      c.box(oar, "oar_blade", [0.16, 0.045, 0.55], [side * 1.8, -0.15, 0.8], wood);
      this.oars.push(oar);
    }
    for (const mesh of this.boat.getChildMeshes()) mesh.isPickable = false;
  }
  private makeMemoryTools(): void {
    const c = new RelicCraft(this.game.scene),
      ink = c.mat("debt_written", "#d4b889");
    ink.albedoTexture = c.painted("sora_in_earth", (ctx) => {
      ctx.fillStyle = "#7a6343";
      ctx.fillRect(0, 0, 512, 512);
      ctx.fillStyle = "#2c1710";
      ctx.font = "bold 80px Georgia";
      ctx.textAlign = "center";
      ctx.fillText("SORA", 256, 290);
    });
    const name = CreateGround(
      "sora_written_in_debt",
      { width: 0.65, height: 0.4 },
      this.game.scene,
    );
    name.position.set(-2, -0.525, -24);
    name.material = ink;
    name.isPickable = false;
    this.writtenName = name;
    this.pen = c.root("sok_memory_stylus", [0, 0, 0], this.memoryHands.right.root);
    const wood = c.mat("sok_stylus", "#453425");
    c.tube(
      this.pen,
      "stylus_shaft",
      [
        [0, 0.03, 0],
        [0.02, 0.19, 0.015],
      ],
      0.004,
      wood,
    );
    for (const mesh of this.pen.getChildMeshes()) {
      mesh.renderingGroupId = 1;
      mesh.isPickable = false;
    }
  }
  private update(dt: number): void {
    if (!this.running) return;
    const g = this.game,
      p = this.progress,
      s = p.stage,
      active = !this.paused;
    this.time += dt;
    this.equipment.update(dt);
    this.memoryHands.update(dt, this.equipment);
    this.cinematics.updateAmbient(this.time);
    this.details.update(dt, !["market", "memory", "dawn", "complete"].includes(s));
    if (s === "escape") this.guardian.animate(this.time, 0, 1);
    const memoryVisible =
      s === "memory" &&
      !g.cutscene &&
      !g.notebook.isOpen &&
      !g.satchel.isOpen &&
      !g.sketchbook?.isVisible;
    this.memoryHands.right.root.setEnabled(memoryVisible);
    this.pen.setEnabled(memoryVisible);
    if (memoryVisible) {
      this.memoryHands.right.root.position.set(0.17, -0.21, 0.38);
      this.memoryHands.right.root.rotation.set(-0.7, 0, -0.3);
      this.memoryHands.right.update(dt, "drawing");
    }
    const storm = !["market", "memory", "dawn", "complete"].includes(s);
    this.water.update(
      dt,
      p.flags.get("ep3.pump.running", false) && s === "vault" ? -1.8 : s === "memory" ? -1.85 : 0.5,
      this.spirit.state === "ripple" || this.spirit.state === "rising"
        ? this.spirit.position
        : null,
      storm,
    );
    this.wetEdge.style.setProperty("--wetness", String(this.survival.wetness * 0.38));
    this.wetEdge.classList.toggle("shivering", this.survival.shivering && active);
    if (!active) return;
    this.activeSeconds += dt;
    this.grace = Math.max(0, this.grace - dt);
    this.strokeAge += dt;
    if (s === "crossing") {
      if (this.crossing > 0) this.crossing = Math.min(1, this.crossing + dt * 0.0035);
      const t = this.crossing,
        at = new Vector3(
          -74 + t * 78.5,
          -0.35 + Math.sin(this.time * 1.8) * 0.045,
          15 + Math.sin(t * Math.PI) * 8,
        );
      this.boat.position.set(at.x, -0.09 + Math.sin(this.time * 1.8) * 0.045, at.z);
      this.boat.rotation.set(
        0.015 * Math.sin(this.time * 1.4),
        Math.PI / 2,
        0.035 * Math.sin(this.time * 1.9),
      );
      this.oars.forEach((o, i) => {
        o.rotation.y = Math.sin(Math.min(1, this.strokeAge) * Math.PI) * (i === 0 ? -1 : 1) * 0.6;
      });
      g.player.teleport(at, Math.PI / 2);
      if (this.crossing >= 1) {
        p.dock();
        this.sync();
        g.player.teleport(
          new Vector3(VILLAGE.clinic.x, VILLAGE.clinic.y, VILLAGE.clinic.z),
          VILLAGE.clinic.yaw,
        );
        g.fallGuard.reset(g.player.feet);
        g.flags.set("ep3.checkpoint", "CP1");
        void this.dialog(() => this.persist("Clinic · Landing lamp"));
        this.message("Pa Lok", "Above the water, girl. And keep that light bright.");
      }
      return;
    }
    const feet = g.player.feet,
      warm = VILLAGE.warmth.some(
        (l) => Math.abs(feet.y - l.y) < 0.7 && Math.hypot(feet.x - l.x, feet.z - l.z) < l.radius,
      );
    const inClinic = Math.abs(feet.x) < 12 && feet.z > -11 && feet.z < 10;
    const inCellar = Math.abs(feet.x) < 7.2 && feet.z < -18.5 && feet.z > -28;
    const waterLevel = inCellar ? this.water.cellar.position.y : inClinic ? this.flood : -0.08;
    const depth = Math.max(0, waterLevel - feet.y);
    const vulnerable = (s === "clinic" || s === "vault" || s === "purification") && depth > 0.12;
    const sheltered = inClinic || (feet.y > 3 && feet.x < -3 && feet.x > -12 && feet.z < 4);
    if (["clinic", "vault", "purification", "escape"].includes(s))
      this.survival.update(dt, { depth, rain: storm, warm, sheltered });
    const speed = 1 - this.survival.wetness * 0.18;
    g.player.config.walkSpeed = 1.6 * speed;
    g.player.config.hurrySpeed = 3.4 * speed;
    if (s === "clinic") this.flood = Math.min(0.57, this.flood + dt * (2 - p.sealed) * 0.00035);
    else if (s === "purification" || s === "escape")
      this.flood = Math.min(0.85, this.flood + dt * 0.002);
    this.water.wards.position.y = this.flood;
    this.spirit.update(dt, feet, vulnerable, warm);
    const rising = this.spirit.state === "rising" && vulnerable;
    this.kanha.setEnabled(rising || (s === "purification" && feet.y > 3));
    this.kanha.setAbsolutePosition(
      s === "purification" && feet.y > 3
        ? Vector3.FromArray(RITUAL_FIGURES.mother)
        : new Vector3(
            this.spirit.position.x,
            -1.1 + Math.min(1, this.activeSeconds * 0.2),
            this.spirit.position.z,
          ),
    );
    const spiritAt = this.kanha.getAbsolutePosition();
    this.kanha.rotation.y = Math.atan2(feet.x - spiritAt.x, feet.z - spiritAt.z);
    this.kanha.rotation.z = 0;
    if (s === "clinic") {
      const t = (this.activeSeconds % 24) / 24;
      this.pich.setAbsolutePosition(new Vector3(-10 + t * 4, 3.35, -3 - t * 4));
      this.pich.setEnabled(t < 0.22);
    } else if (s === "purification") {
      this.pich.setEnabled(true);
      this.pich.setAbsolutePosition(Vector3.FromArray(RITUAL_FIGURES.child));
      this.pich.rotation.y = Math.atan2(feet.x + 12.2, feet.z - 3.1) - 0.15;
    }
    const danger = vulnerable
      ? Math.max(
          0,
          1 - Math.hypot(feet.x - this.spirit.position.x, feet.z - this.spirit.position.z) / 12,
        )
      : 0;
    g.threatActive = active && (s === "escape" || danger > 0.35);
    g.atmosphere.mood.fear = s === "escape" ? 0.75 : danger * 0.8;
    this.sounds.update(dt, s, this.spirit.position, danger, g.flags.get("ep3.pump.running", false));
    if (this.spirit.state === "ripple" && !this.warnedWake) {
      this.warnedWake = true;
      this.message("Sora", "No wind. Those rings are coming toward me. The raised boards.");
    }
    if (this.survival.shivering && !this.warnedCold) {
      this.warnedCold = true;
      this.message(
        "Sora",
        "I cannot feel my fingers. The stove, upstairs. Or one of the wall lamps.",
      );
    }
    if (s === "escape") {
      this.escapeSeconds += dt;
      for (const [i, beam] of this.looseBeams.entries())
        beam.rotation.y =
          Math.sin(this.escapeSeconds * 1.7 + i) *
          (0.08 + Math.min(0.25, this.escapeSeconds * 0.002));
      if (this.escapeSeconds > 20 && !g.flags.get("ep3.escape.warned", false)) {
        g.flags.set("ep3.escape.warned", true);
        this.message(
          "Sora",
          "The boat is gone. North end of the upper veranda. Across the roofs to the last stilt.",
        );
      }
    }
    if (
      !this.catching &&
      this.grace <= 0 &&
      (this.spirit.catches(feet, vulnerable, warm) ||
        this.survival.collapsed ||
        (["clinic", "purification"].includes(s) && !inCellar && feet.y < -1.2) ||
        (s === "escape" && (this.escapeSeconds > 210 || feet.y < 1)))
    ) {
      this.catching = true;
      g.atmosphere.scare();
      void g.retryFromCheckpoint();
    }
  }
  private async rescue(): Promise<void> {
    await this.dialog(async () => {
      await this.view.show(
        "5:00 AM · Pa Lok’s raft",
        [
          "His lantern rises from the mist beneath the last stilt. ‘I could not sleep. Not again.’",
          "On the raft he tells me a young man in a town suit paid him to keep me from the clinic, and asked where I would tie the boat. I know whose cuffs were dry.",
          "He presses his old compass into my hand. ‘Where you are going, you will need to know which way is home.’",
        ],
        ["Take the brass compass"],
      );
      this.progress.finish();
      this.sync();
      await this.persist("Tonle Sap · Third seal broken");
    });
    await this.ending();
  }
  private async ending(): Promise<void> {
    await this.dialog(async () => {
      await this.view.show(
        "The third seal",
        [
          "Inside the jar’s seal, wrapped in oilcloth: burnt rubber. Compagnie des Caoutchoucs de Kampong Cham, 1928. Blood seeps east across Sok’s map.",
          "I fill the fifth circle. Two nights remain.",
          this.game.flags.get("ep3.mother.freed", false)
            ? "Kanha and Pich are free. Her voice will remember me in the last night’s Water trial."
            : "The seal is broken. My mother remains in the water.",
        ],
        ["Close the map"],
      );
      while (true) {
        const action = await this.view.show(
          "The Unbroken Debt",
          [
            "Episode 3 · The Drowned Village",
            "Third seal broken · Night 5 of 7",
            `Records found: ${this.progress.lore.length} / 5 · Respect: ${this.game.flags.get("series.respect", 0)}`,
            "Next: Episode 4 · The Rubber Plantation",
            "Created by Rithy Bondeth. Babylon.js · Havok. Full third-party credits are on the title screen.",
          ],
          ["Return to title", "Export completion save"],
        );
        if (action === 0) {
          location.assign(import.meta.env.BASE_URL);
          return;
        }
        const code = await encodeSaveCode(this.capture()),
          url = URL.createObjectURL(new Blob([code], { type: "text/plain" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = "boon-sop-episode-3.save.txt";
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    });
  }
}
