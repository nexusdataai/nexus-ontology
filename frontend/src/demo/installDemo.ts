/**
 * Demo mode (design preview without a backend).
 * ----------------------------------------------------------------------------
 * Loaded ONLY when the build is made with VITE_DEMO=true (see main.tsx). In a
 * normal build this file and the sample data are not included at all.
 *
 * It answers the app's API calls in the browser with the same sample routes
 * the development plugin uses (frontend/dev/sample-data). Nothing is stored:
 * a reload shows the original sample data again. src/services is untouched;
 * screens make exactly the requests they make against the real backend.
 */
import { routes } from '../../dev/sample-data/routes';

const API_PREFIXES = ['/api/', '/health', '/stats', '/tools', '/journeys'];
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function installDemo() {
  const realFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const req = input instanceof Request ? input : null;
    const url = new URL(req ? req.url : String(input), window.location.origin);
    const path = url.pathname;
    if (url.origin !== window.location.origin || !API_PREFIXES.some((p) => path.startsWith(p))) {
      return realFetch(input as RequestInfo, init);
    }

    const method = (init?.method || req?.method || 'GET').toUpperCase();
    let body: unknown = undefined;
    if (method !== 'GET' && method !== 'HEAD') {
      let raw = '';
      const b = init?.body;
      if (typeof b === 'string') raw = b;
      else if (b == null && req) raw = await req.clone().text().catch(() => '');
      try { body = raw ? JSON.parse(raw) : undefined; } catch { body = raw; }
    }

    // A short pause so loading states and transitions are visible, as with a real server.
    await wait(140 + Math.random() * 160);

    for (const r of routes) {
      if (r.method && r.method !== method) continue;
      const m = typeof r.path === 'string' ? (r.path === path ? [path] : null) : path.match(r.path);
      if (!m) continue;
      const out = await r.handle({ path, query: url.searchParams, body, match: m as string[] });
      const rawOut = out as { __raw?: unknown; __contentType?: string } | null;
      if (rawOut && typeof rawOut === 'object' && typeof rawOut.__raw === 'string') {
        return new Response(rawOut.__raw, { status: 200, headers: { 'Content-Type': rawOut.__contentType || 'text/plain; charset=utf-8' } });
      }
      return new Response(JSON.stringify(out), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // Logged so scripts/check-pages.mjs can list screens the sample data does not cover yet.
    console.warn(`[demo] No sample data for ${method} ${path}`);
    return new Response(JSON.stringify({ message: `No sample data for ${method} ${path}` }), { status: 404, headers: { 'Content-Type': 'application/json' } });
  };

  // Keep the preview out of search engines.
  const meta = document.createElement('meta');
  meta.name = 'robots';
  meta.content = 'noindex, nofollow, noarchive';
  document.head.appendChild(meta);
}
