/**
 * Paints the far forest's tree cards: silhouettes seen through rain and fog
 * beyond the modelled trees (ForestBorder). Atlas of 4 × 2 square cells, each
 * a tree standing on the cell's bottom edge, on a transparent ground:
 * 0–3 broadleaf crowns (3 an emergent with buttresses), 4 sugar palm, 5 bamboo
 * clump, 6 coconut palm, 7 dead tree. Colours follow the modelled leaves and
 * bark under the night grade; there are no reference images.
 */
export const CARD_COLUMNS = 4;
export const CARD_ROWS = 2;

type Ctx = CanvasRenderingContext2D;

function leaf(
  ctx: Ctx,
  x: number,
  y: number,
  rx: number,
  ry: number,
  angle: number,
  colour: string,
) {
  ctx.fillStyle = colour;
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, angle, 0, Math.PI * 2);
  ctx.fill();
}

/** Old-growth night greens: cold, deep and barely saturated. */
function green(random: () => number, light: number): string {
  const hue = 120 + random() * 34;
  const sat = 10 + random() * 16;
  return `hsl(${hue.toFixed(0)},${sat.toFixed(0)}%,${(light * 0.8 + random() * 5).toFixed(1)}%)`;
}

function bark(random: () => number, light = 14): string {
  return `hsl(${(24 + random() * 14).toFixed(0)},${(10 + random() * 10).toFixed(0)}%,${(light + random() * 6).toFixed(1)}%)`;
}

/** A tapered limb from (x0, y0) to (x1, y1), bent through a control point. */
function limb(
  ctx: Ctx,
  x0: number,
  y0: number,
  cx: number,
  cy: number,
  x1: number,
  y1: number,
  w0: number,
  w1: number,
  colour: string,
) {
  const steps = 8;
  ctx.strokeStyle = colour;
  ctx.lineCap = "round";
  for (let i = 0; i < steps; i++) {
    const t0 = i / steps,
      t1 = (i + 1) / steps;
    const at = (t: number) => [
      (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
      (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1,
    ];
    const [ax, ay] = at(t0);
    const [bx, by] = at(t1);
    ctx.lineWidth = w0 + (w1 - w0) * t0;
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.stroke();
  }
}

function broadleaf(ctx: Ctx, s: number, random: () => number, emergent: boolean) {
  const base = s;
  const cx = s / 2 + (random() - 0.5) * s * 0.06;
  const trunkTop = s * (emergent ? 0.42 : 0.55 - random() * 0.08);
  const crownY = s * (emergent ? 0.24 : 0.3 + random() * 0.06);
  const hw = s * (emergent ? 0.3 : 0.38 + random() * 0.08);
  const hh = s * (emergent ? 0.17 : 0.2 + random() * 0.05);
  const w = s * (emergent ? 0.045 : 0.036);
  // Buttressed foot and trunk.
  ctx.fillStyle = bark(random, 12);
  ctx.beginPath();
  ctx.moveTo(cx - w * (emergent ? 3.2 : 2), base);
  ctx.quadraticCurveTo(cx - w * 0.7, base - s * 0.05, cx - w * 0.5, base - s * 0.12);
  ctx.lineTo(cx - w * 0.32, trunkTop);
  ctx.lineTo(cx + w * 0.32, trunkTop);
  ctx.lineTo(cx + w * 0.5, base - s * 0.12);
  ctx.quadraticCurveTo(cx + w * 0.7, base - s * 0.05, cx + w * (emergent ? 3 : 2.2), base);
  ctx.closePath();
  ctx.fill();
  // Limbs up into the crown.
  const limbs = 4 + Math.floor(random() * 3);
  const ends: [number, number][] = [];
  for (let i = 0; i < limbs; i++) {
    const side = i % 2 ? 1 : -1;
    const ex = cx + side * hw * (0.3 + random() * 0.6);
    const ey = crownY + hh * (random() - 0.2) * 0.8;
    const sy = trunkTop + (base - trunkTop) * random() * 0.25;
    limb(
      ctx,
      cx,
      sy,
      cx + side * hw * 0.15,
      (sy + ey) / 2,
      ex,
      ey,
      w * 0.45,
      w * 0.12,
      bark(random, 11),
    );
    ends.push([ex, ey]);
  }
  // Leaf clusters in a lumpy, flat-topped crown, darker underneath.
  const lumps = Array.from({ length: 7 }, () => 0.8 + random() * 0.45);
  const clusters = emergent ? 80 : 110;
  for (let k = 0; k < clusters; k++) {
    const a = random() * Math.PI * 2;
    const r = Math.sqrt(random());
    const lump = lumps[Math.floor(((a / (Math.PI * 2)) * lumps.length) % lumps.length)];
    const x = cx + Math.cos(a) * r * hw * lump;
    let y = crownY + Math.sin(a) * r * hh * lump;
    if (k < ends.length * 3) {
      const [ex, ey] = ends[k % ends.length];
      y = ey + (random() - 0.5) * hh * 0.5;
      void ex;
    }
    const under = (y - (crownY - hh)) / (2 * hh); // 0 top … 1 bottom
    const size = s * (0.035 + random() * 0.04);
    for (let j = 0; j < 22; j++) {
      const lx = x + (random() - 0.5) * size * 2;
      const ly = y + (random() - 0.5) * size * 1.4;
      leaf(
        ctx,
        lx,
        ly,
        s * 0.012 + random() * s * 0.008,
        s * 0.005 + random() * s * 0.004,
        random() * Math.PI,
        green(random, 15 - under * 7),
      );
    }
  }
  // A few lianas hanging out of the crown.
  for (let i = 0; i < 4; i++) {
    const x = cx + (random() - 0.5) * hw * 1.4;
    const y0 = crownY + hh * 0.5;
    limb(
      ctx,
      x,
      y0,
      x + (random() - 0.5) * 8,
      y0 + s * 0.12,
      x + (random() - 0.5) * 12,
      y0 + s * (0.15 + random() * 0.2),
      2,
      1,
      bark(random, 9),
    );
  }
}

function sugarPalm(ctx: Ctx, s: number, random: () => number) {
  const cx = s / 2;
  const top = s * 0.24;
  limb(
    ctx,
    cx,
    s,
    cx + (random() - 0.5) * 6,
    s * 0.6,
    cx + (random() - 0.5) * 4,
    top,
    s * 0.024,
    s * 0.018,
    bark(random, 13),
  );
  // Dead fans hanging below the crown.
  for (let i = 0; i < 7; i++) {
    const a = Math.PI * (0.25 + random() * 0.5);
    const x = cx + Math.cos(a) * s * 0.04 * (random() - 0.5) * 4;
    leaf(
      ctx,
      x,
      top + s * (0.05 + random() * 0.04),
      s * 0.025,
      s * 0.06,
      (random() - 0.5) * 0.4,
      `hsl(30,${18 + random() * 10}%,${12 + random() * 5}%)`,
    );
  }
  // Round crown of stiff fan leaves on short petioles.
  for (let i = 0; i < 34; i++) {
    const a = -Math.PI * (0.05 + random() * 0.9) + (random() < 0.25 ? Math.PI * 0.9 * random() : 0);
    const len = s * (0.08 + random() * 0.06);
    const ex = cx + Math.cos(a) * len;
    const ey = top + Math.sin(a) * len * 0.8;
    limb(ctx, cx, top, (cx + ex) / 2, (top + ey) / 2, ex, ey, 2, 1, bark(random, 16));
    const r = s * (0.045 + random() * 0.035);
    const colour = green(random, 15);
    ctx.strokeStyle = colour;
    ctx.lineWidth = 1.6;
    for (let k = 0; k < 16; k++) {
      const b = a + (k / 15 - 0.5) * Math.PI * 0.9;
      ctx.beginPath();
      ctx.moveTo(ex, ey);
      ctx.lineTo(ex + Math.cos(b) * r, ey + Math.sin(b) * r);
      ctx.stroke();
    }
  }
}

function bamboo(ctx: Ctx, s: number, random: () => number) {
  const cx = s / 2;
  for (let i = 0; i < 26; i++) {
    const x0 = cx + (random() - 0.5) * s * 0.12;
    const lean = (random() - 0.5) * 2;
    const height = s * (0.55 + random() * 0.42);
    const tipX = x0 + lean * s * 0.32;
    const tipY = s - height;
    const ctrlX = x0 + lean * s * 0.05;
    const ctrlY = s - height * 0.7;
    limb(
      ctx,
      x0,
      s,
      ctrlX,
      ctrlY,
      tipX,
      tipY,
      s * 0.012,
      s * 0.004,
      `hsl(${55 + random() * 25},${18 + random() * 10}%,${12 + random() * 6}%)`,
    );
    // Sprays of narrow leaves along the upper culm, hanging from the arch.
    for (let k = 0; k < 60; k++) {
      const t = 0.4 + random() * 0.6;
      const x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * ctrlX + t * t * tipX;
      const y = (1 - t) ** 2 * s + 2 * (1 - t) * t * ctrlY + t * t * tipY;
      leaf(
        ctx,
        x + (random() - 0.5) * 14,
        y + random() * 12,
        s * 0.014,
        s * 0.0035,
        Math.PI * 0.5 + (random() - 0.5) * 1.6,
        green(random, 13),
      );
    }
  }
}

function coconut(ctx: Ctx, s: number, random: () => number) {
  const lean = (random() - 0.5) * s * 0.2;
  const cx = s / 2;
  const topX = cx + lean;
  const top = s * 0.2;
  limb(
    ctx,
    cx - lean * 0.4,
    s,
    cx + lean * 0.2,
    s * 0.55,
    topX,
    top,
    s * 0.026,
    s * 0.017,
    bark(random, 15),
  );
  for (let i = 0; i < 15; i++) {
    const a = -Math.PI * random();
    const len = s * (0.18 + random() * 0.1);
    const ex = topX + Math.cos(a) * len;
    const ey = top + Math.abs(Math.sin(a)) * len * 0.15 + s * 0.08 * Math.abs(Math.cos(a));
    const mx = topX + Math.cos(a) * len * 0.5;
    const my = top - len * 0.2 * Math.abs(Math.sin(a));
    limb(ctx, topX, top, mx, my, ex, ey, 2.5, 1, bark(random, 18));
    for (let k = 1; k < 20; k++) {
      const t = k / 20;
      const x = (1 - t) ** 2 * topX + 2 * (1 - t) * t * mx + t * t * ex;
      const y = (1 - t) ** 2 * top + 2 * (1 - t) * t * my + t * t * ey;
      for (const side of [-1, 1])
        leaf(
          ctx,
          x,
          y + s * 0.012,
          s * 0.018 * (1 - t * 0.5),
          s * 0.003,
          a + side * 1.1 + Math.PI / 2,
          green(random, 17),
        );
    }
  }
}

function deadTree(ctx: Ctx, s: number, random: () => number) {
  const cx = s / 2;
  const grow = (x: number, y: number, a: number, len: number, w: number, depth: number) => {
    const ex = x + Math.cos(a) * len;
    const ey = y + Math.sin(a) * len;
    limb(
      ctx,
      x,
      y,
      (x + ex) / 2 + (random() - 0.5) * len * 0.2,
      (y + ey) / 2,
      ex,
      ey,
      w,
      w * 0.6,
      `hsl(30,6%,${18 + random() * 6}%)`,
    );
    if (depth === 0) return;
    const n = 2 + Math.floor(random() * 2);
    for (let i = 0; i < n; i++)
      grow(ex, ey, a + (random() - 0.5) * 1.4, len * (0.5 + random() * 0.25), w * 0.6, depth - 1);
  };
  grow(cx, s, -Math.PI / 2 + (random() - 0.5) * 0.15, s * 0.45, s * 0.04, 3);
}

/** Paints all eight cells into a canvas of `4 × cell` by `2 × cell` pixels. */
export function paintForestCards(ctx: Ctx, cell: number, random: () => number): void {
  ctx.clearRect(0, 0, cell * CARD_COLUMNS, cell * CARD_ROWS);
  const painters: ((c: Ctx, s: number) => void)[] = [
    (c, s) => broadleaf(c, s, random, false),
    (c, s) => broadleaf(c, s, random, false),
    (c, s) => broadleaf(c, s, random, false),
    (c, s) => broadleaf(c, s, random, true),
    (c, s) => sugarPalm(c, s, random),
    (c, s) => bamboo(c, s, random),
    (c, s) => coconut(c, s, random),
    (c, s) => deadTree(c, s, random),
  ];
  painters.forEach((paint, i) => {
    ctx.save();
    ctx.translate((i % CARD_COLUMNS) * cell, Math.floor(i / CARD_COLUMNS) * cell);
    ctx.beginPath();
    ctx.rect(0, 0, cell, cell);
    ctx.clip();
    paint(ctx, cell);
    ctx.restore();
  });
}
