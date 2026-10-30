/** Actual house, runtime furniture and lamp, with an isolated save database. */
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
  const output = document.getElementById("results")!;
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
  output.textContent = "Preparing WebGPU…";
  const engine = await createEngine(canvas);
  if (!engine) throw new Error("WebGPU is required");
  useLocalDecoders();
  output.textContent = "Detecting graphics preset…";
  const game = new Game(engine, await detectDevice());
  output.textContent = "Loading physics, fonts and hand models…";
  let loadedMeshes = 0;
  const loading = game.scene.onNewMeshAddedObservable.add(() => {
    if (++loadedMeshes % 100 === 0)
      output.textContent = `Loading village geometry… ${loadedMeshes} meshes`;
  });
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-house-placement-review"),
  });
  for (const flag of [
    "ep1.arrival.road",
    "ep1.arrival.courtyard",
    "ep1.act2.started",
    "ep1.sok.unlocked",
  ])
    game.flags.set(flag, true);
  game.fade.waitForEnter = async () => {};
  await game.start({ audio: false });
  loading.remove();
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  const checks: string[] = [];
  // Inspect the final runtime meshes, after the imported placeholders were replaced.
  for (const name of ["desk_foot", "sok_stand_foot"]) {
    const feet = game.scene.meshes.filter((m) => m.name === name && m.isEnabled());
    if (feet.length !== 4) throw new Error(`${name}: expected four feet, got ${feet.length}`);
    for (const mesh of feet) {
      mesh.computeWorldMatrix(true);
      const base = mesh.getBoundingInfo().boundingBox.minimumWorld.y;
      if (Math.abs(base - 2.5) > 0.001)
        throw new Error(`${name} floats above floor: base ${base.toFixed(5)}`);
    }
    checks.push(`PASS all four ${name.replaceAll("_", " ")} bases touch the floor`);
  }
  const views: Record<string, { feet: number[]; target: number[]; radius: number }> = {
    "storage-wall": { feet: [-10.5, 0, -10.8], target: [-10.5, 1.2, -13.02], radius: 1.35 },
    stairs: { feet: [-10.1, 0, -9.3], target: [-7.5, 1.6, -10.75], radius: 1.6 },
    spade: { feet: [1.7, 0, -9], target: [2.85, 0.65, -10.15], radius: 0.85 },
    traps: { feet: [3.2, 0, -16.6], target: [4.6, 1.65, -18.16], radius: 0.85 },
    "ground-traps": { feet: [-1.5, 0, -15.7], target: [-2.6, 0.45, -17.1], radius: 0.9 },
    umbrellas: { feet: [2.8, 0, 0.8], target: [3.85, 0.55, -0.8], radius: 0.85 },
    phone: { feet: [1.75, 2.5, -17.2], target: [2.7, 3.7, -17.2], radius: 0.35 },
    doorway: { feet: [1.8, 2.5, -15.6], target: [2.97, 3.7, -15.5], radius: 0.95 },
    kitchen: { feet: [4.8, 2.5, -13.1], target: [5.2, 3.2, -12.6], radius: 1.3 },
    hall: { feet: [-1.8, 2.5, -15.5], target: [-2.85, 3.8, -15.85], radius: 0.8 },
    mats: { feet: [1.3, 2.5, -13], target: [2.15, 2.62, -12.7], radius: 1 },
    altar: { feet: [0, 2.5, -14.8], target: [0, 3.5, -17.6], radius: 1.65 },
    "altar-detail": { feet: [0, 2.5, -16.3], target: [0, 3.99, -17.7], radius: 0.8 },
    "leaf-offering": { feet: [0.65, 2.5, -16.8], target: [0, 3.69, -17.56], radius: 0.16 },
    bedroom: { feet: [4.1, 2.5, -17], target: [4.7, 2.9, -15.9], radius: 1.4 },
    desk: { feet: [-4.2, 2.5, -16.1], target: [-5.2, 2.9, -17.1], radius: 1.3 },
    gramophone: { feet: [-4.2, 2.5, -15], target: [-5.4, 2.95, -15.6], radius: 1.1 },
    wood: { feet: [1.9, 2.5, -16], target: [2.94, 3.75, -16], radius: 0.6 },
    cobweb: { feet: [4.7, 0, -11], target: [5.62, 1.85, -10.1], radius: 0.5 },
    hammock: { feet: [3.7, 0, -12], target: [6, 1.05, -12], radius: 1.85 },
    "hammock-knot": { feet: [4.8, 0, -10.5], target: [6, 1.36, -10.29], radius: 0.4 },
  };
  let view = new URLSearchParams(location.search).get("view") ?? "altar";
  let phonePreview = false;
  const previewReceiver = (active: boolean) => {
    phonePreview = active;
    game.hands.holdPhone(active);
    game.scene.getTransformNodeByName("arrival_receiver")!.setEnabled(!active);
    game.cutscene = active;
    game.gated.holdStill = active;
    document.getElementById("receiver")!.setAttribute("aria-pressed", String(active));
  };
  if (!(view in views)) view = "altar";
  const show = async (name: string) => {
    view = name;
    previewReceiver(false);
    game.sketchbook?.close();
    game.stopInspecting();
    const spec = views[name];
    game.player.teleport(Vector3.FromArray(spec.feet));
    act.vigil.lamp.light();
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    if (view !== name) return;
    game.inspectObject(Vector3.FromArray(spec.target), spec.radius);
    output.textContent = `${checks.join("\n")}\nViewing ${name} · production geometry and lighting`;
  };
  for (const name of Object.keys(views))
    document.getElementById(name)!.onclick = () => void show(name);
  document.getElementById("receiver")!.onclick = async () => {
    if (view !== "phone") await show("phone");
    previewReceiver(!phonePreview);
    if (phonePreview) game.inspectObject(Vector3.FromArray(views.phone.target), 0.65);
    output.textContent = `${checks.join("\n")}\n${phonePreview ? "Receiver lifted · cord follows the hand" : "Receiver returned · cord reconnects to the hook"}`;
  };
  let cordCheckAge = 0;
  game.scene.onAfterRenderObservable.add(() => {
    cordCheckAge += game.deltaSeconds;
    if (view !== "phone" || cordCheckAge < 0.5) return;
    cordCheckAge = 0;
    const mesh = game.scene.getMeshByName("arrival_phone_cord")!;
    const socket = game.scene.getTransformNodeByName("arrival_phone_cord_terminal")!;
    const rest = game.scene.getTransformNodeByName("arrival_phone_cord_rest")!;
    const end = game.hands.phoneCordPoint ?? rest.getAbsolutePosition();
    const vertices = mesh.getVerticesData("position")!;
    const distance = (at: Vector3) => {
      let nearest = Infinity;
      for (let i = 0; i < vertices.length; i += 3)
        nearest = Math.min(nearest, Vector3.Distance(at, Vector3.FromArray(vertices, i)));
      return nearest;
    };
    const error = Math.max(distance(socket.getAbsolutePosition()), distance(end));
    output.textContent = `${checks.join("\n")}\n${error < 0.003 ? "PASS" : "FAIL"} telephone cord ${phonePreview ? "follows the held receiver" : "connects to the resting receiver"} · endpoint gap ${(error * 1000).toFixed(2)} mm`;
  });
  document.getElementById("capture")!.onclick = () => {
    const captureView = phonePreview ? "phone-held" : view;
    void saveShot(engine, game.camera, `house-${captureView}`).then(() => {
      output.textContent += `\nSaved debug-shots/house-${captureView}.png`;
    });
  };
  await show(view);
}
void review().catch((error: unknown) => {
  document.getElementById("results")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
