from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from src.services.flow_runtime.context import ProcessContext
from src.services.flow_runtime.session import ProcessSession


@dataclass
class ProcessorSpec:
    processor_id: str
    nifi_class: str = ""
    relationships: List[str] = field(default_factory=lambda: ["success", "failure"])
    properties_schema: List[Dict[str, Any]] = field(default_factory=list)


class AbstractProcessor(ABC):
    spec: ProcessorSpec

    @abstractmethod
    def on_trigger(self, context: ProcessContext, session: ProcessSession) -> None:
        pass


_PROCESSOR_REGISTRY: Dict[str, Type[AbstractProcessor]] = {}


def register_processor(processor_id: str):
    def _wrap(cls: Type[AbstractProcessor]) -> Type[AbstractProcessor]:
        _PROCESSOR_REGISTRY[processor_id] = cls
        cls.spec = getattr(cls, "spec", ProcessorSpec(processor_id=processor_id))
        return cls

    return _wrap


def get_processor_class(processor_id: str) -> Optional[Type[AbstractProcessor]]:
    return _PROCESSOR_REGISTRY.get(processor_id)


def list_registered_processor_ids() -> List[str]:
    return sorted(_PROCESSOR_REGISTRY.keys())