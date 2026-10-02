/**
 * Reference cheat-sheet for the Tool Builder Monaco editor.
 *
 * Monaco's Python LSP support is limited (no real IntelliSense), so we
 * surface this string as a side-panel help block and as the body of the
 * default "New Tool" template so authors discover the helpers.
 */

export const TOOL_HELPER_REFERENCE = `# Helpers injected into every async def run(...) call:
#
# vdl                       - read-only Virtual Data Layer
#   await vdl.query(entity, filters=[{field, operator, value}], limit=100) -> list[dict]
#   await vdl.list_entities() -> list[str]
#   await vdl.get_entity_schema(entity) -> dict
#
# connectors                - write surface (every call is verified + audited)
#   await connectors.call(api_id, payload) -> {http_status, response, verdict, ...}
#
# ctx                       - per-invocation context
#   ctx.user, ctx.journey_id, ctx.session_id, ctx.invocation_id, ctx.started_at
#
# log                       - buffered logger (visible in Test panel)
#   log.info(msg, **kw), log.warning(msg, **kw), log.error(msg, **kw)
#
# Allowed stdlib modules: json, datetime, uuid, re, math, decimal,
# itertools, functools, statistics, time
`;

export const DEFAULT_TOOL_TEMPLATE = `async def run(params: dict, vdl, connectors, ctx, log) -> dict:
    """Custom ReAct tool.

    Args:
        params:     validated against tool.parameters JSON Schema
        vdl:        await vdl.query(entity, filters=[...], limit=N)
        connectors: await connectors.call(api_id, payload)
        ctx:        ctx.user / ctx.journey_id / ctx.invocation_id
        log:        log.info(...) / log.warning(...) / log.error(...)
    """
    log.info("starting", params=params)

    # Example: read 5 overdue invoices and place credit hold on their accounts.
    # invoices = await vdl.query(
    #     "AR_Invoice",
    #     filters=[{"field": "Status", "operator": "eq", "value": "Overdue"}],
    #     limit=5,
    # )
    # for inv in invoices:
    #     await connectors.call("sfdc.account.credit_hold.set", {
    #         "account_id": inv["Customer_ID"],
    #         "hold": True,
    #         "reason": "auto via tool",
    #     })

    return {"ok": True}
`;

export const RISK_OPTIONS: { value: string; label: string }[] = [
  { value: 'read_only', label: 'Read only' },
  { value: 'low_risk_write', label: 'Low-risk write' },
  { value: 'high_risk_write', label: 'High-risk write' },
];
