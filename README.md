# PostgreSQL Docs Assistant — RAG Chatbot

A full-stack **Retrieval-Augmented Generation (RAG)** application that answers questions about the official PostgreSQL 16 documentation using semantic search and a large language model.

> Ask anything about PostgreSQL and get precise, source-backed answers in seconds.

---

## What Makes This Interesting Technically

- **Dual-stage retrieval with graceful fallback** — pgvector cosine similarity retrieves the top-20 candidates, then Cohere Rerank v4 reorders them by semantic relevance. If Cohere is unavailable, a local cross-encoder (`mmarco-mMiniLMv2`) kicks in automatically, so the system works without any external reranking dependency.

- **Adaptive score filtering** — instead of a fixed cutoff, chunks are kept if their reranker score is ≥ `RERANKER_SCORE_RATIO × best_score`. This relative threshold is more robust than a hardcoded value: it adapts to the natural score distribution of each query rather than silently over-filtering or under-filtering.

- **Streaming SSE responses** — the backend streams tokens via Server-Sent Events as soon as the LLM starts generating. The frontend renders the answer progressively with source links and latency appended at the end of the stream.

- **Unbiased evaluation pipeline** — ground-truth Q&A pairs are generated from documentation chunks directly (not from the retriever output), which avoids the circular bias of testing a retriever with data it was implicitly used to generate. Each question is then validated by a second LLM call to confirm it can be answered from a single chunk.

---

## Evaluation Results

Evaluated on 40 natural-language user-style questions and 39 technical questions from the PostgreSQL 16 docs (79 total):

```
════════════════════════════════════════════════════════════════════════════
  RAG EVALUATION REPORT — PostgreSQL Docs Assistant (combined)
════════════════════════════════════════════════════════════════════════════

  ── RETRIEVAL ────────────────────────────────────────────────────────────
  Hit Rate @1          Acceptable chunk ranked 1st          0.937  ██████████████████░░  GOOD
  Hit Rate @3          Acceptable chunk in top 3            1.000  ████████████████████  GOOD
  Hit Rate @5          Acceptable chunk in top 5            1.000  ████████████████████  GOOD
  MRR                  Mean Reciprocal Rank                 0.968  ███████████████████░  GOOD

  ── GENERATION ─────────────────────────────────────────────────────────
  Faithfulness         Answer grounded in chunks            0.935  ██████████████████░░  GOOD
  Correctness          Answer addresses the question        0.996  ███████████████████░  GOOD
  Completeness         Answer covers key points             0.996  ███████████████████░  GOOD
════════════════════════════════════════════════════════════════════════════
```

On technical questions, Hit Rate @1 reaches **100%** (MRR = 1.0, zero misses).
On user-style questions, Correctness and Completeness reach **100%**.

---

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────────────────┐
│   Next.js Frontend  │  HTTP  │         FastAPI Backend              │
│                     │ ──────►│                                      │
│  • Chat UI          │        │  • /ask  (rate-limited: 15 req/min)  │
│  • Markdown render  │◄────── │  • RAG pipeline                      │
│  • Source links     │  JSON  │  • Conversation history (last 10)    │
└─────────────────────┘        └──────────────┬───────────────────────┘
                                              │
                          ┌───────────────────┼──────────────────────┐
                          │                   │                      │
                   ┌──────▼──────┐   ┌────────▼──────┐   ┌──────────▼───────┐
                   │  pgvector   │   │  OpenAI        │   │  OpenAI          │
                   │  (similarity│   │  Embeddings    │   │  Chat LLM        │
                   │   search)   │   │  (query embed) │   │  (answer gen.)   │
                   └─────────────┘   └───────────────┘   └──────────────────┘
```

**RAG Flow:**
1. User question → embedded with `text-embedding-3-large`
2. Top-20 candidates retrieved from pgvector, reranked with Cohere Rerank v4 (cross-encoder fallback), top-5 kept
3. Adaptive filtering: chunks kept if score ≥ `RERANKER_SCORE_RATIO × best_score` (with `RERANKER_THRESHOLD` as absolute floor)
4. Filtered chunks + conversation history → sent to `gpt-5-mini`
5. Answer + source URLs returned to the frontend

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |
| **Backend** | FastAPI, Python 3.11+ |
| **LLM** | OpenAI gpt-5-mini |
| **Embeddings** | OpenAI text-embedding-3-large |
| **Reranking** | Cohere Rerank v4 (+ cross-encoder fallback) |
| **Vector Store** | PostgreSQL 16 + pgvector |
| **ORM / RAG** | LangChain (langchain-postgres, langchain-openai) |

---

## Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+, Docker, an OpenAI API key (Cohere optional).

```bash
# 1. Configure environment
cp .env.example .env                              # add your API keys
cp frontend/.env.local.example frontend/.env.local

# 2. Full setup: downloads PostgreSQL docs, starts DB, embeds everything
make setup        # or: bash scripts/setup.sh

# 3. Start the app
make start        # or: bash scripts/start.sh
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

See `make help` for all available commands.

---

## Project Structure

```
.
├── backend/
│   ├── main.py                    # FastAPI app, routing, rate limiting
│   ├── rag_service.py             # RAG pipeline (embedding, retrieval, reranking, LLM)
│   ├── models.py                  # Pydantic request/response models
│   ├── requirements.txt
│   ├── requirements-dev.txt       # Test & lint dependencies
│   ├── tests/
│   │   ├── test_models.py         # Pydantic model validation tests
│   │   └── test_rag_service.py    # Pure function unit tests
│   └── docker-compose.yml         # PostgreSQL + pgvector setup
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   ├── hooks/useChat.ts       # Chat state & streaming SSE logic
│   │   ├── lib/utils.ts           # cn() utility
│   │   ├── types.ts               # Shared types & constants
│   │   └── component/
│   │       ├── ChatInterface.tsx  # Main layout
│   │       ├── Sidebar.tsx
│   │       ├── ChatInput.tsx
│   │       ├── WelcomeScreen.tsx
│   │       ├── AIMessage.tsx
│   │       ├── UserMessage.tsx
│   │       ├── CodeBlock.tsx
│   │       └── LoadingBubble.tsx
│   └── .env.local.example
│
├── scripts/
│   ├── setup.sh / setup.bat       # Full pipeline (docs → chunks → embeddings)
│   ├── start.sh / start.bat       # Start frontend + backend
│   ├── chunk_docs.py              # HTML docs → chunked JSON
│   └── generate_embeddings.py     # JSON chunks → pgvector
│
├── benchmark/
│   ├── generate_dataset.py        # chunk → LLM → (question, answer, source_chunk_id)
│   ├── evaluate.py                # Hit Rate, MRR, Faithfulness, Correctness, Completeness
│   └── requirements.txt
│
├── Makefile
├── .env.example
└── README.md
```

---

## Configuration

All runtime settings are controlled via environment variables — no hardcoded values.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `DATABASE_URL` | — | PostgreSQL connection string (required) |
| `LLM_MODEL` | `gpt-5-mini` | Chat completion model |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | Embedding model |
| `COLLECTION_NAME` | `postgres_docs_v10` | pgvector collection name |
| `SIMILARITY_THRESHOLD` | `0.4` | Minimum cosine similarity (raw embedding scores) |
| `RERANKER_ENABLED` | `true` | Enable reranking stage |
| `COHERE_API_KEY` | — | Cohere API key (optional — enables Cohere Rerank) |
| `COHERE_RERANK_MODEL` | `rerank-v4.0-fast` | Cohere reranker model |
| `FALLBACK_RERANKER_MODEL` | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | Local cross-encoder fallback |
| `RERANKER_THRESHOLD` | `0.5` | Absolute minimum reranker score |
| `RERANKER_SCORE_RATIO` | `0.8` | Keep chunks scoring ≥ ratio × best score |
| `BASE_DOC_URL` | `https://www.postgresql.org/docs/16/` | Base URL for source links |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL (frontend) |

---

## API

### `POST /ask`

Rate limited to **15 requests/minute** per IP.

**Request:**
```json
{
  "message": "What is MVCC in PostgreSQL?",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "ai", "content": "..." }
  ]
}
```

**Response:**
```json
{
  "answer": "MVCC (Multi-Version Concurrency Control) is...",
  "sources": ["https://www.postgresql.org/docs/16/mvcc.html"],
  "latency_ms": 843
}
```

### `POST /ask/stream`

Same request body as `/ask`. Returns a `text/event-stream` response with two event types:
- `{"type": "token", "content": "..."}` — one token at a time
- `{"type": "done", "sources": [...], "latency_ms": 843}` — final metadata

### `GET /health`

Returns `{"status": "ok", "db": "ok"}` when both the app and database are reachable. Returns HTTP 503 if the database is down.

---

## RAG Evaluation

The `benchmark/` folder contains a two-step evaluation pipeline that measures **retrieval** and **generation** independently.

### Why two separate axes?

| Axis | What it measures | Cost |
|---|---|---|
| **Retrieval** | Did the system find the right documentation chunk? | Free (no LLM) |
| **Generation** | Is the answer faithful, correct, and complete? | OpenAI API |

### Metrics

| Metric | Axis | Description |
|---|---|---|
| **Hit Rate @k** | Retrieval | % of questions where an acceptable chunk appears in top-k results |
| **MRR** | Retrieval | Mean Reciprocal Rank — how high does the correct chunk rank on average? |
| **Boundary Hit Rate** | Retrieval | Among misses, % where an adjacent chunk was retrieved — indicates a chunking boundary problem, not a retrieval problem |
| **Faithfulness** | Generation | Answer is grounded in the retrieved chunks — no hallucination (RAGAS) |
| **Correctness** | Generation | Answer correctly addresses the question (LLM-as-judge) |
| **Completeness** | Generation | Answer covers all key points needed (LLM-as-judge) |

### Dataset generation methodology

Ground truths are generated **from documentation chunks**, not from the retriever:

```
chunk (from indexed docs) → LLM → { question, expected_answer, source_chunk_id }
```

This avoids the circular bias of generating ground truths with the same retriever you are testing.
Each entry is validated by a second LLM call to confirm the question is self-contained and answerable from a single chunk.

### Run the evaluation

```bash
# Install benchmark dependencies
cd benchmark && pip install -r requirements.txt

# Generate evaluation dataset (run once)
python generate_dataset.py                  # 40 questions, auto-validates
python generate_dataset.py --n 80           # more questions

# Retrieval-only evaluation (fast, no API cost)
make eval-retrieval

# Full evaluation (retrieval + generation, uses OpenAI API)
make eval-full
```

Results are saved to `benchmark/evaluation_results_*.json` with per-question scores for detailed analysis.

---

## Known Limitations

- The knowledge base is static (PostgreSQL 16 docs only). New PostgreSQL versions require re-running the ingestion pipeline.
- Conversation history is session-only — there is no persistence across page reloads.
- The fallback cross-encoder runs on CPU, which adds ~2–3s latency compared to Cohere.

---

## License

MIT
