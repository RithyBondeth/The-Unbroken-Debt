import { DRAWING_VIEW_RADIUS, drawingFocus } from "../../src/player/DrawingPose";
import type { InkMarks } from "../../src/episodes/ep1/prologue/InkMarks";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { saveShot } from "../../src/debug/saveShot";

async function review() {
  if (!import.meta.env.DEV) return;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-studio-review"),
  });
  await game.start({ audio: false });
  // This visual fixture skips only the first illustration input, so every
  // previewed prop can use its real focus and interaction handler afterward.
  const drawingReview = new URLSearchParams(location.search).has("drawing");
  const ready = game.scene.onBeforeRenderObservable.add(() => {
    if (game.cutscene || game.saves.saving) return;
    ready.remove();
    if (!drawingReview) game.bus.emit("interact:use", { id: "interact_illustration" });
  });
  const views: [string, number[], number[]][] = [
    ["Drawing table", [-3, 0, -1.7], [-3, 0.914, -0.72]],
    ["Room", [-4.8, 0, -3.1], [-2.4, 1.25, -2.1]],
    ["Writing desk", [-1.65, 0, -2.35], [-0.42, 0.9, -2.45]],
    ["Telephone", [-4.95, 0, -3.55], [-5.91, 1.45, -3.55]],
    ["Window", [-3.05, 0, -2.4], [-3, 1.65, -0.3]],
    ["Bed and shelf", [-2.65, 0, -2.6], [-4.15, 1.25, -4.6]],
    ["Lantern hook", [-4.8, 0, -2.05], [-5.82, 1.66, -1.575]],
    ["Books and candle", [-3.25, 0, -3.6], [-3.26, 1.5, -4.82]],
    ["Gathered net", [-4.8, 0, -2.95], [-4.99, 2.53, -4.48]],
  ];
  async function view(feet: number[], at: number[], radius = 0.65) {
    game.stopInspecting();
    game.sketchbook?.close();
    game.satchel.close();
    game.player.teleport(new Vector3(...(feet as [number, number, number])));
    // Let the smoothed camera and physics settle before computing the aim ray.
    for (let i = 0; i < 60; i++)
      await new Promise<void>((done) => game.scene.onAfterRenderObservable.addOnce(() => done()));
    game.inspectObject(new Vector3(...(at as [number, number, number])), radius);
  }
  const nav = document.getElementById("views")!;
  let currentView = "room";
  const button = (name: string, action: () => void) => {
    const b = document.createElement("button");
    b.textContent = name;
    b.style.cssText =
      "padding:8px 12px;background:#e0d1b0;color:#211c15;border:1px solid #86704b;cursor:pointer";
    b.addEventListener("click", action);
    nav.append(b);
  };
  for (const [label, feet, target] of views)
    button(label, () => {
      currentView = label.toLowerCase().replaceAll(" ", "-");
      void view(feet, target, label === "Room" ? 2 : label === "Bed and shelf" ? 1.5 : 0.65);
    });
  button("Open drawer", () => {
    game.bus.emit("interact:use", { id: "interact_drawer" });
    void view([-1.5, 0, -2.5], [-0.88, 0.65, -2.6], 0.23);
  });
  button("Matchbox close-up", () => void view([-1.5, 0, -2.65], [-0.89, 0.665, -2.65], 0.11));
  button("Preview drawing", () => {
    const prologue = (window as unknown as { prologue?: object }).prologue;
    if (!prologue) return;
    const ink = Reflect.get(prologue, "ink") as InkMarks;
    const paper = game.scene.getMeshByName("interact_illustration");
    if (paper) game.inspectObject(drawingFocus(paper), DRAWING_VIEW_RADIUS);
    currentView = "drawing-detail";
    void ink.inkLine(12).finally(() => game.stopInspecting());
  });
  button("Free look", () => game.stopInspecting());
  button("Interact E", () => window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE" })));
  let phonePreview = false;
  button("Preview receiver", () => {
    phonePreview = !phonePreview;
    game.hands.holdPhone(phonePreview);
    game.scene.getTransformNodeByName("telephone_earpiece")?.setEnabled(!phonePreview);
    game.cutscene = phonePreview;
    game.gated.holdStill = phonePreview;
    currentView = phonePreview ? "held-receiver" : "telephone";
  });
  const capture = document.createElement("output");
  nav.append(capture);
  button("Save screenshot", () => {
    engine.setSize(1600, 1000);
    void saveShot(engine, game.camera, `studio-${currentView}`)
      .then(() => {
        capture.textContent = `Saved debug-shots/studio-${currentView}.png`;
      })
      .catch((error) => {
        capture.textContent = `Capture failed: ${String(error)}`;
      })
      .finally(() => engine.resize());
  });
  game.scene.onAfterRenderObservable.add(() => {
    document.getElementById("status")!.textContent =
      `Target: ${game.interaction.focus ?? "none"} · illustration inked=${game.flags.get("ep1.illustration.inked", false)} · lamp collected=${game.inventory.has("lamp")} · E uses the focused object · Q closes the sketchbook\nIsolated visual preview; start with Click to begin.`;
  });
}
void review().catch((error: unknown) => {
  document.getElementById("status")!.textContent = String(error);
});
