/** Earned saves only: no seeded story flags or inventory. Scripted movement / input, real runtime. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import type { Prologue } from "../../src/episodes/ep1/prologue/Prologue";
import { KANHA_LAYOUT, SLOTS } from "../../src/episodes/ep1/data/betel";
import { CP3_FEET } from "../../src/episodes/ep1/data/walker";
import { CP4_FEET } from "../../src/episodes/ep1/data/desk";
import { CP5_FEET, JARS } from "../../src/episodes/ep1/data/hunt";
import { CP6_FEET, CP6_YAW, RITUAL_BURNER } from "../../src/episodes/ep1/data/ritual";
import { CHEST_ITEMS } from "../../src/episodes/ep1/act3/ChestProgress";
const params = new URLSearchParams(location.search),
  step = params.get("step") ?? (params.has("continue") ? "act1" : "start");
const logKey = "boon-sop-journey-report";
if (step === "start") sessionStorage.removeItem(logKey);
const output = document.getElementById("results")!;
output.textContent = sessionStorage.getItem(logKey) ?? "";
const report = (s: string) => {
  output.textContent += `${s}\n`;
  sessionStorage.setItem(logKey, output.textContent);
  console.info(`[Journey] ${s}`);
};
const assert = (ok: unknown, s: string) => {
  if (!ok) throw new Error(s);
  report(`PASS ${s}`);
};
const pause = (ms = 200) => new Promise<void>((r) => setTimeout(r, ms));
async function wait(test: () => boolean, label: string, ms = 90000) {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > ms) throw new Error(`Timeout: ${label}`);
    await pause(100);
  }
}
window.addEventListener("unhandledrejection", (e) => report(`UNHANDLED ${String(e.reason)}`));
async function run() {
  if (!import.meta.env.DEV) return;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice()),
    saves = new SaveStore(undefined, "boon-sop-full-journey");
  Object.defineProperty(game, "saves", { value: saves });
  if (step === "start") {
    await saves.clear("autosave");
    await saves.clear("episode1");
    await saves.clear("checkpoint");
    for (const key of ["road-caught", "walker-caught", "hunt-caught", "hunt-retry-verified"])
      sessionStorage.removeItem(`journey-${key}`);
  }
  const restore = params.get("restore");
  if (restore) {
    if (!/^CP[1-6]$/.test(restore)) throw new Error("Unknown earned checkpoint");
    const earned = (await new SaveStore(undefined, `boon-sop-journey-${restore}`).load("slot1"))
      .save;
    if (!earned) throw new Error(`No earned ${restore} snapshot`);
    await saves.save("autosave", earned);
    report(`RESTORE earned ${restore} snapshot for regression replay`);
  }
  // Keep full gameplay timing; accelerate subtitle-only arrival exchanges.
  const say = game.subtitles.say.bind(game.subtitles);
  game.subtitles.say = (speaker, text, seconds) =>
    say(speaker, text, speaker === "Sok" ? seconds : seconds * 0.1);
  const use = (id: string) => game.bus.emit("interact:use", { id });
  const key = (code: string) => window.dispatchEvent(new KeyboardEvent("keydown", { code }));
  // A timer can finish before the browser renders a teleported camera. Wait for
  // real frames so inspection and picking use its current position and view.
  async function frames(count = 2) {
    for (let i = 0; i < count; i++)
      await new Promise<void>((done) => game.scene.onAfterRenderObservable.addOnce(() => done()));
  }
  async function free() {
    game.stopInspecting();
    game.satchel.close();
    await wait(() => !game.sketchbook?.isBusy, "book animation");
    game.sketchbook?.close();
    await wait(() => !game.gated.reading, "book closes");
  }
  async function aim(feet: Vector3, at: Vector3, radius = 0.4, closeMenus = true) {
    if (closeMenus) await free();
    game.player.teleport(feet);
    await pause(300);
    await frames();
    // Havok can retain small idle motion on contact; do not wait indefinitely
    // for an almost-zero speed when the character is already standing still.
    await pause(500);
    await frames();
    game.inspectObject(at, radius);
    if (step === "start") report(`AIM ${at.toString()}`);
    await pause(350);
    await frames();
    if (closeMenus && (game.sketchbook?.isOpen || game.sketchbook?.isBusy)) {
      await free();
      await pause(400);
      await free();
      game.inspectObject(at, radius);
      await pause(350);
      await frames();
    }
  }
  async function ray(id: string) {
    if (game.interaction.focus !== id)
      report(
        `DIAG feet=${game.player.feet.toString()} eye=${game.camera.globalPosition.toString()} forward=${game.camera.getForwardRay().direction.toString()} hit=${game.scene.pickWithRay(game.camera.getForwardRay(1.8))?.pickedMesh?.name}`,
      );
    assert(game.interaction.focus === id, `interaction ray: ${id} (${game.interaction.focus})`);
    if (id === "interact_telephone" && params.has("manual-phone")) {
      report("MANUAL PHONE READY: press E on the focused ringing phone");
      await wait(() => game.flags.get("ep1.phone.answered", false), "physical E answers phone");
    } else {
      key("KeyE");
      window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyE" }));
    }
    await pause(100);
  }
  async function readAll() {
    while (document.querySelector(".document-reader:not([hidden])")) {
      document
        .querySelector<HTMLButtonElement>(
          ".document-reader:not([hidden]) footer button:nth-of-type(2)",
        )!
        .click();
      await pause(100);
    }
  }
  async function checkpoint(id: string, next: string) {
    await wait(() => !saves.saving, "save writes");
    const saved = (await saves.load("autosave")).save;
    assert(saved?.checkpoint === id, `${id} written from earned progress`);
    await new SaveStore(undefined, `boon-sop-journey-${id}`).save("slot1", saved!);
    report(`RELOAD ${id} → ${next}`);
    location.replace(`?continue&step=${next}`);
  }
  async function button(label: string) {
    await wait(
      () =>
        [
          ...document.querySelectorAll<HTMLButtonElement>(".resolution button,.story-card button"),
        ].some((b) => b.textContent === label && !b.disabled),
      `button ${label}`,
    );
    [...document.querySelectorAll<HTMLButtonElement>(".resolution button,.story-card button")]
      .find((b) => b.textContent === label && !b.disabled)!
      .click();
    await pause(200);
  }
  report(`START ${step}; click to begin`);
  await game.start();
  if (game.flags.get("ep1.travel.pending", false)) {
    report("PASS studio departure resumes the rainy taxi; click to begin the full 72-second ride");
    return;
  }
  await wait(() => !game.cutscene, "start", 300000);
  if (step === "start") {
    const p = (window as unknown as { prologue: Prologue }).prologue;
    assert(!!p, "fresh game starts in studio, without seeded progress");
    const object = (id: string) => {
      const n = game.scene.getMeshByName(id) ?? game.scene.getTransformNodeByName(id);
      if (!n) throw new Error(`missing studio ${id}`);
      return n.getAbsolutePosition();
    };
    await aim(
      new Vector3(object("interact_illustration").x, 0, object("interact_illustration").z - 0.8),
      object("interact_illustration"),
    );
    await ray("interact_illustration");
    await wait(() => game.flags.get("ep1.illustration.inked", false), "ink line");
    await aim(
      new Vector3(object("interact_telephone").x + 0.9, 0, object("interact_telephone").z),
      object("interact_telephone"),
    );
    assert(
      game.interaction.focus === "interact_telephone",
      "quiet phone can be focused before packing",
    );
    key("KeyE");
    window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyE" }));
    assert(
      document.querySelector(".story-hint.shown")?.textContent?.includes("satchel"),
      "using the quiet phone identifies the missing satchel instead of silently ignoring E",
    );
    await aim(
      new Vector3(object("interact_drawer").x, 0, object("interact_drawer").z - 0.8),
      object("interact_drawer"),
    );
    await ray("interact_drawer");
    await pause(600);
    await wait(
      () => game.interaction.focus === "matchbox",
      "drawer opening reveals and focuses matchbox",
    );
    key("KeyE");
    window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyE" }));
    assert(
      game.inventory.count("matches") === 10,
      "E takes ten matches directly from the opened drawer without precision aiming",
    );
    await frames();
    for (const id of ["letters", "interact_satchel", "interact_sketchbook", "interact_lamp"]) {
      await free();
      const n =
        game.scene.getMeshByName(id === "letters" ? "letters_string" : id) ??
        game.scene.getTransformNodeByName(id);
      if (!n) throw new Error(`missing pickup ${id}`);
      const bounds = n.getHierarchyBoundingVectors(true);
      const at = Vector3.Center(bounds.min, bounds.max);
      const feet = at.add(
        id === "interact_satchel"
          ? new Vector3(0, 0, 0.9)
          : new Vector3(id === "interact_lamp" ? 1.3 : -0.85, 0, 0),
      );
      feet.y = 0;
      await aim(feet, at, 0.25);
      await ray(id);
      await pause(id === "letters" ? 800 : 200);
    }
    await free();
    assert(game.inventory.count("matches") === 10, "prologue supplies ten matches");
    assert(game.inventory.count("letters") === 1, "letters collected once");
    await wait(() => game.flags.has("ep1.clock.stopped"), "ink spill");
    await wait(() => game.sketchbook?.isOpen === true, "automatic ink-blot entry");
    report("PASS ink-blot entry opens the sketchbook automatically");
    await wait(() => Reflect.get(p, "ringing") === true, "phone rings with notebook untouched");
    await wait(
      () => !game.sketchbook?.isOpen && !game.sketchbook?.isBusy,
      "ringing phone puts away the automatic sketchbook",
      5000,
    );
    await aim(
      new Vector3(object("interact_telephone").x + 0.9, 0, object("interact_telephone").z),
      object("interact_telephone"),
      0.4,
      false,
    );
    report("PASS ringing phone is reachable without the test closing the sketchbook");
    await ray("interact_telephone");
    if (!params.has("manual-phone"))
      assert(
        game.scene.getTransformNodeByName("telephone_earpiece")?.isEnabled() === false,
        "answering lifts the rebuilt receiver from its hook",
      );
    await wait(() => game.flags.get("ep1.phone.answered", false), "phone call");
    assert(
      game.scene.getTransformNodeByName("telephone_earpiece")?.isEnabled() === true,
      "completed call returns the rebuilt receiver to its hook",
    );
    // Reproduce storage failure at the first real checkpoint.
    const original = saves.saveCheckpoint.bind(saves);
    let failed = false;
    saves.saveCheckpoint = async (data) => {
      if (!failed && data.flags["ep1.travel.pending"] === true) {
        failed = true;
        report("INJECT departure storage failure");
        throw new Error("QA departure storage unavailable");
      }
      return original(data);
    };
    await aim(
      new Vector3(object("interact_door").x + 0.9, 0, object("interact_door").z),
      object("interact_door"),
    );
    await ray("interact_door");
    await button("Retry save");
    report("PASS departure storage failure recovered");
    return;
  }
  const act = (window as unknown as { act: ActOne }).act;
  assert(!!act, "earned save resumes village");
  const cp = game.resumedSave?.checkpoint;
  assert(act.vigil.lamp.oil >= 0.49, `${cp} guarantees half a tank on reload`);
  if (step === "act1") {
    assert(cp === "CP1" && game.inventory.count("matches") === 10, "CP1 retains the prologue kit");
    assert(!act.early.active && !game.threatActive, "arrival has no chase or cart obstacle");
    await new SaveStore(undefined, "boon-sop-journey-CP1").save("slot1", game.resumedSave!);
    key("KeyF");
    await wait(() => act.vigil.lamp.burning, "first lamp match");
    assert(game.inventory.count("matches") === 9, "first light consumes one ordinary match");
    game.player.teleport(new Vector3(0, 0, -2), Math.PI);
    await wait(() => !game.cutscene, "arrival road dialogue");
    await aim(new Vector3(2.7, 0, -1.85), new Vector3(2.7, 0.79, -2.6));
    await ray("interact_arrival_note");
    await readAll();
    await aim(new Vector3(1.8, 2.5, -17.2), new Vector3(2.65, 3.7, -17.2));
    await ray("interact_arrival_phone");
    await wait(
      () => game.flags.get("ep1.arrival.callComplete", false) && !game.cutscene,
      "phone duties",
    );
    await aim(new Vector3(-0.65, 2.5, -20.6), new Vector3(-0.65, 3.614, -21.5));
    await ray("interact_blessed_matches");
    await free();
    await act.beats.saveProgress();
    assert(
      (await saves.load("autosave")).save?.checkpoint === "CP1",
      "Act I autosaves keep CP1 until the opening",
    );
    assert(
      (await saves.load("autosave")).save?.clock === "23:30",
      "Act I autosave retains CP1 clock",
    );
    use("interact_door_sok");
    assert(!!game.scene.getTransformNodeByName("col_door_sok_body"), "Sok door locked before CP2");
    for (const id of [
      "interact_sewing_box",
      "interact_shed_door",
      "interact_land_deed",
      "interact_kanha_photo",
      "interact_betel_tray",
      "interact_betel_leaves",
      "interact_areca_nut",
      "interact_lime_pot",
      "interact_altar_candle",
      "interact_incense_bundle",
    ]) {
      await free();
      use(id);
      await pause(100);
    }
    use("interact_altar");
    const order = ["betel", "areca", "lime", "candle", "incense"],
      held = new Set(order);
    // A wrong placement must be correctable before the final arrangement.
    for (const slot of SLOTS) {
      const available = order.filter((item) => held.has(item));
      for (let k = 0; k <= available.indexOf(KANHA_LAYOUT[slot]); k++) use(`betel_slot_${slot}`);
      held.delete(KANHA_LAYOUT[slot]);
    }
    await wait(() => game.flags.get("ep1.betel.done", false), "blessing");
    assert(
      game.inventory.count("blessed_matches") === 3,
      "offering preserves three prepared blessed matches",
    );
    // The 11-minute upkeep cycle is accelerated; all later encounters use production time.
    act.beats.progress.update(660);
    await free();
    game.player.teleport(new Vector3(0, 0, -2), Math.PI);
    await wait(() => act.early.active, "listening passage after the vigil");
    if (act.vigil.lamp.burning) key("KeyF");
    key("KeyC");
    await wait(
      () => game.flags.get("ep1.early.complete", false) && !act.early.active,
      "presence passes the gate",
      60000,
    );
    window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyC" }));
    assert(game.checkpoints.last?.flags["ep1.early.complete"] === true, "passage completion saved");
    await wait(() => game.flags.get("ep1.sok.unlocked", false) && !game.cutscene, "Act II opening");
    await checkpoint("CP2", "investigate");
    return;
  }
  if (step === "investigate") {
    assert(cp === "CP2" && act.lights.hangingLevel === 0, "CP2 restores extinguished tent");
    assert(!game.scene.getTransformNodeByName("col_door_sok_body"), "CP2 restores open doorway");
    const inv = act.investigation,
      m = inv.models;
    const journalAt = m.journal.position;
    await aim(
      new Vector3(journalAt.x + 1.45, 2.5, journalAt.z + 0.7),
      journalAt.add(new Vector3(0, -0.05, 0)),
    );
    if (!game.flags.get("ep1.journal.plankOpen", false)) {
      await ray("interact_sok_wall_plank");
      await pause(1100);
    }
    if (!game.flags.get("ep1.journal.found", false)) {
      game.inspectObject(m.papers.getAbsolutePosition().add(new Vector3(0.01, -0.05, 0)));
      await pause(350);
      await ray("interact_sok_journal");
      await readAll();
    }
    await wait(() => inv.started, "record awakening");
    await free();
    const at = m.gramophone.position;
    await aim(new Vector3(at.x + 0.85, 2.5, at.z + 1.1), at.add(new Vector3(0, 1.05, 0.1)), 0.6);
    use("interact_gramophone");
    report(
      `GOVERNOR tuning=${inv.tuning} rpm=${inv.governor.rpm} distanceToFloorRoot=${Vector3.Distance(game.camera.globalPosition, m.gramophone.position)}`,
    );
    for (let n = inv.governor.rpm; n < 78; n++) key("ArrowRight");
    assert(inv.governor.rpm === 78, "reachable gramophone accepts governor input");
    await wait(() => inv.governor.solved, "governor hold");
    await wait(() => game.flags.get("ep1.gramophone.heard", false), "full Sok recording", 180000);
    report("PASS all four Sok paragraphs played");
    await free();
    game.player.teleport(CP3_FEET);
    await wait(() => act.walker.armed && !saves.saving, "CP3 armed");
    await checkpoint("CP3", "walker");
    return;
  }
  if (step === "walker" || step === "desk") {
    assert(
      cp === "CP3" && Vector3.Distance(game.player.feet, CP3_FEET) < 0.3,
      "CP3 resumes inside Sok’s room",
    );
    if (!game.flags.get("ep1.walker.complete", false)) {
      const w = act.walker;
      game.player.teleport(new Vector3(-2.2, 2.5, -13.45));
      await wait(() => w.brain.active, "walker starts");
      const matches = game.inventory.count("matches");
      if (
        !sessionStorage.getItem("journey-walker-caught") ||
        game.flags.get("ep1.opening.version", 0) < 2
      ) {
        game.inventory.add("qa_transient");
        game.flags.set("ep1.incense.neglected", true);
      }
      if (
        game.flags.get("ep1.opening.version", 0) >= 2 &&
        !sessionStorage.getItem("journey-walker-caught")
      ) {
        game.player.teleport(w.brain.position.clone());
        sessionStorage.setItem("journey-walker-caught", "1");
        await button("Retry checkpoint");
        return;
      } else if (game.flags.get("ep1.opening.version", 0) < 2) {
        game.player.teleport(w.brain.position.clone());
        await wait(() => w.restarts === 1 && !game.cutscene, "CP3 catch recovery");
      }
      assert(
        !game.inventory.has("qa_transient") && game.inventory.count("matches") === matches,
        "CP3 restores inventory snapshot",
      );
      assert(!game.flags.get("ep1.incense.neglected", false), "CP3 restores respect flags");
      game.player.teleport(new Vector3(-2.2, 2.5, -13.45));
      await wait(() => w.brain.active, "walker retry");
      const spot = w.models.wardrobes.find((s) => s.id === "H1")!;
      await aim(spot.front, spot.root.position.add(new Vector3(0, 1.15, 0)), 0.6);
      await ray("interact_wardrobe_H1");
      if (act.vigil.lamp.burning) key("KeyF");
      assert(!act.vigil.lamp.burning, "F extinguishes the lamp during the live threat");
      await wait(() => w.hiding.concealed, "concealment");
      game.toggleSatchel();
      game.toggleSketchbook();
      assert(!game.satchel.isOpen && !game.sketchbook?.isOpen, "threat gates menus");
      await wait(() => game.flags.get("ep1.walker.complete", false), "walker full patrol", 90000);
      key("KeyE");
      await free();
      assert(!game.hiding && !game.threatActive, "survival releases hiding and threat gates");
      report("PASS walker caught → CP3 retry → H1 survival");
    } else report("PASS completed CP3 restores without replaying walker");
    await free();
    await pause(1000);
    await free();
    const d = act.desk,
      m = d.models;
    await aim(
      new Vector3(0, 2.5, -20.25),
      m.compartment.position.add(new Vector3(0, 0.26, 0.06)),
      0.35,
    );
    await ray("interact_altar_key_panel");
    await pause(900);
    game.inspectObject(m.key.getAbsolutePosition(), 0.12);
    await pause(350);
    await ray("interact_desk_key");
    await aim(
      new Vector3(-4.3, 2.5, -15.8),
      m.drawer.getAbsolutePosition().add(new Vector3(0, 0.642, 0.555)),
      0.5,
    );
    await ray("interact_sok_desk");
    await wait(() => m.drawerReady, "desk drawer");
    await aim(
      new Vector3(-4.3, 2.5, -15.8),
      m.journal.getAbsolutePosition().add(new Vector3(0, 0.013, 0.04)),
      0.32,
    );
    await ray("interact_sok_journal_b");
    await readAll();
    await free();
    game.player.teleport(CP4_FEET, Math.PI);
    await wait(() => d.progress.portraitAwake, "scripted ash");
    await free();
    use("interact_incense_bundle");
    use("interact_incense_0");
    await wait(() => d.progress.actThree, "incense relight / thread snap", 150000);
    await checkpoint("CP4", "hunt-entry");
    return;
  }
  if (step === "hunt-entry") {
    assert(
      cp === "CP4" && Vector3.Distance(game.player.feet, CP4_FEET) < 0.3,
      "CP4 restores clear tent aisle",
    );
    assert(game.flags.get("ep1.walker.complete", false), "CP4 retains walker survival");
    game.player.teleport(new Vector3(1.25, 0, -10.8));
    await wait(() => act.hunt.progress.started, "CP5 entry");
    await checkpoint("CP5", "hunt");
    return;
  }
  if (step === "hunt") {
    assert(
      cp === "CP5" && Vector3.Distance(game.player.feet, CP5_FEET) < 0.3,
      "CP5 resumes safe entrance",
    );
    const h = act.hunt;
    if (
      game.flags.get("ep1.opening.version", 0) >= 2 &&
      sessionStorage.getItem("journey-hunt-caught") &&
      !sessionStorage.getItem("journey-hunt-retry-verified")
    ) {
      assert(
        !game.inventory.has("brass_key_bit"),
        "CP5 death restores the last safe checkpoint before the fragment pickup",
      );
      sessionStorage.setItem("journey-hunt-retry-verified", "1");
    }
    for (const id of ["J6", "J2", "J4"]) {
      const jar = JARS.find((j) => j.id === id)!;
      await wait(
        () => !h.brain.active || Vector3.Distance(h.brain.position, jar.at) > 4.2,
        `patrol gap ${id}`,
        90000,
      );
      await aim(jar.at.add(new Vector3(0, 0, 1.1)), jar.at.add(new Vector3(0, 0.93, 0)), 0.4);
      await ray(`interact_jar_${id}`);
      await pause(700);
      game.inspectObject(jar.at.add(new Vector3(0, 0.68, 0)), 0.4);
      await pause(300);
      game.interaction.use();
      assert(game.flags.get(`ep1.jar.${id}.taken`, false), `${id} fragment collected`);
      if (id === "J6") {
        if (
          game.flags.get("ep1.opening.version", 0) >= 2 &&
          !sessionStorage.getItem("journey-hunt-caught")
        ) {
          h.brain.position.copyFrom(game.player.feet);
          h.brain.position.y = 0;
          sessionStorage.setItem("journey-hunt-caught", "1");
          await button("Retry checkpoint");
          return;
        } else if (game.flags.get("ep1.opening.version", 0) < 2) {
          h.brain.position.copyFrom(game.player.feet);
          h.brain.position.y = 0;
          await wait(() => h.restarts === 1, "roamer catch recovery");
          assert(
            game.inventory.count("brass_key_bit") === 1,
            "legacy CP5 catch retains fresh fragment",
          );
        }
      }
      game.stopInspecting();
      game.player.teleport(CP5_FEET);
      await pause(300);
    }
    await free();
    game.toggleSatchel();
    await pause(350);
    const assemble = document.querySelector<HTMLButtonElement>(".story-satchel button");
    assert(assemble && !assemble.disabled, "three fragments enable satchel recipe");
    assemble!.click();
    await wait(() => h.progress.assembled, "assembly");
    await free();
    const c = act.chest,
      m = c.models;
    await aim(new Vector3(-4.5, 2.5, -11.82), new Vector3(-4.5, 2.49, -12.4), 0.55);
    use("interact_loose_planks");
    await wait(() => m.planksReady, "planks");
    use("interact_hidden_chest");
    await wait(() => m.lidReady, "chest lid");
    for (const item of CHEST_ITEMS) {
      await free();
      use(`interact_chest_${item}`);
      await pause(300);
      assert(game.inventory.count(item) === 1, `chest discovery ${item}`);
    }
    await free();
    game.player.teleport(CP6_FEET, CP6_YAW);
    game.player.pitch = 0.8;
    await pause(500);
    const to = RITUAL_BURNER.subtract(game.camera.globalPosition);
    game.player.pitch = -Math.atan2(to.y, Math.hypot(to.x, to.z));
    await pause(500);
    await ray("interact_ritual_burner");
    assert(act.ritual.progress.placed, "token placed without burning");
    await checkpoint("CP6", "ritual");
    return;
  }
  if (step === "ritual") {
    assert(
      cp === "CP6" && Vector3.Distance(game.player.feet, CP6_FEET) < 0.3,
      "CP6 restores burner and token",
    );
    Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => true });
    const p = act.ritual.progress;
    async function burner() {
      await free();
      game.player.teleport(CP6_FEET, CP6_YAW);
      await pause(250);
      const to = RITUAL_BURNER.subtract(game.camera.globalPosition);
      game.player.pitch = -Math.atan2(to.y, Math.hypot(to.x, to.z));
      await pause(350);
      await ray("interact_ritual_burner");
    }
    for (let i = 0; i < 3; i++) {
      await burner();
      assert(p.active, "ritual starts");
      game.player.yaw = 0;
      await wait(() => !p.active, "turn failure");
    }
    assert(
      game.inventory.count("blessed_matches") === 0 && !p.broken,
      "three turn failures consume matches, retain seal",
    );
    const mesh = act.ritual.spare.getChildMeshes()[0];
    mesh.computeWorldMatrix(true);
    const at = mesh.getAbsolutePosition();
    await aim(new Vector3(at.x, 2.5, at.z + 0.7), at, 0.2);
    game.stopInspecting();
    await pause(300); // Restore ordinary look before using the spare.
    use("interact_ritual_spare");
    assert(game.inventory.count("blessed_matches") === 1, "altar spare prevents soft lock");
    await burner();
    await wait(() => p.elapsed > 2, "partial ritual");
    Object.defineProperty(game.input, "pointerLocked", { get: () => false });
    await checkpoint("CP6", "ritual-resume");
    return;
  }
  if (step === "ritual-resume") {
    assert(
      !act.ritual.progress.active &&
        act.ritual.progress.elapsed === 0 &&
        game.inventory.count("blessed_matches") === 0,
      "interrupted CP6 retains spent match and resets hold",
    );
    Object.defineProperty(game.input, "pointerLocked", { get: () => true });
    use("interact_ritual_spare");
    await free();
    game.player.teleport(CP6_FEET, CP6_YAW);
    game.player.pitch = 0.8;
    await pause(300);
    const to = RITUAL_BURNER.subtract(game.camera.globalPosition);
    game.player.pitch = -Math.atan2(to.y, Math.hypot(to.x, to.z));
    await pause(350);
    await ray("interact_ritual_burner");
    await wait(() => act.ritual.progress.broken, "25-second successful ritual");
    assert(!game.inventory.has("bronze_token"), "seal consumes token");
    await wait(() => act.resolution.active, "dawn begins");
    await button("Wait for Vuthy");
    await button("Show him the journal");
    await button("Let him return to Grandmother");
    await button("Unfold the map");
    await button("Close the map");
    await button("Open the sketchbook");
    await button("View credits");
    await wait(() => !saves.saving, "completion archive");
    const end = (await saves.load("episode1")).save;
    assert(
      end?.flags["ep1.complete"] === true && end.flags["series.nextEpisode"] === 2,
      "earned journey reaches credits and Episode 2 completion archive",
    );
    assert(
      end?.flags["ep1.journal.shared"] === true && end.flags["series.night"] === 3,
      "ending choice and night count persist",
    );
    report(
      "FULL JOURNEY PASSED: fresh prologue → CP1 → CP2 → CP3 catch/retry → CP4 → CP5 catch/loot → CP6 failures/spares/reload → credits",
    );
  }
}
void run().catch((error) => report(`FAIL ${String(error)}`));
