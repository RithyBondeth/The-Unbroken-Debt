import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import { CreateScreenshotAsync } from "@babylonjs/core/Misc/screenshotTools";

/**
 * Development builds only: saves the next frame, post-processing included, at
 * the full render size to debug-shots/<name>.png (served by vite.config.ts).
 */
export async function saveShot(
  engine: AbstractEngine,
  camera: Camera,
  name: string,
): Promise<void> {
  if (!import.meta.env.DEV) return;
  const size = { width: engine.getRenderWidth(), height: engine.getRenderHeight() };
  const data = await CreateScreenshotAsync(engine, camera, size, "image/png");
  await fetch(`/__debug/shot?name=${encodeURIComponent(name)}`, { method: "POST", body: data });
}
