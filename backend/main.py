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
