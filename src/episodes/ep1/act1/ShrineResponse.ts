/** Game-time performance after a successful checkpoint. No control or lamp state changes. */
const DURATION = 6.2;
const smooth = (a: number, b: number, t: number) => {
  const u = Math.max(0, Math.min(1, (t - a) / (b - a)));
  return u * u * (3 - 2 * u);
};

export class ShrineResponse {
  private time = -1;
  private pending = false;
  private committed = false;
  get active(): boolean {
    return this.pending || (this.committed && this.time < DURATION);
  }
  get darkness(): number {
    return this.pending
      ? 0.45
      : this.active
        ? smooth(0, 1.55, this.time) * (1 - smooth(2.4, 4.5, this.time))
        : 0;
  }
  get turn(): number {
    return this.active && this.committed
      ? smooth(0.8, 2.1, this.time) * (1 - smooth(4, DURATION, this.time))
      : 0;
  }
  get silence(): number {
    return this.active ? Math.max(this.darkness, this.turn * 0.85) : 0;
  }
  begin(): void {
    this.time = 0;
    this.pending = true;
    this.committed = false;
  }
  settle(success: boolean): void {
    if (!success) {
      this.cancel();
      return;
    }
    this.pending = false;
    this.committed = true;
    this.time = 0;
  }
  cancel(): void {
    this.time = -1;
    this.pending = false;
    this.committed = false;
  }
  update(dt: number): ("knock" | "breath" | "ring")[] {
    if (!this.active || this.pending) return [];
    const before = this.time;
    this.time += Math.max(0, dt);
    const cues: [number, "knock" | "breath" | "ring"][] = [
      [0.6, "knock"],
      [1.02, "knock"],
      [1.48, "knock"],
      [1.85, "breath"],
      [3.05, "ring"],
    ];
    return cues.filter(([at]) => before < at && this.time >= at).map(([, cue]) => cue);
  }
}
