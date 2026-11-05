export type WaterPoint = { x: number; z: number };
/** Water-only pursuit; a visible wake announces every approach before contact becomes lethal. */
export class DrownedBrain {
  readonly position: WaterPoint = { x: 5, z: -5 };
  state: "submerged" | "ripple" | "rising" | "withdrawn" = "submerged";
  private clock = 0;
  private exposure = 0;
  update(dt: number, player: WaterPoint, vulnerable: boolean, warm: boolean): void {
    dt = Math.max(0, Math.min(0.1, dt));
    this.clock += dt;
    if (warm || !vulnerable) {
      this.exposure = Math.max(0, this.exposure - dt * 2);
      this.state = "withdrawn";
      return;
    }
    this.exposure += dt;
    this.state = this.exposure < 2.5 ? "ripple" : "rising";
    const dx = player.x - this.position.x,
      dz = player.z - this.position.z;
    const distance = Math.hypot(dx, dz);
    const speed = this.state === "rising" ? 0.95 : 0.5;
    if (distance > 0.1) {
      this.position.x += (dx / distance) * Math.min(distance, dt * speed);
      this.position.z += (dz / distance) * Math.min(distance, dt * speed);
    }
  }
  catches(player: WaterPoint, vulnerable: boolean, warm: boolean): boolean {
    return (
      vulnerable &&
      !warm &&
      this.state === "rising" &&
      this.exposure > 5 &&
      Math.hypot(player.x - this.position.x, player.z - this.position.z) < 0.85
    );
  }
}
