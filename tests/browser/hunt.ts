/** Isolated IndexedDB fixtures driving the actual WebGPU/Havok game, rays and recipe UI.
 * /tests/browser/hunt.html?continue&case=entry → reload → finish → reload assembled.
 */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { CP5_FEET, CP5_YAW, JARS, FRAGMENT_IDS } from "../../src/episodes/ep1/data/hunt";
import { saveShot } from "../../src/debug/saveShot";
const output = document.getElementById("results")!;
const report = (s: string) => (output.textContent += `${s}\n`);
const assert = (ok: unknown, s: string) => {
  if (!ok) throw new Error(s);
  report(`PASS ${s}`);
};
const pause = (ms = 350) => new Promise((done) => setTimeout(done, ms));
async function wait(test: () => boolean, ms = 30000) {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > ms) throw new Error("Timed out waiting for hunt");
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
async function verify() {
  if (!import.meta.env.DEV) return;
  const which = new URLSearchParams(location.search).get("case") ?? "entry";
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice()),
    saves = new SaveStore(undefined, "boon-sop-hunt-verification");
  Object.defineProperty(game, "saves", { value: saves });
  if (which === "entry") {
    const save = newGameSave();
    save.checkpoint = "CP4";
    save.clock = "02:00";
    save.lamp = { oil: 1, state: "out" };
    save.inventory = {
      lamp: 1,
      satchel: 1,
      sketchbook: 1,
      matches: 20,
      blessed_matches: 3,
      incense: 2,
      sok_journal: 1,
      sok_journal_b: 1,
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
      "ep1.altar.compartmentOpen",
      "ep1.desk.keyTaken",
      "ep1.desk.open",
      "ep1.journalB.read",
      "ep1.portrait.awake",
      "ep1.portrait.seen",
      "ep1.thread.broken",
      "ep1.act2.complete",
      "ep1.act3.started",
    ])
      save.flags[flag] = true;
    save.flags["ep1.clock"] = "02:00";
    save.flags["ep1.checkpoint"] = "CP4";
    save.flags["ep1.incense.remaining"] = 0.75;
    save.flags["sketchbook.written"] =
      "SB-01,SB-04,SB-05,SB-A2-05,SB-A2-06,SB-06,SB-A2-07,SB-A3-01";
    await saves.save("autosave", save);
  }
  report("Click to begin. Actual scene and interactions; separate test save database.");
  await game.start();
  const act = (window as unknown as { act: ActOne }).act,
    h = act.hunt;
  await wait(() => !game.cutscene, 300000);
  async function freeHands() {
    game.stopInspecting();
    game.satchel.close();
    await pause(150);
    await wait(() => !game.sketchbook?.isBusy);
    if (game.sketchbook?.isOpen) game.sketchbook.toggle();
    await wait(() => !game.gated.reading && !game.sketchbook?.isBusy);
  }
  async function aim(feet: Vector3, at: Vector3, radius = 0.4) {
    await freeHands();
    game.player.teleport(feet);
    await pause();
    game.inspectObject(at, radius);
    await pause();
  }
  async function jarView(id: string) {
    const j = JARS.find((j) => j.id === id)!;
    await aim(j.at.add(new Vector3(0, 0, 1)), j.at.add(new Vector3(0, 0.72, 0)), 0.48);
  }
  document.getElementById("jar")!.onclick = () =>
    void (async () => {
      game.cutscene = true;
      h.models.roamer.setEnabled(false);
      act.vigil.lamp.restore({ oil: 1, state: "open" });
      await jarView("J1");
      h.models.jarState("J1", true, false, true);
      h.models.updateJars(0);
      await pause(800);
      await saveShot(engine, game.camera, "hunt_detailed_jar");
    })();
  document.getElementById("roamer")!.onclick = () =>
    void (async () => {
      game.cutscene = true;
      act.vigil.lamp.restore({ oil: 1, state: "open" });
      await aim(new Vector3(-1.7, 0, -12), new Vector3(-3.6, 1, -16.6), 1.4);
      h.models.pose(new Vector3(-3.6, 0, -16.6), new Vector3(0.4, 0, 1), 0, 1);
      await pause(800);
      await saveShot(engine, game.camera, "hunt_roamer");
    })();
  document.getElementById("results-toggle")!.onclick = () => (output.hidden = !output.hidden);
  if (which === "assembled") {
    assert(game.resumedSave?.checkpoint === "CP5", "assembled key resumes at CP5");
    assert(
      h.progress.assembled && game.inventory.count("brass_key") === 1,
      "assembled key restores exactly once",
    );
    assert(
      FRAGMENT_IDS.every((id) => !game.inventory.has(id)),
      "consumed pieces stay absent after reload",
    );
    assert(
      h.models.jars
        .filter((j) => ["J2", "J4", "J6"].includes(j.id))
        .every((j) => j.opening > 0.99 && !j.contents.isEnabled()),
      "looted jars stay open and empty after reload",
    );
    report("CP5 → JARS → CAUGHT → RESTORE → ASSEMBLE → RELOAD PASSED");
    return;
  }
  if (which === "entry") {
    assert(!h.progress.started, "hunt waits until Sora enters below the house");
    game.player.teleport(new Vector3(1.25, 0, -10.8), CP5_YAW);
    await pause();
    assert(
      h.progress.started && game.flags.get<string>("ep1.checkpoint", "") === "CP5",
      "entry captures CP5 before the roamer appears",
    );
    await pause(2800);
    assert(
      h.brain.active && h.models.roamer.isEnabled(),
      "dragging sound precedes the roamer’s appearance",
    );
    // Controlled sense fixtures against real rendered occluders, then normal hunt updates.
    game.cutscene = true;
    game.player.teleport(new Vector3(1, 0, -12));
    await pause();
    h.brain.position.set(1, 0, -16);
    assert(h.canSeeSora(), "open aisle has line of sight");
    game.player.teleport(new Vector3(0, 0, -12));
    await pause();
    h.brain.position.set(0, 0, -16);
    assert(!h.canSeeSora(), "central house post blocks rendered sight");
    game.player.teleport(new Vector3(0, 2.5, -12));
    await pause();
    assert(!h.canSeeSora(), "roamer cannot see Sora upstairs");
    h.brain.start();
    game.cutscene = false;
    await jarView("J6");
    assert(
      game.interaction.focus === "interact_jar_J6",
      `jar lid reachable through ordinary ray (${game.interaction.focus})`,
    );
    game.interaction.use();
    assert(
      h.brain.state === "investigating",
      "lifting a jar lid attracts the roamer through the noise bus",
    );
    await pause(650);
    game.inspectObject(JARS[5].at.add(new Vector3(0, 0.68, 0)), 0.4);
    await pause();
    assert(game.interaction.focus?.startsWith("interact_jar_"), "open jar remains reachable");
    await saveShot(engine, game.camera, "hunt_open_jar");
    game.interaction.use();
    assert(game.inventory.count("brass_key_bit") === 1, "jar grants one physical key fragment");
    // Force a contact fixture immediately after pickup: memory must not await IndexedDB.
    h.brain.position.copyFrom(game.player.feet);
    h.brain.position.y = 0;
    await wait(() => h.restarting);
    await wait(() => h.restarts === 1);
    assert(
      game.inventory.count("brass_key_bit") === 1,
      "caught restart retains the just-collected fragment",
    );
    assert(
      Vector3.Distance(game.player.feet, CP5_FEET) < 0.3,
      "catch returns Sora to clear ground at CP5",
    );
    assert(
      !game.cutscene && !game.threatActive && !game.gated.holdStill && !game.gated.holdLook,
      "restart releases movement, camera and menus",
    );
    assert(
      h.models.jars[5].opening > 0.99 && !h.models.jars[5].contents.isEnabled(),
      "collected jar remains open and empty on retry",
    );
    await wait(() => !saves.saving);
    assert(
      (await saves.load("autosave")).save?.inventory.brass_key_bit === 1,
      "CP5 disk save includes the pickup",
    );
    link("finish", "Reload CP5 and finish collecting");
    return;
  }
  assert(
    game.resumedSave?.checkpoint === "CP5" && Vector3.Distance(game.player.feet, CP5_FEET) < 0.3,
    "CP5 resumes at the safe entrance",
  );
  assert(
    game.inventory.count("brass_key_bit") === 1 && !h.models.jars[5].contents.isEnabled(),
    "partial progress restores from disk",
  );
  for (const id of ["J2", "J4"]) {
    // Wait at the entrance for a real patrol gap instead of teleporting onto the
    // creature's starting position. Actual AI continues throughout the search.
    const at = JARS.find((j) => j.id === id)!.at;
    await wait(() => !h.brain.active || Vector3.Distance(h.brain.position, at) > 4.2, 60000);
    await jarView(id);
    assert(game.interaction.focus === `interact_jar_${id}`, `${id} can be opened`);
    game.interaction.use();
    await pause(600);
    game.inspectObject(JARS.find((j) => j.id === id)!.at.add(new Vector3(0, 0.68, 0)), 0.4);
    await pause(150);
    game.interaction.use();
    assert(game.flags.get(`ep1.jar.${id}.taken`, false), `${id} fragment collected`);
    game.stopInspecting();
    game.player.teleport(CP5_FEET);
    await pause(100);
  }
  assert(h.progress.pieces === 3, "all three distinct key pieces are in the satchel");
  await freeHands();
  game.toggleSatchel();
  await pause();
  const button = document.querySelector<HTMLButtonElement>(".story-satchel button");
  assert(button && !button.disabled, "safe satchel offers the key assembly action");
  await saveShot(engine, game.camera, "hunt_key_pieces");
  button!.click();
  await wait(() => h.progress.assembled);
  assert(
    game.inventory.count("brass_key") === 1 && h.progress.pieces === 0,
    "animation commits the three-to-one key recipe",
  );
  await pause(400);
  await saveShot(engine, game.camera, "hunt_assembled_key");
  await wait(() => !saves.saving);
  assert(
    (await saves.load("autosave")).save?.inventory.brass_key === 1,
    "assembled key is saved to CP5",
  );
  link("assembled", "Reload the assembled key");
}
void verify().catch((error) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
