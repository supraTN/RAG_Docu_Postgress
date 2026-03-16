"""Tests for Pydantic request/response models."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import AnswerResponse, ChatMessage, QuestionRequest


class TestQuestionRequest:
    def test_valid_message(self):
        req = QuestionRequest(message="What is MVCC?")
        assert req.message == "What is MVCC?"

    def test_message_is_stripped(self):
        req = QuestionRequest(message="  What is MVCC?  ")
        assert req.message == "What is MVCC?"

    def test_empty_message_raises(self):
        with pytest.raises(Exception):
            QuestionRequest(message="   ")

    def test_message_too_long_raises(self):
        with pytest.raises(Exception):
            QuestionRequest(message="x" * 501)

    def test_history_default_empty(self):
        req = QuestionRequest(message="test")
        assert req.history == []

    def test_history_max_length_enforced(self):
        history = [ChatMessage(role="user", content=f"msg {i}") for i in range(21)]
        with pytest.raises(Exception):
            QuestionRequest(message="test", history=history)

    def test_history_at_max_length_is_valid(self):
        history = [ChatMessage(role="user", content=f"msg {i}") for i in range(20)]
        req = QuestionRequest(message="test", history=history)
        assert len(req.history) == 20

    def test_default_model_is_none(self):
        req = QuestionRequest(message="test")
        assert req.model is None

    def test_valid_model_gpt4(self):
        req = QuestionRequest(message="test", model="gpt-4.1-mini")
        assert req.model == "gpt-4.1-mini"

    def test_valid_model_gpt5(self):
        req = QuestionRequest(message="test", model="gpt-5-mini")
        assert req.model == "gpt-5-mini"

    def test_invalid_model_raises(self):
        with pytest.raises(Exception):
            QuestionRequest(message="test", model="gpt-3")


class TestAnswerResponse:
    def test_minimal_response(self):
        resp = AnswerResponse(answer="MVCC is...", sources=[])
        assert resp.latency_ms is None

    def test_with_latency(self):
        resp = AnswerResponse(answer="MVCC is...", sources=["https://example.com"], latency_ms=450)
        assert resp.latency_ms == 450

    def test_with_multiple_sources(self):
        sources = ["https://example.com/1", "https://example.com/2"]
        resp = AnswerResponse(answer="answer", sources=sources)
        assert len(resp.sources) == 2


class TestChatMessage:
    def test_user_role(self):
        msg = ChatMessage(role="user", content="hello")
        assert msg.role == "user"

    def test_ai_role(self):
        msg = ChatMessage(role="ai", content="hello")
        assert msg.role == "ai"

    def test_invalid_role_raises(self):
        with pytest.raises(Exception):
            ChatMessage(role="system", content="hello")
