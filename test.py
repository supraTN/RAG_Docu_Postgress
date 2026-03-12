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

# pdf 6:
import os
import sys
import glob
import json
import re
import tiktoken
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as md
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Set INPUT_DIR via env var or first CLI argument.
# Auto-detects any postgresql-*/ folder at the project root if not specified.
def _find_pg_docs_dir() -> str:
    root = os.path.join(os.path.dirname(__file__), "..")
    candidates = sorted(glob.glob(os.path.join(root, "postgresql-*", "doc", "src", "sgml", "html")))
    if not candidates:
        raise FileNotFoundError(
            "No postgresql-*/ folder found at project root.\n"
            "Run scripts/setup.sh (or setup.bat) first, or set POSTGRES_DOCS_DIR."
        )
    return candidates[-1]  # pick latest version if multiple

INPUT_DIR = os.getenv("POSTGRES_DOCS_DIR") or _find_pg_docs_dir()
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "postgres_rag_data_v6_perfect.json")
TARGET_CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
MIN_TOKEN_THRESHOLD = 20

SPLIT_MARKER = "SEMANTICSPLITMARKER"
CODE_MARKER_TEMPLATE = "CODEBLOCKX{}X"

encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(encoder.encode(text))

def protect_code_blocks(soup, code_store):
    tags = soup.find_all(['pre', 'programlisting'])
    for i, pre_tag in enumerate(tags):
        code_content = pre_tag.get_text()
        placeholder = CODE_MARKER_TEMPLATE.format(i)
        code_store[placeholder] = code_content.strip()
        # Surround with whitespace so the splitter can cut around the placeholder
        pre_tag.replace_with(NavigableString(f"\n\n {placeholder} \n\n"))

def inject_semantic_splits(soup):
    for admo in soup.select('div.tip, div.note, div.warning'):
        if admo.next_sibling:
            admo.insert_after(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))
        else:
            admo.parent.append(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))

    for dl in soup.select('dl, div.variablelist, div.sect2'):
        dl.insert_before(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))

def finalize_text(text):
    text = re.sub(r'\[#\]\(#.*?\)', '', text)
    text = text.replace(SPLIT_MARKER, "")
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def process_files():
    final_data = []
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-3.5-turbo",
        chunk_size=TARGET_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
    )

    if not os.path.exists(INPUT_DIR):
        print(f"Error: directory {INPUT_DIR} not found.")
        return

    files = glob.glob(os.path.join(INPUT_DIR, "*.html"))
    print(f"Processing {len(files)} HTML files...")

    for file_path in files:
        filename = os.path.basename(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_html = f.read()

        soup = BeautifulSoup(raw_html, 'html.parser')
        
        for noise in soup.select('div.navheader, div.navfooter, div.toc, script, style'):
            noise.decompose()
        
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "Unknown"

        code_store = {}
        protect_code_blocks(soup, code_store)
        inject_semantic_splits(soup)

        content_div = soup.find('div', id='docContent') or soup.find('body')
        if not content_div: continue
        
        md_text = md(str(content_div), heading_style="ATX", newline_style="BACKSLASH", code_language="")

        # Découpage sémantique majeur
        raw_chunks = re.split(r"\s*" + re.escape(SPLIT_MARKER) + r"\s*", md_text)

        chunk_counter = 0

        for block in raw_chunks:
            block = block.strip()
            if not block: continue

            sub_chunks = text_splitter.split_text(block)

            for sub in sub_chunks:
                if "CODEBLOCKX" in sub:
                    def restore_code_match(match):
                        key = match.group(0)
                        code_content = code_store.get(key.strip(), "")
                        return f"\n```sql\n{code_content}\n```\n"

                    sub = re.sub(r"CODEBLOCKX\d+X", restore_code_match, sub)
                    # Chunks containing large code blocks may exceed TARGET_CHUNK_SIZE — expected.

                cleaned_content = finalize_text(sub)

                token_count = count_tokens(cleaned_content)
                if token_count < MIN_TOKEN_THRESHOLD:
                    continue

                final_data.append({
                    "id": f"{filename}_{chunk_counter}",
                    "source": filename,
                    "title": title,
                    "content": cleaned_content,
                    "token_count": token_count,
                    "type": "text_block"
                })
                chunk_counter += 1

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"Done. {len(final_data)} chunks written to {OUTPUT_FILE}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        INPUT_DIR = sys.argv[1]
    process_files()

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
# main.py:
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import AuthenticationError, RateLimitError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from models import AnswerResponse, QuestionRequest
import logging
import time
import os
import rag_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if rag_service.RERANKER_ENABLED:
        rag_service._get_reranker()
        logger.info("Reranker preloaded")
    yield


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="PostgreSQL RAG API",
    description="Retrieval-Augmented Generation API for PostgreSQL documentation.",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
@limiter.limit("15/minute")
def ask(request: Request, question: QuestionRequest) -> AnswerResponse:
    logger.info(f"Question received: {question.message[:100]}...")

    try:
        start_time = time.time()
        result = rag_service.generate_answer_with_score(question)
        result.latency_ms = int((time.time() - start_time) * 1000)

        logger.info(f"Response in {result.latency_ms}ms — {len(result.sources)} sources")
        return result

    except AuthenticationError as e:
        logger.error(f"OpenAI Auth Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Configuration error. Please contact support."
        )

    except RateLimitError as e:
        logger.error(f"OpenAI Rate Limit: {e}")
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again in a moment."
        )

    except Exception as e:
        error_str = str(e).lower()

        if "connection" in error_str or "psycopg" in error_str:
            logger.error(f"Database error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Please try again."
            )

        logger.error(f"Unexpected error: {type(e).__name__} - {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
        )
