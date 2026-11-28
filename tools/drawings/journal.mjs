// Sora's diary, open on her writing desk in the Ep1 studio (November 2026): the
// studio's save point (tools/areas/ep1_area_studio.py, open_journal). One spread, two
// pages of 720 x 1000 px side by side (about 0.2 mm a pixel on the 15.2 x 21.5 cm page).
//
// Ruled paper gone the colour of weak tea, foxed, darker into the gutter. Her entry for
// tonight in Khmer (the user, November 19), handwritten: the Freehand face slanted,
// jostled cluster by cluster and its strokes wobbled and weighted like a dip pen's, in
// iron-gall ink:
// the left-hand page full, the right-hand page stopping mid-sentence at eight o'clock,
// paler where the pen ran dry and dark again after each dip. Under it, a quick pencil
// study of the shadow she saw on the wall in the lightning (the studio's shadow scare).
// The words are KHMER.diary* in ep1.mjs, where every Khmer string waits for review.

/* global rng, clamp, noise, document */

import { canvasPage } from "./village.mjs";

const PAGE = [720, 1000];
// Wide rules, as in a Khmer exercise book: room for the vowels above and the subscripts below.
const RULE = 40;
const TOP_RULE = 150;

function paintJournal(ctx, W, H, data) {
  const [PW, PH] = data.page;
  const TOP = data.top;
  const RULE_PX = data.rule;
  const SIZE = data.size;
  const r = rng(1932);

  // ---- The paper.
  ctx.fillStyle = "rgb(232,221,195)";
  ctx.fillRect(0, 0, W, H);
  for (let side = 0; side < 2; side++) {
    const ox = side * PW;
    // The rules, the red margin.
    ctx.strokeStyle = "rgba(96,118,150,0.3)";
    ctx.lineWidth = 1.2;
    for (let y = TOP; y < PH - 50; y += RULE_PX) {
      ctx.beginPath();
      ctx.moveTo(ox + 30, y + 0.5);
      ctx.lineTo(ox + PW - 30, y + 0.5);
      ctx.stroke();
    }
    ctx.strokeStyle = "rgba(168,72,58,0.34)";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(ox + 96, 40);
    ctx.lineTo(ox + 96, PH - 40);
    ctx.stroke();
  }

  document.fonts.load(`${SIZE}px Freehand`).then(() => {
    // ---- Her hand. The words are wrapped where Khmer words end (no spaces between
    // them) and written a cluster at a time onto a layer of their own: slanted forward
    // as everyday Khmer handwriting is (aksar chriang), each cluster a little off the
    // line, a little turned, a little larger or smaller, the lines drifting. The layer's
    // red channel carries how much ink was on the nib; it fades over a few words and
    // comes back after each dip.
    const words = new Intl.Segmenter("km", { granularity: "word" });
    // One Khmer cluster: a consonant (or independent vowel) with its subscripts, vowels
    // and signs (the browser's grapheme breaks would split a subscript from its base).
    const CLUSTER =
      /[\u1780-\u17B3](?:\u17D2[\u1780-\u17B3]|[\u17B4-\u17D1\u17D3\u17DD])*|[\s\S]/gu;
    const SLANT = -0.24;
    const layer = document.createElement("canvas");
    layer.width = W;
    layer.height = H;
    const lc = layer.getContext("2d", { willReadFrequently: true });
    lc.font = `${SIZE}px Freehand`;
    lc.textBaseline = "alphabetic";
    lc.filter = "blur(0.55px)";
    let load = 1;
    let sinceDip = 0;
    let lastEnd = [0, 0];
    function cluster(text, x, base) {
      const k = 1 + r.normal(0.04);
      lc.save();
      lc.setTransform(k, 0, (SLANT + r.normal(0.05)) * k, k, x, base + r.normal(0.9));
      lc.rotate(r.normal(0.02));
      lc.fillStyle = `rgb(${Math.round(255 * Math.max(0, load + r.normal(0.04)))},0,0)`;
      lc.fillText(text, 0, 0);
      lc.restore();
      return lc.measureText(text).width * k;
    }
    function write(paragraphs, ox, firstLine) {
      const left = ox + 106;
      const right = ox + PW - 46;
      let line = firstLine;
      let tilt = r.normal(0.006);
      let phase = r() * 6;
      const baseAt = (x) =>
        TOP + line * RULE_PX - 8 + (x - left) * tilt + 1.3 * Math.sin((x - left) / 95 + phase);
      for (const paragraph of paragraphs) {
        let x = left + 34 + r() * 6;
        for (const { segment } of words.segment(paragraph)) {
          if (/^\s+$/.test(segment)) {
            x += SIZE * (0.28 + r() * 0.12);
            continue;
          }
          if (x + lc.measureText(segment).width > right && x > left) {
            line++;
            tilt = r.normal(0.006);
            phase = r() * 6;
            x = left + r() * 5;
          }
          for (const part of segment.match(CLUSTER) ?? []) {
            x += cluster(part, x, baseAt(x)) * (0.95 + r() * 0.07);
            load = Math.max(0.2, load - 0.006);
          }
          lastEnd = [x, baseAt(x)];
          x += 1.5 + r() * 2;
          sinceDip++;
          load = Math.max(0.25, 1 - sinceDip * 0.05);
          if (r() < 0.05 || load <= 0.25) {
            sinceDip = 0;
            load = 1;
          }
        }
        line++;
      }
      return line;
    }
    // The place and the year at the head of the left-hand page, then the entry.
    let hx = PW - 80 - lc.measureText(data.heading).width;
    for (const part of data.heading.match(CLUSTER) ?? []) hx += cluster(part, hx, TOP - 14);
    write(data.left, 0, 1);
    const end = write(data.right, PW, 1);

    // The layer onto the page as ink: the strokes wobble (no pen draws a font's clean
    // curve), thicken and thin with the pressure, iron-gall blue-black where the nib was
    // full, browner where it ran dry.
    {
      const src = lc.getImageData(0, 0, W, H).data;
      const page = ctx.getImageData(0, 0, W, H);
      const dst = page.data;
      const wx = noise(W, H, 6, 21, 2);
      const wy = noise(W, H, 6, 22, 2);
      const press = noise(W, H, 24, 23, 3);
      const at = (x, y, c) => {
        const x0 = Math.floor(x);
        const y0 = Math.floor(y);
        if (x0 < 0 || y0 < 0 || x0 >= W - 1 || y0 >= H - 1) return 0;
        const fx = x - x0;
        const fy = y - y0;
        const i = (y0 * W + x0) * 4 + c;
        return (
          (src[i] * (1 - fx) + src[i + 4] * fx) * (1 - fy) +
          (src[i + W * 4] * (1 - fx) + src[i + W * 4 + 4] * fx) * fy
        );
      };
      for (let y = 0; y < H; y++)
        for (let x = 0; x < W; x++) {
          const n = y * W + x;
          const sx = x + (wx[n] - 0.5) * 3.6;
          const sy = y + (wy[n] - 0.5) * 3.6;
          const a = at(sx, sy, 3) / 255;
          if (a < 0.02) continue;
          const t = 0.22 + 0.4 * press[n];
          const cover = clamp((a - (t - 0.2)) / 0.4);
          if (cover <= 0) continue;
          const fullness = clamp(at(sx, sy, 0) / Math.max(1, at(sx, sy, 3)));
          const ink = [
            24 + (1 - fullness) * 78,
            20 + (1 - fullness) * 52,
            46 - (1 - fullness) * 10,
          ];
          const o = cover * (0.72 + 0.26 * fullness);
          const i = n * 4;
          for (let c = 0; c < 3; c++) dst[i + c] = dst[i + c] * (1 - o) + ink[c] * o;
        }
      ctx.putImageData(page, 0, 0);
    }
    // A blot where the pen stopped, mid-sentence, when the telephone rang.
    ctx.fillStyle = "rgba(28,22,40,0.8)";
    ctx.beginPath();
    ctx.ellipse(lastEnd[0] + 12, lastEnd[1] - 3, 5, 4, 0.4, 0, Math.PI * 2);
    ctx.fill();

    // ---- A pencil study under the writing: the shadow she saw on the wall beside the
    // door frame in the lightning, a woman with her hair hanging over her face, one arm
    // reaching, the long fingers spread; hatched dark, the outline gone over twice.
    const sx = PW + 400;
    // Below the last line, small: about 300 px high.
    const sy = Math.min(Math.max(TOP + end * RULE_PX + 110, 660), PH - 290);
    const S = 0.68;
    const at = ([x, y]) => [sx + x * S, sy + y * S];
    function stroke(points, wobble = 1.2, times = 2) {
      for (let t = 0; t < times; t++) {
        ctx.beginPath();
        points.forEach((q, i) => {
          const [px, py] = at(q);
          const p = [px + r.normal(wobble), py + r.normal(wobble)];
          if (i) ctx.lineTo(p[0], p[1]);
          else ctx.moveTo(p[0], p[1]);
        });
        ctx.stroke();
      }
    }
    ctx.strokeStyle = "rgba(70,70,74,0.42)";
    ctx.lineWidth = 1.2;
    // The door frame beside it, a few ruled lines.
    stroke(
      [
        [-190, -70],
        [-188, 400],
      ],
      0.6,
      2,
    );
    stroke(
      [
        [-172, -68],
        [-170, 400],
      ],
      0.6,
      1,
    );
    stroke(
      [
        [-190, -70],
        [-110, -73],
      ],
      0.6,
      1,
    );
    // Her outline: the bowed head, the hair hanging straight down over the face and
    // past the shoulders, one arm out towards the door frame, the dress to the floor.
    const outline = [
      [0, -40],
      [12, -38],
      [20, -28],
      [24, -10],
      [26, 22],
      [30, 40],
      [44, 48],
      [50, 92],
      [52, 140],
      [46, 200],
      [52, 300],
      [60, 382],
      [40, 394],
      [-34, 394],
      [-46, 380],
      [-40, 300],
      [-34, 200],
      [-30, 150],
      [-32, 84],
      [-62, 84],
      [-96, 82],
      [-124, 78],
      [-128, 68],
      [-120, 62],
      [-84, 60],
      [-50, 52],
      [-28, 36],
      [-24, 4],
      [-22, -14],
      [-18, -28],
      [-10, -37],
    ];
    ctx.save();
    ctx.beginPath();
    outline.forEach((q, i) => {
      const [x, y] = at(q);
      if (i) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    });
    ctx.closePath();
    ctx.clip();
    // Hatched dark: two layers of quick diagonal strokes, the second across the first.
    ctx.lineWidth = 1.0;
    for (const [lean, gap, alpha] of [
      [0.55, 3.4, 0.38],
      [-0.4, 4.6, 0.3],
    ])
      for (let k = -60; k < 160; k++) {
        const y = -90 + k * gap;
        ctx.strokeStyle = `rgba(58,58,64,${alpha})`;
        ctx.beginPath();
        ctx.moveTo(sx - 150 + r.normal(1.2), sy + y + r.normal(1.2));
        ctx.lineTo(sx + 60 + r.normal(1.2), sy + y - 210 * lean + r.normal(1.2));
        ctx.stroke();
      }
    ctx.restore();
    ctx.strokeStyle = "rgba(56,56,62,0.55)";
    ctx.lineWidth = 1.3;
    stroke([...outline, outline[0]], 0.9, 2);
    // The long fingers, spread, reaching for the door frame.
    ctx.lineWidth = 1.1;
    for (const [dx, dy] of [
      [-34, -14],
      [-40, -5],
      [-40, 4],
      [-34, 12],
      [-20, 18],
    ])
      stroke(
        [
          [-124, 70],
          [-124 + dx * 0.5, 70 + dy * 0.5],
          [-124 + dx, 70 + dy],
        ],
        0.5,
        1,
      );
    // Strands of the hair, darker, falling over the face.
    ctx.strokeStyle = "rgba(40,40,46,0.55)";
    for (let k = 0; k < 10; k++)
      stroke(
        [
          [-16 + k * 3.6, -34],
          [-20 + k * 4.2, 30],
          [-22 + k * 4.6, 96 + (k % 3) * 10],
        ],
        1,
        1,
      );

    // ---- Age: grain, blotches, foxing, the gutter in shadow, the edges darkened.
    const img = ctx.getImageData(0, 0, W, H);
    const p = img.data;
    const grain = noise(W, H, 1.3, 7, 2);
    const blotch = noise(W, H, 160, 11, 4);
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++) {
        const i = (y * W + x) * 4;
        const toGutter = x < PW ? PW - x : x - PW;
        const gutter = 1 - 0.32 * Math.exp(-toGutter / 38);
        const edgeX = Math.min(x, W - 1 - x);
        const edge = 1 - 0.16 * Math.exp(-Math.min(edgeX, y, H - 1 - y) / 26);
        const b = blotch[y * W + x];
        const tone = (0.9 + 0.16 * b) * gutter * edge * (0.96 + 0.08 * grain[y * W + x]);
        p[i] = clamp(p[i] * tone, 0, 255);
        p[i + 1] = clamp(p[i + 1] * tone * (0.985 - 0.02 * b), 0, 255);
        p[i + 2] = clamp(p[i + 2] * tone * (0.94 - 0.06 * b), 0, 255);
      }
    ctx.putImageData(img, 0, 0);
    // Foxing: small rust-brown spots, more towards the edges.
    for (let k = 0; k < 70; k++) {
      const x = r() * W;
      const y = r() * H;
      const rad = 1 + r() * 4;
      ctx.fillStyle = `rgba(150,96,52,${0.08 + r() * 0.18})`;
      ctx.beginPath();
      ctx.arc(x, y, rad, 0, Math.PI * 2);
      ctx.fill();
    }
    document.title = "done";
  });
}

/** The diary spread; `text` is { heading, left: [paragraphs], right: [paragraphs] } in Khmer. */
export function journalTextures(text) {
  return [
    {
      name: "studio_journal",
      file: "T_studio_journal_BC",
      size: [PAGE[0] * 2, PAGE[1]],
      draw: () =>
        canvasPage(PAGE[0] * 2, PAGE[1], paintJournal, {
          page: PAGE,
          rule: RULE,
          top: TOP_RULE,
          size: 28,
          ...text,
        }),
    },
  ];
}
