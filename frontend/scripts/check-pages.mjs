#!/usr/bin/env node
/**
 * Page check: opens every screen of the product in a headless browser against
 * a running backend and reports what is broken. It only reads: it never clicks
 * a button, saves, runs or deletes anything.
 *
 * Usage (from frontend/):
 *   npm install --no-save playwright-core@1.62.1   # once; not added to package.json
 *   npx playwright-core install chromium           # once, if no Chromium is cached
 *   node scripts/check-pages.mjs https://ontology.yourbrain.tech
 *
 * Options:
 *   --only=/apps        check only pages whose path starts with this
 *   --wait=5000         milliseconds to let each page load (default 5000)
 *   --json=report.json  also write the full result as JSON
 *   --strict            treat known backend issues as failures too
 *
 * A page FAILS when: the app crashes (uncaught error), the page shows the
 * "Something went wrong" screen, the content area is empty, or an API call
 * returns 5xx (or 4xx other than the expected ones). Known backend issues are
 * listed in KNOWN below and reported as warnings unless --strict is given.
 * Exit code: 0 when every page passes, 1 otherwise.
 */
const args = process.argv.slice(2);
const base = (args.find((a) => !a.startsWith('--')) || '').replace(/\/$/, '');
const opt = (name, fallback) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : fallback;
};
const strict = args.includes('--strict');
const only = opt('only', '');
const waitMs = Number(opt('wait', '5000'));
const jsonPath = opt('json', '');

if (!base) {
  console.error('Give the address to check, for example:\n  node scripts/check-pages.mjs https://ontology.yourbrain.tech');
  process.exit(2);
}

let chromium;
try {
  ({ chromium } = await import('playwright-core'));
} catch {
  try {
    ({ chromium } = await import('playwright'));
  } catch {
    console.error('Playwright is not installed. From frontend/ run:\n  npm install --no-save playwright-core@1.62.1\n  npx playwright-core install chromium');
    process.exit(2);
  }
}

/** Fixed screens. Pages that need an id (one solution, one dashboard, one view) are added from the API below. */
const PAGES = [
  '/',
  '/ai-stack/data-plane',
  '/ai-stack/data-plane?tab=virtualdata',
  '/ai-stack/data-plane?tab=vdl-apis',
  '/ai-stack/data-plane?tab=mappingrules',
  '/ai-stack/data-plane?tab=pipelines',
  '/ai-stack/data-plane?tab=connectors',
  '/ai-stack/data-plane/sample-crm?mode=simulator&source=simulator',
  '/ai-stack/data-plane/sample-crm?mode=simulator&source=simulator&tab=query',
  '/ai-stack/control-plane',
  '/ai-stack/control-plane?tab=explorer',
  '/ai-stack/control-plane?tab=policies',
  '/ai-stack/control-plane?tab=workflows',
  '/ai-stack/control-plane?tab=integrations',
  '/ai-stack/reasoning',
  '/ai-stack/reasoning?tab=playground',
  '/ai-stack/reasoning?tab=tools',
  '/workspace/apps',
  '/ai-analytics',
  '/ai-analytics?tab=views',
  '/ai-analytics?tab=solutions',
  '/dashboard/builder',
  '/views/builder',
  '/workspace/automation',
  '/workspace/automation?tab=copilot',
  '/workspace/automation?tab=builder',
  '/workspace/automation?tab=registry',
  '/operations/diagnostics',
  '/operations/health',
  '/operations/health?tab=jobs',
  '/operations/health?tab=audit',
  '/settings',
  '/help',
  '/simulator',
];

/** Requests that fail today because of the backend, not the UI. Shown as warnings. */
const KNOWN = [
  { re: /\/api\/data-planes\/sample-/, why: 'sample sources have no data-plane record (404)' },
  { re: /\/api\/v1\/control-plane\/journeys\//, why: 'old control-plane journey route (404); the UI falls back to /api/v1/journeys' },
  { re: /\/api\/v1\/tests\/status/, why: 'test runner not deployed (503)' },
  { re: /\/api\/fdw\/tables\/external_sources\/.*\/columns/, why: 'columns of external_sources tables (500)' },
  { re: /\/api\/v1\/auth\/me/, why: 'sign-in is switched off on this environment (401)', quiet: true },
  { re: /\/api\/v1\/solutions\/by-app\/(sourcing|trade)-cpq/, why: 'CPQ solutions have no solution record (404)' },
  { re: /\/api\/v1\/dashboards\/sfv-[0-9a-f]+$/, why: 'a view tab points at a dashboard id that does not exist (404)', status: 404 },
];
const knownOf = (url, status) => KNOWN.find((k) => k.re.test(url) && (!k.status || k.status === status));

/** Read the API through the app's own page, so design previews (VITE_DEMO) answer too. */
let page;
async function getJson(path) {
  try {
    return await page.evaluate(async (p) => {
      const r = await fetch(p);
      return r.ok ? r.json() : null;
    }, path);
  } catch {
    return null;
  }
}

/** One real solution, dashboard and view, so their pages are checked with data. */
async function discoverPages() {
  const extra = [];
  const cat = await getJson('/api/v1/solution-catalog');
  const sols = (cat && (cat.solutions || cat.items || cat.data || cat)) || [];
  for (const s of Array.isArray(sols) ? sols : []) {
    const id = s.id || s.appId || s.solutionId;
    // Catalogue entries marked coming soon have no screens yet.
    if (!id || /coming|planned/i.test(String(s.status || ''))) continue;
    extra.push(`/apps/${id}`);
    if (id === 'order-to-cash') extra.push(`/apps/${id}?section=analytics`, `/apps/${id}?section=workflows`, `/apps/${id}?section=reports`);
  }
  const dl = await getJson('/api/v1/dashboards');
  const dashes = (dl && (dl.dashboards || dl.items || dl.data || dl)) || [];
  const d = Array.isArray(dashes) && dashes[0];
  if (d && (d.uid || d.id)) extra.push(`/dashboard/view/${d.uid || d.id}`, `/dashboard/builder/${d.uid || d.id}`);
  const vl = await getJson('/api/v1/views');
  const views = (vl && (vl.views || vl.items || vl.data || vl)) || [];
  const v = Array.isArray(views) && views[0];
  if (v && (v.viewId || v.id)) extra.push(`/views/${v.viewId || v.id}`, `/views/builder/${v.viewId || v.id}`);
  return extra;
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
page = await context.newPage();
await page.goto(base + '/', { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
await page.waitForTimeout(2500);
const pages = [...PAGES, ...(await discoverPages())].filter((p) => !only || p.startsWith(only));
if (pages.length === 0) {
  // Git Bash on Windows rewrites "/apps" into a Windows path; set MSYS_NO_PATHCONV=1 there.
  console.error(`No page matches --only=${only}. Give a path that starts with "/", for example --only=/apps.`);
  process.exit(2);
}


const results = [];
let current = null;
page.on('pageerror', (err) => current && current.crashes.push(String(err.message || err).slice(0, 300)));
// Design preview builds (VITE_DEMO=true) answer API calls in the browser; a call
// the sample data does not cover is logged instead of reaching the network.
page.on('console', (msg) => {
  if (!current || !/\[demo\] No sample data/.test(msg.text())) return;
  const text = msg.text().replace('[demo] ', '');
  const known = knownOf(text.replace(/^No sample data for [A-Z]+ /, ''), 404);
  (known && !strict ? current.warnings : current.failedCalls).push(`${text}${known ? ` (known: ${known.why})` : ''}`);
});
page.on('response', (res) => {
  if (!current) return;
  const url = res.url();
  if (!url.startsWith(base) || !/\/(api|health|stats|tools|journeys)\//.test(url.slice(base.length))) return;
  const status = res.status();
  if (status < 400) return;
  const path = url.slice(base.length);
  const known = knownOf(path, status);
  if (known && known.quiet && !strict) return;
  (known && !strict ? current.warnings : current.failedCalls).push(`${res.request().method()} ${path} → ${status}${known ? ` (known: ${known.why})` : ''}`);
});

const started = Date.now();
for (const path of pages) {
  current = { path, crashes: [], failedCalls: [], warnings: [], problems: [], ms: 0 };
  const t0 = Date.now();
  try {
    await page.goto(base + path, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(waitMs);
    const state = await page.evaluate(() => {
      const main = document.querySelector('main');
      const text = (main ? main.innerText : document.body.innerText || '').trim();
      return { hasMain: !!main, length: text.length, broken: /Something went wrong while showing this screen/.test(document.body.innerText || ''), title: document.title };
    });
    if (state.broken) current.problems.push('shows the "Something went wrong" screen');
    if (!state.hasMain) current.problems.push('no content area: the app did not start');
    else if (state.length < 20) current.problems.push('content area is empty');
    current.title = state.title;
  } catch (e) {
    current.problems.push(`did not load: ${String(e.message || e).split('\n')[0]}`);
  }
  current.ms = Date.now() - t0;
  current.ok = current.crashes.length === 0 && current.failedCalls.length === 0 && current.problems.length === 0;
  results.push(current);
  const mark = current.ok ? (current.warnings.length ? 'PASS*' : 'PASS ') : 'FAIL ';
  console.log(`${mark} ${path}`);
  for (const p of current.problems) console.log(`        ${p}`);
  for (const c of current.crashes) console.log(`        crash: ${c}`);
  for (const f of current.failedCalls) console.log(`        ${f}`);
  for (const w of current.warnings) console.log(`        warning: ${w}`);
}
current = null;
await browser.close();

const failed = results.filter((r) => !r.ok);
const warned = results.filter((r) => r.ok && r.warnings.length);
console.log(`\n${results.length} pages checked in ${Math.round((Date.now() - started) / 1000)} s: ${results.length - failed.length} passed (${warned.length} with known backend warnings), ${failed.length} failed.`);
if (jsonPath) {
  const { writeFileSync } = await import('node:fs');
  writeFileSync(jsonPath, JSON.stringify({ base, checkedAt: new Date().toISOString(), results }, null, 2));
  console.log(`Report written to ${jsonPath}`);
}
process.exit(failed.length ? 1 : 0);
