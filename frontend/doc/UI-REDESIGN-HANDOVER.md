# UI redesign handover

Branch: `ui-redesign` in `akbar-ai-labs/nexus-ontology-UI`
(copy of `nexusdataai/nexus-ontology` at commit `ba8b315`).

This is a visual redesign of the existing front end. The backend connection is
unchanged: screens call the same endpoints through the same service files, so
there is nothing to reconnect.

Design rules and components: `frontend/doc/design-system/README.md`, live at
`/design-system` in the app. Cursor and Kiro read the short version
automatically (`.cursor/rules/nexus-ui.mdc`,
`frontend/.kiro/steering/ui-design-system.md`).

## Design preview link (no backend)

https://ho9jjp-8ibpkf-h2ypod-w3a69a-45cwag.vercel.app

A static build of this branch on Vercel that runs on the sample data, so the
whole design can be clicked through in a browser. No sign-in. Nothing is
saved; a reload resets it. Not indexed by search engines.

- Built with `VITE_DEMO=true` and `VITE_BYPASS_AUTH=true`. In demo mode
  `src/demo/installDemo.ts` answers the app's API calls in the browser from
  `frontend/dev/sample-data`. A normal build does not include that file or
  the sample data, and `src/services` is unchanged.
- Redeploy from `frontend/`: `npx vercel deploy --prod --build-env VITE_DEMO=true --build-env VITE_BYPASS_AUTH=true`
- Usage, cost and data protection show sample figures there, as they do in
  the product today.

## What was not touched

- `backend/` (nothing).
- `frontend/src/services/*` (no changes to endpoints, payloads or auth).
- Login flow, role checks, route paths. Every existing URL still works.

## How to take it

```bash
git remote add ui https://github.com/akbar-ai-labs/nexus-ontology-UI.git
git fetch ui ui-redesign
git merge ui/ui-redesign        # or cherry-pick area by area
cd frontend && npm install      # two new packages: Geist fonts
```

New dependencies: `@fontsource-variable/geist`,
`@fontsource-variable/geist-mono` (self-hosted fonts, no external requests).

If `vite` fails on Windows with "Failed to load native binding" from
`@swc/core`, install the version the lockfile expects
(`npm install --no-save @swc/core@1.7.26`). This is an environment issue and
not related to the redesign.

## Status by area

The first pass (commit `5abc9dd`) rebuilt the shell and restyled every screen.
The second pass (10 Nov) redesigned the inside of the screens: new layout and
hierarchy, same data and behaviour. Layout recipes for new screens are in
`frontend/doc/design-system/SCREEN-PATTERNS.md`.

| Area | Status | What changed in the second pass |
|---|---|---|
| Design tokens, fonts, logo | Done | Chart palette retuned to one hue family (blue, light blue, slate, then teal / amber / violet only for 4+ categories). |
| Design kit | Done | `components/ds/kit.tsx` (StatusPill, Panel, Toolbar, SearchInput, Chips, MetricStrip, KeyValues, Meter, CodeBlock, DetailSheet, Timeline, Field, InlineError, TableShell), `ds/charts.tsx` (one tooltip, axis, grid and motion for every chart), `ds/SystemLogo.tsx` (real logos for Salesforce, SAP, Oracle, Google Drive, Microsoft). |
| Icons and logos | Done | 97 icons, one family (UIcons regular rounded by Freepik) through `<Icon>`; brand logos in `src/assets/brands`. Licence: covered by the Freepik/Magnific subscription (confirmed 10 Nov 2026); brand logos are trademarks used only to name the integration. Some untouched inner files still import Lucide. |
| App shell | Done | Help and Enterprise Simulator are now real pages in the sidebar. |
| Nexus assistant | Done, working | `components/assistant/AssistantDock.tsx`, mounted once in `App.tsx`. Launcher docked bottom-right; chat panel (bottom sheet on phones); talks to `POST /api/v1/control-plane/agent/stream`; shows live agent status, tools used, typed-out answer; page-aware suggestions; Ctrl+J. The old disabled `Chatbot.tsx` is no longer mounted. |
| Home | Unchanged (approved) | |
| Login | Unchanged | |
| Data Plane | Done | Sources unchanged (approved). Entities: master–detail explorer with Fields / Relationships / Data layer / Sample data. Mapping rules: grouped list + editor with field-mapping table and preview; audit in a modal. Pipelines: rows with one-hue stage progress, expandable runs. Connectors: catalogue with real logos; connector page with API accordion. API workbench: catalogue first, health checks in a second tab. API registries: shared table, filters and drawers restyled. |
| Control Plane | Done | Pipeline: object page with stages and counts. Index: verdict, content types, build action, document browser. Policies / Workflows / Integrations: one master–detail pattern; policies read as rules, workflows as a step timeline, integrations as source → target; form builders now open with the file's real content. **Graph**: rebuilt (see below). |
| Reasoning | Done | Copilot as a chat workspace with live agent trace; Playground (retrieval bundle, graph view, test suite); tool catalogue, registry and builder. |
| Solutions | Done | Catalogue: goal search hero, featured solution, cover art per solution (`components/apps/SolutionCover.tsx`). Inside a solution: Business Insights (live KPIs against target, what needs attention, how it works), Process Analytics (KPI strip, donut, ranked bars, tables, alerts), Workflow Actions (breakdown + log + detail sheet), Reports and alerts. |
| AI Analytics | Done | Dashboards and views as a library with thumbnails (`components/analytics/LibraryCard.tsx`), tag filters; solution mapping as one list with drag-to-order. All dashboard panels on the chart kit (`lib/dashboard/panels/*`): donut with legend, ranked bars, KPI with target marker, readable tooltip in both themes, Markdown notes. |
| AI Automation | Done | Journey Studio as an object page (header, last-run numbers, one numbered step pipeline with the selected step's detail and console, results, recent runs, schedules). Journey list as rows with stage progress. Copilot as a chat with the plan as numbered steps and approval in place. Builder with step palette, canvas and inspector. Registry as a table with a detail sheet. The nine create dialogs share one shell. |
| AI Ops: Diagnostics | Done | One shared report for the eight solution checks (`components/diagnostics/SolutionDiagnosticsView.tsx`): what will run, verdict, four headline numbers, five numbered steps that open when they fail. Platform checks on the same styling. |
| AI Ops: Health | Done | Monitoring as a status page (verdict, history of the last 48 checks, issues, per-area numbers). Scheduled jobs table. Audit log with detail sheet. Usage, cost and data protection clearly marked as sample figures. Test reports. |
| Settings | Done | Profile, password, two-step sign-in, theme with previews. System (group list + parameter rows, save bar only when changed), Secrets (table + edit sheet), Roles and permissions (one matrix, roles, history), Users and invitations, License (statement, renew / deactivate, features, history), log level. |
| Help | New | `/help`: documentation (start here, guides by area, FAQ, shortcuts), support (three self-checks, email with context), contact (message form that opens the user's email app). |
| Enterprise Simulator | New page | `/simulator` checks whether the simulator answers before offering to open it, so there is no more blank tab. |

### The knowledge graph

`components/control-plane/KnowledgeGraphView.tsx` was rebuilt on the same
endpoints (`/api/v1/control-plane/entities/graph`, `/entities/{id}`, mapping
rules, preview):

- **Constellation**: entities sit inside the territory of the system that owns
  them, so cross-system links stand out.
- **Lanes**: one column per system, read left to right.
- **Lineage**: one entity in the middle, what feeds it on the left, what it
  feeds on the right.
- Hover or select an entity to light up its links; the dashes flow in the
  direction of the relationship and the relation is labelled.
- **Trace a path** between two entities (shortest path, shown as a chain).
- Filter by system (logo chips), show only cross-system links, search, drag
  nodes, zoom, fit, minimap.
- Inspector on the right (a sheet on phones): links, governance (policies,
  workflows, integrations), fields, data layer, live sample rows.

Layout is computed once per view with d3-force and tweened; rendering is plain
React (SVG for links and territories, HTML buttons for nodes, so every node is
keyboard reachable).

## Shared patterns introduced

| Pattern | File | Replaces |
|---|---|---|
| Page bar with grouped, URL-synced tabs | `components/ds/PageTabs.tsx` | Seven different hand-built tab strips |
| Full-height panes | `.h-pane`, `.h-pane-sub`, `.pane-wide` in `styles/components.css` | `h-[calc(100vh-…)]` |
| Confirmation | `components/ds/confirm.tsx` (`await confirmDialog({...})`) | 13 `window.confirm` calls |
| Large custom modal | `components/ds/Modal.tsx` | Six hand-built `fixed inset-0` overlays |
| Page error boundary | `components/ds/PageErrorBoundary.tsx` | A failing screen used to blank the whole app |
| Navigation config | `config/navigation.ts` | Menu defined separately in sidebar and layout |
| Screen kit | `components/ds/kit.tsx` | Per-screen status badges, stat boxes, search fields, side drawers |
| Chart kit | `components/ds/charts.tsx` | Per-chart colours, axes and tooltips |
| System logos | `components/ds/SystemLogo.tsx` | Coloured dots and initials for systems |
| Solution dashboard widgets frame | `components/apps/widgets/WidgetFrame.tsx` | Card + spinner in every widget |
| Diagnostics report | `components/diagnostics/SolutionDiagnosticsView.tsx` | Eight copies of the same 300-line panel |

## Screen map

All endpoints are unchanged. "Files changed" lists the files with structural
changes; the colour and type sweep touched about 210 more files with
class-name changes only.

| Screen | Files changed | Endpoints used |
|---|---|---|
| App shell | `components/Layout.tsx`, `Sidebar.tsx`, `UserMenu.tsx`, `components/ds/*`, `config/navigation.ts` | `GET /api/v1/config/simulator` |
| Home | `pages/HomePage.tsx`, `components/home/PlatformStack.tsx` | `GET /api/v1/control-plane/stats`, `GET /api/v1/journeys/` (also lists the five most recent journeys from the same response: `id`, `name`, `type`, `status`, `updated_at`) |
| Login | `pages/Login.tsx`, `components/auth/EnterpriseLoginForm.tsx` | unchanged auth calls |
| Data Plane | `pages/ai-stack/DataPlanePage.tsx`, `components/ConnectorsTab.tsx`, `components/registry-browser/StatsTiles.tsx` | `/api/data-planes`, `/api/v1/data-source-mode`, `/api/fdw/tables`, journeys with `component_type=data-pipeline` |
| Control Plane | `pages/ai-stack/ControlPlanePage.tsx`, `components/control-plane/KnowledgeGraphView.tsx` | `/api/v1/control-plane/stats`, `/api/v1/knowledge-pipelines`, `/api/v1/control-plane/entities/graph` |
| Reasoning | `pages/ai-stack/ReasoningPage.tsx` | `/api/v1/control-plane/agent/stream`, `/api/v1/control-plane/tools` |
| Solutions | `components/AppCatalogue.tsx`, `components/apps/AppShell.tsx`, `AppSidebar.tsx`, `sections/AppOverview.tsx` | `/api/v1/solution-catalog`, `/api/v1/solutions/by-app/{id}` |
| AI Analytics | `pages/AIAnalyticsPage.tsx`, `lib/dashboard/components/DashboardGrid.tsx`, `pages/dashboard/DashboardViewerPage.tsx` | `/api/v1/dashboards`, `/api/v1/views`, `/api/v1/solutions` |
| AI Automation | `pages/workspace/AIAutomationPage.tsx`, `components/journeys/JourneyListView.tsx`, `JourneyCard.tsx`, `JourneysPanel.tsx` | `/api/v1/journeys/` and children |
| Diagnostics | `pages/DiagnosticsPage.tsx` | `/api/v1/diagnostics/*` |
| Health | `pages/Operations.tsx` | `/api/v1/ai-health/*`, `/api/v1/schedules/`, `/api/v1/diagnostics/history`, `/api/v1/tests/*` |
| Settings | `pages/Settings.tsx`, `components/settings/RBACManager.tsx`, `pages/UserManagement.tsx` | `/api/v1/users/*`, `/api/v1/rbac/*`, `/api/v1/license/*`, `/api/v1/config/*` |

## Behaviour changes to be aware of

- **Tabs are in the URL.** `?tab=` is now written as well as read on every
  tabbed page, including Settings (`/settings?tab=system` now opens System,
  which the Data Plane "source mode" link relies on) and Diagnostics.
- **Solution apps keep their section in the URL** (`/apps/{id}?section=analytics`).
  The overview shortcuts now open the matching section (they pointed at ids
  that did not exist before).
- **Top bar.** A search field opens a working palette (Ctrl+K). The Bell and
  Refresh buttons were removed because they had no function.
- **Assistant.** The assistant is a docked launcher at the bottom-right of
  every signed-in page (Ctrl+J). It is live: it calls the same agent stream
  endpoint as the Copilot. It is mounted in `App.tsx`, not in `Layout`.
- **Help and Enterprise Simulator** are pages (`/help`, `/simulator`). The
  sidebar no longer links straight to the simulator address.
- **Solution dashboards ignore per-widget colours** from
  `config/dashboardWidgets.ts` (`config.color`, `config.colors`) and use the
  chart palette. Bar widgets rank categories horizontally; pie widgets are
  donuts that fold categories beyond five into "Other".
- **Diagnostics**: the eight solution panels keep their own state and
  endpoint and render one shared view. Sections open only when they fail.
- **Delete now asks first** for dashboards, views, schedules, policy /
  workflow / integration files (it did not before).
- **Control Plane form builders** load the file's real content before
  editing (they used to regenerate from the header only, which dropped steps,
  mappings and policy sections on save). Policies can be duplicated.
- **Knowledge index**: Build / rebuild is now on the Index tab.
- **Confirmations** are in-app dialogs instead of browser pop-ups.
- **AI Automation**: the nine "New … journey" buttons are one menu.
- **Settings › Appearance** now switches the theme. Notifications and Language
  still say they are not available.
- **Theme values** moved from JavaScript (`use-theme.tsx`) to CSS
  (`tokens.css`). The hook still toggles the `dark` class and stores
  `app-theme` in localStorage.
- **Wording.** Call-centre leftovers visible to users were replaced
  ("Processing call" → "Processing item", "Real Webex" → "Real source",
  "Calls Processed" → "Jobs processed", "Deduped / No Rec" →
  "Duplicates / No data"). Identifiers and API fields were not renamed.
- `src/index.css` was deleted. It was not imported anywhere
  (`main.tsx` imports `src/styles/index.css`).

## Things found but deliberately left for the backend owner

- **Policy / workflow / integration editors, Form mode.** From reading the
  code, opening an existing file in Form mode appears to regenerate the body
  from header fields only, and saving would keep that. Not verified against a
  live backend. Files: `PolicyFormBuilder.tsx`, `WorkflowFormBuilder.tsx`,
  `IntegrationFormBuilder.tsx`.
- **User management calls are sent with `requireAuth: false`**
  (`pages/UserManagement.tsx`). Whether the backend still enforces auth was
  not checked.
- **Mock screens** are unchanged in behaviour: Health › End usage, Data
  protection and Cost; Settings › Users › Invitations; the Salesforce,
  Office 365, KnowledgeBase and Langflow connector screens.
- **Dead code** (old dashboards, maps, TMF/ODA viewers, Supabase leftovers,
  `pages/backbone/*`) was restyled by the sweep but not removed.
- **174 TypeScript errors** existed before the redesign and are unchanged;
  none are in the files written for it.

## Development without a backend

`dev/sample-data/` holds a Vite dev-server plugin that answers API calls with
sample JSON (a fictional beverage company). It is active only when
`VITE_SAMPLE_DATA=true` is set in `.env.local`, only under `vite dev`, and is
not included in builds. See `.env.sample-data.example`. Sign-in, password and
MFA calls are never answered by it.

## Test checklist (run against a live backend)

- [ ] Sign in (SSO and direct), MFA, forced password change, sign out.
- [ ] Sidebar: every item opens the same page as before; collapse and expand.
- [ ] Ctrl+K search opens; selecting an item navigates.
- [ ] Theme toggle switches dark and light and survives a reload.
- [ ] Home: counts match the Control Plane stats and journey total; every
      link opens the same destination as before.
- [ ] Data Plane: each of the eight original tabs is reachable under its
      section; open a source; preview an entity; save and delete a mapping
      rule (in-app confirmation appears); run and open a pipeline.
- [ ] Control Plane: pipeline studio runs; knowledge index paging and build;
      graph: switch Constellation / Lanes / Lineage, select a node, trace a
      path, open sample rows; open, edit in Form mode and save a policy, a
      workflow and an integration and confirm nothing is lost.
- [ ] Assistant: open with the bottom-right button or Ctrl+J, ask a question,
      expand the tools used, start a new chat, check it on a phone.
- [ ] Reasoning: ask the Copilot a question and open the reasoning steps;
      run a playground query; test a tool; open the tool builder.
- [ ] Solutions: search, filter, open an app; each sidebar section loads;
      attached views render.
- [ ] AI Analytics: open, edit and save a dashboard; build a view; map a
      view to a solution.
- [ ] AI Automation: create a journey from the menu; open its studio; start
      a stage; schedule; delete a journey; plan with the Copilot; build and
      run in the builder.
- [ ] Diagnostics: run one solution check and one platform check.
- [ ] Health: monitoring loads and "Check now" works; jobs table (toggle,
      run now, edit, delete); audit log opens a run; test reports.
- [ ] Help: the three tabs; "Email support" opens the mail app.
- [ ] Enterprise Simulator page: shows Running and opens the simulator when
      it is up; says so when it is not.
- [ ] Settings: profile, password change, MFA setup; users list and role
      change; roles matrix edit and save; license status; system parameter
      edit; secret edit.
- [ ] Phone width (375px): drawer, bottom tabs, Home, a dashboard, Settings.
