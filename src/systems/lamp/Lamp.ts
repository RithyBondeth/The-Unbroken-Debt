import type { EventBus } from "../../core/EventBus";
import type { GameEvents, LampState } from "../../core/events";

/** Episode 1 Beat Sheet, section 5: "A full tank lasts ~12 min." */
export const FULL_TANK_SECONDS = 12 * 60;
/** Controls and Interface, section 6: "the flame shrinks and sputters below 25%". */
export const SPUTTER_BELOW = 0.25;

/**
 * Sora's hurricane lamp (TDD section 4, Lamp): open, shuttered or out, and the
 * kerosene left in the tank, which burns while the wick is lit. Emits
 * `lamp:state` on every change and `lamp:oil` in steps of 1%.
 */
export class Lamp {
  private _oil: number;
  private _state: LampState;
  private reported: number;

  constructor(
    private readonly bus?: EventBus<GameEvents>,
    oil = 1,
    state: LampState = "out",
  ) {
    this._oil = clamp01(oil);
    this._state = this._oil > 0 ? state : "out";
    this.reported = Math.round(this._oil * 100);
  }

  get oil(): number {
    return this._oil;
  }

  get state(): LampState {
    return this._state;
  }

  /** The wick is burning (open or shuttered). */
  get burning(): boolean {
    return this._state !== "out";
  }

  /**
   * How strong the flame is, 0 to 1: full above a quarter tank, then shrinking
   * with the oil and sputtering (`time` in seconds drives the sputter).
   */
  flame(time: number): number {
    if (!this.burning) return 0;
    if (this._oil >= SPUTTER_BELOW) return 1;
    const low = this._oil / SPUTTER_BELOW;
    const sputter = 0.5 + 0.5 * Math.sin(time * 23) * Math.sin(time * 7.3);
    return Math.max(0.05, low * (0.75 + 0.25 * sputter));
  }

  /** Lights the wick (the caller strikes the match). False if it is dry or already lit. */
  light(): boolean {
    if (this.burning || this._oil <= 0) return false;
    this.setState("open");
    return true;
  }

  putOut(): void {
    if (this.burning) this.setState("out");
  }

  /** Pours in kerosene; a bottle fills the tank (`amount` 1). */
  refill(amount = 1): void {
    this._oil = clamp01(this._oil + amount);
    this.report();
  }

  /** Checkpoints restore at least this much oil, so a restart is never hopeless (Beat Sheet, section 7). */
  restoreAtLeast(level: number): void {
    if (this._oil < level) this.refill(level - this._oil);
  }

  update(dt: number): void {
    if (!this.burning) return;
    this._oil = Math.max(0, this._oil - dt / FULL_TANK_SECONDS);
    this.report();
    if (this._oil <= 0) this.setState("out");
  }

  toJSON(): { oil: number; state: LampState } {
    return { oil: Math.round(this._oil * 1000) / 1000, state: this._state };
  }

  /** Restore the checkpoint exactly, then apply its minimum-oil allowance. */
  restore(snapshot: { oil: number; state: LampState }): void {
    this._oil = clamp01(snapshot.oil);
    this.setState(this._oil > 0 ? snapshot.state : "out");
    this.reported = -1;
    this.report();
  }

  private setState(state: LampState): void {
    this._state = state;
    this.bus?.emit("lamp:state", { state });
  }

  private report(): void {
    const level = Math.round(this._oil * 100);
    if (level === this.reported) return;
    this.reported = level;
    this.bus?.emit("lamp:oil", { level: this._oil });
  }
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
