import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import type { VillageLights } from "../act1/VillageLights";
import { RitualProgress, RITUAL_SECONDS } from "./RitualProgress";
import { RelicCraft } from "./RelicCraft";
import { CP6_FEET, RITUAL_BURNER } from "../data/ritual";
import { TENT_FLAME_MESH } from "../data/arrival";
import { FAILING_LAMPS } from "../data/desk";
import { coldGust } from "../audio/actTwoSounds";
import { matchStrike } from "../audio/vigilSounds";
import { ritualDrone, spiritShriek } from "../audio/actThreeSounds";
import { rattlingBreath, seededRandom } from "../../../audio/synth";

/** A3-07–08. The player keeps mouse look while movement and other interactions are gated. */
export class FinalRitual {
  readonly progress: RitualProgress;
  readonly burner;
  readonly spare;
  private readonly token;
  private readonly flame;
  private readonly shadow;
  private readonly fire: PointLight;
  private readonly sounds = new Map<string, StaticSound>();
  private finishing = -1;
  private midpoint = false;
  constructor(
    private readonly game: Game,
    private readonly area: Area,
    private readonly lights: VillageLights,
    private readonly save: () => Promise<unknown>,
  ) {
    this.progress = new RitualProgress(game.flags, game.inventory);
    const craft = new RelicCraft(game.scene);
    this.burner = craft.root("ritual_burner", [0, 0, 0]);
    const brass = craft.mat("ritual_brass", "#93713b", 0.65, 0.7);
    // A thin rim over the existing main burner provides a precise interaction target.
    craft.ring(this.burner, "ritual_burner_rim", 0.41, 0.025, [0, 0.575, -3.55], brass);
    this.token = craft.cylinder(
      this.burner,
      "ritual_token",
      0.095,
      0.009,
      [0, 0.587, -3.55],
      brass,
    );
    const ember = craft.mat("ritual_ember", "#f2a34b");
    ember.emissiveColor.set(1, 0.25, 0.025);
    this.flame = craft.sphere(
      this.burner,
      "ritual_flame",
      [0.055, 0.15, 0.055],
      [0, 0.67, -3.55],
      ember,
    );
    this.spare = craft.root("ritual_spare", [0, 0, 0]);
    const altar = area.level.interactables.find((m) => m.name === "interact_incense_bundle");
    const at = altar?.position ?? new Vector3(-0.45, 3.62, -17.55);
    craft.box(
      this.spare,
      "ritual_spare_match",
      [0.12, 0.04, 0.08],
      [at.x + 0.15, at.y + 0.035, at.z],
      brass,
    );
    const shade = craft.mat("ritual_shadow", "#09090a");
    shade.alpha = 0.78;
    this.shadow = craft.root("ritual_shadow_on_tent", [0, 0, -6.85]);
    craft.sphere(this.shadow, "ritual_shadow_head", [0.32, 0.45, 0.015], [0, 1.85, 0], shade);
    craft.sphere(this.shadow, "ritual_shadow_body", [0.65, 1.6, 0.015], [0, 0.95, 0], shade);
    this.fire = new PointLight("ritual_fire", RITUAL_BURNER.clone(), game.scene);
    this.fire.diffuse.set(1, 0.35, 0.06);
    this.fire.range = 3;
    this.fire.renderPriority = 9;
    for (const mesh of this.shadow.getChildMeshes()) mesh.isPickable = false;
    this.fire.intensity = 0;
    game.interaction.add(
      "interact_ritual_burner",
      [
        ...this.burner.getChildMeshes(),
        ...area.container.meshes.filter((mesh) => /^main_burner/.test(mesh.name)),
      ],
      { outline: false },
    );
    game.interaction.add("interact_ritual_spare", this.spare, { outline: false });
    game.bus.on("interact:use", ({ id }) => this.use(id));
    game.bus.on("interact:focus", ({ id }) => {
      if (!this.progress.ready || this.progress.broken || this.progress.active) return;
      if (id === "interact_ritual_burner")
        game.hints.show(this.progress.placed ? "hint.ritualLight" : "hint.ritualPlace", 4);
      if (id === "interact_ritual_spare") game.hints.show("hint.ritualSpare", 4);
    });
    this.apply();
    if (this.progress.broken) this.relight(1);
  }
  private get handsFree(): boolean {
    const g = this.game;
    return (
      !g.cutscene &&
      !g.threatActive &&
      !g.hiding &&
      !g.inspecting &&
      !g.satchel.isOpen &&
      !g.sketchbook?.isOpen &&
      !g.sketchbook?.isBusy
    );
  }
  private use(id: string): void {
    const g = this.game,
      p = this.progress;
    if (!this.handsFree || !p.ready || p.broken) return;
    if (id === "interact_ritual_spare") {
      if (p.spare()) {
        this.apply();
        void this.save();
        g.hints.show("note.ritualSpareTaken", 5);
      }
      return;
    }
    if (id !== "interact_ritual_burner" || Vector3.Distance(g.player.feet, CP6_FEET) > 1.8) return;
    if (!p.placed) {
      if (!p.place()) return;
      g.bus.emit("sequence:end", { id: "A3-06" });
      this.apply();
      void this.save();
      g.hints.show("hint.ritualLight", 7);
      return;
    }
    if (!g.inventory.has("blessed_matches")) {
      g.hints.show("note.ritualNoMatches", 8);
      return;
    }
    // Start facing the burner. The 100-degree limit is measured horizontally toward it.
    if (Math.abs(this.angle()) > 0.5 || !p.start()) return;
    g.stopInspecting();
    g.gated.holdStill = true;
    g.threatActive = true;
    this.midpoint = false;
    g.hands?.animate("strike");
    this.sounds.get("match")?.play();
    this.sounds.get("breath")?.play();
    this.sounds.get("mantra")?.play();
    g.bus.emit("sequence:start", { id: "A3-07" });
    void g.subtitles.say("Sora", "I give it back. Whatever he took, I give it back.", 7);
    // Persist the cost before any success or failure, even if the browser closes mid-hold.
    this.apply();
    void this.save();
  }
  private angle(): number {
    const eye = this.game.camera.globalPosition;
    const target = RITUAL_BURNER.subtract(eye);
    const forward = this.game.camera.getForwardRay().direction;
    return Math.atan2(
      forward.x * target.z - forward.z * target.x,
      forward.x * target.x + forward.z * target.z,
    );
  }
  update(dt: number): void {
    const g = this.game,
      p = this.progress;
    if (p.active) {
      // UnderHouseHunt also owns threatActive outside its area; reassert our gate each frame.
      g.threatActive = true;
      const paused = g.cutscene || document.hidden || !g.input.pointerLocked;
      const result = p.update(dt, this.angle(), paused);
      if (!this.midpoint && p.elapsed >= RITUAL_SECONDS / 2) {
        this.midpoint = true;
        void g.subtitles.say("Presence", "…Sora.", 4);
      }
      this.shadow.scaling.setAll(0.65 + (p.elapsed / RITUAL_SECONDS) * 0.8);
      g.hints.show("hint.ritualHold", 1);
      if (result) {
        this.sounds.get("breath")?.stop();
        this.sounds.get("mantra")?.stop();
        g.gated.holdStill = false;
        g.threatActive = false;
        g.bus.emit("sequence:end", { id: "A3-07" });
        if (result === "failed")
          g.hints.show(
            g.inventory.has("blessed_matches") ? "note.ritualFailed" : "note.ritualNoMatches",
            8,
          );
        else {
          this.finishing = 0;
          this.sounds.get("wind")?.play();
          this.sounds.get("screech")?.play();
          g.bus.emit("sequence:start", { id: "A3-08" });
        }
        void this.save();
      }
    }
    if (this.finishing >= 0) {
      this.finishing += dt;
      this.relight(Math.min(1, this.finishing / 8));
      if (this.finishing >= 8) {
        this.finishing = -1;
        g.hints.show("note.sealBroken", 10);
        g.bus.emit("sequence:end", { id: "A3-08" });
      }
    } else if (p.broken) this.relight(1);
    this.apply();
  }
  private apply(): void {
    const p = this.progress;
    this.burner.setEnabled(p.ready && !p.broken);
    this.token.setEnabled(p.placed && !p.broken);
    this.flame.setEnabled(p.active);
    this.shadow.setEnabled(p.active);
    this.spare.setEnabled(
      p.placed && !p.broken && !p.active && !this.game.inventory.has("blessed_matches"),
    );
    this.fire.intensity = p.active ? 2 + Math.sin(p.elapsed * 17) * 0.2 : 0;
  }
  private relight(amount: number): void {
    this.lights.hangingLevel = 1;
    this.lights.tentLevel = 1;
    this.lights.flames.forEach((light, i, all) => {
      this.lights.practicalLevels.set(
        light.name,
        Math.max(0, Math.min(1, amount * all.length - i)),
      );
    });
    for (const mesh of this.area.container.meshes) {
      if (
        TENT_FLAME_MESH.test(mesh.name) ||
        FAILING_LAMPS.some((lamp) => lamp.mesh.test(mesh.name))
      ) {
        mesh.setEnabled(true);
        mesh.visibility = amount;
      }
    }
  }
  async makeSounds(): Promise<void> {
    const a = this.game.audio;
    if (!a) return;
    const rate = a.context.sampleRate;
    // Wordless timing stand-in: no invented ceremonial text. The licensed smot remains in NightLife.
    const mantra = ritualDrone(rate, seededRandom(1913));
    const screech = spiritShriek(rate, seededRandom(1914));
    const breath = rattlingBreath(rate, seededRandom(1910));
    for (const [id, data, at, loop] of [
      ["match", matchStrike(rate, seededRandom(1912)), RITUAL_BURNER, false],
      ["mantra", mantra, RITUAL_BURNER, true],
      ["breath", breath, CP6_FEET.add(new Vector3(0, 1.55, 0.6)), true],
      ["screech", screech, CP6_FEET.add(new Vector3(0, 1.55, 1)), false],
      ["wind", coldGust(rate, seededRandom(1911)), RITUAL_BURNER, false],
    ] as const)
      this.sounds.set(
        id,
        await a.spatialSound(`ritual_${id}`, a.buffer(data, rate), "threat", at, {
          loop,
          minDistance: 1,
          volume: 0.65,
        }),
      );
  }
}
