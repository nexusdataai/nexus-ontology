---
inclusion: always
---

# Nexus AI UI standards

Follow these when creating or changing any screen in `frontend/`.
Full reference: `frontend/doc/design-system/README.md`. Live examples: the
`/design-system` route in the app.

- Colours come from tokens only (`src/styles/tokens.css`). Use classes such as
  `bg-card`, `bg-surface-2`, `text-foreground`, `text-muted-foreground`,
  `text-subtle-foreground`, `border-border`, `bg-primary`, `text-success`,
  `text-warning`, `text-destructive`. No hex values and no Tailwind palette
  classes (`text-purple-400`, `bg-emerald-500/10`, `dark:bg-[#141b2d]`).
- Blue is the only accent. Green, amber and red are for status only.
- Smallest text is `text-xs` (12px). Never `text-[10px]` or smaller.
- Numbers are written in the text face with the `num` class (tabular figures).
  Geist Mono is only for identifiers and code (`mono-id`).
- Icons: `<Icon name="…">` from `src/components/ds/Icon` only. Do not import
  from `lucide-react` in new code. Add icons with `npm run icons`.
- Prefer hairline-divided lists and whitespace over cards. Never nest cards.
  Write metrics inline ("86 schemas"); no rows of identical stat boxes.
- No uppercase mono labels, no numbered tags, no tinted icon squares on
  every row.
- Every page: `<Layout>` → `<div className="page">` → `<PageHeader>`.
- New navigation entries go in `src/config/navigation.ts` only.
- Use components from `src/components/ui` and `src/components/ds`. Do not build
  one-off buttons, tabs, badges, modals or tables.
- Tabbed pages: `PageTabsBar` + `useUrlTab` (ds/PageTabs); the active tab lives
  in the URL (`?tab=`). Group related tabs into sections. Full-height tools use
  the `h-pane` / `h-pane-sub` classes, never `h-[calc(100vh-…)]`.
- Overlays: `Dialog`, `Sheet`, `await confirmDialog({...})` (ds/confirm),
  `ModalOverlay` + `ModalPanel` (ds/Modal), `toast`. Never `window.confirm`,
  `alert`, or hand-built `fixed inset-0` modals.
- Forms: shadcn `Input`, `Select`, `Checkbox`, `Switch`. No native controls.
- Every list or panel has `Skeleton` loading, `EmptyState` empty and a visible
  error state.
- Icon-only buttons need `aria-label`. Use `<button>` / `<a>`, not clickable
  `<div>`.
- Mobile first: one column by default, add columns at `sm` / `lg`. No fixed
  pixel layout widths.
- Motion: `ease-brand`, `.rise` for entrances, `.flow-line` for diagram
  connectors, `<AnimatedNumber>` for counters.
- Diagrams: `.canvas-dots` background, card nodes, details in a `Sheet`.
- Do not change `src/services/*`, API paths or response shapes as part of a
  visual change.

## Composing a screen (read `frontend/doc/design-system/SCREEN-PATTERNS.md`)

- Pick a recipe before writing: A master–detail (explorers, editors), B
  collection (catalogues, lists), C object page (a run, a journey, a
  connector), D report (diagnostics, audits, test results), E editor (rules,
  policies, builders). Copy the closest existing screen:
  `EntityExplorer.tsx` (A), `DataPipelinesTab.tsx` (B), `SolutionDiagnosticsView.tsx` (D),
  `MappingRulesEditor.tsx` (E).
- Build from `@/components/ds/kit`: `StatusPill` for every status, `MetricStrip`
  for headline numbers, `KeyValues` for facts, `Toolbar` + `SearchInput` +
  `Chips` for filters, `DetailSheet` to inspect one item, `Timeline` for steps,
  `CodeBlock` for JSON and IDs, `Field` for form rows, `InlineError` for failures.
- A source system is always `<SystemLogo system={…} />`, never a coloured dot
  or initials.
- Charts use `@/components/ds/charts` (`ChartTooltip`, `axisProps`, `gridProps`,
  `lineProps`, `barProps`, `seriesColor`). Blue first. Donut with a legend, not
  a labelled pie. Ranked horizontal bars for categories.
- One primary object and one primary button per screen. The first item of a
  list is selected by default; never show "Select an item".
- Do not build: rows of identical stat boxes with tinted icons, coloured top
  strips, gradients, more than one accent colour, cards inside cards, badges
  for things that are not statuses, uppercase micro-labels, raw API keys as
  column headers.
- Write for a business reader: sentence case, plain words, buttons that say
  what happens ("Run checks", "Save rule").
