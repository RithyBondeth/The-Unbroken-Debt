/** Quiet forest review with the real lamp, fog, physics and isolated saves. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { isQualityName } from "../../src/render/QualityPresets";
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
  const device = await detectDevice();
  // `&quality=low` reviews another preset's forest density and fog on this machine.
  const quality = new URLSearchParams(location.search).get("quality");
  if (isQualityName(quality)) device.quality = quality;
  const game = new Game(engine, device);
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-forest-review"),
  });
  game.flags.set("ep1.arrival.road", true);
  game.flags.set("ep1.arrival.courtyard", true);
  game.flags.set("ep1.act2.started", true);
  game.fade.waitForClick = async () => {};
  await game.start({ audio: false });
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  let view = "path";
  const fill = new HemisphericLight("forest_review_fill", Vector3.Up(), game.scene);
  fill.diffuse = new Color3(0.72, 0.8, 0.86);
  fill.groundColor = new Color3(0.14, 0.16, 0.12);
  fill.specular = new Color3(0.08, 0.09, 0.1);
  fill.renderPriority = 8;
  fill.intensity = 0.65;
  fill.setEnabled(false);
  const fillButton = document.getElementById("fill")!;
  fillButton.addEventListener("click", () => {
    const enabled = !fill.isEnabled();
    fill.setEnabled(enabled);
    fillButton.setAttribute("aria-pressed", String(enabled));
  });
  const lampButton = document.getElementById("lamp")!;
  lampButton.addEventListener("click", () => {
    if (act.vigil.lamp.burning) act.vigil.lamp.putOut();
    else act.vigil.lamp.light();
    lampButton.setAttribute("aria-pressed", String(act.vigil.lamp.burning));
  });
  const views: Record<string, [Vector3, Vector3, number]> = {
    path: [new Vector3(-1, 0, 42), new Vector3(2, 1.8, 30), 5],
    grass: [new Vector3(2, 0, 18.5), new Vector3(4.2, 0.35, 18.5), 0.55],
    tree: [new Vector3(11, 0, 14), new Vector3(12, 0.8, 14), 0.9],
    canopy: [new Vector3(2, 0, 31), new Vector3(3, 9, 34), 4],
    road: [new Vector3(-1.5, 0, 60), new Vector3(-1.5, 2, 49), 5],
    yard: [new Vector3(10.5, 0, -1), new Vector3(17, 1.8, 1), 3],
    house: [new Vector3(-10.8, 0, -4), new Vector3(0, 3.8, -14), 8],
    rear: [new Vector3(0, 0, -20.5), new Vector3(0, 4, -30), 5],
  };
  const show = async (which: string) => {
    view = which;
    game.stopInspecting();
    game.player.teleport(views[which][0]);
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    if (view !== which) return;
    act.vigil.lamp.light();
    lampButton.setAttribute("aria-pressed", "true");
    game.inspectObject(views[which][1], views[which][2]);
    const detail = game.scene.materials.filter((m) => m.name.startsWith("M_forest_")).length;
    status.textContent = `${which} · production lamp / fog / grade · ${detail} forest materials`;
  };
  for (const which of Object.keys(views))
    document.getElementById(which)!.addEventListener("click", () => {
      void show(which);
    });
  document.getElementById("capture")!.addEventListener("click", () => {
    void saveShot(engine, game.camera, `forest-${view}`).then(() => {
      status.textContent = `Saved debug-shots/forest-${view}.png`;
    });
  });
  await show(new URLSearchParams(location.search).get("view") ?? "path");
}
void review().catch((error: unknown) => {
  document.getElementById("review-status")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
