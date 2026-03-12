#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Next.js) in parallel.
# Usage: ./scripts/start.sh
#
# Logs:
#   /tmp/rag_backend.log
#   /tmp/rag_frontend.log

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[start]${NC} $1"; }

cleanup() {
  info "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ── Backend ─────────────────────────────────────────────────────────────────

info "Starting FastAPI backend on http://localhost:8000"
cd "${ROOT_DIR}/backend"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 \
  > /tmp/rag_backend.log 2>&1 &
BACKEND_PID=$!

# ── Frontend ─────────────────────────────────────────────────────────────────

info "Starting Next.js frontend on http://localhost:3000"
cd "${ROOT_DIR}/frontend"
npm run dev > /tmp/rag_frontend.log 2>&1 &
FRONTEND_PID=$!

# ── Stream logs ──────────────────────────────────────────────────────────────

info "Both services running. Press Ctrl+C to stop."
echo -e "${YELLOW}Backend logs:${NC}  tail -f /tmp/rag_backend.log"
echo -e "${YELLOW}Frontend logs:${NC} tail -f /tmp/rag_frontend.log"
echo ""

tail -f /tmp/rag_backend.log &
tail -f /tmp/rag_frontend.log &

wait "$BACKEND_PID" "$FRONTEND_PID"
