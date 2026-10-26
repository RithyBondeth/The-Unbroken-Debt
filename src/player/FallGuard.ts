import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** A rectangle on the ground (x, z), in metres. */
export interface GroundBounds {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

/**
 * The safety net under every area: remembers where Sora last stood on solid
 * ground and, if she ever drops below the world (a gap in a collider, a physics
 * hitch) or ends up outside the area's walls, says where to put her back.
 */
export class FallGuard {
  /** Feet lower than this have left the world. */
  floorY = -6;
  /** Where she may stand, if the area has walls; outside them by `slack` counts as lost. */
  bounds: GroundBounds | null = null;
  slack = 1.5;
  private readonly safe = new Vector3();
  private hasSafe = false;
  private sinceRecord = Infinity;

  /** Sets the first safe point (a spawn or a checkpoint). */
  reset(feet: Vector3): void {
    this.safe.copyFrom(feet);
    this.hasSafe = true;
    this.sinceRecord = 0;
  }

  /**
   * Call every frame. Returns where to respawn if she is lost, otherwise null.
   * `supported` is true when the character controller stands on something.
   */
  update(dt: number, feet: Vector3, supported: boolean): Vector3 | null {
    if (this.lost(feet)) return this.hasSafe ? this.safe.clone() : null;
    this.sinceRecord += dt;
    // Only footing that held for a moment counts, and only inside the walls.
    if (supported && this.sinceRecord >= 0.5 && this.withinBounds(feet, 0)) {
      this.safe.copyFrom(feet);
      this.safe.y += 0.05;
      this.hasSafe = true;
      this.sinceRecord = 0;
    }
    return null;
  }

  lost(feet: Vector3): boolean {
    return feet.y < this.floorY || !this.withinBounds(feet, this.slack);
  }

  private withinBounds(feet: Vector3, slack: number): boolean {
    const b = this.bounds;
    return (
      !b ||
      (feet.x > b.minX - slack &&
        feet.x < b.maxX + slack &&
        feet.z > b.minZ - slack &&
        feet.z < b.maxZ + slack)
    );
  }
}
