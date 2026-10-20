import { defineConfig } from "vite";

export default defineConfig({
  optimizeDeps: {
    // Havok ships a WebAssembly file that must not be pre-bundled.
    exclude: ["@babylonjs/havok"],
    // Crawl lazily loaded modules (spikes) at startup so every Babylon import is
    // pre-bundled in one pass. A second pass would load duplicate Babylon classes
    // (for example two Scene prototypes) and break scene components such as physics.
    entries: ["index.html", "src/spikes/**/*.ts"],
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
