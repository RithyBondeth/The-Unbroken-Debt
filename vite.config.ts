import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";

/**
 * Development server only: POST /__debug/shot?name=<name> with a PNG data URL
 * saves it to debug-shots/<name>.png, so spike screenshots can be checked at
 * full resolution (src/debug/saveShot.ts).
 */
function debugShots(): Plugin {
  return {
    name: "debug-shots",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/__debug/shot", (req, res) => {
        const name = new URL(req.url ?? "", "http://x").searchParams.get("name") ?? "shot";
        const chunks: Buffer[] = [];
        req.on("data", (c: Buffer) => chunks.push(c));
        req.on("end", () => {
          const data = Buffer.concat(chunks)
            .toString()
            .replace(/^data:image\/png;base64,/, "");
          mkdirSync("debug-shots", { recursive: true });
          writeFileSync(
            `debug-shots/${name.replace(/[^\w-]/g, "_")}.png`,
            Buffer.from(data, "base64"),
          );
          res.end("saved");
        });
      });
    },
  };
}

export default defineConfig({
  plugins: [debugShots()],
  resolve: {
    // `@/core/Game` is `src/core/Game`: imports across top-level folders use it.
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  optimizeDeps: {
    // Havok ships a WebAssembly file that must not be pre-bundled.
    exclude: ["@babylonjs/havok"],
    // Crawl lazy modules and browser reviews at startup so every Babylon import is
    // pre-bundled in one pass. A second pass would load duplicate Babylon classes
    // (for example two Scene prototypes) and break scene components such as physics.
    entries: ["index.html", "src/spikes/**/*.ts", "tests/browser/**/*.ts"],
  },
  build: {
    target: "es2022",
    sourcemap: true,
    chunkSizeWarningLimit: 4000,
  },
  server: {
    port: 5173,
  },
});
