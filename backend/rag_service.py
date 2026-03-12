from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from models import AnswerResponse, QuestionRequest, ChatMessage
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "postgres_docs_v6")
BASE_DOC_URL = os.getenv("BASE_DOC_URL", "https://www.postgresql.org/docs/16/")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")  # "cuda" for GPU

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANKER_MODEL, device=RERANKER_DEVICE)
    return _reranker


def rerank_docs(
    question: str, docs_and_scores: list[tuple[Document, float]]
) -> list[tuple[Document, float]]:
    """Rerank docs using a cross-encoder. Returns docs sorted by reranker score."""
    if not RERANKER_ENABLED or not docs_and_scores:
        return docs_and_scores
    reranker = _get_reranker()
    pairs = [(question, doc.page_content) for doc, _ in docs_and_scores]
    scores = reranker.predict(pairs)
    reranked = sorted(zip(scores, docs_and_scores), key=lambda x: x[0], reverse=True)
    # Replace embedding score with cross-encoder sigmoid score (0→1) for consistent threshold filtering
    import numpy as np
    return [(doc, float(1 / (1 + np.exp(-score)))) for score, (doc, _) in reranked]


SYSTEM_PROMPT = """You are a PostgreSQL expert assistant.

RULES (very important):
1) Answer ONLY using the excerpts provided in the sources below.
2) You may refer to the conversation history to understand context and follow-up questions,
   but never invent information that is not in the provided sources.
3) If the excerpts are not relevant, say: "I'm sorry, but the available documentation doesn't cover this topic."
4) If the question is completely off-topic (not about databases/PostgreSQL), redirect politely.
5) Do NOT include inline citations like [Chunk X] in your answer. Sources are displayed separately to the user.
6) Keep your answer concise (max 150 words). Start with a direct answer, add a SQL example if relevant.
7) If the question is ambiguous, ask 1-2 clarifying questions but still provide a generic answer.
"""

FOLLOW_UP_SYSTEM_PROMPT = """You are a PostgreSQL expert assistant engaged in an ongoing conversation.

The user's follow-up question did not match any new documentation excerpts.
Based solely on the conversation history above, please:
- Answer the follow-up (e.g., provide more examples, clarify, expand on a point already made).
- Stay strictly on-topic about PostgreSQL.
- Do not invent facts beyond what was already discussed.
- If you truly cannot answer without new documentation, ask the user to be more specific.
- Keep your answer concise (max 150 words).
"""

embedding = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
vectorstore = PGVector(
    collection_name=COLLECTION_NAME,
    connection=DATABASE_URL,
    embeddings=embedding,
    use_jsonb=True,
)
llm = ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY)


def get_embedding_score(question: QuestionRequest, top_k: int = 5) -> list[tuple[Document, float]]:
    import time
    fetch_k = top_k * 4 if RERANKER_ENABLED else top_k

    t0 = time.time()
    docs_and_scores = vectorstore.similarity_search_with_relevance_scores(question.message, fetch_k)
    import logging; logging.getLogger(__name__).info(f"[TIMING] embedding+vectorsearch: {int((time.time()-t0)*1000)}ms")

    if RERANKER_ENABLED:
        t1 = time.time()
        docs_and_scores = rerank_docs(question.message, docs_and_scores)[:top_k]
        logging.getLogger(__name__).info(f"[TIMING] reranking: {int((time.time()-t1)*1000)}ms")

    return docs_and_scores


def _select_valid_docs_and_sources(
    docs_and_scores: list[tuple[Document, float]],
) -> tuple[list[Document], list[str]]:
    """Filter retrieved docs by threshold and deduplicate source URLs."""
    valid_docs: list[Document] = []
    sources: set[str] = set()

    threshold = SIMILARITY_THRESHOLD
    for doc, score in docs_and_scores:
        if score > threshold:
            valid_docs.append(doc)
            source_file = doc.metadata.get("source", "")
            if source_file:
                sources.add(BASE_DOC_URL + source_file)

    return valid_docs, list(sources)


def _history_to_messages(history: list[ChatMessage]) -> list[BaseMessage]:
    """Convert conversation history to LangChain messages (last 10 only)."""
    result: list[BaseMessage] = []
    for msg in history[-10:]:
        if msg.role == "user":
            result.append(HumanMessage(content=msg.content))
        else:
            result.append(AIMessage(content=msg.content))
    return result


def _build_rag_messages(
    docs: list[Document],
    question: str,
    history: list[ChatMessage],
) -> list[BaseMessage]:
    """Build the message list for a question that has RAG sources."""
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    messages.extend(_history_to_messages(history))

    user_prompt = f"Here is the question:\n{question}\n\nHere are the sources:\n"
    for i, doc in enumerate(docs):
        user_prompt += (
            f"[Chunk {i}] {doc.page_content}\n"
            f"Source URL: {doc.metadata.get('source')}\n\n"
        )
    messages.append(HumanMessage(content=user_prompt))
    return messages


def _build_follow_up_messages(
    question: str,
    history: list[ChatMessage],
) -> list[BaseMessage]:
    """Build the message list for a follow-up with no new RAG sources."""
    messages: list[BaseMessage] = [SystemMessage(content=FOLLOW_UP_SYSTEM_PROMPT)]
    messages.extend(_history_to_messages(history))
    messages.append(HumanMessage(content=question))
    return messages


def generate_answer_with_score(
    question: QuestionRequest,
    docs_and_scores: list[tuple[Document, float]] | None = None,
) -> AnswerResponse:
    if docs_and_scores is None:
        docs_and_scores = get_embedding_score(question)
    valid_docs, sources = _select_valid_docs_and_sources(docs_and_scores)

    if not valid_docs and question.history:
        messages = _build_follow_up_messages(question.message, question.history)
        import time, logging
        t = time.time()
        resp = llm.invoke(messages)
        logging.getLogger(__name__).info(f"[TIMING] llm.invoke (follow-up): {int((time.time()-t)*1000)}ms")
        return AnswerResponse(answer=resp.content, sources=[])

    if not valid_docs:
        return AnswerResponse(
            answer=(
                "I couldn't find relevant PostgreSQL documentation for this question. "
                "Try being more specific by mentioning a command, feature, or PostgreSQL concept."
            ),
            sources=[],
        )

    import logging as _log
    for doc, score in docs_and_scores[:len(valid_docs)]:
        _log.getLogger(__name__).info(f"[SOURCE] score={score:.3f} | {doc.metadata.get('source', '?')}")

    messages = _build_rag_messages(valid_docs, question.message, question.history)
    import time, logging
    t = time.time()
    resp = llm.invoke(messages)
    usage = resp.response_metadata.get("token_usage", {})
    logging.getLogger(__name__).info(
        f"[TIMING] llm.invoke: {int((time.time()-t)*1000)}ms | "
        f"tokens in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}"
    )
    return AnswerResponse(answer=resp.content, sources=sources)
