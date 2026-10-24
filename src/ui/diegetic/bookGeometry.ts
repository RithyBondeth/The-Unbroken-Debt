/** Metres, matching the A5 page textures. +Y rises from the paper, +Z goes up the page. */
export const BOOK = { width: 0.148, height: 0.21, block: 0.006, pageY: 0.0005 };

/** The sewn gutter dips between the softly arched paper blocks. */
export function paperHeight(distance: number, z: number): number {
  const u = Math.min(1, Math.max(0, distance / BOOK.width));
  const swell = 0.0065 * Math.sin(Math.PI * u ** 0.42);
  const corner = 0.0012 * u ** 5 * (0.5 + 0.5 * Math.cos(z * 39));
  return BOOK.pageY + swell + corner;
}

/** A rounded rectangle in the X/Z plane, counter-clockwise viewed from above. */
export function roundedOutline(
  width: number,
  depth: number,
  radius: number,
  segments = 8,
): [number, number][] {
  const out: [number, number][] = [];
  for (let c = 0; c < 4; c++) {
    const a = (c * Math.PI) / 2;
    const cx = (c === 0 || c === 3 ? 1 : -1) * (width / 2 - radius);
    const cz = (c < 2 ? 1 : -1) * (depth / 2 - radius);
    for (let k = 0; k <= segments; k++) {
      const angle = a + ((k / segments) * Math.PI) / 2;
      out.push([cx + Math.cos(angle) * radius, cz + Math.sin(angle) * radius]);
    }
  }
  return out;
}
