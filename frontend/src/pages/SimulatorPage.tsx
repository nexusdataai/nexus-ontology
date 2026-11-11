/**
 * Enterprise Simulator landing page.
 *
 * The simulator is a separate application (its address comes from
 * /api/v1/config/simulator). Opening it blindly gives a blank browser tab
 * when it is not running, so this page checks first, says what the simulator
 * is for, and only then offers to open it.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Icon, type IconName } from '@/components/ds/Icon';
import { StatusPill, KeyValues } from '@/components/ds/kit';
import { SystemLogo } from '@/components/ds/SystemLogo';
import { getSimulatorConfig } from '@/services/simulatorLink';

type State = 'checking' | 'online' | 'offline';

const USES: { title: string; text: string; icon: IconName }[] = [
  { title: 'Realistic source systems', text: 'Stand-ins for Salesforce, SAP and Oracle with consistent customers, orders, deliveries and invoices.', icon: 'database' },
  { title: 'Inject business events', text: 'Create a late delivery, a price mismatch or a credit breach and watch the agents react.', icon: 'bolt' },
  { title: 'Safe to experiment', text: 'Nothing here touches a production system. Reset the data whenever you like.', icon: 'shield-check' },
];

async function reachable(url: string): Promise<boolean> {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), 3500);
  try {
    // no-cors: we only need to know that something answers at this address.
    await fetch(url, { mode: 'no-cors', cache: 'no-store', signal: ctrl.signal });
    return true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

export default function SimulatorPage() {
  const [url, setUrl] = useState('');
  const [state, setState] = useState<State>('checking');

  const check = useCallback(async () => {
    setState('checking');
    const cfg = await getSimulatorConfig();
    setUrl(cfg.uiUrl);
    setState(cfg.enabled !== false && (await reachable(cfg.uiUrl)) ? 'online' : 'offline');
  }, []);

  useEffect(() => { check(); }, [check]);

  return (
    <Layout>
      <div className="page">
        <div className="grid items-start gap-x-12 gap-y-10 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <section className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-lg font-medium tracking-tight text-foreground">Enterprise Simulator</h1>
              {state === 'checking' ? <StatusPill status="running">Checking</StatusPill> : state === 'online' ? <StatusPill status="online" live tone="success">Running</StatusPill> : <StatusPill status="offline">Not running</StatusPill>}
            </div>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              A practice enterprise for Nexus AI. It plays the part of your business systems, so you can try connectors, mapping rules, solutions and automations end to end before pointing them at real data.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              {state === 'online' ? (
                <Button asChild>
                  <a href={url} target="_blank" rel="noopener noreferrer">Open the simulator <Icon name="external-link" className="h-3.5 w-3.5" /></a>
                </Button>
              ) : (
                <Button onClick={check} disabled={state === 'checking'}>
                  <Icon name={state === 'checking' ? 'spinner' : 'refresh'} className={state === 'checking' ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} />
                  {state === 'checking' ? 'Checking' : 'Check again'}
                </Button>
              )}
              <Button variant="outline" asChild><Link to="/ai-stack/data-plane">See connected sources</Link></Button>
            </div>

            {state === 'offline' && (
              <div className="mt-6 animate-fade-up rounded-xl border border-border bg-card p-5 shadow-xs">
                <h2 className="flex items-center gap-2 text-md font-medium text-foreground">
                  <Icon name="info" className="h-4 w-4 text-muted-foreground" /> The simulator is not running in this environment
                </h2>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  Nothing answered at <span className="font-mono text-xs text-foreground">{url}</span>, so opening it would show an empty page. It runs as its own service next to the platform. Ask your administrator to start it, then check again.
                </p>
              </div>
            )}

            <ul className="mt-10 divide-y divide-border border-y border-border">
              {USES.map((u, i) => (
                <li key={u.title} className="rise flex items-start gap-4 py-4" style={{ ['--i' as any]: i }}>
                  <Icon name={u.icon} className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                  <div>
                    <h3 className="text-sm font-medium text-foreground">{u.title}</h3>
                    <p className="mt-0.5 text-sm text-muted-foreground">{u.text}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <aside className="min-w-0 rounded-xl border border-border bg-card p-6 shadow-xs">
            <h2 className="text-md font-medium text-foreground">How it fits in</h2>
            <ol className="mt-5 space-y-0">
              {[
                { label: 'Simulated systems', node: <span className="flex items-center gap-2"><SystemLogo system="salesforce" tile size="sm" /><SystemLogo system="sap" tile size="sm" /><SystemLogo system="oracle" tile size="sm" /></span> },
                { label: 'Data Plane reads them like real sources', node: <Icon name="database" className="h-5 w-5 text-foreground" /> },
                { label: 'Solutions and agents act on the result', node: <Icon name="brain-ai" className="h-5 w-5 text-foreground" /> },
              ].map((s, i, arr) => (
                <li key={s.label} className="relative flex gap-4 pb-6 last:pb-0">
                  {i < arr.length - 1 && (
                    <svg className="absolute left-[19px] top-10 h-[calc(100%-40px)] w-px overflow-visible text-primary dark:text-brand-hi" aria-hidden="true">
                      <line x1="0" y1="0" x2="0" y2="100%" stroke="currentColor" strokeWidth="1.5" className="flow-line" />
                    </svg>
                  )}
                  <span className="flex h-10 min-w-10 shrink-0 items-center justify-center">{s.node}</span>
                  <span className="pt-2.5 text-sm text-muted-foreground">{s.label}</span>
                </li>
              ))}
            </ol>
            <div className="mt-6 border-t border-border pt-2">
              <KeyValues items={[{ label: 'Address', value: url || 'Not configured', mono: true }, { label: 'Opens in', value: 'A new browser tab' }]} />
            </div>
          </aside>
        </div>
      </div>
    </Layout>
  );
}
