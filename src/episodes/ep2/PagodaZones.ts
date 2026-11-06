import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Node } from "@babylonjs/core/node";
import { LOST_GARDEN, type GardenZone } from "./data/pagoda";

/** How near Sora must be for a zone to be drawn. The trees along the walls hide the rest. */
export const ZONE_REACH = 30;

/** Metres from a point to a zone's rectangle, 0 inside it. */
export function zoneDistance(zone: GardenZone, x: number, z: number): number {
  const dx = Math.max(zone.minX - x, 0, x - zone.maxX),
    dz = Math.max(zone.minZ - z, 0, z - zone.maxZ);
  return Math.hypot(dx, dz);
}

/** The `zone_` node a mesh hangs under, or "" if it belongs to the compound. */
export function zoneOf(mesh: Node): string {
  for (let n: Node | null = mesh; n; n = n.parent) if (n.name.startsWith("zone_")) return n.name;
  return "";
}

/**
 * Switches the lost garden's zones on and off by distance, so the compound doesn't pay for
 * ground nobody can see. Batching keeps each zone's meshes apart (see `zoneOf`), but merged
 * batches lose their parents, so they are found by the group the batcher recorded. Colliders
 * are not in the zones, and stay live.
 */
export class PagodaZones {
  private readonly zones: { zone: GardenZone; meshes: AbstractMesh[]; shown: boolean }[];

  constructor(meshes: readonly AbstractMesh[]) {
    this.zones = LOST_GARDEN.map((zone) => ({
      zone,
      meshes: meshes.filter(
        (m) => (m.metadata as { batchGroup?: string } | null)?.batchGroup === "zone_" + zone.id,
      ),
      shown: true,
    }));
  }

  /** `at` is where Sora stands, or null during a scene the zones must not show in. */
  update(at: { x: number; z: number } | null): void {
    for (const entry of this.zones) {
      const shown = at !== null && zoneDistance(entry.zone, at.x, at.z) < ZONE_REACH;
      if (shown === entry.shown) continue;
      entry.shown = shown;
      for (const mesh of entry.meshes) mesh.setEnabled(shown);
    }
  }
}
