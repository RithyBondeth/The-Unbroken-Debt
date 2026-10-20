#!/usr/bin/env node
// Exports every .blend in art-source/blender/ to a .glb in art-export/ (same sub-folders),
// using tools/export-blend.py inside Blender. Technical Design Document, section 7.3.
// Usage: npm run export            (all files)
//        npm run export -- ep1     (only files under art-source/blender/ep1/)
// Set BLENDER to the Blender executable if it is not on the PATH or in /Applications.

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";

const SRC = "art-source/blender";
const OUT = "art-export";
const filter = process.argv[2] ?? "";

function findBlender() {
  const candidates = [
    process.env.BLENDER,
    "/Applications/Blender.app/Contents/MacOS/Blender",
    "blender",
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate.includes("/") && !existsSync(candidate)) continue;
    try {
      execFileSync(candidate, ["--version"], { stdio: "ignore" });
      return candidate;
    } catch {
      // Try the next one.
    }
  }
  console.error("Blender not found. Install it or set BLENDER to its executable.");
  process.exit(1);
}

function findBlends(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return findBlends(path);
    return name.endsWith(".blend") ? [path] : [];
  });
}

const blender = findBlender();
const files = findBlends(SRC).filter((f) => relative(SRC, f).startsWith(filter));
if (files.length === 0) {
  console.log(`No .blend files found in ${SRC}/${filter}`);
  process.exit(0);
}

for (const input of files) {
  const output = join(OUT, relative(SRC, input)).replace(/\.blend$/, ".glb");
  mkdirSync(dirname(output), { recursive: true });
  console.log(`\n▶ ${input} → ${output}`);
  execFileSync(
    blender,
    ["--factory-startup", "-b", input, "-P", "tools/export-blend.py", "--", output],
    { stdio: "inherit" },
  );
}

console.log(`\nDone: ${files.length} file(s).`);
