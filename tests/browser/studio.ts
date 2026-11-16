import { DRAWING_VIEW_RADIUS, drawingFocus } from "@/player/drawingPose";
import type { InkMarks } from "@/episodes/ep1/prologue/InkMarks";
import { Game } from "@/core/Game";
import { createEngine } from "@/render/createEngine";
import { detectDevice } from "@/render/detectDevice";
import { useLocalDecoders } from "@/render/decoders";
import { SaveStore } from "@/systems/saves/SaveStore";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { saveShot } from "@/debug/saveShot";

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
  // Runtime coordinates are Blender's (-x, z, -y) (tools/areas/ep1_area_studio.py).
  const views: [string, number[], number[]][] = [
    ["Drawing table", [-3, 0, -1.7], [-3, 0.914, -0.72]],
    ["Room", [-2.3, 0, -5.4], [-1.6, 1.25, -1.5]],
    ["Writing desk", [-1.65, 0, -2.35], [-0.42, 0.9, -2.45]],
    ["Posters", [-2.6, 0, -2.6], [-4.58, 1.9, -2.6]],
    ["Balcony doors", [-3.0, 0, -2.4], [-3.4, 1.65, 0.13]],
    ["Books and candle", [-3.0, 0, -4.9], [-3.0, 1.45, -5.85]],
    ["Airwell", [-0.6, 0, -6.5], [-2.3, 1.0, -8.2]],
    ["Telephone", [-2.95, 0, -6.9], [-2.95, 1.47, -6.2]],
    ["Lantern hook", [-2.42, 0, -6.9], [-2.42, 1.4, -6.25]],
    ["Stair gate", [-3.97, 0, -6.55], [-3.97, 0.6, -7.0]],
    ["Bed and altar", [-1.6, 0, -10.2], [-2.5, 1.2, -13.0]],
    ["Gathered net", [-2.6, 0, -11.2], [-3.85, 2.6, -12.95]],
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
      void view(
        feet,
        target,
        ["Room", "Airwell"].includes(label) ? 2 : label === "Bed and altar" ? 1.5 : 0.65,
      );
    });
  button("Drawer hint", () => {
    const drawer = game.scene.getMeshByName("interact_drawer");
    if (!drawer) return;
    currentView = "drawer-hint";
    void view([-1.5, 0, -2.5], drawer.getAbsolutePosition().asArray(), 0.4);
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
