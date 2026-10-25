/** Authored village shrine in production lighting, with isolated review saves. */
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
    value: new SaveStore(undefined, "boon-sop-shrine-review"),
  });
  game.flags.set("ep1.arrival.road", true);
  game.flags.set("ep1.arrival.courtyard", true);
  game.flags.set("ep1.act2.started", true);
  game.fade.waitForClick = async () => {};
  await game.start({ audio: false });
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  let view = "shrine";
  const show = async (which: string) => {
    view = which;
    game.sketchbook?.close();
    game.stopInspecting();
    const views: Record<string, [Vector3, Vector3, number]> = {
      shrine: [new Vector3(0.3, 0, 35), new Vector3(4, 1.15, 34.9), 2.5],
      statues: [new Vector3(1.8, 0, 35.0), new Vector3(4.12, 1.1, 34.9), 0.85],
      details: [new Vector3(2.8, 0, 35.1), new Vector3(3.65, 0.48, 34.9), 0.75],
      chicken: [new Vector3(2.75, 0, 35.3), new Vector3(3.62, 0.45, 35.15), 0.28],
      house: [new Vector3(2.5, 0, 36.45), new Vector3(4.02, 1.55, 36.45), 0.7],
      packets: [new Vector3(3.2, 0, 25.2), new Vector3(4.8, 0.045, 25.5), 0.38],
    };
    const [feet, target, radius] = views[which];
    game.player.teleport(feet);
    // Teleport updates physics first; inspection needs the next camera transform.
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    act.vigil.lamp.light();
    game.inspectObject(target, radius);
    status.textContent = `${which} · production lamp, materials and colour grade`;
  };
  for (const which of ["shrine", "statues", "details", "house", "chicken", "packets"])
    document.getElementById(which)!.addEventListener("click", () => {
      void show(which);
    });
  document.getElementById("capture")!.addEventListener("click", () => {
    void saveShot(engine, game.camera, `shrine-${view}`).then(() => {
      status.textContent = `Saved debug-shots/shrine-${view}.png`;
    });
  });
  await show("shrine");
}
void review().catch((error: unknown) => {
  document.getElementById("review-status")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
