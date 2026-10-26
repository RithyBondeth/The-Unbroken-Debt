/** Exercise real encounter triggers and the actual player controller, without changing normal saves. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DitheredTileFadeMaterialPlugin } from "@babylonjs/core/Materials/ditheredTileFadeMaterialPlugin";
import { Game } from "../../src/core/Game";
import { GatedInput, type InputSource } from "../../src/player/InputSource";
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
  let walking = false;
  const bot: InputSource = {
    readMove: (out) =>
      Object.assign(out, { x: 0, z: walking ? 1 : 0, hurry: false, crouch: false }),
    consumeLook: (out) => {
      out.yaw = 0;
      out.pitch = 0;
    },
    dispose: () => {},
  };
  Object.defineProperty(game, "gated", { value: new GatedInput(bot) });
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-encounter-regression"),
  });
  game.flags.set("ep1.arrival.road", true);
  game.flags.set("ep1.arrival.courtyard", true);
  game.fade.waitForClick = async () => {};
  await game.start({ audio: false });
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  game.player.teleport(new Vector3(0, 0, 53), Math.PI);
  act.vigil.lamp.light();
  let mode = "ready",
    blocked = 0,
    frames = 0,
    maxFrame = 0,
    intermediate = 0,
    elapsed = 0;
  let startZ = 0;
  const coverage = { lowerBound: 0, upperBound: 0 };
  const spirit = game.scene.getMeshByName("neakta_shadow_effigy")!;
  const surface = spirit
    .getChildMeshes()
    .find((mesh): mesh is Mesh => mesh instanceof Mesh && mesh.getTotalVertices() > 0)!;
  const fade = DitheredTileFadeMaterialPlugin.GetOrCreate(surface.material as PBRMaterial);
  const reset = (next: string) => {
    walking = false;
    game.stopInspecting();
    mode = next;
    blocked = 0;
    frames = 0;
    maxFrame = 0;
    intermediate = 0;
    elapsed = 0;
  };
  document.getElementById("spirit")!.addEventListener("click", () => {
    reset("spirit");
    const feet = new Vector3(0, 0, 46);
    game.player.teleport(feet, Math.atan2(5, 37.2 - feet.z));
    game.player.pitch = 0.035;
  });
  document.getElementById("courtyard")!.addEventListener("click", () => {
    reset("courtyard");
    game.flags.set("ep1.arrival.courtyard", false);
    game.player.teleport(new Vector3(0, 0, 11.5), Math.PI);
    game.player.pitch = 0;
    startZ = 11.5;
    walking = true;
  });
  document.getElementById("capture")!.addEventListener("click", () => {
    void saveShot(engine, game.camera, `encounter-${mode}`);
  });
  let previous = performance.now();
  game.scene.onBeforeRenderObservable.add(() => {
    const now = performance.now();
    const frameMs = now - previous;
    previous = now;
    if (mode === "ready" || mode.endsWith("complete")) return;
    elapsed += game.deltaSeconds;
    frames++;
    maxFrame = Math.max(maxFrame, frameMs);
    if (game.gated.holdStill) blocked++;
    fade.getFadeBoundsToRef(surface, coverage);
    if (spirit.isEnabled() && coverage.upperBound > 0 && coverage.upperBound < 1) intermediate++;
    if (walking && (game.player.feet.z <= 1 || elapsed > 9)) {
      walking = false;
      mode = "courtyard complete";
    }
    if (mode === "spirit" && elapsed > 2) mode = "spirit complete";
    const distance = mode.startsWith("courtyard")
      ? ` · travelled ${(startZ - game.player.feet.z).toFixed(2)} m`
      : ` · coverage ${coverage.upperBound.toFixed(2)} · transition frames ${intermediate}`;
    status.textContent = `${mode}${distance} · movement locked ${blocked}/${frames} frames · max frame ${maxFrame.toFixed(1)} ms`;
  });
  status.textContent = "Ready · real apparition trigger and courtyard walking controls";
}
void review().catch((error: unknown) => {
  document.getElementById("review-status")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
