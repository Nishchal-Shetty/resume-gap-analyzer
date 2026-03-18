## Stack
- Backend: FastAPI + Python 3.11, runs on port 8000
- Frontend: React + Vite + Tailwind, runs on port 5173
- LLM: Anthropic API (claude-sonnet-4-6), tool use pattern

## Commands
- cd backend && uvicorn main:app --reload → start backend
- cd frontend && npm run dev → start frontend

## Key files
- backend/analyzer.py → all LLM logic lives here
- backend/scraper.py → PDF and URL parsing

## Conventions
- All LLM calls go through analyzer.py, never inline in routes
- Return consistent JSON shape from all /analyze/* endpoints
