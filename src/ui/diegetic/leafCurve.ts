/**
 * Shape of a page while it turns. The page is a strip of `segments` pieces
 * hinged at the spine; each piece leans a little further behind the one before
 * it, so the outer edge lags and the page curls like paper instead of turning
 * like a board. Coordinates: x across the book (+x is the right-hand page),
 * y up off the paper.
 */

/**
 * Cross-section of the page at turn progress `t` (0 = lying flat on the right,
 * 1 = lying flat on the left). Returns `segments + 1` points from the spine to
 * the outer edge, each [x, y] in the same units as `width`.
 */
export function leafProfile(
  t: number,
  width: number,
  segments: number,
  curl = 0.9,
): [number, number][] {
  const p = Math.min(1, Math.max(0, t));
  // Ease in and out: the page lifts, travels, then settles.
  const eased = p * p * (3 - 2 * p);
  const angle = eased * Math.PI;
  // The bend is strongest mid-turn and gone at both ends, so the page lands flat.
  const bend = curl * Math.sin(p * Math.PI);
  const step = width / segments;
  const points: [number, number][] = [[0, 0]];
  let x = 0;
  let y = 0;
  for (let i = 0; i < segments; i++) {
    const along = (i + 0.5) / segments;
    const a = Math.min(Math.PI, Math.max(0, angle - bend * along));
    x += Math.cos(a) * step;
    y += Math.sin(a) * step;
    points.push([x, y]);
  }
  return points;
}
