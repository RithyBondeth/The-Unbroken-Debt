// The Ep1 studio's printed matter: real public-domain prints of 1932 or earlier
// (art-source/library/archive/, listed with sources and licences in
// art-source/library/polyhaven.json), aged as paper that has hung on a damp
// Phnom Penh wall for years. Clean, not ruined: toned, foxed a little, folded
// where posters were posted folded, pin holes with rust where they are tacked.
// Layout (shared with tools/areas/ep1_area_studio.py): tools/areas/studio_prints.json.
// The user's own posters (November 2026, art-source/library/posters/) are aged the same
// way: printed posters as posters, photographs as photographic prints, the hand-painted
// shop signs as painted boards.

/* global rng, clamp, lerp, smooth, rgb, noise, document, Image */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { canvasPage } from "./village.mjs";

const ARCHIVE = join("art-source", "library", "archive");
const LAYOUT = JSON.parse(readFileSync(join("tools", "areas", "studio_prints.json"), "utf8"));

/**
 * Paints every print of one atlas. Each kind is a different paper:
 * poster — a colour lithograph posted folded in four, full bleed;
 * magazine — a newsprint colour supplement, yellowed more, folded down the middle;
 * mounted — a photographic reproduction on a grey-brown card mount;
 * postcard — a collotype card with a narrow cream border, pinned at the top;
 * photo — a colour photographic print with a white border, pinned at the top corners;
 * board — a hand-painted signboard, its paint chipped and grimy, nailed at the corners.
 */
function paintPrints(ctx, W, H, data) {
  const imgs = data.items.map((item) => {
    const img = new Image();
    img.src = item.src;
    return img;
  });
  Promise.all(
    imgs.map(
      (img) =>
        new Promise((done) =>
          img.complete ? done() : ((img.onload = done), (img.onerror = done)),
        ),
    ),
  ).then(() => {
    ctx.fillStyle = "#3a2e22";
    ctx.fillRect(0, 0, W, H);
    data.items.forEach((item, k) => paintOne(item, imgs[k]));
    document.title = "done";
  });

  function paintOne(item, img) {
    const [x, y, w, h] = item.rect;
    const r = rng(item.seed);
    const kind = item.kind;
    const paper = {
      poster: [232, 220, 192],
      magazine: [226, 210, 172],
      mounted: [196, 184, 156],
      postcard: [222, 210, 182],
      photo: [236, 232, 220],
      board: [92, 76, 58],
    }[kind];
    ctx.fillStyle = rgb(paper);
    ctx.fillRect(x, y, w, h);

    // Where the image goes on the paper.
    const margin = {
      poster: 0.0,
      magazine: 0.0,
      mounted: 0.085,
      postcard: 0.035,
      photo: 0.04,
      board: 0.0,
    }[kind];
    const mx = Math.round(w * margin),
      my = Math.round(kind === "mounted" ? h * margin * 0.9 : h * margin);
    const ix = x + mx,
      iy = y + my,
      iw = w - 2 * mx,
      ih = h - 2 * my - (kind === "mounted" ? Math.round(h * 0.05) : 0);
    // Cover-fit the source into the image area; `crop` ([left, top, right, bottom], fractions)
    // first trims what is not the picture (the archive's caption band).
    const [c0, c1, c2, c3] = item.crop ?? [0, 0, 0, 0];
    const cw = img.width * (1 - c0 - c2),
      ch = img.height * (1 - c1 - c3);
    const s = Math.max(iw / cw, ih / ch);
    const sw = iw / s,
      sh = ih / s;
    const sx = img.width * c0 + (cw - sw) / 2,
      sy = img.height * c1 + (ch - sh) / 2;
    ctx.save();
    ctx.imageSmoothingQuality = "high";
    // Low-resolution sources (the 1906 poster is 429 px wide) are enlarged softly;
    // the paper grain added below hides the softness at arm's length.
    ctx.drawImage(img, sx, sy, sw, sh, ix, iy, iw, ih);
    ctx.restore();

    // A thin plate mark round photographic reproductions on their mount.
    if (kind === "mounted") {
      ctx.strokeStyle = "rgba(70,58,40,0.35)";
      ctx.lineWidth = 2;
      ctx.strokeRect(ix - 9, iy - 9, iw + 18, ih + 18);
      ctx.strokeStyle = "rgba(255,248,230,0.25)";
      ctx.lineWidth = 1;
      ctx.strokeRect(ix - 7, iy - 7, iw + 14, ih + 14);
    }

    // Age the whole sheet, pixel by pixel: printing inks fade towards the paper,
    // the paper yellows and darkens towards its edges, with fine grain and blotches.
    const img2 = ctx.getImageData(x, y, w, h),
      p = img2.data;
    const grain = noise(w, h, 1.4, item.seed, 2);
    const blotch = noise(w, h, Math.max(w, h) / 6, item.seed + 7, 4);
    const fade = {
      poster: 0.16,
      magazine: 0.22,
      mounted: 0.12,
      postcard: 0.1,
      photo: 0.14,
      board: 0.2,
    }[kind];
    const yellow = {
      poster: 0.18,
      magazine: 0.3,
      mounted: 0.12,
      postcard: 0.16,
      photo: 0.15,
      board: 0.24,
    }[kind];
    const tone = [214, 190, 140];
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const q = (j * w + i) * 4;
        let c = [p[q], p[q + 1], p[q + 2]];
        // Fade: inks lose saturation and contrast, blacks lift.
        const L = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2];
        c = c.map((v) => lerp(v, L, fade * 0.8));
        c = c.map((v) => lerp(v, 128 + (v - 128) * 0.9, fade) + 10 * fade);
        // Yellowing multiplies towards a tea tone, more at the edges and in blotches.
        const ex = Math.min(i, w - 1 - i) / w,
          ey = Math.min(j, h - 1 - j) / h;
        const edge = 1 - smooth(0.0, 0.06, Math.min(ex, ey));
        const t = clamp(yellow * (0.7 + 0.6 * blotch[j * w + i]) + edge * 0.35);
        c = c.map((v, n) => lerp(v, (v * tone[n]) / 255, t));
        // Paper grain and a slight darkening right at the cut edge (handling).
        const g = 1 + (grain[j * w + i] - 0.5) * 0.09 - edge * 0.12;
        p[q] = clamp((c[0] * g) / 255) * 255;
        p[q + 1] = clamp((c[1] * g) / 255) * 255;
        p[q + 2] = clamp((c[2] * g) / 255) * 255;
      }
    }
    ctx.putImageData(img2, x, y);

    // Foxing: small rust-brown spots, a few with a darker core.
    const spots = { poster: 70, magazine: 55, mounted: 40, postcard: 25, photo: 18, board: 0 }[
      kind
    ];
    for (let n = 0; n < spots; n++) {
      const fx = x + r(0.02, 0.98) * w,
        fy = y + r(0.02, 0.98) * h;
      const rad = r(0.6, 3.2) * (r() < 0.1 ? 3 : 1);
      const grad = ctx.createRadialGradient(fx, fy, 0, fx, fy, rad * 2.2);
      grad.addColorStop(0, `rgba(120,72,30,${r(0.25, 0.55)})`);
      grad.addColorStop(0.5, `rgba(140,96,48,${r(0.1, 0.25)})`);
      grad.addColorStop(1, "rgba(140,96,48,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(fx - rad * 3, fy - rad * 3, rad * 6, rad * 6);
    }

    // Fold lines: a soft valley with a lit ridge on one side and a grey crease line.
    const fold = (x0, y0, x1, y1, depth) => {
      ctx.save();
      ctx.lineCap = "round";
      ctx.strokeStyle = `rgba(60,48,32,${0.18 * depth})`;
      ctx.lineWidth = 7;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
      ctx.strokeStyle = `rgba(255,250,236,${0.22 * depth})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x0 + 3, y0 + 3);
      ctx.lineTo(x1 + 3, y1 + 3);
      ctx.stroke();
      ctx.strokeStyle = `rgba(40,30,20,${0.3 * depth})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
      ctx.restore();
    };
    if (kind === "poster") {
      fold(x + w / 2 + r(-3, 3), y, x + w / 2 + r(-3, 3), y + h, 1);
      fold(x, y + h / 2 + r(-3, 3), x + w, y + h / 2 + r(-3, 3), 0.9);
    }
    if (kind === "magazine") fold(x + w / 2 + r(-2, 2), y, x + w / 2 + r(-2, 2), y + h, 1.2);
    if (kind === "postcard" && r() < 0.6)
      fold(x + w * r(0.75, 0.9), y, x + w, y + h * r(0.1, 0.25), 0.7);
    // A photographic print bent once at a corner where it was handled.
    if (kind === "photo") fold(x + w * r(0.78, 0.9), y + h, x + w, y + h * r(0.8, 0.9), 0.6);

    // Tack holes with a rust halo: four corners for posters, one at the top for cards.
    const hole = (hx, hy) => {
      const grad = ctx.createRadialGradient(hx, hy, 0, hx, hy, 11);
      grad.addColorStop(0, "rgba(70,40,18,0.65)");
      grad.addColorStop(0.35, "rgba(120,70,30,0.35)");
      grad.addColorStop(1, "rgba(120,70,30,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(hx - 12, hy - 12, 24, 24);
      ctx.fillStyle = "rgba(25,18,12,0.9)";
      ctx.beginPath();
      ctx.arc(hx, hy, 2.2, 0, Math.PI * 2);
      ctx.fill();
    };
    if (kind === "poster" || kind === "magazine")
      for (const [hx, hy] of [
        [x + 14, y + 14],
        [x + w - 14, y + 14],
        [x + 14, y + h - 14],
        [x + w - 14, y + h - 14],
      ])
        hole(hx + r(-3, 3), hy + r(-3, 3));
    if (kind === "postcard") hole(x + w / 2 + r(-8, 8), y + 16);
    if (kind === "photo")
      for (const hx of [x + 14, x + w - 14]) hole(hx + r(-3, 3), y + 14 + r(-3, 3));
    if (kind === "board") paintedBoard(ctx, x, y, w, h, r);

    // A water tide-mark low on the larger sheets: rain once came under the doors.
    if (kind === "poster" || kind === "magazine") {
      const ty = y + h * r(0.86, 0.93);
      ctx.save();
      ctx.beginPath();
      ctx.rect(x, y, w, h);
      ctx.clip();
      const tide = ctx.createLinearGradient(0, ty - 30, 0, y + h);
      tide.addColorStop(0, "rgba(150,110,60,0)");
      tide.addColorStop(0.12, "rgba(130,90,45,0.32)");
      tide.addColorStop(0.18, "rgba(150,110,60,0.12)");
      tide.addColorStop(1, "rgba(150,110,60,0.2)");
      ctx.fillStyle = tide;
      ctx.beginPath();
      ctx.moveTo(x, ty);
      for (let i = 0; i <= 24; i++)
        ctx.lineTo(x + (w * i) / 24, ty + Math.sin(i * 1.7 + item.seed) * 7);
      ctx.lineTo(x + w, y + h);
      ctx.lineTo(x, y + h);
      ctx.fill();
      ctx.restore();
    }
  }
}

/**
 * A signboard's wear: paint chipped off in flakes down to the dark wood (more at the
 * edges and the bottom, where it was knocked), grime run down from the top, and the
 * nails at the corners bleeding rust.
 */
function paintedBoard(ctx, x, y, w, h, r) {
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, w, h);
  ctx.clip();
  for (let n = 0; n < 70; n++) {
    const edge = r() < 0.6;
    const cx = edge
      ? r() < 0.5
        ? x + r(0, 0.08) * w * (r() < 0.5 ? 1 : -1) + (r() < 0.5 ? 0 : w)
        : x + r(0, 1) * w
      : x + r(0.05, 0.95) * w;
    const cy = edge && r() < 0.6 ? y + h - r(0, 0.1) * h : y + r(0.03, 0.97) * h;
    // Knocks chip the edges; the painted face keeps only small flakes.
    const size = edge ? r(1.5, 9) * (r() < 0.12 ? 2.5 : 1) : r(1, 3.5);
    ctx.fillStyle = `rgba(${Math.round(r(38, 62))},${Math.round(r(28, 44))},${Math.round(r(18, 30))},${r(0.75, 0.95)})`;
    ctx.beginPath();
    const k = 7 + Math.floor(r(0, 5));
    for (let i = 0; i < k; i++) {
      const a = (i / k) * Math.PI * 2;
      const rr = size * r(0.45, 1.25);
      ctx.lineTo(cx + Math.cos(a) * rr * 1.4, cy + Math.sin(a) * rr);
    }
    ctx.closePath();
    ctx.fill();
  }
  // Grime run down from the top edge in thin streaks.
  for (let n = 0; n < 26; n++) {
    const sx = x + r(0, 1) * w;
    const len = h * r(0.08, 0.45);
    const grad = ctx.createLinearGradient(0, y, 0, y + len);
    grad.addColorStop(0, `rgba(48,36,22,${r(0.12, 0.28)})`);
    grad.addColorStop(1, "rgba(48,36,22,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(sx, y, r(2, 9), len);
  }
  // Rust from the nails, run down below each.
  for (const [nx, ny] of [
    [x + 16, y + 16],
    [x + w - 16, y + 16],
    [x + 16, y + h - 16],
    [x + w - 16, y + h - 16],
  ]) {
    const grad = ctx.createLinearGradient(0, ny, 0, ny + r(30, 70));
    grad.addColorStop(0, "rgba(110,52,20,0.55)");
    grad.addColorStop(1, "rgba(110,52,20,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(nx - 3, ny, 6, 70);
    ctx.fillStyle = "rgba(30,22,16,0.95)";
    ctx.beginPath();
    ctx.arc(nx, ny, 3.2, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function atlas(key) {
  const spec = LAYOUT.atlases[key];
  const items = Object.entries(spec.items).map(([id, item]) => ({
    ...item,
    id,
    // An item may name its own file (`path`, under art-source/library/) instead of the atlas's folder.
    src: `data:image/jpeg;base64,${readFileSync(item.path ? join("art-source", "library", item.path) : join(spec.folder ? join("art-source", "library", spec.folder) : ARCHIVE, `${id}.jpg`)).toString("base64")}`,
  }));
  const [w, h] = spec.size;
  return {
    name: `studio_${key}`,
    file: spec.file,
    size: spec.size,
    draw: () => canvasPage(w, h, paintPrints, { items }, [paintedBoard]),
  };
}

export const studioPrintTextures = [
  atlas("posters"),
  atlas("cards"),
  atlas("colour"),
  atlas("nineties_p"),
  atlas("nineties_l"),
];
