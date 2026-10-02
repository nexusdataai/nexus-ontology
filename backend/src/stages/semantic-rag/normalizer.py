"""
Normalizer — merges extracted OntoDocuments, deduplicates, and produces a clean OntoBundle.
"""

from typing import List
from onto_model import OntoDocument, OntoBundle


class Normalizer:
    def __init__(self, logger=None):
        self._log = logger

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def normalize(self, documents: List[OntoDocument], bundle_id: str = "default") -> OntoBundle:
        seen_ids = {}
        dedup_count = 0

        for doc in documents:
            if doc.id in seen_ids:
                existing = seen_ids[doc.id]
                existing.relationships.extend(doc.relationships)
                if len(doc.content) > len(existing.content):
                    existing.content = doc.content
                if doc.structured_metadata:
                    existing.structured_metadata.update(doc.structured_metadata)
                dedup_count += 1
            else:
                seen_ids[doc.id] = doc

        unique_docs = list(seen_ids.values())
        self._info(f"Normalized: {len(documents)} raw -> {len(unique_docs)} unique "
                    f"({dedup_count} merged)")

        bundle = OntoBundle(bundle_id=bundle_id, source="full", version="1.0")
        for doc in unique_docs:
            bundle.add_document(doc)

        return bundle
