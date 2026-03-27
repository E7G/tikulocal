import { defineConfig } from "vite";

export default defineConfig({
  envPrefix: ["VITE_"],
  build: {
    target: "esnext",
    minify: "esbuild",
    sourcemap: false,
  },
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
});
