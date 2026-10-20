export interface SnagSample {
  dt: number;
  supported: boolean;
  climbing: boolean;
  wishSpeed: number;
  speed: number;
  /** A wall or obstacle is directly ahead, so stopping is expected. */
  blockedAhead: boolean;
}

/**
 * Counts "snags": the player is on the ground, pushing to move, nothing is in
 * the way, yet speed collapses. This is the S1 pass condition for 1 cm floor gaps.
 */
export class SnagDetector {
  count = 0;
  /** Seconds of input needed before a stall counts, to ignore acceleration from rest. */
  readonly settleTime = 0.35;
  /** Seconds of stall before it counts as a snag. */
  readonly stallTime = 0.15;
  /** Fraction of the wished speed below which the player is stalled. */
  readonly stallRatio = 0.4;

  private pushing = 0;
  private stalled = 0;
  private inSnag = false;

  /** Returns true on the frame a new snag is detected. */
  update(s: SnagSample): boolean {
    const active = s.supported && !s.climbing && s.wishSpeed > 0.5;
    if (!active || s.blockedAhead) {
      this.pushing = 0;
      this.stalled = 0;
      this.inSnag = false;
      return false;
    }

    this.pushing += s.dt;
    if (this.pushing < this.settleTime) return false;

    if (s.speed < s.wishSpeed * this.stallRatio) {
      this.stalled += s.dt;
      if (!this.inSnag && this.stalled >= this.stallTime) {
        this.inSnag = true;
        this.count++;
        return true;
      }
    } else {
      this.stalled = 0;
      this.inSnag = false;
    }
    return false;
  }

  reset(): void {
    this.count = 0;
    this.pushing = 0;
    this.stalled = 0;
    this.inSnag = false;
  }
}
