/**
 * Pure pacing, cooldown, and staging definitions for Episode 1 Village's Asian
 * psychological horror director (Preay, Headless Ghost, Shrouded Corpse, shadow-only cues).
 * Every beat relies on anticipation, sound vacuum, living motion, cover retreats,
 * blackout light-cuts, and directional HRTF sound storytelling.
 */

export type VillageHauntId =
  | "roadsidePeeker"
  | "shopDoorCrossing"
  | "roadsideHeadless"
  | "extraFootstep"
  | "corpseVanish"
  | "wellHeadless"
  | "strobeCloser"
  | "weepingBackTurned"
  | "shadowBanner"
  | "provokedPreay";

/** Minimum quiet breathing room (seconds) between unprovoked ambient horror beats. */
export const HAUNT_COOLDOWN_SEC = 24;

/** Where the shrouded corpse (`shrouded_corpse.glb`) rests beneath the north-west forest canopy before vanishing. */
export const CORPSE_SPOT = { x: 35.4, z: -47.6, yaw: 0.95 } as const;

/** Preay roadside corner-peeker spot leaning out beside the west roadside shop shoulder. */
export const ROADSIDE_PEEK_SPOT = { x: -9.4, z: 49.4 } as const;

/** Dark alley cover behind the west roadside shop where Preay physically retreats when spotted. */
export const ROADSIDE_PEEK_RETREAT = { x: -14.9, z: 49.8 } as const;

/** Walkable Moto Shop interior crossing path (doorway silhouette passing left -> right behind wall). */
export const SHOP_CROSSING_PATH = {
  from: { x: 11.1, y: 0.47, z: 60.35 },
  to: { x: 14.8, y: 0.47, z: 60.55 },
} as const;

/** Preay back-turned weeping spot in the dark lane beside the servants' hut / yard edge. */
export const WEEPING_SPOT = { x: 24.5, z: -26.2 } as const;

/**
 * Pure pacing gate for autonomous village scares: enforces cooldown, one-shot memory,
 * and priority so provoked puzzle scares always land cleanly without stacking.
 */
export class VillageHauntPacer {
  private readonly done = new Set<VillageHauntId>();
  private cooldown = 10;
  /** Increases when the player breaks wards or triggers wrong folklore choices. */
  aggravation = 0;

  tick(dt: number, busy: boolean): void {
    if (!busy && this.cooldown > 0) this.cooldown = Math.max(0, this.cooldown - dt);
  }

  hasDone(id: VillageHauntId): boolean {
    return this.done.has(id);
  }

  canTriggerAutonomous(id: VillageHauntId, busy: boolean): boolean {
    return !busy && this.cooldown <= 0 && !this.done.has(id);
  }

  markTriggered(id: VillageHauntId, repeatable = false): void {
    if (!repeatable) this.done.add(id);
    // Higher aggravation slightly shortens breathing room, never dropping below 12s
    this.cooldown = Math.max(12, HAUNT_COOLDOWN_SEC - this.aggravation * 3.5);
  }

  aggravate(amount = 1): void {
    this.aggravation = Math.min(4, this.aggravation + amount);
  }
}
