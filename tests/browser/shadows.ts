/** Real shadow models in the production village, with isolated save storage. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
import { ShadowFigure } from "../../src/episodes/ep1/entities/ShadowFigure";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";

async function review(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const status = document.getElementById("review-status")!;
  const canvas = document.getElementById("game") as HTMLCanvasElement;
  if (new URLSearchParams(location.search).has("landscape")) {
    Object.assign(canvas.style, {
      position: "fixed",
      width: "100vw",
      height: "62.5vw",
      top: "50%",
      bottom: "auto",
      transform: "translateY(-50%)",
    });
  }
  const engine = await createEngine(canvas);
  if (!engine) throw new Error("WebGPU is required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-shadow-review"),
  });
  game.flags.set("ep1.arrival.road", true);
  game.flags.set("ep1.arrival.courtyard", true);
  game.flags.set("ep1.act2.started", true);
  game.fade.waitForEnter = async () => {};
  const warmup = ShadowFigure.warmup.bind(ShadowFigure);
  ShadowFigure.warmup = async (scene) => {
    status.textContent = "Preparing spirit materials…";
    await warmup(scene);
    status.textContent = "Preparing village views…";
  };
  await game.start({ audio: false });
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  // Same constructor, height and posture used by the production forest apparition.
  const forest = new ShadowFigure(game.scene, "forest_review", 2.5);
  forest.root.position.set(5, 0, 37.2);
  forest.root.rotation.y = -0.58;
  let view = "forest",
    seconds = 0;
  game.scene.onBeforeRenderObservable.add(() => {
    seconds += game.deltaSeconds;
    forest.animate(seconds);
    if (view === "mask" || view === "hall")
      act.walker.models.pose(new Vector3(-1.65, 2.5, -13.8), new Vector3(0, 0, -1), seconds);
    const glow = game.scene.getLightByName("neakta_glow");
    if (glow) {
      glow.setEnabled(true);
      glow.intensity = view === "forest" || view === "profile" ? 4 : 0;
    }
  });
  const show = async (which: string) => {
    view = which;
    game.sketchbook?.close();
    game.stopInspecting();
    forest.root.setEnabled(which === "forest" || which === "profile");
    act.walker.models.walker.setEnabled(which === "hall" || which === "mask");
    act.hunt.models.roamer.setEnabled(which === "under");
    const views: Record<string, [Vector3, Vector3, number]> = {
      forest: [new Vector3(2.5, 0, 39.7), new Vector3(5, 1.3, 37.2), 1.55],
      profile: [new Vector3(7.8, 0, 38.8), new Vector3(5, 1.3, 37.2), 1.5],
      hall: [new Vector3(-1.65, 2.5, -21.05), new Vector3(-1.65, 3.65, -13.8), 2.3],
      mask: [new Vector3(-1.65, 2.5, -15.4), new Vector3(-1.62, 4.58, -13.8), 0.3],
      under: [new Vector3(-2.4, 0, -12.8), new Vector3(-1.5, 0.96, -10.65), 1.35],
    };
    const [feet, target, radius] = views[which];
    act.walker.models.pose(new Vector3(-1.65, 2.5, -13.8), new Vector3(0, 0, -1), 0);
    act.hunt.models.pose(
      new Vector3(-1.5, 0, -10.65),
      new Vector3(0.2, 0, -1),
      0,
      which === "under" ? 1 : 0,
    );
    game.player.teleport(feet);
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    if (view !== which) return;
    act.vigil.lamp.light();
    game.inspectObject(target, radius);
    status.textContent = `${which} · production lamp and colour grade · authored ancestral effigy`;
  };
  for (const which of ["forest", "hall", "under", "mask", "profile"])
    document.getElementById(which)!.addEventListener("click", () => {
      void show(which);
    });
  document.getElementById("capture")!.addEventListener("click", () => {
    engine.setSize(1600, 1000);
    void saveShot(engine, game.camera, `shadow-${view}`).then(() => {
      status.textContent = `Saved debug-shots/shadow-${view}.png`;
    });
  });
  await show("forest");
}
void review().catch((error: unknown) => {
  document.getElementById("review-status")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
