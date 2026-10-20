/**
 * Sora's small drawings beside her notes, drawn with a wobbly fountain-pen
 * line and ink wash (Art Bible, section 10). Placeholders until the real
 * illustrations exist: each is a few strokes, deterministic per id.
 */

export const INK = "#17120f";
export const BLOOD_INK = "#5e1a14";

export interface Pen {
  ctx: CanvasRenderingContext2D;
  /** Pixels per millimetre of paper. */
  mm: number;
  rand: () => number;
}

/** Small deterministic random generator (mulberry32). */
export function seeded(text: string): () => number {
  let h = 1779033703;
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 3432918353);
  return () => {
    h = (h + 0x6d2b79f5) | 0;
    let t = Math.imul(h ^ (h >>> 15), 1 | h);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A hand-drawn polyline through points given in millimetres. */
function stroke(pen: Pen, points: [number, number][], width = 0.35, close = false): void {
  const { ctx, mm, rand } = pen;
  ctx.beginPath();
  points.forEach(([x, y], i) => {
    const jx = (rand() - 0.5) * 0.5;
    const jy = (rand() - 0.5) * 0.5;
    if (i === 0) ctx.moveTo((x + jx) * mm, (y + jy) * mm);
    else ctx.lineTo((x + jx) * mm, (y + jy) * mm);
  });
  if (close) ctx.closePath();
  ctx.lineWidth = width * mm;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = INK;
  ctx.stroke();
}

function ellipse(cx: number, cy: number, rx: number, ry: number, steps = 24, from = 0, to = 1) {
  const pts: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const a = (from + (to - from) * (i / steps)) * Math.PI * 2;
    pts.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]);
  }
  return pts;
}

/** Translucent ink wash over a closed shape. */
function wash(pen: Pen, points: [number, number][], alpha: number, colour = INK): void {
  const { ctx, mm } = pen;
  ctx.beginPath();
  points.forEach(([x, y], i) =>
    i === 0 ? ctx.moveTo(x * mm, y * mm) : ctx.lineTo(x * mm, y * mm),
  );
  ctx.closePath();
  ctx.globalAlpha *= alpha;
  ctx.fillStyle = colour;
  ctx.fill();
  ctx.globalAlpha /= alpha;
}

function lamp(pen: Pen, x: number, y: number, h: number): void {
  const w = h * 0.45;
  stroke(pen, ellipse(x + w / 2, y + h * 0.45, w * 0.42, h * 0.28), 0.35, true);
  stroke(
    pen,
    [
      [x + w * 0.1, y + h * 0.8],
      [x + w * 0.9, y + h * 0.8],
      [x + w * 0.8, y + h * 0.95],
      [x + w * 0.2, y + h * 0.95],
    ],
    0.35,
    true,
  );
  stroke(pen, ellipse(x + w / 2, y + h * 0.18, w * 0.35, h * 0.2, 16, 0.5, 1));
  stroke(pen, ellipse(x + w / 2, y + h * 0.46, w * 0.06, h * 0.1), 0.3, true);
}

function incense(pen: Pen, x: number, y: number, h: number): void {
  for (let i = 0; i < 4; i++) {
    const sx = x + i * 3;
    stroke(
      pen,
      [
        [sx, y + h],
        [sx + 0.6, y + h * 0.25],
      ],
      0.3,
    );
    wash(pen, ellipse(sx + 0.6, y + h * 0.22, 0.7, 0.9), 0.8);
    stroke(
      pen,
      [
        [sx + 0.6, y + h * 0.18],
        [sx + 1.5, y + h * 0.08],
        [sx + 0.4, y],
      ],
      0.15,
    );
  }
  stroke(
    pen,
    [
      [x - 2, y + h],
      [x + 12, y + h],
    ],
    0.4,
  );
}

function thread(pen: Pen, x: number, y: number, h: number): void {
  const pts: [number, number][] = [];
  for (let i = 0; i <= 40; i++) {
    const a = (i / 40) * Math.PI * 2;
    pts.push([
      x + h * 0.45 + Math.cos(a) * h * 0.42 + Math.sin(a * 3) * 0.6,
      y + h / 2 + Math.sin(a) * h * 0.3,
    ]);
  }
  stroke(pen, pts, 0.25, true);
}

/** Draws drawing `id` into the box (millimetres), at the context's current alpha. */
export function drawSketch(pen: Pen, id: string, x: number, y: number, w: number, h: number): void {
  const { ctx } = pen;
  ctx.save();
  switch (id) {
    case "inkBlot": {
      // The illustration Sora was finishing, ruined by a spreading blot.
      stroke(pen, ellipse(x + w * 0.35, y + h * 0.3, w * 0.12, h * 0.16), 0.3, true);
      stroke(pen, [
        [x + w * 0.22, y + h * 0.95],
        [x + w * 0.3, y + h * 0.5],
        [x + w * 0.4, y + h * 0.5],
        [x + w * 0.5, y + h * 0.95],
      ]);
      stroke(
        pen,
        [
          [x + w * 0.05, y + h * 0.95],
          [x + w * 0.95, y + h * 0.95],
        ],
        0.3,
      );
      const blot: [number, number][] = [];
      for (let i = 0; i < 48; i++) {
        const a = (i / 48) * Math.PI * 2;
        const r = h * (0.28 + pen.rand() * 0.12 + (i % 7 === 0 ? 0.12 : 0));
        blot.push([x + w * 0.58 + Math.cos(a) * r, y + h * 0.48 + Math.sin(a) * r * 0.85]);
      }
      wash(pen, blot, 0.92);
      for (let i = 0; i < 9; i++) {
        const a = pen.rand() * Math.PI * 2;
        const d = h * (0.5 + pen.rand() * 0.3);
        wash(
          pen,
          ellipse(
            x + w * 0.58 + Math.cos(a) * d,
            y + h * 0.48 + Math.sin(a) * d * 0.8,
            0.6 + pen.rand() * 1.6,
            0.6 + pen.rand() * 1.4,
            10,
          ),
          0.9,
        );
      }
      break;
    }
    case "duties":
      lamp(pen, x + 4, y + 2, h - 4);
      incense(pen, x + w * 0.38, y + 4, h - 8);
      thread(pen, x + w * 0.68, y + 4, h - 8);
      break;
    case "altar": {
      const top = y + h * 0.45;
      stroke(
        pen,
        [
          [x + w * 0.15, top],
          [x + w * 0.85, top],
          [x + w * 0.85, y + h * 0.95],
          [x + w * 0.15, y + h * 0.95],
        ],
        0.35,
        true,
      );
      stroke(
        pen,
        [
          [x + w * 0.1, top],
          [x + w * 0.9, top],
        ],
        0.5,
      );
      stroke(
        pen,
        [
          [x + w * 0.3, top],
          [x + w * 0.3, y + h * 0.12],
        ],
        0.3,
      );
      stroke(
        pen,
        [
          [x + w * 0.7, top],
          [x + w * 0.7, y + h * 0.12],
        ],
        0.3,
      );
      wash(pen, ellipse(x + w * 0.3, y + h * 0.1, 1, 1.6), 0.8);
      wash(pen, ellipse(x + w * 0.7, y + h * 0.1, 1, 1.6), 0.8);
      stroke(pen, ellipse(x + w * 0.5, y + h * 0.32, w * 0.1, h * 0.12), 0.3, true);
      wash(
        pen,
        [
          [x + w * 0.15, top],
          [x + w * 0.85, top],
          [x + w * 0.85, y + h * 0.95],
          [x + w * 0.15, y + h * 0.95],
        ],
        0.12,
      );
      break;
    }
    case "names": {
      ctx.font = `${5.5 * pen.mm}px "Patrick Hand"`;
      ctx.fillStyle = INK;
      ctx.fillText("Chea", (x + 6) * pen.mm, (y + 6) * pen.mm);
      stroke(
        pen,
        [
          [x + 6, y + 8],
          [x + 24, y + 8],
        ],
        0.25,
      );
      for (let i = 1; i < 5; i++) {
        const ly = y + 8 + i * 7;
        stroke(
          pen,
          [
            [x + 6, ly],
            [x + 9, ly - 1],
            [x + 12, ly + 0.5],
            [x + 15, ly - 0.8],
            [x + 18 + pen.rand() * 4, ly],
          ],
          0.3,
        );
      }
      stroke(
        pen,
        [
          [x + 3, y + 1],
          [x + 3, y + h - 2],
        ],
        0.25,
      );
      break;
    }
    case "jars": {
      stroke(
        pen,
        [
          [x, y + 6],
          [x + w * 0.9, y + 6],
        ],
        0.5,
      );
      for (const px of [0.05, 0.85])
        stroke(
          pen,
          [
            [x + w * px, y + 6],
            [x + w * px, y + h],
          ],
          0.6,
        );
      for (let i = 0; i < 3; i++) {
        const cx = x + w * (0.25 + i * 0.22);
        const body = ellipse(cx, y + h * 0.68, 5.5, 7.5, 24);
        stroke(pen, body, 0.35, true);
        wash(pen, body, 0.15);
        stroke(pen, ellipse(cx, y + h * 0.68 - 7, 2.5, 0.8), 0.3, true);
      }
      break;
    }
    case "burner": {
      const cx = x + w * 0.4;
      const bowl = ellipse(cx, y + h * 0.6, 8, 4, 20, 0, 0.5);
      stroke(pen, bowl, 0.4);
      stroke(
        pen,
        [
          [cx - 8, y + h * 0.6],
          [cx + 8, y + h * 0.6],
        ],
        0.4,
      );
      stroke(
        pen,
        [
          [cx - 4, y + h * 0.7],
          [cx - 6, y + h * 0.95],
        ],
        0.35,
      );
      stroke(
        pen,
        [
          [cx + 4, y + h * 0.7],
          [cx + 6, y + h * 0.95],
        ],
        0.35,
      );
      wash(pen, ellipse(cx, y + h * 0.5, 2, 3.5), 0.5);
      // A small figure, and a tall shadow behind it.
      const fx = x + w * 0.62;
      stroke(pen, ellipse(fx, y + h * 0.42, 1.6, 1.8), 0.3, true);
      stroke(
        pen,
        [
          [fx, y + h * 0.48],
          [fx, y + h * 0.75],
          [fx - 2, y + h * 0.95],
        ],
        0.3,
      );
      stroke(
        pen,
        [
          [fx, y + h * 0.75],
          [fx + 2, y + h * 0.95],
        ],
        0.3,
      );
      wash(
        pen,
        [
          [fx + 4, y + h * 0.95],
          [fx + 6, y + h * 0.1],
          [fx + 11, y + h * 0.05],
          [fx + 13, y + h * 0.95],
        ],
        0.55,
      );
      break;
    }
    case "portrait": {
      const cx = x + 13;
      stroke(pen, ellipse(cx, y + h * 0.35, 6, 7.5), 0.35, true);
      stroke(pen, ellipse(cx, y + h * 0.95, 10, 6, 20, 0.5, 1), 0.35);
      stroke(
        pen,
        [
          [cx - 6, y + h * 0.28],
          [cx - 2, y + h * 0.12],
          [cx + 4, y + h * 0.1],
          [cx + 6, y + h * 0.3],
        ],
        0.25,
      );
      for (let i = 0; i < 6; i++)
        stroke(
          pen,
          [
            [cx + 2 + i, y + h * 0.4],
            [cx + i, y + h * 0.55],
          ],
          0.15,
        );
      break;
    }
    default:
      stroke(
        pen,
        [
          [x, y],
          [x + w, y + h],
        ],
        0.3,
      );
  }
  ctx.restore();
}

/** The seven night circles: empty outline, pencil fill, or ink wash. */
export function drawNightCircles(
  pen: Pen,
  marks: readonly string[],
  x: number,
  y: number,
  w: number,
): void {
  const r = Math.min(5.5, w / 16);
  for (let i = 0; i < 7; i++) {
    const cx = x + r + (i * (w - 2 * r)) / 6;
    const circle = ellipse(cx, y + r, r, r, 28);
    if (marks[i] === "ink") wash(pen, circle, 0.75);
    if (marks[i] === "pencil") {
      pen.ctx.save();
      pen.ctx.globalAlpha *= 0.45;
      for (let k = -r; k < r; k += 1.1)
        stroke(
          pen,
          [
            [cx + k, y + r - Math.sqrt(r * r - k * k) * 0.9],
            [cx + k + 0.8, y + r + Math.sqrt(r * r - k * k) * 0.9],
          ],
          0.18,
        );
      pen.ctx.restore();
    }
    stroke(pen, circle, 0.35, true);
  }
}

/** Sora's plan of the house and the funeral tent, drawn as she explores. */
export function drawHousePlan(pen: Pen, x: number, y: number, w: number, h: number): void {
  // House on stilts (plan): outer walls, rooms, stair.
  const house: [number, number][] = [
    [x, y],
    [x + w * 0.62, y],
    [x + w * 0.62, y + h * 0.55],
    [x, y + h * 0.55],
  ];
  stroke(pen, house, 0.45, true);
  wash(pen, house, 0.06);
  stroke(
    pen,
    [
      [x + w * 0.32, y],
      [x + w * 0.32, y + h * 0.3],
    ],
    0.3,
  );
  stroke(
    pen,
    [
      [x, y + h * 0.3],
      [x + w * 0.45, y + h * 0.3],
    ],
    0.3,
  );
  for (let i = 0; i < 6; i++) {
    const sx = x + w * 0.62 + i * 1.6;
    stroke(
      pen,
      [
        [sx, y + h * 0.42],
        [sx, y + h * 0.55],
      ],
      0.2,
    );
  }
  for (const [px, py] of [
    [0.05, 0.08],
    [0.3, 0.08],
    [0.57, 0.08],
    [0.05, 0.48],
    [0.3, 0.48],
    [0.57, 0.48],
  ]) {
    stroke(pen, ellipse(x + w * px, y + h * py, 0.8, 0.8, 8), 0.3, true);
  }
  // Funeral tent in the courtyard.
  const tent: [number, number][] = [
    [x + w * 0.45, y + h * 0.68],
    [x + w * 0.98, y + h * 0.68],
    [x + w * 0.98, y + h],
    [x + w * 0.45, y + h],
  ];
  stroke(pen, tent, 0.35, true);
  for (let i = 1; i < 5; i++)
    stroke(
      pen,
      [
        [x + w * (0.45 + i * 0.106), y + h * 0.68],
        [x + w * (0.45 + i * 0.106), y + h],
      ],
      0.12,
    );
  // The path between them.
  stroke(
    pen,
    [
      [x + w * 0.66, y + h * 0.56],
      [x + w * 0.68, y + h * 0.62],
      [x + w * 0.66, y + h * 0.67],
    ],
    0.2,
  );
}
