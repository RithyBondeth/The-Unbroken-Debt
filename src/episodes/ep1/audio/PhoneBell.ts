/** Seconds in one `phoneRing` clip: 1.6 s of bell, then 2.4 s of quiet. */
export const RING_CYCLE = 4;

/** The bell's last strikes have died away this far into a cycle. */
const RING_TAIL = 3;

interface Bell {
  play(): void;
  stop(): void;
}

/**
 * A telephone nobody has answered yet: a burst of rings, then a long quiet,
 * then another burst, until `stop()`. The player still knows the phone wants
 * them, but it does not nag every four seconds while they look around.
 * `sound` is the looping `phoneRing` clip.
 */
export class PhoneBell {
  private on = false;
  private ringing = false;
  private time = 0;

  constructor(
    private readonly sound: Bell | null,
    private readonly rings = 5,
    private readonly quiet = 35,
  ) {}

  get active(): boolean {
    return this.on;
  }

  /** Seconds a burst lasts: every ring, stopped once the last has faded. */
  get burst(): number {
    return (this.rings - 1) * RING_CYCLE + RING_TAIL;
  }

  start(): void {
    if (this.on) return;
    this.on = true;
    this.ring();
  }

  stop(): void {
    this.on = false;
    if (this.ringing) this.sound?.stop();
    this.ringing = false;
  }

  update(dt: number): void {
    if (!this.on) return;
    this.time += dt;
    if (this.ringing && this.time >= this.burst) {
      this.sound?.stop();
      this.ringing = false;
      this.time = 0;
    } else if (!this.ringing && this.time >= this.quiet) this.ring();
  }

  private ring(): void {
    this.ringing = true;
    this.time = 0;
    this.sound?.play();
  }
}
