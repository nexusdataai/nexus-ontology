/**
 * Development-only sample data.
 * ----------------------------------------------------------------------------
 * Lets the UI be designed and reviewed without a running backend.
 *
 * - Enabled ONLY when VITE_SAMPLE_DATA=true in .env.local (never committed).
 * - Runs inside the Vite dev server. It is not part of `vite build`, so it can
 *   never ship to staging or production.
 * - Does not touch src/services: screens make exactly the same requests they
 *   make against the real backend; this plugin just answers them.
 *
 * To work against the real backend, remove VITE_SAMPLE_DATA from .env.local.
 */
import type { Plugin } from 'vite';
import { routes } from './routes';

const API_PREFIXES = ['/api/', '/health', '/stats', '/tools', '/journeys'];

export function sampleData(): Plugin {
  const missing = new Set<string>();
  return {
    name: 'nexus-sample-data',
    apply: 'serve',
    configureServer(server) {
      server.config.logger.info('\n  Sample data is ON (VITE_SAMPLE_DATA=true). No backend calls are made.\n');
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url || '/', 'http://localhost');
        const path = url.pathname;
        if (!API_PREFIXES.some(p => path.startsWith(p))) return next();

        const method = (req.method || 'GET').toUpperCase();
        let body: unknown = undefined;
        if (method !== 'GET' && method !== 'HEAD') {
          const chunks: Buffer[] = [];
          for await (const c of req) chunks.push(c as Buffer);
          const raw = Buffer.concat(chunks).toString('utf8');
          try { body = raw ? JSON.parse(raw) : undefined; } catch { body = raw; }
        }

        for (const r of routes) {
          if (r.method && r.method !== method) continue;
          const m = typeof r.path === 'string' ? (r.path === path ? [path] : null) : path.match(r.path);
          if (!m) continue;
          const out = await r.handle({ path, query: url.searchParams, body, match: m as string[] });
          res.statusCode = 200;
          // A handler may return { __raw, __contentType } to send text as-is
          // (file contents, event streams) instead of JSON.
          const rawOut = out as { __raw?: unknown; __contentType?: string } | null;
          if (rawOut && typeof rawOut === 'object' && typeof rawOut.__raw === 'string') {
            res.setHeader('Content-Type', rawOut.__contentType || 'text/plain; charset=utf-8');
            res.end(rawOut.__raw);
            return;
          }
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(out));
          return;
        }

        const key = `${method} ${path}`;
        if (!missing.has(key)) {
          missing.add(key);
          server.config.logger.warn(`  [sample-data] no sample for ${key}`);
        }
        res.statusCode = 404;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({ message: `No sample data for ${key}` }));
      });
    },
  };
}
