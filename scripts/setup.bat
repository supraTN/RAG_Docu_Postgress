@echo off
:: Full RAG pipeline setup
:: 1. Download PostgreSQL 16.10 docs
:: 2. Start PostgreSQL + pgvector via Docker
:: 3. Chunk HTML docs into JSON
:: 4. Generate embeddings and load into PGVector (skips if already indexed)
::
:: Prerequisites: Python 3.10+, Docker, curl
:: Usage: double-click or run from project root: scripts\setup.bat

set ROOT=%~dp0..
set PG_VERSION=16.10
set PG_DIR=%ROOT%\postgresql-%PG_VERSION%
set SCRIPTS_DIR=%ROOT%\scripts
set ENV_FILE=%ROOT%\.env
set CHUNKS_FILE=%SCRIPTS_DIR%\postgres_rag_data_v8.json
set PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe

:: ── 0. Check prerequisites ──────────────────────────────────────────────────

where python >nul 2>&1 || (echo [error] python not found & exit /b 1)
where docker >nul 2>&1 || (echo [error] docker not found & exit /b 1)
where curl   >nul 2>&1 || (echo [error] curl not found & exit /b 1)
if not exist "%PYTHON_EXE%" (
  echo [setup] No .venv found. Creating project virtualenv...
  python -m venv "%ROOT%\.venv" || (echo [error] Failed to create .venv & exit /b 1)
)
"%PYTHON_EXE%" -m pip --version >nul 2>&1 || (echo [error] pip missing in .venv. Recreate virtualenv. & exit /b 1)

if not exist "%ENV_FILE%" (
  echo [error] .env file not found at project root.
  echo Create one with:
  echo   OPENAI_API_KEY=sk-...
  echo   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag_postgresql_docs
  exit /b 1
)

:: ── 1. Download PostgreSQL sources ──────────────────────────────────────────

if exist "%PG_DIR%" (
  echo [setup] postgresql-%PG_VERSION%\ already present, skipping download.
) else (
  echo [setup] Downloading PostgreSQL %PG_VERSION% sources - this may take a few minutes...
  curl --progress-bar -L "https://ftp.postgresql.org/pub/source/v%PG_VERSION%/postgresql-%PG_VERSION%.tar.gz" -o "%TEMP%\postgresql-%PG_VERSION%.tar.gz"
  if errorlevel 1 (echo [error] Download failed. & exit /b 1)
  for %%I in ("%TEMP%\postgresql-%PG_VERSION%.tar.gz") do echo [setup] Download complete: %%~zI bytes.
  echo [setup] Extracting PostgreSQL sources - this can take 30-90s...
  tar -xzf "%TEMP%\postgresql-%PG_VERSION%.tar.gz" -C "%ROOT%"
  if errorlevel 1 (echo [error] Extraction failed. & exit /b 1)
  echo [setup] Extraction complete.
  del "%TEMP%\postgresql-%PG_VERSION%.tar.gz"
  echo [setup] Docs available at: postgresql-%PG_VERSION%\doc\src\sgml\html\
)

:: ── 2. Start PostgreSQL + pgvector ──────────────────────────────────────────

echo [setup] Starting PostgreSQL + pgvector via Docker...
docker compose -f "%ROOT%\backend\docker-compose.yml" up -d

echo [setup] Waiting for Postgres to be ready...
set /a MAX_WAIT=90
set /a ELAPSED=0
:wait_loop
docker compose -f "%ROOT%\backend\docker-compose.yml" exec -T postgres pg_isready -U postgres >nul 2>&1 && goto pg_ready
timeout /t 1 /nobreak >nul
set /a ELAPSED+=1
if %ELAPSED% GEQ %MAX_WAIT% (
  echo [error] Postgres did not become ready after %MAX_WAIT%s.
  echo [error] Check logs with: docker compose -f backend\docker-compose.yml logs postgres
  exit /b 1
)
goto wait_loop
:pg_ready
echo [setup] Postgres is ready.

:: ── 3. Install Python dependencies ──────────────────────────────────────────

echo [setup] Installing Python dependencies...
"%PYTHON_EXE%" -m pip install -r "%ROOT%\backend\requirements.txt" || (echo [error] Failed to install backend requirements. & exit /b 1)
"%PYTHON_EXE%" -m pip install beautifulsoup4 markdownify tiktoken || (echo [error] Failed to install chunking dependencies. & exit /b 1)

:: ── 4. Chunk HTML docs into JSON ─────────────────────────────────────────────

if exist "%CHUNKS_FILE%" (
  echo [setup] Chunks file already exists - skipping chunking step.
  echo [setup] Delete %CHUNKS_FILE% to re-run.
) else (
  echo [setup] Chunking PostgreSQL HTML docs...
  cd /d "%SCRIPTS_DIR%"
  "%PYTHON_EXE%" chunk_docs.py || (echo [error] chunk_docs.py failed. & exit /b 1)
  echo [setup] Chunks written to scripts\postgres_rag_data_v8.json
)

:: ── 5. Generate embeddings → PGVector ───────────────────────────────────────

echo [setup] Generating embeddings and loading into PGVector (skips if collection already has data)...
cd /d "%SCRIPTS_DIR%"
"%PYTHON_EXE%" generate_embeddings.py || (echo [error] generate_embeddings.py failed. & exit /b 1)

echo.
echo [setup] Pipeline complete. You can now start the app:
echo   scripts\start.bat
