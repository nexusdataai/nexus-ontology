"""
Semantic Chunker & Embedder

Chunks OntoDocuments by semantic unit (not token count) and generates
embeddings using the existing EmbeddingService.
"""

import os
import sys
from typing import List, Dict, Any
from onto_model import OntoBundle, OntoDocument


class Chunker:
    def __init__(self, logger=None):
        self._log = logger

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def chunk_and_embed(self, bundle: OntoBundle) -> List[Dict[str, Any]]:
        """
        Each OntoDocument is one semantic chunk (no random splitting).
        Returns list of dicts with: onto_id, content, metadata, embedding.
        """
        try:
            from src.services.control_plane.embedding_service import EmbeddingService
            embedding_svc = EmbeddingService()
        except Exception as e:
            self._info(f"EmbeddingService not available: {e} — generating placeholder embeddings")
            embedding_svc = None

        results = []
        batch_size = 20
        docs = bundle.documents

        for batch_start in range(0, len(docs), batch_size):
            batch = docs[batch_start:batch_start + batch_size]
            texts = [doc.content for doc in batch]

            if embedding_svc:
                try:
                    embeddings = embedding_svc.embed_batch(texts)
                except Exception:
                    embeddings = embedding_svc.embed_texts(texts) if hasattr(embedding_svc, 'embed_texts') else [
                        embedding_svc.embed_text(t) for t in texts
                    ]
            else:
                embeddings = [[0.0] * 1536 for _ in texts]

            for doc, emb in zip(batch, embeddings):
                results.append({
                    "onto_id": doc.id,
                    "content_type": f"onto_{doc.category}",
                    "source_id": doc.id,
                    "content": doc.content,
                    "metadata": {
                        "system": doc.system,
                        "entity_type": doc.entity_type,
                        "object_name": doc.object_name,
                        "field_name": doc.field_name,
                        "category": doc.category,
                        "version": doc.version,
                        "risk_level": doc.risk_level,
                        "source": doc.source,
                    },
                    "embedding": emb,
                })

            if batch_start % 100 == 0 and batch_start > 0:
                self._info(f"  Embedded {batch_start}/{len(docs)} chunks")

        self._info(f"Chunking complete: {len(results)} chunks with embeddings")
        return results
