"""
Onto Model — Canonical format for enterprise semantic knowledge documents.

The .onto format is a structured representation of enterprise metadata
(schemas, policies, workflows, integration mappings) enriched with
semantic descriptions for safe AI-agent reasoning.

Each OntoDocument is a semantic unit that captures:
- What the entity is (object, field, policy, workflow)
- What constraints apply
- What dependencies exist (graph relationships)
- Which system owns it
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import hashlib


@dataclass
class OntoRelationship:
    """A directed relationship between two OntoDocuments."""
    relation_type: str          # triggers | syncs_to | constrained_by | depends_on | owned_by | validates
    target_id: str              # Target OntoDocument ID
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OntoDocument:
    """
    A single semantic knowledge unit in the enterprise ontology.

    Represents one of: Field, Object, Policy, Workflow, Integration, Schema.
    The `content` field holds the LLM-enriched natural language description
    that gets embedded for vector search.
    """
    id: str                                     # e.g. SF_ACCOUNT_CREDIT_LIMIT_V3
    system: str                                 # Salesforce | Oracle | Internal | BSSMagic
    entity_type: str                            # Field | Object | Policy | Workflow | Integration | Schema
    object_name: str                            # Account | AR_Customer | CreditApprovalFlow
    category: str                               # schema | policy | workflow | integration
    content: str                                # LLM-enriched semantic description (gets embedded)

    field_name: Optional[str] = None            # Credit_Limit__c (for field-level docs)
    version: str = "1.0"
    environment: str = "prod"
    risk_level: str = "medium"                  # high | medium | low
    structured_metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: List[OntoRelationship] = field(default_factory=list)
    source: str = ""                            # fdw | policy_doc | workflow_def | integration_map
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @staticmethod
    def generate_id(system: str, object_name: str, field_name: Optional[str] = None,
                    entity_type: str = "Field", version: str = "1.0") -> str:
        parts = [system.upper(), object_name.upper()]
        if field_name:
            parts.append(field_name.upper())
        parts.append(f"V{version.replace('.', '_')}")
        raw_id = "_".join(parts)
        raw_id = raw_id.replace(" ", "_").replace("-", "_").replace(".", "_")
        if len(raw_id) > 128:
            suffix = hashlib.md5(raw_id.encode()).hexdigest()[:8]
            raw_id = raw_id[:119] + "_" + suffix
        return raw_id

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['relationships'] = [r.to_dict() for r in self.relationships]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OntoDocument':
        rels = data.pop('relationships', [])
        doc = cls(**data)
        doc.relationships = [OntoRelationship(**r) for r in rels]
        return doc


@dataclass
class OntoBundle:
    """
    A collection of OntoDocuments produced by a single pipeline run.

    Bundles are versioned, timestamped, and uploadable to S3 as .onto files.
    """
    bundle_id: str
    source: str                                 # fdw | policy | workflow | integration | full
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    documents: List[OntoDocument] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def add_document(self, doc: OntoDocument):
        self.documents.append(doc)

    def compute_statistics(self) -> Dict[str, Any]:
        by_category = {}
        by_system = {}
        by_entity_type = {}
        total_relationships = 0

        for doc in self.documents:
            by_category[doc.category] = by_category.get(doc.category, 0) + 1
            by_system[doc.system] = by_system.get(doc.system, 0) + 1
            by_entity_type[doc.entity_type] = by_entity_type.get(doc.entity_type, 0) + 1
            total_relationships += len(doc.relationships)

        self.statistics = {
            "total_documents": len(self.documents),
            "total_relationships": total_relationships,
            "by_category": by_category,
            "by_system": by_system,
            "by_entity_type": by_entity_type,
        }
        return self.statistics

    def to_dict(self) -> Dict[str, Any]:
        self.compute_statistics()
        return {
            "bundle_id": self.bundle_id,
            "source": self.source,
            "version": self.version,
            "created_at": self.created_at,
            "statistics": self.statistics,
            "documents": [d.to_dict() for d in self.documents],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OntoBundle':
        docs_data = data.pop('documents', [])
        bundle = cls(**{k: v for k, v in data.items() if k != 'statistics'})
        bundle.documents = [OntoDocument.from_dict(d) for d in docs_data]
        bundle.compute_statistics()
        return bundle

    @classmethod
    def from_json(cls, json_str: str) -> 'OntoBundle':
        return cls.from_dict(json.loads(json_str))
