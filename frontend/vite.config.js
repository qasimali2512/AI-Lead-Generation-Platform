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
        manualChunks: (id) => {
          if (id.includes("react") || id.includes("react-dom") || id.includes("react-router-dom")) {
            return "vendor-react";
          }
          if (id.includes("lucide-react")) {
            return "vendor-ui";
          }
          if (id.includes("axios")) {
            return "vendor-http";
          }
          if (id.includes("react-toastify")) {
            return "vendor-toast";
          }
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
});