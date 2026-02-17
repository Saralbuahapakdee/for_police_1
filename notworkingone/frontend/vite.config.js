import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": {
        target: "http://backend:5000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        ws: true,
      },
    },
    host: "0.0.0.0",
    port: 5173,
    // Allow access from all hosts
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "eaa21757-8ab2-473e-9739-793b13995617.cloud.ce.kmitl.ac.th",
    ],
  },
})