/**
 * The four Nexus platforms and how each one relates to the ontology.
 * Shown in the top-bar platform switcher and on Health > Connected platforms.
 *
 * Addresses: the simulator's comes from the backend (/api/v1/config/simulator);
 * the others default to the yourbrain.tech hosts and can be overridden in
 * public/config.json under "platforms": { "aiEngine": "...", "sre": "..." }.
 */
import { useEffect, useState } from 'react';
import type { IconName } from '@/components/ds/Icon';
import { getSimulatorConfig } from '@/services/simulatorLink';

export type PlatformId = 'ontology' | 'ai-engine' | 'sre' | 'simulator';
export type Relation = 'self' | 'connected' | 'not-connected' | 'separate';

export interface Platform {
  id: PlatformId;
  name: string;
  role: string;
  icon: IconName;
  relation: Relation;
  /** One sentence on how it works with the ontology. */
  link: string;
  url: string;
}

const BASE: Omit<Platform, 'url'>[] = [
  { id: 'ontology', name: 'Ontology', role: 'Data, knowledge, reasoning and solutions', icon: 'network', relation: 'self',
    link: 'This platform: the data plane, the ontology and knowledge graph, the copilot, solutions and automations.' },
  { id: 'simulator', name: 'Enterprise Simulator', role: 'Practice enterprise systems', icon: 'flask', relation: 'connected',
    link: 'Supplies the data for every source running in simulator mode. The ontology calls its API and reads its tables in place.' },
  { id: 'ai-engine', name: 'AI Engine', role: 'Journey and job execution', icon: 'bolt', relation: 'not-connected',
    link: 'Runs AI journeys and executions. The ontology has a connection for sending copilot journey runs to it; that connection is not switched on yet.' },
  { id: 'sre', name: 'SRE', role: 'Cluster operations and incidents', icon: 'heartbeat', relation: 'separate',
    link: 'Watches the cluster all four platforms run on: services, incidents and runbooks. It does not read ontology data.' },
];

let cache: Promise<Platform[]> | null = null;

export function getPlatforms(): Promise<Platform[]> {
  if (cache) return cache;
  cache = (async () => {
    let overrides: Record<string, string> = {};
    try {
      const res = await fetch('/config.json', { cache: 'no-store' });
      if (res.ok) overrides = ((await res.json()) as { platforms?: Record<string, string> }).platforms || {};
    } catch { /* defaults */ }
    let sim = '';
    try { sim = (await getSimulatorConfig()).uiUrl; } catch { /* defaults */ }
    const urls: Record<PlatformId, string> = {
      ontology: window.location.origin,
      simulator: overrides.simulator || sim || 'https://simulator.yourbrain.tech',
      'ai-engine': overrides.aiEngine || 'https://ai-engine.yourbrain.tech',
      sre: overrides.sre || 'https://sre.yourbrain.tech',
    };
    return BASE.map(p => ({ ...p, url: urls[p.id] }));
  })();
  return cache;
}

/** Whether something answers at an address (no-cors: the reply itself is not read). */
async function reachable(url: string): Promise<boolean> {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), 4000);
  try {
    await fetch(url, { mode: 'no-cors', cache: 'no-store', signal: ctrl.signal });
    return true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

export type Reach = 'checking' | 'up' | 'down';

/** The platforms, with whether each one answers right now. */
export function usePlatforms(check = true) {
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [reach, setReach] = useState<Record<string, Reach>>({});
  useEffect(() => {
    let live = true;
    getPlatforms().then(list => {
      if (!live) return;
      setPlatforms(list);
      if (!check) return;
      setReach(Object.fromEntries(list.map(p => [p.id, p.id === 'ontology' ? 'up' : 'checking'])));
      list.filter(p => p.id !== 'ontology').forEach(p => reachable(p.url).then(ok => { if (live) setReach(r => ({ ...r, [p.id]: ok ? 'up' : 'down' })); }));
    });
    return () => { live = false; };
  }, [check]);
  return { platforms, reach };
}

export const RELATION_LABEL: Record<Relation, string> = {
  self: 'This platform',
  connected: 'Connected',
  'not-connected': 'Not connected yet',
  separate: 'Separate',
};
