/** Actual village / interaction / IndexedDB checks, using a separate test database. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { saveShot } from "../../src/debug/saveShot";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { CHEST_ITEMS } from "../../src/episodes/ep1/act3/ChestProgress";
import { CP6_FEET, CP6_YAW, RITUAL_BURNER } from "../../src/episodes/ep1/data/ritual";

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
    if (performance.now() - start > ms) throw new Error("Timed out waiting for ritual sequence");
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
  const game = new Game(engine, await detectDevice());
  const saves = new SaveStore(undefined, "boon-sop-ritual-verification");
  Object.defineProperty(game, "saves", { value: saves });
  if (which === "entry") {
    const save = newGameSave();
    save.checkpoint = "CP5";
    save.clock = "02:35";
    save.lamp = { oil: 1, state: "open" };
    save.inventory = {
      lamp: 1,
      brass_key: 1,
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
      "ep1.hunt.started",
      "ep1.brassKey.assembled",
      "ep1.fragments.3",
    ])
      save.flags[flag] = true;
    save.flags["ep1.coffin.triggered"] = true;
    save.flags["ep1.clock"] = "02:35";
    save.flags["ep1.checkpoint"] = "CP5";
    save.flags["ep1.incense.remaining"] = 0.75;
    save.flags["sketchbook.written"] =
      "SB-01,SB-04,SB-05,SB-A2-05,SB-A2-06,SB-06,SB-A2-07,SB-A3-01";
    await saves.save("autosave", save);
    for (const id of ["J2", "J4", "J6"]) {
      save.flags[`ep1.jar.${id}.open`] = true;
      save.flags[`ep1.jar.${id}.taken`] = true;
    }
    save.flags["ep1.chest.planksOpen"] = true;
    save.flags["ep1.chest.unlocked"] = true;
    save.flags["ep1.ritual.ready"] = true;
    save.flags["ep1.coffin.closed"] = true;
    save.flags["sketchbook.written"] += ",SB-07,SB-CHEST-MAP,SB-CHEST-SLIP";
    delete save.inventory.brass_key;
    for (const item of CHEST_ITEMS) {
      save.flags[`ep1.chest.${item}.taken`] = true;
      save.inventory[item] = 1;
    }
    save.flags["ep1.slip.unread"] = true;
    await saves.save("autosave", save);
  }
  report("Click to begin. Actual village and isolated ritual verification saves.");
  await game.start();
  // The fixture drives yaw/pitch directly, like the movement spike's input bot.
  // Embedded automation surfaces reject pointer lock; simulate only that input
  // capability here. Production continues to pause when real pointer lock is lost.
  Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => true });
  report("Scripted look input enabled; production pointer-lock handling is unchanged.");
  const act = (window as unknown as { act: ActOne }).act;
  const p = act.ritual.progress;
  await wait(() => !game.cutscene, 300000);
  await pause(700);
  if (which !== "entry") {
    assert(game.resumedSave?.checkpoint === "CP6", "CP6 loaded from IndexedDB");
    assert(Vector3.Distance(game.player.feet, CP6_FEET) < 0.25, "CP6 spawns at the burner");
    assert(p.placed && !p.active && p.elapsed === 0, "token restored; hold does not resume");
    assert(
      game.inventory.has("seal_map") && game.inventory.has("folded_slip"),
      "chest discoveries preserved",
    );
    assert(game.flags.get("ep1.slip.unread", false), "folded slip remains unread");
  }
  async function aimBurner() {
    game.stopInspecting();
    game.satchel.close();
    await wait(() => !game.sketchbook?.isBusy);
    game.sketchbook?.close();
    await wait(() => !game.gated.reading);
    game.player.teleport(CP6_FEET, CP6_YAW);
    game.player.pitch = 0.8;
    await pause(400);
    // Use the exact direction from the current eye to the burner, without inspection gating.
    const to = RITUAL_BURNER.subtract(game.camera.globalPosition);
    game.player.pitch = -Math.atan2(to.y, Math.hypot(to.x, to.z));
    await pause(400);
    assert(
      game.interaction.focus === "interact_ritual_burner",
      `main burner ray is usable (${game.interaction.focus})`,
    );
  }
  async function finish(next: string, label: string) {
    await wait(() => !saves.saving);
    const stored = (await saves.load("autosave")).save;
    assert(stored?.checkpoint === "CP6", "CP6 persisted");
    document.exitPointerLock();
    if (p.active) Object.defineProperty(game.input, "pointerLocked", { get: () => false });
    link(next, label);
  }
  if (which === "complete") {
    assert(
      p.broken && !game.inventory.has("bronze_token"),
      "broken seal restored without token duplication",
    );
    assert(game.inventory.count("blessed_matches") === 0, "last spent spare stays spent");
    assert(
      act.lights.hangingLevel === 1 &&
        [...act.lights.practicalLevels.values()].every((n) => n === 1),
      "lamps restore lit",
    );
    assert(!game.threatActive && !game.gated.holdStill, "controls restored after success reload");
    report("CHEST → CP6 → RETRIES → SPARE → INTERRUPT → SEAL → RELOAD PASSED");
    document.exitPointerLock();
    await pause(3200);
    await saveShot(engine, game.camera, "ritual_seal_reload");
    return;
  }
  await aimBurner();
  if (which === "entry") {
    assert(
      !p.placed && game.inventory.count("blessed_matches") === 3,
      "chest-ready state starts with three blessed matches",
    );
    game.interaction.use();
    assert(p.placed, "actual burner interaction places token");
    await finish("placed", "Verify placed-token reload and exhaust matches");
  } else if (which === "placed") {
    assert(game.inventory.count("blessed_matches") === 3, "placing consumes no matches");
    for (let i = 0; i < 3; i++) {
      await aimBurner();
      game.interaction.use();
      assert(
        p.active && game.gated.holdStill && game.threatActive,
        "attempt starts with movement and menu gates",
      );
      game.player.yaw = 0;
      await wait(() => !p.active);
      assert(!p.broken && !game.gated.holdStill, "turning around fails and releases movement");
    }
    assert(
      game.inventory.count("blessed_matches") === 0 && game.inventory.has("bronze_token"),
      "three failures exhaust matches but retain token",
    );
    await finish("exhausted", "Verify exhaustion reload and collect spare");
  } else if (which === "exhausted") {
    assert(game.inventory.count("blessed_matches") === 0, "empty match supply survives reload");
    const mesh = act.ritual.spare.getChildMeshes()[0];
    mesh.computeWorldMatrix(true);
    const at = mesh.getAbsolutePosition();
    game.player.teleport(new Vector3(at.x, 2.5, at.z + 0.7), Math.PI);
    await pause(400);
    const to = at.subtract(game.camera.globalPosition);
    game.player.pitch = -Math.atan2(to.y, Math.hypot(to.x, to.z));
    await pause(400);
    assert(
      game.interaction.focus === "interact_ritual_spare",
      `altar spare ray is usable (${game.interaction.focus})`,
    );
    game.interaction.use();
    assert(game.inventory.count("blessed_matches") === 1, "altar grants one spare");
    await aimBurner();
    game.interaction.use();
    await wait(() => p.elapsed > 2);
    assert(game.inventory.count("blessed_matches") === 0, "spare spent before interrupted save");
    await finish("interrupted", "Reload an interrupted ritual");
  } else if (which === "interrupted") {
    assert(
      !p.broken && game.inventory.count("blessed_matches") === 0,
      "interrupted attempt cannot refund a match or break seal",
    );
    // The previous stage verifies the physical altar target. Reuse its event for a second spare.
    game.bus.emit("interact:use", { id: "interact_ritual_spare" });
    assert(
      game.inventory.count("blessed_matches") === 1,
      "another spare prevents a soft lock after interruption",
    );
    await aimBurner();
    game.interaction.use();
    await wait(() => p.broken, 90000);
    assert(!game.inventory.has("bronze_token"), "successful 25-second hold burns token");
    await wait(
      () =>
        act.lights.hangingLevel === 1 &&
        [...act.lights.practicalLevels.values()].every((n) => n === 1),
      30000,
    );
    assert(!game.threatActive && !game.gated.holdStill, "success releases controls");
    await finish("complete", "Verify broken-seal reload");
  }
}
void verify().catch((error: unknown) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
