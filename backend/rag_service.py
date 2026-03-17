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
_raw_db_url = os.getenv("DATABASE_URL", "")
# Railway provides postgresql:// but langchain-postgres needs postgresql+psycopg://
if _raw_db_url.startswith("postgresql://"):
    DATABASE_URL = _raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = _raw_db_url
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "postgres_docs_v10")
BASE_DOC_URL = os.getenv("BASE_DOC_URL", "https://www.postgresql.org/docs/16/")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_RERANK_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-v4.0-fast")
FALLBACK_RERANKER_MODEL = os.getenv("FALLBACK_RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")  # "cuda" for GPU (fallback model only)
RERANKER_THRESHOLD = float(os.getenv("RERANKER_THRESHOLD", "0.5"))  # absolute minimum score post-reranking
RERANKER_SCORE_RATIO = float(os.getenv("RERANKER_SCORE_RATIO", "0.8"))  # keep chunks scoring >= ratio * best_score

_cohere_client = None
_fallback_reranker = None

import threading
_client_lock = threading.Lock()


def _get_cohere_client():
    global _cohere_client
    with _client_lock:
        if _cohere_client is None and COHERE_API_KEY:
            import cohere
            _cohere_client = cohere.Client(api_key=COHERE_API_KEY)
    return _cohere_client


def _get_fallback_reranker():
    global _fallback_reranker
    with _client_lock:
        if _fallback_reranker is None:
            from sentence_transformers import CrossEncoder
            _fallback_reranker = CrossEncoder(FALLBACK_RERANKER_MODEL, device=RERANKER_DEVICE)
    return _fallback_reranker


def _rerank_cohere(
    question: str, docs_and_scores: list[tuple[Document, float]]
) -> list[tuple[Document, float]]:
    """Rerank using Cohere Rerank v4 API."""
    client = _get_cohere_client()
    documents = [doc.metadata.get("raw_content", doc.page_content) for doc, _ in docs_and_scores]
    response = client.rerank(
        model=COHERE_RERANK_MODEL,
        query=question,
        documents=documents,
    )
    reranked = []
    for result in response.results:
        doc, _ = docs_and_scores[result.index]
        reranked.append((doc, float(result.relevance_score)))
    return reranked


def _rerank_fallback(
    question: str, docs_and_scores: list[tuple[Document, float]]
) -> list[tuple[Document, float]]:
    """Rerank using local cross-encoder fallback."""
    reranker = _get_fallback_reranker()
    pairs = [(question, doc.metadata.get("raw_content", doc.page_content)) for doc, _ in docs_and_scores]
    scores = reranker.predict(pairs)
    reranked = sorted(zip(scores, docs_and_scores), key=lambda x: x[0], reverse=True)
    import numpy as np
    return [(doc, float(1 / (1 + np.exp(-score)))) for score, (doc, _) in reranked]


def rerank_docs(
    question: str, docs_and_scores: list[tuple[Document, float]]
) -> list[tuple[Document, float]]:
    """Rerank docs using Cohere API, with local cross-encoder fallback."""
    if not RERANKER_ENABLED or not docs_and_scores:
        return docs_and_scores
    import logging
    logger = logging.getLogger(__name__)
    # Try Cohere first
    if COHERE_API_KEY:
        try:
            return _rerank_cohere(question, docs_and_scores)
        except Exception as e:
            logger.warning(f"Cohere rerank failed, using fallback: {e}")
    # Fallback to local cross-encoder
    return _rerank_fallback(question, docs_and_scores)


# Previous prompt versions — kept for benchmark reference
# SYSTEM_PROMPT = """You are a PostgreSQL expert assistant.

# RULES (very important):
# 1) Answer ONLY using the excerpts provided in the sources below.
# 2) You may refer to the conversation history to understand context and follow-up questions,
#    but never invent information that is not in the provided sources.
# 3) If the excerpts are not relevant, say: "I'm sorry, but the available documentation doesn't cover this topic."
# 4) If the question is completely off-topic (not about databases/PostgreSQL), redirect politely.
# 5) Do NOT include inline citations like [Chunk X] in your answer. Sources are displayed separately to the user.
# 6) Keep your answer concise (max 150 words). Start with a direct answer, add a SQL example if relevant.
# 7) If the question is ambiguous, ask 1-2 clarifying questions but still provide a generic answer.
# """

# FOLLOW_UP_SYSTEM_PROMPT = """You are a PostgreSQL expert assistant engaged in an ongoing conversation.

# The user's follow-up question did not match any new documentation excerpts.
# Based solely on the conversation history above, please:
# - Answer the follow-up (e.g., provide more examples, clarify, expand on a point already made).
# - Stay strictly on-topic about PostgreSQL.
# - Do not invent facts beyond what was already discussed.
# - If you truly cannot answer without new documentation, ask the user to be more specific.
# - Keep your answer concise (max 150 words).
# """

# --- Prompt v2 (strict documentation dump) ---
# SYSTEM_PROMPT = """You are a PostgreSQL documentation assistant.
#
# You must answer using ONLY the provided documentation excerpts.
#
# Rules:
# 1) Use only the information explicitly supported by the provided excerpts.
# 2) Do not use prior knowledge, assumptions, or general PostgreSQL knowledge.
# 3) If the answer is not clearly supported by the excerpts, say exactly:
#    "I'm sorry, but the available documentation doesn't cover this topic."
# 4) Do not add extra background, explanations, or best practices unless they are explicitly stated in the excerpts.
# 5) Do not invent examples. Only include an SQL example if one is directly supported by the excerpts.
# 6) Keep the answer concise and factual.
# 7) Start with a direct answer.
# 8) If the question is ambiguous, ask a short clarifying question instead of guessing.
# 9) Do not mention chunk numbers, citations, or internal retrieval details.
# 10) Do not combine information from conversation history unless it is consistent with the provided excerpts.
#
# Preferred style:
# - short
# - precise
# - documentation-grounded
# - no unnecessary introduction
# """
#
# FOLLOW_UP_SYSTEM_PROMPT = """You are a PostgreSQL documentation assistant continuing an existing conversation.
#
# No new documentation excerpts were retrieved for this follow-up.
#
# Rules:
# 1) Answer only from the existing conversation history.
# 2) Do not introduce new PostgreSQL facts that were not already stated in the conversation.
# 3) If the follow-up requires documentation that is not available in the conversation, say:
#    "I'm sorry, but I need more specific documentation context to answer that."
# 4) Keep the answer concise and factual.
# 5) If the user asks for clarification, rephrase or summarize what was already said.
# 6) If the follow-up is ambiguous, ask a short clarifying question instead of guessing.
# 7) Do not add extra examples unless they were already discussed.
#
# Preferred style:
# - short
# - precise
# - no speculation
# """

# --- Prompt v3 (practical, adaptive) ---
SYSTEM_PROMPT = """You are a PostgreSQL expert assistant that helps users by explaining concepts from the official documentation in a clear, practical way.

Your knowledge base is the provided documentation excerpts. Use them as your source of truth.

Rules:
1) You ONLY answer questions about PostgreSQL and databases. If the question is off-topic (weather, sports, general knowledge, etc.), say:
   "I'm a PostgreSQL documentation assistant — I can only help with PostgreSQL-related questions."
2) Base your answers on the provided excerpts. Do not invent facts or features not covered by the excerpts.
3) If the excerpts don't cover the topic, say:
   "I'm sorry, but the available documentation doesn't cover this topic."
4) You ARE allowed to reorganize, simplify, and explain the information in your own words to make it easier to understand.
5) Adapt your explanation to the user's apparent level. If the question is basic, give a straightforward step-by-step answer. If the question is advanced, be more technical.
6) When practical steps are involved, present them as a clear numbered list of what to do, not a dump of every option.
7) Include SQL or shell examples only when they help illustrate the answer. You may simplify examples from the excerpts.
8) Start with a direct answer, then add details only if they help.
9) If the question is ambiguous, ask a short clarifying question.
10) Do not mention chunk numbers, citations, or internal retrieval details.

Preferred style:
- clear and practical
- adapted to the user's level
- concise but not at the expense of clarity
- no unnecessary introduction
"""

FOLLOW_UP_SYSTEM_PROMPT = """You are a PostgreSQL expert assistant continuing an existing conversation.

No new documentation excerpts were retrieved for this follow-up.

Rules:
1) You ONLY answer questions about PostgreSQL and databases. If the question is off-topic (weather, sports, general knowledge, etc.), say:
   "I'm a PostgreSQL documentation assistant — I can only help with PostgreSQL-related questions."
2) Answer using the conversation history. Do not invent new PostgreSQL facts.
3) If the user didn't understand, explain differently — use simpler words, analogies, or a concrete example. Do NOT repeat the same answer.
4) If the follow-up requires documentation not available in the conversation, say:
   "I'm sorry, but I need more specific documentation context to answer that."
5) If the follow-up is ambiguous, ask a short clarifying question.

Preferred style:
- clear and practical
- if the user is confused, simplify rather than repeat
- no speculation
"""

embedding = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
vectorstore = PGVector(
    collection_name=COLLECTION_NAME,
    connection=DATABASE_URL,
    embeddings=embedding,
    use_jsonb=True,
)
llm = ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, reasoning={"effort": "medium"})
llm_streaming = ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, streaming=True)

# Cache LLM instances per model to avoid recreating them
_llm_cache: dict[str, ChatOpenAI] = {}


def _get_streaming_llm(model: str | None = None) -> ChatOpenAI:
    """Return a streaming ChatOpenAI instance for the requested model."""
    model = model or LLM_MODEL
    with _client_lock:
        if model not in _llm_cache:
            _llm_cache[model] = ChatOpenAI(model=model, api_key=OPENAI_API_KEY, streaming=True)
    return _llm_cache[model]


def get_embedding_score(question: QuestionRequest, top_k: int = 5) -> tuple[list[tuple[Document, float]], bool]:
    """Return (docs_and_scores, is_reranked) tuple."""
    import time
    fetch_k = top_k * 4 if RERANKER_ENABLED else top_k

    t0 = time.time()
    docs_and_scores = vectorstore.similarity_search_with_relevance_scores(question.message, fetch_k)
    import logging; logging.getLogger(__name__).info(f"[TIMING] embedding+vectorsearch: {int((time.time()-t0)*1000)}ms")

    is_reranked = False
    if RERANKER_ENABLED:
        t1 = time.time()
        docs_and_scores = rerank_docs(question.message, docs_and_scores)[:top_k]
        is_reranked = True
        logging.getLogger(__name__).info(f"[TIMING] reranking: {int((time.time()-t1)*1000)}ms")

    return docs_and_scores, is_reranked


def _select_valid_docs_and_sources(
    docs_and_scores: list[tuple[Document, float]],
    is_reranked: bool = False,
) -> tuple[list[Document], list[str]]:
    """Filter retrieved docs and deduplicate source URLs.

    When reranked, uses adaptive filtering: keeps chunks whose score is
    at least RERANKER_SCORE_RATIO * best_score (and above RERANKER_THRESHOLD).
    Always keeps at least the top chunk if it passes the absolute threshold.
    For raw embedding scores, uses SIMILARITY_THRESHOLD as before.
    """
    if not docs_and_scores:
        return [], []

    valid_docs: list[Document] = []
    sources: set[str] = set()

    if is_reranked:
        best_score = docs_and_scores[0][1]
        relative_threshold = best_score * RERANKER_SCORE_RATIO
        threshold = max(relative_threshold, RERANKER_THRESHOLD)
    else:
        threshold = SIMILARITY_THRESHOLD

    for doc, score in docs_and_scores:
        if score >= threshold:
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
            f"[Chunk {i}] {doc.metadata.get('raw_content', doc.page_content)}\n"
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
    is_reranked: bool | None = None,
) -> AnswerResponse:
    if docs_and_scores is None:
        docs_and_scores, is_reranked = get_embedding_score(question)
    if is_reranked is None:
        is_reranked = RERANKER_ENABLED
    valid_docs, sources = _select_valid_docs_and_sources(docs_and_scores, is_reranked=is_reranked)

    if not valid_docs and question.history:
        messages = _build_follow_up_messages(question.message, question.history)
        import time, logging
        t = time.time()
        resp = llm.invoke(messages)
        logging.getLogger(__name__).info(f"[TIMING] llm.invoke (follow-up): {int((time.time()-t)*1000)}ms")
        answer = resp.content if isinstance(resp.content, str) else next((b["text"] for b in resp.content if isinstance(b, dict) and b.get("type") == "text"), "")
        return AnswerResponse(answer=answer, sources=[])

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
    answer = resp.content if isinstance(resp.content, str) else next((b["text"] for b in resp.content if isinstance(b, dict) and b.get("type") == "text"), "")
    return AnswerResponse(answer=answer, sources=sources)


def stream_answer(question: QuestionRequest):
    """Generator that yields SSE events: token chunks, then sources + latency."""
    import time, logging, json
    logger = logging.getLogger(__name__)

    t_start = time.time()
    docs_and_scores, is_reranked = get_embedding_score(question)
    valid_docs, sources = _select_valid_docs_and_sources(docs_and_scores, is_reranked=is_reranked)

    if not valid_docs and question.history:
        messages = _build_follow_up_messages(question.message, question.history)
        sources = []
    elif not valid_docs:
        no_match = (
            "I couldn't find relevant PostgreSQL documentation for this question. "
            "Try being more specific by mentioning a command, feature, or PostgreSQL concept."
        )
        yield f"data: {json.dumps({'type': 'token', 'content': no_match})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'sources': [], 'latency_ms': int((time.time() - t_start) * 1000)})}\n\n"
        return
    else:
        for doc, score in docs_and_scores[:len(valid_docs)]:
            logger.info(f"  [SOURCE] score={score:.3f} | {doc.metadata.get('source', '?')}")
        messages = _build_rag_messages(valid_docs, question.message, question.history)

    streaming_llm = _get_streaming_llm(question.model)
    for chunk in streaming_llm.stream(messages):
        # With reasoning models, content can be a string or a list of blocks
        content = chunk.content
        if isinstance(content, str):
            token = content
        elif isinstance(content, list):
            # Extract text blocks only (skip thinking/reasoning blocks)
            token = "".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            token = ""
        if token:
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    latency_ms = int((time.time() - t_start) * 1000)
    logger.info(f"[STREAM] completed in {latency_ms}ms | chunks={len(valid_docs)} | sources={len(sources)}")
    yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'latency_ms': latency_ms})}\n\n"
