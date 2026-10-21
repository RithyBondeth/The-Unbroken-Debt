// Episode 1 drawings and prints for Sora's studio (Episode 1 Beat Sheet 4.1:
// "drafting table, ink bottles, typography prints"). Each entry renders to
// art-source/textures/ep1/<file>.png at `size` pixels; `npm run drawings -- ep1`.
//
// Khmer text: every string is listed in KHMER below for the native-speaker and
// cultural-advisor review (Cultural Guide, section 4). Keep it to that list.

import { ellipse, Sheet } from "./pen.mjs";

/** Every Khmer string on the studio's paper, with its meaning. Review: pending. */
export const KHMER = {
  watPhnom: ["វត្តភ្នំ", "Wat Phnom (title of the illustration)"],
  phnomPenh: ["ភ្នំពេញ", "Phnom Penh"],
  year: ["១៩៣២", "1932"],
  lastYear: ["១៩៣១", "1931"],
  byline: ["គំនូរដោយ សូរ៉ា", "drawing by Sora"],
  sora: ["សូរ៉ា", "Sora (her signature)"],
  tonleSap: ["ទន្លេសាប", "Tonle Sap"],
  sugarPalms: ["ដើមត្នោត", "sugar palm trees"],
  woodenHouse: ["ផ្ទះឈើ", "wooden house"],
  boat: ["ទូក", "boat"],
  angkorWat: ["អង្គរវត្ត", "Angkor Wat (caption of the framed print)"],
  ornament: ["ក្បាច់", "ornament"],
  lotus: ["ផ្កាឈូក", "lotus flower"],
  naga: ["នាគ", "naga"],
  letters: ["អក្សរ", "letters"],
  khmerScript: ["អក្សរខ្មែរ", "Khmer script (title of the alphabet chart)"],
  consonantCount: ["ព្យញ្ជនៈ ៣៣ តួ", "the 33 consonants"],
  consonants: [
    "ក ខ គ ឃ ង ច ឆ ជ ឈ ញ ដ ឋ ឌ ឍ ណ ត ថ ទ ធ ន ប ផ ព ភ ម យ រ ល វ ស ហ ឡ អ",
    "the consonants, in order",
  ],
  numerals: ["០ ១ ២ ៣ ៤ ៥ ៦ ៧ ៨ ៩", "numerals 0 to 9"],
};

const RED = "#9b2a1f";

const lerp = (a, b, t) => a + (b - a) * t;

// ------------------------------------------------------------------ motifs

/** A Borassus (sugar) palm: tall straight trunk, round crown of stiff fans. */
function palm(s, x, ground, height, { lean = 0, size = 1, fans = 26 } = {}) {
  const r = s.r;
  const top = [x + lean, ground - height];
  const mid = [x + lean * 0.4 + r(-6, 6), ground - height * 0.5];
  const at = (t) => [
    (1 - t) ** 2 * x + 2 * (1 - t) * t * mid[0] + t * t * top[0],
    (1 - t) ** 2 * ground + 2 * (1 - t) * t * mid[1] + t * t * top[1],
  ];
  const half = (t) => ((16 - 5 * t) * size) / 2 + (t < 0.05 ? (0.05 - t) * 90 * size : 0);
  const R = 64 * size;
  const C = top;
  const samples = Array.from({ length: 25 }, (_, k) => (k / 24) * 0.97);
  const left = samples.map((t) => [at(t)[0] - half(t), at(t)[1]]);
  const right = samples.map((t) => [at(t)[0] + half(t), at(t)[1]]);

  if (!s.inked(...C)) {
    // Still pencil: the crown blocked in with a circle and a few fans.
    s.guide(ellipse(C[0], C[1] - 4 * size, R * 1.1, R * 0.92, 40), { opacity: 0.38 });
    for (let i = 0; i < 7; i++) {
      const a = -Math.PI * 1.05 + (i / 6) * Math.PI * 1.1 + r(-0.15, 0.15);
      const k = r(0.35, 0.55);
      s.guide(
        [
          [C[0] + Math.cos(a) * R * k, C[1] + Math.sin(a) * R * k * 0.9],
          [C[0] + Math.cos(a) * R * 1.05, C[1] + Math.sin(a) * R * 0.9],
        ],
        { opacity: 0.25, smooth: false },
      );
    }
  } else {
    s.guide(ellipse(C[0], C[1] - 4 * size, R * 1.1, R * 0.92, 40), { opacity: 0.08 });
    for (let i = 0; i < fans; i++) {
      let a = r(-Math.PI, Math.PI);
      if (Math.abs(a - Math.PI / 2) < 0.45)
        a = Math.PI / 2 + (a < Math.PI / 2 ? -1 : 1) * r(0.45, 0.8);
      const down = Math.max(0, Math.sin(a));
      const dir = [Math.cos(a), Math.sin(a)];
      const L1 = r(14, 26) * size;
      const B = [C[0] + dir[0] * L1, C[1] + dir[1] * L1 * 0.85 + down * 4 * size];
      s.stroke([C, B], { w: 1.6 * size, detail: true, smooth: false });
      const spread = r(0.7, 1.5);
      const L2 = r(44, 60) * size;
      const blade = [];
      for (let k = 0; k < 8; k++) {
        const b = a + spread * (k / 7 - 0.5);
        const droop = (0.15 * Math.abs(Math.cos(b)) + 0.3 * down) * L2;
        const tip = [B[0] + Math.cos(b) * L2, B[1] + Math.sin(b) * L2 + droop];
        const bend = [B[0] + Math.cos(b) * L2 * 0.5, B[1] + Math.sin(b) * L2 * 0.5 + droop * 0.25];
        s.stroke([B, bend, tip], { w: 1.3 * size, detail: true, taper: 0.45, shake: 0.2 });
        blade.push([lerp(B[0], tip[0], 0.66), lerp(B[1], tip[1], 0.66)]);
      }
      s.stroke(blade, { w: 1.1 * size, detail: true, shake: 0.5 });
      s.wash([B, ...blade], {
        opacity: 0.08 + down * 0.24 + (dir[0] < 0 ? 0.06 : 0),
        smooth: false,
      });
    }
    // The dark heart of the crown and its shaded underside.
    s.wash(ellipse(C[0], C[1] + 4 * size, 26 * size, 20 * size, 16), { opacity: 0.55 });
    s.hatch(ellipse(C[0] - 6 * size, C[1] + 8 * size, R * 0.7, R * 0.42, 20, 0, Math.PI), {
      angle: 0.8,
      gap: 4 * size,
      w: 0.95 * size,
    });
    // Last year's fans, dry and hanging in a skirt under the crown.
    for (let i = 0; i < 6; i++) {
      const a = Math.PI / 2 + r(-0.9, 0.9);
      const B = [C[0] + Math.cos(a) * 16 * size, C[1] + 12 * size];
      const L2 = r(50, 72) * size;
      const tips = [];
      for (let k = 0; k < 6; k++) {
        const b = a + 0.3 * (k / 5 - 0.5);
        const tip = [B[0] + Math.cos(b) * L2 * 0.5, B[1] + L2];
        s.stroke([B, [lerp(B[0], tip[0], 0.5) + r(-2, 2), B[1] + L2 * 0.5], tip], {
          w: 1.1 * size,
          detail: true,
        });
        tips.push(tip);
      }
      s.wash([B, ...tips], { opacity: 0.32, smooth: false });
    }
    for (let k = 0; k < 7; k++) {
      const p = [C[0] + r(-14, 14) * size, C[1] + r(6, 18) * size];
      s.stroke(ellipse(p[0], p[1], 5.5 * size, 5 * size, 12), { w: 1.3 * size, detail: true });
      s.wash(ellipse(p[0], p[1], 5 * size, 5 * size, 8), { opacity: 0.55, smooth: false });
    }
  }
  s.occlude(ellipse(C[0], C[1] + 6 * size, 30 * size, 26 * size, 16));

  // Trunk: outlines, growth rings, shade on the side away from the light.
  s.stroke(left, { w: 2.5 * size });
  s.stroke(right, { w: 2.1 * size });
  for (let t = 0.04; t < 0.95; t += (11 / height) * r(0.8, 1.3)) {
    const [cx, cy] = at(t);
    const h = half(t);
    s.stroke(
      [
        [cx - h, cy],
        [cx - h * 0.2, cy + 1.6],
        [cx + h * r(0.1, 0.6), cy + 1],
      ],
      { w: 1.0 * size, detail: true, taper: 0.5 },
    );
  }
  const shadeSide = [
    ...left,
    ...samples.map((t) => [at(t)[0] - half(t) * 0.15, at(t)[1]]).reverse(),
  ];
  s.hatch(shadeSide, { angle: Math.PI / 2 + 0.05, gap: 3.2 * size, w: 0.95 * size });
  s.wash([...left, ...right.slice().reverse()], { opacity: 0.16, smooth: false });
  s.occlude([...left, ...right.slice().reverse()]);
}

/**
 * A rounded mass of leaves: a scalloped edge lost where the light falls (upper
 * right), leaf marks gathering in the shade below, a glaze of wash.
 */
function clump(s, cx, cy, rx, ry, { weight = 1, shade = 0.2 } = {}) {
  const r = s.r;
  const n = Math.max(9, Math.round((rx + ry) / 7));
  const pts = [];
  for (let k = 0; k < n; k++) {
    const a = (k / n) * Math.PI * 2 + r(-0.1, 0.1);
    const m = 1 + r(-0.16, 0.12);
    pts.push([cx + Math.cos(a) * rx * m, cy + Math.sin(a) * ry * m]);
  }
  const outline = [];
  for (let k = 0; k < n; k++) {
    const a = pts[k];
    const b = pts[(k + 1) % n];
    const mx = (a[0] + b[0]) / 2;
    const my = (a[1] + b[1]) / 2;
    const len = Math.hypot(mx - cx, my - cy) || 1;
    const bulge = Math.hypot(b[0] - a[0], b[1] - a[1]) * r(0.3, 0.55);
    outline.push(a, [mx + ((mx - cx) / len) * bulge, my + ((my - cy) / len) * bulge]);
  }
  if (!s.inked(cx, cy)) {
    s.guide([...pts, pts[0]], { opacity: 0.3 });
    s.occlude(outline);
    return outline;
  }
  const ring = [...outline, outline[0]];
  for (let i = 0; i < ring.length - 1;) {
    const len = 2 + Math.floor(r(0, 4));
    const seg = ring.slice(i, i + len + 1);
    const [mx, my] = seg[Math.floor(seg.length / 2)];
    const lit = Math.cos(Math.atan2(my - cy, mx - cx) + Math.PI / 4);
    if (seg.length > 1 && !(lit > 0.35 && r.chance(0.6)))
      s.stroke(seg, { w: (1.1 + (1 - lit) * 0.75) * weight, shake: 0.5, detail: lit > 0.35 });
    i += len;
  }
  // Leaf clusters: little runs of scallops, thick in the shade, sparse in the light.
  const count = Math.round((rx * ry) / 60);
  for (let k = 0; k < count; k++) {
    const u = r(-1, 1);
    const v = r(-1, 1);
    if (u * u + v * v > 0.75) continue;
    const dark = ((v + 1) / 2) * 0.75 + ((1 - u) / 2) * 0.25;
    if (!r.chance(0.08 + dark * dark * 0.92)) continue;
    const px = cx + u * rx;
    const py = cy + v * ry;
    const sz = r(3.5, 6) * weight;
    const bumps = 2 + Math.floor(r(0, 3));
    const run = [];
    for (let b = 0; b <= bumps * 2; b++)
      run.push([px + (b - bumps) * sz * 0.9, py + (b % 2 ? sz * 0.7 : 0) + r(-0.6, 0.6)]);
    s.stroke(run, { w: (0.8 + dark * 0.5) * weight, detail: true, taper: 0.45, shake: 0.15 });
  }
  const shaded = outline.filter(([x, y]) => (y - cy) / ry - (x - cx) / rx > 0.1);
  if (shaded.length > 2) s.wash(shaded, { opacity: shade });
  s.wash(outline, { opacity: shade * 0.5 });
  s.occlude(outline);
  return outline;
}

/** A belt of trees: two or three leaf masses each, trunks showing below. */
function grove(
  s,
  x0,
  x1,
  base,
  { count = 8, hMin = 120, hMax = 200, rx = [45, 75], trunks = false } = {},
) {
  const r = s.r;
  const trees = [];
  for (let k = 0; k < count; k++) {
    const h = r(hMin, hMax);
    trees.push({
      x: lerp(x0, x1, (k + r(0.15, 0.85)) / count),
      h,
      rx: r(...rx),
      y: base - h * r(0.55, 0.72),
    });
  }
  const masses = [];
  for (const t of trees) {
    const n = 2 + Math.floor(r(0, 2));
    for (let j = 0; j < n; j++)
      masses.push([
        t.x + r(-0.55, 0.55) * t.rx,
        t.y - j * t.rx * 0.5 + r(-8, 8),
        t.rx * r(0.7, 1.0),
        t.rx * r(0.5, 0.68),
      ]);
  }
  masses.sort((a, b) => b[1] + b[3] - (a[1] + a[3]));
  for (const m of masses) clump(s, ...m, { shade: r(0.14, 0.28) });
  if (trunks)
    for (const t of trees) {
      const y = t.y + t.rx * 0.35;
      s.stroke(
        [
          [t.x - 5, base],
          [t.x - 4, lerp(base, y, 0.5)],
          [t.x - 10, y],
        ],
        { w: 1.8 },
      );
      s.stroke(
        [
          [t.x + 5, base],
          [t.x + 5, lerp(base, y, 0.6)],
          [t.x + 13, y],
        ],
        { w: 1.6 },
      );
      s.hatch(
        [
          [t.x - 5, base],
          [t.x - 10, y],
          [t.x, y],
          [t.x, base],
        ],
        { angle: Math.PI / 2, gap: 3, w: 0.8 },
      );
    }
}

/** A short concave Khmer gable: naga bargeboards, spikes, end hooks, chovea. */
function gable(s, P, half, base, apex, { tympanum = false, tiles = false, w = 2.0 } = {}) {
  const r = s.r;
  const edge = (side, t, inset = 0) => [
    side * (half * (1 - t) - inset * 0.4),
    base + (apex - base) * t ** 1.22 - inset,
  ];
  const T = (t) => Array.from({ length: 13 }, (_, k) => t[0] + ((t[1] - t[0]) * k) / 12);
  for (const side of [-1, 1]) {
    s.stroke(P(T([0, 1]).map((t) => edge(side, t))), { w });
    s.stroke(P(T([0.04, 0.93]).map((t) => edge(side, t, 11))), { w: w * 0.7 });
    // Flame spikes along the naga's back.
    for (const t of [0.14, 0.28, 0.42, 0.56, 0.7, 0.83]) {
      const [x, y] = edge(side, t);
      const [x2, y2] = edge(side, t + 0.02);
      const len = Math.hypot(x2 - x, y2 - y) || 1;
      const nx = -(y2 - y) / len;
      const ny = (x2 - x) / len;
      const out = ny > 0 ? 1 : -1;
      s.stroke(
        P([
          [x, y],
          [x + nx * out * 7 + (x2 - x) * 2, y + ny * out * 7 + 2],
          [x + nx * out * 13 + (x2 - x) * 4, y + ny * out * 12 + 5],
        ]),
        { w: w * 0.6, detail: true, taper: 0.5 },
      );
    }
    // The naga's head curling up at the foot of each bargeboard.
    const hx = side * half;
    s.stroke(
      P([
        [hx, base],
        [hx + side * 13, base - 3],
        [hx + side * 23, base + 5],
        [hx + side * 24, base + 17],
        [hx + side * 17, base + 22],
        [hx + side * 12, base + 16],
      ]),
      { w: w * 0.85 },
    );
    s.stroke(
      P([
        [hx + side * 20, base + 22],
        [hx + side * 22, base + 31],
        [hx + side * 18, base + 39],
      ]),
      { w: w * 0.5, detail: true },
    );
  }
  // Chovea: the slender horn at the apex, its tip turned like a bird's beak.
  s.stroke(
    P([
      [0, apex],
      [2, apex + 18],
      [-1, apex + 38],
      [-9, apex + 52],
      [-21, apex + 56],
    ]),
    { w: w * 1.1 },
  );
  s.stroke(
    P([
      [4, apex - 2],
      [6, apex + 16],
      [3, apex + 34],
      [-4, apex + 47],
    ]),
    { w: w * 0.6, detail: true },
  );
  if (tympanum) {
    const tb = base + 14;
    const inner = [
      ...T([0, 0.86]).map((t) => edge(-1, t, 24)),
      ...T([0, 0.86])
        .reverse()
        .map((t) => edge(1, t, 24)),
    ];
    s.stroke(P(inner), { w: w * 0.6 });
    s.stroke(
      P([
        [-half + 26, tb],
        [half - 26, tb],
      ]),
      { w: w * 0.7, smooth: false },
    );
    // Dharma wheel in the middle; flame scrolls around it.
    const cy = lerp(tb, apex, 0.36);
    s.stroke(P(ellipse(0, cy, 24, 24, 30)), { w: w * 0.8 });
    s.stroke(P(ellipse(0, cy, 16, 16, 24)), { w: w * 0.5, detail: true });
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2;
      s.stroke(
        P([
          [Math.cos(a) * 4, cy + Math.sin(a) * 4],
          [Math.cos(a) * 16, cy + Math.sin(a) * 16],
        ]),
        { w: w * 0.45, detail: true, smooth: false },
      );
    }
    // Carved flame scrolls (kbach) filling the panel, mirrored about the axis.
    for (let gy = tb + 12; gy < apex - 46; gy += 15) {
      const xi = (half - 32) * (1 - (gy - tb) / (apex - 34 - tb));
      for (let gx = xi - 8; gx > 6; gx -= 16) {
        if (Math.hypot(gx, gy - cy) < 30) continue;
        const j = r(-1.5, 1.5);
        for (const side of [-1, 1]) {
          const X = (v) => side * (gx + v);
          s.stroke(
            P([
              [X(-5), gy - 2 + j],
              [X(-1), gy + 4],
              [X(4), gy + 2],
              [X(3), gy - 3],
              [X(-1), gy - 2],
            ]),
            { w: w * 0.45, detail: true, taper: 0.4, shake: 0.1 },
          );
          s.stroke(
            P([
              [X(4), gy + 2],
              [X(9), gy + 6],
              [X(12), gy + 11],
            ]),
            { w: w * 0.4, detail: true, taper: 0.5, shake: 0.1 },
          );
        }
      }
    }
    s.wash(P(inner), { opacity: 0.12 });
  }
  const outline = [
    ...T([0, 1]).map((t) => edge(-1, t)),
    ...T([0, 1])
      .reverse()
      .map((t) => edge(1, t)),
  ];
  if (tiles) {
    // Tiled roof showing beyond the gable in front (hidden parts drop out).
    const roof = [
      ...T([0, 0.9]).map((t) => edge(-1, t, 13)),
      ...T([0, 0.9])
        .reverse()
        .map((t) => edge(1, t, 13)),
    ];
    s.hatch(P(roof), { angle: Math.PI / 2 + 0.04, gap: 6, w: 0.8, shorten: 0.05 });
    s.wash(P(roof), { opacity: 0.12, smooth: false });
  }
  s.wash(
    P([
      ...T([0, 0.95]).map((t) => edge(-1, t)),
      ...T([0, 0.95])
        .reverse()
        .map((t) => edge(-1, t, 11)),
    ]),
    { opacity: 0.22, smooth: false },
  );
  s.occlude(P([[-half - 26, base - 4], ...outline, [half + 26, base - 4]]));
}

/** A Khmer vihara in front elevation: plinth, columns, tiered gables. */
function vihara(s, cx, yb, sc) {
  const P = (pts) => pts.map(([x, y]) => [cx + x * sc, yb - y * sc]);
  const r = s.r;
  // Columns with lotus capitals (front-most).
  for (const x of [-182, -140, -90, -40, 40, 90, 140, 182]) {
    const col = [
      [x - 5.5, 30],
      [x - 5.5, 104],
      [x + 5.5, 104],
      [x + 5.5, 30],
    ];
    s.stroke(
      P([
        [x - 5.5, 30],
        [x - 5.5, 104],
      ]),
      { w: 1.8, smooth: false },
    );
    s.stroke(
      P([
        [x + 5.5, 30],
        [x + 5.5, 104],
      ]),
      { w: 1.6, smooth: false },
    );
    s.stroke(
      P([
        [x - 8, 26],
        [x - 8, 31],
        [x + 8, 31],
        [x + 8, 26],
      ]),
      { w: 1.4, smooth: false },
    );
    s.stroke(
      P([
        [x - 5.5, 104],
        [x - 9, 111],
        [x + 9, 111],
        [x + 5.5, 104],
      ]),
      { w: 1.4 },
    );
    s.stroke(
      P([
        [x - 10, 111],
        [x - 10, 116],
        [x + 10, 116],
        [x + 10, 111],
      ]),
      { w: 1.3, smooth: false },
    );
    s.hatch(
      P([
        [x - 5.5, 31],
        [x - 5.5, 104],
        [x - 1, 104],
        [x - 1, 31],
      ]),
      { angle: Math.PI / 2, gap: 3, w: 0.8 },
    );
    s.occlude(
      P([
        [x - 10, 26],
        [x - 10, 116],
        [x + 10, 116],
        [x + 10, 26],
      ]),
    );
    void col;
  }
  // Doorway and windows on the shaded wall behind the columns.
  s.stroke(
    P([
      [-24, 30],
      [-24, 94],
      [24, 94],
      [24, 30],
    ]),
    { w: 1.8, smooth: false },
  );
  s.stroke(
    P([
      [0, 30],
      [0, 94],
    ]),
    { w: 1.0, smooth: false },
  );
  for (const side of [-1, 1]) {
    s.stroke(
      P([
        [side * 5, 40],
        [side * 5, 62],
        [side * 19, 62],
        [side * 19, 40],
        [side * 5, 40],
      ]),
      { w: 0.9, smooth: false, detail: true },
    );
    s.stroke(
      P([
        [side * 5, 68],
        [side * 5, 88],
        [side * 19, 88],
        [side * 19, 68],
        [side * 5, 68],
      ]),
      { w: 0.9, smooth: false, detail: true },
    );
  }
  s.stroke(
    P([
      [-30, 94],
      [-26, 104],
      [0, 110],
      [26, 104],
      [30, 94],
    ]),
    { w: 1.2 },
  );
  for (const x of [-115, -161, 115, 161]) {
    s.stroke(
      P([
        [x - 11, 46],
        [x - 11, 92],
        [x + 11, 92],
        [x + 11, 46],
        [x - 11, 46],
      ]),
      { w: 1.3, smooth: false },
    );
    for (const bx of [-6, -2, 2, 6])
      s.stroke(
        P([
          [x + bx, 47],
          [x + bx, 91],
        ]),
        { w: 1.0, smooth: false, detail: true },
      );
  }
  s.wash(
    P([
      [-24, 30],
      [-24, 94],
      [24, 94],
      [24, 30],
    ]),
    { opacity: 0.55, smooth: false },
  );
  s.wash(
    P([
      [-196, 30],
      [-196, 116],
      [196, 116],
      [196, 30],
    ]),
    { opacity: 0.42, smooth: false },
  );
  s.hatch(
    P([
      [-196, 30],
      [-196, 116],
      [196, 116],
      [196, 30],
    ]),
    { angle: 0.6, gap: 4.5, w: 0.8 },
  );
  s.hatch(
    P([
      [-196, 30],
      [-196, 116],
      [-60, 116],
      [-60, 30],
    ]),
    { angle: -0.7, gap: 5, w: 0.7 },
  );
  // Plinth with mouldings.
  for (const [y, w] of [
    [0, 2.2],
    [8, 1.2],
    [20, 1.4],
    [26, 2.0],
  ])
    s.stroke(
      P([
        [-198, y],
        [198, y],
      ]),
      { w, smooth: false, shake: 0.4 },
    );
  s.stroke(
    P([
      [-198, 0],
      [-198, 26],
    ]),
    { w: 2, smooth: false },
  );
  s.stroke(
    P([
      [198, 0],
      [198, 26],
    ]),
    { w: 2, smooth: false },
  );
  s.hatch(
    P([
      [-198, 8],
      [-198, 20],
      [198, 20],
      [198, 8],
    ]),
    { angle: 0.25, gap: 5, w: 0.7, shorten: 0.4 },
  );
  // Beam with a row of dentils, then the lower roof sloping out over it.
  for (const [y, w] of [
    [116, 1.8],
    [124, 1.0],
    [132, 1.6],
  ])
    s.stroke(
      P([
        [-200, y],
        [200, y],
      ]),
      { w, smooth: false },
    );
  for (let x = -196; x < 196; x += 8)
    s.stroke(
      P([
        [x, 124],
        [x, 131],
      ]),
      { w: 0.8, smooth: false, detail: true },
    );
  s.wash(
    P([
      [-200, 104],
      [-200, 124],
      [200, 124],
      [200, 104],
    ]),
    { opacity: 0.3, smooth: false },
  );
  const skirt = [
    [-226, 128],
    [-156, 180],
    [156, 180],
    [226, 128],
  ];
  s.stroke(
    P([
      [-228, 127],
      [228, 127],
    ]),
    { w: 2.4, smooth: false },
  );
  s.stroke(
    P([
      [-228, 127],
      [-156, 180],
    ]),
    { w: 1.9, smooth: false },
  );
  s.stroke(
    P([
      [228, 127],
      [156, 180],
    ]),
    { w: 1.9, smooth: false },
  );
  for (let x = -220; x < 220; x += 7) {
    const y1 = Math.abs(x) > 156 ? 128 + (226 - Math.abs(x)) * (52 / 70) : 179;
    s.stroke(
      P([
        [x, 129],
        [x + r(-1, 1), y1],
      ]),
      { w: 0.8, smooth: false, detail: true },
    );
  }
  s.wash(P(skirt), { opacity: 0.16, smooth: false });
  // Naga hooks at the corners of the lower roof.
  for (const side of [-1, 1]) {
    const hx = side * 228;
    s.stroke(
      P([
        [hx, 127],
        [hx + side * 12, 125],
        [hx + side * 20, 133],
        [hx + side * 19, 145],
        [hx + side * 12, 148],
        [hx + side * 9, 141],
      ]),
      { w: 1.6 },
    );
  }
  s.occlude(P(skirt));
  // Two gables: the porch's in front, the hall's rising behind it.
  gable(s, P, 140, 180, 352, { tympanum: true, w: 2.4 });
  gable(s, P, 172, 166, 414, { tiles: true, w: 2.2 });
  s.occlude(
    P([
      [-216, -2],
      [-216, 130],
      [216, 130],
      [216, -2],
    ]),
  );
}

/** A bell-shaped stupa (chedi) on stepped bases, with a ringed spire. */
function stupa(s, cx, yb, sc) {
  const P = (pts) => pts.map(([x, y]) => [cx + x * sc, yb - y * sc]);
  const tiers = [
    [78, 0, 30],
    [64, 30, 56],
    [52, 56, 78],
  ];
  // Spire and finial (front to back does not matter up here).
  s.stroke(
    P([
      [0, 360],
      [0, 402],
    ]),
    { w: 1.4, smooth: false },
  );
  s.stroke(P(ellipse(0, 374, 3.5, 5, 10)), { w: 1.2, detail: true });
  s.stroke(
    P([
      [-14, 214],
      [-9, 290],
      [-3, 360],
    ]),
    { w: 1.8 },
  );
  s.stroke(
    P([
      [14, 214],
      [9, 290],
      [3, 360],
    ]),
    { w: 1.6 },
  );
  for (let k = 0; k < 9; k++) {
    const y = 222 + k * 15;
    const w = 14 - (y - 214) * (11 / 146);
    s.stroke(
      P([
        [-w, y],
        [0, y - 2],
        [w, y],
      ]),
      { w: 1.0, detail: true },
    );
  }
  s.hatch(
    P([
      [-14, 214],
      [-3, 360],
      [-1, 360],
      [-5, 214],
    ]),
    { angle: Math.PI / 2, gap: 2.5, w: 0.7 },
  );
  // Harmika.
  s.stroke(
    P([
      [-18, 190],
      [-18, 214],
      [18, 214],
      [18, 190],
    ]),
    { w: 1.6, smooth: false },
  );
  s.stroke(
    P([
      [-20, 206],
      [20, 206],
    ]),
    { w: 1.0, smooth: false, detail: true },
  );
  // Bell.
  const bell = [
    [-46, 92],
    [-45, 120],
    [-37, 152],
    [-22, 178],
    [0, 190],
    [22, 178],
    [37, 152],
    [45, 120],
    [46, 92],
  ];
  s.stroke(P(bell.slice(0, 5)), { w: 2.2 });
  s.stroke(P(bell.slice(4)), { w: 1.8 });
  for (let k = 1; k < 7; k++) {
    const x = -44 + k * 4.2;
    const yTop = 92 + (190 - 92) * Math.sqrt(Math.max(0, 1 - (x / 46) ** 2)) - 6;
    s.stroke(
      P([
        [x, 94],
        [x + 1, (94 + yTop) / 2],
        [x + 3, yTop],
      ]),
      { w: 0.85, detail: true },
    );
  }
  s.wash(P(bell.slice(0, 6).concat([[-6, 92]])), { opacity: 0.24 });
  s.wash(P(bell), { opacity: 0.07 });
  // Lotus band of petals.
  s.stroke(
    P([
      [-48, 92],
      [48, 92],
    ]),
    { w: 1.4, smooth: false },
  );
  for (let x = -44; x < 44; x += 11)
    s.stroke(
      P([
        [x, 79],
        [x + 2, 88],
        [x + 5.5, 91],
        [x + 9, 88],
        [x + 11, 79],
      ]),
      { w: 0.9, detail: true },
    );
  // Stepped bases.
  for (const [hw, y0, y1] of tiers) {
    s.stroke(
      P([
        [-hw, y0],
        [-hw, y1],
        [hw, y1],
        [hw, y0],
      ]),
      { w: 1.8, smooth: false },
    );
    s.stroke(
      P([
        [-hw + 3, y1 - 5],
        [hw - 3, y1 - 5],
      ]),
      { w: 0.9, smooth: false, detail: true },
    );
    s.wash(
      P([
        [-hw, y1 - 6],
        [-hw, y1],
        [hw, y1],
        [hw, y1 - 6],
      ]),
      { opacity: 0.25, smooth: false },
    );
    s.hatch(
      P([
        [-hw, y0],
        [-hw, y1],
        [-hw + 16, y1],
        [-hw + 16, y0],
      ]),
      { angle: Math.PI / 2, gap: 3.2, w: 0.75 },
    );
  }
  s.stroke(
    P([
      [-9, 36],
      [-9, 48],
      [-5, 53],
      [0, 54],
      [5, 53],
      [9, 48],
      [9, 36],
    ]),
    { w: 1.1, detail: true },
  );
  s.wash(
    P([
      [-9, 36],
      [-9, 48],
      [0, 54],
      [9, 48],
      [9, 36],
    ]),
    { opacity: 0.4, smooth: false },
  );
  s.occlude(
    P([
      [-80, -2],
      [-80, 80],
      [-48, 92],
      [-46, 120],
      [-30, 168],
      [0, 192],
      [30, 168],
      [46, 120],
      [48, 92],
      [80, 80],
      [80, -2],
    ]),
  );
}

/** The naga balustrade's end: the body rears up into a seven-headed hood. */
function nagaHood(s, ox, oy, k = 1) {
  // Drawn at k = 1 around (0, 0), scaled to k and moved to (ox, oy).
  const at = (pts) => pts.map(([px, py]) => [ox + px * k, oy + py * k]);
  const x = 0;
  const y = 0;
  // Pedestal.
  s.stroke(
    at([
      [x - 26, y + 40],
      [x - 26, y + 6],
      [x + 26, y + 6],
      [x + 26, y + 40],
    ]),
    { w: 2.0, smooth: false },
  );
  s.stroke(
    at([
      [x - 30, y + 6],
      [x + 30, y + 6],
    ]),
    { w: 1.6, smooth: false },
  );
  s.hatch(
    at([
      [x - 26, y + 8],
      [x - 26, y + 40],
      [x - 12, y + 40],
      [x - 12, y + 8],
    ]),
    { angle: Math.PI / 2, gap: 3.5, w: 0.8 },
  );
  // Neck rising from the pedestal.
  s.stroke(
    at([
      [x - 9, y + 6],
      [x - 10, y - 20],
      [x - 6, y - 44],
    ]),
    { w: 2.0 },
  );
  s.stroke(
    at([
      [x + 9, y + 6],
      [x + 10, y - 20],
      [x + 6, y - 44],
    ]),
    { w: 1.8 },
  );
  for (let i = 0; i < 5; i++)
    s.stroke(
      at([
        [x - 8, y - i * 9],
        [x, y - i * 9 - 3],
        [x + 8, y - i * 9],
      ]),
      { w: 0.8, detail: true },
    );
  // Hood: seven heads on an arc.
  const hc = [x, y - 52];
  const heads = [];
  for (let i = 0; i < 7; i++) {
    const a = -Math.PI + 0.35 + (i / 6) * (Math.PI - 0.7);
    const hx = hc[0] + Math.cos(a) * 34;
    const hy = hc[1] + Math.sin(a) * 30;
    heads.push([hx + Math.cos(a) * 9, hy + Math.sin(a) * 9]);
    s.stroke(
      at([
        [hx - Math.sin(a) * 6, hy + Math.cos(a) * 6],
        [hx + Math.cos(a) * 12 - Math.sin(a) * 3, hy + Math.sin(a) * 12 + Math.cos(a) * 3],
        [hx + Math.cos(a) * 14, hy + Math.sin(a) * 14],
        [hx + Math.cos(a) * 12 + Math.sin(a) * 3, hy + Math.sin(a) * 12 - Math.cos(a) * 3],
        [hx + Math.sin(a) * 6, hy - Math.cos(a) * 6],
      ]),
      { w: 1.4 },
    );
    s.stroke(at(ellipse(hx + Math.cos(a) * 7, hy + Math.sin(a) * 7, 1.6, 1.6, 6)), {
      w: 1.6,
      detail: true,
    });
  }
  s.stroke(
    at([
      [x - 30, y - 40],
      [x - 18, y - 58],
      [x, y - 64],
      [x + 18, y - 58],
      [x + 30, y - 40],
    ]),
    { w: 1.2, detail: true },
  );
  for (let i = 0; i < 5; i++) {
    const a = -Math.PI + 0.6 + (i / 4) * (Math.PI - 1.2);
    s.stroke(
      at([
        [hc[0], hc[1] + 6],
        [hc[0] + Math.cos(a) * 24, hc[1] + Math.sin(a) * 22],
      ]),
      { w: 0.8, detail: true },
    );
  }
  s.wash(at([[x - 26, y + 40], [x - 34, y - 52], ...heads, [x + 34, y - 52], [x + 26, y + 40]]), {
    opacity: 0.16,
  });
  s.occlude(at([[x - 30, y + 42], [x - 44, y - 50], ...heads, [x + 44, y - 50], [x + 30, y + 42]]));
}

/** The great naga staircase climbing the hill to the vihara. */
function staircase(s, cx, top, bottom, wTop, wBottom) {
  nagaHood(s, cx - wBottom - 34, bottom - 40, 1.4);
  nagaHood(s, cx + wBottom + 34, bottom - 40, 1.4);
  const edge = (side, t) => [cx + side * lerp(wTop, wBottom, t), lerp(top, bottom, t)];
  // Naga bodies along both sides, scales on the inked side.
  for (const side of [-1, 1]) {
    const outer = Array.from({ length: 9 }, (_, k) => {
      const [x, y] = edge(side, k / 8);
      return [x + side * 14, y - 4];
    });
    const inner = Array.from({ length: 9 }, (_, k) => edge(side, k / 8));
    s.stroke(outer, { w: 2.0 });
    s.stroke(inner, { w: 1.6 });
    for (let k = 1; k < 26; k++) {
      const [x, y] = edge(side, k / 26);
      s.stroke(
        [
          [x + side * 2, y - 2],
          [x + side * 7, y - 6],
          [x + side * 12, y - 3],
        ],
        { w: 0.75, detail: true },
      );
    }
    s.wash([...outer, ...inner.slice().reverse()], { opacity: 0.18, smooth: false });
    // Bend down from the bottom of the rail into the rearing neck.
    const [bx, by] = edge(side, 1);
    s.stroke(
      [
        [bx, by],
        [bx + side * 10, by + 10],
        [bx + side * 22, by],
      ],
      { w: 1.6 },
    );
  }
  // Steps: risers closer together towards the top.
  for (let k = 0; k <= 26; k++) {
    const t = (k / 26) ** 1.35;
    const [x0, y] = edge(-1, t);
    const [x1] = edge(1, t);
    s.stroke(
      [
        [x0, y],
        [x1, y],
      ],
      { w: 1.1 + t * 0.8, smooth: false, shake: 0.3, detail: k % 4 !== 0 },
    );
    if (k < 26) {
      const y2 = edge(-1, ((k + 1) / 26) ** 1.35)[1];
      s.hatch(
        [
          [x0, y],
          [x0, lerp(y, y2, 0.45)],
          [x1, lerp(y, y2, 0.45)],
          [x1, y],
        ],
        { angle: 0.15, gap: 4.5, w: 0.6, shorten: 0.3 },
      );
    }
  }
  const poly = [edge(-1, 0), edge(-1, 1), edge(1, 1), edge(1, 0)];
  s.wash(poly, { opacity: 0.06, smooth: false });
  s.occlude([
    [cx - wTop - 16, top - 6],
    [cx - wBottom - 16, bottom + 2],
    [cx + wBottom + 16, bottom + 2],
    [cx + wTop + 16, top - 6],
  ]);
}

/** A monk climbing away from us under a parasol. */
function monk(s, ox, oy, k = 1) {
  const at = (pts) => pts.map(([px, py]) => [ox + px * k, oy + py * k]);
  const x = 0;
  const y = 0;
  s.stroke(
    at([
      [x - 4, y + 52],
      [x - 5, y + 60],
    ]),
    { w: 1.6, detail: true },
  );
  s.stroke(
    at([
      [x + 5, y + 52],
      [x + 6, y + 59],
    ]),
    { w: 1.6, detail: true },
  );
  const robe = [
    [x - 10, y + 10],
    [x - 14, y + 32],
    [x - 15, y + 53],
    [x + 14, y + 54],
    [x + 13, y + 30],
    [x + 9, y + 9],
  ];
  s.stroke(at(robe), { w: 1.8 });
  s.stroke(
    at([
      [x - 9, y + 12],
      [x + 2, y + 30],
      [x + 12, y + 50],
    ]),
    { w: 1.0, detail: true },
  );
  s.stroke(
    at([
      [x - 12, y + 30],
      [x - 6, y + 44],
      [x - 2, y + 53],
    ]),
    { w: 0.9, detail: true },
  );
  s.wash(at(robe), { opacity: 0.36 });
  s.stroke(at(ellipse(x, y + 2, 7, 8, 16)), { w: 1.6 });
  s.wash(at(ellipse(x, y + 2, 7, 8, 10)), { opacity: 0.1 });
  // Parasol over the right shoulder.
  s.stroke(
    at([
      [x + 6, y + 20],
      [x + 14, y - 8],
      [x + 20, y - 26],
    ]),
    { w: 1.2 },
  );
  const top = [x + 22, y - 30];
  s.stroke(
    at([
      [top[0] - 32, top[1] + 10],
      [top[0] - 14, top[1] - 4],
      [top[0], top[1] - 8],
      [top[0] + 16, top[1] - 3],
      [top[0] + 32, top[1] + 10],
    ]),
    { w: 1.7 },
  );
  s.stroke(
    at([
      [top[0] - 32, top[1] + 10],
      [top[0] - 16, top[1] + 7],
      [top[0], top[1] + 9],
      [top[0] + 16, top[1] + 7],
      [top[0] + 32, top[1] + 10],
    ]),
    { w: 1.2 },
  );
  for (const rib of [-24, -10, 6, 20])
    s.stroke(
      at([
        [top[0], top[1] - 8],
        [top[0] + rib, top[1] + 8],
      ]),
      { w: 0.8, detail: true },
    );
  s.wash(
    at([
      [top[0] - 32, top[1] + 10],
      [top[0], top[1] - 8],
      [top[0] + 32, top[1] + 10],
    ]),
    { opacity: 0.2 },
  );
  s.occlude(
    at([
      [x - 16, y + 60],
      [x - 16, y - 8],
      [top[0] - 32, top[1] + 12],
      [top[0] + 32, top[1] + 12],
      [x + 16, y + 60],
    ]),
  );
}

/** A woman resting by her shoulder-pole baskets in the palms' shade. */
function vendor(s, x, y) {
  const r = s.r;
  for (const bx of [x + 40, x + 92]) {
    s.stroke(ellipse(bx, y - 22, 21, 6, 20), { w: 1.4 });
    const body = [
      [bx - 21, y - 22],
      [bx - 19, y - 6],
      [bx - 12, y + 2],
      [bx + 12, y + 2],
      [bx + 19, y - 6],
      [bx + 21, y - 22],
    ];
    s.stroke(body, { w: 1.7 });
    for (let k = -16; k <= 16; k += 5)
      s.stroke(
        [
          [bx + k, y - 18],
          [bx + k * 0.8, y],
        ],
        { w: 0.7, detail: true },
      );
    for (let k = 0; k < 3; k++)
      s.stroke(
        [
          [bx - 19, y - 14 + k * 5],
          [bx, y - 12 + k * 5],
          [bx + 19, y - 14 + k * 5],
        ],
        { w: 0.6, detail: true },
      );
    s.wash(body, { opacity: 0.2 });
    // Fruit heaped in the basket.
    for (let k = 0; k < 4; k++)
      s.stroke(ellipse(bx - 10 + k * 7, y - 27 + r(-2, 2), 4.5, 4, 10), { w: 1.0, detail: true });
    s.occlude([...body, [bx + 22, y - 30], [bx - 22, y - 30]]);
  }
  s.stroke(
    [
      [x + 10, y - 40],
      [x + 70, y - 34],
      [x + 130, y - 30],
    ],
    { w: 1.6 },
  );
  // Seated figure, knees up, krama over the head.
  const fig = [
    [x - 18, y + 2],
    [x - 20, y - 18],
    [x - 14, y - 36],
    [x - 8, y - 52],
    [x + 2, y - 60],
    [x + 12, y - 54],
    [x + 14, y - 40],
    [x + 20, y - 26],
    [x + 26, y - 14],
    [x + 22, y + 2],
  ];
  s.stroke(fig, { w: 1.8 });
  s.stroke(
    [
      [x - 8, y - 52],
      [x - 2, y - 44],
      [x + 10, y - 42],
    ],
    { w: 1.1, detail: true },
  );
  s.stroke(
    [
      [x + 2, y - 30],
      [x + 18, y - 22],
      [x + 24, y - 10],
    ],
    { w: 1.0, detail: true },
  );
  s.wash(fig, { opacity: 0.28 });
  s.occlude(fig);
}

/** A few blades of grass. */
function tuft(s, x, y, size = 1) {
  const r = s.r;
  for (let k = 0; k < 4; k++) {
    const lean = r(-9, 9) * size;
    const h = r(8, 16) * size;
    s.stroke(
      [
        [x + k * 3 * size - 4, y],
        [x + k * 3 * size + lean * 0.4 - 4, y - h * 0.6],
        [x + k * 3 * size + lean - 4, y - h],
      ],
      { w: 0.9, detail: true, taper: 0.5 },
    );
  }
}

function bird(s, x, y, size = 1) {
  s.stroke(
    [
      [x - 9 * size, y - 2 * size],
      [x - 4 * size, y - 4 * size],
      [x, y],
    ],
    { w: 1.1, detail: true },
  );
  s.stroke(
    [
      [x, y],
      [x + 4 * size, y - 5 * size],
      [x + 10 * size, y - 3 * size],
    ],
    { w: 1.1, detail: true },
  );
}

/** A scroll of Khmer ornament either side of a title: a swelling stem, leaf flames, a curl. */
function flourish(s, x, y, dir, { color, k = 1 } = {}) {
  const Q = (dx, dy) => [x + dir * dx * k, y + dy * k];
  const o = { ink: true, color };
  s.stroke([Q(0, 0), Q(30, -6), Q(70, 2), Q(115, -4), Q(150, -16), Q(160, -30)], {
    ...o,
    w: 3.4 * k,
    taper: 0.3,
  });
  const curl = Array.from({ length: 16 }, (_, i) => {
    const a = Math.PI * 0.5 - (i / 15) * Math.PI * 1.9;
    const rr = 13 * (1 - (i / 15) * 0.7);
    return Q(148 + Math.cos(a) * rr, -32 - Math.sin(a) * rr);
  });
  s.stroke(curl, { ...o, w: 2.2 * k, taper: 0.4 });
  for (const [bx, by, up] of [
    [38, -5, -1],
    [64, 1, 1],
    [92, -1, -1],
    [118, -6, 1],
  ]) {
    const tip = Q(bx + 22, by + up * 20);
    s.stroke([Q(bx, by), Q(bx + 6, by + up * 12), tip], { ...o, w: 1.9 * k, taper: 0.5 });
    s.stroke([Q(bx + 4, by), Q(bx + 14, by + up * 6), tip], { ...o, w: 1.2 * k, taper: 0.5 });
  }
  s.stroke([Q(-8, 0), Q(-18, 3)], { ...o, w: 2.4 * k, taper: 0.5 });
}

function tape(s, x, y, angle, len, wide) {
  s.top(
    `<g transform="translate(${x} ${y}) rotate(${angle})"><rect x="${-len / 2}" y="${-wide / 2}" width="${len}" height="${wide}" fill="#efe2bb" fill-opacity="0.82" stroke="#8c7748" stroke-opacity="0.25" stroke-width="1.5"/><line x1="${-len / 2 + 8}" y1="${-wide / 4}" x2="${len / 2 - 20}" y2="${-wide / 5}" stroke="#fff8df" stroke-opacity="0.5" stroke-width="3"/></g>`,
  );
}

/** A wooden house on stilts, gable end towards us, its long side receding right. */
function stiltHouse(
  s,
  x,
  base,
  { w = 150, depth = 120, stilt = 110, wallH = 64, roofH = 92, ladder = true } = {},
) {
  const r = s.r;
  const v = [depth, -depth * 0.22];
  const x0 = x - w / 2;
  const x1 = x + w / 2;
  const floor = base - stilt;
  const wallTop = floor - wallH;
  const apex = [x, wallTop - roofH];
  const eave = 16;
  const add = (p, k = 1) => [p[0] + v[0] * k, p[1] + v[1] * k];
  // Ladder up to the door, in front of everything.
  if (ladder) {
    const lx = x0 + w * 0.3;
    s.stroke(
      [
        [lx - 30, base + 4],
        [lx - 6, floor],
      ],
      { w: 1.6, smooth: false },
    );
    s.stroke(
      [
        [lx - 8, base + 4],
        [lx + 16, floor],
      ],
      { w: 1.6, smooth: false },
    );
    for (let k = 1; k < 7; k++) {
      const t = k / 7;
      s.stroke(
        [
          [lerp(lx - 30, lx - 6, t), lerp(base + 4, floor, t)],
          [lerp(lx - 8, lx + 16, t), lerp(base + 4, floor, t)],
        ],
        { w: 1.1, smooth: false, detail: true },
      );
    }
    s.occlude([
      [lx - 32, base + 6],
      [lx - 8, floor - 2],
      [lx + 18, floor - 2],
      [lx - 6, base + 6],
    ]);
  }
  // Roof: gable end with the thatch's side plane behind.
  const gable = [[x0 - eave, wallTop + 8], apex, [x1 + eave, wallTop + 8]];
  s.stroke(gable, { w: 2.2, smooth: false });
  s.stroke(
    [
      [x0 - eave + 6, wallTop + 4],
      [x - 2, apex[1] + 10],
      [x1 + eave - 6, wallTop + 4],
    ],
    { w: 1.0, smooth: false, detail: true },
  );
  for (let k = -3; k <= 3; k++)
    s.stroke(
      [
        [x + k * (w / 9), wallTop + 2],
        [x + k * (w / 9) * 0.92, wallTop - roofH * (1 - Math.abs(k) / 4.2) + 10],
      ],
      { w: 0.8, smooth: false, detail: true },
    );
  s.wash(gable, { opacity: 0.08, smooth: false });
  const roofSide = [apex, add(apex), add([x1 + eave, wallTop + 8]), [x1 + eave, wallTop + 8]];
  s.occlude([...gable, gable[0]]);
  s.stroke([apex, add(apex)], { w: 2.0, smooth: false });
  s.stroke([[x1 + eave, wallTop + 8], add([x1 + eave, wallTop + 8])], { w: 2.2, smooth: false });
  for (let k = 0.04; k < 1; k += 0.035) {
    const a = [lerp(apex[0], apex[0] + v[0], k), lerp(apex[1], apex[1] + v[1], k)];
    const b = [
      lerp(x1 + eave, x1 + eave + v[0], k + r(-0.01, 0.01)),
      lerp(wallTop + 8, wallTop + 8 + v[1], k) + r(0, 4),
    ];
    s.stroke([a, [lerp(a[0], b[0], 0.5) + r(-2, 2), lerp(a[1], b[1], 0.5)], b], {
      w: 0.85,
      detail: true,
      taper: 0.5,
    });
  }
  s.wash(roofSide, { opacity: 0.16, smooth: false });
  s.occlude(roofSide);
  // Walls: planks on the gable end, woven bamboo along the side.
  s.stroke(
    [
      [x0, wallTop + 8],
      [x0, floor],
      [x1, floor],
      [x1, wallTop + 8],
    ],
    { w: 2.0, smooth: false },
  );
  for (let px = x0 + 9; px < x1; px += 9)
    s.stroke(
      [
        [px, wallTop + 9],
        [px + r(-1, 1), floor - 1],
      ],
      { w: 0.75, smooth: false, detail: true },
    );
  const win = [
    [x + 4, wallTop + 22],
    [x + 4, floor - 18],
    [x + w * 0.36, floor - 18],
    [x + w * 0.36, wallTop + 22],
  ];
  s.stroke([...win, win[0]], { w: 1.5, smooth: false });
  s.wash(win, { opacity: 0.6, smooth: false });
  s.hatch(win, { angle: 0.9, gap: 3.5, w: 0.8 });
  const side = [[x1, floor], [x1, wallTop + 8], add([x1, wallTop + 8]), add([x1, floor])];
  s.stroke([[x1, floor], add([x1, floor])], { w: 2.0, smooth: false });
  s.stroke([add([x1, floor]), add([x1, wallTop + 8])], { w: 1.6, smooth: false });
  s.hatch(side, { angle: 0.7, gap: 6, w: 0.7, shorten: 0.02 });
  s.hatch(side, { angle: -0.5, gap: 6, w: 0.6, shorten: 0.02 });
  const door = [
    add([x1, floor], 0.55),
    add([x1, wallTop + 18], 0.55),
    add([x1, wallTop + 18], 0.75),
    add([x1, floor], 0.75),
  ];
  s.stroke(door, { w: 1.3, smooth: false });
  s.wash(door, { opacity: 0.55, smooth: false });
  s.wash(side, { opacity: 0.22, smooth: false });
  // Floor beams and stilts with cross-bracing.
  s.stroke([[x0 - 8, floor + 4], [x1 + 4, floor + 4], add([x1 + 4, floor + 4])], {
    w: 1.8,
    smooth: false,
  });
  const posts = [
    [x0 + 4, floor + 4],
    [x, floor + 4],
    [x1 - 4, floor + 4],
    add([x1 - 4, floor + 4], 0.5),
    add([x1 - 4, floor + 4], 1),
  ];
  for (const [px, py] of posts) {
    const bottom = base + (px > x1 ? -(px - x1) * 0.22 : 0);
    s.stroke(
      [
        [px - 3, py],
        [px - 3 + r(-2, 2), bottom],
      ],
      { w: 1.7, smooth: false },
    );
    s.stroke(
      [
        [px + 3, py],
        [px + 3 + r(-2, 2), bottom],
      ],
      { w: 1.3, smooth: false },
    );
  }
  s.stroke(
    [
      [x0 + 4, floor + 10],
      [x, base - 6],
    ],
    { w: 1.0, smooth: false, detail: true },
  );
  s.stroke(
    [
      [x, floor + 10],
      [x1 - 4, base - 6],
    ],
    { w: 1.0, smooth: false, detail: true },
  );
  s.wash([[x0, floor + 4], [x1, floor + 4], add([x1, floor + 4]), add([x1, base]), [x0, base]], {
    opacity: 0.3,
    smooth: false,
  });
  // A water jar by the posts.
  const jx = x1 + 20;
  s.stroke(
    [
      [jx - 10, base - 22],
      [jx - 16, base - 12],
      [jx - 13, base],
      [jx + 13, base],
      [jx + 16, base - 12],
      [jx + 10, base - 22],
    ],
    { w: 1.5 },
  );
  s.stroke(ellipse(jx, base - 22, 10, 3, 12), { w: 1.2, detail: true });
  s.wash(
    [
      [jx - 16, base - 12],
      [jx - 13, base],
      [jx + 2, base],
      [jx, base - 22],
    ],
    { opacity: 0.35 },
  );
  s.occlude([
    [x0 - eave - 2, wallTop + 10],
    apex,
    add(apex),
    add([x1 + eave, wallTop + 8]),
    add([x1, base]),
    [x0, base + 4],
  ]);
}

/** A long river canoe; a rower standing at the stern with a pole. */
function boat(s, x, y, len, { rower = true, k = 1 } = {}) {
  const h = len / 2;
  if (rower) {
    const rx = x + h * 0.55;
    const ry = y - 8 * k;
    s.stroke(
      [
        [rx + 40 * k, ry - 92 * k],
        [rx - 50 * k, ry + 40 * k],
      ],
      { w: 1.4 * k, smooth: false },
    );
    s.stroke(
      [
        [rx - 4 * k, ry],
        [rx - 2 * k, ry - 22 * k],
      ],
      { w: 1.4 * k, smooth: false, detail: true },
    );
    s.stroke(
      [
        [rx + 5 * k, ry],
        [rx + 4 * k, ry - 22 * k],
      ],
      { w: 1.4 * k, smooth: false, detail: true },
    );
    const body = [
      [rx - 7 * k, ry - 22 * k],
      [rx - 9 * k, ry - 46 * k],
      [rx, ry - 52 * k],
      [rx + 9 * k, ry - 46 * k],
      [rx + 7 * k, ry - 22 * k],
    ];
    s.stroke(body, { w: 1.6 * k });
    s.wash(body, { opacity: 0.3 });
    s.stroke(
      [
        [rx - 6 * k, ry - 42 * k],
        [rx + 16 * k, ry - 54 * k],
        [rx + 26 * k, ry - 60 * k],
      ],
      { w: 1.4 * k },
    );
    s.stroke(ellipse(rx, ry - 58 * k, 5 * k, 6 * k, 10), { w: 1.3 * k });
    s.stroke(
      [
        [rx - 18 * k, ry - 60 * k],
        [rx, ry - 70 * k],
        [rx + 18 * k, ry - 60 * k],
        [rx - 18 * k, ry - 60 * k],
      ],
      { w: 1.5 * k, smooth: false },
    );
    s.wash(
      [
        [rx - 18 * k, ry - 60 * k],
        [rx, ry - 70 * k],
        [rx + 18 * k, ry - 60 * k],
      ],
      { opacity: 0.25, smooth: false },
    );
  }
  const top = [
    [x - h, y - 18 * k],
    [x - h * 0.6, y - 5 * k],
    [x + h * 0.6, y - 5 * k],
    [x + h, y - 20 * k],
  ];
  const hull = [...top, [x + h * 0.7, y + 4 * k], [x - h * 0.7, y + 4 * k]];
  s.stroke(top, { w: 2.0 * k });
  s.stroke(
    [
      [x - h, y - 18 * k],
      [x - h * 0.7, y + 4 * k],
      [x + h * 0.7, y + 4 * k],
      [x + h, y - 20 * k],
    ],
    { w: 2.2 * k },
  );
  s.stroke(
    [
      [x - h * 0.8, y - 9 * k],
      [x, y - 2 * k],
      [x + h * 0.8, y - 10 * k],
    ],
    { w: 0.8 * k, detail: true },
  );
  s.wash(hull, { opacity: 0.4 });
  s.occlude(hull);
  // Its reflection, broken by the ripples.
  for (let j = 0; j < 6; j++) {
    const yy = y + (10 + j * 6) * k;
    const ww = h * (0.75 - j * 0.1);
    s.stroke(
      [
        [x - ww + s.r(-8, 8), yy],
        [x + ww * s.r(0.3, 0.9), yy],
      ],
      { w: 1.0 * k, smooth: false, detail: true, taper: 0.5 },
    );
  }
}

/** Ripples: broken horizontal strokes, closer together towards the far bank. */
function water(s, x0, x1, y0, y1, { density = 1 } = {}) {
  const r = s.r;
  for (let y = y0 + 4; y < y1; y += lerp(5, 16, (y - y0) / (y1 - y0)) / density) {
    for (let x = x0 + r(0, 60); x < x1; x += r(60, 160)) {
      const len = r(14, 60) * lerp(0.6, 1.4, (y - y0) / (y1 - y0));
      if (r.chance(0.35)) continue;
      s.stroke(
        [
          [x, y],
          [x + len * 0.5, y + r(-0.6, 0.6)],
          [x + len, y],
        ],
        { w: lerp(0.7, 1.2, (y - y0) / (y1 - y0)), detail: true, taper: 0.5 },
      );
    }
  }
}

/** An Angkor tower (prasat): a lotus-bud spire of stacked tiers over its shrine. */
function prasat(s, x, base, top, bw) {
  // Swelling a little above the shrine, then curving in to the tip like a lotus bud.
  const half = (t) =>
    (bw / 2) *
    Math.sqrt(Math.max(0, 1 - t ** 1.8)) *
    (1 + 0.16 * Math.sin(t * Math.PI)) *
    (1 + 0.04 * Math.sin(t * Math.PI * 10));
  const H = base - top;
  const left = Array.from({ length: 21 }, (_, k) => [x - half(k / 20), base - (H * k) / 20]);
  const right = left.map(([px, py]) => [2 * x - px, py]);
  s.stroke(left, { w: 1.9 });
  s.stroke(right, { w: 1.6 });
  for (let k = 1; k < 10; k++) {
    const t = k / 10;
    const y = base - H * t;
    s.stroke(
      [
        [x - half(t), y],
        [x, y + 3],
        [x + half(t), y],
      ],
      { w: 0.9, detail: true },
    );
  }
  s.stroke(
    [
      [x, top],
      [x, top - 14],
    ],
    { w: 1.2, smooth: false },
  );
  s.hatch([...left, ...left.map(([px, py]) => [x - (x - px) * 0.35, py]).reverse()], {
    angle: Math.PI / 2,
    gap: 3,
    w: 0.75,
  });
  s.wash([...left, [x, top], [x - 2, base]], { opacity: 0.2, smooth: false });
  // The shrine under the spire, with its dark doorway.
  const sb = base + bw * 0.45;
  s.stroke(
    [
      [x - bw * 0.55, sb],
      [x - bw * 0.55, base],
      [x + bw * 0.55, base],
      [x + bw * 0.55, sb],
    ],
    { w: 1.6, smooth: false },
  );
  const door = [
    [x - bw * 0.12, sb],
    [x - bw * 0.12, base + bw * 0.12],
    [x + bw * 0.12, base + bw * 0.12],
    [x + bw * 0.12, sb],
  ];
  s.stroke(door, { w: 1.2, smooth: false });
  s.wash(door, { opacity: 0.6, smooth: false });
  s.occlude([
    ...left,
    ...right.slice().reverse(),
    [x + bw * 0.55, base],
    [x + bw * 0.55, sb],
    [x - bw * 0.55, sb],
    [x - bw * 0.55, base],
  ]);
}

/** A long gallery: a tiled roof over a colonnade, on a terrace. */
function gallery(s, x0, x1, y, h = 34) {
  const roof = [
    [x0, y],
    [x0 + 14, y - h * 0.55],
    [x1 - 14, y - h * 0.55],
    [x1, y],
  ];
  s.stroke([...roof, roof[0]], { w: 1.8, smooth: false });
  for (let x = x0 + 8; x < x1 - 4; x += 6)
    s.stroke(
      [
        [x, y - 1],
        [x + (x < (x0 + x1) / 2 ? 1 : -1), y - h * 0.5],
      ],
      { w: 0.7, smooth: false, detail: true },
    );
  s.wash(roof, { opacity: 0.14, smooth: false });
  const wall = [
    [x0 + 4, y],
    [x0 + 4, y + h * 0.6],
    [x1 - 4, y + h * 0.6],
    [x1 - 4, y],
  ];
  s.stroke(
    [
      [x0 + 4, y + h * 0.6],
      [x1 - 4, y + h * 0.6],
    ],
    { w: 1.6, smooth: false },
  );
  for (let x = x0 + 12; x < x1 - 8; x += 13)
    s.stroke(
      [
        [x, y + 2],
        [x, y + h * 0.6 - 1],
      ],
      { w: 1.0, smooth: false, detail: true },
    );
  s.wash(wall, { opacity: 0.38, smooth: false });
  s.occlude([[x0, y + h * 0.6], ...roof]);
}

/** A lotus bud: pointed, petals overlapping. */
function lotusBud(s, x, y, size = 1) {
  const S = (dx, dy) => [x + dx * size, y + dy * size];
  s.stroke([S(0, 0), S(-16, -20), S(-10, -44), S(0, -58)], { w: 1.8 });
  s.stroke([S(0, 0), S(16, -20), S(10, -44), S(0, -58)], { w: 1.6 });
  s.stroke([S(-14, -12), S(-4, -30), S(0, -50)], { w: 1.0, detail: true });
  s.stroke([S(14, -12), S(4, -30), S(0, -50)], { w: 1.0, detail: true });
  s.stroke([S(0, 0), S(2, 30), S(-2, 70)], { w: 1.6 });
  s.wash([S(0, 0), S(-16, -20), S(-10, -44), S(0, -58), S(-3, -30)], { opacity: 0.2 });
}

// --------------------------------------------------------------- drawings

const rect = (x0, y0, x1, y1) => [
  [x0, y0],
  [x1, y0],
  [x1, y1],
  [x0, y1],
  [x0, y0],
];

/** Keeps a picture inside its ruled frame. */
function frame(s, x0, y0, x1, y1) {
  const { width: W, height: H } = s;
  s.occlude([
    [0, 0],
    [W, 0],
    [W, y0],
    [0, y0],
  ]);
  s.occlude([
    [0, y1],
    [W, y1],
    [W, H],
    [0, H],
  ]);
  s.occlude([
    [0, 0],
    [x0, 0],
    [x0, H],
    [0, H],
  ]);
  s.occlude([
    [x1, 0],
    [W, 0],
    [W, H],
    [x1, H],
  ]);
}

/**
 * P02: the plate Sora is inking tonight, Wat Phnom for a Phnom Penh printer.
 * Inked and washed up to the middle; the right half is still pencil.
 */
function illustration() {
  const s = new Sheet({ width: 2000, height: 1400, seed: 1932 });
  const edge = (y) => 1004 + 36 * Math.sin(y / 70);
  s.inked = (x, y) => x < edge(y);
  s.inkedArea = [
    [0, 0],
    ...Array.from({ length: 141 }, (_, k) => [edge(k * 10), k * 10]),
    [0, 1400],
  ];
  const ground = 985;

  // Plate border, ruled first.
  for (const [x0, y0, x1, y1, w] of [
    [118, 98, 1882, 1292, 3.2],
    [134, 114, 1866, 1276, 1.3],
  ])
    s.stroke(
      [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
        [x0, y0],
      ],
      { w, smooth: false, ruled: true, ink: true },
    );
  s.stroke(
    [
      [134, 1150],
      [1866, 1150],
    ],
    { w: 1.3, smooth: false, ruled: true, ink: true },
  );
  s.text(KHMER.watPhnom[0], 1000, 1232, { font: "Preahvihear", size: 78, ink: true, spacing: 4 });
  flourish(s, 830, 1212, -1);
  flourish(s, 1170, 1212, 1);
  s.text(KHMER.byline[0], 190, 1250, {
    font: "Freehand",
    size: 30,
    anchor: "start",
    ink: false,
    opacity: 0.45,
  });
  s.text(`${KHMER.phnomPenh[0]} ${KHMER.year[0]}`, 1810, 1250, {
    font: "Freehand",
    size: 30,
    anchor: "end",
  });
  // Pen tests in the margin, a tea ring, drafting tape at the corners.
  for (const [x, y] of [
    [1700, 1330],
    [1760, 1340],
    [1820, 1325],
  ])
    s.stroke(
      [
        [x, y],
        [x + 12, y - 8],
        [x + 24, y + 4],
        [x + 36, y - 6],
      ],
      { w: 1.6, ink: true },
    );
  s.top(
    `<circle cx="1855" cy="1352" r="5" fill="#211b16" opacity="0.85"/><circle cx="1866" cy="1345" r="2" fill="#211b16" opacity="0.8"/>`,
  );
  s.top(
    `<circle cx="260" cy="1360" r="62" fill="none" stroke="#7a5326" stroke-width="7" opacity="0.1"/>`,
  );
  tape(s, 40, 40, -45, 170, 50);
  tape(s, 1960, 40, 45, 170, 50);
  tape(s, 40, 1360, 45, 170, 50);
  tape(s, 1960, 1360, -45, 170, 50);
  // Everything in the picture stays inside the inner rule.
  s.occlude([
    [0, 0],
    [2000, 0],
    [2000, 114],
    [0, 114],
  ]);
  s.occlude([
    [0, 1150],
    [2000, 1150],
    [2000, 1400],
    [0, 1400],
  ]);
  s.occlude([
    [0, 0],
    [134, 0],
    [134, 1400],
    [0, 1400],
  ]);
  s.occlude([
    [1866, 0],
    [2000, 0],
    [2000, 1400],
    [1866, 1400],
  ]);

  // Pencil construction: horizon, centre line, the vihara's blocking-in.
  s.guide(
    [
      [150, ground],
      [1850, ground],
    ],
    { opacity: 0.22, smooth: false },
  );
  s.guide(
    [
      [1000, 160],
      [1000, 1140],
    ],
    { opacity: 0.18, smooth: false },
  );
  s.guide(
    [
      [1560, 1140],
      [1000, 610],
      [440, 1140],
    ],
    { opacity: 0.12, smooth: false },
  );

  // Foreground, front to back.
  palm(s, 296, 1146, 800, { lean: 14, size: 1.2, fans: 28 });
  palm(s, 458, 1112, 610, { lean: -10, size: 1.0, fans: 24 });
  palm(s, 1690, 1140, 760, { lean: -16, size: 1.15 });
  vendor(s, 560, 1112);
  s.stroke(
    [
      [920, 996],
      [870, 1040],
      [800, 1096],
      [730, 1150],
    ],
    { w: 2.0 },
  );
  s.stroke(
    [
      [1080, 996],
      [1130, 1040],
      [1200, 1096],
      [1270, 1150],
    ],
    { w: 2.0 },
  );
  for (const [x, y, k] of [
    [250, 1140, 1.2],
    [380, 1128, 1],
    [640, 1090, 1],
    [700, 1140, 1.2],
    [860, 1060, 0.9],
    [895, 1012, 0.8],
    [1110, 1014, 0.8],
    [1180, 1080, 1],
    [1330, 1120, 1.1],
    [1480, 1100, 1],
    [1600, 1135, 1.2],
    [760, 1030, 0.9],
    [520, 1060, 0.9],
    [180, 1100, 1],
  ])
    tuft(s, x, y, k);
  s.wash(
    [
      [134, 1150],
      [160, 1110],
      [420, 1100],
      [700, 1104],
      [915, 998],
      [870, 1050],
      [760, 1150],
    ],
    { opacity: 0.1 },
  );
  s.wash(
    [
      [200, 1148],
      [330, 1130],
      [520, 1126],
      [690, 1140],
      [620, 1150],
    ],
    { opacity: 0.26 },
  );
  monk(s, 962, 724, 1.35);
  staircase(s, 1000, 612, ground, 40, 112);

  // Trees on the hill, front belt first.
  // Low bushes along the foot of the hill hide where the trunks meet the ground.
  for (let x = 150; x < 1860; x += s.r(45, 80))
    if (Math.abs(x - 1000) > 150)
      clump(s, x, ground + s.r(-4, 8), s.r(24, 40), s.r(14, 22), { shade: 0.22 });
  grove(s, 140, 860, ground + 10, { count: 7, hMin: 150, hMax: 230, rx: [55, 85], trunks: true });
  grove(s, 1140, 1860, ground + 10, { count: 7, hMin: 150, hMax: 230, rx: [55, 85], trunks: true });
  grove(s, 360, 880, ground - 80, { count: 5, hMin: 140, hMax: 200 });
  grove(s, 1120, 1640, ground - 80, { count: 5, hMin: 140, hMax: 200 });
  grove(s, 560, 860, ground - 190, { count: 4, hMin: 110, hMax: 160, rx: [40, 60] });
  grove(s, 1140, 1440, ground - 190, { count: 4, hMin: 110, hMax: 160, rx: [40, 60] });

  vihara(s, 1000, 612, 0.86);
  grove(s, 740, 830, 648, { count: 2, hMin: 120, hMax: 150, rx: [40, 52] });
  grove(s, 1170, 1260, 648, { count: 2, hMin: 120, hMax: 150, rx: [40, 52] });
  stupa(s, 712, 622, 1.06);
  grove(s, 560, 660, 610, { count: 2, hMin: 160, hMax: 210, rx: [45, 60] });
  grove(s, 1280, 1420, 610, { count: 2, hMin: 230, hMax: 290, rx: [60, 80] });

  // The hill's line where it shows between the trees, and the far bank.
  s.stroke(
    [
      [150, 960],
      [300, 900],
      [460, 790],
      [620, 690],
      [800, 625],
      [1000, 612],
      [1200, 625],
      [1380, 690],
      [1540, 790],
      [1700, 900],
      [1850, 960],
    ],
    { w: 1.6 },
  );
  for (const [x, y, rx] of [
    [190, 935, 50],
    [270, 915, 42],
    [1750, 915, 45],
    [1820, 935, 40],
  ])
    clump(s, x, y, rx, rx * 0.55, { weight: 0.8, shade: 0.12 });

  // Sky: streaks of wash low over the hill, birds.
  for (const [x0, x1, y, h, o] of [
    [134, 760, 330, 26, 0.07],
    [200, 620, 285, 14, 0.06],
    [134, 470, 380, 34, 0.06],
    [480, 980, 170, 18, 0.05],
  ])
    s.wash(
      [
        [x0, y],
        [lerp(x0, x1, 0.3), y - h * 0.6],
        [x1, y - h * 0.2],
        [x1 - 40, y + h * 0.4],
        [lerp(x0, x1, 0.5), y + h * 0.5],
        [x0 + 20, y + h * 0.3],
      ],
      { opacity: o },
    );
  s.stroke(
    [
      [200, 300],
      [300, 292],
      [420, 296],
      [520, 286],
    ],
    { w: 1.1, detail: true },
  );
  s.stroke(
    [
      [150, 352],
      [260, 344],
      [340, 350],
    ],
    { w: 1.0, detail: true },
  );
  bird(s, 590, 205, 1.3);
  bird(s, 640, 178, 1.1);
  bird(s, 612, 250, 0.9);
  bird(s, 1520, 220, 1.1);
  s.guide(
    [
      [1508, 218],
      [1520, 223],
      [1532, 215],
    ],
    { opacity: 0.4 },
  );

  // Where the pen stopped: a last stroke trailing off.
  s.stroke(
    [
      [1004, 470],
      [1030, 468],
      [1052, 472],
    ],
    { w: 2.0, ink: true },
  );
  return s.svg({ foxing: 30, age: 0.8 });
}

/** Over the bed: a finished, signed view of a Tonle Sap village (1931). */
function tonleSap() {
  const s = new Sheet({ width: 1400, height: 980, seed: 1931 });
  s.underdrawing = 0.08;
  const bank = 600;
  s.stroke(rect(60, 60, 1340, 860), { w: 1.6, smooth: false, ruled: true });
  s.text(KHMER.tonleSap[0], 72, 922, { font: "Freehand", size: 46, anchor: "start" });
  s.text(`${KHMER.sora[0]} ${KHMER.lastYear[0]}`, 1328, 918, {
    font: "Freehand",
    size: 38,
    anchor: "end",
  });
  frame(s, 60, 60, 1340, 860);

  boat(s, 560, 800, 340, { k: 1.25 });
  stiltHouse(s, 300, 676, { w: 176, depth: 140, stilt: 130 });
  stiltHouse(s, 1000, 662, { w: 150, depth: 120, stilt: 116, ladder: false });
  stiltHouse(s, 690, 630, { w: 96, depth: 80, stilt: 84, wallH: 46, roofH: 64, ladder: false });
  boat(s, 1190, 728, 170, { k: 0.75 });
  // Reflections: the dark under the houses, drawn down into the water.
  for (const [x, y, w] of [
    [300, 690, 90],
    [1000, 676, 76],
    [690, 640, 50],
  ])
    for (let k = 0; k < 7; k++) {
      const yy = y + 8 + k * 9;
      const ww = w * (1 - k * 0.1) * s.r(0.7, 1);
      s.wash(
        [
          [x - ww, yy],
          [x + ww * 1.4, yy - 1],
          [x + ww * 1.3, yy + 4],
          [x - ww * 0.9, yy + 5],
        ],
        { opacity: 0.16, smooth: false },
      );
    }
  palm(s, 520, bank, 430, { size: 0.78, fans: 24 });
  palm(s, 1200, bank + 4, 500, { size: 0.82, fans: 24 });
  palm(s, 150, bank + 2, 360, { size: 0.66, fans: 20 });
  palm(s, 860, bank - 6, 300, { size: 0.55, fans: 18 });
  for (let x = 70; x < 1340; x += s.r(40, 70))
    clump(s, x, bank - s.r(6, 22), s.r(22, 42), s.r(14, 24), { shade: 0.2 });
  s.stroke(
    [
      [60, bank + 2],
      [500, bank - 2],
      [900, bank + 1],
      [1340, bank - 3],
    ],
    { w: 1.4 },
  );
  water(s, 60, 1340, bank + 2, 860);
  s.wash(
    [
      [60, bank + 2],
      [1340, bank - 3],
      [1340, 860],
      [60, 860],
    ],
    { opacity: 0.06 },
  );
  for (let x = 60; x < 1340; x += s.r(20, 40))
    clump(s, x, bank - 70 - s.r(0, 20), s.r(14, 26), s.r(8, 14), { weight: 0.7, shade: 0.1 });
  for (const [x0, x1, y, h, o] of [
    [60, 700, 220, 22, 0.06],
    [400, 1100, 160, 16, 0.05],
    [900, 1340, 260, 26, 0.06],
    [60, 380, 300, 18, 0.05],
  ])
    s.wash(
      [
        [x0, y],
        [lerp(x0, x1, 0.3), y - h * 0.6],
        [x1, y - h * 0.2],
        [x1 - 40, y + h * 0.4],
        [lerp(x0, x1, 0.5), y + h * 0.5],
        [x0 + 20, y + h * 0.3],
      ],
      { opacity: o },
    );
  bird(s, 760, 200, 1.3);
  bird(s, 810, 178, 1.1);
  bird(s, 860, 215, 1);
  return s.svg({ foxing: 18, age: 0.9 });
}

/** A sheet from Sora's sketchbook, pinned to the wall. */
function study(seed, draw) {
  const s = new Sheet({ width: 1000, height: 1000, seed });
  s.underdrawing = 0.22;
  draw(s);
  return s.svg({ foxing: 14, age: 0.7 });
}

const palmsStudy = () =>
  study(41, (s) => {
    const horizon = 560;
    s.guide(
      [
        [40, horizon],
        [960, horizon],
      ],
      { opacity: 0.3, smooth: false },
    );
    s.text(KHMER.sugarPalms[0], 70, 940, { font: "Freehand", size: 50, anchor: "start" });
    s.text(KHMER.lastYear[0], 930, 940, { font: "Freehand", size: 34, anchor: "end" });
    palm(s, 330, 760, 560, { size: 0.95, fans: 26 });
    palm(s, 640, 640, 360, { size: 0.66, fans: 22 });
    palm(s, 770, 600, 270, { size: 0.5, fans: 18 });
    stiltHouse(s, 150, horizon + 2, {
      w: 56,
      depth: 44,
      stilt: 34,
      wallH: 24,
      roofH: 34,
      ladder: false,
    });
    // Paddy dikes running to the horizon, water standing between them.
    for (const y of [600, 650, 730, 860])
      s.stroke(
        [
          [40, y + 4],
          [520, y],
          [960, y + 6],
        ],
        { w: lerp(1.0, 2.0, (y - 600) / 260) },
      );
    for (const x of [-300, 100, 500, 900, 1300])
      s.stroke(
        [
          [x, 980],
          [lerp(x, 500, 0.75), 610],
        ],
        { w: 1.4, smooth: false },
      );
    water(s, 40, 960, 600, 900, { density: 0.6 });
    for (let x = 40; x < 960; x += s.r(25, 45))
      clump(s, x, horizon - s.r(4, 14), s.r(14, 26), s.r(8, 14), { weight: 0.7, shade: 0.12 });
    s.wash(
      [
        [40, 600],
        [960, 606],
        [960, 900],
        [40, 900],
      ],
      { opacity: 0.05 },
    );
  });

const houseStudy = () =>
  study(52, (s) => {
    s.text(KHMER.woodenHouse[0], 70, 120, { font: "Freehand", size: 54, anchor: "start" });
    s.guide(
      [
        [60, 840],
        [960, 820],
      ],
      { opacity: 0.3, smooth: false },
    );
    s.guide(
      [
        [150, 330],
        [940, 160],
      ],
      { opacity: 0.18, smooth: false },
    );
    stiltHouse(s, 420, 840, { w: 250, depth: 200, stilt: 200, wallH: 110, roofH: 150 });
    palm(s, 840, 830, 560, { size: 0.72, fans: 22 });
    for (const [x, y] of [
      [180, 850],
      [260, 870],
      [640, 860],
      [720, 880],
      [880, 850],
    ])
      tuft(s, x, y, 1.5);
    s.stroke(
      [
        [60, 850],
        [400, 846],
        [960, 830],
      ],
      { w: 1.4 },
    );
    s.wash(
      [
        [100, 850],
        [700, 846],
        [760, 900],
        [140, 905],
      ],
      { opacity: 0.1 },
    );
  });

const ornamentStudy = () =>
  study(63, (s) => {
    s.text(KHMER.ornament[0], 70, 120, { font: "Freehand", size: 54, anchor: "start" });
    const P = (pts) => pts.map(([x, y]) => [330 + x * 1.35, 610 - y * 1.35]);
    s.guide(
      [
        [330, 280],
        [330, 640],
      ],
      { opacity: 0.25, smooth: false },
    );
    gable(s, P, 150, 0, 210, { tympanum: true, w: 2.4 });
    s.stroke(
      P([
        [-150, 0],
        [150, 0],
      ]),
      { w: 2.0, smooth: false },
    );
    nagaHood(s, 770, 560, 2.4);
    s.text(KHMER.naga[0], 770, 700, { font: "Freehand", size: 40 });
    for (const x of [150, 280, 410]) lotusBud(s, x, 830, 1.15);
    s.text(KHMER.lotus[0], 280, 960, { font: "Freehand", size: 40 });
    flourish(s, 620, 860, 1, { k: 1.4 });
    s.guide(
      [
        [600, 860],
        [920, 860],
      ],
      { opacity: 0.2, smooth: false },
    );
  });

const boatStudy = () =>
  study(85, (s) => {
    s.text(KHMER.boat[0], 70, 120, { font: "Freehand", size: 54, anchor: "start" });
    boat(s, 470, 520, 520, { k: 1.6 });
    water(s, 60, 940, 470, 640, { density: 0.8 });
    boat(s, 380, 830, 380, { rower: false, k: 1.2 });
    water(s, 120, 720, 800, 900, { density: 0.7 });
    s.guide(
      [
        [60, 470],
        [940, 470],
      ],
      { opacity: 0.25, smooth: false },
    );
    s.text(KHMER.tonleSap[0], 930, 960, { font: "Freehand", size: 34, anchor: "end" });
  });

/**
 * In the gilt frame on the west wall: a print of Angkor Wat, the five towers over
 * the moat, as sold in Phnom Penh. The frame's canvas shows only the middle of the
 * square texture (u 0.03–0.97, v 0.13–0.82), so the picture sits there.
 */
function angkorPrint() {
  const s = new Sheet({ width: 1000, height: 1000, seed: 1113 });
  s.underdrawing = 0.06;
  const [x0, y0, x1, y1] = [62, 150, 938, 740];
  s.stroke(rect(x0, y0, x1, y1), { w: 1.6, smooth: false, ruled: true });
  s.stroke(rect(x0 - 10, y0 - 10, x1 + 10, y1 + 10), { w: 3, smooth: false, ruled: true });
  s.text(KHMER.angkorWat[0], 500, 800, { font: "Preahvihear", size: 44, spacing: 2 });
  flourish(s, 390, 786, -1, { k: 0.45 });
  flourish(s, 610, 786, 1, { k: 0.45 });
  frame(s, x0, y0, x1, y1);
  const horizon = 560;
  palm(s, 150, 600, 360, { size: 0.68, fans: 22 });
  palm(s, 236, 590, 280, { size: 0.5, fans: 18 });
  palm(s, 850, 600, 320, { size: 0.62, fans: 22 });
  // Causeway to the west gate, its balustrades running in.
  s.stroke(
    [
      [420, y1],
      [486, horizon + 8],
    ],
    { w: 1.8, smooth: false },
  );
  s.stroke(
    [
      [580, y1],
      [514, horizon + 8],
    ],
    { w: 1.8, smooth: false },
  );
  s.stroke(
    [
      [404, y1],
      [480, horizon + 8],
    ],
    { w: 1.2, smooth: false },
  );
  s.stroke(
    [
      [596, y1],
      [520, horizon + 8],
    ],
    { w: 1.2, smooth: false },
  );
  s.occlude([
    [400, y1],
    [478, horizon + 6],
    [522, horizon + 6],
    [600, y1],
  ]);
  water(s, x0, x1, horizon + 6, y1, { density: 0.7 });
  // The towers' reflection in the moat.
  for (const [x, top, bw] of [
    [500, 250, 64],
    [420, 320, 48],
    [580, 320, 48],
    [330, 368, 42],
    [670, 368, 42],
  ])
    s.wash(
      [
        [x - bw / 2, horizon + 10],
        [x - bw * 0.4, horizon + 10 + (horizon - top) * 0.3],
        [x, horizon + 10 + (horizon - top) * 0.55],
        [x + bw * 0.4, horizon + 10 + (horizon - top) * 0.3],
        [x + bw / 2, horizon + 10],
      ],
      { opacity: 0.1 },
    );
  s.stroke(
    [
      [x0, horizon + 6],
      [x1, horizon + 6],
    ],
    { w: 1.4, smooth: false },
  );
  gallery(s, 190, 810, 520, 40);
  gallery(s, 270, 730, 478, 34);
  gallery(s, 340, 660, 440, 30);
  prasat(s, 330, 410, 368, 42);
  prasat(s, 670, 410, 368, 42);
  prasat(s, 420, 380, 320, 48);
  prasat(s, 580, 380, 320, 48);
  prasat(s, 500, 360, 250, 64);
  for (let x = x0; x < x1; x += s.r(22, 40))
    clump(s, x, horizon - s.r(4, 18), s.r(16, 30), s.r(10, 16), { weight: 0.75, shade: 0.14 });
  for (const [a, b, y, h, o] of [
    [x0, 520, 230, 20, 0.06],
    [480, x1, 190, 16, 0.05],
    [x0, 420, 330, 18, 0.05],
  ])
    s.wash(
      [
        [a, y],
        [lerp(a, b, 0.3), y - h * 0.6],
        [b, y - h * 0.2],
        [b - 40, y + h * 0.4],
        [lerp(a, b, 0.5), y + h * 0.5],
        [a + 20, y + h * 0.3],
      ],
      { opacity: o },
    );
  bird(s, 700, 230, 1.1);
  bird(s, 740, 210, 0.9);
  return s.svg({ paper: "#e6dcc4", foxing: 16, age: 1 });
}

const letteringStudy = () =>
  study(74, (s) => {
    s.inked = (x, y) => y < 700 || x < 380;
    for (const y of [270, 440, 610, 740, 880]) {
      s.guide(
        [
          [60, y],
          [940, y],
        ],
        { opacity: 0.28, smooth: false, w: 0.8 },
      );
      s.guide(
        [
          [60, y - 46],
          [940, y - 46],
        ],
        { opacity: 0.16, smooth: false, w: 0.8 },
      );
    }
    s.text(KHMER.letters[0], 70, 110, { font: "Freehand", size: 44, anchor: "start" });
    s.text(KHMER.phnomPenh[0], 500, 265, { font: "Preahvihear", size: 150, outline: 2.6 });
    s.text(KHMER.phnomPenh[0], 500, 435, { font: "Preahvihear", size: 112 });
    const letters = KHMER.consonants[0].split(" ");
    s.text(letters.slice(0, 10).join(" "), 500, 600, { font: "Freehand", size: 62 });
    s.text(letters.slice(10, 20).join(" "), 500, 730, { font: "Freehand", size: 62 });
    s.text(KHMER.numerals[0], 500, 868, { font: "Preahvihear", size: 56 });
    for (const [x, y] of [
      [860, 960],
      [900, 950],
    ])
      s.stroke(
        [
          [x, y],
          [x + 12, y - 8],
          [x + 24, y + 3],
        ],
        { w: 1.6, ink: true },
      );
  });

/** A printed two-colour wall chart of the Khmer consonants (the "typography prints"). */
function alphabetChart() {
  const s = new Sheet({ width: 700, height: 1000, seed: 33 });
  s.underdrawing = 0;
  s.stroke(rect(22, 22, 678, 978), { w: 6, smooth: false, ruled: true, color: RED });
  s.stroke(rect(36, 36, 664, 964), { w: 1.6, smooth: false, ruled: true });
  for (const [x, y, dir] of [
    [64, 74, 1],
    [636, 74, -1],
  ])
    flourish(s, x, y, dir, { color: RED, k: 0.5 });
  s.text(KHMER.khmerScript[0], 350, 160, { font: "Preahvihear", size: 84, fill: RED });
  s.text(KHMER.consonantCount[0], 350, 222, { font: "Preahvihear", size: 34 });
  s.stroke(
    [
      [110, 250],
      [590, 250],
    ],
    { w: 2.2, smooth: false, ruled: true, color: RED },
  );
  const letters = KHMER.consonants[0].split(" ");
  const rows = [
    letters.slice(0, 5),
    letters.slice(5, 10),
    letters.slice(10, 15),
    letters.slice(15, 20),
    letters.slice(20, 25),
    letters.slice(25, 29),
    letters.slice(29),
  ];
  const cell = 96;
  rows.forEach((row, j) => {
    const y = 272 + j * 86;
    const x0 = 350 - (row.length * cell) / 2;
    row.forEach((letter, i) => {
      const x = x0 + i * cell;
      s.stroke(rect(x + 6, y, x + cell - 6, y + 78), { w: 1.3, smooth: false, ruled: true });
      s.text(letter, x + cell / 2, y + 60, { font: "Preahvihear", size: 56 });
    });
  });
  s.stroke(
    [
      [110, 892],
      [590, 892],
    ],
    { w: 1.4, smooth: false, ruled: true, color: RED },
  );
  s.text(KHMER.numerals[0], 350, 934, { font: "Preahvihear", size: 30, spacing: 2 });
  return s.svg({ paper: "#ece3cd", foxing: 22, age: 0.9 });
}

export const drawings = [
  {
    name: "illustration",
    file: "T_studio_illustration_BC",
    size: [2048, 2048],
    draw: illustration,
  },
  { name: "tonle_sap", file: "T_studio_print_tonle_sap_BC", size: [1024, 1024], draw: tonleSap },
  { name: "alphabet", file: "T_studio_print_alphabet_BC", size: [1024, 1024], draw: alphabetChart },
  { name: "angkor", file: "T_studio_print_angkor_BC", size: [1024, 1024], draw: angkorPrint },
  { name: "study_palms", file: "T_studio_study_palms_BC", size: [1024, 1024], draw: palmsStudy },
  { name: "study_house", file: "T_studio_study_house_BC", size: [1024, 1024], draw: houseStudy },
  {
    name: "study_ornament",
    file: "T_studio_study_ornament_BC",
    size: [1024, 1024],
    draw: ornamentStudy,
  },
  {
    name: "study_lettering",
    file: "T_studio_study_lettering_BC",
    size: [1024, 1024],
    draw: letteringStudy,
  },
  { name: "study_boats", file: "T_studio_study_boats_BC", size: [1024, 1024], draw: boatStudy },
];
