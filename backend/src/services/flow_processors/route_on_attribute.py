from __future__ import annotations

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.RouteOnAttribute")
class RouteOnAttributeProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nexus.RouteOnAttribute",
        relationships=["matched", "unmatched"],
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        routing_strategy = context.get_property("Routing Strategy", "Route to Property name")
        ff = session.get()
        if ff is None:
            return
        matched = False
        props = context._properties  # noqa: SLF001
        for rel, expr in props.items():
            if rel in ("Routing Strategy",):
                continue
            if not expr:
                continue
            resolved = context.resolve(str(expr), ff.attributes)
            if resolved and resolved.lower() not in ("false", "0", "no"):
                session.transfer(ff, rel)
                matched = True
                break
        if not matched:
            rel = "unmatched" if routing_strategy else "unmatched"
            session.transfer(ff, rel)