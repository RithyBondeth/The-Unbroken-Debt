import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";

/**
 * The user's posters on the studio's walls (90s Posters/, November 2026) change
 * places each time the room loads. tools/areas/ep1_area_studio.py hangs one poster
 * in each slot, `poster90_p_<k>` (pinned portrait sheets) and `poster90_l_<k>`
 * (framed landscape pictures); every poster of a kind has a cell of the same size in
 * its atlas (tools/areas/studio_prints.json), so a slot can show any of them. A
 * slot's picture is the rectangle its UVs span; shuffling moves each slot's UVs onto
 * another slot's rectangle. The lightmap UVs (the second set) stay as they are.
 *
 * @returns how many slots were shuffled
 */
export function shufflePosters(scene: Scene, random: () => number = Math.random): number {
  let moved = 0;
  for (const kind of ["p", "l"]) {
    const pattern = new RegExp(`^poster90_${kind}_\\d+$`);
    const slots = scene.meshes.filter(
      (m) => pattern.test(m.name) && m.isVerticesDataPresent(VertexBuffer.UVKind),
    );
    if (slots.length < 2) continue;
    const rects = slots.map(uvRect);
    const order = rects.map((_, i) => i);
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
    slots.forEach((slot, i) => {
      const from = rects[i];
      const to = rects[order[i]];
      if (from === to) return;
      const uvs = slot.getVerticesData(VertexBuffer.UVKind);
      if (!uvs) return;
      for (let v = 0; v < uvs.length; v += 2) {
        uvs[v] = to.u0 + ((uvs[v] - from.u0) / (from.u1 - from.u0)) * (to.u1 - to.u0);
        uvs[v + 1] = to.v0 + ((uvs[v + 1] - from.v0) / (from.v1 - from.v0)) * (to.v1 - to.v0);
      }
      slot.setVerticesData(VertexBuffer.UVKind, uvs, false);
      moved++;
    });
  }
  return moved;
}

interface Rect {
  u0: number;
  v0: number;
  u1: number;
  v1: number;
}

/** The atlas rectangle a slot shows: its UVs' bounds (the paper's edge UVs lie inside it). */
function uvRect(mesh: AbstractMesh): Rect {
  const uvs = mesh.getVerticesData(VertexBuffer.UVKind) ?? [0, 0, 1, 1];
  let u0 = Infinity,
    v0 = Infinity,
    u1 = -Infinity,
    v1 = -Infinity;
  for (let i = 0; i < uvs.length; i += 2) {
    u0 = Math.min(u0, uvs[i]);
    u1 = Math.max(u1, uvs[i]);
    v0 = Math.min(v0, uvs[i + 1]);
    v1 = Math.max(v1, uvs[i + 1]);
  }
  return { u0, v0, u1, v1 };
}
