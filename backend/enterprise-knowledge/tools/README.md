# Tool Catalogue

One YAML per registered ReAct tool, grouped by domain.

```
tools/
  o2c/
    place_credit_hold.yaml
    send_dunning_notice.yaml
    ...
  virtual_query/
    query_virtual_entity.yaml
  rag/
    search_enterprise_knowledge.yaml
  ...
```

The YAML schema is `ToolDoc` in
[`src/models/automation_models.py`](../../src/models/automation_models.py).
The Python registration in `src/services/control_plane/tools/*.py` remains
the source of truth for execution; YAML is metadata that powers the
knowledge graph and Copilot's semantic tool discovery.

## Bootstrap

To dump every currently-registered tool as a YAML draft:

```bash
python3 scripts/migrations/dump_tool_catalog.py
python3 scripts/migrations/dump_tool_catalog.py --overwrite          # force
python3 scripts/migrations/dump_tool_catalog.py --group o2c          # filter
```

Run inside a backend pod (or locally with `PYTHONPATH=.`).

## Authoring guidelines

After bootstrap, hand-edit each YAML to fill in:

- `description` - what the tool does in plain English (Copilot reads this).
- `consumes_entities` / `produces_entities` - virtual entity names this tool reads / writes.
- `tags` - capability hints (`["credit", "collections"]`) for retrieval.
- `example_invocation` - one realistic params dict.

## Indexing

The automation indexer (`services/control_plane/automation_indexer.py`)
walks this folder on startup and writes each tool as `onto_tool` into
the vector store, with `(:TOOL)-[:CALLS_API]->(:CONNECTOR_API)` and
`(:TOOL)-[:READS|:WRITES]->(:VIRTUAL_ENTITY)` edges in the graph.
