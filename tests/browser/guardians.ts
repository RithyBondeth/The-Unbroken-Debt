/** Production guardians and player lamp; isolated saves, no encounter or lighting substitutes. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";

async function review(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const status = document.getElementById("review-status")!;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU is required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-guardian-review"),
  });
  game.flags.set("ep1.arrival.road", true);
  game.flags.set("ep1.arrival.courtyard", true);
  game.flags.set("ep1.act2.started", true);
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  // Wait for the act's initial handover to finish before placing the review camera.
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  let view = "front";
  const show = async (which: string) => {
    view = which;
    game.sketchbook?.close();
    game.stopInspecting();
    const raised = which === "raised";
    const target = raised ? new Vector3(-4.4, 1.25, 60.8) : new Vector3(1.4, 1.35, 61);
    const distance = which === "road" ? 4 : 1.65;
    const feet = target.add(new Vector3(which === "side" ? -1.15 : 0, -target.y, distance));
    game.player.teleport(feet);
    act.vigil.lamp.light();
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    if (view !== which) return;
    game.inspectObject(target, which === "road" ? 2.5 : 1.1);
    const guardians = game.scene.meshes.filter((mesh) => /^tingmong_\d+/.test(mesh.name));
    status.textContent = `${which}: ${guardians.length} guardian material sections · production lamp and colour grade`;
  };
  for (const which of ["front", "side", "road", "raised"])
    document.getElementById(which)!.addEventListener("click", () => {
      void show(which);
    });
  document.getElementById("capture")!.addEventListener("click", () => {
    void saveShot(engine, game.camera, `guardian-${view}`).then(() => {
      status.textContent = `Saved debug-shots/guardian-${view}.png`;
    });
  });
  await show("front");
}
void review().catch((error: unknown) => {
  document.getElementById("review-status")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
