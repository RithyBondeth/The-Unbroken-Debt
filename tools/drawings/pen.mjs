// Pen, pencil and ink wash on aged paper, for Sora's drawings and the studio's
// prints (Art Bible, section 10: "confident fountain-pen line, ink wash shading").
// A Sheet collects strokes and writes one SVG; render.mjs turns it into a texture.
//
// Draw front to back: `occlude()` a shape once it is drawn, and later strokes
// and washes stop at its edge, as a pen drawing leaves hidden lines out.

export const INK = "#211b16";
export const PENCIL = "#57534e";
export const PAPER = "#e8dcc3";

const f1 = (v) => Math.round(v * 10) / 10;
const smoothstep = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a || 1)));
  return t * t * (3 - 2 * t);
};

/** Seeded random numbers (mulberry32), so every render is identical. */
export function random(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const r = (min = 0, max = 1) => min + (max - min) * next();
  r.normal = (sd = 1) =>
    sd * Math.sqrt(-2 * Math.log(next() || 1e-9)) * Math.cos(2 * Math.PI * next());
  r.pick = (list) => list[Math.floor(next() * list.length)];
  r.chance = (p) => next() < p;
  return r;
}

/** Points on a Catmull-Rom curve through `pts`, about every `step` units. */
export function spline(pts, step = 2.5, closed = false) {
  if (pts.length < 2) return pts.slice();
  const P = closed ? [pts.at(-1), ...pts, pts[0], pts[1]] : [pts[0], ...pts, pts.at(-1)];
  const out = [];
  for (let i = 1; i < P.length - 2; i++) {
    const [p0, p1, p2, p3] = [P[i - 1], P[i], P[i + 1], P[i + 2]];
    const n = Math.max(1, Math.ceil(Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step));
    for (let k = 0; k < n; k++) {
      const t = k / n;
      const t2 = t * t;
      const t3 = t2 * t;
      out.push(
        [0, 1].map(
          (j) =>
            0.5 *
            (2 * p1[j] +
              (p2[j] - p0[j]) * t +
              (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
              (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * t3),
        ),
      );
    }
  }
  out.push(closed ? pts[0] : pts.at(-1));
  return out;
}

/** Straight segments through `pts`, split about every `step` units. */
export function polyline(pts, step = 2.5) {
  const out = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const [a, b] = [pts[i], pts[i + 1]];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step));
    for (let k = 0; k < n; k++)
      out.push([a[0] + ((b[0] - a[0]) * k) / n, a[1] + ((b[1] - a[1]) * k) / n]);
  }
  out.push(pts.at(-1));
  return out;
}

export function ellipse(cx, cy, rx, ry, n = 48, start = 0, end = Math.PI * 2) {
  return Array.from({ length: n + 1 }, (_, k) => {
    const a = start + ((end - start) * k) / n;
    return [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry];
  });
}

function bounds(poly) {
  let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const [x, y] of poly) {
    x0 = Math.min(x0, x);
    y0 = Math.min(y0, y);
    x1 = Math.max(x1, x);
    y1 = Math.max(y1, y);
  }
  return [x0, y0, x1, y1];
}

function inside([x, y], poly) {
  let hit = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

const centroid = (pts) => [
  pts.reduce((s, p) => s + p[0], 0) / pts.length,
  pts.reduce((s, p) => s + p[1], 0) / pts.length,
];

const d = (pts, close = false) =>
  "M" + pts.map((p) => `${f1(p[0])} ${f1(p[1])}`).join("L") + (close ? "Z" : "");

export class Sheet {
  /**
   * @param {object} o
   * @param {number} o.width design units
   * @param {number} o.height
   * @param {number} [o.seed]
   */
  constructor({ width, height, seed = 1 }) {
    this.width = width;
    this.height = height;
    this.seed = seed;
    this.r = random(seed);
    this.pencil = [];
    this.ink = [];
    this.washes = [];
    this.over = [];
    this.occluders = [];
    this.masks = [];
    /** Where the ink has reached. Elsewhere the drawing is still only pencil. */
    this.inked = () => true;
    /** Pencil left under finished ink (0 = rubbed out). */
    this.underdrawing = 0.12;
    /** Outline of the inked part, if not all of it: washes stop at its edge. */
    this.inkedArea = null;
  }

  /** Later strokes and washes stop at this shape's edge. */
  occlude(poly) {
    this.occluders.push({ poly, box: bounds(poly) });
  }

  hidden(p) {
    for (const { poly, box } of this.occluders) {
      if (p[0] < box[0] || p[0] > box[2] || p[1] < box[1] || p[1] > box[3]) continue;
      if (inside(p, poly)) return true;
    }
    return false;
  }

  /** Splits a sampled path into the runs not hidden behind an occluder. */
  visible(path) {
    if (!this.occluders.length) return [path];
    const runs = [];
    let run = [];
    for (const p of path) {
      if (this.hidden(p)) {
        if (run.length > 1) runs.push(run);
        run = [];
      } else run.push(p);
    }
    if (run.length > 1) runs.push(run);
    return runs;
  }

  /** A hand's slow wander off the ideal line. */
  shake(path, amp) {
    if (!amp) return path;
    const [a, b, c] = [this.r(0, 6.3), this.r(0, 6.3), this.r(14, 22)];
    let s = 0;
    return path.map((p, i) => {
      const q = path[Math.min(i + 1, path.length - 1)];
      const o = path[Math.max(i - 1, 0)];
      const tx = q[0] - o[0];
      const ty = q[1] - o[1];
      const len = Math.hypot(tx, ty) || 1;
      if (i) s += Math.hypot(p[0] - path[i - 1][0], p[1] - path[i - 1][1]);
      const off = amp * (0.65 * Math.sin(s / 41 + a) + 0.35 * Math.sin(s / c + b));
      return [p[0] - (ty / len) * off, p[1] + (tx / len) * off];
    });
  }

  /** Outline of a nib stroke: swells after the touch-down, thins as the pen lifts. */
  nib(pts, w, taper, ruled) {
    const n = pts.length;
    const s = [0];
    for (let i = 1; i < n; i++)
      s.push(s[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const L = s[n - 1] || 1;
    const rampIn = Math.min(L * 0.3, (4 + 2 * w) * taper * 4);
    const rampOut = Math.min(L * 0.45, (8 + 4 * w) * taper * 4);
    const phase = this.r(0, 6.3);
    const left = [];
    const right = [];
    for (let i = 0; i < n; i++) {
      const q = pts[Math.min(i + 1, n - 1)];
      const o = pts[Math.max(i - 1, 0)];
      const tx = q[0] - o[0];
      const ty = q[1] - o[1];
      const len = Math.hypot(tx, ty) || 1;
      let hw = w / 2;
      if (!ruled) {
        hw *=
          (0.4 + 0.6 * smoothstep(0, rampIn, s[i])) *
          (0.2 + 0.8 * smoothstep(0, rampOut, L - s[i]));
        hw *= 1 + 0.14 * Math.sin(s[i] / 27 + phase);
      }
      left.push([pts[i][0] - (ty / len) * hw, pts[i][1] + (tx / len) * hw]);
      right.push([pts[i][0] + (ty / len) * hw, pts[i][1] - (tx / len) * hw]);
    }
    return d([...left, ...right.reverse()], true);
  }

  /**
   * A pen line along a smooth curve through `pts` (or straight segments).
   * `detail` lines (hatching, texture) were never pencilled first.
   */
  stroke(
    pts,
    {
      w = 2.2,
      smooth = true,
      shake = 0.5,
      taper = 0.25,
      detail = false,
      ink,
      ruled = false,
      opacity = 1,
      color,
    } = {},
  ) {
    if (pts.length < 2) return;
    let path = smooth && pts.length > 2 ? spline(pts) : polyline(pts);
    path = this.shake(path, ruled ? 0 : shake);
    const inked = ink ?? this.inked(...centroid(pts));
    for (const run of this.visible(path)) {
      if (!detail) {
        const o = inked ? this.underdrawing : 0.55;
        if (o > 0)
          this.pencil.push(
            `<path d="${d(run.filter((_, i) => i % 2 === 0 || i === run.length - 1))}" stroke-opacity="${o}" stroke-width="${f1(Math.max(0.9, w * 0.5))}"/>`,
          );
      }
      if (inked)
        this.ink.push(
          `<path d="${this.nib(run, w, taper, ruled)}"${opacity < 1 ? ` opacity="${opacity}"` : ""}${color ? ` fill="${color}"` : ""}/>`,
        );
    }
  }

  line(x0, y0, x1, y1, o = {}) {
    const n = Math.max(2, Math.round(Math.hypot(x1 - x0, y1 - y0) / 40));
    const pts = Array.from({ length: n + 1 }, (_, k) => [
      x0 + ((x1 - x0) * k) / n,
      y0 + ((y1 - y0) * k) / n,
    ]);
    this.stroke(pts, { smooth: false, ...o });
  }

  /** Pencil only: construction lines Sora has not inked (or rubbed out). */
  guide(pts, { opacity = 0.35, w = 1.0, smooth = true } = {}) {
    const path = smooth && pts.length > 2 ? spline(pts) : polyline(pts);
    for (const run of this.visible(path))
      this.pencil.push(`<path d="${d(run)}" stroke-opacity="${opacity}" stroke-width="${w}"/>`);
  }

  /** Parallel hatching inside `poly` at `angle` (radians), `gap` apart. */
  hatch(
    poly,
    { angle = 0.9, gap = 7, w = 1.1, jitter = 0.25, shorten = 0.12, ink, opacity = 1, color } = {},
  ) {
    const [x0, y0, x1, y1] = bounds(poly);
    const dx = Math.cos(angle);
    const dy = Math.sin(angle);
    const nx = -dy;
    const ny = dx;
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const R = Math.hypot(x1 - x0, y1 - y0) / 2 + 2;
    for (let k = -R; k <= R; k += gap * this.r(0.8, 1.2)) {
      const ox = cx + nx * k;
      const oy = cy + ny * k;
      const ts = [];
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const [ax, ay] = poly[j];
        const [bx, by] = poly[i];
        const ex = bx - ax;
        const ey = by - ay;
        const den = dx * ey - dy * ex;
        if (Math.abs(den) < 1e-9) continue;
        const t = ((ax - ox) * ey - (ay - oy) * ex) / den;
        const u = ((ax - ox) * dy - (ay - oy) * dx) / den;
        if (u >= 0 && u < 1) ts.push(t);
      }
      ts.sort((a, b) => a - b);
      for (let i = 0; i + 1 < ts.length; i += 2) {
        const len = ts[i + 1] - ts[i];
        if (len < 3) continue;
        const a = ts[i] + len * this.r(0, shorten);
        const b = ts[i + 1] - len * this.r(0, shorten);
        const tilt = this.r(-jitter, jitter) * 0.05;
        this.stroke(
          [
            [ox + dx * a, oy + dy * a],
            [ox + dx * b + nx * tilt * len, oy + dy * b + ny * tilt * len],
          ],
          { w, smooth: false, shake: 0.3, taper: 0.35, detail: true, ink, opacity, color },
        );
      }
    }
  }

  /** A transparent glaze of diluted ink over `poly`. */
  wash(poly, { opacity = 0.16, ink, smooth = true } = {}) {
    if (!(ink ?? poly.some((p) => this.inked(...p)))) return;
    const shape = smooth ? spline(poly, 6, true) : poly;
    // Masked only by the occluders it overlaps (the wash filter spreads it ~8 units).
    const [x0, y0, x1, y1] = bounds(shape);
    const over = [];
    this.occluders.forEach(({ box }, i) => {
      if (box[0] < x1 + 10 && box[2] > x0 - 10 && box[1] < y1 + 10 && box[3] > y0 - 10)
        over.push(i);
    });
    let mask = "";
    if (over.length) {
      const id = `m${this.masks.length}`;
      this.masks.push(
        `<mask id="${id}" maskUnits="userSpaceOnUse" x="0" y="0" width="${this.width}" height="${this.height}"><rect width="${this.width}" height="${this.height}" fill="#fff"/>${over.map((i) => `<use href="#o${i}"/>`).join("")}</mask>`,
      );
      mask = ` mask="url(#${id})"`;
    }
    this.washes.push(`<path d="${d(shape, true)}" opacity="${opacity}"${mask}/>`);
  }

  /** Lettering: inked where the ink has reached, pencilled elsewhere. */
  text(
    str,
    x,
    y,
    {
      size = 40,
      font = "Freehand",
      anchor = "middle",
      ink,
      opacity,
      spacing = 0,
      rotate = 0,
      weight = 400,
      fill,
      outline,
    } = {},
  ) {
    const inked = ink ?? this.inked(x, y);
    const attrs = `x="${f1(x)}" y="${f1(y)}" font-family="${font}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" letter-spacing="${spacing}"${rotate ? ` transform="rotate(${rotate} ${f1(x)} ${f1(y)})"` : ""}`;
    const paint = outline
      ? ` fill="none" stroke="${fill ?? INK}" stroke-width="${outline}"`
      : fill
        ? ` fill="${fill}"`
        : "";
    if (inked)
      this.ink.push(
        `<text ${attrs}${paint}${opacity ? ` opacity="${opacity}"` : ""}>${str}</text>`,
      );
    else
      this.pencil.push(
        `<text ${attrs} fill="${PENCIL}" stroke="none" opacity="${opacity ?? 0.5}">${str}</text>`,
      );
  }

  /** Raw SVG drawn over everything (tape, pins, stains). */
  top(svg) {
    this.over.push(svg);
  }

  svg({ paper = PAPER, foxing = 24, age = 1 } = {}) {
    const { width: W, height: H, r } = this;
    const all = `filterUnits="userSpaceOnUse" x="0" y="0" width="${W}" height="${H}"`;
    const spots = [];
    for (let k = 0; k < foxing; k++) {
      const edge = r.chance(0.7);
      const x = edge ? r.pick([r(0, W * 0.12), r(W * 0.88, W)]) : r(0, W);
      const y = edge ? r(0, H) : r.pick([r(0, H * 0.1), r(H * 0.9, H)]);
      spots.push(
        `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(r(2, 9) * (W / 1000))}" fill="url(#fox)" opacity="${f1(r(0.25, 0.7) * age * 10) / 10}"/>`,
      );
    }
    const masks = [
      ...this.occluders.map(({ poly }, i) => `<path id="o${i}" d="${d(poly, true)}" fill="#000"/>`),
      ...this.masks,
    ];
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" width="100%" height="100%">
<defs>
<filter id="tone" ${all}><feTurbulence type="fractalNoise" baseFrequency="${f1(5000 / W) / 1000}" numOctaves="4" seed="${this.seed}"/><feColorMatrix type="matrix" values="0 0 0 0 0.42 0 0 0 0 0.31 0 0 0 0 0.17 ${0.55 * age} 0 0 0 ${-0.2 * age}"/></filter>
<filter id="grain" ${all}><feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="${this.seed + 1}"/><feColorMatrix type="matrix" values="0 0 0 0 0.3 0 0 0 0 0.24 0 0 0 0 0.16 0.35 0 0 0 -0.1"/></filter>
<filter id="nib" ${all}><feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves="2" seed="5" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.2" xChannelSelector="R" yChannelSelector="G" result="d"/><feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="2" seed="9" result="g"/><feColorMatrix in="g" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.5 0 0 0 0.78" result="ga"/><feComposite in="d" in2="ga" operator="in"/></filter>
<filter id="pencil" ${all}><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="3" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 2.2 0 0 0 -0.5" result="m"/><feComposite in="SourceGraphic" in2="m" operator="in"/></filter>
<filter id="wash"><feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="3" seed="21" result="warp"/><feDisplacementMap in="SourceGraphic" in2="warp" scale="16" xChannelSelector="R" yChannelSelector="G" result="shape"/><feTurbulence type="fractalNoise" baseFrequency="0.22" numOctaves="3" seed="4" result="g"/><feColorMatrix in="g" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1.1 0 0 0 0.1" result="ga"/><feComposite in="shape" in2="ga" operator="in" result="body"/><feMorphology in="shape" operator="erode" radius="2.2" result="inner"/><feComposite in="shape" in2="inner" operator="out" result="edge"/><feGaussianBlur in="edge" stdDeviation="0.9" result="soft"/><feMerge><feMergeNode in="body"/><feMergeNode in="soft"/></feMerge></filter>
<radialGradient id="fox"><stop offset="0" stop-color="#8a5a2b" stop-opacity="0.55"/><stop offset="0.6" stop-color="#9a6a35" stop-opacity="0.25"/><stop offset="1" stop-color="#9a6a35" stop-opacity="0"/></radialGradient>
<radialGradient id="age" cx="0.5" cy="0.5" r="0.75"><stop offset="0.55" stop-color="#7a5a30" stop-opacity="0"/><stop offset="1" stop-color="#7a5a30" stop-opacity="${0.28 * age}"/></radialGradient>
${masks.join("\n")}
${this.inkedArea ? `<clipPath id="inkedArea"><path d="${d(this.inkedArea, true)}"/></clipPath>` : ""}
</defs>
<rect width="${W}" height="${H}" fill="${paper}"/>
<rect width="${W}" height="${H}" filter="url(#tone)"/>
<rect width="${W}" height="${H}" fill="url(#age)"/>
${spots.join("")}
<g filter="url(#pencil)" fill="none" stroke="${PENCIL}" stroke-linecap="round" stroke-linejoin="round">${this.pencil.join("")}</g>
<g fill="${INK}"${this.inkedArea ? ' clip-path="url(#inkedArea)"' : ""}>${this.washes.map((w) => w.replace("<path ", '<path filter="url(#wash)" ')).join("")}</g>
<g fill="${INK}" filter="url(#nib)">${this.ink.join("")}</g>
<rect width="${W}" height="${H}" filter="url(#grain)"/>
${this.over.join("\n")}
</svg>`;
  }
}
