"""
Policy Document Extractor

Parses business policy documents (Markdown, PDF, plain text) from local
filesystem or S3 into OntoDocument objects.

Supports:
- Markdown (.md) — split by ## headings into individual policy rules
- PDF (.pdf) — extracted via pymupdf/fitz if available, fallback to raw text
- Text (.txt) — treated as a single policy document
"""

import os
import sys
import glob
from typing import List, Optional

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stage_dir = os.path.dirname(_current_dir)
if _stage_dir not in sys.path:
    sys.path.insert(0, _stage_dir)

from onto_model import OntoDocument, OntoRelationship


class PolicyExtractor:
    def __init__(self, logger=None, local_path: str = "", s3_prefix: str = ""):
        self._log = logger
        self._local_path = local_path
        self._s3_prefix = s3_prefix

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def extract(self) -> List[OntoDocument]:
        docs: List[OntoDocument] = []

        if self._local_path and os.path.exists(self._local_path):
            docs.extend(self._extract_local(self._local_path))

        if self._s3_prefix:
            docs.extend(self._extract_s3(self._s3_prefix))

        if not docs:
            self._info("No policy documents found — skipping")

        return docs

    def _extract_local(self, path: str) -> List[OntoDocument]:
        docs = []
        if os.path.isfile(path):
            files = [path]
        else:
            files = (
                glob.glob(os.path.join(path, "**/*.md"), recursive=True)
                + glob.glob(os.path.join(path, "**/*.txt"), recursive=True)
                + glob.glob(os.path.join(path, "**/*.pdf"), recursive=True)
            )

        self._info(f"Found {len(files)} policy files in {path}")

        for filepath in files:
            ext = os.path.splitext(filepath)[1].lower()
            filename = os.path.basename(filepath)

            if ext == ".md":
                docs.extend(self._parse_markdown(filepath, filename))
            elif ext == ".pdf":
                docs.extend(self._parse_pdf(filepath, filename))
            elif ext == ".txt":
                docs.extend(self._parse_text(filepath, filename))

        return docs

    def _extract_s3(self, prefix: str) -> List[OntoDocument]:
        self._info(f"S3 policy extraction from prefix '{prefix}' — not yet implemented")
        return []

    def _parse_markdown(self, filepath: str, filename: str) -> List[OntoDocument]:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        sections = content.split("\n## ")
        docs = []

        policy_name = os.path.splitext(filename)[0]
        first_line = content.split("\n", 1)[0].lstrip("# ").strip()
        root_title = first_line if first_line else policy_name

        section_ids = []
        for i, section in enumerate(sections):
            section = section.strip()
            if not section or len(section) < 20:
                continue

            lines = section.split("\n", 1)
            title = lines[0].lstrip("# ").strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            doc_id = OntoDocument.generate_id(
                "Internal", f"Policy_{filename}_{i}", entity_type="Policy"
            )
            section_ids.append(doc_id)
            docs.append(OntoDocument(
                id=doc_id,
                system="Internal",
                entity_type="Policy",
                object_name=title,
                category="policy",
                content=f"Policy: {title}\n\n{body}",
                source="policy_doc",
                structured_metadata={"source_file": filename, "section_index": i},
            ))

        cross_ref_entities = []
        cross_ref_workflows = []
        cross_ref_integrations = []
        cross_ref_apps = []
        for doc in docs:
            title_lower = doc.object_name.lower()
            if "related entities" in title_lower:
                cross_ref_entities = [line.strip("- ").strip() for line in doc.content.split("\n") if line.strip().startswith("- ")]
            elif "related workflows" in title_lower:
                cross_ref_workflows = [line.strip("- ").strip() for line in doc.content.split("\n") if line.strip().startswith("- ")]
            elif "related integrations" in title_lower:
                cross_ref_integrations = [line.strip("- ").strip() for line in doc.content.split("\n") if line.strip().startswith("- ")]
            elif "used by" in title_lower:
                cross_ref_apps = [line.strip("- ").strip() for line in doc.content.split("\n") if line.strip().startswith("- ")]

        root_id = OntoDocument.generate_id("Internal", policy_name, entity_type="Policy")
        root_rels = [
            OntoRelationship(
                relation_type="contains",
                target_id=sid,
                description=f"Section of {root_title}",
            )
            for sid in section_ids
        ]

        root_content = f"Policy Document: {root_title}\n\nThis policy contains {len(section_ids)} sections covering: " + \
                    ", ".join(d.object_name for d in docs[1:min(6, len(docs))]) + "."
        if cross_ref_entities:
            root_content += "\nRelated Entities: " + ", ".join(cross_ref_entities[:10])
        if cross_ref_workflows:
            root_content += "\nRelated Workflows: " + ", ".join(cross_ref_workflows[:5])
        if cross_ref_integrations:
            root_content += "\nRelated Integrations: " + ", ".join(cross_ref_integrations[:5])
        if cross_ref_apps:
            root_content += "\nUsed By: " + ", ".join(cross_ref_apps[:5])

        root_meta = {"source_file": filename, "root": True, "section_count": len(section_ids)}
        if cross_ref_entities:
            root_meta["related_entities"] = cross_ref_entities
        if cross_ref_workflows:
            root_meta["related_workflows"] = cross_ref_workflows

        docs.insert(0, OntoDocument(
            id=root_id,
            system="Internal",
            entity_type="Policy",
            object_name=root_title,
            category="policy",
            content=root_content,
            source="policy_doc",
            structured_metadata=root_meta,
            relationships=root_rels,
        ))

        self._info(f"  Parsed {len(docs)} policy docs ({len(section_ids)} sections + 1 root) from {filename}")
        return docs

    def _parse_pdf(self, filepath: str, filename: str) -> List[OntoDocument]:
        try:
            import fitz
            pdf_doc = fitz.open(filepath)
            text = "\n".join(page.get_text() for page in pdf_doc)
            pdf_doc.close()
        except ImportError:
            self._info(f"  pymupdf not available — reading PDF as raw text: {filename}")
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        if not text.strip():
            return []

        doc_id = OntoDocument.generate_id("Internal", f"Policy_{filename}", entity_type="Policy")
        return [OntoDocument(
            id=doc_id,
            system="Internal",
            entity_type="Policy",
            object_name=filename,
            category="policy",
            content=text[:8000],
            source="policy_doc",
            structured_metadata={"source_file": filename, "format": "pdf"},
        )]

    def _parse_text(self, filepath: str, filename: str) -> List[OntoDocument]:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        if not text.strip():
            return []

        doc_id = OntoDocument.generate_id("Internal", f"Policy_{filename}", entity_type="Policy")
        return [OntoDocument(
            id=doc_id,
            system="Internal",
            entity_type="Policy",
            object_name=filename,
            category="policy",
            content=text[:8000],
            source="policy_doc",
            structured_metadata={"source_file": filename, "format": "text"},
        )]
