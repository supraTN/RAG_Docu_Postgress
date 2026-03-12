@echo off
:: Start backend (FastAPI) and frontend (Next.js) in separate windows.
:: Usage: double-click or run from project root: scripts\start.bat

set ROOT=%~dp0..

echo [start] Starting FastAPI backend on http://localhost:8000
start "RAG Backend" cmd /k "cd /d %ROOT%\backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo [start] Starting Next.js frontend on http://localhost:3000
start "RAG Frontend" cmd /k "cd /d %ROOT%\frontend && npm run dev"

echo.
echo Both services starting in separate windows.
echo Close those windows to stop the services.
