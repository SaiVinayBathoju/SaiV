# SaiV — AI Learning Assistant

SaiV is an AI-powered learning assistant that turns YouTube videos and PDFs into flashcards, quizzes, and a context-aware chat. It uses **Retrieval-Augmented Generation (RAG)** to provide grounded, accurate answers from your learning material.

> **For evaluators:** See **[EVALUATION.md](EVALUATION.md)** for documentation aligned to the evaluation criteria (Architecture, AI Integration, RAG, Flashcards & Quiz, UI/UX, Error Handling, Documentation).

## Features

- **Content Processing**: Paste a YouTube URL or upload a PDF
- **Flashcards**: Auto-generate 10–15 flashcards from key concepts
- **Quizzes**: Generate 5–10 multiple-choice questions with explanations
- **RAG Chat**: Ask questions and get answers grounded in your material
- **Streaming**: Real-time streaming responses in the chat UI

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), TailwindCSS, TypeScript |
| Backend | FastAPI (Python), async |
| Database | Supabase (PostgreSQL + pgvector) |
| AI | OpenAI (GPT-4o-mini, text-embedding-3-small) and/or Google Gemini (gemini-2.5-flash, gemini-embedding-001) |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Next.js UI    │────▶│  FastAPI Backend │────▶│   Supabase      │
│   (Port 3000)   │     │  (Port 8000)     │     │   Postgres      │
└─────────────────┘     └────────┬─────────┘     │   + pgvector    │
                                 │               └─────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ OpenAI / Gemini  │
                        │ (LLM + Embed)    │
                        └──────────────────┘
```

### RAG Pipeline

1. **Ingest**: YouTube transcript or PDF text is extracted and cleaned.
2. **Chunk**: Text is split into overlapping chunks (~512 chars).
3. **Embed**: Chunks are embedded with `text-embedding-3-small`.
4. **Store**: Chunks and embeddings are stored in Supabase pgvector.
5. **Retrieve**: For each chat query, the top-k similar chunks are retrieved.
6. **Generate**: GPT-4 answers using retrieved context; says "I'm not sure" if the answer isn't in the context.

## Setup

### Prerequisites

- Node.js 18+
- Python 3.10+
- Supabase account
- OpenAI API key

### 1. Database (Supabase)

1. Create a project at [supabase.com](https://supabase.com).
2. In the SQL Editor, run the schema in `database/schema.sql`.
3. In Settings → API, copy `Project URL` and `service_role` key.

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with Supabase URL, service key, and OpenAI API key

uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 4. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key (*or use `GEMINI_API_KEY` for free tier) |
| `GEMINI_API_KEY` | No | Google Gemini (free at aistudio.google.com); used for chat/flashcards/quiz and as fallback |
| `EMBEDDING_FALLBACK_TO_LOCAL` | No | Set to `false` on Render/cloud; local fallback needs `fastembed`, which requires Rust to build |
| `NEXT_PUBLIC_API_URL` | No | Backend URL (default: proxied via Next.js) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/process-video` | Process YouTube URL, return `document_id` |
| POST | `/process-pdf` | Upload PDF (multipart), return `document_id` |
| POST | `/generate-flashcards` | Generate flashcards for `document_id` |
| POST | `/generate-quiz` | Generate quiz for `document_id` |
| POST | `/chat` | Stream RAG chat (SSE) for `document_id` |

## Project Structure

```
SaiV/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # API endpoints
│   │   ├── services/       # YouTube, PDF, AI, RAG
│   │   ├── schemas/        # Pydantic models
│   │   ├── utils/          # Chunking, logging
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── app/                # Next.js App Router
│   ├── components/
│   ├── lib/api.ts          # API client
│   └── package.json
├── database/
│   └── schema.sql
└── README.md
```

## Deploying to Vercel (frontend only)

1. In the [Vercel Dashboard](https://vercel.com), import your repo and create a project.
2. **Root Directory:** In **Project Settings → General**, set **Root Directory** to `frontend`. (If you leave it blank, the root `vercel.json` will use `outputDirectory: "frontend/.next"` so the build can succeed.)
3. **Output Directory:** In **Project Settings → Build & Development Settings**, set **Output Directory** to `.next` (or leave it **empty**). If it is set to `public`, you will get "No Output Directory named 'public' found" — clear it or change it to `.next`.
4. Add environment variables (e.g. `NEXT_PUBLIC_API_URL` if your backend is hosted elsewhere).
5. Deploy. The backend (FastAPI) must be deployed separately (e.g. Railway, Render, or a VPS).

## Deploying backend to Render

1. Create a **Web Service**, connect the repo, set **Root Directory** to `backend`.
2. **Build Command:** `pip install --no-cache-dir -r requirements.txt`
3. **Start Command:** `python run.py` (uses `backend/run.py` so the app loads correctly and logs any startup error).
4. Set env vars (Supabase, `OPENAI_API_KEY` and/or `GEMINI_API_KEY`, `EMBEDDING_FALLBACK_TO_LOCAL=false`).
5. If you see `py-rust-stemmers` build errors: **Settings → Clear build cache & deploy**.

Alternatively, use the repo-root `render.yaml` Blueprint (same build/start commands).

## Error Handling

- **Invalid YouTube URL**: Returns a clear validation message.
- **Empty transcript**: Handles videos without captions.
- **Unsupported PDF**: Handles scanned/image PDFs and encryption.
- **LLM timeouts**: Logged and surfaced as user-friendly errors.
- **RAG no context**: Assistant says it’s unsure instead of guessing.

## License

MIT
