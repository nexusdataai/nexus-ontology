from __future__ import annotations

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession

_RESERVED = frozenset(
    {
        "Delete Attributes Expression",
        "Store State",
        "canonical-value-lookup-cache-size",
    }
)


@register_processor("nifi.UpdateAttribute")
class UpdateAttributeProcessor(AbstractProcessor):
    spec = ProcessorSpec(
        processor_id="nifi.UpdateAttribute",
        nifi_class="org.apache.nifi.processors.attributes.UpdateAttribute",
        relationships=["success"],
    )

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        delete_expr = context.get_property("Delete Attributes Expression", "")
        ff = session.get()
        if ff is None:
            return
        props = context._properties  # noqa: SLF001
        for key, val in props.items():
            if key in _RESERVED:
                continue
            ff.put_attribute(key, context.resolve(str(val), ff.attributes))
        if delete_expr:
            import re

            try:
                pat = re.compile(delete_expr)
                for k in list(ff.attributes.keys()):
                    if pat.search(k):
                        del ff.attributes[k]
            except re.error:
                pass
        session.transfer(ff, "success")