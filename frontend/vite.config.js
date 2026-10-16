import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-ui":    ["lucide-react"],
          "vendor-http":  ["axios"],
          "vendor-toast": ["react-toastify"],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
});