import type { Scene } from "@babylonjs/core/scene";
import type { TargetCamera } from "@babylonjs/core/Cameras/targetCamera";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";

export interface WarmView {
  eye: Vector3;
  target: Vector3;
}

/** Draw upcoming views behind the loading fade, including their actual GPU pipelines.
 * This runs before the gameplay loop and never changes the player's physics pose.
 */
export async function warmSceneViews(
  scene: Scene,
  camera: TargetCamera,
  views: readonly WarmView[],
): Promise<void> {
  if (!views.length) return;
  const position = camera.position.clone();
  const rotation = camera.rotation.clone();
  const quaternion = camera.rotationQuaternion?.clone() ?? null;
  const engine = scene.getEngine();
  let index = 0,
    stable = 0;
  const place = scene.onBeforeRenderObservable.add(() => {
    camera.position.copyFrom(views[index].eye);
    camera.setTarget(views[index].target);
  });
  try {
    await new Promise<void>((resolve, reject) => {
      const frame = () => {
        try {
          scene.render();
          const active = scene.getActiveMeshes();
          let ready = true;
          for (let i = 0; i < active.length; i++)
            if (!active.data[i].isReady(true)) {
              ready = false;
              break;
            }
          stable = ready ? stable + 1 : 0;
          if (stable < 3) return;
          stable = 0;
          if (++index < views.length) return;
          engine.stopRenderLoop(frame);
          resolve();
        } catch (error) {
          engine.stopRenderLoop(frame);
          reject(
            error instanceof Error ? error : new Error("Loading view failed", { cause: error }),
          );
        }
      };
      engine.runRenderLoop(frame);
    });
  } finally {
    place.remove();
    camera.position.copyFrom(position);
    camera.rotation.copyFrom(rotation);
    camera.rotationQuaternion = quaternion;
  }
}
