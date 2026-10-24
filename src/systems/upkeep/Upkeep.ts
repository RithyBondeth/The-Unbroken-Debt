import type { EventBus } from "../../core/EventBus";
import type { GameEvents } from "../../core/events";

export interface UpkeepOptions {
  /** Seconds from fresh to burnt out. */
  duration: number;
  /** Fractions left at which warning stages 1 and 2 fire (e.g. 0.25 and 0.1). */
  warnings: [number, number];
}

/**
 * A duty that decays and must be renewed (TDD section 4, Upkeep): the incense
 * sticks at the coffin's corners. Emits `upkeep:warning` at each stage and
 * `upkeep:expired` when it runs out; `outFor` counts the time since.
 */
export class Upkeep {
  private left: number;
  private stage: 0 | 1 | 2 = 0;
  private expired = false;
  private _outFor = 0;

  constructor(
    readonly id: string,
    private readonly options: UpkeepOptions,
    private readonly bus?: EventBus<GameEvents>,
  ) {
    this.left = options.duration;
  }

  /** Fraction left, 1 when fresh, 0 when out. */
  get fraction(): number {
    return this.left / this.options.duration;
  }

  get alive(): boolean {
    return !this.expired;
  }

  /** Warning stage reached: 0 none, 1 low, 2 nearly out. */
  get warning(): 0 | 1 | 2 {
    return this.stage;
  }

  /** Seconds since it ran out (0 while alive). */
  get outFor(): number {
    return this._outFor;
  }

  update(dt: number): void {
    if (this.expired) {
      this._outFor += dt;
      return;
    }
    this.left = Math.max(0, this.left - dt);
    const f = this.fraction;
    const [first, second] = this.options.warnings;
    if (this.stage < 1 && f <= first) this.warn(1);
    if (this.stage < 2 && f <= second) this.warn(2);
    if (this.left <= 0) {
      this.expired = true;
      this.bus?.emit("upkeep:expired", { id: this.id });
    }
  }

  /** Fresh sticks, lit: back to full. */
  renew(): void {
    this.left = this.options.duration;
    this.stage = 0;
    this.expired = false;
    this._outFor = 0;
  }

  /** Restores a checkpoint without replaying warnings or counting fresh neglect. */
  restore(fraction: number, outFor = 0): void {
    const f = Math.max(0, Math.min(1, fraction));
    this.left = f * this.options.duration;
    this.expired = f === 0;
    this._outFor = this.expired ? Math.max(0, outFor) : 0;
    this.stage = f <= this.options.warnings[1] ? 2 : f <= this.options.warnings[0] ? 1 : 0;
  }

  /** Puts it out at once (a scripted beat, A2-09). */
  extinguish(): void {
    this.left = 0;
    this.update(0);
  }

  private warn(stage: 1 | 2): void {
    this.stage = stage;
    this.bus?.emit("upkeep:warning", { id: this.id, stage });
  }
}
