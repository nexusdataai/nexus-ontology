#!/usr/bin/env python3
"""Scaffold a new flow processor module from catalog metadata."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "enterprise-knowledge" / "flow-processors" / "processors.json"


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


TEMPLATE = '''from __future__ import annotations

from src.services.flow_processors.handlers.builtin import dispatch
from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec, register_processor
from src.services.flow_runtime.session import ProcessSession


@register_processor("nexus.{short}")
class {short}Processor(AbstractProcessor):
    spec = ProcessorSpec(processor_id="nexus.{short}")

    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        dispatch("{short}", context, session)
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("processor_id", help="e.g. nexus.FlattenJson")
    args = ap.parse_args()
    short = args.processor_id.replace("nifi.", "nexus.").split(".")[-1]
    path = ROOT / "src" / "services" / "flow_processors" / f"{camel_to_snake(short)}.py"
    path.write_text(TEMPLATE.format(short=short), encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()