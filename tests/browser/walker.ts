/** The production encounter, physical wardrobes and IndexedDB, using an isolated verification slot. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { CP3_FEET } from "../../src/episodes/ep1/data/walker";

const results = document.getElementById("results")!;
const report = (s: string) => (results.textContent += `${s}\n`);
const assert = (test: unknown, label: string) => {
  if (!test) throw new Error(label);
  report(`PASS ${label}`);
};
const wait = async (test: () => boolean, ms = 30000) => {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > ms) throw new Error("Timed out waiting for walker state");
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
};
const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
function next(url: string, label: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.textContent = label;
  a.style.cssText =
    "position:fixed;bottom:12px;left:12px;z-index:1002;background:#e3d3af;color:#231e16;padding:12px";
  document.body.append(a);
}

async function verify(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search),
    which = params.get("case") ?? "prepare";
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  const saves = new SaveStore(undefined, "boon-sop-walker-verification");
  Object.defineProperty(game, "saves", { value: saves });
  if (!params.has("continue")) {
    for (const key of [
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
    ])
      game.flags.set(key, true);
    game.inventory.add("sok_journal");
    game.inventory.add("blessed_matches", 3);
  }
  report("Click to begin. Separate verification save; real walker speed and physical wardrobes.");
  await game.start();
  const act = (window as unknown as { act: ActOne }).act,
    w = act.walker;
  document.getElementById("toggle")!.onclick = () => (results.hidden = !results.hidden);
  await wait(() => !game.cutscene, 300000);
  if (!params.has("continue")) {
    game.sketchbook?.restore(["SB-01", "SB-A2-01", "SB-04", "SB-05", "SB-A2-05"]);
    act.vigil.lamp.light();
    game.player.teleport(CP3_FEET, Math.PI / 2);
    await wait(() => w.armed && !game.saves.saving);
  }
  assert(w.armed, "CP3 arms before the threshold trigger");
  const saved = (await saves.load("autosave")).save;
  assert(saved?.checkpoint === "CP3", "IndexedDB contains CP3");
  assert(
    game.flags.get("ep1.journal.found", false) && game.flags.get("ep1.gramophone.heard", false),
    "journal and solved recording remain complete",
  );
  if (which === "visual") {
    game.player.teleport(new Vector3(1.4, 2.5, -14.4));
    await pause(500);
    game.scene.onBeforeRenderObservable.add(() => {
      if (w.brain.active) game.inspectObject(w.brain.position.add(new Vector3(0, 1.3, 0)), 1.4);
    });
    report("Live model preview: the camera follows the walker. Normal play uses mouse look.");
    return;
  }
  if (which === "prepare") {
    assert(
      w.brain.state === "idle" && !game.threatActive,
      "saving CP3 does not start the encounter early",
    );
    report("CP3 PREPARE PASSED");
    next("?continue&case=caught", "Reload CP3 and test catch / restart");
    return;
  }
  assert(Vector3.Distance(game.player.feet, CP3_FEET) < 0.25, "CP3 resumes inside Sok’s room");
  if (which === "complete") {
    assert(
      game.flags.get("ep1.walker.complete", false),
      "surviving the walker restores as complete",
    );
    game.player.teleport(new Vector3(-2.2, 2.5, -13.45));
    await pause(1200);
    assert(
      !w.brain.active && !game.threatActive,
      "completed walker does not replay on crossing the threshold",
    );
    report("COMPLETED CP3 RESTORE PASSED");
    next("?start=act1&case=h2", "Test the hall wardrobe H2 from a fresh encounter");
    return;
  }
  game.player.teleport(new Vector3(-2.2, 2.5, -13.45));
  await wait(() => w.brain.active);
  assert(game.threatActive, "leaving Sok’s room starts the walker");
  if (which === "caught") {
    game.inventory.remove("matches");
    game.inventory.add("caught_test_item");
    game.flags.set("ep1.incense.neglected", true);
    game.player.teleport(w.brain.position.clone());
    await wait(() => w.restarting);
    await wait(() => w.restarts === 1 && !game.cutscene);
    assert(
      Vector3.Distance(game.player.feet, CP3_FEET) < 0.25,
      "catch restarts at CP3 without reloading the page",
    );
    assert(
      game.inventory.count("matches") === saved?.inventory.matches &&
        !game.inventory.has("caught_test_item"),
      "restart restores the inventory snapshot",
    );
    assert(
      !game.flags.get("ep1.incense.neglected", false),
      "restart restores pre-encounter respect flags",
    );
    assert(act.vigil.lamp.oil >= 0.49, "restart restores at least half a lamp tank");
    assert(
      !game.hiding && !game.gated.holdStill && !game.gated.holdLook && !game.threatActive,
      "restart releases every movement and menu gate",
    );
    assert(
      game.flags.get("ep1.gramophone.heard", false),
      "catch never repeats the gramophone puzzle",
    );
    game.player.teleport(new Vector3(-2.2, 2.5, -13.45));
    await wait(() => w.brain.active);
  }
  const wardrobe = w.models.wardrobes.find((spot) => spot.id === (which === "h2" ? "H2" : "H1"))!;
  game.player.teleport(wardrobe.front, wardrobe.yaw + Math.PI);
  await pause(500);
  game.inspectObject(wardrobe.root.position.add(new Vector3(0, 1.15, 0)), 0.6);
  await pause(500);
  assert(
    game.interaction.focus === `interact_wardrobe_${wardrobe.id}`,
    `${wardrobe.id} is reachable through the real E interaction ray`,
  );
  game.interaction.use();
  assert(game.hiding, `${wardrobe.id} enters hiding`);
  if (act.vigil.lamp.burning) window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyF" }));
  await wait(() => w.hiding.concealed);
  game.toggleSketchbook();
  game.toggleSatchel();
  assert(
    !game.sketchbook?.isOpen && !game.satchel.isOpen,
    "the live threat cannot be bypassed with a menu",
  );
  await pause(1800);
  assert(
    Vector3.Distance(game.player.feet, wardrobe.root.position) < 0.15,
    "Havok keeps Sora inside the hollow wardrobe",
  );
  await wait(() => game.flags.get("ep1.walker.complete", false), 65000);
  await wait(() => !game.saves.saving);
  assert(
    w.restarts === (which === "caught" ? 1 : 0),
    "quiet hiding survives the full route without a catch",
  );
  assert(
    !game.threatActive && !w.models.walker.isEnabled(),
    "the walker leaves by the rear and releases the threat gate",
  );
  assert(
    (await saves.load("autosave")).save?.flags["ep1.walker.complete"] === true,
    "completed encounter persists to CP3",
  );
  window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE" }));
  await pause(400);
  assert(!game.hiding && !game.gated.hiding, "E exits the wardrobe after the threat passes");
  await wait(() => !!game.sketchbook?.written.has("SB-A2-06"));
  assert(
    game.sketchbook?.written.has("SB-A2-06"),
    "the survival note is written after leaving hiding",
  );
  report(`${wardrobe.id} SAFE HIDING PASSED`);
  next("?continue&case=complete", "Reload completed CP3");
}
void verify().catch((error) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
