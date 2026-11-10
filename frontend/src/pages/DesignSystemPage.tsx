/**
 * Design system reference (route: /design-system).
 * A living page: it renders the real tokens and components, so it can never
 * drift from the product. Use it to pick the right pattern before building.
 * Written guidance lives in doc/design-system/README.md.
 */
import { useState } from 'react';
import { Icon } from '@/components/ds/Icon';
import { ICONS } from '@/components/ds/icons.generated';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { PageHeader, SectionHeader, IconTile, StatusDot, Kbd, StatTile, EmptyState } from '@/components/ds/primitives';
import { AnimatedNumber } from '@/components/ds/AnimatedNumber';
import { Logo } from '@/components/ds/Logo';

const SURFACES = [
  { name: 'background', cls: 'bg-background', use: 'Page' },
  { name: 'card', cls: 'bg-card', use: 'Raised surface' },
  { name: 'surface-2', cls: 'bg-surface-2', use: 'Inset fill' },
  { name: 'surface-3', cls: 'bg-surface-3', use: 'Hover / pressed' },
  { name: 'popover', cls: 'bg-popover', use: 'Menus, dialogs' },
  { name: 'sidebar', cls: 'bg-sidebar', use: 'Navigation rail' },
];
const BRAND = [
  { name: 'primary', cls: 'bg-primary', use: 'Main action' },
  { name: 'brand', cls: 'bg-brand', use: 'Brand blue #3d73ff' },
  { name: 'brand-hi', cls: 'bg-brand-hi', use: 'Accent text on dark' },
  { name: 'brand-lo', cls: 'bg-brand-lo', use: 'Pressed / deep' },
];
const STATUS = [
  { name: 'success', cls: 'bg-success', use: 'Passed, healthy' },
  { name: 'warning', cls: 'bg-warning', use: 'Needs attention' },
  { name: 'destructive', cls: 'bg-destructive', use: 'Failed, delete' },
  { name: 'info', cls: 'bg-info', use: 'Neutral notice' },
];
const CHART = ['bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5', 'bg-chart-6'];

const TYPE = [
  { cls: 'text-4xl font-medium', label: 'text-4xl · 38', sample: 'Display' },
  { cls: 'text-3xl font-medium', label: 'text-3xl · 30', sample: 'Page title' },
  { cls: 'text-2xl font-medium', label: 'text-2xl · 24', sample: 'Page title (phone)' },
  { cls: 'text-xl font-medium', label: 'text-xl · 20', sample: 'Dialog title' },
  { cls: 'text-md font-medium', label: 'text-md · 15', sample: 'Card and section title' },
  { cls: 'text-base', label: 'text-base · 14', sample: 'Body text' },
  { cls: 'text-sm text-muted-foreground', label: 'text-sm · 13', sample: 'Controls, descriptions, table cells' },
  { cls: 'text-xs text-muted-foreground', label: 'text-xs · 12', sample: 'Labels and meta. Smallest size allowed.' },
];

function Swatch({ name, cls, use }: { name: string; cls: string; use: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <div className={`h-14 ${cls}`} />
      <div className="px-3 py-2">
        <div className="font-mono text-xs text-foreground">{name}</div>
        <div className="text-xs text-muted-foreground">{use}</div>
      </div>
    </div>
  );
}

function Block({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <SectionHeader title={title} description={description} />
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default function DesignSystemPage() {
  const [n, setN] = useState(5630);

  return (
    <Layout title="Design system">
      <div className="page max-w-[1200px]">
        <PageHeader
          eyebrow="Reference"
          title="Design system"
          description="The tokens and components every Nexus AI screen is built from. If a pattern is not on this page, add it here first, then use it."
        />

        <Block title="Brand" description="Use the Logo component. Do not redraw or recolour the mark.">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex h-24 items-center justify-center rounded-xl border border-border bg-sidebar"><Logo /></div>
            <div className="flex h-24 items-center justify-center rounded-xl border border-border bg-sidebar"><Logo markOnly markClassName="h-9 w-9" /></div>
          </div>
        </Block>

        <Block title="Colour" description="Graphite surfaces, one blue accent. Green, amber and red are for status only. Never write a hex value in a component.">
          <div className="eyebrow mb-2">Surfaces</div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">{SURFACES.map(s => <Swatch key={s.name} {...s} />)}</div>
          <div className="eyebrow mb-2 mt-6">Brand</div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{BRAND.map(s => <Swatch key={s.name} {...s} />)}</div>
          <div className="eyebrow mb-2 mt-6">Status</div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{STATUS.map(s => <Swatch key={s.name} {...s} />)}</div>
          <div className="eyebrow mb-2 mt-6">Charts (use in this order)</div>
          <div className="flex h-10 overflow-hidden rounded-lg border border-border">
            {CHART.map(c => <div key={c} className={`flex-1 ${c}`} title={c} />)}
          </div>
        </Block>

        <Block title="Typography" description="Geist for everything. Numbers use tabular figures (.num). Geist Mono only for identifiers and code (.mono-id).">
          <div className="divide-y divide-border rounded-xl border border-border bg-card">
            {TYPE.map(t => (
              <div key={t.label} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6">
                <span className="w-36 shrink-0 font-mono text-xs text-subtle-foreground">{t.label}</span>
                <span className={t.cls}>{t.sample}</span>
              </div>
            ))}
            <div className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6">
              <span className="w-36 shrink-0 font-mono text-xs text-subtle-foreground">.eyebrow</span>
              <span className="eyebrow">Group label</span>
            </div>
            <div className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6">
              <span className="w-36 shrink-0 font-mono text-xs text-subtle-foreground">.eyebrow-brand</span>
              <span className="eyebrow-brand">Platform map</span>
            </div>
            <div className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6">
              <span className="w-36 shrink-0 font-mono text-xs text-subtle-foreground">.num</span>
              <span className="num text-xl">1,287 · 95.3%</span>
            </div>
            <div className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6">
              <span className="w-36 shrink-0 font-mono text-xs text-subtle-foreground">.mono-id</span>
              <span className="mono-id">jr-o2c-01</span>
            </div>
          </div>
        </Block>

        <Block title="Icons" description="One family: UIcons regular rounded, by Freepik (the Magnific stock family). Use through the Icon component. 16px next to text, 18px in toolbars, 20px in mobile tabs. Icons take the text colour.">
          {Object.keys(ICONS).length === 0 ? (
            <p className="text-sm text-muted-foreground">Run <code className="rounded bg-surface-2 px-1.5 py-0.5">npm run icons</code> to compile the icon set.</p>
          ) : (
            <div className="grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-5 lg:grid-cols-8">
              {Object.keys(ICONS).sort().map(name => (
                <div key={name} className="flex flex-col items-center gap-2 bg-card px-2 py-4 text-muted-foreground transition-colors hover:text-foreground">
                  <Icon name={name} className="h-5 w-5" />
                  <span className="mono-id max-w-full truncate">{name}</span>
                </div>
              ))}
            </div>
          )}
        </Block>

        <Block title="Buttons" description="One primary action per view. Outline for secondary, ghost for toolbars, destructive only for irreversible actions.">
          <div className="flex flex-wrap items-center gap-2.5">
            <Button><Icon name="plus" />New journey</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive"><Icon name="trash" />Delete</Button>
            <Button variant="link">Link</Button>
            <Button disabled>Disabled</Button>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2.5">
            <Button size="sm">Small</Button>
            <Button>Default</Button>
            <Button size="lg">Large</Button>
            <Button size="icon" variant="outline" aria-label="Search"><Icon name="search" /></Button>
            <Button size="icon-sm" variant="ghost" aria-label="Search"><Icon name="search" /></Button>
          </div>
        </Block>

        <Block title="Status" description="Badges for state, dots for live signals. Always pair colour with a word.">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="success"><StatusDot tone="success" />Completed</Badge>
            <Badge variant="info"><StatusDot tone="brand" live />Running</Badge>
            <Badge variant="warning"><StatusDot tone="warning" />Warning</Badge>
            <Badge variant="danger"><StatusDot tone="danger" />Failed</Badge>
            <Badge variant="neutral">Draft</Badge>
            <Badge variant="outline">Outline</Badge>
            <Badge>Primary</Badge>
          </div>
        </Block>

        <Block title="Tabs" description='Line tabs for the sections of a page. Segment tabs to switch a view in place. Keep the active tab in the URL (?tab=).'>
          <div className="grid gap-6 lg:grid-cols-2">
            <Tabs defaultValue="a">
              <TabsList variant="line">
                <TabsTrigger value="a"><Icon name="database" />Sources</TabsTrigger>
                <TabsTrigger value="b">Virtual data</TabsTrigger>
                <TabsTrigger value="c">Mapping rules</TabsTrigger>
              </TabsList>
              <TabsContent value="a" className="text-sm text-muted-foreground">Line variant: page sections.</TabsContent>
              <TabsContent value="b" className="text-sm text-muted-foreground">Virtual data.</TabsContent>
              <TabsContent value="c" className="text-sm text-muted-foreground">Mapping rules.</TabsContent>
            </Tabs>
            <Tabs defaultValue="a">
              <TabsList>
                <TabsTrigger value="a">Table</TabsTrigger>
                <TabsTrigger value="b">JSON</TabsTrigger>
                <TabsTrigger value="c">Graph</TabsTrigger>
              </TabsList>
              <TabsContent value="a" className="text-sm text-muted-foreground">Segment variant: view switch.</TabsContent>
              <TabsContent value="b" className="text-sm text-muted-foreground">JSON.</TabsContent>
              <TabsContent value="c" className="text-sm text-muted-foreground">Graph.</TabsContent>
            </Tabs>
          </div>
        </Block>

        <Block title="Forms" description="Labels above fields. 36px controls. Use the shadcn Select, Checkbox and Switch, never native ones.">
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted-foreground">Name</span>
              <Input placeholder="Order-to-Cash daily run" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted-foreground">Type</span>
              <Select defaultValue="fdw">
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="fdw">FDW</SelectItem>
                  <SelectItem value="etl">ETL</SelectItem>
                  <SelectItem value="cdc">CDC</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <div className="flex items-end gap-3 pb-1.5">
              <Switch id="ds-switch" defaultChecked />
              <label htmlFor="ds-switch" className="text-sm">Enabled</label>
            </div>
          </div>
        </Block>

        <Block title="Cards and numbers" description="Cards group one idea. StatTile for a number with a label; it becomes a button when it links somewhere.">
          <div className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <IconTile icon="bolt" tone="brand" />
                  <div>
                    <CardTitle>Card title</CardTitle>
                    <CardDescription>One line of context</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">Card body. Padding is 20px. Radius is 12px.</CardContent>
            </Card>
            <div className="grid grid-cols-2 gap-2.5 lg:col-span-2 lg:grid-cols-4">
              <StatTile label="Embeddings" value={<AnimatedNumber value={n} />} onClick={() => setN(v => v + 417)} hint="Click to count up" />
              <StatTile label="Graph nodes" value={<AnimatedNumber value={412} />} />
              <StatTile label="Success rate" value={<span className="num">95.3%</span>} />
              <StatTile label="Not loaded" value={<AnimatedNumber value={null} />} />
            </div>
          </div>
        </Block>

        <Block title="Tables" description="Header row is quiet, rows are 44px, numbers are right-aligned in mono. On phones, wrap the table so it scrolls sideways.">
          <div className="overflow-hidden rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Journey</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Jobs</TableHead>
                  <TableHead className="text-right">Success</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">Order-to-Cash daily run</TableCell>
                  <TableCell><Badge variant="success">Completed</Badge></TableCell>
                  <TableCell className="num text-right">64</TableCell>
                  <TableCell className="num text-right">95.3%</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Demand forecast refresh</TableCell>
                  <TableCell><Badge variant="info"><StatusDot tone="brand" live />Running</Badge></TableCell>
                  <TableCell className="num text-right">28</TableCell>
                  <TableCell className="num text-right">96.2%</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Procurement spend scan</TableCell>
                  <TableCell><Badge variant="danger">Failed</Badge></TableCell>
                  <TableCell className="num text-right">12</TableCell>
                  <TableCell className="num text-right">75.0%</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </Block>

        <Block title="Overlays and feedback" description="Dialog for a short task, Sheet for details beside the page, AlertDialog to confirm a destructive action, toast for results. Never use window.confirm or alert.">
          <div className="flex flex-wrap gap-2.5">
            <Dialog>
              <DialogTrigger asChild><Button variant="outline">Dialog</Button></DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>New journey</DialogTitle>
                  <DialogDescription>A short, focused task with one primary action.</DialogDescription>
                </DialogHeader>
                <Input placeholder="Journey name" />
                <DialogFooter><Button>Create</Button></DialogFooter>
              </DialogContent>
            </Dialog>
            <Sheet>
              <SheetTrigger asChild><Button variant="outline">Sheet</Button></SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle>Details</SheetTitle>
                  <SheetDescription>Use for inspecting an item without leaving the list.</SheetDescription>
                </SheetHeader>
              </SheetContent>
            </Sheet>
            <AlertDialog>
              <AlertDialogTrigger asChild><Button variant="outline">Confirm delete</Button></AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete this journey?</AlertDialogTitle>
                  <AlertDialogDescription>This cannot be undone.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction>Delete</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <Button variant="outline" onClick={() => toast.success('Journey saved')}>Toast</Button>
          </div>
        </Block>

        <Block title="States" description="Every list and panel needs a loading, an empty and an error state.">
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2.5 rounded-xl border border-border bg-card p-5">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-24 w-full" />
            </div>
            <EmptyState
              icon="folder"
              title="No journeys yet"
              description="Create your first journey to automate a business process."
              action={<Button><Icon name="plus" />New journey</Button>}
            />
          </div>
        </Block>

        <Block title="Canvas and motion" description="Diagrams sit on a dotted canvas with card nodes and animated connectors. Motion is short and eased; it is disabled automatically for users who prefer reduced motion.">
          <div className="canvas-dots relative flex h-56 items-center justify-center gap-0 overflow-hidden rounded-xl border border-border">
            <div className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2.5 shadow-sm">
              <IconTile icon="database" size="sm" />
              <div><div className="text-sm font-medium">Source</div><div className="text-xs text-muted-foreground">Salesforce</div></div>
            </div>
            <svg width="96" height="12" className="overflow-visible" aria-hidden="true">
              <line x1="0" y1="6" x2="96" y2="6" stroke="hsl(var(--border-strong))" />
              <line x1="0" y1="6" x2="96" y2="6" stroke="hsl(var(--brand))" strokeWidth="1.5" className="flow-line" />
            </svg>
            <div className="glow-brand flex items-center gap-3 rounded-lg border border-brand/40 bg-card px-3 py-2.5">
              <IconTile icon="cube" size="sm" tone="brand" />
              <div><div className="text-sm font-medium">Entity</div><div className="text-xs text-muted-foreground">Customer</div></div>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Shortcuts use</span><Kbd>Ctrl</Kbd><Kbd>K</Kbd>
            <span className="ml-3">Classes:</span>
            <code className="rounded bg-surface-2 px-1.5 py-0.5">.rise</code>
            <code className="rounded bg-surface-2 px-1.5 py-0.5">.flow-line</code>
            <code className="rounded bg-surface-2 px-1.5 py-0.5">.shimmer</code>
            <code className="rounded bg-surface-2 px-1.5 py-0.5">.canvas-dots</code>
            <code className="rounded bg-surface-2 px-1.5 py-0.5">.glow-brand</code>
          </div>
        </Block>
      </div>
    </Layout>
  );
}
