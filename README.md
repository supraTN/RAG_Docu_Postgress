# PostgreSQL Docs Assistant — RAG Chatbot

A full-stack **Retrieval-Augmented Generation (RAG)** application that answers questions about the official PostgreSQL 16 documentation using semantic search and a large language model.

> Ask anything about PostgreSQL and get precise, source-backed answers in seconds.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |
| **Backend** | FastAPI, Python 3.11+ |
| **LLM** | OpenAI gpt-4.1-mini |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Vector Store** | PostgreSQL 16 + pgvector |
| **ORM / RAG** | LangChain (langchain-postgres, langchain-openai) |

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
1. User question → embedded with `text-embedding-3-small`
2. Top-10 candidates retrieved from pgvector, reranked with a cross-encoder, top-5 kept
3. Chunks above the similarity threshold + conversation history → sent to `gpt-4.1-mini`
4. Answer + source URLs returned to the frontend

---

## Project Structure

```
.
├── backend/
│   ├── main.py            # FastAPI app, routing, rate limiting
│   ├── rag_service.py     # RAG pipeline (embedding, retrieval, reranking, LLM)
│   ├── models.py          # Pydantic request/response models
│   ├── requirements.txt
│   └── docker-compose.yml # PostgreSQL + pgvector setup
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   ├── hooks/useChat.ts          # Chat state & API logic
│   │   ├── lib/utils.ts              # cn() utility
│   │   ├── types.ts                  # Shared types & constants
│   │   └── component/
│   │       ├── ChatInterface.tsx     # Main layout
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
│   ├── setup.sh / setup.bat          # Full pipeline (docs → chunks → embeddings)
│   ├── start.sh  / start.bat         # Start frontend + backend
│   ├── chunk_docs.py                 # HTML docs → chunked JSON
│   └── generate_embeddings.py        # JSON chunks → pgvector
│
├── benchmark/
│   ├── generate_dataset.py   # chunk → LLM → (question, answer, source_chunk_id)
│   ├── evaluate.py           # Hit Rate, MRR, Faithfulness, Answer Relevancy
│   └── requirements.txt
│
├── .env.example
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL)
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Environment Variables

```bash
cp .env.example .env
# Edit .env with your OpenAI API key and database credentials

cp frontend/.env.local.example frontend/.env.local
# Edit .env.local if your backend runs on a different port
```

### 2. Run the setup pipeline

The setup script handles everything: downloading the PostgreSQL docs, starting the database, installing dependencies, chunking and indexing.

**Linux / macOS / Git Bash:**
```bash
bash scripts/setup.sh
```

**Windows:**
```bat
scripts\setup.bat
```

### 3. Start the app

**Linux / macOS / Git Bash:**
```bash
bash scripts/start.sh
```

**Windows:**
```bat
scripts\start.bat
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

---

## Configuration

All runtime settings are controlled via environment variables — no hardcoded values.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `DATABASE_URL` | — | PostgreSQL connection string (required) |
| `LLM_MODEL` | `gpt-4.1-mini` | Chat completion model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `COLLECTION_NAME` | `postgres_docs_v6` | pgvector collection name |
| `SIMILARITY_THRESHOLD` | `0.4` | Minimum cosine similarity to include a chunk |
| `RERANKER_ENABLED` | `true` | Enable cross-encoder reranking |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker model |
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

### `GET /health`

Returns `{ "status": "ok" }`.

---

## RAG Evaluation

The `benchmark/` folder contains a two-step evaluation pipeline that measures **retrieval** and **generation** independently.

### Why two separate axes?

| Axis | What it measures | Cost |
|---|---|---|
| **Retrieval** | Did the system find the right documentation chunk? | Free (no LLM) |
| **Generation** | Is the answer faithful and relevant given the chunks? | OpenAI API |

### Metrics

| Metric | Axis | Description |
|---|---|---|
| **Hit Rate @k** | Retrieval | % of questions where the source chunk is in top-k results |
| **MRR** | Retrieval | Mean Reciprocal Rank — how high does the source chunk rank on average? |
| **Boundary Hit Rate** | Retrieval | Among misses, % where an adjacent chunk was retrieved — indicates a chunking boundary problem rather than a retrieval problem |
| **Faithfulness** | Generation | Answer is grounded in the retrieved chunks (no hallucination) |
| **Answer Relevancy** | Generation | Answer actually addresses the question |

### Dataset generation methodology

Ground truths are generated **from documentation chunks**, not from the retriever:

```
chunk (from indexed docs) → LLM → { question, expected_answer, source_chunk_id }
```

This avoids the circular bias of generating ground truths with the same retriever you are testing.
Each entry includes a `source_url` for manual verification.

### Run the evaluation

```bash
cd benchmark
pip install -r requirements.txt

# Step 1 — Generate evaluation dataset (run once)
python generate_dataset.py                  # 40 questions, auto-validates
python generate_dataset.py --n 80           # more questions
python generate_dataset.py --chunk-report   # inspect chunk quality only

# Step 2 — Retrieval-only (fast, free)
python evaluate.py --retrieval-only

# Step 3 — Full evaluation with RAGAS (retrieval + generation)
python evaluate.py
python evaluate.py --limit 10               # quick test on first 10 questions
python evaluate.py --skip-answer-relevancy  # faithfulness only (cheaper)
```

### Example output

```
════════════════════════════════════════════════════════════════════════════
  RAG EVALUATION REPORT — PostgreSQL Docs Assistant
  Questions : 40   |   Total time : 187.4s   |   2025-03-09 14:22
════════════════════════════════════════════════════════════════════════════

  ── RETRIEVAL ────────────────────────────────────────────────────────────
  Hit Rate @1          Source chunk ranked 1st          0.625  ████████████░░░░░░░░  GOOD
  Hit Rate @3          Source chunk in top 3            0.800  ████████████████░░░░  GOOD
  Hit Rate @5          Source chunk in top 5            0.875  █████████████████░░░  GOOD
  MRR                  Mean Reciprocal Rank             0.712  ██████████████░░░░░░  GOOD
  Boundary Hit Rate    Misses w/ adjacent chunk found   0.200  ████░░░░░░░░░░░░░░░░  OK

  ── GENERATION (RAGAS) ───────────────────────────────────────────────────
  Faithfulness         Answer grounded in chunks        0.891  ██████████████████░░  GOOD
  Answer Relevancy     Answer addresses the question    0.847  ████████████████░░░░  GOOD
════════════════════════════════════════════════════════════════════════════
```

Results are also saved to `benchmark/evaluation_results.json` for further analysis.

---

## License

MIT
