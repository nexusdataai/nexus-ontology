# Syncing from `nexus-ontology-UI/frontend`

`nexus-ontology-UI` is the design sandbox. Production UI lives here in `nexus-ontology/frontend`.

## Workflow

1. Prototype visual changes in `../nexus-ontology-UI/frontend`.
2. Port into this tree in small PRs — prefer copying `src/styles/`, `src/components/ds/`, shell (`Layout`, `Sidebar`, `navigation.ts`), then pages by domain.
3. Do **not** change `src/services/*` for visual-only work (see [README.md](./README.md)).
4. After porting: `npm run icons`, `npm run type-check`, `npm test`, `npm run build:prod`.

## Bulk compare

```bash
diff -rq nexus-ontology/frontend/src nexus-ontology-UI/frontend/src
```

Review anything under `services/` or auth-critical paths before overwriting production files.
