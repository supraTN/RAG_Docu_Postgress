#!/usr/bin/env bash
# Full RAG pipeline setup
# 1. Download PostgreSQL 16.10 docs
# 2. Start PostgreSQL + pgvector via Docker
# 3. Chunk HTML docs into JSON
# 4. Generate embeddings and load into PGVector (skips if already indexed)
#
# Prerequisites: Python 3.10+, Docker, curl
# Usage: ./scripts/setup.sh

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PG_VERSION="16.10"
PG_DIR="${ROOT_DIR}/postgresql-${PG_VERSION}"
SCRIPT_DIR="${ROOT_DIR}/scripts"
ENV_FILE="${ROOT_DIR}/.env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[setup]${NC} $1"; }
warning() { echo -e "${YELLOW}[setup]${NC} $1"; }
error()   { echo -e "${RED}[error]${NC} $1"; exit 1; }

# ── 0. Check prerequisites ──────────────────────────────────────────────────

command -v docker  &>/dev/null || error "docker not found"
command -v curl    &>/dev/null || error "curl not found"

VENV_DIR="${ROOT_DIR}/.venv"
if [ ! -d "${VENV_DIR}" ]; then
  info "No .venv found. Creating project virtualenv..."
  if command -v python &>/dev/null; then
    python -m venv "${VENV_DIR}"
  elif command -v python3 &>/dev/null; then
    python3 -m venv "${VENV_DIR}"
  else
    error "python/python3 not found. Install Python 3.10+ first."
  fi
fi

PYTHON_BIN=""
if [ -x "${VENV_DIR}/bin/python" ]; then
  PYTHON_BIN="${VENV_DIR}/bin/python"
elif [ -f "${VENV_DIR}/Scripts/python.exe" ]; then
  PYTHON_BIN="${VENV_DIR}/Scripts/python.exe"
else
  error "Virtualenv creation failed: no python executable found in ${VENV_DIR}."
fi

if ! "${PYTHON_BIN}" -m pip --version &>/dev/null; then
  warning "pip missing in virtualenv, trying ensurepip..."
  "${PYTHON_BIN}" -m ensurepip --upgrade &>/dev/null || true
fi
"${PYTHON_BIN}" -m pip --version &>/dev/null || error "pip is missing in ${PYTHON_BIN}. Recreate .venv."

if [ ! -f "${ENV_FILE}" ]; then
  error ".env file not found at project root.\nCreate one with:\n  OPENAI_API_KEY=sk-...\n  DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag_postgresql_docs"
fi

# ── 1. Download PostgreSQL sources ──────────────────────────────────────────

if [ -d "${PG_DIR}" ]; then
  info "postgresql-${PG_VERSION}/ already present, skipping download."
else
  info "Downloading PostgreSQL ${PG_VERSION} sources (this may take a few minutes)..."
  ARCHIVE="/tmp/postgresql-${PG_VERSION}.tar.gz"
  curl --progress-bar -L "https://ftp.postgresql.org/pub/source/v${PG_VERSION}/postgresql-${PG_VERSION}.tar.gz" -o "${ARCHIVE}"
  ARCHIVE_SIZE="$(du -h "${ARCHIVE}" 2>/dev/null | cut -f1 || true)"
  if [ -n "${ARCHIVE_SIZE}" ]; then
    info "Download complete (${ARCHIVE_SIZE})."
  else
    info "Download complete."
  fi
  info "Extracting PostgreSQL sources (this can take 30-90s)..."
  tar -xzf "${ARCHIVE}" -C "${ROOT_DIR}"
  info "Extraction complete."
  rm "${ARCHIVE}"
  info "Docs available at: postgresql-${PG_VERSION}/doc/src/sgml/html/ (auto-detected by chunk_docs.py)"
fi

# ── 2. Start PostgreSQL + pgvector ──────────────────────────────────────────

info "Starting PostgreSQL + pgvector via Docker..."
docker compose -f "${ROOT_DIR}/backend/docker-compose.yml" up -d

info "Waiting for Postgres to be ready..."
max_wait=90
elapsed=0
until docker compose -f "${ROOT_DIR}/backend/docker-compose.yml" exec -T postgres pg_isready -U postgres &>/dev/null; do
  sleep 1
  elapsed=$((elapsed + 1))
  if [ "$elapsed" -ge "$max_wait" ]; then
    error "Postgres did not become ready after ${max_wait}s. Check logs with: docker compose -f backend/docker-compose.yml logs postgres"
  fi
done
info "Postgres is ready."

# ── 3. Install Python dependencies ──────────────────────────────────────────

info "Installing Python dependencies..."
"${PYTHON_BIN}" -m pip install -q -r "${ROOT_DIR}/backend/requirements.txt"
# Extra deps needed by the chunking script
"${PYTHON_BIN}" -m pip install -q beautifulsoup4 markdownify tiktoken

# ── 4. Chunk HTML docs into JSON ─────────────────────────────────────────────

CHUNKS_FILE="${SCRIPT_DIR}/postgres_rag_data_v8.json"

if [ -f "${CHUNKS_FILE}" ]; then
  warning "Chunks file already exists — skipping chunking step."
  warning "Delete ${CHUNKS_FILE} to re-run."
else
  info "Chunking PostgreSQL HTML docs..."
  cd "${SCRIPT_DIR}"
  "${PYTHON_BIN}" chunk_docs.py
  info "Chunks written to scripts/postgres_rag_data_v8.json"
fi

# ── 5. Generate embeddings → PGVector ───────────────────────────────────────

info "Generating embeddings and loading into PGVector (skips if collection already has data)..."
cd "${SCRIPT_DIR}"
"${PYTHON_BIN}" generate_embeddings.py

info "Pipeline complete. Start the app with:"
info "  make start   (or: bash scripts/start.sh)"
