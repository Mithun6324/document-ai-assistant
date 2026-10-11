# Document AI Assistant

Production-ready **Document AI Assistant** with RAG over PDF/DOCX documents.

Users can upload documents, ask grounded questions, view citations, and revisit chat history — with multi-user JWT authentication.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React (Vite), Tailwind CSS, React Query, Axios, Lucide |
| Backend | FastAPI, SQLAlchemy, JWT |
| Database | PostgreSQL |
| Vector store | ChromaDB |
| Embeddings | Sentence Transformers `all-MiniLM-L6-v2` |
| Chunking | spaCy `en_core_web_sm` (semantic) |
| LLM | **Gemini 2.0 Flash** (free-tier API key) |
| Extraction | pdfplumber, python-docx |

## Features

- PDF / DOCX upload with drag-and-drop and processing progress
- Duplicate detection (file hash)
- Soft delete
- Semantic chunking (sections → paragraphs → sentences)
- Hybrid retrieval (vector + keyword) + re-ranking
- Similarity threshold gate
- Streaming chat answers (SSE)
- Multi-document / selected-document chat
- Citations + source panel
- Chat history + Markdown export
- Per-document question list
- Suggested questions
- Feedback (thumbs up/down)
- Dark SaaS UI

**Not in v1:** admin panel, email notifications, cloud deployment (local Docker only).

## Quick start

### 1. Prerequisites

- Docker + Docker Compose **or** local Python 3.11+, Node 20+, PostgreSQL 16
- Free Gemini API key: https://aistudio.google.com/apikey

### 2. Configure

```bash
cp backend/.env.example backend/.env
# Set GEMINI_API_KEY in backend/.env

cp frontend/.env.example frontend/.env
```

### 3. Run with Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:5173  
- Backend API: http://localhost:8000  
- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### 4. Local (without full compose)

**Postgres**

```bash
docker compose up -d postgres
```

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

## API overview

| Method | Path | Auth |
|---|---|---|
| POST | `/auth/register` | No |
| POST | `/auth/login` | No |
| GET | `/auth/me` | Yes |
| POST | `/documents/upload` | Yes |
| GET | `/documents` | Yes |
| GET | `/documents/{id}` | Yes |
| GET | `/documents/{id}/status` | Yes |
| GET | `/documents/{id}/questions` | Yes |
| GET | `/documents/{id}/suggested-questions` | Yes |
| DELETE | `/documents/{id}` | Yes |
| POST | `/chat` | Yes |
| POST | `/chat/stream` | Yes |
| GET | `/chat/history` | Yes |
| GET | `/chat/history/{id}` | Yes |
| GET | `/chat/history/{id}/export` | Yes |
| PATCH | `/chat/messages/{id}/feedback` | Yes |
| GET | `/dashboard` | Yes |
| GET | `/health` | No |

See [docs/API.md](docs/API.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Project layout

```
backend/app/
  api/           # routes
  services/      # business logic + LLM providers
  models/        # SQLAlchemy
  schemas/       # Pydantic
  utils/
frontend/src/
  pages/
  components/
  hooks/
  services/
```

## Notes

1. First document upload downloads the embedding model (one-time).
2. Re-ranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) downloads on first query.
3. Without a valid `GEMINI_API_KEY`, chat will return a temporary unavailable message after retrieval.
4. Email notifications are deferred to a later release.
