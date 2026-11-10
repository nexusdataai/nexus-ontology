# Screen patterns

How Nexus AI screens are composed. Read this with `README.md` (tokens and
rules) before building or changing a screen. The building blocks are in
`src/components/ds/kit.tsx`, `ds/charts.tsx`, `ds/SystemLogo.tsx`,
`ds/primitives.tsx`, `ds/Icon.tsx` and `components/ui/*`.

Reference screens that show the intended quality: `pages/HomePage.tsx`,
the Sources tab in `pages/ai-stack/DataPlanePage.tsx`,
`components/AppCatalogue.tsx`, `components/apps/sections/AppOverview.tsx`,
`pages/Settings.tsx` (side menu).

## What "designed" means here

A screen is not finished when it has the right colours. It is finished when
someone opening it for the first time can tell, in order: where they are, what
the main object is, what state it is in, and what they can do next.

1. **One primary object per screen.** Give it a clear header: name, the
   system it belongs to (`SystemLogo`), its state (`StatusPill`), and the one
   primary action. Everything else is secondary.
2. **Text-first.** Numbers are written into sentences or a `MetricStrip`.
   Do not build rows of identical bordered stat boxes with an icon in a tinted
   square. Do not add an icon to every heading.
3. **Hairlines and space, not boxes.** Lists are rows divided by
   `border-border` hairlines. A `Panel` wraps one coherent object. Never put
   a panel or card inside another one.
4. **Colour means something.** Neutral surfaces. Blue for the primary action,
   the current selection and live data. Green / amber / red only for status,
   always through `StatusPill` (dot + word), never as a filled block.
   No gradient strips, no coloured top borders, no per-category hues.
5. **Density with rhythm.** 14px body, 13px controls and table cells, 12px
   meta. Rows 40–44px. 20px panel padding. 40px between page sections.
6. **Progressive disclosure.** Lists show what is needed to choose. Details
   open in a `DetailSheet` (right side) or in the main column of a
   master–detail layout. JSON, IDs, endpoints and file paths are hidden
   behind a "Technical details" disclosure or a `CodeBlock`, not shown inline.
7. **Plain language.** "Tools registry", not "DDB (TOOLREG#)". Sentence case
   everywhere. Buttons say what happens: "Run check", "Save rule".
8. **Motion explains.** `rise` for first paint of a list, a lift on hover for
   clickable cards, `flow-line` where data moves, `AnimatedNumber` for
   headline counts, `Skeleton` while loading. Nothing loops for decoration.

## Layout recipes

### A. Master–detail (explorers, editors, registries with rich items)

```
┌ list (280–320px) ─┬ detail ─────────────────────────────────────┐
│ SearchInput       │ header: SystemLogo · name · StatusPill · CTA │
│ Chips (filter)    │ meta line (text)                              │
│ rows, grouped     │ Tabs variant="line": Overview | … | Data      │
│ (logo, name, meta)│ content of the tab                            │
└───────────────────┴───────────────────────────────────────────────┘
```

- Container: `grid lg:grid-cols-[300px_minmax(0,1fr)]` inside an `h-pane`
  or `h-pane-sub`; each column scrolls on its own (`min-h-0 overflow-y-auto
  scroll-thin`). The list has `border-r border-border bg-sidebar/40`.
- The first item is selected by default: never show a blank detail area with
  "select something".
- Selected row: `bg-accent text-foreground` with the name in medium weight.
- Below `lg`: the list is hidden behind a `Select` (or a "Browse" button
  that opens the list in a `Sheet`); the detail takes the full width.
- No resizable splitters and no bottom preview drawers. Secondary views are
  tabs inside the detail.

### B. Collection (catalogues, lists of pipelines, journeys, dashboards)

- `PageHeader` or section heading, then a `Toolbar`: `SearchInput`, `Chips`
  or `Select` filters, `ToolbarSpacer`, secondary button, primary button.
- Few rich items (≤ 12): cards in `grid gap-4 md:grid-cols-2 xl:grid-cols-3`.
  Card = `rounded-xl border border-border bg-card p-5 shadow-xs` with hover
  `-translate-y-0.5 border-brand/50 shadow-md`. Top: logo/icon tile left,
  status right. Then title, 2-line description, one meta line, footer link.
- Many uniform items: a table in `TableShell` (`ui/table`). First column is
  the name (medium weight) with a muted second line; numbers right-aligned
  with `num`; status as `StatusPill`; row actions on the right, visible on
  hover and focus. Clicking the row opens a `DetailSheet`.
- Always: `Skeleton` rows while loading, `EmptyState` when empty,
  `InlineError` with retry on failure.

### C. Object page (a run, a journey, a dashboard, a connector)

- Back link (`Icon chevron-left` + parent name) above the header.
- Header: title, `StatusPill`, meta as text ("Every 24 h · next run 04:04"),
  actions right (one primary).
- `MetricStrip` for 3–5 headline numbers.
- Body in two columns on `xl`: main (wide) and aside (320–360px) with
  `KeyValues`, recent activity, links.
- Steps and stages use `Timeline`. Logs use `CodeBlock` or a `DetailSheet`.

### D. Report / results (diagnostics, audits, test runs)

- Summary first: one sentence verdict + `MetricStrip` (passed, warnings,
  failed, last run).
- Then sections as `Panel`s with the section verdict as a `StatusPill` in the
  header actions; tables inside are flush (`flush`).
- Only failing or warning rows are expanded by default.

### E. Editor (rules, policies, tools, builders)

- Sticky header inside the editor: object name (inline editable where it was
  before), dirty state ("Unsaved changes" in muted text), secondary actions,
  primary "Save".
- Form in sections with a heading and a one-line hint, `Field` for each
  control, max width ~720px for text forms.
- Mapping-style editors use a table: `source → target → transform`, one row
  per field, with an arrow glyph between, and a live sample-data column or
  side panel.

## Component cheatsheet

| Need | Use |
|---|---|
| Status | `<StatusPill status={row.status} />` (`variant="soft"` only in headers) |
| A source system | `<SystemLogo system="sfdc" tile size="md" />`, `systemName()` |
| Headline numbers | `<MetricStrip items={[…]} />`, optional `spark` |
| Label/value facts | `<KeyValues items={[…]} />` |
| A titled surface | `<Panel title actions flush>` |
| Filters | `<Toolbar>`, `<SearchInput>`, `<Chips>`, `ui/select` |
| Inspect one item | `<DetailSheet>` |
| Large custom dialog | `<ModalOverlay><ModalPanel>` |
| Confirm | `await confirmDialog({ title, description, destructive })` |
| Result of an action | `toast.success(…)` / `toast.error(…)` (sonner) |
| Steps | `<Timeline items={[…]} />` |
| Progress / share | `<Meter value max tone />` |
| JSON / code / IDs | `<CodeBlock>`, `.mono-id` |
| Charts | `ds/charts.tsx`: `ChartTooltip`, `axisProps`, `gridProps`, `lineProps`, `barProps`, `AreaFill`, `seriesColor`, `ChartLegend` |
| Icons | `<Icon name="…" />` (names: see `/design-system`) |
| Empty / loading / error | `EmptyState`, `Skeleton`, `InlineError` |

## Things that make a screen look generated (do not do these)

- A grid of 4–8 identical boxes, each with a big number, a tiny label and a
  coloured icon.
- A coloured strip or gradient on top of every card.
- Three or more accent colours on one screen.
- Badges everywhere; uppercase micro-labels; emoji as icons.
- Everything in a card; cards inside cards; resizable panes for their own
  sake.
- A blank area saying "Select an item" where the first item could be shown.
- Raw keys from the API as column headers (`total_open_ar`): label them
  ("Open receivables").
