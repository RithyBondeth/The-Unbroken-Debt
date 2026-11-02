/**
 * Painted textures for the forest's omens (TreeOmens): blood on bark, old
 * betel-juice stains, wet cotton cloth and twisted thread. Drawn on a canvas
 * at load, from seeded randomness, so every stain has the irregular, broken
 * edge a real one takes from rough bark rather than a clean vector shape.
 */

type Ctx = CanvasRenderingContext2D;

/** Smooth value noise in 0–1 over pixel coordinates, `cell` pixels per lattice step. */
function valueNoise(random: () => number, cell: number): (x: number, y: number) => number {
  const size = 64;
  const lattice = Float32Array.from({ length: size * size }, () => random());
  const at = (i: number, j: number) => lattice[(i & (size - 1)) + (j & (size - 1)) * size];
  return (x, y) => {
    const fx = x / cell,
      fy = y / cell;
    const i = Math.floor(fx),
      j = Math.floor(fy);
    const tx = fx - i,
      ty = fy - j;
    const sx = tx * tx * (3 - 2 * tx),
      sy = ty * ty * (3 - 2 * ty);
    const a = at(i, j) + (at(i + 1, j) - at(i, j)) * sx;
    const b = at(i, j + 1) + (at(i + 1, j + 1) - at(i, j + 1)) * sx;
    return a + (b - a) * sy;
  };
}

/** A rounded stroke: a finger, a drip's run. */
function capsule(ctx: Ctx, x0: number, y0: number, x1: number, y1: number, width: number): void {
  ctx.lineCap = "round";
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();
}

/** A run of liquid down bark: wavering, thinning, ending in a bead. */
function drip(ctx: Ctx, random: () => number, x: number, y: number, length: number, width: number) {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  let px = x,
    py = y,
    w = width;
  const steps = Math.max(4, Math.round(length / 14));
  for (let s = 0; s < steps; s++) {
    const nx = px + (random() - 0.5) * 5;
    const ny = py + length / steps;
    ctx.lineWidth = w;
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(nx, ny);
    ctx.stroke();
    px = nx;
    py = ny;
    w = Math.max(width * 0.45, w * (0.94 + random() * 0.05));
  }
  ctx.beginPath();
  ctx.ellipse(px, py + w * 0.4, w * 0.75, w * 1.05, 0, 0, Math.PI * 2);
  ctx.fill();
}

/**
 * Breaks a painted film up the way bark does: the ridges take the stain, the
 * cracks and the rain-washed patches let it go, and pooled edges dry darker.
 */
function weather(ctx: Ctx, w: number, h: number, random: () => number, wash: number): void {
  const image = ctx.getImageData(0, 0, w, h);
  const d = image.data;
  const fine = valueNoise(random, 5);
  const ridges = valueNoise(random, 19);
  const broad = valueNoise(random, 70);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const i = (x + y * w) * 4;
      if (d[i + 3] === 0) continue;
      const n = fine(x, y) * 0.45 + ridges(x * 0.6, y * 1.6) * 0.55;
      const keep = Math.min(
        1,
        Math.max(0, 0.85 + (n - 0.5) * 1.8 - wash * (broad(x, y) - 0.3) * 0.8),
      );
      d[i + 3] = Math.round(d[i + 3] * keep);
      const dark = 0.75 + 0.45 * broad(x + 300, y);
      d[i] = Math.min(255, d[i] * dark);
      d[i + 1] = Math.min(255, d[i + 1] * dark);
      d[i + 2] = Math.min(255, d[i + 2] * dark);
    }
  ctx.putImageData(image, 0, 0);
}

/**
 * Blood on a trunk (w × h, twice as tall as wide): a hand pressed to the bark
 * and dragged down it, or a smear from higher up, with the rain drawing the
 * blood down in thin runs that end in beads.
 */
export function paintBlood(
  ctx: Ctx,
  w: number,
  h: number,
  kind: "hand" | "drips",
  random: () => number,
): void {
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = ctx.strokeStyle = "rgba(132, 11, 7, 0.95)";
  const cx = w * 0.5,
    top = h * 0.16;
  let runsFrom: number;
  if (kind === "hand") {
    // The hand slid as it fell: the print, then its own fingers dragged below it.
    const lean = (random() - 0.5) * 0.3;
    for (let drag = 0; drag < 7; drag++) {
      const dy = drag * h * 0.035;
      ctx.globalAlpha = drag === 0 ? 1 : 0.55 - drag * 0.06;
      const palmY = top + h * 0.12 + dy;
      ctx.beginPath();
      ctx.ellipse(cx, palmY, w * 0.15, h * 0.085, lean, 0, Math.PI * 2);
      ctx.fill();
      const fingers: [number, number][] = [
        [-0.28, 0.19],
        [-0.09, 0.23],
        [0.09, 0.22],
        [0.27, 0.17],
      ];
      fingers.forEach(([a, len], k) => {
        const bx = cx + (k - 1.5) * w * 0.065;
        const angle = a + lean;
        capsule(
          ctx,
          bx,
          palmY - h * 0.05,
          bx + Math.sin(angle) * len * h * 0.5,
          palmY - h * 0.05 - Math.cos(angle) * len * h * 0.5,
          w * 0.062,
        );
      });
      if (drag === 0) capsule(ctx, cx + w * 0.13, palmY, cx + w * 0.27, palmY - h * 0.06, w * 0.07);
    }
    ctx.globalAlpha = 1;
    runsFrom = top + h * 0.38;
  } else {
    // A smear wiped across the bark at shoulder height, heavier at one end.
    for (let k = 0; k < 9; k++) {
      ctx.globalAlpha = 0.5 + random() * 0.4;
      const y = top + h * 0.06 + random() * h * 0.08;
      capsule(
        ctx,
        w * (0.15 + random() * 0.1),
        y,
        w * (0.62 + random() * 0.25),
        y + h * 0.04,
        w * (0.05 + random() * 0.06),
      );
    }
    ctx.globalAlpha = 1;
    runsFrom = top + h * 0.14;
  }
  // Rain-thinned runs: paler and more transparent the further they get.
  const runs = 5 + Math.floor(random() * 4);
  for (let k = 0; k < runs; k++) {
    const x = w * (0.22 + random() * 0.56);
    const length = h * (0.12 + random() * 0.5);
    ctx.fillStyle =
      ctx.strokeStyle = `rgba(${96 + random() * 30}, ${10 + random() * 6}, 7, ${0.55 + random() * 0.35})`;
    drip(ctx, random, x, runsFrom + random() * h * 0.05, length, w * (0.018 + random() * 0.03));
  }
  // Fine spatter flung round it.
  ctx.fillStyle = "rgba(92, 8, 5, 0.85)";
  for (let k = 0; k < 40; k++) {
    const a = random() * Math.PI * 2,
      r = w * (0.2 + random() * 0.32);
    ctx.beginPath();
    ctx.arc(
      cx + Math.cos(a) * r,
      top + h * 0.15 + Math.sin(a) * r * 0.8,
      1 + random() * 3.5,
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }
  weather(ctx, w, h, random, 0.6);
}

/** Old betel-juice spat at a tree's roots: rust-red, dried, half washed out. Not blood; it looks it. */
export function paintBetel(ctx: Ctx, w: number, h: number, random: () => number): void {
  ctx.clearRect(0, 0, w, h);
  for (let k = 0; k < 14; k++) {
    ctx.fillStyle = `rgba(${120 + random() * 30}, ${36 + random() * 14}, ${14 + random() * 8}, ${0.5 + random() * 0.4})`;
    const x = w * (0.2 + random() * 0.6),
      y = h * (0.25 + random() * 0.5);
    ctx.beginPath();
    ctx.ellipse(
      x,
      y,
      w * (0.03 + random() * 0.12),
      h * (0.02 + random() * 0.07),
      random() * 3,
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }
  for (let k = 0; k < 4; k++) {
    ctx.strokeStyle = ctx.fillStyle = "rgba(118, 38, 15, 0.5)";
    drip(ctx, random, w * (0.3 + random() * 0.4), h * 0.55, h * (0.1 + random() * 0.25), w * 0.02);
  }
  weather(ctx, w, h, random, 0.9);
}

/**
 * Cotton cloth wound round a spirit tree (w × h strip): its weave, the dirt
 * and mildew of a monsoon, folds, and a frayed lower edge. `colour` is sRGB.
 */
export function paintCloth(
  ctx: Ctx,
  w: number,
  h: number,
  colour: readonly [number, number, number],
  random: () => number,
): void {
  const image = ctx.createImageData(w, h);
  const d = image.data;
  const stain = valueNoise(random, 40);
  const mildew = valueNoise(random, 9);
  const fold = valueNoise(random, 26);
  const edge = valueNoise(random, 11);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const i = (x + y * w) * 4;
      const weave = 0.9 + 0.1 * ((x & 1) ^ (y & 1));
      const folds = 0.78 + 0.32 * Math.sin(x * 0.09 + fold(x, y) * 5) ** 2;
      const dirt = 1 - 0.55 * Math.max(0, stain(x, y) - 0.45) * 2;
      const grey = 1 - 0.35 * Math.max(0, mildew(x, y) - 0.6) * 2.5;
      const k = weave * folds * dirt * grey;
      d[i] = colour[0] * k;
      d[i + 1] = colour[1] * k;
      d[i + 2] = colour[2] * k;
      // The bottom frays into loose threads; small holes rot through.
      const frayed =
        y > h * (0.78 + 0.16 * edge(x, 0)) && (x + Math.floor(edge(x, y) * 6)) % 3 !== 0;
      const hole = mildew(x * 1.7, y * 1.7) > 0.86;
      d[i + 3] = frayed || hole ? 0 : 255;
    }
  ctx.putImageData(image, 0, 0);
}

/** Twisted cotton: plies running diagonally round the thread, light and dark. */
export function paintThread(ctx: Ctx, size: number, random: () => number): void {
  const image = ctx.createImageData(size, size);
  const d = image.data;
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) {
      const i = (x + y * size) * 4;
      const ply = 0.72 + 0.28 * Math.sin(((x + y * 0.8) / size) * Math.PI * 8) ** 2;
      const v = Math.round(255 * ply * (0.92 + random() * 0.08));
      d[i] = d[i + 1] = d[i + 2] = v;
      d[i + 3] = 255;
    }
  ctx.putImageData(image, 0, 0);
}
