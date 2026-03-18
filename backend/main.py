from contextlib import asynccontextmanager
import secrets
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

API_KEY = os.getenv("API_KEY")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(_api_key_header)):
    if API_KEY is None:
        return
    if not api_key or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    missing = [v for v in ("OPENAI_API_KEY", "DATABASE_URL") if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    if rag_service.RERANKER_ENABLED:
        if rag_service.COHERE_API_KEY:
            rag_service._get_cohere_client()
            logger.info("Cohere reranker client ready")
        else:
            rag_service._get_fallback_reranker()
            logger.info("Fallback cross-encoder preloaded")
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
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


_health_cache: dict = {"result": None, "expires": 0.0}


@app.get("/health")
@limiter.limit("10/minute")
def health(request: Request):
    now = time.time()
    if _health_cache["result"] and now < _health_cache["expires"]:
        return _health_cache["result"]
    try:
        import psycopg
        conn_str = rag_service.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
        with psycopg.connect(conn_str, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        result = {"status": "ok", "db": "ok"}
        _health_cache["result"] = result
        _health_cache["expires"] = now + 30
        return result
    except Exception as e:
        logger.warning(f"Health check DB probe failed: {type(e).__name__}")
        _health_cache["result"] = None
        raise HTTPException(status_code=503, detail={"status": "degraded", "db": "unreachable"})


@app.post("/ask")
@limiter.limit("15/minute")
def ask(request: Request, question: QuestionRequest, _=Depends(verify_api_key)) -> AnswerResponse:
    logger.info(f"Question received: len={len(question.message)} history={len(question.history)}")

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


@app.post("/ask/stream")
@limiter.limit("15/minute")
def ask_stream(request: Request, question: QuestionRequest, _=Depends(verify_api_key)):
    logger.info(f"[STREAM] Question received: len={len(question.message)} history={len(question.history)}")
    return StreamingResponse(
        rag_service.stream_answer(question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
