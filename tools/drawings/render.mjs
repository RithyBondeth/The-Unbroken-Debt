#!/usr/bin/env node
// Renders the drawings and prints in tools/drawings/<episode>.mjs to PNG textures
// in art-source/textures/<episode>/, with headless Chrome: it shapes Khmer
// script properly (stacked consonants, vowel signs), which Blender cannot.
// The area scripts in tools/areas/ then put them on paper in the room.
// Usage: npm run drawings -- ep1            (every drawing in Episode 1)
//        npm run drawings -- ep1 illustration
// Set CHROME to the Chrome executable if it is not in the usual place.

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const [episode = "ep1", only] = process.argv.slice(2);
const OUT = join("art-source", "textures", episode);

// Khmer and English faces chosen in S5 and the Art Bible (SIL Open Font Licence).
const FONTS = {
  Preahvihear: "public/fonts/Preahvihear-Regular.ttf",
  Freehand: "public/fonts/Freehand-Regular.ttf",
  PatrickHand: "public/fonts/PatrickHand-Regular.ttf",
};

function findChrome() {
  const candidates = [
    process.env.CHROME,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "google-chrome",
    "chromium",
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate.includes("/") && !existsSync(candidate)) continue;
    return candidate;
  }
  throw new Error("Chrome not found: set CHROME to its executable.");
}

const fontFaces = Object.entries(FONTS)
  .map(
    ([family, file]) =>
      `@font-face{font-family:"${family}";font-display:block;src:url(data:font/ttf;base64,${readFileSync(file).toString("base64")})}`,
  )
  .join("");

const { drawings } = await import(pathToFileURL(join("tools", "drawings", `${episode}.mjs`)).href);
const chrome = findChrome();
const scratch = mkdtempSync(join(tmpdir(), "drawings-"));
mkdirSync(OUT, { recursive: true });

for (const drawing of drawings.filter((d) => !only || d.name === only)) {
  const started = performance.now();
  const [w, h] = drawing.size;
  const page = join(scratch, `${drawing.name}.html`);
  writeFileSync(
    page,
    `<!doctype html><meta charset="utf-8"><style>${fontFaces}html,body{margin:0;width:${w}px;height:${h}px;overflow:hidden}svg{display:block}</style>${drawing.draw()}`,
  );
  const out = join(OUT, `${drawing.file}.png`);
  execFileSync(
    chrome,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--force-device-scale-factor=1",
      `--window-size=${w},${h}`,
      "--virtual-time-budget=20000",
      `--screenshot=${join(process.cwd(), out)}`,
      pathToFileURL(page).href,
    ],
    { stdio: "ignore", timeout: 180_000 },
  );
  console.log(`${out}  ${w}x${h}  ${((performance.now() - started) / 1000).toFixed(1)} s`);
}
rmSync(scratch, { recursive: true, force: true });
