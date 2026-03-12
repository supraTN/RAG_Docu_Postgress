@echo off
:: Full RAG pipeline setup
:: 1. Download PostgreSQL 16.10 docs
:: 2. Start PostgreSQL + pgvector via Docker
:: 3. Chunk HTML docs into JSON
:: 4. Generate embeddings and load into PGVector
::
:: Prerequisites: Python 3.10+, Docker, curl
:: Usage: double-click or run from project root: scripts\setup.bat

set ROOT=%~dp0..
set PG_VERSION=16.10
set PG_DIR=%ROOT%\postgresql-%PG_VERSION%
set SCRIPTS_DIR=%ROOT%\scripts
set ENV_FILE=%ROOT%\.env
set CHUNKS_FILE=%SCRIPTS_DIR%\postgres_rag_data_v6_perfect.json

:: ── 0. Check prerequisites ──────────────────────────────────────────────────

where python >nul 2>&1 || (echo [error] python not found & pause & exit /b 1)
where docker >nul 2>&1 || (echo [error] docker not found & pause & exit /b 1)
where curl   >nul 2>&1 || (echo [error] curl not found & pause & exit /b 1)

if not exist "%ENV_FILE%" (
  echo [error] .env file not found at project root.
  echo Create one with:
  echo   OPENAI_API_KEY=sk-...
  echo   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag_postgresql_docs
  pause & exit /b 1
)

:: ── 1. Download PostgreSQL sources ──────────────────────────────────────────

if exist "%PG_DIR%" (
  echo [setup] postgresql-%PG_VERSION%\ already present, skipping download.
) else (
  echo [setup] Downloading PostgreSQL %PG_VERSION% sources...
  curl -L "https://ftp.postgresql.org/pub/source/v%PG_VERSION%/postgresql-%PG_VERSION%.tar.gz" -o "%TEMP%\postgresql-%PG_VERSION%.tar.gz"
  echo [setup] Extracting...
  tar -xzf "%TEMP%\postgresql-%PG_VERSION%.tar.gz" -C "%ROOT%"
  del "%TEMP%\postgresql-%PG_VERSION%.tar.gz"
  echo [setup] Docs available at: postgresql-%PG_VERSION%\doc\src\sgml\html\
)

:: ── 2. Start PostgreSQL + pgvector ──────────────────────────────────────────

echo [setup] Starting PostgreSQL + pgvector via Docker...
docker compose -f "%ROOT%\backend\docker-compose.yml" up -d

echo [setup] Waiting for Postgres to be ready...
:wait_loop
docker exec rag_postgres pg_isready -U postgres >nul 2>&1 && goto pg_ready
timeout /t 1 /nobreak >nul
goto wait_loop
:pg_ready
echo [setup] Postgres is ready.

:: ── 3. Install Python dependencies ──────────────────────────────────────────

echo [setup] Installing Python dependencies...
pip install -q -r "%ROOT%\backend\requirements.txt"
pip install -q beautifulsoup4 markdownify tiktoken

:: ── 4. Chunk HTML docs into JSON ─────────────────────────────────────────────

if exist "%CHUNKS_FILE%" (
  echo [setup] Chunks file already exists - skipping chunking step.
  echo [setup] Delete %CHUNKS_FILE% to re-run.
) else (
  echo [setup] Chunking PostgreSQL HTML docs...
  cd /d "%SCRIPTS_DIR%"
  python chunk_docs.py
  echo [setup] Chunks written to scripts\postgres_rag_data_v6_perfect.json
)

:: ── 5. Generate embeddings → PGVector ───────────────────────────────────────

echo [setup] Generating embeddings and loading into PGVector...
cd /d "%SCRIPTS_DIR%"
python generate_embeddings.py

echo.
echo [setup] Pipeline complete. You can now start the app:
echo   scripts\start.bat
pause
