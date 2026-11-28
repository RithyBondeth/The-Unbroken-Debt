// Real public-domain 1872-1932 vintage book covers for Sora's Phnom Penh studio
// (art-source/library/books/, layout in tools/areas/studio_books.json).
// Packs 32 distinct books into two 2048x2048 atlases: each cell holds the real
// aged front cover, a color-matched titled spine with raised bands and shelf wear,
// and a matching cloth/leather back board.

/* global rng, clamp, lerp, smooth, noise, document, Image */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { canvasPage } from "./village.mjs";

const BOOKS = join("art-source", "library", "books");
const LAYOUT = JSON.parse(readFileSync(join("tools", "areas", "studio_books.json"), "utf8"));

function paintBooks(ctx, W, H, data) {
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
    ctx.fillStyle = "#2b231b";
    ctx.fillRect(0, 0, W, H);
    data.items.forEach((item, k) => paintOne(item, imgs[k], k));
    document.title = "done";
  });

  function paintOne(item, img, idx) {
    const r = rng(item.seed);
    const [fx, fy, fw, fh] = item.front;
    const [sx, sy, sw, sh] = item.spine;
    const [bx, by, bw, bh] = item.back;

    // --------------------------------------------------- 1. REAL FRONT COVER
    ctx.fillStyle = item.spineBg;
    ctx.fillRect(fx, fy, fw, fh);
    const [c0, c1, c2, c3] = item.crop ?? [0, 0, 0, 0];
    const cw = img.width * (1 - c0 - c2);
    const ch = img.height * (1 - c1 - c3);
    const s = Math.max(fw / cw, fh / ch);
    const srcW = fw / s;
    const srcH = fh / s;
    const srcX = img.width * c0 + (cw - srcW) / 2;
    const srcY = img.height * c1 + (ch - srcH) / 2;
    ctx.save();
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, srcX, srcY, srcW, srcH, fx, fy, fw, fh);
    ctx.restore();

    // Gentle tropical-humidity ageing, cloth weave & edge wear (keeps cover art crisp!)
    const imgData = ctx.getImageData(fx, fy, fw, fh);
    const p = imgData.data;
    const grain = noise(fw, fh, 1.5, item.seed + 1, 2);
    const blotch = noise(fw, fh, 64, item.seed + 13, 3);
    const tone = [230, 212, 174];
    for (let j = 0; j < fh; j++) {
      const weaveY = (j & 1) === 0 ? 1.012 : 0.988;
      for (let i = 0; i < fw; i++) {
        const q = (j * fw + i) * 4;
        const weave = weaveY * ((i & 1) === 0 ? 1.01 : 0.99);
        const ex = Math.min(i, fw - 1 - i) / fw;
        const ey = Math.min(j, fh - 1 - j) / fh;
        const edge = 1 - smooth(0.0, 0.05, Math.min(ex, ey));
        const t = clamp(0.11 * (0.7 + 0.6 * blotch[j * fw + i]) + edge * 0.24);
        const g = (1 + (grain[j * fw + i] - 0.5) * 0.06 - edge * 0.14) * weave;
        for (let c = 0; c < 3; c++) {
          const aged = lerp(p[q + c], (p[q + c] * tone[c]) / 255, t);
          p[q + c] = clamp((aged * g) / 255) * 255;
        }
      }
    }
    ctx.putImageData(imgData, fx, fy);

    // Subtle hinge groove along left edge of the front cover (where the board flexes)
    const groove = ctx.createLinearGradient(fx, 0, fx + 18, 0);
    groove.addColorStop(0, "rgba(18,12,8,0.42)");
    groove.addColorStop(0.35, "rgba(255,244,218,0.12)");
    groove.addColorStop(0.55, "rgba(18,12,8,0.22)");
    groove.addColorStop(1, "rgba(18,12,8,0)");
    ctx.fillStyle = groove;
    ctx.fillRect(fx, fy, 18, fh);

    // Subtle worn corners
    for (const [cx, cy] of [
      [fx + fw - 4, fy + 4],
      [fx + fw - 4, fy + fh - 4],
    ]) {
      const rad = ctx.createRadialGradient(cx, cy, 1, cx, cy, 18);
      rad.addColorStop(0, "rgba(205,186,148,0.34)");
      rad.addColorStop(1, "rgba(205,186,148,0)");
      ctx.fillStyle = rad;
      ctx.fillRect(cx - 18, cy - 18, 36, 36);
    }

    // --------------------------------------------------- 2. MATCHING TITLED SPINE
    ctx.save();
    ctx.beginPath();
    ctx.rect(sx, sy, sw, sh);
    ctx.clip();
    ctx.fillStyle = item.spineBg;
    ctx.fillRect(sx, sy, sw, sh);

    // Rounded spine shading (darker at hinges, softly lit down the centre ridge)
    const round = ctx.createLinearGradient(sx, 0, sx + sw, 0);
    round.addColorStop(0, "rgba(0,0,0,0.38)");
    round.addColorStop(0.18, "rgba(255,245,220,0.08)");
    round.addColorStop(0.5, "rgba(255,248,230,0.12)");
    round.addColorStop(0.84, "rgba(0,0,0,0.08)");
    round.addColorStop(1, "rgba(0,0,0,0.42)");
    ctx.fillStyle = round;
    ctx.fillRect(sx, sy, sw, sh);

    // Fine buckram / leather grain on the spine
    for (let n = 0; n < 700; n++) {
      ctx.fillStyle = r() < 0.5 ? "rgba(0,0,0,0.08)" : "rgba(255,245,220,0.06)";
      ctx.fillRect(sx + r(0, sw), sy + r(0, sh), r(1, 5), r(1, 2));
    }

    // Head & tail shelf wear (rubbed paler at top and bottom caps)
    for (const [y0, y1] of [
      [sy, sy + 28],
      [sy + sh, sy + sh - 28],
    ]) {
      const cap = ctx.createLinearGradient(0, y0, 0, y1);
      cap.addColorStop(0, "rgba(198,178,142,0.28)");
      cap.addColorStop(1, "rgba(198,178,142,0)");
      ctx.fillStyle = cap;
      ctx.fillRect(sx, Math.min(y0, y1), sw, 28);
    }

    // Raised bands & gilt/blind ornamental rules
    const bandPositions = idx % 3 === 0 ? [0.08, 0.24, 0.72, 0.9] : [0.09, 0.34, 0.66, 0.91];
    for (const frac of bandPositions) {
      const by_ = sy + sh * frac;
      ctx.fillStyle = "rgba(0,0,0,0.34)";
      ctx.fillRect(sx, by_ + 3, sw, 4);
      ctx.fillStyle = item.spineFg;
      ctx.globalAlpha = 0.78;
      ctx.fillRect(sx + 6, by_ - 1, sw - 12, 2.5);
      ctx.globalAlpha = 0.35;
      ctx.fillRect(sx + 8, by_ - 5, sw - 16, 1.2);
      ctx.globalAlpha = 1;
    }

    // Contrasting spine label plate on ~half of the volumes for rich period variety
    const hasPlate = idx % 2 === 1;
    const hex = item.spineFg.replace("#", "");
    const fgLum =
      (parseInt(hex.slice(0, 2), 16) * 0.299 +
        parseInt(hex.slice(2, 4), 16) * 0.587 +
        parseInt(hex.slice(4, 6), 16) * 0.114) /
      255;
    if (hasPlate) {
      const py = sy + sh * 0.13;
      const ph = sh * 0.2;
      ctx.fillStyle = fgLum < 0.45 ? "rgba(232,218,186,0.88)" : "rgba(22,16,12,0.72)";
      ctx.fillRect(sx + 7, py, sw - 14, ph);
      ctx.strokeStyle = item.spineFg;
      ctx.lineWidth = 1.6;
      ctx.globalAlpha = 0.85;
      ctx.strokeRect(sx + 9, py + 2, sw - 18, ph - 4);
      ctx.globalAlpha = 1;
    }

    // Spine typography: mix vertical French-style spines and classic horizontal stacked spines
    ctx.fillStyle = item.spineFg;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    if (!hasPlate && idx % 3 !== 2) {
      // Vertical classic spine lettering (rotated 90° down, very legible on standing books)
      ctx.save();
      ctx.translate(sx + sw / 2, sy + sh * 0.48);
      ctx.rotate(Math.PI / 2);
      ctx.font = "bold 20px Georgia, serif";
      ctx.fillText(item.title, 0, -8, sh * 0.44);
      ctx.globalAlpha = 0.82;
      ctx.font = "14px Georgia, serif";
      ctx.fillText(item.author, 0, 14, sh * 0.42);
      ctx.restore();
    } else {
      // Horizontal stacked serif title inside upper panel + author below + year at foot
      const words = item.title.split(/\s+/);
      const lines = [];
      let cur = "";
      for (const word of words) {
        if (cur && (cur + " " + word).length > 10) {
          lines.push(cur);
          cur = word;
        } else cur = cur ? `${cur} ${word}` : word;
      }
      if (cur) lines.push(cur);
      const topY = sy + sh * (hasPlate ? 0.18 : 0.16);
      const step = lines.length > 2 ? 18 : 22;
      ctx.font = lines.length > 2 ? "bold 14px Georgia, serif" : "bold 16px Georgia, serif";
      lines.slice(0, 3).forEach((ln, li) => {
        ctx.fillText(ln, sx + sw / 2, topY + li * step, sw - 18);
      });
      ctx.globalAlpha = 0.86;
      ctx.font = "12px Georgia, serif";
      ctx.fillText(item.author, sx + sw / 2, sy + sh * 0.5, sw - 16);
    }
    // Publication year or publisher mark near the tail cap
    ctx.globalAlpha = 0.72;
    ctx.font = "12px Georgia, serif";
    ctx.fillText(item.year, sx + sw / 2, sy + sh * 0.83, sw - 16);
    ctx.globalAlpha = 1;
    ctx.restore();

    // --------------------------------------------------- 3. MATCHING BACK BOARD
    ctx.fillStyle = item.spineBg;
    ctx.fillRect(bx, by, bw, bh);
    for (let n = 0; n < 400; n++) {
      ctx.fillStyle = r() < 0.5 ? "rgba(0,0,0,0.09)" : "rgba(255,245,220,0.05)";
      ctx.fillRect(bx + r(0, bw), by + r(0, bh), r(1, 4), r(1, 3));
    }
    ctx.strokeStyle = "rgba(0,0,0,0.22)";
    ctx.lineWidth = 4;
    ctx.strokeRect(bx + 2, by + 2, bw - 4, bh - 4);
  }
}

function atlas(key) {
  const spec = LAYOUT.atlases[key];
  const items = Object.entries(spec.items).map(([id, item]) => ({
    ...item,
    id,
    src: `data:image/jpeg;base64,${readFileSync(join(BOOKS, item.file)).toString("base64")}`,
  }));
  const [w, h] = spec.size;
  return {
    name: `studio_${key}`,
    file: spec.file,
    size: spec.size,
    draw: () => canvasPage(w, h, paintBooks, { items }),
  };
}

export const studioBookTextures = [atlas("books_a"), atlas("books_b")];
