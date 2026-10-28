// Textures for the Episode 1 village (Beat Sheet 4.2–4.4) that no library has:
// Uncle Sok's original identity-matched funeral portrait, banana and palm
// leaves, the white crocodile flag that marks a house in mourning, the coffin's
// gilt panels, a woven reed mat, the tent's scalloped valance and banana stems.
// Each paints a <canvas> in headless Chrome (render.mjs); `alpha` textures keep
// a transparent background for cut-out leaves and cloth.
//
// References: Léon Busy's autochromes of Cambodia, 1921 (Archives de la Planète,
// Musée Albert-Kahn, CC0 on Wikimedia Commons): palm-thatched stilt houses,
// banana and sugar palm groves, a woman in mourning with shaved head and white
// cloth, a civil servant's teak house with X-braced railings.

// The painters run in the page, where LIB defines their helpers.
/* global rng, clamp, lerp, smooth, mix3, rgb, noise, mottle, hardAlpha, document, Image */

import { readFileSync } from "node:fs";
import { join } from "node:path";

const ARCHIVE = join("art-source", "library", "archive");

/** Helpers shared by every painter, defined again inside each page. */
const LIB = String.raw`
function rng(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const r = (min = 0, max = 1) => min + (max - min) * next();
  r.normal = (sd = 1) => sd * Math.sqrt(-2 * Math.log(next() || 1e-9)) * Math.cos(2 * Math.PI * next());
  return r;
}
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const mix3 = (c0, c1, t) => c0.map((v, i) => lerp(v, c1[i], t));
const rgb = (c, a = 1) => "rgba(" + c.map(Math.round).join(",") + "," + a + ")";

/** Smooth value noise in [0, 1] at a pixel grid of 'cell' px, as a Float32Array (w x h). */
function noise(w, h, cell, seed, octaves = 4) {
  const out = new Float32Array(w * h);
  const r = rng(seed);
  let amp = 1, total = 0;
  for (let o = 0; o < octaves; o++) {
    const c = Math.max(1, cell / 2 ** o);
    const gw = Math.ceil(w / c) + 2, gh = Math.ceil(h / c) + 2;
    const g = new Float32Array(gw * gh).map(() => r());
    for (let y = 0; y < h; y++) {
      const fy = y / c, iy = Math.floor(fy), ty = fy - iy, sy = ty * ty * (3 - 2 * ty);
      for (let x = 0; x < w; x++) {
        const fx = x / c, ix = Math.floor(fx), tx = fx - ix, sx = tx * tx * (3 - 2 * tx);
        const a = g[iy * gw + ix], b = g[iy * gw + ix + 1];
        const d = g[(iy + 1) * gw + ix], e = g[(iy + 1) * gw + ix + 1];
        out[y * w + x] += amp * lerp(lerp(a, b, sx), lerp(d, e, sx), sy);
      }
    }
    total += amp;
    amp *= 0.5;
  }
  for (let i = 0; i < out.length; i++) out[i] /= total;
  return out;
}

/** Multiplies the canvas colour by (1 + k * (noise - 0.5)), keeping alpha. */
function mottle(ctx, w, h, cell, seed, k) {
  const n = noise(w, h, cell, seed);
  const img = ctx.getImageData(0, 0, w, h), p = img.data;
  for (let i = 0; i < w * h; i++) {
    const f = 1 + k * (n[i] - 0.5);
    p[i * 4] *= f; p[i * 4 + 1] *= f; p[i * 4 + 2] *= f;
  }
  ctx.putImageData(img, 0, 0);
}

/** Sharpens the alpha edge to 0 or 255 so alpha-tested cut-outs have clean outlines. */
function hardAlpha(ctx, w, h, cut = 110) {
  const img = ctx.getImageData(0, 0, w, h), p = img.data;
  for (let i = 3; i < p.length; i += 4) p[i] = p[i] > cut ? 255 : 0;
  ctx.putImageData(img, 0, 0);
}
`;

/** A page that runs `painter(ctx, w, h, data)` on a w x h canvas; `uses` are painters it calls. */
function canvasPage(w, h, painter, data = null, uses = []) {
  return `<canvas id="c" width="${w}" height="${h}"></canvas><script>${LIB}
${uses.map((f) => f.toString()).join("\n")}
const DATA = ${JSON.stringify(data)};
(${painter.toString()})(document.getElementById("c").getContext("2d", { willReadFrequently: true }), ${w}, ${h}, DATA);
</script>`;
}

// ------------------------------------------------------------------ portrait

/** Identity-matched original funeral photograph; the family archive prints stay separate. */
function portrait() {
  // Original Sok identity, shared with the sketchbook, already mounted and aged.
  const file = join("art-source", "textures", "ep1", "notebook", "sok-funeral-photo.png");
  return `<img width="768" height="1024" src="data:image/png;base64,${readFileSync(file).toString("base64")}">`;
}

/**
 * The family's photographs on the hall wall, three prints side by side in one
 * map (the group on the left half, a quarter each for the others): the whole
 * family before their house, the mother,
 * and the eldest daughter, from the 1921 Busy family autochrome.
 * Cheaper prints than his and older, faded to the colour of weak tea, the
 * group one water-stained where the roof leaked onto the wall.
 */
function paintFamilyPrints(ctx, W, H, data) {
  const imgs = data.srcs.map((src) => {
    const img = new Image();
    img.src = src;
    return img;
  });
  Promise.all(
    imgs.map((img) => new Promise((done) => (img.complete ? done() : (img.onload = done)))),
  ).then(() => {
    data.tiles.forEach(({ crop, x: x0, w: tw, src = 0, fade, oval }, k) => {
      const img = imgs[src];
      const r = rng(1930 + k);
      // The mount: cheap grey-brown card.
      ctx.fillStyle = "#c9bc9f";
      ctx.fillRect(x0, 0, tw, H);
      // The print, fitted to the crop's shape inside a margin.
      const [, , cw, ch] = crop;
      const room = [tw * 0.84, H * 0.84];
      const s = Math.min(room[0] / cw, room[1] / ch);
      const pw = Math.round(cw * s),
        ph = Math.round(ch * s);
      const px = Math.round(x0 + (tw - pw) / 2),
        py = Math.round(H * 0.06 + (room[1] - ph) / 2);
      const print = silverPrint(
        img,
        crop,
        pw,
        ph,
        fade ?? 0.4 + 0.1 * k,
        oval ?? (k === 0 ? 0 : 1),
        77 + k,
      );
      ctx.drawImage(print, px, py);
      // Foxing, a water stain on the group, scratches.
      for (let j = 0; j < 18; j++) {
        const fx = x0 + r(0, tw),
          fy = r(0, H),
          fs = r(1.5, 6);
        const g = ctx.createRadialGradient(fx, fy, 0, fx, fy, fs * 2);
        g.addColorStop(0, "rgba(120,80,40,0.5)");
        g.addColorStop(1, "rgba(120,80,40,0)");
        ctx.fillStyle = g;
        ctx.fillRect(fx - fs * 2, fy - fs * 2, fs * 4, fs * 4);
      }
      if (k === 0) {
        ctx.filter = "blur(3px)";
        ctx.strokeStyle = "rgba(110,72,35,0.3)";
        ctx.lineWidth = 4;
        ctx.fillStyle = "rgba(150,105,55,0.2)";
        ctx.beginPath();
        ctx.moveTo(x0 + tw * 0.55, 0);
        for (let a = 0; a <= 20; a++)
          ctx.lineTo(
            x0 + tw * (0.55 + 0.4 * (a / 20)) + r(-6, 6),
            H * (0.18 + 0.25 * Math.sin((a / 20) * Math.PI)) + r(-6, 6),
          );
        ctx.lineTo(x0 + tw, 0);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.filter = "none";
      }
      ctx.strokeStyle = "rgba(245,236,214,0.3)";
      for (let j = 0; j < 6; j++) {
        ctx.lineWidth = r(0.5, 1.2);
        ctx.beginPath();
        const sx = x0 + r(0, tw),
          sy = r(0, H),
          a = r(-0.5, 0.5) + Math.PI / 2;
        ctx.moveTo(sx, sy);
        ctx.lineTo(sx + Math.cos(a) * r(20, 120), sy + Math.sin(a) * r(20, 120));
        ctx.stroke();
      }
      // The card darkens towards its edges.
      const edge = ctx.createRadialGradient(
        x0 + tw / 2,
        H / 2,
        tw * 0.3,
        x0 + tw / 2,
        H / 2,
        tw * 0.9,
      );
      edge.addColorStop(0, "rgba(0,0,0,0)");
      edge.addColorStop(1, "rgba(80,52,22,0.4)");
      ctx.fillStyle = edge;
      ctx.fillRect(x0, 0, tw, H);
    });
  });
}

/**
 * A toned silver print of `crop` from `img`, `pw` x `ph`: orthochromatic (reds
 * print dark), soft, grainy, faded towards the paper by `fade` (0..1); `oval` 1
 * vignettes it like a studio portrait, 0 fades only its edges.
 */
function silverPrint(img, crop, pw, ph, fade, oval, seed) {
  const off = document.createElement("canvas");
  off.width = pw;
  off.height = ph;
  const o = off.getContext("2d", { willReadFrequently: true });
  o.filter = "blur(1.3px)";
  o.drawImage(img, crop[0], crop[1], crop[2], crop[3], 0, 0, pw, ph);
  o.filter = "none";
  const photo = o.getImageData(0, 0, pw, ph),
    p = photo.data;
  const grain = noise(pw, ph, 1.5, seed, 2);
  const blotch = noise(pw, ph, 90, seed + 1, 3);
  const dark = [52, 36, 22],
    mid = [140, 104, 66],
    light = [226, 208, 172];
  for (let y = 0; y < ph; y++) {
    for (let x = 0; x < pw; x++) {
      const i = (y * pw + x) * 4;
      let L = (0.12 * p[i] + 0.52 * p[i + 1] + 0.36 * p[i + 2]) / 255;
      L = clamp((L - 0.1) / 0.82);
      L = L < 0.5 ? 2 * L * L : 1 - 2 * (1 - L) * (1 - L);
      L += (grain[y * pw + x] - 0.5) * 0.18 + (blotch[y * pw + x] - 0.5) * 0.14;
      L = lerp(L, 0.8, fade);
      const dx = (x - pw / 2) / (pw * 0.46),
        dy = (y - ph * 0.48) / (ph * 0.48);
      const v = oval
        ? smooth(0.8, 1.05, Math.sqrt(dx * dx + dy * dy))
        : smooth(0.86, 1.0, Math.max(Math.abs(dx), Math.abs(dy)));
      L = lerp(L, 0.86, v);
      const c = L < 0.5 ? mix3(dark, mid, L / 0.5) : mix3(mid, light, (L - 0.5) / 0.5);
      p[i] = c[0];
      p[i + 1] = c[1];
      p[i + 2] = c[2];
      p[i + 3] = 255;
    }
  }
  o.putImageData(photo, 0, 0);
  return off;
}

function familyPrints() {
  const srcs = [
    "Un_fonctionnaire_cambodgien_et_sa_famille_A36130.jpg",
    "Un_bonze_revenant_de_la_quete_A35898.jpg",
  ].map((file) => `data:image/jpeg;base64,${readFileSync(join(ARCHIVE, file)).toString("base64")}`);
  // The group, the mother, the eldest daughter (pixels in the 2560 x 1898 original of
  // A36130), and a young monk on the steps of Angkor Wat (A35898, 1519 x 2048), kept
  // high on the wall by the altar; where each goes in the map: u 0-0.4, 0.4-0.6,
  // 0.6-0.8, 0.8-1.
  const tiles = [
    { crop: [845, 691, 1408, 973], x: 0, w: 1024 },
    { crop: [1140, 745, 340, 450], x: 1024, w: 512 },
    { crop: [1950, 810, 290, 390], x: 1536, w: 512 },
    { crop: [91, 91, 1365, 1877], x: 2048, w: 512, src: 1, fade: 0.35, oval: 0 },
  ];
  return canvasPage(2560, 716, paintFamilyPrints, { srcs, tiles }, [silverPrint]);
}

/**
 * Papers in the hall, one map (pixel rectangles in HOUSE_PAPERS): a Chinese
 * merchant's give-away calendar for 1932 open at July, a head-tax receipt of the
 * Protectorate (the impôt personnel every adult man paid, a sore point of the
 * time) with the payer's thumbprint, and the primary-school certificate of the
 * Franco-Khmer schools, which Sok kept framed. French in print as the forms were;
 * the Khmer lines are in the KHMER list (tools/drawings/ep1.mjs) for review.
 */
function paintHousePapers(ctx, W, H, data) {
  const draw = () => {
    const r = rng(1932);
    const K = data.khmer;
    // Unused corners of the map: dark, so nothing pale bleeds into the papers' edges.
    ctx.fillStyle = "#3a2e22";
    ctx.fillRect(0, 0, W, H);
    const toKhmer = (n) => String(n).replace(/[0-9]/g, (d) => "០១២៣៤៥៦៧៨៩"[d]);
    const text = (t, x, y, size, opts = {}) => {
      ctx.save();
      ctx.font = `${opts.weight || ""} ${size}px ${opts.font || "Georgia, serif"}`;
      ctx.fillStyle = opts.color || "rgba(38,28,20,0.92)";
      ctx.textAlign = opts.align || "center";
      ctx.textBaseline = "alphabetic";
      if (opts.spacing) ctx.letterSpacing = `${opts.spacing}px`;
      ctx.fillText(t, x, y);
      ctx.restore();
    };
    const paper = ([x, y, w, h], base, seed) => {
      ctx.fillStyle = base;
      ctx.fillRect(x, y, w, h);
      const n = noise(w, h, 60, seed, 4),
        img = ctx.getImageData(x, y, w, h),
        p = img.data;
      for (let i = 0; i < w * h; i++) {
        const f = 0.9 + 0.2 * n[i];
        p[i * 4] *= f;
        p[i * 4 + 1] *= f;
        p[i * 4 + 2] *= f * 0.97;
      }
      ctx.putImageData(img, x, y);
    };
    const age = ([x, y, w, h], k) => {
      // Mildew and fly specks, browned edges, a tide-mark of damp.
      for (let j = 0; j < 40 * k; j++) {
        const fx = x + r(0, w),
          fy = y + r(0, h),
          fs = r(0.8, 3.5);
        ctx.fillStyle = `rgba(60,45,30,${r(0.2, 0.6)})`;
        ctx.beginPath();
        ctx.arc(fx, fy, fs, 0, Math.PI * 2);
        ctx.fill();
      }
      for (let j = 0; j < 6 * k; j++) {
        const fx = x + r(0, w),
          fy = y + r(0, h),
          fs = r(10, 40);
        const g = ctx.createRadialGradient(fx, fy, 0, fx, fy, fs);
        g.addColorStop(0, "rgba(110,95,60,0.22)");
        g.addColorStop(1, "rgba(110,95,60,0)");
        ctx.fillStyle = g;
        ctx.fillRect(fx - fs, fy - fs, fs * 2, fs * 2);
      }
      const e = ctx.createRadialGradient(
        x + w / 2,
        y + h / 2,
        Math.min(w, h) * 0.35,
        x + w / 2,
        y + h / 2,
        Math.max(w, h) * 0.75,
      );
      e.addColorStop(0, "rgba(0,0,0,0)");
      e.addColorStop(1, "rgba(95,62,25,0.45)");
      ctx.fillStyle = e;
      ctx.fillRect(x, y, w, h);
    };

    // ---- The calendar.
    const C = data.calendar,
      [cx, cy, cw, ch] = C;
    paper(C, "#e6dcc4", 11);
    ctx.fillStyle = "#8e2a20";
    ctx.fillRect(cx, cy, cw, ch * 0.09);
    text("MAISON TAN HONG & Cie", cx + cw / 2, cy + ch * 0.045, cw * 0.05, {
      color: "#e8c67a",
      weight: "bold",
      spacing: 2,
    });
    text(
      "BATTAMBANG  ·  Riz  ·  Tissus  ·  Pétrole  ·  Quincaillerie",
      cx + cw / 2,
      cy + ch * 0.075,
      cw * 0.027,
      { color: "#e8c67a" },
    );
    // A lithograph: rice fields and sugar palms at evening, the colours run.
    const [px, py, pw, ph] = [cx + cw * 0.07, cy + ch * 0.11, cw * 0.86, ch * 0.36];
    const sky = ctx.createLinearGradient(0, py, 0, py + ph);
    sky.addColorStop(0, "#c98a5a");
    sky.addColorStop(0.55, "#e2b77a");
    sky.addColorStop(0.56, "#7d8a52");
    sky.addColorStop(1, "#4f5e36");
    ctx.fillStyle = sky;
    ctx.fillRect(px, py, pw, ph);
    ctx.strokeStyle = "rgba(230,200,140,0.5)";
    for (let j = 0; j < 9; j++) {
      ctx.beginPath();
      ctx.moveTo(px, py + ph * (0.6 + j * 0.045));
      ctx.lineTo(px + pw, py + ph * (0.58 + j * 0.05));
      ctx.stroke();
    }
    ctx.fillStyle = "#2c2a1c";
    for (let j = 0; j < 7; j++) {
      const tx = px + pw * (0.08 + j * 0.14 + r(-0.03, 0.03)),
        top = py + ph * r(0.12, 0.3);
      ctx.fillRect(tx - 2, top, 4, py + ph * 0.56 - top);
      for (let f = 0; f < 18; f++) {
        const a = (f / 18) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(tx, top);
        ctx.lineTo(tx + Math.cos(a) * pw * 0.05, top + Math.sin(a) * ph * 0.08);
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#2c2a1c";
        ctx.stroke();
      }
    }
    ctx.strokeStyle = "rgba(40,28,20,0.8)";
    ctx.lineWidth = 3;
    ctx.strokeRect(px, py, pw, ph);
    text(K.calendar, cx + cw / 2, cy + ch * 0.54, cw * 0.075, {
      font: "Preahvihear",
      color: "#8e2a20",
    });
    text("CALENDRIER 1932", cx + cw / 2, cy + ch * 0.585, cw * 0.045, {
      weight: "bold",
      spacing: 3,
    });
    text("JUILLET", cx + cw / 2, cy + ch * 0.65, cw * 0.1, {
      weight: "bold",
      color: "#8e2a20",
      spacing: 4,
    });
    const days = ["L", "M", "M", "J", "V", "S", "D"];
    const gx = cx + cw * 0.08,
      gw = (cw * 0.84) / 7,
      gy = cy + ch * 0.7,
      gh = ch * 0.05;
    days.forEach((d, i) =>
      text(d, gx + gw * (i + 0.5), gy, cw * 0.035, {
        weight: "bold",
        color: i === 6 ? "#8e2a20" : undefined,
      }),
    );
    for (let day = 1; day <= 31; day++) {
      const i = day - 1 + 4; // 1 July 1932 was a Friday
      const col = i % 7,
        row = Math.floor(i / 7);
      const x = gx + gw * (col + 0.5),
        y = gy + gh * (row + 1);
      text(String(day), x, y, cw * 0.045, { color: col === 6 ? "#8e2a20" : undefined });
      text(toKhmer(day), x, y + gh * 0.36, cw * 0.022, {
        font: "Preahvihear",
        color: "rgba(60,45,30,0.75)",
      });
    }
    // Days crossed off in pencil, up to the 14th.
    ctx.strokeStyle = "rgba(50,45,45,0.5)";
    ctx.lineWidth = 2;
    for (let day = 1; day <= 14; day++) {
      const i = day - 1 + 4,
        x = gx + gw * ((i % 7) + 0.5),
        y = gy + gh * (Math.floor(i / 7) + 1);
      ctx.beginPath();
      ctx.moveTo(x - gw * 0.3, y - gh * 0.5);
      ctx.lineTo(x + gw * 0.3, y + gh * 0.1);
      ctx.stroke();
    }
    age(C, 2);

    // ---- The tax receipt.
    const T = data.receipt,
      [tx, ty, tw, th] = T;
    paper(T, "#cfd3bd", 12);
    ctx.strokeStyle = "rgba(40,50,40,0.85)";
    ctx.lineWidth = 3;
    ctx.strokeRect(tx + 14, ty + 14, tw - 28, th - 28);
    ctx.lineWidth = 1;
    ctx.strokeRect(tx + 22, ty + 22, tw - 44, th - 44);
    const L = tx + 44;
    text("PROTECTORAT DU CAMBODGE", tx + tw / 2, ty + th * 0.1, tw * 0.044, {
      weight: "bold",
      spacing: 1,
    });
    text(K.kingdom, tx + tw / 2, ty + th * 0.17, tw * 0.05, { font: "Preahvihear" });
    text("IMPÔT PERSONNEL", tx + tw / 2, ty + th * 0.26, tw * 0.075, {
      weight: "bold",
      spacing: 3,
    });
    text("Exercice 1931  —  N° 004517", tx + tw / 2, ty + th * 0.31, tw * 0.04);
    const field = (label, y, value) => {
      text(label, L, ty + th * y, tw * 0.042, { align: "left" });
      ctx.strokeStyle = "rgba(40,50,40,0.5)";
      ctx.setLineDash([3, 4]);
      ctx.beginPath();
      ctx.moveTo(L + tw * 0.32, ty + th * y + 4);
      ctx.lineTo(tx + tw - 44, ty + th * y + 4);
      ctx.stroke();
      ctx.setLineDash([]);
      if (value)
        text(value, L + tw * 0.36, ty + th * y - 2, tw * 0.06, {
          align: "left",
          font: "PatrickHand",
          color: "rgba(30,35,80,0.85)",
        });
    };
    field("Khêt :", 0.4, "Battambang");
    field("Srok :", 0.47, "Sangkè");
    field("Nom :", 0.54, "Sok");
    field("Somme :", 0.61, "2 $ 50");
    field("Reçu le :", 0.68, "12 mars 1931");
    // The payer's thumbprint, and the Résidence's stamp half over the signature.
    const fx = tx + tw * 0.27,
      fy = ty + th * 0.84;
    ctx.strokeStyle = "rgba(40,30,60,0.55)";
    ctx.lineWidth = 1.6;
    for (let j = 1; j < 14; j++) {
      ctx.beginPath();
      ctx.ellipse(
        fx,
        fy,
        j * 2.6,
        j * 3.4,
        0.2,
        Math.PI * 0.05 * r(0, 3),
        Math.PI * (1.6 + r(0, 0.35)),
      );
      ctx.stroke();
    }
    const sx = tx + tw * 0.68,
      sy = ty + th * 0.84;
    ctx.strokeStyle = "rgba(150,40,40,0.75)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(sx, sy, tw * 0.13, 0, Math.PI * 2);
    ctx.stroke();
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(sx, sy, tw * 0.1, 0, Math.PI * 2);
    ctx.stroke();
    text("RÉSIDENCE", sx, sy - 4, tw * 0.03, { color: "rgba(150,40,40,0.8)", weight: "bold" });
    text("BATTAMBANG", sx, sy + tw * 0.04, tw * 0.03, {
      color: "rgba(150,40,40,0.8)",
      weight: "bold",
    });
    ctx.strokeStyle = "rgba(30,35,80,0.7)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(sx - tw * 0.18, sy + 10);
    for (let j = 0; j < 12; j++) ctx.lineTo(sx - tw * 0.18 + j * tw * 0.03, sy + 10 + r(-14, 14));
    ctx.stroke();
    age(T, 1);

    // ---- The certificate.
    const S = data.certificate,
      [ex, ey, ew, eh] = S;
    paper(S, "#ece2c8", 13);
    ctx.strokeStyle = "rgba(90,60,30,0.85)";
    for (const [inset, wdt] of [
      [18, 6],
      [32, 1.5],
      [40, 1],
    ]) {
      ctx.lineWidth = wdt;
      ctx.strokeRect(ex + inset, ey + inset, ew - inset * 2, eh - inset * 2);
    }
    // A plain geometric band of lozenges inside the border.
    ctx.fillStyle = "rgba(90,60,30,0.6)";
    for (let j = 0; j < 30; j++) {
      for (const [bx, by] of [
        [ex + 50 + ((ew - 100) * j) / 29, ey + 25],
        [ex + 50 + ((ew - 100) * j) / 29, ey + eh - 25],
      ]) {
        ctx.beginPath();
        ctx.moveTo(bx, by - 5);
        ctx.lineTo(bx + 5, by);
        ctx.lineTo(bx, by + 5);
        ctx.lineTo(bx - 5, by);
        ctx.fill();
      }
    }
    const mid = ex + ew / 2;
    text("GOUVERNEMENT GÉNÉRAL DE L'INDOCHINE", mid, ey + eh * 0.1, ew * 0.035, { spacing: 1 });
    text("PROTECTORAT DU CAMBODGE", mid, ey + eh * 0.14, ew * 0.035, { spacing: 1 });
    text("Enseignement franco-cambodgien", mid, ey + eh * 0.19, ew * 0.04, {
      font: "Georgia, serif",
    });
    text("CERTIFICAT", mid, ey + eh * 0.3, ew * 0.1, {
      weight: "bold",
      spacing: 6,
      color: "rgba(60,35,20,0.95)",
    });
    text("D'ÉTUDES PRIMAIRES ÉLÉMENTAIRES", mid, ey + eh * 0.355, ew * 0.035, {
      weight: "bold",
      spacing: 1,
    });
    text(K.certificate, mid, ey + eh * 0.42, ew * 0.055, {
      font: "Preahvihear",
      color: "rgba(60,35,20,0.9)",
    });
    const lines = [
      ["Le Résident de France à Battambang certifie que", null],
      ["l'élève", "Sok"],
      ["de l'école de", "Battambang"],
      ["a subi avec succès les épreuves", null],
      ["de la session de", "juin 1907"],
    ];
    lines.forEach(([label, value], j) => {
      const y = ey + eh * (0.52 + j * 0.065);
      if (value) {
        text(label, ex + ew * 0.44, y, ew * 0.036, { align: "right" });
        text(value, ex + ew * 0.48, y, ew * 0.058, {
          align: "left",
          font: "PatrickHand",
          color: "rgba(30,30,70,0.85)",
        });
      } else text(label, mid, y, ew * 0.038, { font: "Georgia, serif" });
    });
    text("Battambang, le 30 juin 1907", ex + ew * 0.62, ey + eh * 0.86, ew * 0.032);
    ctx.strokeStyle = "rgba(30,30,70,0.7)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(ex + ew * 0.52, ey + eh * 0.9);
    for (let j = 0; j < 14; j++)
      ctx.lineTo(ex + ew * 0.52 + j * ew * 0.018, ey + eh * 0.9 + r(-10, 10));
    ctx.stroke();
    ctx.strokeStyle = "rgba(120,50,40,0.6)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(ex + ew * 0.22, ey + eh * 0.88, ew * 0.08, 0, Math.PI * 2);
    ctx.stroke();
    // Water got behind the glass once: a tide-mark across the lower corner.
    ctx.save();
    ctx.filter = "blur(4px)";
    ctx.fillStyle = "rgba(140,105,60,0.22)";
    ctx.beginPath();
    ctx.moveTo(ex, ey + eh * 0.7);
    for (let j = 0; j <= 20; j++)
      ctx.lineTo(
        ex + ew * 0.45 * (j / 20),
        ey + eh * (0.7 + 0.3 * Math.sin((j / 20) * Math.PI * 0.5)) + r(-8, 8),
      );
    ctx.lineTo(ex, ey + eh);
    ctx.fill();
    ctx.restore();
    age(S, 1);
  };
  Promise.all(["40px Preahvihear", "40px PatrickHand"].map((f) => document.fonts.load(f))).then(
    draw,
  );
}

/**
 * A candle or wick flame for every flame card (khmer.flame, the held lamp): a
 * teardrop drawn soft, orange at the rim, yellow, a pale core over the wick and a
 * little blue where it meets the wick; alpha fades it into the air. The colour is
 * the light (emission); the game flickers the cards' size.
 */
function paintFlame(ctx, W, H) {
  const drop = (cx, base, w, h) => {
    ctx.beginPath();
    ctx.moveTo(cx, base - h);
    ctx.bezierCurveTo(
      cx + w * 0.12,
      base - h * 0.62,
      cx + w * 0.55,
      base - h * 0.32,
      cx + w * 0.48,
      base - h * 0.1,
    );
    ctx.bezierCurveTo(
      cx + w * 0.42,
      base + h * 0.02,
      cx - w * 0.42,
      base + h * 0.02,
      cx - w * 0.48,
      base - h * 0.1,
    );
    ctx.bezierCurveTo(cx - w * 0.55, base - h * 0.32, cx - w * 0.12, base - h * 0.62, cx, base - h);
    ctx.fill();
  };
  ctx.clearRect(0, 0, W, H);
  const cx = W / 2,
    base = H * 0.95;
  for (const [w, h, colour, blur] of [
    [W * 0.95, H * 0.92, "rgba(255,110,25,0.45)", W * 0.08],
    [W * 0.78, H * 0.85, "rgba(255,150,40,0.85)", W * 0.05],
    [W * 0.6, H * 0.72, "rgba(255,200,90,0.95)", W * 0.04],
    [W * 0.4, H * 0.5, "rgba(255,240,190,1)", W * 0.03],
  ]) {
    ctx.filter = `blur(${blur}px)`;
    ctx.fillStyle = colour;
    drop(cx, base, w, h);
  }
  // Blue at the root, and the dark wick showing through it.
  ctx.filter = `blur(${W * 0.03}px)`;
  ctx.fillStyle = "rgba(90,120,255,0.35)";
  drop(cx, base, W * 0.42, H * 0.16);
  ctx.filter = "none";
  ctx.fillStyle = "rgba(40,20,10,0.8)";
  ctx.fillRect(cx - W * 0.025, base - H * 0.1, W * 0.05, H * 0.1);
}

/**
 * Kanha's drawing of the betel tray, pinned by the ancestral altar (A1-08): the
 * round tray seen from above as she set it out, the candle at the back, the
 * incense at the front, betel leaves to the left, areca nuts to the right and the
 * lime pot in the middle (Episode 1, section 6.1; the layout is to confirm with
 * the cultural advisor). Ink gone brown on paper gone yellow, a pin hole at the
 * top; no lettering. Sora knows the hand: it is like her own.
 */
function paintKanhaDrawing(ctx, W, H) {
  const r = rng(1920);
  ctx.fillStyle = "#cdb98a";
  ctx.fillRect(0, 0, W, H);
  mottle(ctx, W, H, 40, 23, 0.3);
  // Foxing: small rust-brown spots, and a darker edge where the paper has aged.
  for (let k = 0; k < 40; k++) {
    ctx.fillStyle = `rgba(120,70,30,${r(0.08, 0.25)})`;
    ctx.beginPath();
    ctx.arc(r(0, W), r(0, H), r(1, 5), 0, Math.PI * 2);
    ctx.fill();
  }
  const edge = ctx.createRadialGradient(W / 2, H / 2, W * 0.3, W / 2, H / 2, W * 0.75);
  edge.addColorStop(0, "rgba(90,60,20,0)");
  edge.addColorStop(1, "rgba(90,60,20,0.45)");
  ctx.fillStyle = edge;
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "rgba(30,20,10,0.8)";
  ctx.beginPath();
  ctx.arc(W / 2, H * 0.04, 3, 0, Math.PI * 2);
  ctx.fill();

  const ink = "rgba(60,38,22,0.82)";
  // A line drawn by hand: slightly wavering, a little thicker where the pen pressed.
  const line = (pts, width = 3, closed = false) => {
    ctx.strokeStyle = ink;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    pts.forEach(([x, y], i) => {
      const jx = x + r(-1.2, 1.2),
        jy = y + r(-1.2, 1.2);
      if (i === 0) ctx.moveTo(jx, jy);
      else ctx.lineTo(jx, jy);
    });
    if (closed) ctx.closePath();
    ctx.stroke();
  };
  const ring = (cx, cy, rx, ry, n = 48) =>
    Array.from({ length: n }, (_, i) => {
      const a = (i / n) * Math.PI * 2;
      return [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry];
    });

  const cx = W / 2,
    cy = H * 0.55,
    R = W * 0.38;
  // The tray: a lacquered round with a raised rim, a little oval as she saw it.
  line(ring(cx, cy, R, R * 0.92, 64), 4, true);
  line(ring(cx, cy, R * 0.9, R * 0.82, 64), 2, true);
  // Back: a candle with its flame.
  const bx = cx,
    by = cy - R * 0.55;
  line(
    [
      [bx - 9, by + 34],
      [bx - 9, by - 6],
      [bx + 9, by - 6],
      [bx + 9, by + 34],
    ],
    3,
  );
  line(
    [
      [bx, by - 10],
      [bx - 7, by - 22],
      [bx, by - 38],
      [bx + 7, by - 22],
    ],
    2.5,
    true,
  );
  // Front: three incense sticks laid side by side, smoke curling off one.
  const fy = cy + R * 0.58;
  for (let k = -1; k <= 1; k++)
    line(
      [
        [cx - R * 0.35, fy + k * 9],
        [cx + R * 0.35, fy + k * 9 - 6],
      ],
      2.5,
    );
  const curve = (draw, width) => {
    ctx.strokeStyle = ink;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.beginPath();
    draw();
    ctx.stroke();
  };
  curve(() => {
    const sx = cx + R * 0.37;
    ctx.moveTo(sx, fy - 10);
    ctx.bezierCurveTo(sx + 14, fy - 22, sx - 10, fy - 34, sx + 4, fy - 50);
  }, 1.5);
  // Left: betel leaves, heart-shaped, overlapping, each with its middle vein.
  for (let k = 0; k < 3; k++) {
    ctx.save();
    ctx.translate(cx - R * 0.6 + k * 10, cy - 22 + k * 20);
    ctx.rotate((k - 1) * 0.35);
    curve(() => {
      ctx.moveTo(0, -18);
      ctx.bezierCurveTo(-8, -30, -30, -20, -24, 0);
      ctx.bezierCurveTo(-20, 14, -6, 22, 0, 32);
      ctx.bezierCurveTo(6, 22, 20, 14, 24, 0);
      ctx.bezierCurveTo(30, -20, 8, -30, 0, -18);
    }, 2.5);
    curve(() => {
      ctx.moveTo(0, -16);
      ctx.quadraticCurveTo(2, 8, 0, 28);
    }, 1.4);
    ctx.restore();
  }
  // Right: areca nuts, round, cross-hatched on their shadowed side.
  for (const [dx, dy] of [
    [0, -16],
    [-14, 10],
    [14, 12],
  ]) {
    const ax = cx + R * 0.58 + dx,
      ay = cy + dy;
    line(ring(ax, ay, 12, 12, 20), 2.5, true);
    for (let h = 0; h < 3; h++)
      line(
        [
          [ax + 2 + h * 3, ay + 9],
          [ax + 9, ay + 2 + h * 3],
        ],
        1.2,
      );
  }
  // Middle: the small lidded lime pot.
  line(ring(cx, cy + 6, 20, 15, 32), 3, true);
  line(ring(cx, cy - 6, 14, 6, 24), 2.5, true);
  line(
    [
      [cx - 4, cy - 12],
      [cx, cy - 18],
      [cx + 4, cy - 12],
    ],
    2,
  );
}

/**
 * A page of Sok's notes, found by the ash circle under the house: cheap lined
 * paper in his hand, the word for debt at the top, the years of the payments down
 * the side (1911 the pact, 1920 Kanha, 1932 now) with scratched-out lines after
 * each, 1932 ringed again and again. One corner burnt away. The Khmer is in the
 * KHMER list (tools/drawings/ep1.mjs) for review.
 */
function paintSokNotes(ctx, W, H, data) {
  const draw = () => {
    const r = rng(1932 + 7);
    ctx.fillStyle = "#d9cfb2";
    ctx.fillRect(0, 0, W, H);
    mottle(ctx, W, H, 50, 21, 0.25);
    ctx.strokeStyle = "rgba(90,110,140,0.35)";
    ctx.lineWidth = 1.5;
    for (let y = H * 0.16; y < H; y += H * 0.065) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }
    const ink = "rgba(25,22,40,0.88)";
    ctx.fillStyle = ink;
    ctx.textBaseline = "alphabetic";
    ctx.font = `${Math.round(W * 0.16)}px Freehand`;
    ctx.fillText(data.debt, W * 0.1, H * 0.13);
    const scribble = (x, y, w) => {
      ctx.strokeStyle = ink;
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.moveTo(x, y);
      for (let t = 0; t < w; t += 6) ctx.lineTo(x + t, y + r(-7, 5) - (t % 18 < 9 ? 4 : 0));
      ctx.stroke();
    };
    data.years.forEach((year, i) => {
      const y = H * (0.3 + i * 0.22);
      ctx.font = `${Math.round(W * 0.1)}px Freehand`;
      ctx.fillStyle = ink;
      ctx.fillText(year, W * 0.08, y);
      for (let line = 0; line < 2; line++)
        scribble(W * 0.42, y - 6 + line * H * 0.06, W * r(0.3, 0.45));
      // Each line struck through, harder each time.
      ctx.strokeStyle = "rgba(25,22,40,0.7)";
      ctx.lineWidth = 2 + i;
      ctx.beginPath();
      ctx.moveTo(W * 0.4, y + H * 0.02);
      ctx.lineTo(W * 0.92, y - H * 0.03);
      ctx.stroke();
    });
    // 1932, ringed over and over in brown-red ink that has run.
    const y = H * (0.3 + 2 * 0.22) - H * 0.03;
    ctx.strokeStyle = "rgba(110,30,20,0.75)";
    for (let k = 0; k < 6; k++) {
      ctx.lineWidth = r(1.5, 3);
      ctx.beginPath();
      ctx.ellipse(
        W * 0.27 + r(-3, 3),
        y + r(-3, 3),
        W * r(0.23, 0.26),
        H * r(0.05, 0.065),
        r(-0.15, 0.15),
        0,
        Math.PI * 2,
      );
      ctx.stroke();
    }
    ctx.fillStyle = "rgba(110,30,20,0.6)";
    for (let k = 0; k < 3; k++)
      ctx.fillRect(W * r(0.1, 0.35), y + H * 0.06, 2.5, H * r(0.04, 0.12));
    // The corner burnt off: char, a brown scorch, then nothing.
    const g = ctx.createRadialGradient(W, H, W * 0.2, W, H, W * 0.55);
    g.addColorStop(0, "rgba(10,8,6,1)");
    g.addColorStop(0.55, "rgba(20,12,6,1)");
    g.addColorStop(0.75, "rgba(90,50,20,0.7)");
    g.addColorStop(1, "rgba(120,80,40,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.moveTo(W, H * 0.7);
    for (let t = 0; t <= 1; t += 0.05)
      ctx.lineTo(
        W - W * 0.38 * Math.sin((t * Math.PI) / 2) + r(-8, 8),
        H * 0.7 + H * 0.3 * t + r(-8, 8),
      );
    ctx.lineTo(W, H);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";
    hardAlpha(ctx, W, H, 110);
  };
  document.fonts.load("40px Freehand").then(draw);
}

/** Soft projected silhouette matching the stooped 3D form, for lightning on cloth. */
function paintShadowFigure(ctx, W, H) {
  const r = rng(16);
  ctx.clearRect(0, 0, W, H);
  ctx.save();
  ctx.scale(W, H);
  ctx.fillStyle = "#000";
  ctx.filter = `blur(${W * 0.003}px)`;
  // Unequal shoulders, compressed neck and a slightly bowed, off-centre head.
  ctx.beginPath();
  ctx.moveTo(0.48, 0.055);
  ctx.bezierCurveTo(0.53, 0.025, 0.595, 0.05, 0.601, 0.094);
  ctx.bezierCurveTo(0.614, 0.142, 0.575, 0.183, 0.55, 0.19);
  ctx.lineTo(0.57, 0.207);
  ctx.bezierCurveTo(0.63, 0.213, 0.681, 0.231, 0.696, 0.271);
  ctx.lineTo(0.655, 0.38);
  ctx.bezierCurveTo(0.62, 0.46, 0.592, 0.52, 0.602, 0.605);
  ctx.bezierCurveTo(0.608, 0.72, 0.642, 0.81, 0.631, 0.936);
  // Irregular overlapping cloth ends, not a regular zigzag fringe.
  for (let k = 0; k <= 21; k++) {
    const x = 0.631 - (k / 21) * 0.285;
    ctx.lineTo(x, 0.91 + r(-0.015, 0.055));
  }
  ctx.bezierCurveTo(0.333, 0.76, 0.369, 0.67, 0.377, 0.585);
  ctx.bezierCurveTo(0.395, 0.47, 0.361, 0.37, 0.331, 0.281);
  ctx.bezierCurveTo(0.33, 0.241, 0.389, 0.214, 0.451, 0.205);
  ctx.lineTo(0.468, 0.171);
  ctx.bezierCurveTo(0.447, 0.14, 0.445, 0.081, 0.48, 0.055);
  ctx.fill();
  // Tapered sleeves follow shoulder, upper arm, elbow and the hanging wrist.
  for (const side of [-1, 1]) {
    const shift = side < 0 ? 0.017 : 0;
    const x = side < 0 ? 0.334 : 0.687;
    ctx.beginPath();
    ctx.moveTo(x, 0.253 + shift);
    ctx.bezierCurveTo(x + side * 0.039, 0.34, x + side * 0.055, 0.43, x + side * 0.048, 0.49);
    ctx.bezierCurveTo(x + side * 0.04, 0.57, x + side * 0.046, 0.65, x + side * 0.05, 0.69);
    ctx.lineTo(x + side * 0.017, 0.699);
    ctx.bezierCurveTo(x + side * 0.007, 0.62, x + side * 0.001, 0.55, x + side * 0.003, 0.5);
    ctx.bezierCurveTo(x - side * 0.017, 0.43, x - side * 0.031, 0.34, x - side * 0.034, 0.29);
    ctx.closePath();
    ctx.fill();
    // Fingers remain close to the palm; their joints differ in length and curl.
    for (let f = 0; f < 4; f++) {
      const fx = x + side * (0.017 + f * 0.009),
        len = [0.055, 0.077, 0.072, 0.049][f];
      ctx.beginPath();
      ctx.moveTo(fx - 0.004, 0.683 + shift);
      ctx.bezierCurveTo(fx - 0.005, 0.705, fx + 0.002, 0.711 + len, fx + 0.009, 0.7 + len);
      ctx.lineTo(fx + 0.01, 0.693 + len);
      ctx.bezierCurveTo(fx + 0.004, 0.71 + len, fx + 0.003, 0.708, fx + 0.004, 0.683 + shift);
      ctx.fill();
    }
  }
  // The lowest part loses density against the fabric, rather than becoming a cloud outline.
  ctx.globalCompositeOperation = "destination-out";
  const fade = ctx.createLinearGradient(0, 0.82, 0, 1);
  fade.addColorStop(0, "rgba(0,0,0,0)");
  fade.addColorStop(1, "rgba(0,0,0,1)");
  ctx.fillStyle = fade;
  ctx.fillRect(0, 0.82, 1, 0.18);
  ctx.restore();
}

// ------------------------------------------------------------------ leaves

/**
 * Four banana leaves, one per 512 px row, base on the left and tip on the
 * right: young and whole, torn by the wind along its veins, ragged, and dry
 * and brown (the dead leaves that hang down the stem).
 */
function paintBanana(ctx, W, H) {
  const rows = 4,
    RH = H / rows;
  const looks = [
    { top: [62, 104, 38], edge: [44, 80, 30], tears: 4, dry: 0.1, seed: 11 },
    { top: [70, 112, 40], edge: [48, 84, 30], tears: 14, dry: 0.25, seed: 12 },
    { top: [76, 108, 42], edge: [92, 92, 40], tears: 30, dry: 0.5, seed: 13 },
    { top: [128, 98, 56], edge: [92, 64, 34], tears: 40, dry: 1.0, seed: 14 },
  ];
  looks.forEach((look, row) => {
    const r = rng(look.seed);
    const y0 = row * RH,
      mid = y0 + RH / 2;
    const x0 = 16,
      x1 = W - 20,
      len = x1 - x0,
      half = RH * 0.44;
    const width = (t) =>
      half *
      (t < 0.06 ? (t / 0.06) * 0.35 : 0.35 + 0.65 * smooth(0.06, 0.3, t)) *
      (t > 0.86 ? Math.sqrt(Math.max(0, 1 - ((t - 0.86) / 0.14) ** 2)) : 1);
    const bend = (t) => Math.sin(t * Math.PI) * RH * 0.03 * (row % 2 ? 1 : -1);
    ctx.save();
    ctx.beginPath();
    for (let k = 0; k <= 200; k++) {
      const t = k / 200;
      ctx.lineTo(x0 + len * t, mid + bend(t) - width(t) * (1 + 0.02 * Math.sin(t * 40)));
    }
    for (let k = 200; k >= 0; k--) {
      const t = k / 200;
      ctx.lineTo(x0 + len * t, mid + bend(t) + width(t) * 0.94);
    }
    ctx.closePath();
    ctx.clip();
    // Blade colour: lighter along the midrib, darker and drier towards the edge.
    const g = ctx.createLinearGradient(0, mid - half, 0, mid + half);
    g.addColorStop(0, rgb(mix3(look.edge, [120, 100, 50], look.dry * 0.5)));
    g.addColorStop(0.5, rgb(look.top));
    g.addColorStop(1, rgb(mix3(look.edge, [120, 100, 50], look.dry * 0.5)));
    ctx.fillStyle = g;
    ctx.fillRect(0, y0, W, RH);
    // The blade is pleated along its veins: broad light and dark bands across it.
    for (let x = x0; x < x1;) {
      const w = r(10, 34);
      ctx.fillStyle =
        r() < 0.5 ? `rgba(255,255,200,${r(0.03, 0.09)})` : `rgba(0,25,0,${r(0.05, 0.14)})`;
      ctx.fillRect(x, y0, w, RH);
      x += w;
    }
    // Parallel side veins, nearly square to the midrib, curving towards the tip.
    for (let x = x0; x < x1; x += 3 + r() * 3) {
      const t = (x - x0) / len;
      for (const side of [-1, 1]) {
        ctx.strokeStyle = r() < 0.5 ? "rgba(255,255,210,0.10)" : "rgba(0,20,0,0.12)";
        ctx.lineWidth = 1 + r() * 1.5;
        ctx.beginPath();
        ctx.moveTo(x, mid + bend(t));
        ctx.quadraticCurveTo(
          x + 6,
          mid + bend(t) + side * width(t) * 0.6,
          x + 22,
          mid + bend(t) + side * width(t) * 1.05,
        );
        ctx.stroke();
      }
    }
    // Dry, yellowed margins and brown spots.
    ctx.lineWidth = 18;
    ctx.strokeStyle = rgb([150, 120, 60], 0.25 + 0.4 * look.dry);
    ctx.stroke();
    for (let k = 0; k < 40 * (0.3 + look.dry); k++) {
      const x = r(x0, x1),
        y = mid + r(-1, 1) * half;
      ctx.fillStyle = rgb([90, 62, 30], r(0.1, 0.35));
      ctx.beginPath();
      ctx.ellipse(x, y, r(2, 12), r(2, 7), r(0, 3), 0, Math.PI * 2);
      ctx.fill();
    }
    // The midrib: a pale, raised channel.
    ctx.restore();
    ctx.beginPath();
    for (let k = 0; k <= 100; k++) {
      const t = k / 100;
      ctx.lineTo(x0 + len * t, mid + bend(t));
    }
    ctx.lineCap = "round";
    ctx.strokeStyle = rgb(mix3([170, 180, 110], [170, 140, 90], look.dry));
    ctx.lineWidth = 9;
    ctx.stroke();
    ctx.strokeStyle = "rgba(40,50,20,0.35)";
    ctx.lineWidth = 2;
    ctx.stroke();
    // Wind tears: cuts along the veins from the edge towards the midrib.
    ctx.globalCompositeOperation = "destination-out";
    ctx.strokeStyle = "#000";
    ctx.lineCap = "butt";
    for (let k = 0; k < look.tears; k++) {
      const t = r(0.12, 0.95),
        side = r() < 0.5 ? -1 : 1;
      const x = x0 + len * t,
        depth = width(t) * r(0.35, 0.97);
      const ex = x + 22,
        ey = mid + bend(t) + side * width(t) * 1.1;
      ctx.lineWidth = r(1.5, 5);
      ctx.beginPath();
      ctx.moveTo(ex, ey);
      ctx.lineTo(x + 6, mid + bend(t) + side * (width(t) - depth));
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
  });
  mottle(ctx, W, H, 40, 15, 0.25);
  hardAlpha(ctx, W, H);
}

/** A sugar (Borassus) palm's fan: stiff pleated segments, split and drooping at the tips. */
function paintPalmFan(ctx, W, H) {
  const r = rng(42);
  const ox = W / 2,
    oy = H * 0.82,
    R = W * 0.47,
    n = 58;
  const a0 = -Math.PI * 0.96,
    a1 = -Math.PI * 0.04;
  for (let k = 0; k < n; k++) {
    const a = lerp(a0, a1, (k + 0.5) / n),
      da = (a1 - a0) / n;
    const rr = R * (0.82 + 0.18 * r());
    const split = rr * r(0.45, 0.6);
    const at = (ang, rad) => [ox + Math.cos(ang) * rad, oy + Math.sin(ang) * rad];
    // Each segment is folded along its middle: one half lit, one in shade. The
    // segments are joined near the stalk and split into pointed tips further out.
    for (const half of [0, 1]) {
      const edge = a + (half ? da / 2 : -da / 2);
      const lit = half ? [104, 118, 70] : [70, 84, 46];
      const g = ctx.createLinearGradient(ox, oy, ...at(a, rr));
      g.addColorStop(0, rgb(mix3(lit, [130, 120, 70], 0.3)));
      g.addColorStop(0.7, rgb(lit));
      g.addColorStop(1, rgb(mix3(lit, [140, 110, 60], 0.6)));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(...at(edge, split));
      ctx.quadraticCurveTo(...at(edge + (a - edge) * 0.3, rr * 0.85), ...at(a, rr));
      ctx.closePath();
      ctx.fill();
    }
    ctx.strokeStyle = "rgba(220,220,170,0.25)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(ox, oy);
    ctx.lineTo(...at(a, rr));
    ctx.stroke();
  }
  mottle(ctx, W, H, 30, 4, 0.3);
  // The petiole: a stout stalk with toothed edges, down to the bottom of the card.
  ctx.fillStyle = "rgb(84,82,52)";
  ctx.beginPath();
  ctx.moveTo(ox - 14, H);
  ctx.lineTo(ox - 9, oy);
  ctx.lineTo(ox + 9, oy);
  ctx.lineTo(ox + 14, H);
  ctx.fill();
  ctx.fillStyle = "rgb(60,56,34)";
  for (let y = oy; y < H; y += 9) {
    ctx.beginPath();
    ctx.moveTo(ox - 12, y);
    ctx.lineTo(ox - 18, y + 4);
    ctx.lineTo(ox - 12, y + 7);
    ctx.moveTo(ox + 12, y);
    ctx.lineTo(ox + 18, y + 4);
    ctx.lineTo(ox + 12, y + 7);
    ctx.fill();
  }
  hardAlpha(ctx, W, H);
}

/** A coconut frond: a long rachis (base on the left) with narrow leaflets on both sides. */
function paintCoconut(ctx, W, H) {
  const r = rng(77);
  const rows = 2,
    RH = H / rows;
  for (let row = 0; row < rows; row++) {
    const mid = row * RH + RH / 2,
      x0 = 10,
      x1 = W - 10;
    const spine = (t) => mid + Math.sin(t * Math.PI * 0.9) * RH * 0.06;
    for (let k = 0; k < 150; k++) {
      const t = 0.08 + 0.9 * (k / 150);
      const x = lerp(x0, x1, t),
        L = RH * 0.46 * Math.sin(Math.PI * Math.min(1, t * 1.05)) * (0.85 + 0.15 * r());
      for (const side of [-1, 1]) {
        const ang = side * (0.95 + r(-0.12, 0.12)),
          dry = r() < 0.08 + 0.2 * row;
        const c = dry ? [130, 108, 60] : mix3([92, 116, 50], [124, 138, 64], r());
        ctx.fillStyle = rgb(c);
        const ex = x + Math.cos(ang) * L * 0.55,
          ey = spine(t) + Math.sin(ang) * L;
        ctx.beginPath();
        ctx.moveTo(x - 3, spine(t));
        ctx.quadraticCurveTo(x + (ex - x) * 0.4 - 5, spine(t) + (ey - spine(t)) * 0.5, ex, ey);
        ctx.quadraticCurveTo(
          x + (ex - x) * 0.4 + 6,
          spine(t) + (ey - spine(t)) * 0.5,
          x + 5,
          spine(t),
        );
        ctx.fill();
        ctx.strokeStyle = "rgba(230,230,170,0.3)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, spine(t));
        ctx.lineTo(ex, ey);
        ctx.stroke();
      }
    }
    ctx.strokeStyle = "rgb(150,140,80)";
    ctx.lineCap = "round";
    ctx.beginPath();
    for (let k = 0; k <= 60; k++) ctx.lineTo(lerp(x0, x1, k / 60), spine(k / 60));
    ctx.lineWidth = 7;
    ctx.stroke();
  }
  mottle(ctx, W, H, 24, 9, 0.3);
  hardAlpha(ctx, W, H);
}

// ------------------------------------------------------------- cloth and mats

/**
 * The white crocodile flag (ទង់ក្រពើ) hung on a tall bamboo pole outside a
 * house where someone has died. White cotton cut to the animal's shape and
 * drawn over in charcoal: head at the top, tied to the pole's tip, legs spread,
 * the tail hanging down. Rain-soaked and mud-splashed at the hem.
 * Shape and drawing to confirm with the cultural advisor (Cultural Guide 6, #2).
 */
function paintCrocodileFlag(ctx, W, H) {
  const r = rng(1932);
  const c = W / 2;
  // Half-width of the body down the flag (y from 0 to H).
  const body = (y) => {
    const t = y / H;
    if (t < 0.03) return 12 + (t / 0.03) * 30; // snout
    if (t < 0.12) return 42 + ((t - 0.03) / 0.09) * 58; // head
    if (t < 0.15) return 100 - ((t - 0.12) / 0.03) * 26; // neck
    if (t < 0.48) return 74 + Math.sin(((t - 0.15) / 0.33) * Math.PI) * 52; // belly
    return 76 * Math.pow(1 - (t - 0.48) / 0.52, 0.9) + 4; // tail
  };
  const legs = [
    [0.19, -1],
    [0.19, 1],
    [0.41, -1],
    [0.41, 1],
  ];
  ctx.fillStyle = "#e7e1d1";
  ctx.beginPath();
  for (let y = 0; y <= H; y += 8) {
    const zig = y / H > 0.5 ? (Math.floor(y / 24) % 2 ? 7 : -3) : 0; // scutes along the tail
    ctx.lineTo(c - body(y) - zig, y);
  }
  for (let y = H; y >= 0; y -= 8) {
    const zig = y / H > 0.5 ? (Math.floor(y / 24) % 2 ? 7 : -3) : 0;
    ctx.lineTo(c + body(y) + zig, y);
  }
  ctx.closePath();
  ctx.fill();
  for (const [t, side] of legs) {
    const y = t * H,
      back = t > 0.3;
    ctx.beginPath();
    ctx.moveTo(c + side * body(y) * 0.8, y - 34);
    ctx.quadraticCurveTo(
      c + side * (body(y) + 70),
      y + (back ? 10 : -20),
      c + side * (body(y) + 118),
      y + (back ? 64 : 20),
    );
    // Toes: three to five fingers spread at the end of the limb.
    for (let k = 0; k < 4; k++) {
      const a = (back ? 0.7 : 0.3) + k * 0.35;
      ctx.lineTo(
        c + side * (body(y) + 118 + Math.cos(a) * 34),
        y + (back ? 64 : 20) + Math.sin(a) * 34,
      );
      ctx.lineTo(
        c + side * (body(y) + 112 + Math.cos(a + 0.18) * 12),
        y + (back ? 64 : 20) + Math.sin(a + 0.18) * 12,
      );
    }
    ctx.quadraticCurveTo(c + side * (body(y) + 40), y + 40, c + side * body(y) * 0.8, y + 40);
    ctx.fill();
  }
  // The weave, soft folds where it hangs, rain and grime.
  mottle(ctx, W, H, 30, 21, 0.14);
  ctx.globalCompositeOperation = "source-atop";
  for (let x = 0; x < W; x += 1) {
    const f = Math.sin(x / 23) * 0.5 + Math.sin(x / 9 + 1) * 0.3;
    ctx.fillStyle = f > 0 ? `rgba(255,255,255,${0.05 * f})` : `rgba(60,55,45,${-0.12 * f})`;
    ctx.fillRect(x, 0, 1, H);
  }
  const hem = ctx.createLinearGradient(0, H * 0.55, 0, H);
  hem.addColorStop(0, "rgba(90,70,50,0)");
  hem.addColorStop(1, "rgba(90,70,50,0.55)");
  ctx.fillStyle = hem;
  ctx.fillRect(0, 0, W, H);
  for (let k = 0; k < 160; k++) {
    const y = H * (0.6 + 0.4 * r() ** 0.5);
    ctx.fillStyle = `rgba(80,58,38,${r(0.1, 0.4)})`;
    ctx.beginPath();
    ctx.arc(r(0, W), y, r(1, 5), 0, Math.PI * 2);
    ctx.fill();
  }
  // Charcoal drawing: outline, eyes and nostrils, the ridges of the back, the scales.
  const ink = (a = 0.85) => `rgba(28,24,22,${a})`;
  ctx.strokeStyle = ink();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = 5;
  ctx.beginPath();
  for (let y = 10; y <= H - 30; y += 12) ctx.lineTo(c - body(y) + 12 + r(-1.5, 1.5), y);
  ctx.stroke();
  ctx.beginPath();
  for (let y = 10; y <= H - 30; y += 12) ctx.lineTo(c + body(y) - 12 + r(-1.5, 1.5), y);
  ctx.stroke();
  for (const side of [-1, 1]) {
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.ellipse(c + side * 38, H * 0.085, 15, 11, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = ink(0.9);
    ctx.beginPath();
    ctx.arc(c + side * 36, H * 0.087, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(c + side * 9, H * 0.018, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(c - 30, H * 0.03);
  ctx.quadraticCurveTo(c - 55, H * 0.1, c - 20, H * 0.125);
  ctx.moveTo(c + 30, H * 0.03);
  ctx.quadraticCurveTo(c + 55, H * 0.1, c + 20, H * 0.125);
  ctx.stroke();
  // Back ridges: rows of chevrons down the spine and dots for the scutes.
  for (let y = H * 0.16; y < H * 0.95; y += r(34, 46)) {
    const w = body(y) * r(0.45, 0.6);
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(c - w, y + 10);
    ctx.lineTo(c, y);
    ctx.lineTo(c + w, y + 10);
    ctx.stroke();
    for (const side of [-1, 1])
      for (let k = 1; k <= 2; k++) {
        ctx.fillStyle = ink(0.7);
        ctx.beginPath();
        ctx.arc(c + side * w * (k / 2.6), y + 14, 3, 0, Math.PI * 2);
        ctx.fill();
      }
  }
  for (const [t, side] of legs) {
    const y = t * H,
      back = t > 0.3;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(c + side * body(y) * 0.7, y);
    ctx.quadraticCurveTo(
      c + side * (body(y) + 60),
      y + (back ? 20 : -6),
      c + side * (body(y) + 108),
      y + (back ? 60 : 18),
    );
    ctx.stroke();
  }
  ctx.globalCompositeOperation = "source-over";
  hardAlpha(ctx, W, H, 90);
}

/**
 * Gilt panels for the coffin: gold leaf kbach (Khmer ornament) on red lacquer,
 * a border of lotus petals, flame-leaf corners and a lotus medallion, worn
 * through to the black undercoat at the edges. Mapped once over each panel.
 */
function paintCoffinPanel(ctx, W, H) {
  const r = rng(812);
  const red = ctx.createLinearGradient(0, 0, 0, H);
  red.addColorStop(0, "#6e1a12");
  red.addColorStop(1, "#4c100b");
  ctx.fillStyle = red;
  ctx.fillRect(0, 0, W, H);
  mottle(ctx, W, H, 60, 31, 0.25);
  const gold = (a = 1) => {
    const g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, `rgba(196,150,62,${a})`);
    g.addColorStop(0.5, `rgba(226,190,104,${a})`);
    g.addColorStop(1, `rgba(176,128,52,${a})`);
    return g;
  };
  const m = H * 0.07;
  ctx.strokeStyle = gold();
  ctx.lineWidth = H * 0.012;
  ctx.strokeRect(m, m, W - 2 * m, H - 2 * m);
  ctx.lineWidth = H * 0.005;
  ctx.strokeRect(m * 1.9, m * 1.9, W - 3.8 * m, H - 3.8 * m);
  // Border band of lotus petals (ក្បាច់ផ្កាឈូក) between the two gold rules.
  const petal = (x, y, s, a) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(a);
    ctx.beginPath();
    ctx.moveTo(0, s * 0.5);
    ctx.bezierCurveTo(-s * 0.45, s * 0.2, -s * 0.3, -s * 0.35, 0, -s * 0.55);
    ctx.bezierCurveTo(s * 0.3, -s * 0.35, s * 0.45, s * 0.2, 0, s * 0.5);
    ctx.fill();
    ctx.restore();
  };
  ctx.fillStyle = gold();
  const band = (m + m * 1.9) / 2,
    s = m * 0.7;
  for (let x = m * 2.4; x < W - m * 2.2; x += s * 0.9) {
    petal(x, band, s, 0);
    petal(x, H - band, s, Math.PI);
  }
  for (let y = m * 2.4; y < H - m * 2.2; y += s * 0.9) {
    petal(band, y, s, -Math.PI / 2);
    petal(W - band, y, s, Math.PI / 2);
  }
  // Flame-leaf scrolls (kbach phni tes) in the corners of the field.
  const scroll = (x, y, sx, sy) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(sx, sy);
    ctx.lineWidth = H * 0.008;
    ctx.strokeStyle = gold();
    for (let k = 0; k < 3; k++) {
      const L = H * (0.22 - k * 0.05);
      ctx.beginPath();
      ctx.moveTo(0, k * H * 0.04);
      ctx.bezierCurveTo(
        L * 0.6,
        k * H * 0.04,
        L,
        -L * 0.1 + k * H * 0.04,
        L * 0.85,
        -L * 0.45 + k * H * 0.05,
      );
      ctx.bezierCurveTo(L * 0.75, -L * 0.7, L * 0.5, -L * 0.5, L * 0.62, -L * 0.36);
      ctx.stroke();
      petal(L * 0.92, -L * 0.52 + k * H * 0.05, H * 0.045, 0.6);
    }
    ctx.restore();
  };
  const fm = m * 2.3;
  scroll(fm, H - fm, 1, 1);
  scroll(W - fm, H - fm, -1, 1);
  scroll(fm, fm, 1, -1);
  scroll(W - fm, fm, -1, -1);
  // Lotus medallion in the centre.
  const cx = W / 2,
    cy = H / 2,
    R = H * 0.2;
  ctx.lineWidth = H * 0.008;
  ctx.beginPath();
  ctx.ellipse(cx, cy, R * 1.9, R * 1.15, 0, 0, Math.PI * 2);
  ctx.stroke();
  for (let k = 0; k < 16; k++) {
    const a = (k / 16) * Math.PI * 2;
    petal(cx + Math.cos(a) * R * 1.35, cy + Math.sin(a) * R * 0.8, R * 0.5, a + Math.PI / 2);
  }
  ctx.fillStyle = "#5a140e";
  ctx.beginPath();
  ctx.ellipse(cx, cy, R * 0.9, R * 0.55, 0, 0, Math.PI * 2);
  ctx.fill();
  // A lotus in bloom: a fan of petals rising from a cup.
  ctx.fillStyle = gold();
  for (let k = -3; k <= 3; k++)
    petal(cx + k * R * 0.16, cy - R * 0.05 - (3 - Math.abs(k)) * R * 0.04, R * 0.42, k * 0.32);
  ctx.beginPath();
  ctx.ellipse(cx, cy + R * 0.28, R * 0.42, R * 0.12, 0, 0, Math.PI * 2);
  ctx.fill();
  // Wear: gold rubbed through, lacquer chipped to the black undercoat, grime in the lows.
  const n = noise(W, H, 16, 33, 4),
    img = ctx.getImageData(0, 0, W, H),
    p = img.data;
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const i = y * W + x,
        edge = Math.min(x, y, W - x, H - y) / H;
      const wear = 0.85 * smooth(0.7, 0.82, n[i] + (0.08 - Math.min(0.08, edge)) * 2.5);
      p[i * 4] = lerp(p[i * 4], 26, wear);
      p[i * 4 + 1] = lerp(p[i * 4 + 1], 14, wear);
      p[i * 4 + 2] = lerp(p[i * 4 + 2], 10, wear);
    }
  ctx.putImageData(img, 0, 0);
  for (let k = 0; k < 160; k++) {
    ctx.strokeStyle = `rgba(20,8,6,${r(0.08, 0.22)})`;
    ctx.lineWidth = r(0.5, 1.5);
    ctx.beginPath();
    const x = r(0, W),
      y = r(0, H);
    ctx.moveTo(x, y);
    ctx.lineTo(x + r(-30, 30), y + r(-6, 6));
    ctx.stroke();
  }
}

/**
 * A woven reed mat (កន្ទេល): dyed and natural strands in a 2/2 twill, red
 * and green bands with stepped diamonds. Tiles seamlessly; 1 m across.
 */
function paintMat(ctx, W, H) {
  const s = 16,
    n = W / s,
    r = rng(5);
  const straw = [196, 166, 104],
    red = [138, 42, 30],
    green = [46, 74, 44],
    dark = [40, 28, 20];
  const rowColour = (j) => {
    const b = j % 64;
    if (b < 3 || (b > 29 && b < 34)) return red;
    if (b === 4 || b === 28 || b === 35 || b === 59) return dark;
    return straw;
  };
  const colColour = (i, j) => {
    // Stepped diamonds inside the straw bands.
    const bi = i % 32,
      bj = j % 64;
    if (bj > 6 && bj < 27) {
      const d = Math.abs(bi - 16) + Math.abs(bj - 16.5);
      if (d < 9 && d > 5) return green;
      if (d <= 2) return red;
    }
    return straw;
  };
  for (let j = 0; j < n; j++)
    for (let i = 0; i < n; i++) {
      const over = (i + j) % 4 < 2;
      const motif = colColour(i, j);
      const c = motif !== straw ? motif : over ? rowColour(j) : straw;
      const v = 0.85 + 0.2 * r();
      const g = over
        ? ctx.createLinearGradient(i * s, 0, i * s + s, 0)
        : ctx.createLinearGradient(0, j * s, 0, j * s + s);
      g.addColorStop(0, rgb(c.map((x) => x * v * 0.8)));
      g.addColorStop(0.5, rgb(c.map((x) => Math.min(255, x * v * 1.08))));
      g.addColorStop(1, rgb(c.map((x) => x * v * 0.78)));
      ctx.fillStyle = g;
      ctx.fillRect(i * s, j * s, s, s);
      ctx.fillStyle = "rgba(0,0,0,0.28)";
      if (over) ctx.fillRect(i * s, j * s, s, 1.2);
      else ctx.fillRect(i * s, j * s, 1.2, s);
    }
  mottle(ctx, W, H, 128, 6, 0.3);
  // Wear: paler where people sit, a few broken strands.
  for (let k = 0; k < 60; k++) {
    ctx.fillStyle = `rgba(${dark.join(",")},${r(0.2, 0.5)})`;
    ctx.fillRect(Math.floor(r(0, n)) * s + 4, Math.floor(r(0, n)) * s + 4, s - 8, 2);
  }
}

/** The tent's white cotton valance: a gathered band with a scalloped hem. Tiles across. */
function paintValance(ctx, W, H) {
  ctx.fillStyle = "#ece6d8";
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(W, 0);
  const n = 8,
    w = W / n,
    top = H * 0.62;
  ctx.lineTo(W, top);
  for (let k = n - 1; k >= 0; k--) ctx.arc(k * w + w / 2, top, w / 2, 0, Math.PI, false);
  ctx.closePath();
  ctx.fill();
  ctx.globalCompositeOperation = "source-atop";
  for (let x = 0; x < W; x++) {
    const f =
      Math.sin((x / W) * Math.PI * 2 * 16) * 0.6 + Math.sin((x / W) * Math.PI * 2 * 40) * 0.3;
    ctx.fillStyle = f > 0 ? `rgba(255,255,255,${0.06 * f})` : `rgba(70,62,50,${-0.16 * f})`;
    ctx.fillRect(x, 0, 1, H);
  }
  ctx.fillStyle = "rgba(120,110,95,0.35)";
  ctx.fillRect(0, H * 0.1, W, 3);
  ctx.fillRect(0, H * 0.16, W, 1.5);
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "rgba(80,70,55,0.25)");
  g.addColorStop(0.3, "rgba(80,70,55,0)");
  g.addColorStop(1, "rgba(80,70,55,0.18)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  mottle(ctx, W, H, 24, 8, 0.12);
  ctx.globalCompositeOperation = "source-over";
  hardAlpha(ctx, W, H);
}

/** Banana pseudo-stem: overlapping sheaths, fibres and dark blotches. Tiles vertically. */
function paintBananaStem(ctx, W, H) {
  const r = rng(19);
  ctx.fillStyle = "rgb(112,128,64)";
  ctx.fillRect(0, 0, W, H);
  for (let k = 0; k < 9; k++) {
    const x = (k / 9) * W,
      w = W / 9 + r(10, 40);
    const g = ctx.createLinearGradient(x, 0, x + w, 0);
    const c = mix3([110, 128, 60], [150, 140, 80], r());
    g.addColorStop(0, rgb(c.map((v) => v * 0.7)));
    g.addColorStop(0.3, rgb(c));
    g.addColorStop(1, rgb(c.map((v) => v * 0.85)));
    ctx.fillStyle = g;
    ctx.fillRect(x, 0, w, H);
  }
  for (let x = 0; x < W; x += 2) {
    ctx.fillStyle = `rgba(${r() < 0.5 ? "255,255,220" : "20,30,0"},${r(0.03, 0.1)})`;
    ctx.fillRect(x, 0, 1, H);
  }
  for (let k = 0; k < 60; k++) {
    const x = r(0, W),
      y = r(0, H);
    ctx.fillStyle = `rgba(${r() < 0.6 ? "70,40,40" : "120,90,50"},${r(0.15, 0.45)})`;
    ctx.beginPath();
    ctx.ellipse(x, y, r(4, 18), r(10, 60), 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.ellipse(x, y + H, r(4, 18), r(10, 60), 0, 0, Math.PI * 2);
    ctx.fill();
  }
  mottle(ctx, W, H, 64, 20, 0.25);
}

/** A bamboo culm: yellow-tan, greyed by weather, one node per tile. Wraps round a pole. */
function paintBamboo(ctx, W, H) {
  const r = rng(23);
  const g = ctx.createLinearGradient(0, 0, W, 0);
  g.addColorStop(0, "rgb(150,126,74)");
  g.addColorStop(0.5, "rgb(176,150,92)");
  g.addColorStop(1, "rgb(150,126,74)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  for (let x = 0; x < W; x += 2) {
    ctx.fillStyle = `rgba(${r() < 0.5 ? "255,240,200" : "60,45,20"},${r(0.03, 0.1)})`;
    ctx.fillRect(x, 0, r(1, 3), H);
  }
  mottle(ctx, W, H, 50, 24, 0.4);
  // Grey weathering and black mould streaks running down from the node.
  for (let k = 0; k < 30; k++) {
    const x = r(0, W),
      y = H * 0.5 + r(0, H * 0.4);
    const s = ctx.createLinearGradient(0, H * 0.5, 0, y + 80);
    s.addColorStop(0, "rgba(40,36,30,0.45)");
    s.addColorStop(1, "rgba(40,36,30,0)");
    ctx.fillStyle = s;
    ctx.fillRect(x, H * 0.5, r(6, 30), y - H * 0.5 + 80);
  }
  // The node: a dark joint line with a pale raised collar above and below.
  const y = H * 0.5;
  ctx.fillStyle = "rgba(220,200,150,0.5)";
  ctx.fillRect(0, y - 14, W, 10);
  ctx.fillRect(0, y + 6, W, 6);
  ctx.fillStyle = "rgba(50,38,22,0.85)";
  ctx.fillRect(0, y - 3, W, 6);
}

/** A sugar palm trunk: near-black, ringed with old leaf scars, split by long cracks. Tiles vertically. */
function paintPalmTrunk(ctx, W, H) {
  const r = rng(31);
  ctx.fillStyle = "rgb(64,58,52)";
  ctx.fillRect(0, 0, W, H);
  mottle(ctx, W, H, 40, 32, 0.5);
  for (let y = 0; y < H; y += r(40, 90)) {
    ctx.fillStyle = `rgba(20,16,14,${r(0.35, 0.7)})`;
    ctx.beginPath();
    ctx.moveTo(0, y);
    for (let x = 0; x <= W; x += 32) ctx.lineTo(x, y + Math.sin(x / 60 + y) * 6 + r(-2, 2));
    for (let x = W; x >= 0; x -= 32) ctx.lineTo(x, y + r(5, 12) + Math.sin(x / 60 + y) * 6);
    ctx.fill();
    ctx.fillStyle = "rgba(140,128,110,0.18)";
    ctx.fillRect(0, y - 4, W, 3);
  }
  for (let k = 0; k < 40; k++) {
    ctx.strokeStyle = `rgba(15,12,10,${r(0.3, 0.7)})`;
    ctx.lineWidth = r(1, 3);
    const x = r(0, W),
      y = r(0, H);
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + r(-6, 6), y + r(60, 260));
    ctx.stroke();
  }
}

/**
 * The storm sky, an equirectangular map (wraps left to right): one low, heavy
 * overcast of rain cloud at night, dark slate, its folds showing only as small
 * changes of tone; a little lighter where the moon is hidden behind it and in the
 * rain haze low down, so the village's far treeline of sugar palms, coconut palms
 * and bamboo stands black against it. No stars and no moon: it is raining.
 */
function paintSky(ctx, W, H) {
  const r = rng(77);
  // Periodic value noise in x, so the sky has no seam.
  const wrapNoise = (cell, seed, oct, stretch = 1) => {
    const out = new Float32Array(W * H);
    const rr = rng(seed);
    let amp = 1,
      total = 0;
    for (let o = 0; o < oct; o++) {
      const c = cell / 2 ** o;
      const gw = Math.max(2, Math.round(W / (c * stretch))),
        gh = Math.ceil(H / c) + 2;
      const g = new Float32Array(gw * gh).map(() => rr());
      for (let y = 0; y < H; y++) {
        const fy = y / c,
          iy = Math.floor(fy),
          ty = fy - iy,
          sy = ty * ty * (3 - 2 * ty);
        for (let x = 0; x < W; x++) {
          const fx = (x / W) * gw,
            ix = Math.floor(fx) % gw,
            tx = fx - Math.floor(fx),
            sx = tx * tx * (3 - 2 * tx);
          const ix1 = (ix + 1) % gw;
          const a = g[iy * gw + ix],
            b = g[iy * gw + ix1],
            d = g[(iy + 1) * gw + ix],
            e = g[(iy + 1) * gw + ix1];
          out[y * W + x] += amp * lerp(lerp(a, b, sx), lerp(d, e, sx), sy);
        }
      }
      total += amp;
      amp *= 0.55;
    }
    for (let i = 0; i < out.length; i++) out[i] /= total;
    return out;
  };
  // Storm cloud lies in layers: stretched sideways, rolled by a second noise.
  const base = wrapNoise(110, 3, 6, 3.2),
    warp = wrapNoise(70, 5, 3, 2),
    rolls = wrapNoise(40, 9, 3, 1.5);
  const img = ctx.createImageData(W, H),
    p = img.data;
  const moonU = 0.62,
    moonV = 0.24;
  for (let y = 0; y < H; y++) {
    const v = y / H; // 0 at the zenith, 0.5 at the horizon
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      const wx = Math.floor((x + (warp[i] - 0.5) * 260 + W) % W);
      const wy = Math.min(H - 1, Math.max(0, Math.floor(y + (rolls[i] - 0.5) * 60)));
      const n = base[wy * W + wx];
      // The cloud's folds: faint rims where one layer rolls over another.
      const rim = smooth(0.48, 0.55, n) - smooth(0.6, 0.72, n);
      let du = Math.abs(x / W - moonU);
      du = Math.min(du, 1 - du);
      const moon = Math.exp(-((du * 2.2) ** 2 + ((v - moonV) * 3.2) ** 2));
      const horizon = smooth(0.25, 0.5, v) * (1 - smooth(0.5, 0.56, v));
      const light = clamp(0.2 * n + 0.15 * rim + moon * (0.25 + 0.3 * n) + 0.4 * horizon);
      const col = mix3([7, 9, 14], [36, 41, 54], light);
      const below = smooth(0.5, 0.53, v);
      const out = mix3(col, [12, 13, 15], below);
      p[i * 4] = out[0];
      p[i * 4 + 1] = out[1];
      p[i * 4 + 2] = out[2];
      p[i * 4 + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  // The treeline along the horizon: sugar palms' round crowns, coconut fronds,
  // bamboo plumes and the broad tops of other trees, all one dark silhouette.
  const hz = H * 0.5;
  ctx.fillStyle = "rgb(13,14,16)";
  ctx.fillRect(0, hz - 6, W, H - hz + 6);
  const silhouette = (x0) => {
    for (let k = 0; k < 2; k++) {
      const x = x0 + k * W - W * (k ? 1 : 0);
      const kind = r();
      const h = r(18, 46);
      if (kind < 0.35) {
        ctx.fillRect(x - 1.2, hz - h, 2.4, h);
        for (let j = 0; j < 22; j++) {
          const a = r(0, Math.PI * 2),
            l = r(4, 9);
          ctx.beginPath();
          ctx.moveTo(x, hz - h);
          ctx.lineTo(x + Math.cos(a) * l - 2, hz - h + Math.sin(a) * l * 0.8);
          ctx.lineTo(x + Math.cos(a) * l + 2, hz - h + Math.sin(a) * l * 0.8);
          ctx.fill();
        }
      } else if (kind < 0.55) {
        const lean = r(-6, 6);
        ctx.beginPath();
        ctx.moveTo(x - 1, hz);
        ctx.quadraticCurveTo(x + lean * 0.3, hz - h * 0.6, x + lean, hz - h);
        ctx.lineTo(x + lean + 1.6, hz - h);
        ctx.quadraticCurveTo(x + lean * 0.3 + 2, hz - h * 0.6, x + 1, hz);
        ctx.fill();
        for (let j = 0; j < 9; j++) {
          const a = Math.PI + (j / 8) * Math.PI;
          ctx.lineWidth = 1.6;
          ctx.strokeStyle = "rgb(13,14,16)";
          ctx.beginPath();
          ctx.moveTo(x + lean, hz - h);
          ctx.quadraticCurveTo(
            x + lean + Math.cos(a) * 8,
            hz - h - 5,
            x + lean + Math.cos(a) * 13,
            hz - h + 6,
          );
          ctx.stroke();
        }
      } else if (kind < 0.75) {
        for (let j = 0; j < 14; j++) {
          const a = -Math.PI / 2 + r(-0.7, 0.7),
            l = h * r(0.5, 0.9);
          ctx.lineWidth = r(1, 2.5);
          ctx.strokeStyle = "rgb(13,14,16)";
          ctx.beginPath();
          ctx.moveTo(x, hz);
          ctx.quadraticCurveTo(
            x + Math.cos(a) * l * 0.4,
            hz - l * 0.8,
            x + Math.cos(a) * l * 0.9,
            hz - l * 0.9 + l * 0.15,
          );
          ctx.stroke();
        }
      } else {
        for (let j = 0; j < 9; j++) {
          ctx.beginPath();
          ctx.ellipse(x + r(-14, 14), hz - h * r(0.5, 0.9), r(6, 14), r(4, 9), 0, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillRect(x - 6, hz - h * 0.6, 12, h * 0.6);
      }
    }
  };
  for (let x = 0; x < W; x += r(3, 11)) silhouette(x);
  for (let x = 0; x < W; x += 2) {
    const h = 6 + 8 * Math.abs(Math.sin(x * 0.013)) + r(0, 5);
    ctx.fillRect(x, hz - h, 2, h);
  }
}

/** Broad tropical leaves bunched at twig ends, four clusters in a 2 x 2 atlas. */
function paintLeafClusters(ctx, W, H) {
  const r = rng(61);
  const cells = 2,
    S = W / cells;
  for (let cy = 0; cy < cells; cy++)
    for (let cx = 0; cx < cells; cx++) {
      const ox = cx * S,
        oy = cy * S;
      const dry = cy * cells + cx === 3;
      for (let k = 0; k < 70; k++) {
        const a = r(0, Math.PI * 2),
          d = Math.sqrt(r()) * S * 0.36;
        const x = ox + S / 2 + Math.cos(a) * d,
          y = oy + S / 2 + Math.sin(a) * d * 0.85;
        const L = r(S * 0.08, S * 0.15),
          Wd = L * r(0.32, 0.45),
          ang = a + r(-0.6, 0.6);
        const c = dry
          ? mix3([92, 80, 42], [120, 96, 52], r())
          : mix3([30, 52, 22], [62, 88, 36], r());
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(ang);
        const g = ctx.createLinearGradient(0, -Wd, 0, Wd);
        g.addColorStop(0, rgb(c.map((v) => v * 0.75)));
        g.addColorStop(0.5, rgb(c.map((v) => v * 1.15)));
        g.addColorStop(1, rgb(c.map((v) => v * 0.7)));
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.moveTo(-L * 0.5, 0);
        ctx.quadraticCurveTo(0, -Wd, L * 0.5, 0);
        ctx.quadraticCurveTo(0, Wd, -L * 0.5, 0);
        ctx.fill();
        ctx.strokeStyle = "rgba(200,220,150,0.25)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(-L * 0.5, 0);
        ctx.lineTo(L * 0.5, 0);
        ctx.stroke();
        ctx.restore();
      }
      ctx.strokeStyle = "rgb(60,48,34)";
      ctx.lineWidth = 3;
      for (let k = 0; k < 6; k++) {
        const a = r(0, Math.PI * 2);
        ctx.beginPath();
        ctx.moveTo(ox + S / 2, oy + S * 0.98);
        ctx.quadraticCurveTo(
          ox + S / 2,
          oy + S * 0.6,
          ox + S / 2 + Math.cos(a) * S * 0.25,
          oy + S / 2 + Math.sin(a) * S * 0.2,
        );
        ctx.stroke();
      }
    }
  mottle(ctx, W, H, 40, 62, 0.3);
  hardAlpha(ctx, W, H);
}

/** Bamboo: thin twigs with sprays of long narrow leaves. Two sprays in one strip. */
function paintBambooLeaves(ctx, W, H) {
  const r = rng(71);
  for (let row = 0; row < 2; row++) {
    const y0 = row * (H / 2),
      mid = y0 + H / 4;
    ctx.strokeStyle = "rgb(110,96,52)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(4, mid);
    ctx.quadraticCurveTo(W * 0.5, mid - 20, W - 8, mid + 10);
    ctx.stroke();
    for (let k = 0; k < 60; k++) {
      const t = r(0.05, 0.98),
        x = 4 + t * (W - 12),
        y = mid - 20 * Math.sin(t * Math.PI) + 10 * t;
      const side = r() < 0.5 ? -1 : 1,
        L = r(40, 95),
        a = side * r(0.35, 1.0) + 0.25;
      const c = r() < 0.12 ? [120, 108, 60] : mix3([52, 80, 32], [96, 118, 52], r());
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(a);
      ctx.fillStyle = rgb(c);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.quadraticCurveTo(L * 0.4, -L * 0.09, L, 0);
      ctx.quadraticCurveTo(L * 0.4, L * 0.09, 0, 0);
      ctx.fill();
      ctx.restore();
    }
  }
  mottle(ctx, W, H, 20, 72, 0.3);
  hardAlpha(ctx, W, H);
}

/** Grass and rice stubble: a tuft of thin blades, some bent over. */
function paintGrass(ctx, W, H) {
  const r = rng(81);
  for (let k = 0; k < 140; k++) {
    const x = W / 2 + r.normal(W * 0.14),
      h = r(H * 0.35, H * 0.95),
      bend = r(-0.5, 0.5) * h;
    const c =
      r() < 0.3
        ? mix3([120, 112, 62], [150, 130, 76], r())
        : mix3([50, 76, 30], [92, 112, 48], r());
    ctx.fillStyle = rgb(c);
    ctx.beginPath();
    ctx.moveTo(x - 3, H);
    ctx.quadraticCurveTo(x + bend * 0.3, H - h * 0.6, x + bend, H - h);
    ctx.quadraticCurveTo(x + bend * 0.3 + 2, H - h * 0.6, x + 3, H);
    ctx.fill();
  }
  mottle(ctx, W, H, 24, 82, 0.3);
  hardAlpha(ctx, W, H);
}

/** An old crocodile flag left from an earlier death: greyed, mildewed, torn to rags. */
function paintOldFlag(ctx, W, H) {
  paintCrocodileFlag(ctx, W, H);
  const r = rng(1931);
  const img = ctx.getImageData(0, 0, W, H),
    p = img.data;
  const n = noise(W, H, 40, 77, 4),
    m = noise(W, H, 12, 78, 3);
  for (let i = 0; i < W * H; i++) {
    if (!p[i * 4 + 3]) continue;
    const y = Math.floor(i / W) / H;
    const age = 0.55 + 0.45 * n[i];
    p[i * 4] = p[i * 4] * age * 0.78 + 18;
    p[i * 4 + 1] = p[i * 4 + 1] * age * 0.8 + 18;
    p[i * 4 + 2] = p[i * 4 + 2] * age * 0.72 + 14;
    // Mildew blooms and holes eaten through the cloth, worst at the hem.
    if (m[i] > 0.72 - 0.12 * y) {
      p[i * 4] *= 0.55;
      p[i * 4 + 1] *= 0.6;
      p[i * 4 + 2] *= 0.5;
    }
    if (n[i] < 0.22 + 0.25 * y * y) p[i * 4 + 3] = 0;
  }
  ctx.putImageData(img, 0, 0);
  // Torn into strips from the bottom up.
  ctx.globalCompositeOperation = "destination-out";
  ctx.strokeStyle = "#000";
  for (let k = 0; k < 14; k++) {
    const x = r(W * 0.25, W * 0.75);
    ctx.lineWidth = r(3, 10);
    ctx.beginPath();
    ctx.moveTo(x, H);
    ctx.lineTo(x + r(-20, 20), H * r(0.45, 0.85));
    ctx.stroke();
  }
  ctx.globalCompositeOperation = "source-over";
  hardAlpha(ctx, W, H, 90);
}

/** A spider's web strung in a corner: radial threads and a spiral, sagging and broken. */
function paintCobweb(ctx, W, H) {
  const r = rng(91);
  const cx = W * 0.08,
    cy = H * 0.08;
  ctx.strokeStyle = "rgba(230,230,225,0.9)";
  const spokes = 11;
  const ends = [];
  for (let k = 0; k < spokes; k++) {
    const a = (k / (spokes - 1)) * (Math.PI / 2) + r(-0.04, 0.04);
    const L = W * r(0.75, 1.05);
    ends.push([a, L]);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(a) * L, cy + Math.sin(a) * L);
    ctx.stroke();
  }
  ctx.lineWidth = 1.5;
  for (let ring = 0.12; ring < 0.95; ring += r(0.035, 0.06)) {
    ctx.beginPath();
    let open = false;
    for (let k = 0; k < spokes; k++) {
      const [a, L] = ends[k];
      const R = L * ring + r(-4, 4);
      const x = cx + Math.cos(a) * R,
        y = cy + Math.sin(a) * R + ring * 12;
      if (r() < 0.08) {
        open = false;
        continue;
      }
      if (!open) {
        ctx.moveTo(x, y);
        open = true;
      } else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  // Dust caught in the threads.
  for (let k = 0; k < 120; k++) {
    ctx.fillStyle = `rgba(200,195,180,${r(0.3, 0.8)})`;
    ctx.fillRect(r(0, W * 0.8), r(0, H * 0.8), r(1, 3), r(1, 3));
  }
  hardAlpha(ctx, W, H, 60);
}

/** Muddy bare footprints walking up the sheet, left and right, fading as the mud wears off. */
function paintFootprints(ctx, W, H) {
  const r = rng(101);
  const steps = 4;
  for (let k = 0; k < steps; k++) {
    const side = k % 2 ? 1 : -1,
      y = H * (0.88 - k * 0.24),
      x = W / 2 + side * W * 0.16;
    const a = 0.75 - k * 0.15;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(side * 0.08);
    ctx.fillStyle = `rgba(52,36,24,${a})`;
    ctx.beginPath();
    ctx.ellipse(0, 0, W * 0.09, H * 0.075, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(side * W * 0.01, -H * 0.075, W * 0.06, H * 0.05, 0, 0, Math.PI * 2);
    ctx.fill();
    for (let t = 0; t < 5; t++) {
      ctx.beginPath();
      ctx.arc(
        -W * 0.06 * side + t * W * 0.03 * side,
        -H * 0.135 + Math.abs(t - 1) * 3,
        W * (t === 0 ? 0.022 : 0.015),
        0,
        Math.PI * 2,
      );
      ctx.fill();
    }
    ctx.restore();
  }
  for (let k = 0; k < 80; k++) {
    ctx.fillStyle = `rgba(52,36,24,${r(0.1, 0.4)})`;
    ctx.beginPath();
    ctx.arc(r(W * 0.2, W * 0.8), r(0, H), r(1, 4), 0, Math.PI * 2);
    ctx.fill();
  }
}

/**
 * A protective yantra (យ័ន្ត) on white cloth, pinned over the door: a square of
 * ruled cells holding the five syllables na mo bu ddha ya (ន មោ ពុ ទ្ធា យ),
 * enclosed in rings of loops, drawn in red and black ink. Pending review.
 */
function paintYantra(ctx, W, H, data) {
  const draw = () => {
    ctx.fillStyle = "#e6dfcf";
    ctx.fillRect(0, 0, W, H);
    mottle(ctx, W, H, 50, 111, 0.18);
    const cx = W / 2,
      cy = H / 2;
    ctx.strokeStyle = "rgba(30,24,20,0.9)";
    ctx.lineWidth = 3;
    ctx.strokeRect(W * 0.08, H * 0.08, W * 0.84, H * 0.84);
    ctx.strokeStyle = "rgba(140,30,22,0.85)";
    ctx.lineWidth = 2;
    for (let k = 0; k < 28; k++) {
      const a = (k / 28) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx + Math.cos(a) * W * 0.36, cy + Math.sin(a) * H * 0.36, W * 0.035, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.strokeStyle = "rgba(30,24,20,0.9)";
    ctx.beginPath();
    ctx.arc(cx, cy, W * 0.3, 0, Math.PI * 2);
    ctx.stroke();
    const g = W * 0.36;
    ctx.strokeRect(cx - g / 2, cy - g / 2, g, g);
    for (let k = 1; k < 3; k++) {
      ctx.beginPath();
      ctx.moveTo(cx - g / 2 + (g * k) / 3, cy - g / 2);
      ctx.lineTo(cx - g / 2 + (g * k) / 3, cy + g / 2);
      ctx.moveTo(cx - g / 2, cy - g / 2 + (g * k) / 3);
      ctx.lineTo(cx + g / 2, cy - g / 2 + (g * k) / 3);
      ctx.stroke();
    }
    ctx.fillStyle = "rgba(30,24,20,0.92)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = `${Math.round(W * 0.07)}px Freehand`;
    const cells = [
      [0, 1],
      [1, 0],
      [1, 1],
      [1, 2],
      [2, 1],
    ];
    data.syllables.forEach((syl, i) => {
      const [row, col] = cells[i];
      ctx.fillText(syl, cx - g / 2 + (g * (col + 0.5)) / 3, cy - g / 2 + (g * (row + 0.5)) / 3);
    });
    ctx.font = `${Math.round(W * 0.05)}px Freehand`;
    ctx.fillStyle = "rgba(140,30,22,0.85)";
    for (let k = 0; k < 4; k++) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate((k * Math.PI) / 2);
      ctx.fillText(data.border, 0, -H * 0.42);
      ctx.restore();
    }
    // Smoke-darkened and rain-stained.
    const stain = ctx.createLinearGradient(0, 0, 0, H);
    stain.addColorStop(0, "rgba(60,45,30,0.3)");
    stain.addColorStop(0.3, "rgba(60,45,30,0)");
    stain.addColorStop(1, "rgba(60,45,30,0.25)");
    ctx.fillStyle = stain;
    ctx.fillRect(0, 0, W, H);
  };
  document.fonts.load(`40px Freehand`).then(draw);
}

/** Rain-worn woven sack and charcoal marks; UV front is U=.5, V=.6. */
function paintTingMongFace(ctx, W, H) {
  const r = rng(131);
  ctx.fillStyle = "#958c73";
  ctx.fillRect(0, 0, W, H);
  mottle(ctx, W, H, 55, 132, 0.32);
  // Broad damp tide marks and mildew, under the cloth's visible weave.
  for (let k = 0; k < 240; k++) {
    const x = r(0, W),
      y = r(0, H),
      radius = r(4, 70);
    const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
    g.addColorStop(0, `rgba(30,32,23,${r(0.04, 0.22)})`);
    g.addColorStop(1, "rgba(30,32,23,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  }
  // Soot has soaked into the fibres: uneven blind marks, with no outlined eyes/pupils.
  for (const [u, v, rw, rh] of [
    [0.435, 0.39, 0.03, 0.026],
    [0.565, 0.36, 0.027, 0.022],
  ]) {
    ctx.save();
    ctx.translate(W * u, H * v);
    ctx.rotate(u < 0.5 ? -0.13 : 0.09);
    const stain = ctx.createRadialGradient(0, 0, 0, 0, 0, W * 0.055);
    stain.addColorStop(0, "rgba(18,18,14,.9)");
    stain.addColorStop(0.48, "rgba(26,26,20,.62)");
    stain.addColorStop(1, "rgba(30,29,23,0)");
    ctx.scale(1, 0.7);
    ctx.fillStyle = stain;
    ctx.fillRect(-W * 0.06, -W * 0.06, W * 0.12, W * 0.12);
    for (let j = 0; j < 45; j++) {
      ctx.fillStyle = `rgba(12,13,11,${r(0.12, 0.4)})`;
      ctx.beginPath();
      ctx.ellipse(r(-4, 4), r(-3, 3), W * rw * r(0.7, 1), H * rh * r(0.6, 1), 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    for (let j = 0; j < 10; j++) {
      const x = W * u + r(-W * rw, W * rw),
        y = H * v;
      const g = ctx.createLinearGradient(0, y, 0, y + H * 0.35);
      g.addColorStop(0, "rgba(24,25,18,.25)");
      g.addColorStop(1, "rgba(24,25,18,0)");
      ctx.fillStyle = g;
      ctx.fillRect(x, y, r(1, 3), H * r(0.18, 0.35));
    }
  }
  // Collapsed seam across the lower face, roughly repaired by hand.
  ctx.strokeStyle = "rgba(23,22,17,.8)";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(W * 0.443, H * 0.675);
  ctx.bezierCurveTo(W * 0.477, H * 0.67, W * 0.51, H * 0.7, W * 0.553, H * 0.684);
  ctx.stroke();
  for (let j = 0; j < 9; j++) {
    const x = W * (0.447 + j * 0.012),
      y = H * (0.676 + j * 0.001);
    ctx.lineWidth = r(1, 2);
    ctx.beginPath();
    ctx.moveTo(x - 2, y - r(3, 6));
    ctx.lineTo(x + r(-1, 3), y + r(3, 7));
    ctx.stroke();
  }
  // Flat-felled side seam and pinprick stitching follow the sack round its back.
  ctx.strokeStyle = "rgba(35,32,23,.3)";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(W * 0.12, 0);
  ctx.lineTo(W * 0.13, H);
  ctx.stroke();
  for (let y = 0; y < H; y += 9) {
    ctx.fillStyle = "rgba(40,35,25,.6)";
    ctx.fillRect(W * (0.12 + (0.01 * y) / H) - 3, y, 7, 1.4);
  }
  for (let x = 0; x < W; x += 3) {
    ctx.fillStyle = `rgba(211,200,165,${r(0.035, 0.1)})`;
    ctx.fillRect(x, 0, 1, H);
  }
  for (let y = 0; y < H; y += 3) {
    ctx.fillStyle = `rgba(23,25,18,${r(0.04, 0.1)})`;
    ctx.fillRect(0, y, W, 1);
  }
}

/** Desaturated, weather-stained cotton with faded checks on the wrap. */
function paintGuardianCloth(ctx, W, H, wrap) {
  const r = rng(wrap ? 414 : 413);
  ctx.fillStyle = wrap ? "#51453b" : "#454741";
  ctx.fillRect(0, 0, W, H);
  mottle(ctx, W, H, 70, 415, 0.28);
  if (wrap) {
    for (let i = 0; i < W; i += 64) {
      ctx.fillStyle = "rgba(25,28,25,.24)";
      ctx.fillRect(i, 0, 12, H);
      ctx.fillRect(0, i, W, 12);
      ctx.fillStyle = "rgba(160,141,108,.12)";
      ctx.fillRect(i + 20, 0, 2, H);
      ctx.fillRect(0, i + 20, W, 2);
    }
  }
  for (let j = 0; j < 420; j++) {
    const x = r(0, W),
      y = r(0, H),
      radius = r(8, 140);
    const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
    g.addColorStop(0, `rgba(16,22,17,${r(0.03, 0.18)})`);
    g.addColorStop(1, "rgba(16,22,17,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  }
  for (let i = 0; i < W; i += 3) {
    ctx.fillStyle = `rgba(172,163,140,${r(0.025, 0.09)})`;
    ctx.fillRect(i, 0, 1, H);
    ctx.fillStyle = `rgba(10,16,13,${r(0.04, 0.12)})`;
    ctx.fillRect(0, i, W, 1);
  }
  for (let j = 0; j < 1600; j++) {
    ctx.fillStyle = r() < 0.5 ? "rgba(172,158,119,.1)" : "rgba(8,14,10,.15)";
    ctx.fillRect(r(0, W), r(0, H), r(1, 2), r(2, 8));
  }
}

/** Analytic tangent-space thread relief; repeatable edges for tiled clothing UVs. */
function paintGuardianWeave(ctx, W, H) {
  const data = ctx.createImageData(W, H);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const ax = (x / W) * Math.PI * 512,
        ay = (y / H) * Math.PI * 512;
      const dx = Math.cos(ax) * 0.38 * (1 + 0.25 * Math.sin(ay));
      const dy = Math.cos(ay) * 0.38 * (1 + 0.25 * Math.sin(ax));
      const norm = Math.sqrt(dx * dx + dy * dy + 1),
        i = (y * W + x) * 4;
      data.data[i] = Math.round(127.5 - (dx / norm) * 127.5);
      data.data[i + 1] = Math.round(127.5 - (dy / norm) * 127.5);
      data.data[i + 2] = Math.round(127.5 + 127.5 / norm);
      data.data[i + 3] = 255;
    }
  ctx.putImageData(data, 0, 0);
}

/** A colonial road marker (borne kilométrique): white stone, red cap, the town and distance. */
function paintMilestone(ctx, W, H) {
  ctx.fillStyle = "#cfc9bb";
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#7a2a1e";
  ctx.fillRect(0, 0, W, H * 0.32);
  mottle(ctx, W, H, 24, 141, 0.35);
  ctx.fillStyle = "rgba(25,22,20,0.9)";
  ctx.textAlign = "center";
  ctx.font = `bold ${Math.round(H * 0.075)}px Georgia, serif`;
  ctx.fillText("BATTAMBANG", W * 0.25, H * 0.52);
  ctx.font = `bold ${Math.round(H * 0.16)}px Georgia, serif`;
  ctx.fillText("4", W * 0.25, H * 0.74);
  ctx.font = `${Math.round(H * 0.05)}px Georgia, serif`;
  ctx.fillText("KM", W * 0.25, H * 0.84);
  ctx.font = `bold ${Math.round(H * 0.075)}px Georgia, serif`;
  ctx.fillText("MONGKOLBOREI", W * 0.75, H * 0.52);
  ctx.font = `bold ${Math.round(H * 0.16)}px Georgia, serif`;
  ctx.fillText("31", W * 0.75, H * 0.74);
  ctx.font = `${Math.round(H * 0.05)}px Georgia, serif`;
  ctx.fillText("KM", W * 0.75, H * 0.84);
  const g = ctx.createLinearGradient(0, H * 0.6, 0, H);
  g.addColorStop(0, "rgba(60,50,30,0)");
  g.addColorStop(1, "rgba(60,50,30,0.6)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
}

/** Red betel-juice spat and spilled on stone: splashes and drips, dried dark at the edges. */
function paintStains(ctx, W, H) {
  const r = rng(151);
  for (let k = 0; k < 14; k++) {
    const x = r(W * 0.1, W * 0.9),
      y = r(H * 0.1, H * 0.9),
      s = r(10, 40);
    const g = ctx.createRadialGradient(x, y, 0, x, y, s);
    g.addColorStop(0, "rgba(110,14,10,0.95)");
    g.addColorStop(0.7, "rgba(80,12,8,0.9)");
    g.addColorStop(1, "rgba(60,10,6,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    for (let a = 0; a <= 24; a++) {
      const t = (a / 24) * Math.PI * 2,
        rr = s * (0.7 + 0.4 * r());
      ctx.lineTo(x + Math.cos(t) * rr, y + Math.sin(t) * rr * 0.8);
    }
    ctx.fill();
    for (let j = 0; j < 8; j++) {
      ctx.fillStyle = `rgba(90,12,8,${r(0.6, 1)})`;
      ctx.beginPath();
      ctx.arc(x + r(-2.5, 2.5) * s, y + r(-2.5, 2.5) * s, r(1, 5), 0, Math.PI * 2);
      ctx.fill();
    }
  }
  hardAlpha(ctx, W, H, 100);
}

export const villageTextures = [
  { name: "photo_sok", file: "T_ep1_photo_sok_BC", size: [768, 1024], draw: portrait },
  {
    name: "flame",
    file: "T_ep1_flame_BC",
    size: [128, 256],
    alpha: true,
    draw: () => canvasPage(128, 256, paintFlame),
  },
  {
    name: "kanha_drawing",
    file: "T_ep1_kanha_drawing_BC",
    size: [512, 512],
    draw: () => canvasPage(512, 512, paintKanhaDrawing),
  },
  {
    name: "sok_notes",
    file: "T_ep1_sok_notes_BC",
    size: [512, 720],
    alpha: true,
    draw: () =>
      canvasPage(512, 720, paintSokNotes, { debt: "បំណុល", years: ["១៩១១", "១៩២០", "១៩៣២"] }),
  },
  {
    name: "shadow_figure",
    file: "T_ep1_shadow_figure_BC",
    size: [512, 1024],
    alpha: true,
    draw: () => canvasPage(512, 1024, paintShadowFigure),
  },
  { name: "family_prints", file: "T_ep1_family_prints_BC", size: [2560, 716], draw: familyPrints },
  {
    name: "house_papers",
    file: "T_ep1_house_papers_BC",
    size: [2048, 1024],
    // Rectangles (x, y, w, h) in pixels; ep1_area_village.py maps the same ones.
    draw: () =>
      canvasPage(2048, 1024, paintHousePapers, {
        calendar: [0, 0, 640, 1024],
        receipt: [640, 0, 512, 720],
        certificate: [1152, 0, 716, 1024],
        khmer: {
          calendar: "ប្រតិទិន ១៩៣២",
          kingdom: "ព្រះរាជាណាចក្រកម្ពុជា",
          certificate: "សញ្ញាបត្របឋមសិក្សា",
        },
      }),
  },
  {
    name: "leaf_banana",
    file: "T_ep1_leaf_banana_BC",
    size: [2048, 2048],
    alpha: true,
    draw: () => canvasPage(2048, 2048, paintBanana),
  },
  {
    name: "leaf_palm",
    file: "T_ep1_leaf_palm_BC",
    size: [1024, 1024],
    alpha: true,
    draw: () => canvasPage(1024, 1024, paintPalmFan),
  },
  {
    name: "leaf_coconut",
    file: "T_ep1_leaf_coconut_BC",
    size: [2048, 512],
    alpha: true,
    draw: () => canvasPage(2048, 512, paintCoconut),
  },
  {
    name: "flag_crocodile",
    file: "T_ep1_flag_crocodile_BC",
    size: [512, 2048],
    alpha: true,
    draw: () => canvasPage(512, 2048, paintCrocodileFlag),
  },
  {
    name: "coffin_panel",
    file: "T_ep1_coffin_panel_BC",
    size: [2048, 512],
    draw: () => canvasPage(2048, 512, paintCoffinPanel),
  },
  {
    name: "mat",
    file: "T_ep1_mat_BC",
    size: [1024, 1024],
    draw: () => canvasPage(1024, 1024, paintMat),
  },
  {
    name: "valance",
    file: "T_ep1_valance_BC",
    size: [1024, 256],
    alpha: true,
    draw: () => canvasPage(1024, 256, paintValance),
  },
  {
    name: "banana_stem",
    file: "T_ep1_banana_stem_BC",
    size: [512, 1024],
    draw: () => canvasPage(512, 1024, paintBananaStem),
  },
  {
    name: "bamboo",
    file: "T_ep1_bamboo_BC",
    size: [256, 1024],
    draw: () => canvasPage(256, 1024, paintBamboo),
  },
  {
    name: "palm_trunk",
    file: "T_ep1_palm_trunk_BC",
    size: [512, 1024],
    draw: () => canvasPage(512, 1024, paintPalmTrunk),
  },
  {
    name: "sky",
    file: "T_ep1_sky_storm_BC",
    size: [2048, 1024],
    draw: () => canvasPage(2048, 1024, paintSky),
  },
  {
    name: "leaf_cluster",
    file: "T_ep1_leaf_cluster_BC",
    size: [1024, 1024],
    alpha: true,
    draw: () => canvasPage(1024, 1024, paintLeafClusters),
  },
  {
    name: "bamboo_leaves",
    file: "T_ep1_bamboo_leaves_BC",
    size: [1024, 512],
    alpha: true,
    draw: () => canvasPage(1024, 512, paintBambooLeaves),
  },
  {
    name: "grass",
    file: "T_ep1_grass_BC",
    size: [512, 512],
    alpha: true,
    draw: () => canvasPage(512, 512, paintGrass),
  },
  {
    name: "flag_old",
    file: "T_ep1_flag_old_BC",
    size: [512, 2048],
    alpha: true,
    draw: () => canvasPage(512, 2048, paintOldFlag, null, [paintCrocodileFlag]),
  },
  {
    name: "cobweb",
    file: "T_ep1_cobweb_BC",
    size: [512, 512],
    alpha: true,
    draw: () => canvasPage(512, 512, paintCobweb),
  },
  {
    name: "footprints",
    file: "T_ep1_footprints_BC",
    size: [256, 512],
    alpha: true,
    draw: () => canvasPage(256, 512, paintFootprints),
  },
  {
    name: "yantra",
    file: "T_ep1_yantra_BC",
    size: [512, 512],
    draw: () =>
      canvasPage(512, 512, paintYantra, {
        syllables: ["ន", "មោ", "ពុ", "ទ្ធា", "យ"],
        border: "ន មោ ពុ ទ្ធា យ",
      }),
  },
  {
    name: "tingmong_face",
    file: "T_ep1_tingmong_face_BC",
    size: [1024, 512],
    draw: () => canvasPage(1024, 512, paintTingMongFace),
  },
  {
    name: "tingmong_shirt",
    file: "T_ep1_tingmong_shirt_BC",
    size: [1024, 1024],
    draw: () => canvasPage(1024, 1024, paintGuardianCloth, false),
  },
  {
    name: "tingmong_wrap",
    file: "T_ep1_tingmong_wrap_BC",
    size: [1024, 1024],
    draw: () => canvasPage(1024, 1024, paintGuardianCloth, true),
  },
  {
    name: "tingmong_weave",
    file: "T_ep1_tingmong_weave_N",
    size: [1024, 1024],
    draw: () => canvasPage(1024, 1024, paintGuardianWeave),
  },
  {
    name: "milestone",
    file: "T_ep1_milestone_BC",
    size: [512, 256],
    draw: () => canvasPage(512, 256, paintMilestone),
  },
  {
    name: "stains",
    file: "T_ep1_stains_BC",
    size: [512, 512],
    alpha: true,
    draw: () => canvasPage(512, 512, paintStains),
  },
];
