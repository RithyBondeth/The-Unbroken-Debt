/** Game-time coverage for a spirit emerging and receding into darkness. */
export class SpiritPresence {
  private progress = 0;
  private target = 0;

  constructor(
    private readonly enterSeconds = 0.65,
    private readonly leaveSeconds = 0.25,
  ) {}

  get value(): number {
    return this.progress * this.progress * (3 - 2 * this.progress);
  }

  get visible(): boolean {
    return this.target > 0 || this.progress > 0;
  }

  get settled(): boolean {
    return this.progress === 1 && this.target === 1;
  }

  show(): void {
    this.progress = 0;
    this.target = 1;
  }

  hide(immediate = false): void {
    this.target = 0;
    if (immediate) this.progress = 0;
  }

  update(dt: number): void {
    const step = Math.max(0, dt) / (this.target ? this.enterSeconds : this.leaveSeconds);
    this.progress = this.target
      ? Math.min(1, this.progress + step)
      : Math.max(0, this.progress - step);
  }
}
