import { Game } from "./core/Game";
import { createEngine } from "./render/createEngine";
import { useLocalDecoders } from "./render/decoders";
import { detectDevice } from "./render/detectDevice";
import { hasSpike, runSpike } from "./spikes";
import { showRequirementsPage } from "./ui/html/RequirementsPage";

async function boot(): Promise<void> {
  const canvas = document.getElementById("game") as HTMLCanvasElement;
  const overlay = document.getElementById("overlay") as HTMLElement;
  overlay.hidden = true;

  // Phones, tablets and browsers without (hardware) WebGPU get the requirements page.
  const device = await detectDevice();
  console.info(`[boot] ${device.label} → ${device.blocked ?? `${device.quality} preset`}`);
  if (device.blocked) {
    showRequirementsPage(overlay, device.blocked);
    return;
  }

  const engine = await createEngine(canvas);
  if (!engine) {
    showRequirementsPage(overlay, "no-webgpu");
    return;
  }

  useLocalDecoders();

  // Phase 1 spikes: ?spike=s1 (movement), ?spike=s2 (lighting), ?spike=s3 (assets) or ?spike=s5 (sketchbook).
  const params = new URLSearchParams(window.location.search);
  const spike = params.get("spike");
  if (hasSpike(spike)) {
    await runSpike(spike, engine, params, device);
    return;
  }

  const game = new Game(engine);
  game.start();

  // Development builds only: inspect the game from the browser console.
  if (import.meta.env.DEV) {
    (window as unknown as { game: Game }).game = game;
  }
}

void boot();
