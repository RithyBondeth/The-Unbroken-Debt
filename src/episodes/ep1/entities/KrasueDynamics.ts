export interface KrasueJoint {
  kind: "hair" | "gut" | "organ";
  index: number;
  joint: number;
}

interface Pendulum {
  pitch: number;
  roll: number;
  pitchSpeed: number;
  rollSpeed: number;
}

interface Position {
  x: number;
  y: number;
  z: number;
}

/** Damped secondary motion driven by actual travel, acceleration and head turns.
 * Hair roots stay attached; light tips lag, viscera carry more weight, and all
 * joints recover continuously when the creature brakes at the window.
 */
export class KrasueDynamics {
  readonly angles: Pendulum[];
  private previous: Position | null = null;
  private vx = 0;
  private vz = 0;
  private previousYaw = 0;

  constructor(private readonly joints: readonly KrasueJoint[]) {
    this.angles = joints.map(() => ({ pitch: 0, roll: 0, pitchSpeed: 0, rollSpeed: 0 }));
  }

  reset(): void {
    this.previous = null;
    this.vx = 0;
    this.vz = 0;
    for (const a of this.angles) a.pitch = a.roll = a.pitchSpeed = a.rollSpeed = 0;
  }

  update(dt: number, position: Position, yaw: number, time: number, wind = true): void {
    if (
      !this.previous ||
      Math.hypot(
        position.x - this.previous.x,
        position.y - this.previous.y,
        position.z - this.previous.z,
      ) > 1 ||
      dt > 0.25
    ) {
      this.reset();
      this.previous = { x: position.x, y: position.y, z: position.z };
      this.previousYaw = yaw;
      return;
    }
    dt = Math.max(0, Math.min(0.1, dt));
    if (dt < 0.00001) return;
    const rawX = (position.x - this.previous.x) / dt,
      rawZ = (position.z - this.previous.z) / dt;
    const mix = 1 - Math.exp(-dt * 12);
    const nextX = this.vx + (rawX - this.vx) * mix,
      nextZ = this.vz + (rawZ - this.vz) * mix;
    const ax = (nextX - this.vx) / dt,
      az = (nextZ - this.vz) / dt;
    this.vx = nextX;
    this.vz = nextZ;
    this.previous.x = position.x;
    this.previous.y = position.y;
    this.previous.z = position.z;
    const turn =
      Math.atan2(Math.sin(yaw - this.previousYaw), Math.cos(yaw - this.previousYaw)) / dt;
    this.previousYaw = yaw;
    const c = Math.cos(yaw),
      s = Math.sin(yaw);
    const clamp = (n: number, limit: number) => Math.max(-limit, Math.min(limit, n));
    const drag = clamp((s * nextX + c * nextZ) * 0.09 + (s * ax + c * az) * 0.014, 0.57);
    const lateral = clamp(
      (c * nextX - s * nextZ) * 0.08 + (c * ax - s * az) * 0.012 + turn * 0.018,
      0.38,
    );
    let remaining = dt;
    while (remaining > 0) {
      const step = Math.min(1 / 120, remaining);
      remaining -= step;
      for (let i = 0; i < this.joints.length; i++) {
        const spec = this.joints[i],
          a = this.angles[i];
        const hair = spec.kind === "hair",
          gut = spec.kind === "gut";
        const gain = hair
          ? spec.joint === 0
            ? 0.035
            : 0.23 + spec.joint * 0.13
          : gut
            ? 0.08 + spec.joint * 0.07
            : 0.22;
        const omega = hair ? 10 - spec.joint * 0.8 : gut ? 5.2 - spec.joint * 0.3 : 5.7;
        const damping = hair ? 0.67 : gut ? 0.76 : 0.91;
        const phase = time * (hair ? 1.4 : 0.83) - spec.joint * 0.73 + spec.index * 1.37;
        const breeze = wind
          ? (Math.sin(phase) + Math.sin(phase * 2.13 + spec.index) * 0.27) *
            (hair ? 0.018 : gut ? 0.01 : 0.003)
          : 0;
        const pitch = clamp(drag * gain + breeze * gain, 0.37);
        const roll = clamp(-lateral * gain + breeze * 0.47 * gain, 0.26);
        a.pitchSpeed +=
          (omega * omega * (pitch - a.pitch) - 2 * damping * omega * a.pitchSpeed) * step;
        a.rollSpeed += (omega * omega * (roll - a.roll) - 2 * damping * omega * a.rollSpeed) * step;
        a.pitch = clamp(a.pitch + a.pitchSpeed * step, 0.4);
        a.roll = clamp(a.roll + a.rollSpeed * step, 0.29);
      }
    }
  }
}
