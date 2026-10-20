import { defineConfig } from "vite";

export default defineConfig({
  // Havok ships a WebAssembly file that must not be pre-bundled.
  optimizeDeps: {
    exclude: ["@babylonjs/havok"],
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
