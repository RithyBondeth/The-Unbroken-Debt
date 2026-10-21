#!/usr/bin/env node
// Copies the meshopt and KTX2 decoders into public/vendor/ so the game never
// fetches code from a CDN at run time (Spike S3). Runs after `npm install`.
// The versions come from package.json; src/render/decoders.ts points Babylon here.

import { copyFileSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { build } from "vite";

const OUT = "public/vendor";
const KTX2 = "node_modules/@babylonjs/ktx2decoder";

rmSync(OUT, { recursive: true, force: true });
mkdirSync(join(OUT, "ktx2"), { recursive: true });

// meshopt: the CommonJS build defines a global MeshoptDecoder when loaded as a script.
copyFileSync("node_modules/meshoptimizer/meshopt_decoder.cjs", join(OUT, "meshopt_decoder.js"));

// KTX2: Babylon's decoder worker calls importScripts(), so bundle the ES modules
// into one classic script that defines the global KTX2DECODER.
await build({
  configFile: false,
  logLevel: "warn",
  publicDir: false,
  build: {
    outDir: join(OUT, "ktx2"),
    emptyOutDir: false,
    minify: true,
    lib: {
      entry: join(KTX2, "legacy/legacy.js"),
      formats: ["iife"],
      name: "KTX2DECODER",
      fileName: () => "babylon.ktx2Decoder.js",
    },
  },
});

// The transcoders: WebAssembly files and the Basis Universal script that loads one of them.
for (const file of readdirSync(join(KTX2, "wasm"))) {
  if (file.endsWith(".wasm") || file.endsWith(".js")) {
    copyFileSync(join(KTX2, "wasm", file), join(OUT, "ktx2", file));
  }
}
copyFileSync(join(KTX2, "license.md"), join(OUT, "ktx2", "license.md"));
copyFileSync(join(KTX2, "wasm", "license.md"), join(OUT, "ktx2", "license-transcoders.md"));
copyFileSync("node_modules/meshoptimizer/LICENSE.md", join(OUT, "meshopt-license.md"));

console.log(`Decoders copied to ${OUT}/`);
