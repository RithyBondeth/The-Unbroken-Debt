// Cracks in the Ep1 studio's plaster (November 2026), one per cell of a 4 x 2 atlas
// (cells 512 x 1024 px, about 1 mm a pixel on the wall). tools/areas/ep1_area_studio.py
// lays each on a wall as a decal (crack_decal) that only darkens what is under it, so
// the colour is near-black and the alpha is the crack.
//
// What makes an old limewash crack read as real, and what the drawn tubes lacked:
// - the line is jagged at small scale (it breaks round the sand in the render) and
//   wanders at large scale, never straight and never a smooth curve;
// - it is widest in the middle (2–4 mm) and tapers to nothing at both ends;
// - a few branches split off at a slant, shorter and thinner, some ending in hairlines;
// - the paint has flaked off along it in places, showing the render under it;
// - dust and damp darken a narrow band either side.
// No network of fine cracks (map cracking was rejected on sight in the village).

/* global rng, clamp, lerp */

import { canvasPage } from "./village.mjs";

const COLS = 4;
const ROWS = 2;
const CELL = [512, 1024];

/** Per cell: how far it wanders, how jagged, how wide (px), branches, chips. */
const CRACKS = [
  { seed: 11, wander: 0.35, jag: 0.75, width: 3.4, branches: 3, chips: 3, stairs: true },
  { seed: 23, wander: 0.25, jag: 0.6, width: 2.6, branches: 2, chips: 2 },
  { seed: 37, wander: 0.3, jag: 0.65, width: 3.0, branches: 2, chips: 4 },
  { seed: 41, wander: 0.4, jag: 0.55, width: 2.2, branches: 2, chips: 1 },
  { seed: 53, wander: 0.2, jag: 0.7, width: 2.8, branches: 3, chips: 2 },
  { seed: 67, wander: 0.45, jag: 0.6, width: 2.0, branches: 1, chips: 1 },
  { seed: 79, wander: 0.3, jag: 0.8, width: 3.6, branches: 3, chips: 3, stairs: true },
  { seed: 83, wander: 0.35, jag: 0.6, width: 2.4, branches: 2, chips: 2 },
];

function paintCracks(ctx, W, H, data) {
  const [cw, ch] = data.cell;
  data.cracks.forEach((spec, k) => {
    const ox = (k % data.cols) * cw;
    const oy = Math.floor(k / data.cols) * ch;
    ctx.save();
    ctx.beginPath();
    ctx.rect(ox, oy, cw, ch);
    ctx.clip();
    crack(ox, oy, cw, ch, spec);
    ctx.restore();
  });

  /**
   * A jagged path from `start` heading `angle` (radians, canvas y down) for `length`
   * px: short straight runs that kink at random, about a slowly drifting heading.
   */
  function path(r, start, angle, length, spec, bounds) {
    const pts = [start];
    let [x, y] = start;
    let heading;
    let drift = 0;
    let travelled = 0;
    let flip = 1;
    while (travelled < length) {
      drift = clamp(drift + r.normal(0.12) * spec.wander, -0.55, 0.55);
      heading = angle + drift;
      // Stair-stepping: the crack follows the brick joints under the render for a while.
      let kink = r.normal(0.42) * spec.jag;
      if (spec.stairs && r() < 0.35) {
        flip = -flip;
        kink = flip * r(0.6, 1.0);
      }
      const step = r(3, 13);
      x += Math.cos(heading + kink) * step;
      y += Math.sin(heading + kink) * step;
      if (bounds && (x < bounds[0] || x > bounds[2] || y < bounds[1] || y > bounds[3])) break;
      pts.push([x, y]);
      travelled += step;
    }
    return pts;
  }

  /** Fills a line along `pts` whose width follows `width(t)`, t = 0..1 along it. */
  function ribbon(pts, width, fill) {
    if (pts.length < 2) return;
    const left = [];
    const right = [];
    for (let i = 0; i < pts.length; i++) {
      const a = pts[Math.max(0, i - 1)];
      const b = pts[Math.min(pts.length - 1, i + 1)];
      let nx = -(b[1] - a[1]);
      let ny = b[0] - a[0];
      const len = Math.hypot(nx, ny) || 1;
      nx /= len;
      ny /= len;
      const w = width(i / (pts.length - 1)) / 2;
      left.push([pts[i][0] + nx * w, pts[i][1] + ny * w]);
      right.push([pts[i][0] - nx * w, pts[i][1] - ny * w]);
    }
    ctx.fillStyle = fill;
    ctx.beginPath();
    left.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    for (let i = right.length - 1; i >= 0; i--) ctx.lineTo(right[i][0], right[i][1]);
    ctx.closePath();
    ctx.fill();
  }

  function stroke(pts, width, style, blur) {
    ctx.save();
    ctx.filter = blur ? `blur(${blur}px)` : "none";
    ctx.strokeStyle = style;
    ctx.lineWidth = width;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.stroke();
    ctx.restore();
  }

  /** Width along a crack: grows from a point, varies, dies away to a hairline. */
  function taper(r, max) {
    const wobble = Array.from({ length: 12 }, () => r(0.65, 1.3));
    return (t) => {
      const i = Math.min(10, Math.floor(t * 11));
      const f = lerp(wobble[i], wobble[i + 1], t * 11 - i);
      return Math.max(0.35, max * Math.pow(Math.sin(Math.PI * clamp(t, 0, 1)), 0.55) * f);
    };
  }

  function crack(ox, oy, cw, ch, spec) {
    const r = rng(spec.seed);
    const bounds = [ox + 18, oy + 12, ox + cw - 18, oy + ch - 12];
    const start = [ox + cw * r(0.38, 0.62), oy + ch * r(0.9, 0.95)];
    const main = path(r, start, -Math.PI / 2 + r.normal(0.12), ch * r(0.8, 0.88), spec, bounds);
    const lines = [{ pts: main, width: taper(r, spec.width) }];
    for (let b = 0; b < spec.branches; b++) {
      const at = main[Math.floor(main.length * r(0.15, 0.8))];
      const side = r() < 0.5 ? -1 : 1;
      // Branches leave at a slant either way along the crack, not all upward like twigs.
      const along = r() < 0.6 ? -Math.PI / 2 : Math.PI / 2;
      const pts = path(r, at, along + side * r(0.3, 0.7), ch * r(0.05, 0.18), spec, bounds);
      lines.push({ pts, width: taper(r, spec.width * r(0.35, 0.6)), from: true });
      // Now and then a hairline off the branch.
      if (r() < 0.5 && pts.length > 6) {
        const at2 = pts[Math.floor(pts.length * r(0.3, 0.7))];
        const hair = path(
          r,
          at2,
          -Math.PI / 2 - side * r(0.3, 0.8),
          ch * r(0.03, 0.08),
          spec,
          bounds,
        );
        lines.push({ pts: hair, width: taper(r, 0.8), from: true });
      }
    }
    // Dust and damp in a narrow band either side, darkest close in.
    for (const { pts } of lines) stroke(pts, 16, "rgba(46,36,26,0.07)", 6);
    for (const { pts } of lines) stroke(pts, 6, "rgba(40,30,22,0.14)", 2);
    // Paint flaked off along the main crack: a ragged patch of the darker render under
    // it, its broken edge a hard line.
    for (let c = 0; c < spec.chips; c++) {
      const [px, py] = main[Math.floor(main.length * r(0.2, 0.85))];
      const size = r(7, 20);
      const off = (r() < 0.5 ? -1 : 1) * size * 0.45;
      const pts = [];
      const n = 9 + Math.floor(r(0, 5));
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2;
        const rr = size * r(0.45, 1.0);
        pts.push([px + off + Math.cos(a) * rr * 0.7, py + Math.sin(a) * rr]);
      }
      ctx.fillStyle = "rgba(58,48,38,0.26)";
      ctx.beginPath();
      pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "rgba(28,22,16,0.5)";
      ctx.lineWidth = 0.9;
      ctx.stroke();
    }
    // The open crack itself, near black, and a darker core where it is deepest.
    for (const { pts, width } of lines) ribbon(pts, width, "rgba(16,12,9,0.96)");
    for (const { pts, width } of lines) ribbon(pts, (t) => width(t) * 0.45, "rgba(4,3,2,1)");
  }
}

export const crackTextures = [
  {
    name: "studio_cracks",
    file: "T_studio_cracks_BC",
    size: [CELL[0] * COLS, CELL[1] * ROWS],
    alpha: true,
    draw: () =>
      canvasPage(CELL[0] * COLS, CELL[1] * ROWS, paintCracks, {
        cell: CELL,
        cols: COLS,
        cracks: CRACKS,
      }),
  },
];
