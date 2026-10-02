"""
Notification ReAct tools (Phase 3).

WhatsApp + email + Slack channels routed through the simulator-backed
external connector APIs. Real-channel wiring is out of scope for v1; the
contract is identical so the swap is later.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import RiskLevel, Tool, ToolRegistry

notify_logger = logger.bind(component="notify-tools")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Channel mutators
# ---------------------------------------------------------------------------


async def _send_whatsapp_campaign(
    template_id: str, recipients: List[Dict[str, Any]],
    campaign_id: Optional[str] = None,
    message_body: Optional[str] = None,
    actor: str = "ai-copilot",
) -> Dict[str, Any]:
    from ..connector_runtime import append_row, emit_audit, get_sim
    sim = await get_sim("external")
    cid = campaign_id or f"WAC-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"
    row = {
        "campaign_id": cid, "channel": "whatsapp", "template_id": template_id,
        "queued": len(recipients or []),
        "recipient_ids": [r.get("customer_id") for r in (recipients or [])],
        "message_body": message_body, "queued_at": _now_iso(),
        "status": "queued",
    }
    try:
        await append_row(sim, "external_sources", "WhatsApp_Campaign_Send", row)
        await emit_audit(actor, "send_whatsapp_campaign", cid, row,
                         api_id="external.whatsapp.send_campaign")
        return {"action": "campaign_queued", "channel": "whatsapp",
                "campaign_id": cid, "queued": len(recipients or [])}
    except Exception as e:
        notify_logger.warning(f"send_whatsapp_campaign failed: {e}")
        return {"action": "failed", "error": str(e)}


async def _send_email_campaign(
    subject: str, recipients: List[Dict[str, Any]],
    campaign_id: Optional[str] = None,
    body_html: Optional[str] = None, body_text: Optional[str] = None,
    actor: str = "ai-copilot",
) -> Dict[str, Any]:
    from ..connector_runtime import append_row, emit_audit, get_sim
    sim = await get_sim("external")
    cid = campaign_id or f"EC-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"
    row = {
        "campaign_id": cid, "channel": "email", "subject": subject,
        "queued": len(recipients or []),
        "recipient_ids": [r.get("customer_id") for r in (recipients or [])],
        "queued_at": _now_iso(), "status": "queued",
    }
    try:
        await append_row(sim, "external_sources", "Email_Campaign_Send", row)
        await emit_audit(actor, "send_email_campaign", cid, row,
                         api_id="external.email.send_campaign")
        return {"action": "campaign_queued", "channel": "email",
                "campaign_id": cid, "queued": len(recipients or [])}
    except Exception as e:
        notify_logger.warning(f"send_email_campaign failed: {e}")
        return {"action": "failed", "error": str(e)}


async def _send_slack_alert(
    channel: str, message: str,
    title: Optional[str] = None, severity: str = "info",
    actor: str = "ai-copilot",
) -> Dict[str, Any]:
    from ..connector_runtime import append_row, emit_audit, get_sim
    sim = await get_sim("external")
    message_ts = f"{datetime.now().timestamp():.6f}"
    row = {
        "message_ts": message_ts, "channel": channel,
        "title": title, "message": message, "severity": severity,
        "posted_at": _now_iso(),
    }
    try:
        await append_row(sim, "external_sources", "Slack_Message", row)
        await emit_audit(actor, "post_slack_message", channel, row,
                         api_id="external.slack.post_message")
        return {"action": "slack_posted", "channel": channel,
                "message_ts": message_ts, "severity": severity}
    except Exception as e:
        notify_logger.warning(f"send_slack_alert failed: {e}")
        return {"action": "failed", "error": str(e)}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_notify_tools(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="send_whatsapp_campaign",
        description=(
            "Send a personalised WhatsApp campaign batch to a recipient list using a "
            "pre-approved template. Used by Retain Risky Customers and Churn "
            "Prevention playbooks. Approval required when batch size or spend "
            "exceeds the per-tool gate."
        ),
        parameters={
            "type": "object",
            "properties": {
                "template_id": {"type": "string"},
                "recipients": {"type": "array", "items": {"type": "object", "properties": {
                    "customer_id": {"type": "string"}, "phone": {"type": "string"},
                    "vars": {"type": "object"},
                }}},
                "campaign_id": {"type": "string"},
                "message_body": {"type": "string"},
            },
            "required": ["template_id", "recipients"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _send_whatsapp_campaign(**kw),
        connector_api="external.whatsapp.send_campaign",
        requires_approval=True,
        tool_kind="notify",
        tags=["notify", "whatsapp", "campaign"],
    ))

    registry.register(Tool(
        name="send_email_campaign",
        description=(
            "Send an email campaign batch (typically the opt-out / fallback channel "
            "for WhatsApp; also used by liquidation and renewal playbooks)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "recipients": {"type": "array", "items": {"type": "object", "properties": {
                    "customer_id": {"type": "string"}, "email": {"type": "string"},
                    "vars": {"type": "object"},
                }}},
                "campaign_id": {"type": "string"},
                "body_html": {"type": "string"},
                "body_text": {"type": "string"},
            },
            "required": ["subject", "recipients"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _send_email_campaign(**kw),
        connector_api="external.email.send_campaign",
        tool_kind="notify",
        tags=["notify", "email", "campaign"],
    ))

    registry.register(Tool(
        name="send_slack_alert",
        description=(
            "Post an operational alert to a Slack channel. Used by supply-chain-risk, "
            "OEE-recovery, and quality-hold playbooks to push real-time notifications "
            "to the right ops team."
        ),
        parameters={
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Slack channel name"},
                "message": {"type": "string"},
                "title": {"type": "string"},
                "severity": {"type": "string", "description": "info | warning | critical"},
            },
            "required": ["channel", "message"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _send_slack_alert(**kw),
        connector_api="external.slack.post_message",
        tool_kind="notify",
        tags=["notify", "slack", "alert"],
    ))

    for tool_name in ("send_whatsapp_campaign", "send_email_campaign", "send_slack_alert"):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "notify"

    notify_logger.info("Notify tools registered: 3 channels (bucket=notify)")
