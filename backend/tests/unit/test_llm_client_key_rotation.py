"""
Regression tests for runtime OpenAI key rotation.

Guards against the production failure we hit in nexus-ai-dev where the
backend pods cached a `None` OpenAI key at module-import time (the secret
was still the operator's placeholder), then never re-checked Secrets
Manager when the real key was added later. The user had to restart pods
to pick up the rotated key.

The fix: LLMClient / EmbeddingService / CopilotEngine now read the key
on every call via `_get_openai_key()`, and rebuild their cached
`openai.OpenAI` client only when the underlying key actually changes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _StubOpenAI:
    """A no-op stand-in for openai.OpenAI so tests don't hit the network."""
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs


def _patch_openai(monkeypatch, module) -> None:
    """Install a fake openai module into the target module's namespace.

    The production module does `try: import openai; OPENAI_AVAILABLE = True;
    except ImportError: OPENAI_AVAILABLE = False` so on machines where the
    openai package isn't installed the `openai` symbol is never bound. We
    use raising=False to create both attributes regardless.
    """
    fake = type("M", (), {"OpenAI": _StubOpenAI, "AsyncOpenAI": _StubOpenAI})()
    monkeypatch.setattr(module, "openai", fake, raising=False)
    monkeypatch.setattr(module, "OPENAI_AVAILABLE", True, raising=False)


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------

def test_llm_client_picks_up_rotated_key_without_reconstruction(monkeypatch):
    """
    Scenario: a LLMClient instance is constructed when the key is missing,
    then later the key is populated (e.g. operator pushed the secret to
    AWS Secrets Manager). The same instance must produce an OpenAI client
    on the next call.
    """
    from src.services.control_plane import llm_client as mod
    _patch_openai(monkeypatch, mod)
    # Start with no key resolvable anywhere.
    monkeypatch.setattr(mod, "_get_openai_key", lambda: None)

    client = mod.LLMClient()  # construction does NOT snapshot any more
    assert client.available is False

    with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
        client._ensure_client()

    # Operator rotates the key in AWS Secrets Manager → next call to the
    # resolver returns the real key.
    monkeypatch.setattr(mod, "_get_openai_key", lambda: "sk-rotated-XYZ")

    assert client.available is True
    client._ensure_client()
    assert client._client is not None
    assert client._client.api_key == "sk-rotated-XYZ"
    assert client._client_key == "sk-rotated-XYZ"


def test_llm_client_rebuilds_when_key_changes(monkeypatch):
    """A second rotation while the instance is still alive must rebuild."""
    from src.services.control_plane import llm_client as mod
    _patch_openai(monkeypatch, mod)
    monkeypatch.setattr(mod, "_get_openai_key", lambda: "sk-first")
    client = mod.LLMClient()
    client._ensure_client()
    first = client._client
    assert first.api_key == "sk-first"

    # Same key on a second call must NOT rebuild (cheap reuse).
    client._ensure_client()
    assert client._client is first

    # Rotate to a different key → must rebuild with the new value.
    monkeypatch.setattr(mod, "_get_openai_key", lambda: "sk-second")
    client._ensure_client()
    assert client._client is not first
    assert client._client.api_key == "sk-second"


def test_llm_client_explicit_key_overrides_resolver(monkeypatch):
    """If a caller passes api_key=..., the resolver is never consulted."""
    from src.services.control_plane import llm_client as mod
    _patch_openai(monkeypatch, mod)

    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError("resolver should not be called")

    monkeypatch.setattr(mod, "_get_openai_key", boom)
    client = mod.LLMClient(api_key="sk-explicit")
    client._ensure_client()
    assert client._client.api_key == "sk-explicit"
    assert calls == []   # resolver never invoked


# ---------------------------------------------------------------------------
# EmbeddingService
# ---------------------------------------------------------------------------

def test_embedding_service_picks_up_rotated_key(monkeypatch):
    from src.services.control_plane import embedding_service as mod
    _patch_openai(monkeypatch, mod)
    monkeypatch.setattr(mod, "_get_openai_key", lambda: None)
    svc = mod.EmbeddingService()
    assert svc.available is False
    with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
        svc._ensure_client()

    monkeypatch.setattr(mod, "_get_openai_key", lambda: "sk-late-key")
    assert svc.available is True
    svc._ensure_client()
    assert svc._client.api_key == "sk-late-key"
