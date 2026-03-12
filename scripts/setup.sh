#!/usr/bin/env bash
# Full RAG pipeline setup
# 1. Download PostgreSQL 16.10 docs
# 2. Start PostgreSQL + pgvector via Docker
# 3. Chunk HTML docs into JSON
# 4. Generate embeddings and load into PGVector
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

command -v python3 &>/dev/null || error "python3 not found"
command -v docker  &>/dev/null || error "docker not found"
command -v curl    &>/dev/null || error "curl not found"

if [ ! -f "${ENV_FILE}" ]; then
  error ".env file not found at project root.\nCreate one with:\n  OPENAI_API_KEY=sk-...\n  DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag_postgresql_docs"
fi

# ── 1. Download PostgreSQL sources ──────────────────────────────────────────

if [ -d "${PG_DIR}" ]; then
  info "postgresql-${PG_VERSION}/ already present, skipping download."
else
  info "Downloading PostgreSQL ${PG_VERSION} sources..."
  ARCHIVE="/tmp/postgresql-${PG_VERSION}.tar.gz"
  curl -L "https://ftp.postgresql.org/pub/source/v${PG_VERSION}/postgresql-${PG_VERSION}.tar.gz" -o "${ARCHIVE}"
  info "Extracting..."
  tar -xzf "${ARCHIVE}" -C "${ROOT_DIR}"
  rm "${ARCHIVE}"
  info "Docs available at: postgresql-${PG_VERSION}/doc/src/sgml/html/ (auto-detected by chunk_docs.py)"
fi

# ── 2. Start PostgreSQL + pgvector ──────────────────────────────────────────

info "Starting PostgreSQL + pgvector via Docker..."
docker compose -f "${ROOT_DIR}/backend/docker-compose.yml" up -d

info "Waiting for Postgres to be ready..."
until docker exec rag_postgres pg_isready -U postgres &>/dev/null; do
  sleep 1
done
info "Postgres is ready."

# ── 3. Install Python dependencies ──────────────────────────────────────────

info "Installing Python dependencies..."
pip install -q -r "${ROOT_DIR}/backend/requirements.txt"
# Extra deps needed by the chunking script
pip install -q beautifulsoup4 markdownify tiktoken

# ── 4. Chunk HTML docs into JSON ─────────────────────────────────────────────

CHUNKS_FILE="${SCRIPT_DIR}/postgres_rag_data_v6_perfect.json"

if [ -f "${CHUNKS_FILE}" ]; then
  warning "Chunks file already exists — skipping chunking step."
  warning "Delete ${CHUNKS_FILE} to re-run."
else
  info "Chunking PostgreSQL HTML docs..."
  cd "${SCRIPT_DIR}"
  python3 chunk_docs.py
  info "Chunks written to scripts/postgres_rag_data_v6_perfect.json"
fi

# ── 5. Generate embeddings → PGVector ───────────────────────────────────────

info "Generating embeddings and loading into PGVector..."
cd "${SCRIPT_DIR}"
python3 generate_embeddings.py

info "Pipeline complete. You can now start the backend:"
info "  cd backend && uvicorn main:app --reload"
