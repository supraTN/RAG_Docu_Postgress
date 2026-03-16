"""Tests for pure helper functions in rag_service — no DB, no API calls."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Set required env vars before importing rag_service
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost/test")

# Mock heavy dependencies so the module loads without a live DB or API
_mock_modules = {
    "langchain_openai": MagicMock(),
    "langchain_postgres": MagicMock(),
    "langchain_core": MagicMock(),
    "langchain_core.documents": MagicMock(),
    "langchain_core.messages": MagicMock(),
}
with patch.dict("sys.modules", _mock_modules):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import rag_service

    # Patch the module-level objects created at import time
    rag_service.vectorstore = MagicMock()
    rag_service.llm = MagicMock()


sys.path.insert(0, str(Path(__file__).parent.parent))
from models import ChatMessage


class TestHistoryToMessages:
    def test_empty_history_returns_empty_list(self):
        result = rag_service._history_to_messages([])
        assert result == []

    def test_keeps_last_10_messages(self):
        history = [ChatMessage(role="user", content=f"msg {i}") for i in range(15)]
        result = rag_service._history_to_messages(history)
        assert len(result) == 10

    def test_exactly_10_messages_unchanged(self):
        history = [ChatMessage(role="user", content=f"msg {i}") for i in range(10)]
        result = rag_service._history_to_messages(history)
        assert len(result) == 10

    def test_fewer_than_10_messages_unchanged(self):
        history = [ChatMessage(role="user", content="q"), ChatMessage(role="ai", content="a")]
        result = rag_service._history_to_messages(history)
        assert len(result) == 2


class TestSelectValidDocsAndSources:
    def _make_doc(self, source="test.html"):
        doc = MagicMock()
        doc.metadata = {"source": source, "raw_content": "test content"}
        doc.page_content = "test content"
        return doc

    def test_empty_input_returns_empty(self):
        docs, sources = rag_service._select_valid_docs_and_sources([])
        assert docs == []
        assert sources == []

    def test_keeps_doc_above_similarity_threshold(self):
        doc = self._make_doc()
        result_docs, sources = rag_service._select_valid_docs_and_sources(
            [(doc, 0.9)], is_reranked=False
        )
        assert len(result_docs) == 1
        assert len(sources) == 1

    def test_filters_doc_below_similarity_threshold(self):
        doc = self._make_doc()
        # Default SIMILARITY_THRESHOLD is 0.4; use a score below it
        result_docs, sources = rag_service._select_valid_docs_and_sources(
            [(doc, 0.1)], is_reranked=False
        )
        assert result_docs == []
        assert sources == []

    def test_deduplicates_identical_sources(self):
        doc1 = self._make_doc(source="mvcc.html")
        doc2 = self._make_doc(source="mvcc.html")
        _, sources = rag_service._select_valid_docs_and_sources(
            [(doc1, 0.9), (doc2, 0.8)], is_reranked=False
        )
        assert len(sources) == 1

    def test_reranked_uses_adaptive_threshold(self):
        doc_best = self._make_doc(source="best.html")
        doc_low = self._make_doc(source="low.html")
        # best_score=0.9, ratio=0.8 → threshold=0.72; doc_low score=0.5 should be filtered
        result_docs, _ = rag_service._select_valid_docs_and_sources(
            [(doc_best, 0.9), (doc_low, 0.5)], is_reranked=True
        )
        assert len(result_docs) == 1
        assert result_docs[0] is doc_best
