"""NiFi-shaped flow runtime (JVM-free)."""

from src.services.flow_runtime.dag_runner import run_nifi_dag
from src.services.flow_runtime.flowfile import FlowFile
from src.services.flow_runtime.processor import AbstractProcessor, ProcessorSpec

__all__ = ["FlowFile", "AbstractProcessor", "ProcessorSpec", "run_nifi_dag"]