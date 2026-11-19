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
// study of the dancer she dreamed of. The words are KHMER.diary* in ep1.mjs, where every
// Khmer string waits for review.

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

    // ---- A pencil study under the writing: the dancer of her dream, quick and light,
    // her head lolling to one side under a tall crown, an arm lifted with the nails long
    // like claws, the sampot gathered at the hip.
    ctx.strokeStyle = "rgba(70,70,74,0.42)";
    ctx.lineWidth = 1.3;
    const sx = PW + 360;
    const sy = Math.min(TOP + end * RULE_PX + 95, PH - 430);
    function stroke(points, wobble = 1.2, times = 2) {
      for (let t = 0; t < times; t++) {
        ctx.beginPath();
        points.forEach(([x, y], i) => {
          const p = [sx + x + r.normal(wobble), sy + y + r.normal(wobble)];
          if (i) ctx.lineTo(p[0], p[1]);
          else ctx.moveTo(p[0], p[1]);
        });
        ctx.stroke();
      }
    }
    // Neck, shoulders, torso.
    stroke([
      [-6, 40],
      [-4, 52],
      [-34, 62],
      [-30, 120],
      [-22, 170],
      [-30, 200],
    ]);
    stroke([
      [6, 40],
      [4, 52],
      [36, 60],
      [30, 118],
      [20, 170],
      [28, 200],
    ]);
    // The head, fallen to her right, and the crown's spire rising crooked from it.
    const head = [];
    for (let k = 0; k <= 16; k++) {
      const a = (k / 16) * Math.PI * 2;
      const [ex, ey] = [12 * Math.cos(a), 16 * Math.sin(a)];
      head.push([
        -16 + ex * Math.cos(-0.4) - ey * Math.sin(-0.4),
        22 + ex * Math.sin(-0.4) + ey * Math.cos(-0.4),
      ]);
    }
    stroke(head, 0.8, 2);
    stroke(
      [
        [-28, 12],
        [-34, -10],
        [-40, -34],
        [-44, -62],
      ],
      1,
      2,
    );
    stroke(
      [
        [-8, 4],
        [-20, -14],
        [-32, -38],
        [-44, -62],
      ],
      1,
      2,
    );
    for (let k = 0; k < 4; k++)
      stroke(
        [
          [-30 + k * 2, 0 - k * 12],
          [-16 + k * 1, -2 - k * 12],
        ],
        0.6,
        1,
      );
    // The long nails of the lifted hand, curled like claws.
    stroke(
      [
        [104, -10],
        [116, -22],
        [126, -18],
        [128, -6],
      ],
      0.7,
      1,
    );
    stroke(
      [
        [104, -10],
        [118, -14],
        [127, -4],
        [125, 6],
      ],
      0.7,
      1,
    );
    stroke(
      [
        [102, -6],
        [112, -2],
        [118, 8],
        [114, 16],
      ],
      0.7,
      1,
    );
    // The raised arm, ending at the wrist.
    stroke([
      [36, 60],
      [74, 38],
      [96, 2],
      [104, -10],
    ]);
    // The other arm down and out.
    stroke([
      [-34, 62],
      [-66, 104],
      [-84, 146],
    ]);
    // The sampot, gathered and falling in folds to the ankles; the feet.
    stroke([
      [-30, 200],
      [-46, 300],
      [-50, 380],
      [-20, 388],
    ]);
    stroke([
      [28, 200],
      [44, 296],
      [48, 380],
      [16, 388],
    ]);
    stroke(
      [
        [-6, 206],
        [-10, 290],
        [-8, 372],
      ],
      1,
      1,
    );
    stroke(
      [
        [10, 206],
        [16, 286],
        [18, 370],
      ],
      1,
      1,
    );
    stroke(
      [
        [-20, 388],
        [-34, 404],
        [-8, 406],
      ],
      1,
      1,
    );
    stroke(
      [
        [16, 388],
        [30, 402],
        [6, 405],
      ],
      1,
      1,
    );
    // The sbai over one shoulder.
    stroke(
      [
        [-30, 60],
        [10, 130],
        [24, 176],
      ],
      1,
      1,
    );
    // Shading hatched down one side.
    ctx.lineWidth = 0.9;
    for (let k = 0; k < 14; k++) {
      const y = 210 + k * 12;
      stroke(
        [
          [30 + k * 0.6, y],
          [42 + k * 0.6, y - 10],
        ],
        0.6,
        1,
      );
    }

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
