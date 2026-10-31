/** Real WebGPU / Havok props, interaction rays and IndexedDB; isolated from player saves.
 * Start at /tests/browser/desk.html?continue&case=key and follow the reload links.
 */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { CP4_FEET } from "../../src/episodes/ep1/data/desk";
import { saveShot } from "../../src/debug/saveShot";

const output = document.getElementById("results")!;
const report = (s: string) => (output.textContent += `${s}\n`);
const assert = (value: unknown, s: string) => {
  if (!value) throw new Error(s);
  report(`PASS ${s}`);
};
const pause = (ms = 350) => new Promise((done) => setTimeout(done, ms));
async function wait(test: () => boolean, ms = 30000) {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > ms) throw new Error("Timed out waiting for desk sequence");
    await pause(100);
  }
}
function link(which: string, label: string) {
  const a = document.createElement("a");
  a.href = `?continue&case=${which}`;
  a.textContent = label;
  a.style.cssText =
    "position:fixed;bottom:12px;left:12px;z-index:1001;background:#e4d6b9;color:#201b14;padding:12px";
  document.body.append(a);
}

async function verify(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search),
    which = params.get("case") ?? "key";
  if (!params.has("continue")) {
    link("key", "Begin isolated investigation test");
    return;
  }
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  const saves = new SaveStore(undefined, "boon-sop-desk-verification");
  Object.defineProperty(game, "saves", { value: saves });
  if (which === "key") {
    const save = newGameSave();
    save.checkpoint = "CP3";
    save.clock = "01:25";
    save.lamp = { oil: 1, state: "open" };
    save.inventory = {
      lamp: 1,
      sketchbook: 1,
      satchel: 1,
      sok_journal: 1,
      blessed_matches: 3,
      matches: 20,
      incense: 2,
    };
    for (const flag of [
      "ep1.arrival.road",
      "ep1.arrival.courtyard",
      "ep1.vigil.started",
      "ep1.vuthy.left",
      "ep1.betel.asked",
      "ep1.betel.done",
      "ep1.act1.complete",
      "ep1.act2.started",
      "ep1.sok.unlocked",
      "ep1.journal.plankOpen",
      "ep1.journal.found",
      "ep1.gramophone.started",
      "ep1.gramophone.solved",
      "ep1.gramophone.heard",
      "ep1.walker.armed",
      "ep1.walker.complete",
    ])
      save.flags[flag] = true;
    save.flags["ep1.clock"] = "01:25";
    save.flags["ep1.checkpoint"] = "CP3";
    save.flags["ep1.incense.remaining"] = 0.75;
    save.flags["sketchbook.written"] = "SB-01,SB-04,SB-05,SB-A2-05,SB-A2-06";
    await saves.save("autosave", save);
  }
  report("Click to begin. Separate test database; actual models and interaction rays.");
  await game.start();
  const act = (window as unknown as { act: ActOne }).act,
    d = act.desk,
    m = d.models;
  const frame = () => pause();
  async function freeHands() {
    game.stopInspecting();
    await pause(150);
    await wait(() => !game.sketchbook?.isBusy);
    if (game.sketchbook?.isOpen) game.sketchbook.toggle();
    await wait(() => !game.sketchbook?.isBusy && !game.gated.reading);
  }
  async function aim(feet: Vector3, at: Vector3, radius = 0.4) {
    await freeHands();
    game.player.teleport(feet);
    await frame();
    game.inspectObject(at, radius);
    await frame();
  }
  const viewAltar = () =>
    aim(new Vector3(0, 2.5, -20.25), m.compartment.position.add(new Vector3(0, 0.26, 0.06)), 0.35);
  const viewDesk = () =>
    aim(
      new Vector3(-4.3, 2.5, -15.8),
      m.drawer.getAbsolutePosition().add(new Vector3(0, 0.642, 0.555)),
      0.5,
    );
  const viewPortrait = () => aim(new Vector3(0.65, 0, -2.7), m.portrait.position, 0.42);
  document.getElementById("altar")!.onclick = () => void viewAltar();
  document.getElementById("desk")!.onclick = () => void viewDesk();
  document.getElementById("portrait")!.onclick = () => void viewPortrait();
  document.getElementById("results-toggle")!.onclick = () => (output.hidden = !output.hidden);
  await wait(() => !game.cutscene, 300000);
  assert(
    d.progress.available && !game.threatActive,
    "desk sequence follows a completed walker encounter",
  );
  if (which === "key") {
    await viewDesk();
    assert(
      game.interaction.focus === "interact_sok_desk",
      "locked drawer is reachable through the interaction ray",
    );
    game.interaction.use();
    assert(!d.progress.drawerOpen, "desk cannot open without its key");
    await viewAltar();
    assert(game.interaction.focus === "interact_altar_key_panel", "inset altar panel is reachable");
    game.interaction.use();
    await pause(900);
    game.inspectObject(m.key.getAbsolutePosition(), 0.12);
    await frame();
    assert(
      game.interaction.focus === "interact_desk_key",
      "key is physically accessible behind the hinged panel",
    );
    await saveShot(engine, game.camera, "altar_key_compartment");
    game.interaction.use();
    await wait(() => !saves.saving);
    assert(game.inventory.count("drawer_key") === 1, "key is awarded exactly once");
    assert((await saves.load("autosave")).save?.inventory.drawer_key === 1, "key pickup autosaves");
    link("desk", "Reload with the altar key");
    return;
  }
  assert(d.progress.keyTaken && !m.key.isEnabled(), "collected key stays absent after reload");
  if (which === "desk") {
    assert(game.inventory.count("drawer_key") === 1, "desk key restores in the satchel");
    await viewDesk();
    game.interaction.use();
    await wait(() => m.drawerReady);
    assert(
      d.progress.drawerOpen && !game.inventory.has("drawer_key"),
      "unlocking consumes the key and opens a hollow drawer",
    );
  }
  if (which === "desk" || which === "journal") {
    assert(d.progress.drawerOpen, "drawer remains open");
    await aim(
      new Vector3(-4.3, 2.5, -15.8),
      m.journal.getAbsolutePosition().add(new Vector3(0, 0.013, 0.04)),
      0.32,
    );
    assert(
      game.interaction.focus === "interact_sok_journal_b",
      "journal inside the drawer is reachable",
    );
    await saveShot(engine, game.camera, "sok_open_desk");
    game.interaction.use();
    assert(d.reader.open, "Journal B opens its English translation");
    const next = () =>
      document
        .querySelector<HTMLButtonElement>(
          ".document-reader:not([hidden]) footer button:nth-of-type(2)",
        )!
        .click();
    if (which === "desk") {
      next();
      d.reader.close();
      await wait(() => !saves.saving);
      assert(!d.progress.journalRead, "closing partway does not complete the investigation");
      assert(
        (await saves.load("autosave")).save?.flags["ep1.journalB.page"] === 1,
        "partial journal reading autosaves",
      );
      link("journal", "Reload the open drawer and partial journal");
      return;
    }
    assert(d.reader.pageIndex === 1, "journal resumes at the saved page");
    next();
    next();
    assert(
      d.progress.journalRead && game.inventory.count("sok_journal_b") === 1,
      "final instructions are collected once",
    );
    await freeHands();
    await viewPortrait();
    game.stopInspecting();
    await wait(() => d.progress.portraitAwake);
    assert(!act.vigil.incense.alive, "returning to the tent turns all four incense sticks to ash");
    act.vigil.update(65);
    assert(
      !game.flags.get("ep1.incense.neglected", false),
      "scripted ash does not create a neglect penalty after 60 seconds",
    );
    await pause(1800);
    assert(
      game.flags.get("ep1.portrait.seen", false),
      "portrait scare is noticed through the normal camera view",
    );
    await act.beats.saveProgress();
    await saveShot(engine, game.camera, "sok_portrait_open_eyes");
    link("ash", "Reload the portrait scare before relighting");
    return;
  }
  assert(
    d.progress.journalRead && game.inventory.count("sok_journal_b") === 1,
    "final instructions restore without duplicates",
  );
  assert(d.progress.portraitAwake, "portrait remains awake without replaying the return beat");
  if (which === "ash") {
    assert(
      !act.vigil.incense.alive && !game.flags.get("ep1.incense.neglected", false),
      "scripted ash and its exemption restore",
    );
    await aim(new Vector3(2.9, 0, -4.1), new Vector3(1.9, 0.95, -4.55));
    assert(
      game.interaction.focus?.startsWith("interact_incense_"),
      "corner burner is reachable through the ray",
    );
    game.stopInspecting();
    game.interaction.use();
    await wait(() => d.progress.actThree);
    await wait(() => !saves.saving);
    const saved = (await saves.load("autosave")).save;
    assert(act.vigil.incense.alive, "ordinary match and incense bundle relight the vigil");
    assert(
      saved?.checkpoint === "CP4" && saved.flags["ep1.thread.broken"] === true,
      "thread snap atomically saves CP4",
    );
    assert(
      saved?.clock === "02:00" && saved.flags["ep1.act2.complete"] === true,
      "Act III clock and Act II completion save together",
    );
    assert(
      m.threadMeshes.every((mesh) => mesh.isEnabled()),
      "broken cord halves are visible",
    );
    assert(
      !game.gated.holdStill && !game.gated.holdLook,
      "snap keeps camera and movement under player control",
    );
    link("cp4", "Reload CP4 under the tent");
    return;
  }
  assert(game.resumedSave?.checkpoint === "CP4", "CP4 loads from IndexedDB");
  assert(
    Vector3.Distance(game.player.feet, CP4_FEET) < 0.3,
    "CP4 spawns under the tent in a clear aisle",
  );
  assert(
    d.progress.actThree && m.threadMeshes.every((mesh) => mesh.isEnabled()),
    "Act III and snapped thread restore without a second snap",
  );
  assert(
    !m.intactThreadMeshes[2].isEnabled() && !game.scene.getMeshByName("thread_mesh")?.isEnabled(),
    "intact north cord and imported combined thread stay hidden at CP4",
  );
  assert(!act.walker.brain.active, "hallway walker stays completed at CP4");
  assert(
    game.sketchbook?.written.has("SB-A3-01"),
    "under-house objective restores in the sketchbook",
  );
  d.update(30.1);
  await pause();
  assert(
    act.lights.practicalLevels.get("veranda") === 0,
    "remaining practical lamps go out progressively in Act III",
  );
  await act.beats.saveProgress();
  await viewPortrait();
  await saveShot(engine, game.camera, "sok_portrait_open_eyes");
  await aim(new Vector3(2.5, 0, -5), new Vector3(0.4, 1.4, -7), 0.75);
  await saveShot(engine, game.camera, "protective_thread_cp4");
  report("ALTAR → DESK → PORTRAIT → CP4 PASSED");
}
void verify().catch((error) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
