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
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "1eeaf0a7-dafb-4564-95d3-9c154643f2c0.cloud.ce.kmitl.ac.th",
    ],
  },
})