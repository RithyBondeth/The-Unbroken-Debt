import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";
import type { Observer } from "@babylonjs/core/Misc/observable";

/**
 * The "Show frame rate" setting: frames per second and the render resolution,
 * updated twice a second in a corner. Not the F3 development overlay.
 */
export class FpsCounter {
  private readonly node = document.createElement("p");
  private readonly observer: Observer<AbstractEngine>;
  private last = 0;

  constructor(private readonly engine: AbstractEngine) {
    this.node.className = "fps-counter";
    this.node.setAttribute("aria-hidden", "true");
    document.body.append(this.node);
    this.observer = engine.onEndFrameObservable.add(() => this.update());
  }

  dispose(): void {
    this.observer.remove();
    this.node.remove();
  }

  private update(): void {
    const now = performance.now();
    if (now - this.last < 500) return;
    this.last = now;
    const engine = this.engine;
    this.node.textContent = `${Math.round(engine.getFps())} fps · ${engine.getRenderWidth()}×${engine.getRenderHeight()}`;
  }
}
