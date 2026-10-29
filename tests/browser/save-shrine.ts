/** Real phra phum, light and interaction rays, isolated from player checkpoints. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { GatedInput, type InputSource } from "../../src/player/InputSource";
import { YARD } from "../../src/episodes/ep1/data/forestBorder";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";

import {
  SAVE_SHRINE_POSITION,
  SAVE_SHRINE_APPROACH,
  SAVE_SHRINE_LOCATION,
  SAVE_SHRINE_ROUTE,
} from "../../src/episodes/ep1/data/saveShrine";

async function review(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const output = document.getElementById("results")!;
  const params = new URLSearchParams(location.search);
  const canvas = document.getElementById("game") as HTMLCanvasElement;
  Object.assign(canvas.style, {
    position: "fixed",
    width: "100vw",
    height: "62.5vw",
    top: "50%",
    bottom: "auto",
    transform: "translateY(-50%)",
  });
  const engine = await createEngine(canvas);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  const route: Vector3[] = [];
  const bot: InputSource = {
    readMove: (out) =>
      route.length
        ? Object.assign(out, { x: 0, z: 1, hurry: false, crouch: false })
        : game.input.readMove(out),
    consumeLook: (out) => {
      if (route.length) {
        out.yaw = 0;
        out.pitch = 0;
      } else game.input.consumeLook(out);
    },
    dispose: () => {},
  };
  Object.defineProperty(game, "gated", { value: new GatedInput(bot) });
  const saves = new SaveStore(undefined, "boon-sop-phra-phum-review");
  Object.defineProperty(game, "saves", { value: saves });
  for (const flag of [
    "ep1.arrival.road",
    "ep1.arrival.courtyard",
    "ep1.act2.started",
    "ep1.sok.unlocked",
  ])
    game.flags.set(flag, true);
  if (!params.has("listen")) game.fade.waitForEnter = async () => {};
  await game.start({ audio: params.has("listen") });
  const act = (window as unknown as { act: ActOne }).act;
  const frame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  const wait = async (condition: () => boolean, timeout = 180000) => {
    const started = performance.now();
    while (!condition()) {
      if (performance.now() - started > timeout) throw new Error("Timed out waiting for shrine");
      await frame();
    }
  };
  await wait(() => !game.cutscene, params.has("listen") ? Infinity : 180000);
  const lines: string[] = [];
  const report = (line: string) => {
    lines.push(line);
    output.textContent = lines.join("\n");
  };
  const assert = (value: unknown, line: string) => {
    if (!value) throw new Error(line);
    report(`PASS ${line}`);
  };
  if (params.has("continue")) {
    assert(
      game.resumedSave?.flags["checkpoint.location"] === SAVE_SHRINE_LOCATION,
      "spirit-house checkpoint restored",
    );
    assert(
      Vector3.Distance(game.player.feet, SAVE_SHRINE_APPROACH) < 0.3,
      "stored player position restored beside shrine",
    );
  }
  let view = "front";
  game.scene.onBeforeRenderObservable.add(() => {
    if (view === "roof") {
      // An elevated authoring view exposes all three gables and the ringed
      // spire; normal player height and the real ray return in other views.
      game.camera.position.y = game.player.feet.y + 2.85;
    }
    const target = route[0];
    if (!target) return;
    const feet = game.player.feet;
    if (Math.hypot(feet.x - target.x, feet.z - target.z) < 0.22) {
      route.shift();
      return;
    }
    game.player.yaw = Math.atan2(target.x - feet.x, target.z - feet.z);
  });
  const show = async (which: string) => {
    view = which;
    game.notebook.close();
    game.sketchbook?.close();
    game.stopInspecting();
    game.holdResolution(which === "detail" || which === "roof" ? 0.9 : null);
    game.player.teleport(
      which === "detail"
        ? SAVE_SHRINE_APPROACH
        : SAVE_SHRINE_POSITION.add(
            which === "roof" ? new Vector3(-1.0, 0, 3.0) : new Vector3(-2.0, 0, 4.8),
          ),
      Math.PI,
    );
    await frame();
    await frame();
    if (which === "dark") act.vigil.lamp.putOut();
    else act.vigil.lamp.light();
    // Refresh the camera after teleporting before inspection reads its world position.
    game.camera.getViewMatrix(true);
    game.inspectObject(
      SAVE_SHRINE_POSITION.add(
        new Vector3(0, which === "roof" ? 2.78 : which === "detail" ? 1.6 : 1.95, 0.15),
      ),
      which === "roof" ? 1.18 : which === "detail" ? 0.49 : 2.4,
    );
    output.textContent = `${which} · production lighting · E pays respects and saves\n${lines.join("\n")}`;
  };
  const use = async () => {
    await wait(() => !act.saveShrine.interacting);
    await show("detail");
    await frame();
    game.interaction.update();
    assert(
      game.interaction.focus === "interact_save_courtyard",
      "real camera ray reaches the shrine",
    );
    game.interaction.use();
    await frame();
    await frame();
  };
  let attempts = 0,
    rejectNext = false;
  const write = saves.saveCheckpoint.bind(saves);
  saves.saveCheckpoint = async (data) => {
    attempts++;
    if (rejectNext) {
      rejectNext = false;
      throw new Error("QA storage failure");
    }
    return write(data);
  };
  const save = async () => {
    const before = attempts;
    await use();
    await wait(() => attempts > before && !saves.saving);
    assert(
      game.checkpoints.last?.flags["checkpoint.location"] === SAVE_SHRINE_LOCATION,
      "save commits at the spirit house",
    );
    assert(
      (await saves.load("autosave")).save?.flags["checkpoint.spawn.z"] !== undefined,
      "save includes a restart position",
    );
  };
  const safe = (action: () => Promise<void>) => () =>
    void action().catch((error: unknown) => {
      report(`FAIL ${String(error)}`);
      console.error(error);
    });
  for (const which of ["front", "dark", "detail", "roof"])
    document.getElementById(which)!.onclick = safe(() => show(which));
  document.getElementById("save")!.onclick = safe(save);
  const walkFromGate = async () => {
    game.notebook.close();
    game.sketchbook?.close();
    game.stopInspecting();
    view = "walk";
    game.player.teleport(SAVE_SHRINE_ROUTE[0], 0);
    route.push(...SAVE_SHRINE_ROUTE.slice(1).map((at) => at.clone()));
    try {
      await wait(() => route.length === 0, 30000);
    } finally {
      route.length = 0;
    }
    assert(
      Vector3.Distance(game.player.feet, SAVE_SHRINE_APPROACH) < 0.35,
      "walkable route from main gate outside the fence reaches shrine",
    );
  };
  document.getElementById("walk")!.onclick = safe(walkFromGate);
  document.getElementById("verify")!.onclick = safe(async () => {
    await walkFromGate();
    await save();
    const initial = attempts;
    game.threatActive = true;
    await use();
    assert(attempts === initial, "active threats block checkpoint writes");
    game.threatActive = false;
    const previous = game.checkpoints.last?.savedAt;
    rejectNext = true;
    await use();
    assert(attempts === initial + 1, "storage rejection exercised");
    assert(
      game.checkpoints.last?.savedAt === previous,
      "failed save preserves the previous checkpoint",
    );
    await save();
    report("SAVE SAFETY PASSED · reload the checkpoint to verify its position.");
  });
  document.getElementById("capture")!.onclick = safe(async () => {
    engine.setSize(1600, 1000);
    await saveShot(engine, game.camera, `phra-phum-${view}`);
    report(`Saved debug-shots/phra-phum-${view}.png`);
  });
  const meshes = act.saveShrine.root.getChildMeshes();
  assert(
    !game.scene.getMeshByName("interact_save_courtyard_stand"),
    "old desk and placard removed",
  );
  assert(meshes.length < 40, "shrine stays within its draw-call budget");
  assert(
    act.saveShrine.root.position.x + 0.75 < YARD.minX &&
      act.saveShrine.root.position.z - 0.55 > YARD.maxZ,
    "whole shrine is beyond the compound fence",
  );
  assert(
    !game.scene.getTransformNodeByName("courtyard_phra_phum"),
    "previous courtyard shrine removed",
  );
  await show("front");
}
void review().catch((error: unknown) => {
  document.getElementById("results")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
