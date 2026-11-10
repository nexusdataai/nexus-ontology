# Nexus AI design system

The rules every Nexus AI screen follows. A live version with real components is
in the app at **`/design-system`** (open it from search, Ctrl+K).

The look matches the Nexus AI website: graphite surfaces, one blue accent,
Geist type.

## 0. Design principles

1. **Content before chrome.** Show the user's real objects (journeys,
   entities, sources, runs), not decoration. A screen should still make sense
   with every border removed.
2. **Hierarchy through type and space, not boxes.** Use a card only when a
   group must read as one object. Prefer hairline dividers and whitespace for
   lists and sections. Never put a card inside a card.
3. **Quiet by default, blue on purpose.** Surfaces are neutral. Blue marks the
   one primary action, the current selection, and live data flow.
4. **Numbers are text.** Write metrics inline ("86 schemas") in the text face
   with tabular figures. Reserve big stat tiles for true dashboards.
5. **One signature drawing per area.** Architecture and data-flow visuals are
   drawn as proper diagrams (isometric planes, graphs on a dotted canvas),
   with details beside them, linked by hover.
6. **Motion explains.** Animate to show cause and effect (a plane lifts when
   its row is hovered, a line flows where data moves). No decorative motion.

## 1. Where things live

| What | File |
|---|---|
| Design tokens (colour, type, radius, shadow, motion) | `src/styles/tokens.css` |
| Tailwind mapping of the tokens | `tailwind.config.ts` |
| Global base styles | `src/styles/index.css` |
| Shared CSS classes (`.page`, `.eyebrow`, `.num`, `.canvas-dots`, `.flow-line`, `.rise`, `.shimmer`) | `src/styles/components.css` |
| Keyframes and reduced-motion rule | `src/styles/utils.css` |
| Base components (shadcn/Radix) | `src/components/ui/*` |
| Product primitives (PageHeader, StatTile, IconTile, StatusDot, EmptyState, Kbd, Logo, AnimatedNumber, CommandPalette, MobileNav) | `src/components/ds/*` |
| Icons (one family, from Magnific stock) | `src/components/ds/Icon.tsx`, `src/assets/icons/magnific/*.svg`, `scripts/build-icons.mjs` |
| Platform map drawing | `src/components/home/PlatformStack.tsx` |
| Page bar with grouped, URL-synced tabs | `src/components/ds/PageTabs.tsx` (`PageTabsBar`, `useUrlTab`) |
| Confirmation dialog | `src/components/ds/confirm.tsx` (`confirmDialog`) |
| Large custom modal | `src/components/ds/Modal.tsx` (`ModalOverlay`, `ModalPanel`) |
| Page error boundary | `src/components/ds/PageErrorBoundary.tsx` (mounted in `Layout`) |
| Navigation (sidebar, breadcrumbs, mobile tabs, search) | `src/config/navigation.ts` |
| **Screen kit**: StatusPill, Panel, Toolbar, SearchInput, Chips, MetricStrip, KeyValues, Meter, CodeBlock, DetailSheet, Timeline, Field, InlineError, TableShell | `src/components/ds/kit.tsx` |
| **Chart kit**: palette, axis, grid, tooltip, legend, motion for Recharts | `src/components/ds/charts.tsx` |
| **System logos** (Salesforce, SAP, Oracle, Google Drive, Microsoft …) | `src/components/ds/SystemLogo.tsx`, `src/assets/brands/*.svg` |
| **How to compose a screen** (layout recipes, what to avoid) | `doc/design-system/SCREEN-PATTERNS.md` |
| Assistant (docked chat) | `src/components/assistant/AssistantDock.tsx` |
| Knowledge graph | `src/components/control-plane/KnowledgeGraphView.tsx` |
| App shell | `src/components/Layout.tsx`, `src/components/Sidebar.tsx` |

## 2. Hard rules

1. **No hex colours, no `text-purple-400`-style palette classes in components.**
   Use token classes: `bg-card`, `bg-surface-2`, `text-foreground`,
   `text-muted-foreground`, `text-subtle-foreground`, `border-border`,
   `border-border-strong`, `bg-primary`, `text-success`, `text-warning`,
   `text-destructive`.
2. **Blue is the only accent.** Green, amber and red mean status and nothing
   else. Do not colour-code sections or systems with different hues.
3. **Smallest text is 12px** (`text-xs`). Never `text-[10px]` or smaller.
4. **Geist for everything, including numbers** (add `num` for tabular
   figures). Geist Mono only for identifiers and code (`mono-id`), and for the
   single bracketed brand label (`eyebrow-brand`). No uppercase mono labels.
4a. **Icons come from `<Icon name="…">` only.** The family is UIcons regular
   rounded by Freepik (published on Magnific / Flaticon stock). Do not import
   icons from `lucide-react` in new code and do not mix families. To add one,
   take the SVG of the same family (Magnific stock, or the official
   `@flaticon/flaticon-uicons` package, style `fi-rr-*`), save it as
   `src/assets/icons/magnific/<name>.svg` and run `npm run icons`.
   Licence: Flaticon licence. It needs an active Freepik/Magnific
   subscription or a visible credit to Flaticon.
5. **Every page renders inside `<Layout>` and starts with `<PageHeader>`**
   inside a `<div className="page">`.
6. **One overlay set:** `Dialog` for a short task, `Sheet` for details beside a
   list, `await confirmDialog({...})` to confirm anything destructive,
   `ModalOverlay` + `ModalPanel` for a large custom panel, `toast` (sonner)
   for results. Never `window.confirm`, `alert`, or a hand-built
   `fixed inset-0` modal.
7. **Tabbed pages use `PageTabsBar` with `useUrlTab`.** It renders the page
   title, the section tabs and, for a section with several views, a compact
   row of view tabs. The active tab is read from and written to the URL
   (`?tab=`). Group related tabs into a section instead of adding a seventh
   top-level tab. Inside a page, `ui/tabs` (`variant="line"` or the default
   segment) switches a view in place.
7a. **Full-height tools** (explorers, editors, canvases) sit in `h-pane`
   (under a page bar) or `h-pane-sub` (under a page bar with a view row).
   Do not write `h-[calc(100vh-…)]`.
8. **Forms use the shadcn controls** (`Input`, `Select`, `Checkbox`, `Switch`,
   `Textarea`). No native `<select>` or checkbox. Labels sit above fields.
9. **Every list or panel has loading (`Skeleton`), empty (`EmptyState`) and
   error states.** Do not swallow errors silently.
10. **Icon-only buttons need `aria-label`.** Clickable things are `<button>` or
    `<a>`, not `<div onClick>`.
11. **Mobile first.** Grids start at one column and add columns at `sm` / `lg`.
    No fixed pixel widths for layout. Wide tables scroll inside their own
    container.
12. **Do not change `src/services/*` or API shapes for a visual change.**

## 3. Colour tokens

Light theme is `:root`, graphite theme is `.dark` (default). Values are HSL
triplets so opacity modifiers work: `bg-primary/10`, `border-success/25`.

| Token class | Use |
|---|---|
| `bg-background` | Page |
| `bg-card` | Cards, tables, panels |
| `bg-surface-2` | Inset fills, table header, stat tiles |
| `bg-surface-3` / `bg-accent` | Hover and pressed |
| `bg-popover` | Menus, dialogs, sheets |
| `bg-sidebar` | Navigation rail |
| `text-foreground` | Primary text |
| `text-muted-foreground` | Secondary text |
| `text-subtle-foreground` | Meta text and idle icons |
| `border-border` / `border-border-strong` | Hairlines / control outlines |
| `bg-primary` + `text-primary-foreground` | Main action |
| `text-primary dark:text-brand-hi` | Blue text and icons that must read on both themes |
| `bg-brand`, `brand-hi`, `brand-lo` | Exact brand blues (#3d73ff, #86a8ff, #2756d6) for diagrams and glows |
| `success`, `warning`, `destructive`, `info` | Status. Soft style: `border-success/25 bg-success/10 text-success` |
| `bg-chart-1` … `bg-chart-6`, `hsl(var(--chart-1))` | Chart series, in this order |

## 4. Type scale

| Class | Size | Use |
|---|---|---|
| `text-3xl font-medium` | 30 | Page title (desktop) |
| `text-2xl font-medium` | 24 | Page title (phone) |
| `text-xl font-medium` | 20 | Dialog title |
| `text-md font-medium` | 15 | Card and section title |
| `text-base` | 14 | Body |
| `text-sm` | 13 | Controls, descriptions, table cells |
| `text-xs` | 12 | Labels, meta. Smallest allowed. |
| `.eyebrow` | 12 medium, muted | Quiet group label (sidebar groups, list headings) |
| `.eyebrow-brand` | 12 mono, blue, `{ label }` | Brand label, at most once per page |

Headings use weight 500 with slight negative tracking (built into the scale).

## 5. Shape, elevation, spacing

- Radius: `rounded-sm` 4, `rounded-md` 6 (controls), `rounded-lg` 8 (tiles),
  `rounded-xl` 12 (cards, dialogs).
- Shadows: `shadow-xs` (cards), `shadow-sm`, `shadow-md` (menus, hover lift),
  `shadow-lg` (dialogs). In the graphite theme borders do most of the work.
- Controls are 36px high (`h-9`); small 32px (`h-8`); large 40px.
- Card padding 20px (`p-5`), 16px on phones (`p-4`). Gaps: 10px between tiles,
  16–20px between cards, 40px between page sections.

## 6. Motion

- Easing: `ease-brand` and `ease-brand-out`. Durations: 120 / 200 / 420 ms.
- Entrance: add `.rise` and set `style={{ '--i': index }}` to stagger.
- Hover: lift by 1px and brighten the border to `border-brand/40`.
- Data flow in diagrams: SVG line with class `flow-line`.
- Numbers: `<AnimatedNumber value={n} />`.
- Loading: `<Skeleton />`.
- Bars that fill: class `grow-x` (stagger with `--i`).
- Chat: `animate-fade-up` for new messages, keyframe `typing-dot` for the
  waiting dots.
- All motion is switched off automatically under `prefers-reduced-motion`.

## 7. Diagrams, graphs and canvases

The reference is `KnowledgeGraphView.tsx`.

- Canvas: dot grid drawn from `--border-strong`, pan and zoom on the canvas.
- Nodes: pills (`rounded-full border bg-card`) with the `SystemLogo`, the
  name, and one small number. Dashed border = not mapped yet. Selected =
  `border-brand` + ring. Nodes are real buttons (keyboard and screen reader).
- Links: 1px `--border-strong`, neutral. A link lights up in `--brand-hi`
  with a `flow-line` on top only when its node is hovered, selected or on a
  traced path; everything else dims. Never colour links by type: label them.
- Groups: a soft territory (dashed outline, 2% fill) with the system logo and
  name above it, or a lane. No coloured clusters.
- Controls float on the canvas in small popover-coloured bars: search and
  layout switch top-left, system filters bottom-left, zoom on the right.
- Details open in an inspector column on the right (a `DetailSheet` on
  phones), never in a floating box over the canvas.
- Charts: use `ds/charts.tsx`. One hue first; a donut with its legend beside
  it instead of a labelled pie; ranked horizontal bars for categories; the
  shared `ChartTooltip`.

## 8. Page recipe

A tabbed page:

```tsx
const SECTIONS: TabSection[] = [
  { label: 'Sources', icon: 'database', items: [{ value: 'sources', label: 'Data sources' }] },
  { label: 'Connectors', icon: 'plug', items: [
    { value: 'connectors', label: 'Catalogue' },
    { value: 'connector-registry', label: 'API registry' },
  ] },
];

export default function ExampleTabbedPage() {
  const [tab, setTab] = useUrlTab('sources');
  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab}>
        <PageTabsBar title="Data Plane" description="…" sections={SECTIONS} value={tab} onChange={setTab} />
        <TabsContent value="sources" className="mt-0"><div className="page">…</div></TabsContent>
        <TabsContent value="connector-registry" className="mt-0 h-pane-sub">…</TabsContent>
      </Tabs>
    </Layout>
  );
}
```

A simple page:

```tsx
import Layout from '@/components/Layout';
import { PageHeader } from '@/components/ds/primitives';

export default function ExamplePage() {
  return (
    <Layout>
      <div className="page">
        <PageHeader
          eyebrow="AI Stack"
          title="Example"
          description="One sentence saying what the user does here."
          actions={<Button>New item</Button>}
        />
        <div className="mt-6">{/* content */}</div>
      </div>
    </Layout>
  );
}
```

To add the page to the sidebar, breadcrumbs, mobile tabs and search, add one
entry to `src/config/navigation.ts`.

## 9. Working without a backend

Copy `.env.sample-data.example` to `.env.local`. The Vite dev server then
answers API calls from `dev/sample-data/routes.ts`. This runs in development
only and is never part of a build. Remove `VITE_SAMPLE_DATA` to use the real
backend.
