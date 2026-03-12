from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal

MAX_HISTORY_LENGTH = 20


class ChatMessage(BaseModel):
    role: Literal["user", "ai"]
    content: str


class QuestionRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=500,
        description="The user's current question"
    )
    history: List[ChatMessage] = Field(
        default_factory=list,
        max_length=MAX_HISTORY_LENGTH,
        description="Conversation history (last 20 messages accepted, last 10 used for context)"
    )

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class AnswerResponse(BaseModel):
    answer: str
    sources: List[str]
    latency_ms: Optional[int] = None
