import { RenderTargetTexture } from "@babylonjs/core/Materials/Textures/renderTargetTexture";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import type { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { Observer } from "@babylonjs/core/Misc/observable";
import type { Scene } from "@babylonjs/core/scene";

export interface ShadowSchedulerOptions {
  /**
   * Re-render this many maps every frame in rotation, whether or not anything
   * moved. 0 (default) caches the maps: they re-render only when marked dirty.
   */
  rotatePerFrame?: number;
  /** Most dirty maps re-rendered in one frame; the rest wait for the next frame. */
  maxDirtyPerFrame?: number;
}

/**
 * Shadow maps for lights that never move (candles, braziers, the altar lamp).
 * Static scenery only needs them rendered once, so by default they are cached
 * and re-rendered only when something that moves (a spirit, a swinging door)
 * comes within a light's range: call `markDirtyNear` every frame for each
 * moving caster. Spike S2 measured re-rendering 4 point-light cube maps as the
 * largest single cost, so this is what makes 4 shadowed flames affordable.
 * The player's lamp moves, so it is never scheduled here.
 */
export class ShadowScheduler {
  private readonly rotatePerFrame: number;
  private readonly maxDirtyPerFrame: number;
  private readonly dirty = new Set<ShadowGenerator>();
  private readonly observer: Observer<Scene>;
  private next = 0;
  /** Maps re-rendered in the last frame (for profiling readouts). */
  renderedLastFrame = 0;

  constructor(
    scene: Scene,
    private readonly generators: ShadowGenerator[],
    options: ShadowSchedulerOptions = {},
  ) {
    this.rotatePerFrame = options.rotatePerFrame ?? 0;
    this.maxDirtyPerFrame = options.maxDirtyPerFrame ?? 2;
    for (const generator of generators) {
      const map = generator.getShadowMap();
      if (map) map.refreshRate = RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
    }
    this.observer = scene.onBeforeRenderObservable.add(() => this.tick());
  }

  /** Marks every light whose range reaches a moving caster at `point` (bounding radius `radius`). */
  markDirtyNear(point: Vector3, radius: number): void {
    for (const generator of this.generators) {
      const light = generator.getLight() as PointLight;
      const reach = light.range + radius;
      if (Vector3.DistanceSquared(light.getAbsolutePosition(), point) < reach * reach)
        this.dirty.add(generator);
    }
  }

  /** Re-renders every map (e.g. after a door opens or the level changes). */
  refreshAll(): void {
    for (const generator of this.generators) this.dirty.add(generator);
  }

  dispose(): void {
    this.observer.remove();
    for (const generator of this.generators) {
      const map = generator.getShadowMap();
      if (map) map.refreshRate = 1;
    }
  }

  private tick(): void {
    this.renderedLastFrame = 0;
    const count = this.generators.length;
    if (count === 0) return;

    if (this.rotatePerFrame > 0) {
      for (let i = 0; i < Math.min(this.rotatePerFrame, count); i++) {
        this.render(this.generators[this.next]);
        this.next = (this.next + 1) % count;
      }
      return;
    }

    for (const generator of this.dirty) {
      if (this.renderedLastFrame >= this.maxDirtyPerFrame) break;
      this.dirty.delete(generator);
      this.render(generator);
    }
  }

  private render(generator: ShadowGenerator): void {
    generator.getShadowMap()?.resetRefreshCounter();
    this.renderedLastFrame++;
  }
}
