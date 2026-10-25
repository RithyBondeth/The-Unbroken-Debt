/** Khmer funeral ensemble in production lighting, with isolated review saves. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { TENT_FLAME_MESH } from "../../src/episodes/ep1/data/arrival";

async function review(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const status = document.getElementById("review-status")!;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU is required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-funeral-review"),
  });
  game.flags.set("ep1.arrival.road", true);
  game.flags.set("ep1.arrival.courtyard", true);
  game.flags.set("ep1.act2.started", true);
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  let view = "overview";
  const show = async (which: string) => {
    view = which;
    game.sketchbook?.close();
    game.stopInspecting();
    const views: Record<string, [Vector3, Vector3, number]> = {
      overview: [new Vector3(0, 0, 1.5), new Vector3(0, 1.3, -4.8), 3.1],
      altar: [new Vector3(0.1, 0, -2.65), new Vector3(0, 1.15, -4.4), 1.15],
      flowers: [new Vector3(-1.45, 0.31, -4.45), new Vector3(-2.2, 1.55, -5.68), 0.75],
      coffin: [new Vector3(-1.55, 0.31, -5), new Vector3(0, 1.1, -5.9), 1.15],
      pavilion: [new Vector3(4.8, 0, 1.6), new Vector3(0, 2.25, -4), 4.5],
      monks: [new Vector3(1.5, 0, -3.3), new Vector3(3.0, 0.85, -4.6), 1.25],
    };
    const [feet, target, radius] = views[which];
    game.player.teleport(feet);
    // Teleport updates physics first; inspection needs the next camera transform.
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    act.vigil.lamp.light();
    act.lights.hangingLevel = 1;
    act.lights.tentLevel = 1;
    for (const mesh of act.area.container.meshes)
      if (TENT_FLAME_MESH.test(mesh.name)) mesh.setEnabled(true);
    game.inspectObject(target, radius);
    status.textContent = `${which} · production lamp, materials and colour grade`;
  };
  for (const which of ["overview", "altar", "flowers", "coffin", "pavilion", "monks"])
    document.getElementById(which)!.addEventListener("click", () => {
      void show(which);
    });
  document.getElementById("capture")!.addEventListener("click", () => {
    void saveShot(engine, game.camera, `funeral-${view}`).then(() => {
      status.textContent = `Saved debug-shots/funeral-${view}.png`;
    });
  });
  await show("overview");
}
void review().catch((error: unknown) => {
  document.getElementById("review-status")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
