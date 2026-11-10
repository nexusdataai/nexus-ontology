/**
 * Help centre: documentation, support and contact in one place.
 * Tabs live in the URL (?tab=documentation | support | contact).
 *
 * There is no ticketing backend: "Email support" and the contact form open
 * the user's own email app with the message filled in (mailto:).
 */
import { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import { PageTabsBar, useUrlTab, type TabSection } from '@/components/ds/PageTabs';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon, type IconName } from '@/components/ds/Icon';
import { Field, SearchInput } from '@/components/ds/kit';
import { Kbd } from '@/components/ds/primitives';

const SUPPORT_EMAIL = 'support@ptrtechnology.com';
const CONTACT_EMAIL = 'contact@ptrtechnology.com';

const SECTIONS: TabSection[] = [
  { label: 'Documentation', icon: 'document', items: [{ value: 'documentation', label: 'Documentation' }] },
  { label: 'Support', icon: 'help', items: [{ value: 'support', label: 'Support' }] },
  { label: 'Contact', icon: 'mail', items: [{ value: 'contact', label: 'Contact' }] },
];

const START: { title: string; text: string; to: string; icon: IconName; step: string }[] = [
  { step: 'Step 1', title: 'Check your sources', text: 'Each source system (Salesforce, Oracle, SAP, files, Google Drive, social) runs on simulated or real data. Open one to browse its tables in place.', to: '/ai-stack/data-plane', icon: 'plug' },
  { step: 'Step 2', title: 'Map business entities', text: 'Mapping rules bind each business entity (Customer, AR Invoice, Opportunity) to a source table. An entity with no active rule has no data.', to: '/ai-stack/data-plane?tab=mappingrules', icon: 'route' },
  { step: 'Step 3', title: 'Build the knowledge index', text: 'The knowledge pipeline reads entities, mapping rules, policies, workflows and integration rules, and writes the index and graph the agents use.', to: '/ai-stack/control-plane', icon: 'layers' },
  { step: 'Step 4', title: 'Run a solution', text: 'Open a solution such as Order-to-Cash and choose Run journey. Its numbers, alerts and actions appear after the first run.', to: '/workspace/apps', icon: 'apps' },
];

const GUIDES: { area: string; items: { title: string; text: string; to: string }[] }[] = [
  { area: 'Data Plane', items: [
    { title: 'Sources and simulated data', text: 'Which systems are connected and whether each one reads simulated or real data. Real data needs an administrator to switch it on.', to: '/ai-stack/data-plane' },
    { title: 'Browse a source in place', text: 'Open a source to search its tables, see their columns and preview rows. Nothing is copied: the tables are read where they are.', to: '/ai-stack/data-plane' },
    { title: 'Business entities', text: 'The canonical entities, grouped by business domain, with their fields, links, risk level and live sample rows.', to: '/ai-stack/data-plane?tab=virtualdata' },
    { title: 'Entity APIs', text: 'The read and write operations on each entity, and which connector carries out a write.', to: '/ai-stack/data-plane?tab=vdl-apis' },
    { title: 'Mapping rules', text: 'Bind an entity to a source table, map fields, add a filter, preview five rows. Rules named "Auto" were created by automatic matching and read every column as it is.', to: '/ai-stack/data-plane?tab=mappingrules' },
    { title: 'Data pipelines', text: 'Batch loads for sources that cannot be read in place, such as file uploads, Google Drive and social listening.', to: '/ai-stack/data-plane?tab=pipelines' },
    { title: 'Connectors', text: 'The systems Nexus AI can read from and act on, and the API workbench to test each connector call.', to: '/ai-stack/data-plane?tab=connectors' },
  ] },
  { area: 'Control Plane', items: [
    { title: 'Knowledge pipeline and index', text: 'The thirteen steps from schemas to quality check, each run and what it produced. Rebuild after you change policies, workflows, integration rules or mappings.', to: '/ai-stack/control-plane' },
    { title: 'Knowledge graph', text: 'Entities grouped by business domain, with the source system behind each. Constellation, lanes and lineage views; trace the path between two entities.', to: '/ai-stack/control-plane?tab=explorer' },
    { title: 'Policies', text: 'Business rules, limits and approval thresholds the agents must respect, such as the financial close window or credit limits.', to: '/ai-stack/control-plane?tab=policies' },
    { title: 'Workflows', text: 'Processes that span systems: what starts them, their steps and the entities they depend on.', to: '/ai-stack/control-plane?tab=workflows' },
    { title: 'Integration rules', text: 'Field-level sync between systems, which side owns each field, and how often it runs.', to: '/ai-stack/control-plane?tab=integrations' },
  ] },
  { area: 'Reasoning', items: [
    { title: 'Copilot', text: 'Ask about your enterprise. Every answer lists the tools the agent called, the time it took and the policies it checked.', to: '/ai-stack/reasoning' },
    { title: 'Playground', text: 'See which schemas, policies, workflows and integrations retrieval brings back for a question, and run the test suite.', to: '/ai-stack/reasoning?tab=playground' },
    { title: 'Tools', text: 'The tools the agent may call, which ones only read and which change data, and which need approval.', to: '/ai-stack/reasoning?tab=tools' },
  ] },
  { area: 'Workspace', items: [
    { title: 'Solutions', text: 'Packaged applications (Order-to-Cash, Demand forecasting, CPQ and more) with business insights, process analytics, workflow actions and alerts.', to: '/workspace/apps' },
    { title: 'Dashboards', text: 'Panels on business entities: pick the entity, fields, filters and how to show it, with a live preview.', to: '/ai-analytics' },
    { title: 'Views', text: "Tabs of dashboards that appear in a solution's side menu, such as Monitor, Diagnose, Predict and Outcomes.", to: '/ai-analytics?tab=views' },
    { title: 'Journeys', text: "Automations that run a solution's steps, by hand or on a schedule. Each run keeps its step log and results.", to: '/workspace/automation' },
    { title: 'Automation copilot and playbooks', text: 'Describe a goal; the copilot proposes a plan from the playbooks, and nothing runs until you approve it.', to: '/workspace/automation?tab=copilot' },
  ] },
  { area: 'AI Ops', items: [
    { title: 'Diagnostics', text: 'Five checks per solution, from source data to results, plus checks of simulators, entities, dashboards, automation and tools.', to: '/operations/diagnostics' },
    { title: 'Health', text: 'A check of every platform area every 15 minutes, scheduled jobs, the audit log of diagnostics runs, and test reports.', to: '/operations/health' },
    { title: 'Enterprise Simulator', text: 'The practice enterprise behind simulated data, for testing without touching a real system.', to: '/simulator' },
  ] },
];

const FAQ: { q: string; a: string }[] = [
  { q: 'Does Nexus AI copy my data out of the source systems?', a: 'Most sources are read in place through the virtual data layer, using the mapping rules. Sources that cannot be read in place (file uploads, Google Drive, social listening) are loaded by a data pipeline. Data Plane shows which is which.' },
  { q: 'What is the difference between simulated and real data?', a: 'Every source starts on simulated data from the Enterprise Simulator, so you can try everything safely. An administrator switches a source to real data. The mode shows on the source and on every journey.' },
  { q: 'A solution or dashboard shows no numbers. What should I check?', a: "Most often the solution's journey has not run yet: open the solution and choose Run journey. If it has run, open Diagnostics and run that solution's checks; they show which entity has no data or no active mapping rule." },
  { q: 'Why did the numbers change after a run?', a: "Each journey run recalculates the solution's results from the current data and replaces the previous figures. The run history in AI Automation shows when each run happened and what it read." },
  { q: 'When should I rebuild the knowledge index?', a: 'After you change a policy, workflow, integration rule or mapping rule. Until then the agents answer from the previous index. Rebuilding takes a few minutes and uses the language model.' },
  { q: 'Why did the assistant refuse to run an action?', a: 'Agents can only use the tools and follow the policies in the Control Plane. When a policy blocks a step, the answer says which one. Actions that change a source system wait for approval.' },
  { q: 'How do I give a colleague access?', a: 'Open Settings, then Users to invite people and Roles and permissions to decide what each role may do. Only administrators see these sections.' },
];

const SHORTCUTS: { keys: string[]; label: string }[] = [
  { keys: ['Ctrl', 'K'], label: 'Search or jump to any screen' },
  { keys: ['Ctrl', 'J'], label: 'Open or close the Nexus assistant' },
  { keys: ['Esc'], label: 'Close a panel, sheet or dialog' },
];

const mailto = (to: string, subject: string, body: string) => `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

export default function HelpPage() {
  const [tab, setTab] = useUrlTab('documentation');
  const loc = useLocation();
  const [query, setQuery] = useState('');
  const [topic, setTopic] = useState('question');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');

  const q = query.trim().toLowerCase();
  const guides = useMemo(
    () => GUIDES.map(g => ({ ...g, items: g.items.filter(i => !q || `${i.title} ${i.text} ${g.area}`.toLowerCase().includes(q)) })).filter(g => g.items.length > 0),
    [q],
  );

  const supportBody = [
    'Describe what happened and what you expected:',
    '',
    '',
    '---',
    `Page: ${window.location.origin}${loc.pathname}`,
    `Time: ${new Date().toISOString()}`,
    `Browser: ${navigator.userAgent}`,
  ].join('\n');

  const topics: Record<string, string> = { question: 'Product question', demo: 'Request a demo', pricing: 'Pricing and plans', partner: 'Partnership', other: 'Something else' };
  const canSend = message.trim().length > 0;

  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab}>
        <PageTabsBar title="Help" description="Guides for every part of the product, and how to reach us." sections={SECTIONS} value={tab} onChange={setTab} />

        {/* ------------------------------------------------- documentation */}
        <TabsContent value="documentation" className="mt-0">
          <div className="page space-y-10">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className="text-xl font-medium tracking-tight text-foreground">Start here</h2>
                <p className="mt-1 text-sm text-muted-foreground">Four steps take you from connected systems to a working solution. Do them in this order: each step uses what the one before it produced.</p>
              </div>
              <Button variant="outline" asChild>
                <a href="/docs/" target="_blank" rel="noopener noreferrer">Full documentation <Icon name="external-link" className="h-3.5 w-3.5" /></a>
              </Button>
            </div>

            <ol className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {START.map((s, i) => (
                <li key={s.title} className="rise" style={{ ['--i' as any]: i }}>
                  <Link
                    to={s.to}
                    className="group flex h-full flex-col rounded-xl border border-border bg-card p-5 shadow-xs transition-all duration-300 ease-brand-out hover:-translate-y-0.5 hover:border-brand/50 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="flex items-center justify-between">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-foreground"><Icon name={s.icon} className="h-5 w-5" /></span>
                      <span className="text-xs text-muted-foreground">{s.step}</span>
                    </span>
                    <span className="mt-4 text-md font-medium text-foreground">{s.title}</span>
                    <span className="mt-1 text-sm text-muted-foreground">{s.text}</span>
                    <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-foreground">
                      Open <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
                    </span>
                  </Link>
                </li>
              ))}
            </ol>

            <div className="grid gap-x-12 gap-y-10 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
              <section className="min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
                  <h2 className="text-md font-medium text-foreground">Guides by area</h2>
                  <SearchInput value={query} onChange={setQuery} placeholder="Search the guides" className="w-full sm:w-64" />
                </div>
                {guides.length === 0 ? (
                  <p className="py-8 text-sm text-muted-foreground">No guide matches that search. Try a shorter word, or ask the assistant.</p>
                ) : guides.map(g => (
                  <div key={g.area} className="mt-5">
                    <h3 className="text-xs font-medium text-muted-foreground">{g.area}</h3>
                    <ul className="mt-1 divide-y divide-border">
                      {g.items.map(item => (
                        <li key={item.title}>
                          <Link to={item.to} className="group flex items-center gap-4 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            <span className="min-w-0 flex-1">
                              <span className="block text-sm font-medium text-foreground group-hover:underline group-hover:underline-offset-4">{item.title}</span>
                              <span className="block text-sm text-muted-foreground">{item.text}</span>
                            </span>
                            <Icon name="arrow-right" className="h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5 group-hover:text-foreground" />
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </section>

              <aside className="min-w-0 space-y-8">
                <section>
                  <h2 className="border-b border-border pb-3 text-md font-medium text-foreground">Common questions</h2>
                  <Accordion type="single" collapsible>
                    {FAQ.map((f, i) => (
                      <AccordionItem key={i} value={`q${i}`}>
                        <AccordionTrigger className="text-left text-sm font-medium">{f.q}</AccordionTrigger>
                        <AccordionContent className="text-sm text-muted-foreground">{f.a}</AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </section>
                <section>
                  <h2 className="border-b border-border pb-3 text-md font-medium text-foreground">Keyboard shortcuts</h2>
                  <ul className="divide-y divide-border">
                    {SHORTCUTS.map(s => (
                      <li key={s.label} className="flex items-center justify-between gap-4 py-2.5 text-sm">
                        <span className="text-muted-foreground">{s.label}</span>
                        <span className="flex shrink-0 items-center gap-1">{s.keys.map(k => <Kbd key={k}>{k}</Kbd>)}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              </aside>
            </div>
          </div>
        </TabsContent>

        {/* ------------------------------------------------------- support */}
        <TabsContent value="support" className="mt-0">
          <div className="page grid gap-x-12 gap-y-10 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
            <section className="min-w-0">
              <h2 className="text-xl font-medium tracking-tight text-foreground">Something not working?</h2>
              <p className="mt-1 max-w-xl text-sm text-muted-foreground">These three checks solve most issues, and their results help us help you faster.</p>
              <ol className="mt-6 space-y-px overflow-hidden rounded-xl border border-border bg-border">
                {([
                  { n: 1, title: 'Run diagnostics', text: 'A full check of connections, data mappings and agents. Takes about a minute.', to: '/operations/diagnostics', cta: 'Run diagnostics', icon: 'stethoscope' },
                  { n: 2, title: 'Check system health', text: 'See whether a source system, job or service is down right now.', to: '/operations/health', cta: 'Open health', icon: 'heartbeat' },
                  { n: 3, title: 'Ask the assistant', text: 'Describe the problem in your own words. Press Ctrl + J on any screen.', to: '/ai-stack/reasoning', cta: 'Open Copilot', icon: 'chat-bot' },
                ] as const).map(s => (
                  <li key={s.n} className="flex flex-wrap items-center gap-4 bg-card p-5">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-foreground"><Icon name={s.icon} className="h-5 w-5" /></span>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-medium text-foreground"><span className="num text-muted-foreground">{s.n}.</span> {s.title}</h3>
                      <p className="mt-0.5 text-sm text-muted-foreground">{s.text}</p>
                    </div>
                    <Button variant="outline" size="sm" asChild><Link to={s.to}>{s.cta}</Link></Button>
                  </li>
                ))}
              </ol>
            </section>

            <aside className="min-w-0">
              <div className="rounded-xl border border-border bg-card p-6 shadow-xs">
                <Icon name="mail" className="h-5 w-5 text-primary dark:text-brand-hi" />
                <h2 className="mt-3 text-md font-medium text-foreground">Email the support team</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Opens your email app with the page, time and browser already filled in, so you only need to describe the problem.
                </p>
                <Button className="mt-5 w-full" asChild>
                  <a href={mailto(SUPPORT_EMAIL, 'Nexus AI support request', supportBody)}>Email support</a>
                </Button>
                <p className="mt-3 break-all text-center text-xs text-muted-foreground">{SUPPORT_EMAIL}</p>
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Tip: attach the diagnostics report or a screenshot. Never send passwords or API keys by email.
              </p>
            </aside>
          </div>
        </TabsContent>

        {/* ------------------------------------------------------- contact */}
        <TabsContent value="contact" className="mt-0">
          <div className="page grid gap-x-12 gap-y-10 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
            <section className="min-w-0 max-w-2xl">
              <h2 className="text-xl font-medium tracking-tight text-foreground">Talk to us</h2>
              <p className="mt-1 text-sm text-muted-foreground">Questions about the product, a demo, pricing or working together. Write the message here and send it from your own email app.</p>
              <form
                className="mt-6 space-y-5"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!canSend) return;
                  window.location.href = mailto(CONTACT_EMAIL, subject.trim() || topics[topic], message.trim());
                }}
              >
                <div className="grid gap-5 sm:grid-cols-2">
                  <Field label="Topic" htmlFor="help-topic">
                    <Select value={topic} onValueChange={setTopic}>
                      <SelectTrigger id="help-topic"><SelectValue /></SelectTrigger>
                      <SelectContent>{Object.entries(topics).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                    </Select>
                  </Field>
                  <Field label="Subject" htmlFor="help-subject" hint="Optional">
                    <Input id="help-subject" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder={topics[topic]} />
                  </Field>
                </div>
                <Field label="Message" htmlFor="help-message">
                  <Textarea id="help-message" value={message} onChange={(e) => setMessage(e.target.value)} rows={7} placeholder="How can we help?" />
                </Field>
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="submit" disabled={!canSend}><Icon name="send" className="h-3.5 w-3.5" /> Open in email app</Button>
                  <span className="text-xs text-muted-foreground">Nothing is sent until you press send in your email app.</span>
                </div>
              </form>
            </section>

            <aside className="min-w-0">
              <h2 className="border-b border-border pb-3 text-md font-medium text-foreground">Direct addresses</h2>
              <ul className="divide-y divide-border">
                {[
                  { label: 'General and sales', text: 'Demos, pricing and partnerships', email: CONTACT_EMAIL, icon: 'mail' as IconName },
                  { label: 'Technical support', text: 'Problems with a running environment', email: SUPPORT_EMAIL, icon: 'help' as IconName },
                ].map(c => (
                  <li key={c.email} className="flex items-start gap-3 py-4">
                    <Icon name={c.icon} className="mt-0.5 h-[18px] w-[18px] shrink-0 text-muted-foreground" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">{c.label}</p>
                      <p className="text-sm text-muted-foreground">{c.text}</p>
                      <a href={`mailto:${c.email}`} className="mt-1 inline-block break-all text-sm text-primary underline-offset-4 hover:underline dark:text-brand-hi">{c.email}</a>
                    </div>
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        </TabsContent>
      </Tabs>
    </Layout>
  );
}
