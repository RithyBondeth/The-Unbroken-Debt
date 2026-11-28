// The goods on the village road's shop shelves (tools/areas/village_road.py, the user, Nov 25,
// 2026: "inside every single shop ... even small items ... very detailed and very realistic"):
// one 2048 x 2048 sheet of cheap printed labels and packets as a Cambodian roadside shop
// sold them, two or three spot inks on poor paper, printed a little off register, faded,
// stained and scuffed.
//
// Top half: WRAP labels, 4 x 8 cells of 512 x 128, wrapped round bottles, jars and tins
// (each label printed twice round, so its name faces out either way).
// Bottom half: FACE labels, 8 x 4 cells of 256 x 256, each drawn in a centred rectangle of
// its own aspect (width / height) for the front of a packet, box or card.
// The order is tools/areas/shop_goods.py WRAP and FACE: keep the two in step.
//
// Every Khmer string comes from KHMER in ep1.mjs (keys goods*), for review.

/* global rng, lerp, smooth, noise */
import { canvasPage } from "./village.mjs";

/** Wrap labels: [KHMER key, background, ink, accent, emblem, unit]. */
const WRAP = [
  ["goodsFishSauce", "#eadcb8", "#5a1a12", "#c8402a", "fish", "១ លីត្រ"],
  ["goodsSoySauce", "#1d1a16", "#e9c64a", "#b8341f", "leaf", "៧០០"],
  ["goodsChili", "#b52a1c", "#fbe9c8", "#f2c230", "chili", "២៥០"],
  ["goodsCookingOil", "#f0cd3a", "#1f5a2a", "#c8402a", "drop", "១ លីត្រ"],
  ["goodsOrangeDrink", "#e8772a", "#fff5dc", "#2a4f9a", "sun", "៣០០"],
  ["goodsBeer", "#d9b04a", "#2a1a10", "#a3261c", "star", "៦៤០"],
  ["goodsRiceSpirit", "#f2ede0", "#a11d16", "#1c1c1c", "seal", "៧៥០"],
  ["goodsCondensedMilk", "#2f5fa8", "#fdfbf2", "#e2b23a", "cow", "៣៩៧ ក្រាម"],
  ["goodsCoffee", "#4a2a18", "#f0d9a8", "#c8402a", "cup", "៥០០ ក្រាម"],
  ["goodsHairOil", "#1f5a3a", "#f0d27a", "#b8341f", "flower", "១២០"],
  ["goodsBalm", "#2a6a3a", "#fff0c0", "#d8402a", "leaf", "២៤"],
  ["goodsTalc", "#f2c6c8", "#7a1f3a", "#3a6ab0", "flower", "២០០ ក្រាម"],
  ["goodsShampoo", "#2a8a8a", "#ffffff", "#f2c230", "drop", "៤០០"],
  ["goodsVinegar", "#f4f1e4", "#2a6a2a", "#c8402a", "drop", "៧០០"],
  ["goodsSoda", "#f4f4ee", "#1f4fa0", "#d8302a", "wave", "៣០០"],
  ["goodsCannedFish", "#2a4f9a", "#fff6e0", "#d8302a", "fish", "១៥៥ ក្រាម"],
  ["goodsEngineOil", "#1a1a1a", "#f2a020", "#e8e0c8", "gear", "១ លីត្រ"],
  ["goodsKerosene", "#c8302a", "#ffffff", "#1a1a1a", "flame", "១ លីត្រ"],
  ["goodsCoughSyrup", "#f4f4f0", "#1f4f9a", "#c8302a", "cross", "៦០"],
  ["goodsPerfume", "#c8b0e0", "#3a1a5a", "#e2b23a", "flower", "៥០"],
  ["goodsThread", "#f4efe0", "#b8241c", "#1f3f8a", "spool", "៥០០"],
  ["goodsSweets", "#e84a6a", "#fff4c0", "#2a8a4a", "star", "៥០០ ក្រាម"],
  ["goodsPalmSugar", "#f0e6cc", "#1f4f8a", "#a8541c", "palm", "១ គីឡូ"],
  ["goodsPickles", "#4a8a3a", "#fff4d8", "#c8302a", "leaf", "៥០០"],
  ["goodsPrahok", "#6a4224", "#f4e0b0", "#c8402a", "fish", "៥០០ ក្រាម"],
  ["goodsTea", "#2a6a3a", "#f8e8b0", "#c8302a", "leaf", "២០០ ក្រាម"],
  ["goodsBiscuits", "#b8241c", "#fff0d0", "#e8c040", "flower", "៤៥៤ ក្រាម"],
  ["goodsBattery", "#161616", "#f2c230", "#d8302a", "bolt", "១.៥"],
  ["goodsGrease", "#2a2a24", "#e8a030", "#c8c0a8", "gear", "៥០០ ក្រាម"],
  ["goodsCoconutWater", "#3a7a3a", "#ffffff", "#f2c230", "palm", "៣៣០"],
  ["goodsLotion", "#f4ead8", "#8a3a2a", "#3a8a6a", "lotus", "២០០"],
  ["goodsAlcohol", "#f4f6f8", "#1f4f9a", "#c8302a", "cross", "៥០០"],
];

/** Face labels: [KHMER key, aspect (w / h), background, ink, accent, emblem, style]. */
const FACE = [
  ["goodsCigarettes", 0.62, "#c8241c", "#ffffff", "#e8c040", "star", "pack"],
  ["goodsCigarettes", 0.62, "#1f3f8a", "#ffffff", "#e8e0c8", "seal", "pack"],
  ["goodsMatches", 1.45, "#f2c230", "#1a1a1a", "#c8302a", "elephant", "box"],
  ["goodsInstantNoodles", 1.3, "#d8241c", "#fff4c0", "#f2c230", "bowl", "packet"],
  ["goodsInstantNoodles", 1.3, "#f2c230", "#b8241c", "#2a6a3a", "bowl", "packet"],
  ["goodsBarSoap", 1.5, "#2a8a4a", "#ffffff", "#f2c230", "flower", "box"],
  ["goodsIncense", 0.34, "#b8241c", "#f2d060", "#f2d060", "lotus", "wrap"],
  ["goodsCandles", 0.5, "#f4efe0", "#b8241c", "#e8a020", "flame", "box"],
  ["goodsWashingPowder", 0.75, "#2a5fb8", "#ffffff", "#f2c230", "wave", "box"],
  ["goodsTea", 0.7, "#c8302a", "#f8e8b0", "#2a6a3a", "leaf", "box"],
  ["goodsToothpaste", 3.4, "#f4f4f0", "#c8241c", "#1f4f9a", "tooth", "box"],
  ["goodsMedicine", 1.6, "#f4f4f0", "#1f4f9a", "#c8302a", "cross", "box"],
  ["goodsRazor", 1.6, "#1f3f8a", "#ffffff", "#c8c8c8", "star", "box"],
  ["goodsSongs", 0.62, "#3a1a4a", "#f8e0a0", "#e84a6a", "singer", "card"],
  ["goodsSongs", 0.62, "#b84a2a", "#fff4d8", "#2a2a5a", "singer", "card"],
  ["goodsBiscuits", 1.4, "#e8c040", "#8a1f14", "#2a6a3a", "flower", "box"],
  ["goodsSnacks", 0.75, "#e84a2a", "#ffffff", "#f2c230", "star", "packet"],
  ["goodsDriedSquid", 0.75, "#f2a020", "#5a1a12", "#c8302a", "fish", "packet"],
  ["goodsShrimpCrackers", 0.75, "#f4f0e0", "#d8302a", "#f2a020", "fish", "packet"],
  ["goodsHairDye", 0.75, "#1a1a1a", "#e8c040", "#b8241c", "flower", "box"],
  ["goodsSparkPlug", 0.45, "#c8302a", "#ffffff", "#1a1a1a", "bolt", "box"],
  ["goodsNeedles", 1.5, "#f4efe0", "#1f3f8a", "#c8302a", "spool", "card"],
  ["goodsCalendar", 0.72, "#f4efe0", "#1a1a1a", "#c8302a", "grid", "paper"],
  ["goodsNotebook", 0.72, "#2a5f8a", "#ffffff", "#f2c230", "lotus", "paper"],
  ["goodsLottery", 2.2, "#f4e8c8", "#b8241c", "#1f4f9a", "seal", "paper"],
  ["goodsFacePowder", 1.0, "#e8b8b8", "#7a1f3a", "#e2b23a", "flower", "round"],
  ["goodsWatch", 1.0, "#1a1a1a", "#e8c040", "#c8c8c8", "clock", "box"],
  ["goodsTeeth", 0.72, "#f4f4f0", "#1a1a1a", "#c8302a", "tooth", "paper"],
  ["goodsPriceList", 0.72, "#b89868", "#1a1a1a", "#1a1a1a", "none", "cardboard"],
  ["goodsShrinePaper", 0.6, "#b8241c", "#f2d060", "#f2d060", "lotus", "paper"],
  ["goodsNoCredit", 2.0, "#b89868", "#1a1a1a", "#b8241c", "none", "cardboard"],
  ["goodsBeer", 1.0, "#d9b04a", "#2a1a10", "#a3261c", "star", "paper"],
];

/** Sub-rectangle a face label is drawn in (and the area script maps): x, y, w, h in px. */
export function faceRect(i) {
  const aspect = FACE[i][1];
  const cx = (i % 8) * 256 + 128;
  const cy = 1024 + Math.floor(i / 8) * 256 + 128;
  const w = aspect >= 1 ? 240 : Math.round(240 * aspect);
  const h = aspect >= 1 ? Math.round(240 / aspect) : 240;
  return [cx - Math.floor(w / 2), cy - Math.floor(h / 2), w, h];
}

function paintGoods(ctx, W, H, data) {
  const toKhmer = (n) => String(n).replace(/[0-9]/g, (d) => "០១២៣៤៥៦៧៨៩"[d]);
  ctx.fillStyle = "#2a2219";
  ctx.fillRect(0, 0, W, H);

  const fit = (t, maxW, size, font) => {
    ctx.font = `${size}px ${font}`;
    const w = ctx.measureText(t).width;
    return w > maxW ? Math.floor((size * maxW) / w) : size;
  };
  const text = (t, x, y, size, color, o = {}) => {
    const font = o.font || "Preahvihear";
    const s = o.maxW ? fit(t, o.maxW, size, font) : size;
    ctx.save();
    ctx.font = `${o.weight || ""} ${s}px ${font}`;
    ctx.fillStyle = color;
    ctx.textAlign = o.align || "center";
    ctx.textBaseline = "middle";
    if (o.rot) {
      ctx.translate(x, y);
      ctx.rotate(o.rot);
      ctx.fillText(t, 0, 0);
    } else ctx.fillText(t, x, y);
    ctx.restore();
  };

  // Emblems, drawn in a unit box (cx, cy, size): simple printed devices of the kind.
  const emblem = (kind, cx, cy, s, ink, accent) => {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(s / 100, s / 100);
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    const fill = (c) => {
      ctx.fillStyle = c;
      ctx.fill();
    };
    const stroke = (c, w) => {
      ctx.strokeStyle = c;
      ctx.lineWidth = w;
      ctx.stroke();
    };
    ctx.beginPath();
    switch (kind) {
      case "fish":
        ctx.ellipse(-6, 0, 34, 16, 0, 0, Math.PI * 2);
        fill(accent);
        ctx.beginPath();
        ctx.moveTo(24, 0);
        ctx.lineTo(44, -16);
        ctx.lineTo(44, 16);
        ctx.closePath();
        fill(accent);
        ctx.beginPath();
        ctx.arc(-26, -4, 3.5, 0, Math.PI * 2);
        fill(ink);
        ctx.beginPath();
        for (let k = 0; k < 4; k++) {
          ctx.moveTo(-12 + k * 9, -11);
          ctx.quadraticCurveTo(-8 + k * 9, 0, -12 + k * 9, 11);
        }
        stroke(ink, 2);
        break;
      case "chili":
        ctx.moveTo(-30, -18);
        ctx.quadraticCurveTo(10, -26, 36, 22);
        ctx.quadraticCurveTo(0, 6, -30, -6);
        ctx.closePath();
        fill(accent);
        ctx.beginPath();
        ctx.moveTo(-30, -12);
        ctx.lineTo(-40, -22);
        stroke("#2a6a2a", 6);
        break;
      case "leaf":
        ctx.moveTo(-36, 18);
        ctx.quadraticCurveTo(-30, -30, 36, -24);
        ctx.quadraticCurveTo(26, 30, -36, 18);
        fill(accent);
        ctx.beginPath();
        ctx.moveTo(-36, 18);
        ctx.quadraticCurveTo(0, 0, 30, -20);
        stroke(ink, 2.5);
        break;
      case "drop":
        ctx.moveTo(0, -38);
        ctx.bezierCurveTo(22, -8, 30, 10, 0, 34);
        ctx.bezierCurveTo(-30, 10, -22, -8, 0, -38);
        fill(accent);
        ctx.beginPath();
        ctx.ellipse(-8, 8, 6, 12, 0.4, 0, Math.PI * 2);
        fill("rgba(255,255,255,0.55)");
        break;
      case "sun":
        ctx.arc(0, 0, 22, 0, Math.PI * 2);
        fill(accent);
        ctx.beginPath();
        for (let k = 0; k < 16; k++) {
          const a = (k / 16) * Math.PI * 2;
          ctx.moveTo(Math.cos(a) * 28, Math.sin(a) * 28);
          ctx.lineTo(Math.cos(a) * 42, Math.sin(a) * 42);
        }
        stroke(accent, 4);
        break;
      case "star":
        for (let k = 0; k < 10; k++) {
          const a = (k / 10) * Math.PI * 2 - Math.PI / 2;
          const r = k % 2 ? 16 : 40;
          ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
        }
        ctx.closePath();
        fill(accent);
        break;
      case "seal":
        ctx.arc(0, 0, 38, 0, Math.PI * 2);
        fill(accent);
        ctx.beginPath();
        ctx.arc(0, 0, 31, 0, Math.PI * 2);
        stroke(ink, 3);
        ctx.beginPath();
        ctx.rect(-14, -14, 28, 28);
        stroke(ink, 3);
        break;
      case "cow":
        ctx.ellipse(0, 6, 24, 28, 0, 0, Math.PI * 2);
        fill(accent);
        ctx.beginPath();
        ctx.moveTo(-20, -14);
        ctx.quadraticCurveTo(-42, -30, -36, -40);
        ctx.moveTo(20, -14);
        ctx.quadraticCurveTo(42, -30, 36, -40);
        stroke(accent, 7);
        ctx.beginPath();
        ctx.ellipse(0, 22, 14, 9, 0, 0, Math.PI * 2);
        fill(ink);
        ctx.beginPath();
        ctx.arc(-9, -2, 3.5, 0, Math.PI * 2);
        ctx.arc(9, -2, 3.5, 0, Math.PI * 2);
        fill(ink);
        break;
      case "cup":
        ctx.moveTo(-26, -12);
        ctx.lineTo(22, -12);
        ctx.lineTo(16, 26);
        ctx.lineTo(-20, 26);
        ctx.closePath();
        fill(accent);
        ctx.beginPath();
        ctx.arc(26, 2, 10, -Math.PI / 2, Math.PI / 2);
        stroke(accent, 5);
        ctx.beginPath();
        for (let k = 0; k < 3; k++) {
          ctx.moveTo(-12 + k * 12, -20);
          ctx.quadraticCurveTo(-6 + k * 12, -30, -12 + k * 12, -40);
        }
        stroke(ink, 2.5);
        break;
      case "flower":
        for (let k = 0; k < 6; k++) {
          const a = (k / 6) * Math.PI * 2;
          ctx.beginPath();
          ctx.ellipse(Math.cos(a) * 20, Math.sin(a) * 20, 15, 9, a, 0, Math.PI * 2);
          fill(accent);
        }
        ctx.beginPath();
        ctx.arc(0, 0, 10, 0, Math.PI * 2);
        fill(ink);
        break;
      case "lotus":
        for (let k = -2; k <= 2; k++) {
          ctx.beginPath();
          ctx.moveTo(0, 26);
          ctx.quadraticCurveTo(
            k * 18 - 14,
            -6 - (2 - Math.abs(k)) * 10,
            k * 12,
            -30 + Math.abs(k) * 12,
          );
          ctx.quadraticCurveTo(k * 18 + 14, -6 - (2 - Math.abs(k)) * 10, 0, 26);
          fill(accent);
          stroke(ink, 1.5);
        }
        break;
      case "wave":
        for (let r = 0; r < 3; r++) {
          ctx.beginPath();
          for (let x = -40; x <= 40; x += 2) ctx.lineTo(x, r * 14 - 14 + Math.sin(x * 0.15) * 6);
          stroke(accent, 5);
        }
        break;
      case "gear":
        for (let k = 0; k < 24; k++) {
          const a = (k / 24) * Math.PI * 2;
          const r = k % 2 ? 30 : 38;
          ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
        }
        ctx.closePath();
        fill(accent);
        ctx.beginPath();
        ctx.arc(0, 0, 12, 0, Math.PI * 2);
        fill(ink);
        break;
      case "flame":
        ctx.moveTo(0, 36);
        ctx.bezierCurveTo(-30, 30, -24, -6, 0, -40);
        ctx.bezierCurveTo(10, -18, 30, 0, 0, 36);
        fill(accent);
        ctx.beginPath();
        ctx.moveTo(0, 30);
        ctx.bezierCurveTo(-12, 26, -10, 6, 0, -10);
        ctx.bezierCurveTo(6, 4, 12, 18, 0, 30);
        fill(ink);
        break;
      case "cross":
        ctx.rect(-10, -34, 20, 68);
        ctx.rect(-34, -10, 68, 20);
        fill(accent);
        break;
      case "spool":
        ctx.rect(-22, -30, 44, 8);
        ctx.rect(-22, 22, 44, 8);
        fill(ink);
        ctx.beginPath();
        ctx.rect(-16, -22, 32, 44);
        fill(accent);
        break;
      case "palm":
        ctx.moveTo(0, 40);
        ctx.lineTo(2, -14);
        stroke(ink, 5);
        for (let k = 0; k < 9; k++) {
          const a = -Math.PI + (k / 8) * Math.PI;
          ctx.beginPath();
          ctx.moveTo(2, -16);
          ctx.lineTo(2 + Math.cos(a) * 36, -16 + Math.sin(a) * 24);
          stroke(accent, 5);
        }
        break;
      case "bolt":
        ctx.moveTo(8, -40);
        ctx.lineTo(-18, 4);
        ctx.lineTo(0, 4);
        ctx.lineTo(-8, 40);
        ctx.lineTo(20, -6);
        ctx.lineTo(2, -6);
        ctx.closePath();
        fill(accent);
        break;
      case "elephant":
        ctx.ellipse(4, 0, 34, 22, 0, 0, Math.PI * 2);
        fill(ink);
        ctx.beginPath();
        ctx.arc(-26, -10, 16, 0, Math.PI * 2);
        fill(ink);
        ctx.beginPath();
        ctx.moveTo(-38, -4);
        ctx.quadraticCurveTo(-48, 20, -40, 34);
        stroke(ink, 7);
        for (const x of [-18, -4, 14, 28]) {
          ctx.beginPath();
          ctx.rect(x, 14, 9, 22);
          fill(ink);
        }
        ctx.beginPath();
        ctx.arc(-30, -14, 3, 0, Math.PI * 2);
        fill(accent);
        break;
      case "bowl":
        ctx.arc(0, -4, 36, 0, Math.PI);
        fill(accent);
        ctx.beginPath();
        for (let k = 0; k < 5; k++) {
          ctx.moveTo(-28 + k * 12, -6);
          ctx.quadraticCurveTo(-22 + k * 12, -26, -16 + k * 12, -6);
        }
        stroke(ink, 2.5);
        ctx.beginPath();
        ctx.moveTo(10, -10);
        ctx.lineTo(40, -44);
        ctx.moveTo(18, -8);
        ctx.lineTo(46, -40);
        stroke(ink, 3);
        break;
      case "tooth":
        ctx.moveTo(-24, -24);
        ctx.quadraticCurveTo(0, -36, 24, -24);
        ctx.quadraticCurveTo(30, 0, 16, 34);
        ctx.quadraticCurveTo(8, 10, 0, 10);
        ctx.quadraticCurveTo(-8, 10, -16, 34);
        ctx.quadraticCurveTo(-30, 0, -24, -24);
        fill("#ffffff");
        stroke(accent, 3);
        break;
      case "singer":
        ctx.arc(0, -12, 18, 0, Math.PI * 2);
        fill(accent);
        ctx.beginPath();
        ctx.ellipse(0, 30, 30, 22, 0, Math.PI, 0);
        fill(accent);
        ctx.beginPath();
        ctx.arc(0, -16, 22, Math.PI, 0);
        fill(ink);
        break;
      case "clock":
        ctx.arc(0, 0, 36, 0, Math.PI * 2);
        fill(accent);
        ctx.beginPath();
        ctx.arc(0, 0, 30, 0, Math.PI * 2);
        fill("#f8f4ea");
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(0, -22);
        ctx.moveTo(0, 0);
        ctx.lineTo(14, 6);
        stroke(ink, 3);
        break;
      case "grid":
        for (let r = 0; r < 5; r++)
          for (let c = 0; c < 7; c++) {
            ctx.rect(-42 + c * 12, -24 + r * 12, 11, 11);
          }
        stroke(ink, 1);
        break;
      default:
        break;
    }
    ctx.restore();
  };

  // Print and age: halftone over a band, a misregistered accent, mottle, scuffs, stains.
  const halftone = (x, y, w, h, color, step, r) => {
    ctx.fillStyle = color;
    for (let yy = y + step / 2; yy < y + h; yy += step)
      for (let xx = x + ((yy / step) % 2 ? step / 2 : 0); xx < x + w; xx += step) {
        ctx.beginPath();
        ctx.arc(xx, yy, r, 0, Math.PI * 2);
        ctx.fill();
      }
  };
  const age = (x, y, w, h, seed, k) => {
    const r = rng(seed);
    const n = noise(w, h, 40, seed, 4);
    const fine = noise(w, h, 6, seed + 7, 2);
    const img = ctx.getImageData(x, y, w, h);
    const p = img.data;
    for (let j = 0; j < h; j++)
      for (let i = 0; i < w; i++) {
        const q = j * w + i;
        const ex = Math.min(i, w - 1 - i, j, h - 1 - j) / Math.min(w, h);
        const edge = 1 - 0.35 * k * (1 - smooth(0, 0.12, ex));
        const fade = 0.86 + 0.2 * n[q] + 0.08 * (fine[q] - 0.5);
        const f = edge * fade;
        // Sun-faded towards paper yellow.
        const pale = 0.12 * k * n[q];
        p[q * 4] = lerp(p[q * 4] * f, 232, pale);
        p[q * 4 + 1] = lerp(p[q * 4 + 1] * f, 214, pale);
        p[q * 4 + 2] = lerp(p[q * 4 + 2] * f, 170, pale);
      }
    ctx.putImageData(img, x, y);
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    for (let s = 0; s < 3 * k; s++) {
      ctx.strokeStyle = `rgba(255,248,230,${r(0.15, 0.4)})`;
      ctx.lineWidth = r(0.6, 1.6);
      ctx.beginPath();
      const sx = x + r(0, w);
      const sy = y + r(0, h);
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx + r(-40, 40), sy + r(-10, 10));
      ctx.stroke();
    }
    for (let s = 0; s < 2 * k; s++) {
      const g = ctx.createRadialGradient(
        x + r(0, w),
        y + r(0, h),
        1,
        x + r(0, w),
        y + r(0, h),
        r(10, 40),
      );
      g.addColorStop(0, `rgba(90,60,30,${r(0.08, 0.22)})`);
      g.addColorStop(1, "rgba(90,60,30,0)");
      ctx.fillStyle = g;
      ctx.fillRect(x, y, w, h);
    }
    ctx.restore();
  };

  // ---------------------------------------------------------------- wrap labels
  data.wrap.forEach(([name, bg, ink, accent, mark, unit], i) => {
    const x = (i % 4) * 512;
    const y = Math.floor(i / 4) * 128;
    const r = rng(100 + i);
    ctx.fillStyle = bg;
    ctx.fillRect(x, y, 512, 128);
    // Bands top and bottom in the accent ink, a hairline inside each.
    ctx.fillStyle = accent;
    ctx.fillRect(x, y + 6, 512, 12);
    ctx.fillRect(x, y + 110, 512, 12);
    ctx.fillStyle = ink;
    ctx.fillRect(x, y + 21, 512, 2);
    ctx.fillRect(x, y + 105, 512, 2);
    halftone(x, y + 6, 512, 12, "rgba(255,255,255,0.18)", 5, 1.3);
    for (const half of [0, 256]) {
      const ox = x + half;
      const mx = 1.2 + r(-0.6, 0.6);
      emblem(mark, ox + 46 + mx, y + 64 + mx * 0.7, 60, ink, accent);
      emblem(mark, ox + 46, y + 64, 60, ink, accent);
      text(name, ox + 160, y + 58, 40, ink, { maxW: 170 });
      text(`${data.made}  ${unit}`, ox + 160, y + 92, 13, ink, { maxW: 176 });
      // A thin ornamental rule under the name.
      ctx.fillStyle = accent;
      ctx.fillRect(ox + 92, y + 78, 136, 2);
    }
    age(x, y, 512, 128, 300 + i, 1 + r(0, 1.5));
  });

  // ---------------------------------------------------------------- face labels
  data.face.forEach(([name, , bg, ink, accent, mark, style], i) => {
    const [x, y, w, h] = data.rects[i];
    const r = rng(700 + i);
    const portrait = h > w;
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    ctx.fillStyle = bg;
    ctx.fillRect(x, y, w, h);
    const cx = x + w / 2;
    if (style === "cardboard") {
      // Shop cardboard with a hand-lettered notice in marker.
      const n = noise(w, h, 18, 900 + i, 3);
      const img = ctx.getImageData(x, y, w, h);
      for (let q = 0; q < w * h; q++) {
        const f = 0.86 + 0.24 * n[q];
        img.data[q * 4] *= f;
        img.data[q * 4 + 1] *= f;
        img.data[q * 4 + 2] *= f;
      }
      ctx.putImageData(img, x, y);
      if (name === data.noCreditKey) {
        text(data.k[name], cx, y + h * 0.52, 44, accent, {
          font: "Freehand",
          maxW: w * 0.9,
          rot: -0.03,
        });
      } else {
        text(data.k.goodsPriceList, cx, y + 22, 22, ink, { font: "Freehand", maxW: w * 0.85 });
        data.prices.forEach(([item, price], k) => {
          const yy = y + 52 + k * 24;
          text(data.k[item], x + 12, yy, 18, ink, {
            font: "Freehand",
            align: "left",
            maxW: w * 0.5,
          });
          text(`${toKhmer(price)} ៛`, x + w - 12, yy, 18, ink, {
            font: "Freehand",
            align: "right",
          });
        });
      }
    } else if (style === "card" && mark === "singer") {
      // Cassette J-card: a duotone portrait panel, the singer's name and the songs.
      ctx.fillStyle = accent;
      ctx.fillRect(x + 8, y + 8, w - 16, h * 0.55);
      halftone(x + 8, y + 8, w - 16, h * 0.55, "rgba(0,0,0,0.25)", 4, 1.1);
      emblem("singer", cx, y + 8 + h * 0.3, h * 0.42, ink, bg);
      text(data.k.goodsSongs, cx, y + h * 0.7, 28, ink, { maxW: w * 0.86 });
      for (let k = 0; k < 4; k++) {
        ctx.fillStyle = ink;
        ctx.globalAlpha = 0.65;
        ctx.fillRect(x + 14, y + h * 0.78 + k * 9, (w - 28) * r(0.4, 0.95), 2.5);
        ctx.globalAlpha = 1;
      }
    } else if (mark === "grid") {
      // A shop calendar page: heading, the month's numbers in a grid, a red Sunday.
      text(data.k.goodsCalendar, cx, y + 26, 26, accent, { maxW: w * 0.8 });
      const cols = 7;
      const cw = (w - 20) / cols;
      for (let d = 0; d < 31; d++) {
        const c = (d + 3) % cols;
        const rr = Math.floor((d + 3) / cols);
        text(
          toKhmer(d + 1),
          x + 10 + cw * (c + 0.5),
          y + 60 + rr * 28,
          12,
          c === 0 ? accent : ink,
          { maxW: cw - 2 },
        );
      }
    } else if (mark === "tooth" && style === "paper") {
      // The dentist's chart: two arches of teeth, numbered.
      text(data.k.goodsTeeth, cx, y + 24, 26, accent, { maxW: w * 0.8 });
      for (const [arch, sign] of [
        [y + h * 0.42, 1],
        [y + h * 0.72, -1],
      ]) {
        for (let k = 0; k < 8; k++) {
          const a = Math.PI * (0.12 + (k / 7) * 0.76);
          emblem(
            "tooth",
            cx - Math.cos(a) * w * 0.36,
            arch - sign * Math.sin(a) * h * 0.1,
            22,
            ink,
            accent,
          );
        }
      }
    } else {
      // A printed packet or box front: border, emblem, name, a strip with the maker.
      ctx.strokeStyle = accent;
      ctx.lineWidth = 4;
      ctx.strokeRect(x + 6, y + 6, w - 12, h - 12);
      if (style === "pack" || style === "packet") {
        ctx.fillStyle = accent;
        ctx.fillRect(x, y + h * (portrait ? 0.62 : 0.7), w, h * 0.1);
        halftone(x, y + h * (portrait ? 0.62 : 0.7), w, h * 0.1, "rgba(0,0,0,0.2)", 4, 1);
      }
      const es = Math.min(w, h) * (portrait ? 0.5 : 0.45);
      const ey = portrait ? y + h * 0.32 : y + h * 0.4;
      const ex = portrait ? cx : x + w * (w / h > 2 ? 0.16 : 0.3);
      emblem(mark, ex + 1.5, ey + 1, es, ink, accent);
      emblem(mark, ex, ey, es, ink, accent);
      const tx = portrait ? cx : x + w * (w / h > 2 ? 0.58 : 0.66);
      const tw = portrait ? w * 0.86 : w * (w / h > 2 ? 0.74 : 0.6);
      text(
        data.k[name],
        tx,
        portrait ? y + h * 0.56 : ey,
        portrait ? 30 : Math.min(36, h * 0.3),
        ink,
        { maxW: tw },
      );
      text(
        data.made,
        cx,
        y + h - (portrait ? 18 : Math.max(10, h * 0.12)),
        portrait ? 12 : Math.max(8, h * 0.1),
        ink,
        {
          maxW: w * 0.84,
        },
      );
    }
    ctx.restore();
    age(x, y, w, h, 1100 + i, style === "cardboard" ? 1.4 : 1 + r(0, 1.5));
  });
}

/** The texture entry: needs ep1.mjs's KHMER (goods* keys). */
export function shopGoodsTextures(KHMER) {
  const k = Object.fromEntries(Object.entries(KHMER).map(([key, v]) => [key, v[0]]));
  const wrap = WRAP.map(([key, ...rest]) => [k[key], ...rest]);
  return [
    {
      name: "shop_goods",
      file: "T_ep1_shop_goods_BC",
      size: [2048, 2048],
      draw: () =>
        canvasPage(2048, 2048, paintGoods, {
          wrap,
          face: FACE,
          rects: FACE.map((_, i) => faceRect(i)),
          k,
          made: k.goodsMadeIn,
          noCreditKey: "goodsNoCredit",
          prices: [
            ["goodsCoffee", 500],
            ["goodsTea", 300],
            ["goodsInstantNoodles", 800],
            ["goodsCigarettes", 1500],
            ["goodsSoda", 700],
            ["goodsBeer", 1200],
            ["goodsCandles", 200],
          ],
        }),
    },
  ];
}
