/** Actual village / interaction / IndexedDB checks, using a separate test database. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { CHEST_ITEMS } from "../../src/episodes/ep1/act3/ChestProgress";
import { CP5_FEET } from "../../src/episodes/ep1/data/hunt";
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
    if (performance.now() - start > ms) throw new Error("Timed out waiting for chest sequence");
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
    saves = new SaveStore(
      undefined,
      which === "gallery" ? "boon-sop-chest-gallery" : "boon-sop-chest-verification",
    );
  Object.defineProperty(game, "saves", { value: saves });
  if (["entry", "gallery", "coffin"].includes(which)) {
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
    save.flags["ep1.coffin.triggered"] = which !== "coffin";
    if (which === "coffin") {
      save.flags["ep1.chest.bronze_token.taken"] = true;
      save.inventory.bronze_token = 1;
    }
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
    if (which === "gallery") {
      save.flags["ep1.chest.planksOpen"] = true;
      save.flags["ep1.chest.unlocked"] = true;
      delete save.inventory.brass_key;
    }
    await saves.save("autosave", save);
  }
  report("Click to begin. Actual village and a separate test save database.");
  const loading = setTimeout(
    () =>
      report(
        `Loading diagnostic: ${game.scene.meshes.length} meshes; player ${game.player ? "ready" : "pending"}`,
      ),
    8000,
  );
  await game.start();
  clearTimeout(loading);
  const act = (window as unknown as { act: ActOne }).act,
    c = act.chest,
    m = c.models;
  await wait(() => !game.cutscene, 300000);
  async function freeHands() {
    game.stopInspecting();
    game.satchel.close();
    await pause(150);
    await wait(() => !game.sketchbook?.isBusy);
    game.sketchbook?.close();
    await wait(() => !game.gated.reading && !game.sketchbook?.isBusy);
  }
  async function aim(feet: Vector3, at: Vector3, radius = 0.42) {
    await freeHands();
    game.player.teleport(feet);
    await pause();
    game.inspectObject(at, radius);
    await pause();
  }
  const viewChest = () => aim(new Vector3(-4.5, 2.5, -11.82), new Vector3(-4.5, 2.49, -12.4), 0.55);
  const viewBody = () => aim(new Vector3(1.43, 0.56, -5.04), new Vector3(0.15, 1.02, -5.9), 1.05);
  function crouch(on: boolean) {
    window.dispatchEvent(
      new KeyboardEvent(on ? "keydown" : "keyup", { code: "KeyC", key: "c", bubbles: true }),
    );
  }
  document.getElementById("chest")!.onclick = () => void viewChest();
  document.getElementById("body")!.onclick = () => void viewBody();
  document.getElementById("results-toggle")!.onclick = () => (output.hidden = !output.hidden);
  if (which === "coffin" || which === "coffin-reload") {
    const p = c.coffin.progress;
    if (which === "coffin-reload") {
      assert(p.phase === "closed", "closed coffin restores from disk without another scare");
      assert(game.flags.get("ep1.coffin.headTurned", false), "hidden head turn is saved");
      await viewBody();
      await saveShot(engine, game.camera, "coffin_closed_reload");
      report("COFFIN REVEAL → HOLD / RELEASE → CLOSE → RELOAD PASSED");
      return;
    }
    assert(p.phase === "waiting", "coffin starts shut before Sora approaches");
    await viewBody();
    await wait(() => p.phase === "open");
    assert(c.body.root.position.y < 1, "Sok rests in the hollow coffin below the rim");
    await pause(2300);
    await saveShot(engine, game.camera, "coffin_reveal");
    await aim(new Vector3(0.65, 0.56, -5.05), c.body.closeGrip.getAbsolutePosition(), 0.36);
    assert(
      game.interaction.focus === "interact_coffin_close",
      `near-rim handle is reachable (${game.interaction.focus})`,
    );
    const key = (down: boolean) =>
      window.dispatchEvent(
        new KeyboardEvent(down ? "keydown" : "keyup", { code: "KeyE", key: "e", bubbles: true }),
      );
    key(true);
    await pause(900);
    key(false);
    await pause(1100);
    assert(
      !game.flags.get("ep1.coffin.closed", false) && p.closing === 0,
      "release stops closing and yields the lid",
    );
    key(true);
    await wait(() => game.flags.get("ep1.coffin.closed", false));
    key(false);
    assert(
      game.flags.get("ep1.coffin.headTurned", false),
      "head changes only after the lid covers it",
    );
    await saveShot(engine, game.camera, "coffin_closed");
    await wait(() => !saves.saving);
    link("coffin-reload", "Reload the closed coffin");
    return;
  }
  if (which === "gallery") {
    await viewChest();
    crouch(true);
    await pause(600);
    game.inspectObject(new Vector3(-4.5, 2.27, -12.52), 0.5);
    await pause(700);
    await saveShot(engine, game.camera, "sok_chest_final");
    report(
      "Detailed chest, token, map and sealed slip inspection fixture. Player saves untouched.",
    );
    document.getElementById("body")!.onclick = () =>
      void (async () => {
        crouch(false);
        await viewBody();
        await pause(700);
        await saveShot(engine, game.camera, "sok_corpse_final");
      })();
    // Inspection controls exercise the actual imported morphs without altering player saves.
    for (let pose = 0; pose < 5; pose++) {
      const button = document.createElement("button");
      button.textContent = `Corpse pose ${pose}`;
      document.querySelector("nav")!.append(button);
      button.onclick = () =>
        void (async () => {
          crouch(false);
          await viewBody();
          game.cutscene = true;
          game.flags.set("ep1.corpse.pose", pose);
          game.flags.set("ep1.corpse.seen", false);
          game.flags.set("ep1.corpse.unseenSeconds", 0);
          c.body.pose(pose);
          await pause(700);
          await saveShot(engine, game.camera, `sok_corpse_pose_${pose}`);
          report(`Imported anatomical model, pose ${pose}`);
        })();
    }
    const closeup = document.createElement("button");
    closeup.textContent = "Face close-up";
    document.querySelector("nav")!.append(closeup);
    closeup.onclick = () =>
      void (async () => {
        crouch(false);
        await aim(new Vector3(1.3, 0.56, -5.4), new Vector3(0.71, 1.06, -5.9), 0.26);
        await pause(700);
        await saveShot(engine, game.camera, "sok_corpse_face");
        report("Close-up captured under the actual tent lighting");
      })();
    return;
  }
  if (which === "entry") {
    await viewBody();
    const original = c.corpse.pose;
    assert(c.body.observed(game.camera), "coffin and body are in the camera frustum");
    await pause(4500);
    assert(c.corpse.pose === original, "corpse stays completely still while observed");
    await saveShot(engine, game.camera, "sok_corpse_resting");
    game.inspectObject(new Vector3(6, 1.6, -3), 0.8);
    await pause();
    assert(
      !c.body.observed(game.camera),
      "turning away removes every possible corpse pose from view",
    );
    await wait(() => c.corpse.pose === original + 1);
    await pause(4300);
    assert(
      c.corpse.pose === original + 1,
      "unseen corpse advances once and waits to be seen again",
    );
    await viewBody();
    await saveShot(engine, game.camera, "sok_corpse_changed");
    // Every actual mesh in every pose must fit the conservative visibility box.
    game.cutscene = true;
    for (let pose = 0; pose < 5; pose++) {
      c.body.pose(pose);
      for (const mesh of c.body.root.getChildMeshes()) {
        mesh.refreshBoundingInfo({ applyMorph: true });
        mesh.computeWorldMatrix(true);
        const b = mesh.getBoundingInfo().boundingBox;
        if (!(
          b.minimumWorld.x >= -1.04 &&
          b.maximumWorld.x <= 1.04 &&
          b.minimumWorld.y >= 0.69 &&
          b.maximumWorld.y <= 2.1 &&
          b.minimumWorld.z >= -6.4 &&
          b.maximumWorld.z <= -5.25
        ))
          throw new Error(`pose ${pose}: ${mesh.name} extends outside the visibility guard`);
      }
    }
    c.body.pose(c.corpse.pose);
    game.cutscene = false;
    await viewChest();
    assert(
      game.interaction.focus === "interact_loose_planks",
      `loose boards are reachable (${game.interaction.focus})`,
    );
    game.interaction.use();
    await wait(() => m.planksReady);
    assert(
      c.progress.planksOpen && !c.progress.unlocked,
      "boards lift independently of the chest lock",
    );
    await saveShot(engine, game.camera, "sok_hidden_chest_revealed");
    await wait(() => !saves.saving);
    link("unlock", "Reload the lifted floorboards");
    return;
  }
  assert(c.progress.planksOpen && m.planksReady, "lifted boards restore from disk");
  if (which === "unlock") {
    assert(game.inventory.count("brass_key") === 1, "assembled key survives the plank-only reload");
    await viewChest();
    assert(
      game.interaction.focus === "interact_hidden_chest",
      `recessed chest lock is reachable (${game.interaction.focus})`,
    );
    game.interaction.use();
    await wait(() => m.lidReady);
    assert(
      c.progress.unlocked && !game.inventory.has("brass_key"),
      "opening the chest consumes the assembled key exactly once",
    );
    crouch(true);
    await pause(600);
    game.inspectObject(m.token.getAbsolutePosition(), 0.38);
    await pause();
    await saveShot(engine, game.camera, "sok_chest_open_contents");
    assert(
      game.interaction.focus === "interact_chest_bronze_token",
      `token is reachable inside the hollow chest (${game.interaction.focus})`,
    );
    game.interaction.use();
    game.interaction.use();
    assert(
      game.inventory.count("bronze_token") === 1 && !m.token.isEnabled(),
      "token is collected once and disappears",
    );
    crouch(false);
    await wait(() => !saves.saving);
    link("contents", "Reload the open chest and collected token");
    return;
  }
  assert(
    c.progress.unlocked && !m.token.isEnabled() && game.inventory.count("bronze_token") === 1,
    "open chest and partial pickups restore",
  );
  if (which === "contents") {
    await viewChest();
    crouch(true);
    await pause(550);
    for (const item of ["seal_map", "folded_slip"] as const) {
      game.inspectObject(m.pickups[item].getAbsolutePosition(), 0.36);
      await pause();
      assert(
        game.interaction.focus === `interact_chest_${item}`,
        `${item} is physically reachable`,
      );
      game.interaction.use();
      game.interaction.use();
      assert(game.inventory.count(item) === 1, `${item} is granted once`);
    }
    crouch(false);
    await wait(
      () => c.progress.ready && game.flags.get("sketchbook.written", "").includes("SB-07"),
    );
    assert(
      game.flags.get("ep1.slip.unread", false) && !game.flags.has("ep1.slip.read"),
      "slip stays sealed and unread",
    );
    assert(
      game.flags.get<string>("ep1.checkpoint", "") === "CP5" &&
        !game.flags.get("ep1.seal1.broken", false),
      "preparation keeps CP5 and does not perform the future ritual",
    );
    await freeHands();
    game.player.teleport(new Vector3(1.25, 0, -10.8));
    await wait(() => act.hunt.brain.elapsed > 0.1);
    act.hunt.brain.position.copyFrom(game.player.feet);
    act.hunt.brain.position.y = 0;
    await wait(() => act.hunt.restarts === 1);
    assert(Vector3.Distance(game.player.feet, CP5_FEET) < 0.3, "later catch returns to CP5");
    assert(
      c.progress.ready &&
        c.progress.unlocked &&
        CHEST_ITEMS.every((id) => game.inventory.count(id) === 1),
      "CP5 retry retains all chest discoveries",
    );
    assert(!game.inventory.has("brass_key"), "CP5 retry does not resurrect the consumed key");
    await wait(() => !saves.saving);
    link("complete", "Reload ritual preparation");
    return;
  }
  assert(
    c.progress.ready && CHEST_ITEMS.every((id) => game.inventory.count(id) === 1),
    "complete ritual preparation restores without duplicate loot",
  );
  assert(
    CHEST_ITEMS.every((id) => !m.pickups[id].isEnabled()),
    "looted objects stay absent",
  );
  assert(game.flags.get("sketchbook.written", "").includes("SB-07"), "ritual objective is saved");
  assert(
    game.flags.get("ep1.slip.unread", false) && !game.flags.has("ep1.slip.read"),
    "sealed slip stays unread after reload",
  );
  assert(c.corpse.pose > 0, "corpse pose progress restores");
  report("PLANKS → CHEST → THREE DISCOVERIES → CP5 RETRY → RELOAD PASSED");
}
void verify().catch((error) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
