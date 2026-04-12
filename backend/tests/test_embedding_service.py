"""Tests for EmbeddingService — serialize/deserialize and interface contract."""
from __future__ import annotations

import struct
from unittest.mock import MagicMock, patch

import pytest

from app.embeddings.embedding_service import (
    EmbeddingService,
    deserialize,
    serialize,
    _DIM,
)


# ---------------------------------------------------------------------------
# serialize / deserialize round-trip
# ---------------------------------------------------------------------------

class TestSerializeDeserialize:
    def test_round_trip(self):
        embedding = [0.1, 0.2, -0.3, 0.9]
        assert deserialize(serialize(embedding)) == pytest.approx(embedding, abs=1e-6)

    def test_full_dim_round_trip(self):
        embedding = [float(i) / _DIM for i in range(_DIM)]
        recovered = deserialize(serialize(embedding))
        assert len(recovered) == _DIM
        assert recovered == pytest.approx(embedding, abs=1e-5)

    def test_serialize_produces_bytes(self):
        result = serialize([1.0, 2.0])
        assert isinstance(result, bytes)
        assert len(result) == 8  # 2 float32 = 8 bytes

    def test_empty_round_trip(self):
        assert deserialize(serialize([])) == []


# ---------------------------------------------------------------------------
# EmbeddingService interface
# ---------------------------------------------------------------------------

class TestEmbeddingService:
    def test_embed_returns_list_of_floats(self):
        svc = EmbeddingService()
        fake_array = MagicMock()
        fake_array.tolist.return_value = [0.1] * _DIM

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value.encode.return_value = fake_array
            result = svc.embed("test text")

        assert isinstance(result, list)
        assert len(result) == _DIM
        assert all(isinstance(v, float) for v in result)

    def test_embed_empty_text_returns_zero_vector(self):
        svc = EmbeddingService()
        result = svc.embed("")
        assert result == [0.0] * _DIM

    def test_embed_whitespace_returns_zero_vector(self):
        svc = EmbeddingService()
        result = svc.embed("   ")
        assert result == [0.0] * _DIM

    def test_warmup_loads_model(self):
        svc = EmbeddingService()
        assert svc._model is None
        with patch("sentence_transformers.SentenceTransformer") as MockST:
            svc.warmup()
        assert svc._model is not None

    def test_warmup_idempotent(self):
        svc = EmbeddingService()
        with patch("sentence_transformers.SentenceTransformer") as MockST:
            svc.warmup()
            svc.warmup()  # second call should not reload
        assert MockST.call_count == 1

    def test_embed_text_for_post(self):
        svc = EmbeddingService()
        post = MagicMock()
        post.content = "AI agent orchestration using tool calling"

        fake_array = MagicMock()
        fake_array.tolist.return_value = [0.5] * _DIM

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value.encode.return_value = fake_array
            result = svc.embed_text_for_post(post)

        assert len(result) == _DIM


# ---------------------------------------------------------------------------
# VectorSearch cosine similarity
# ---------------------------------------------------------------------------

class TestVectorSearch:
    def test_cosine_similarity_identical(self):
        from app.embeddings.vector_search import _cosine_similarity
        import numpy as np
        v = np.array([1.0, 0.0, 0.0])
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        from app.embeddings.vector_search import _cosine_similarity
        import numpy as np
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector(self):
        from app.embeddings.vector_search import _cosine_similarity
        import numpy as np
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert _cosine_similarity(a, b) == 0.0

    def test_vector_search_returns_sorted_by_similarity(self):
        from app.embeddings.vector_search import vector_search

        q = [1.0, 0.0]
        close = MagicMock()
        close.id = 1
        close.embedding = serialize([0.99, 0.1])
        close.is_relevant = True

        far = MagicMock()
        far.id = 2
        far.embedding = serialize([0.1, 0.99])
        far.is_relevant = True

        store = MagicMock()
        store.get_posts_with_embeddings.return_value = [far, close]

        results = vector_search(q, store, top_k=2)
        assert results[0].id == close.id
        assert results[1].id == far.id

    def test_vector_search_excludes_ids(self):
        from app.embeddings.vector_search import vector_search

        q = [1.0, 0.0]
        p = MagicMock()
        p.id = 42
        p.embedding = serialize([1.0, 0.0])
        p.is_relevant = True

        store = MagicMock()
        store.get_posts_with_embeddings.return_value = [p]

        results = vector_search(q, store, top_k=5, exclude_ids=[42])
        assert results == []
