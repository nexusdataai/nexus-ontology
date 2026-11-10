/**
 * Sample responses, one entry per backend endpoint.
 * Shapes follow what the screens read today. Keep values realistic.
 *
 * This file is the entry point the plugin imports. The responses live in
 * routes/<area>.ts; shared names (entities, systems, journeys) in fixtures.ts;
 * the row generator and query engine in rows.ts.
 *
 * Routes are matched in array order: within each area, specific paths come
 * before patterns. The catch-all for create/update/delete calls is last.
 */
import { type SampleRoute, asObj } from './fixtures';
import { homeRoutes } from './routes/home';
import { dataPlaneRoutes } from './routes/data-plane';
import { controlPlaneRoutes } from './routes/control-plane';
import { reasoningRoutes } from './routes/reasoning';
import { solutionsRoutes } from './routes/solutions';
import { analyticsRoutes } from './routes/analytics';
import { automationRoutes } from './routes/automation';
import { opsRoutes } from './routes/ops';
import { settingsRoutes } from './routes/settings';

export type { SampleRoute } from './fixtures';

/**
 * Create, update and delete calls that have no route of their own. Nothing is
 * stored: the call succeeds so buttons do not show an error, and the next
 * reload shows the original sample data again.
 *
 * Sign-in, password and MFA calls (/api/v1/auth/) are left unanswered on
 * purpose, so security actions never appear to succeed.
 */
const MUTATION_PATH = /^\/api\/(?!v1\/auth\/)/;
const mutationFallback: SampleRoute[] = [
  { method: 'DELETE', path: MUTATION_PATH, handle: () => ({ success: true, status: 'deleted' }) },
  ...(['POST', 'PUT', 'PATCH'] as const).map((method): SampleRoute => ({
    method,
    path: MUTATION_PATH,
    handle: ({ body }) => ({ ...asObj(body), id: asObj(body).id ?? `sample-${Date.now().toString(36)}`, success: true, status: 'ok' }),
  })),
];

export const routes: SampleRoute[] = [
  ...homeRoutes,
  ...dataPlaneRoutes,
  ...controlPlaneRoutes,
  ...reasoningRoutes,
  ...solutionsRoutes,
  ...analyticsRoutes,
  ...automationRoutes,
  ...opsRoutes,
  ...settingsRoutes,
  ...mutationFallback,
];
