import { Game } from "./core/Game";
import { createEngine } from "./render/createEngine";
import { hasSpike, runSpike } from "./spikes";
import { showRequirementsPage } from "./ui/html/RequirementsPage";

async function boot(): Promise<void> {
  const canvas = document.getElementById("game") as HTMLCanvasElement;
  const overlay = document.getElementById("overlay") as HTMLElement;
  overlay.hidden = true;

  const engine = await createEngine(canvas);
  if (!engine) {
    showRequirementsPage(overlay);
    return;
  }

  // Phase 1 spikes: ?spike=s1 (movement) or ?spike=s2 (lighting).
  const params = new URLSearchParams(window.location.search);
  const spike = params.get("spike");
  if (hasSpike(spike)) {
    await runSpike(spike, engine, params);
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
