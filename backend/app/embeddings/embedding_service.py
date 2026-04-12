"""EmbeddingService: local sentence-transformers inference with HF API fallback.

Default model: sentence-transformers/all-MiniLM-L6-v2
  - Size: ~22 MB
  - Dimensions: 384
  - CPU inference: 50–200 ms per text
  - Max tokens: 256 (longer text is truncated automatically)

Embeddings are serialized as packed float32 bytes for compact BLOB storage.
"""
from __future__ import annotations

import logging
import struct
from typing import Optional

logger = logging.getLogger(__name__)

_DIM = 384  # all-MiniLM-L6-v2 output dimension


def serialize(embedding: list[float]) -> bytes:
    """Pack float list into compact binary (float32)."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def deserialize(data: bytes) -> list[float]:
    """Unpack binary blob back to float list."""
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


class EmbeddingService:
    """Compute text embeddings using a local sentence-transformers model.

    Lazy-loads the model on first call to avoid blocking server startup.
    Falls back to HF Inference API when hf_api_token is set and
    use_local=False.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        use_local: bool = True,
        hf_api_token: str = "",
    ) -> None:
        self._model_name = model_name
        self._use_local = use_local
        self._hf_api_token = hf_api_token
        self._model = None  # lazy load

    def warmup(self) -> None:
        """Pre-load the model. Call once at server startup to avoid first-request latency."""
        if self._use_local and self._model is None:
            logger.info("EmbeddingService: loading model %s …", self._model_name)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            logger.info("EmbeddingService: model loaded (dim=%d)", _DIM)

    def embed(self, text: str) -> list[float]:
        """Return embedding vector for text. Blocks until complete."""
        if not text or not text.strip():
            return [0.0] * _DIM

        if self._use_local:
            return self._embed_local(text)
        elif self._hf_api_token:
            return self._embed_hf_api(text)
        else:
            raise RuntimeError("EmbeddingService: no local model and no HF API token configured.")

    def embed_text_for_post(self, post) -> list[float]:
        """Build embedding input from a Post object and embed it."""
        # Use content (truncated) as the embedding source
        text = (post.content or "")[:512]
        return self.embed(text)

    def _embed_local(self, text: str) -> list[float]:
        if self._model is None:
            self.warmup()
        result = self._model.encode(text, show_progress_bar=False)
        return result.tolist()

    def _embed_hf_api(self, text: str) -> list[float]:
        import httpx
        resp = httpx.post(
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self._model_name}",
            headers={"Authorization": f"Bearer {self._hf_api_token}"},
            json={"inputs": text, "options": {"wait_for_model": True}},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # HF returns list of token embeddings for feature-extraction; take mean pooling
        if isinstance(data[0], list):
            import numpy as np
            return np.mean(data, axis=0).tolist()
        return data
