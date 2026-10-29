/**
 * Real WebGPU/Havok smoke test. Open /tests/browser/act1.html?start=act1 on a
 * separate dev-server port, click to begin, then follow the results panel.
 * Uses its own IndexedDB database: it never overwrites a player's checkpoint.
 */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { PhysicsEngine } from "@babylonjs/core/Physics/v2/physicsEngine";
import { PhysicsRaycastResult } from "@babylonjs/core/Physics/physicsRaycastResult";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { KANHA_LAYOUT, SLOTS } from "../../src/episodes/ep1/data/betel";
import { TENT_FLAME_MESH } from "../../src/episodes/ep1/data/arrival";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";

const results = document.getElementById("results") as HTMLElement;
const output: string[] = [];
const report = (message: string) => {
  output.push(message);
  results.textContent = output.join("\n");
};
const assert = (value: unknown, message: string) => {
  if (!value) throw new Error(message);
  report(`PASS ${message}`);
};
const wait = async (condition: () => boolean, timeout = 30000) => {
  const start = performance.now();
  while (!condition()) {
    if (performance.now() - start > timeout) throw new Error("Timed out waiting for game state");
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
};

async function run(): Promise<void> {
  if (!import.meta.env.DEV) throw new Error("Verification is development-only");
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU is required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  const saves = new SaveStore(undefined, "boon-sop-act1-verification");
  Object.defineProperty(game, "saves", { value: saves });
  // Speed up dialogue only. The production beat controller, puzzle and audio are unchanged.
  const say = game.subtitles.say.bind(game.subtitles);
  game.subtitles.say = (speaker, text, seconds) => say(speaker, text, seconds * 0.025);
  if (new URLSearchParams(location.search).has("continue")) {
    report("Restoring the verification CP2. Click to begin.");
    await game.start();
    const act = (window as unknown as { act: ActOne }).act;
    await wait(() => !game.cutscene, 180000);
    assert(game.flags.get("ep1.act2.started", false), "Act II restored");
    assert(game.flags.get("ep1.sok.unlocked", false), "Sok's door stays unlocked");
    assert(!game.scene.getTransformNodeByName("col_door_sok_body"), "door collider stays removed");
    assert(act.lights.hangingLevel === 0, "pavilion lamps stay out");
    assert(game.inventory.count("blessed_matches") === 3, "blessed matches are not duplicated");
    assert(game.sketchbook?.written.has("SB-A2-01"), "Act II objective restored");
    assert(
      !game.scene.getTransformNodeByName("interact_land_deed")?.isEnabled(),
      "collected lore stays collected",
    );
    assert(game.player.feet.z < -1 && game.player.feet.y < 0.5, "CP2 spawns beneath the tent");
    report("RESTORE PASSED");
    return;
  }
  report("Click to begin. The test uses actual village assets, audio and physics.");
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  await wait(() => !game.cutscene, 180000);
  await wait(() => game.flags.get("ep1.arrival.road", false));
  assert(!game.flags.get("ep1.vigil.started", false), "incense timer waits for duties");
  assert(!act.early.active && !game.threatActive, "arrival is free of a forced encounter");
  assert(!game.scene.meshes.some((m) => m.name.startsWith("road_cart_")), "opening carts removed");
  game.player.teleport(new Vector3(0, 0, -2), Math.PI);
  const arrivalUse = (id: string) => game.bus.emit("interact:use", { id });
  arrivalUse("interact_arrival_note");
  document
    .querySelector<HTMLButtonElement>(".document-reader:not([hidden]) footer button:last-child")
    ?.click();
  assert(
    game.flags.get("ep1.arrival.noteRead", false),
    "family note gives the phone and match instructions",
  );
  arrivalUse("interact_arrival_phone");
  await wait(() => game.flags.get("ep1.arrival.callComplete", false) && !game.cutscene);
  await wait(() => !game.saves.saving);
  arrivalUse("interact_blessed_matches");
  arrivalUse("interact_blessed_matches");
  assert(
    game.inventory.count("blessed_matches") === 3,
    "prepared matchbox can only be collected once",
  );
  assert(game.flags.get("ep1.vuthy.left", false), "phone call confirms Vuthy has already left");
  assert(game.flags.get("ep1.vigil.started", false), "duties start the vigil");
  await wait(() => !!game.sketchbook?.written.has("SB-03") && !game.sketchbook.isBusy);
  game.sketchbook?.write("SB-03b");
  game.sketchbook?.toggle();
  await wait(() => !game.sketchbook?.isBusy && !game.gated.reading);
  assert(!game.gated.reading, "closing the book mid-entry releases world interaction");
  const use = (id: string) => game.bus.emit("interact:use", { id });
  use("interact_door_sok");
  assert(
    !!game.scene.getTransformNodeByName("col_door_sok_body")?.physicsBody,
    "Sok's room is physically locked in Act I",
  );
  use("interact_thread");
  use("interact_shed_door");
  assert(!game.flags.get("ep1.shed.opened", false), "shed requires its key");
  use("interact_sewing_box");
  use("interact_sewing_box");
  assert(game.inventory.count("shed_key") === 1, "sewing box key is unique");
  use("interact_shed_door");
  use("interact_land_deed");
  use("interact_kanha_photo");
  assert(
    game.flags.get("ep1.shed.opened", false) &&
      game.flags.get("lore.ep1.L4", false) &&
      game.flags.get("lore.ep1.L5", false),
    "shed and both lore notes work",
  );
  for (const id of [
    "interact_betel_tray",
    "interact_betel_leaves",
    "interact_areca_nut",
    "interact_lime_pot",
    "interact_altar_candle",
    "interact_incense_bundle",
  ])
    use(id);
  use("interact_altar");
  // Cycle each slot through the same interaction handlers used by E in the game.
  const order = ["betel", "areca", "lime", "candle", "incense"];
  const held = new Set(order);
  for (const slot of SLOTS) {
    const available = order.filter((item) => held.has(item));
    for (let k = 0; k <= available.indexOf(KANHA_LAYOUT[slot]); k++) use(`betel_slot_${slot}`);
    held.delete(KANHA_LAYOUT[slot]);
  }
  await wait(() => game.flags.get("ep1.betel.done", false));
  assert(
    game.inventory.count("blessed_matches") === 3,
    "offering preserves the three prepared blessed matches",
  );
  assert(
    !game.flags.get("ep1.act2.started", false),
    "offering alone cannot skip the incense cycle",
  );
  game.player.teleport(new Vector3(0, 0, -9), Math.PI);
  // Advance only the long vigil clock; the full 13-second opening plays in real time.
  act.beats.progress.update(660);
  await new Promise((resolve) => setTimeout(resolve, 250));
  assert(
    !game.flags.get("ep1.act2.started", false),
    "handover waits until Sora is beneath the tent",
  );
  await wait(() => !game.sketchbook?.isBusy);
  if (game.sketchbook?.isOpen) game.sketchbook.toggle();
  game.player.teleport(new Vector3(0, 0, -2), Math.PI);
  await wait(() => act.early.active);
  const incenseAtPassage = act.vigil.incense.fraction;
  assert(!game.flags.get("ep1.act2.started", false), "listening passage precedes Act II");
  if (act.vigil.lamp.burning) window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyF" }));
  window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyC" }));
  await wait(() => game.flags.get("ep1.early.complete", false) && !act.early.active, 60000);
  window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyC" }));
  assert(
    game.checkpoints.last?.flags["ep1.early.complete"] === true,
    "passage completed and saved",
  );
  assert(
    Math.abs(act.vigil.incense.fraction - incenseAtPassage) < 0.002,
    "forced passage does not consume incense upkeep",
  );
  await wait(() => game.flags.get("ep1.act2.started", false));
  report("Playing A2-01: wildlife silence → gust → upstairs footsteps → door.");
  await wait(() => game.flags.get("ep1.sok.unlocked", false));
  await wait(() => !game.saves.saving);
  const saved = (await saves.load("autosave")).save;
  assert(saved?.checkpoint === "CP2", "CP2 autosave written");
  assert(
    act.lights.flames
      .filter((light) => /^(tent|altar|coffin)/.test(light.name))
      .every((light) => light.intensity === 0),
    "all pavilion flame lights are out",
  );
  assert(
    act.area.container.meshes
      .filter((mesh) => TENT_FLAME_MESH.test(mesh.name))
      .every((mesh) => !mesh.isEnabled()),
    "visible flames are extinguished",
  );
  assert(!game.scene.getTransformNodeByName("col_door_sok_body"), "Sok's door collider removed");
  await new Promise((resolve) => setTimeout(resolve, 2500));
  const hit = new PhysicsRaycastResult();
  (game.scene.getPhysicsEngine() as PhysicsEngine).raycastToRef(
    new Vector3(-2.5, 3.4, -13.45),
    new Vector3(-3.5, 3.4, -13.45),
    hit,
  );
  assert(!hit.hasHit, "Havok ray passes through Sok's doorway");
  assert(
    game.flags.get("ep1.incense.neglected", false) === false,
    "transition doesn't penalise incense respect",
  );
  report("TRANSITION PASSED. Reload with ?continue to verify CP2 restoration.");
  const link = document.createElement("a");
  link.href = "?continue";
  link.textContent = "Verify checkpoint restoration";
  link.style.cssText =
    "position:fixed;bottom:12px;left:12px;z-index:1001;background:white;color:black;padding:12px";
  document.body.append(link);
}

void run().catch((error: unknown) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
