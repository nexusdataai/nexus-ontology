import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
      '/stats': { target: 'http://localhost:8000', changeOrigin: true },
      '/tools': { target: 'http://localhost:8000', changeOrigin: true },
      '/journeys': { target: 'http://localhost:8000', changeOrigin: true },
      '/docs': {
        target: 'http://localhost:8001',
        rewrite: (path) => path.replace(/^\/docs/, ''),
      },
      '/test': {
        target: 'https://d37vwg02pj6oqg.cloudfront.net',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/test/, ''),
      },
    },
  },
  plugins: [
    react(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
