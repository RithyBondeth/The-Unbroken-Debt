import type { Game } from "./core/Game";
import { detectDevice } from "./render/detectDevice";
import { isQualityName } from "./render/QualityPresets";
import { hasSpike, runSpike } from "./spikes";
import { showRequirementsPage } from "./ui/html/RequirementsPage";
import { readWelcomeSettings, showBootError, showWelcomeScreen } from "./ui/html/WelcomeScreen";

/**
 * The engine and the game are a separate chunk, so the welcome screen appears
 * before the whole game has downloaded; fetching starts at once, behind it.
 */
const gameModules = Promise.all([
  import("./core/Game"),
  import("./render/createEngine"),
  import("./render/decoders"),
]);
// A failed download is reported when boot awaits it, not while the welcome screen is up.
gameModules.catch(() => undefined);

async function boot(): Promise<void> {
  const canvas = document.getElementById("game") as HTMLCanvasElement;
  const overlay = document.getElementById("overlay") as HTMLElement;
  overlay.hidden = true;

  const params = new URLSearchParams(window.location.search);
  const spike = params.get("spike");
  // Keep existing developer/checkpoint entry URLs direct.
  const direct = hasSpike(spike) || params.has("start") || params.has("continue");
  const settings = direct ? readWelcomeSettings() : await showWelcomeScreen(overlay);

  // Phones, tablets and browsers without (hardware) WebGPU get the requirements page.
  const device = await detectDevice();
  console.info(`[boot] ${device.label} → ${device.blocked ?? `${device.quality} preset`}`);
  if (device.blocked) {
    showRequirementsPage(overlay, device.blocked);
    return;
  }

  const [{ Game }, { createEngine }, { useLocalDecoders }] = await gameModules;
  const engine = await createEngine(canvas);
  if (!engine) {
    showRequirementsPage(overlay, "no-webgpu");
    return;
  }

  useLocalDecoders();

  // Phase 1 spikes: ?spike=s1 (movement), ?spike=s2 (lighting), ?spike=s3 (assets), ?spike=s4 (spatial audio), ?spike=s5 (sketchbook), ?spike=s6 (saves) or ?spike=s7 (atmosphere).
  if (hasSpike(spike)) {
    await runSpike(spike, engine, params, device);
    return;
  }

  // Development builds only: ?quality=low|medium|high|ultra tests a preset this machine wouldn't pick.
  const forced = params.get("quality");
  const game = new Game(
    engine,
    import.meta.env.DEV && isQualityName(forced) ? { ...device, quality: forced } : device,
  );
  game.input.sensitivity = settings.sensitivity;
  game.input.invertY = settings.invertY;
  await game.start({ audio: settings.sound });
  overlay.hidden = true;
  overlay.replaceChildren();

  // Development builds only: inspect the game from the browser console.
  if (import.meta.env.DEV) {
    (window as unknown as { game: Game }).game = game;
  }
}

void boot().catch((error: unknown) => {
  console.error("[boot]", error);
  showBootError(document.getElementById("overlay")!);
});
