import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const reactRoot = fileURLToPath(new URL("..", import.meta.url));
const buildDirectory = fileURLToPath(new URL("./dist", import.meta.url));

export default defineConfig({
  root: reactRoot,
  plugins: [react()],
  base: "/",
  server: {
    host: "0.0.0.0",
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
  build: {
    outDir: buildDirectory,
    emptyOutDir: true,
    assetsDir: "bundled",
  },
});
