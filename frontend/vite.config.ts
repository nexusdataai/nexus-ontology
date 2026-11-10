import { defineConfig, loadEnv, type PluginOption } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { sampleData } from "./dev/sample-data/plugin";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Development-only: answer API calls with sample data when no backend is
  // available. Off unless VITE_SAMPLE_DATA=true is set in .env.local.
  const useSampleData = env.VITE_SAMPLE_DATA === "true";

  const plugins: PluginOption[] = [react()];
  if (useSampleData) plugins.push(sampleData());

  return {
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
    plugins,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
