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
    allowedHosts: ["localhost", "172.18.0.4", "127.0.0.1"],
  },
})