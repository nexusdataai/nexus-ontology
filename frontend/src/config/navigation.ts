/**
 * Single source of truth for product navigation.
 * Used by the sidebar, mobile navigation, breadcrumbs and the command palette.
 * Add a new screen here and it appears in all four.
 */
import type { IconName } from '@/components/ds/Icon';

export interface NavItem {
  id: string;
  name: string;
  path: string;
  /** Icon name from the product icon set (see components/ds/Icon). */
  icon: IconName;
  /** Short line shown in the command palette. */
  hint?: string;
  /** Extra path prefixes that should highlight this item. */
  match?: string[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'AI Stack',
    items: [
      { id: 'home', name: 'Home', path: '/', icon: 'home', hint: 'Platform overview' },
      { id: 'dp', name: 'Data Plane', path: '/ai-stack/data-plane', icon: 'database', hint: 'Sources, virtual data, mapping, pipelines' },
      { id: 'cp', name: 'Control Plane', path: '/ai-stack/control-plane', icon: 'layers', hint: 'Ontology, knowledge graph, policies' },
      { id: 'reason', name: 'Reasoning', path: '/ai-stack/reasoning', icon: 'brain-ai', hint: 'Copilot, playground, tools' },
    ],
  },
  {
    label: 'Workspace',
    items: [
      { id: 'apps', name: 'Solutions', path: '/workspace/apps', icon: 'apps', hint: 'Packaged business applications', match: ['/apps/'] },
      { id: 'analytics', name: 'AI Analytics', path: '/ai-analytics', icon: 'chart-bar', hint: 'Dashboards and views', match: ['/dashboards', '/dashboard/', '/views'] },
      { id: 'automation', name: 'AI Automation', path: '/workspace/automation', icon: 'workflow', hint: 'Journeys, copilot, builder' },
    ],
  },
  {
    label: 'AI Ops',
    items: [
      { id: 'diag', name: 'Diagnostics', path: '/operations/diagnostics', icon: 'stethoscope', hint: 'Checks per solution and subsystem' },
      { id: 'health', name: 'Health', path: '/operations/health', icon: 'heartbeat', hint: 'Monitoring, jobs, audit' },
      { id: 'simulator', name: 'Enterprise Simulator', path: '/simulator', icon: 'flask', hint: 'Practice enterprise for testing' },
    ],
  },
];

export const SETTINGS_ITEM: NavItem = {
  id: 'settings', name: 'Settings', path: '/settings', icon: 'settings', hint: 'Profile, users, license, system',
  match: ['/user-management'],
};

export const HELP_ITEM: NavItem = {
  id: 'help', name: 'Help', path: '/help', icon: 'help', hint: 'Documentation, support, contact',
};

export const ALL_NAV_ITEMS: NavItem[] = [...NAV_GROUPS.flatMap(g => g.items), SETTINGS_ITEM, HELP_ITEM];

/** Items shown in the phone bottom bar (the rest live in the drawer). */
export const MOBILE_TAB_IDS = ['home', 'apps', 'analytics', 'automation'];

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (item.path === '/') return pathname === '/';
  if (pathname === item.path || pathname.startsWith(item.path + '/')) return true;
  return (item.match || []).some(m => pathname === m || pathname.startsWith(m));
}

/** Sub-page titles that are not top-level navigation items. */
const SUB_TITLES: { prefix: string; title: string }[] = [
  { prefix: '/ai-stack/data-plane/create', title: 'Add data source' },
  { prefix: '/ai-stack/data-plane/', title: 'Runtime explorer' },
  { prefix: '/dashboard/builder', title: 'Dashboard builder' },
  { prefix: '/dashboard/view', title: 'Dashboard' },
  { prefix: '/views/builder', title: 'View builder' },
  { prefix: '/views/', title: 'View' },
  { prefix: '/workspace/tools', title: 'Tools catalogue' },
];

export interface Crumb {
  label: string;
  path?: string;
}

/** Breadcrumb trail for a pathname: Group / Page / Sub-page. */
export function getBreadcrumbs(pathname: string): Crumb[] {
  if (pathname === '/') return [{ label: 'Home' }];

  if (isNavItemActive(SETTINGS_ITEM, pathname)) return [{ label: 'Settings' }];
  if (isNavItemActive(HELP_ITEM, pathname)) return [{ label: 'Help' }];

  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (item.path === '/' || !isNavItemActive(item, pathname)) continue;
      const crumbs: Crumb[] = [{ label: group.label }];
      const sub = SUB_TITLES.find(s => pathname.startsWith(s.prefix) && pathname !== item.path);
      if (sub) {
        crumbs.push({ label: item.name, path: item.path });
        crumbs.push({ label: sub.title });
      } else {
        crumbs.push({ label: item.name });
      }
      return crumbs;
    }
  }

  const sub = SUB_TITLES.find(s => pathname.startsWith(s.prefix));
  return [{ label: sub?.title || 'Nexus AI' }];
}

export function getPageTitle(pathname: string): string {
  const crumbs = getBreadcrumbs(pathname);
  return crumbs[crumbs.length - 1].label;
}
