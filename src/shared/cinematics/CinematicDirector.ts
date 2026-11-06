import type { Game } from "../../core/Game";
import { CinematicClock, type CinematicScript, type SubtitleCue } from "./timeline";
import "./cinematics.css";
export interface CinematicFrame {
  elapsed: number;
  progress: number;
  reducedMotion: boolean;
}
/** Input, captions, skip and pause share one lifecycle, including interrupted/backgrounded scenes. */
export class CinematicDirector {
  private clock: CinematicClock | null = null;
  private finish: (() => void) | null = null;
  private frame: ((value: CinematicFrame) => void) | null = null;
  private lastCue: SubtitleCue | null = null;
  private readonly controls = document.createElement("div");
  private readonly pause = document.createElement("button");
  private readonly skip = document.createElement("button");
  private readonly label = document.createElement("span");
  private readonly abort = new AbortController();
  private readonly reduced = matchMedia("(prefers-reduced-motion: reduce)");
  constructor(private readonly game: Game) {
    this.controls.className = "cinematic-controls";
    this.controls.hidden = true;
    this.controls.setAttribute("role", "group");
    this.controls.setAttribute("aria-label", "Cinematic playback");
    this.label.className = "cinematic-label";
    this.pause.type = this.skip.type = "button";
    this.pause.className = this.skip.className = "ui-button";
    this.skip.textContent = "Skip scene";
    this.pause.onclick = () => this.togglePause();
    this.skip.onclick = () => this.skipScene();
    this.controls.append(this.label, this.pause, this.skip);
    document.body.append(this.controls);
    window.addEventListener(
      "keydown",
      (e) => {
        if (!this.active || e.repeat) return;
        if (e.code === "Enter" && e.target instanceof HTMLButtonElement) return;
        if (e.code === "Escape" || e.code === "Enter") {
          e.preventDefault();
          this.togglePause();
        }
      },
      { signal: this.abort.signal },
    );
    game.scene.onBeforeRenderObservable.add(() => this.update(game.deltaSeconds));
    game.scene.onDisposeObservable.addOnce(() => this.dispose());
  }
  get active(): boolean {
    return this.clock !== null;
  }
  get currentId(): string | null {
    return this.clock?.script.id ?? null;
  }
  get elapsed(): number {
    return this.clock?.elapsed ?? 0;
  }
  get isPaused(): boolean {
    return this.clock?.paused ?? false;
  }
  async play(
    script: CinematicScript,
    onFrame: (frame: CinematicFrame) => void = () => undefined,
  ): Promise<"played" | "skipped"> {
    if (this.active) throw new Error("A cinematic is already playing");
    const g = this.game,
      held = { cutscene: g.cutscene, still: g.gated.holdStill, look: g.gated.holdLook };
    g.cutscene = true;
    g.gated.holdStill = true;
    g.gated.holdLook = true;
    g.input.clear();
    g.stopInspecting();
    g.closeSketchbook();
    g.satchel.close();
    g.hints.hide();
    document.exitPointerLock();
    const clock = new CinematicClock(script);
    this.clock = clock;
    this.frame = onFrame;
    this.lastCue = null;
    this.controls.hidden = false;
    this.controls.dataset.paused = "false";
    this.label.textContent = script.title;
    this.pause.textContent = "Pause · Esc";
    this.pause.focus({ preventScroll: true });
    g.bus.emit("sequence:start", { id: script.id });
    try {
      onFrame({ elapsed: 0, progress: 0, reducedMotion: this.reduced.matches });
      await new Promise<void>((resolve) => {
        this.finish = resolve;
      });
      return clock.skipped ? "skipped" : "played";
    } finally {
      this.clock = null;
      this.frame = null;
      this.finish = null;
      this.controls.hidden = true;
      g.subtitles.hide();
      g.cutscene = held.cutscene;
      g.gated.holdStill = held.still;
      g.gated.holdLook = held.look;
      g.input.clear();
      g.bus.emit("sequence:end", { id: script.id });
    }
  }
  private togglePause(): void {
    if (!this.clock) return;
    this.clock.paused = !this.clock.paused;
    this.pause.textContent = this.clock.paused ? "Resume · Enter" : "Pause · Esc";
    this.controls.dataset.paused = String(this.clock.paused);
  }
  skipScene(): void {
    this.clock?.skip();
    this.finish?.();
  }
  private update(dt: number): void {
    const c = this.clock;
    if (!c) return;
    c.update(dt, !document.hidden);
    if (!c.paused && !document.hidden)
      this.frame?.({
        elapsed: c.elapsed,
        progress: c.elapsed / c.script.duration,
        reducedMotion: this.reduced.matches,
      });
    const cue = c.cue;
    if (cue !== this.lastCue) {
      this.lastCue = cue;
      if (cue) this.game.subtitles.show(cue.speaker, cue.text);
      else this.game.subtitles.hide();
    }
    if (c.finished) this.finish?.();
  }
  dispose(): void {
    this.abort.abort();
    this.skipScene();
    this.controls.remove();
  }
}
