/**
 * Development-only screenshot tour of every Episode 1 location, in story order,
 * with production geometry, lighting and post-processing. `?area=village`
 * (default) or `?area=studio`; `&run` saves every view to debug-shots/tour-*.png.
 * Uses its own save database and never writes player saves.
 */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { isQualityName } from "../../src/render/QualityPresets";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";

/** Feet position and the point to look at, in Babylon world space. */
type View = [feet: [number, number, number], target: [number, number, number]];

const VILLAGE: Record<string, View> = {
  "01-forest-path": [
    [0, 0, 53],
    [0, 1.3, 40],
  ],
  "02-path-shrine": [
    [0, 0, 46],
    [5, 1.25, 37.2],
  ],
  "03-approach": [
    [0, 0, 24],
    [0, 1.3, 6],
  ],
  "04-courtyard": [
    [0, 0, 8],
    [0, 1.3, -10],
  ],
  "05-tent-aisle": [
    [0, 0, -2],
    [0, 1.1, -5],
  ],
  "05b-sok-portrait": [
    [0.05, 0, -3.4],
    [0, 1.12, -4.4],
  ],
  "06-house-front": [
    [5, 0, -3],
    [0, 3, -12],
  ],
  "07-house-side": [
    [-9, 0, -8],
    [-3, 2.4, -14],
  ],
  "08-hall-altar": [
    [0, 2.5, -18.6],
    [0, 3.5, -21.6],
  ],
  "09-hall-length": [
    [3.5, 2.5, -13.2],
    [-4, 3.3, -14.5],
  ],
  "10-sok-room": [
    [-4.15, 2.5, -13.55],
    [-5.6, 3.1, -16],
  ],
  "11-sok-desk": [
    [-4.2, 2.5, -16.1],
    [-5.2, 2.9, -17.1],
  ],
  "12-bedroom": [
    [4.1, 2.5, -17],
    [4.7, 2.9, -15.9],
  ],
  "13-kitchen": [
    [4.8, 2.5, -13.1],
    [5.4, 3.2, -12.4],
  ],
  "14-under-entry": [
    [1.25, 0, -9.15],
    [0, 0.8, -14],
  ],
  "15-under-rear": [
    [-3.6, 0, -16.6],
    [1, 0.8, -12],
  ],
  "16-behind-house": [
    [0, 0, -22],
    [0, 1.6, -34],
  ],
  "17-ritual-burner": [
    [0, 0, -2.5],
    [0, 0.6, -3.55],
  ],
};

async function tour(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search);
  const studio = params.get("area") === "studio";
  const output = document.getElementById("results")!;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU is required");
  useLocalDecoders();
  const device = await detectDevice();
  const quality = params.get("quality");
  if (isQualityName(quality)) device.quality = quality;
  const game = new Game(engine, device);
  Object.defineProperty(game, "saves", { value: new SaveStore(undefined, "boon-sop-tour") });
  if (!studio) {
    // Quiet vigil after the call: the house open, nothing hunting.
    for (const flag of ["ep1.arrival.road", "ep1.arrival.courtyard", "ep1.vigil.started"])
      game.flags.set(flag, true);
    params.set("start", "act1");
    history.replaceState(null, "", `${location.pathname}?${params}`);
  }
  game.fade.waitForEnter = async () => {};
  await game.start({ audio: false });
  // Game.update releases its reading-resolution floor each frame during play.
  if (params.has("fixed")) game.scene.onBeforeRenderObservable.add(() => game.holdResolution(1));
  const deadline = performance.now() + 20000;
  while (game.cutscene && performance.now() < deadline)
    await new Promise((resolve) => setTimeout(resolve, 100));
  game.cutscene = false;

  const frames = (n: number) =>
    new Promise<void>((resolve) => {
      const step = (left: number) =>
        left ? requestAnimationFrame(() => step(left - 1)) : resolve();
      step(n);
    });
  const aim = (feet: Vector3, target: Vector3) => {
    game.player.teleport(feet);
    const eye = feet.add(new Vector3(0, 1.58, 0));
    const d = target.subtract(eye);
    game.player.yaw = Math.atan2(d.x, d.z);
    game.player.pitch = Math.atan2(-d.y, Math.hypot(d.x, d.z));
  };

  const views: Record<string, () => void> = {};
  if (studio) {
    const spawn = game.camera.globalPosition.subtract(new Vector3(0, 1.58, 0));
    for (const [i, yaw] of [0, 90, 180, 270].entries())
      views[`studio-${i + 1}-yaw${yaw}`] = () => {
        game.player.teleport(spawn);
        game.player.yaw = (yaw * Math.PI) / 180;
        game.player.pitch = 0.12;
      };
  } else {
    const act = (window as unknown as { act: ActOne }).act;
    for (const [name, [feet, target]] of Object.entries(VILLAGE))
      views[name] = () => {
        aim(Vector3.FromArray(feet), Vector3.FromArray(target));
        act.vigil.lamp.light();
      };
  }

  const nav = document.getElementById("views")!;
  let currentView = Object.keys(views)[0];
  const prefix = params.get("capture") ?? "tour";
  const captureName = (name: string) => {
    const lit = studio || (window as unknown as { act: ActOne }).act.vigil.lamp.burning;
    return `${prefix}-${name}${lit ? "" : "-unlit"}`;
  };
  const show = async (name: string, save: boolean) => {
    currentView = name;
    views[name]();
    // Let TAA, eye adaptation and fog settle before judging or saving.
    await frames(90);
    if (save) await saveShot(engine, game.camera, captureName(name));
    output.textContent = `${name} · ${game.preset.name}${save ? ` → debug-shots/${prefix}-${name}.png` : ""}`;
  };
  for (const name of Object.keys(views)) {
    const button = document.createElement("button");
    button.textContent = name;
    button.onclick = () => void show(name, false);
    nav.append(button);
  }
  if (!studio) {
    const lamp = document.createElement("button");
    lamp.textContent = "Toggle player lamp";
    lamp.onclick = () => {
      const act = (window as unknown as { act: ActOne }).act;
      if (act.vigil.lamp.burning) act.vigil.lamp.putOut();
      else act.vigil.lamp.light();
    };
    nav.append(lamp);
  }
  const capture = document.createElement("button");
  capture.textContent = "Save screenshot";
  capture.onclick = () => {
    const name = captureName(currentView);
    void saveShot(engine, game.camera, name).then(() => {
      output.textContent = `Saved debug-shots/${name}.png`;
    });
  };
  nav.append(capture);
  if (params.has("run")) {
    for (const name of Object.keys(views)) await show(name, true);
    output.textContent = `DONE ${Object.keys(views).length} views`;
  } else
    await show(
      params.get("view") && views[params.get("view")!]
        ? params.get("view")!
        : Object.keys(views)[0],
      false,
    );
}

void tour().catch((error: unknown) => {
  document.getElementById("results")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
