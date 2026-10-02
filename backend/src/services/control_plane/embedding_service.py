"""
Embedding Service for the AI Control Plane.

Generates text embeddings using OpenAI's text-embedding-3-small model.
Used to embed FDW schema metadata, TMF specs, and business policies
for semantic retrieval by the RAG layer.
"""

import os
import json
from typing import List, Optional

from loguru import logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from ...config.config_provider import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

cp_logger = logger.bind(component="control-plane")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def _get_openai_key() -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    if CONFIG_AVAILABLE:
        try:
            config = get_config()
            return getattr(config, "openai_api_key", None)
        except Exception:
            pass
    try:
        import boto3
        sm = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
        env = os.getenv("ENVIRONMENT", "prod")
        for pattern in (f"call-processing/{env}/openai", f"call-processing-{env}-openai"):
            try:
                secret = sm.get_secret_value(SecretId=pattern)
                data = json.loads(secret["SecretString"])
                for k in ("OPENAI_API_KEY", "api_key", "apiKey"):
                    if k in data:
                        return data[k]
            except Exception:
                continue
    except Exception:
        pass
    return None


class EmbeddingService:
    """Generates embeddings via OpenAI text-embedding-3-small."""

    def __init__(self, api_key: Optional[str] = None):
        # See LLMClient.__init__ for the rationale: explicit key honored
        # for the lifetime of the instance; otherwise resolved fresh on
        # every access so secret rotations propagate without restart.
        self._explicit_api_key = api_key
        self._client = None
        self._client_key: Optional[str] = None

    @property
    def _api_key(self) -> Optional[str]:
        return self._explicit_api_key or _get_openai_key()

    @property
    def available(self) -> bool:
        return OPENAI_AVAILABLE and bool(self._api_key)

    def _ensure_client(self):
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package not installed")
        key = self._api_key
        if not key:
            raise RuntimeError("OpenAI API key not configured")
        if self._client is None or self._client_key != key:
            self._client = openai.OpenAI(api_key=key)
            self._client_key = key

    def embed_text(self, text: str) -> List[float]:
        self._ensure_client()
        resp = self._client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,
        )
        return resp.data[0].embedding

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        self._ensure_client()
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = self._client.embeddings.create(
                input=batch,
                model=EMBEDDING_MODEL,
            )
            all_embeddings.extend([d.embedding for d in resp.data])
        cp_logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings


_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service
