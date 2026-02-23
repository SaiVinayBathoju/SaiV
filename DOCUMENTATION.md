# SaiV — Evaluation Documentation

This document supports project evaluation by describing how SaiV meets each criterion. Use it alongside the codebase and [README.md](README.md).

---

## Project Overview

**SaiV** is an AI-powered learning assistant that turns **YouTube videos** and **PDFs** into study tools:

- **Content processing**: YouTube URL or PDF upload → transcript/text extraction, chunking, embedding, and storage.
- **Flashcards**: 10–15 items generated from document content (OpenAI or Gemini).
- **Quizzes**: 5–10 multiple-choice questions with options and explanations.
- **RAG Chat**: Streaming Q&A grounded in the uploaded material via retrieval-augmented generation.

**Tech stack**: Next.js 14 (App Router) + TypeScript + TailwindCSS (frontend); FastAPI + Python (backend); Supabase (PostgreSQL + pgvector); OpenAI and/or Google Gemini for LLM and embeddings.

---

## 1. Architecture & Code Structure 

### High-level layout

- **`backend/`** — FastAPI app: `app/main.py`, `run.py` (Render start), `requirements.txt`, `.env` / `.env.example`
- **`frontend/`** — Next.js App Router: `app/`, `components/`, `lib/api.ts`, Tailwind config
- **`database/`** — `schema.sql` (Supabase/Postgres + pgvector)
- **Root** — `README.md`, `.gitignore`, `render.yaml` (optional deploy)

### Tech stack

| Layer     | Technology |
|----------|------------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, TailwindCSS; Outfit + Source Sans 3; lucide-react |
| Backend  | FastAPI (async), Python 3.10+, uvicorn; Pydantic v2, pydantic-settings; structlog |
| Database | Supabase (PostgreSQL + pgvector); `supabase` Python client |
| AI       | OpenAI (GPT-4o-mini, text-embedding-3-small) and/or Google Gemini (gemini-2.5-flash, gemini-embedding-001) |

### Backend structure

- **Routes** (`backend/app/api/routes/`): `video.py` (YouTube), `pdf.py` (PDF upload), `flashcards.py`, `quiz.py`, `chat.py`. Each exposes an `APIRouter` with prefix and tags; all mounted in `main.py`.
- **Services** (`backend/app/services/`): `youtube.py` (transcript), `pdf_extractor.py` (PDF text), `rag_service.py` (upsert/retrieve), `embeddings.py` (OpenAI/Gemini/local), `ai_service.py` (flashcards, quiz, chat).
- **Schemas** (`backend/app/schemas/responses.py`): `ApiResponse[T]`, `ProcessContentResponse`, `FlashcardItem`, `FlashcardsResponse`, `QuizItem`, `QuizResponse`, `ChatResponse`.
- **Utils** (`backend/app/utils/`): `chunking.py` (sentence-boundary chunking), `logging_config.py`.

### Design patterns

- **Configuration**: Single `Settings` class in `backend/app/config.py` (Pydantic BaseSettings, `.env` loading). `get_settings()` with `@lru_cache` for a cached singleton.
- **Separation of concerns**: Routes → services → Supabase/OpenAI/Gemini; no DI container; services use `get_settings()` and direct client creation where needed (e.g. `rag_service.get_supabase_client()`).

### Key files

| Purpose        | Path |
|----------------|------|
| App entry      | `backend/app/main.py` |
| Config         | `backend/app/config.py` |
| Routes         | `backend/app/api/routes/*.py` |
| AI & RAG       | `backend/app/services/ai_service.py`, `embeddings.py`, `rag_service.py` |
| DB schema      | `database/schema.sql` |

---

## 2. AI Integration Quality 

### Provider model

- **Config** (`backend/app/config.py`): `ai_provider: "openai" | "gemini" | "auto"`. Default `"auto"`: try Gemini first if no OpenAI key; otherwise try OpenAI, then fall back to Gemini on failure.
- **OpenAI**: `openai_model` (e.g. gpt-4o-mini), `embedding_model` (text-embedding-3-small), `embedding_dimensions` (1536).
- **Gemini**: `gemini_model` (gemini-2.5-flash), `gemini_embedding_model` (models/gemini-embedding-001). Embeddings support `output_dimensionality` (768/1536/3072) and are padded/L2-normalized to 1536 when needed.

### Where each provider is used

| Feature       | OpenAI usage | Gemini usage |
|---------------|--------------|--------------|
| Embeddings    | `embeddings.py`: `client.embeddings.create()` (batch 100) | `_embed_gemini_sync()`; fallback when OpenAI key missing or 401/invalid |
| Flashcards    | `ai_service.py`: `_generate_flashcards_openai()` | `_generate_flashcards_gemini()` |
| Quiz          | `ai_service.py`: `_generate_quiz_openai()` | `_generate_quiz_gemini()` (with retry on empty parse) |
| Chat          | `_chat_stream_openai()` (async streaming) | `_chat_stream_gemini()` (sync in executor) |

### AI feature behavior

- **Chat**: RAG-grounded streaming (SSE). Context from `retrieve_context(document_id, query)` is injected into the system message; model instructed to answer only from context and say “I’m not sure” when not in context.
- **Flashcards**: 10–15 items; JSON `[{"question","answer"}]`; content truncated to ~12k chars for the prompt; parsed with fence stripping and array extraction.
- **Quiz**: 5–10 MCQs; JSON with `question`, `options`, `correctAnswer` (normalized to A/B/C/D), `explanation`; robust parsing (markdown fences, truncated output); empty quiz returns 200 with empty list instead of 500.
- **Quota / key errors**: `_raise_if_quota_error()` surfaces user-friendly messages and suggests using `GEMINI_API_KEY` when OpenAI billing/quota fails.

### Key files

- `backend/app/config.py` — provider and model settings  
- `backend/app/services/ai_service.py` — LLM calls for chat, flashcards, quiz  
- `backend/app/services/embeddings.py` — multi-provider embedding pipeline  

---

## 3. RAG Implementation 

### Document ingestion

- **YouTube** (`backend/app/api/routes/video.py`, `backend/app/services/youtube.py`): Extract video ID (youtube.com/watch, embed, youtu.be, etc.) → fetch transcript (youtube-transcript-api with fallbacks; yt-dlp for VTT/SRT) → `clean_text()` from `chunking.py` → `rag_service.upsert_document(..., source_type="youtube")`.
- **PDF** (`backend/app/api/routes/pdf.py`): Multipart upload; validation: `.pdf` extension, non-empty, size ≤ 10MB. `pdf_extractor.extract_text_from_pdf()` (pypdf); `clean_text()` on full text → `upsert_document(..., source_type="pdf")`. Clear errors for empty or unreadable (e.g. scanned) PDFs.

### Chunking

- **`backend/app/utils/chunking.py`**: `chunk_text(text, chunk_size=512, overlap=50)`. Sentence-boundary splitting (`[.!?]\s+|\n+`), overlap by carrying last sentences into next chunk. Config: `max_chunk_size`, `chunk_overlap` in `config.py`.

### Embeddings

- **`backend/app/services/embeddings.py`**: `generate_embeddings(texts)` async. Order: (1) OpenAI if key set (batch 100, `dimensions=1536`); on 401/invalid key or other error, log and continue; (2) Gemini if key set (pad/normalize to 1536); (3) if `embedding_fallback_to_local`, local fastembed (BAAI/bge-small-en-v1.5), padded and L2-normalized to 1536. All vectors stored as 1536-dimensional and L2-normalized for cosine similarity.

### Vector storage and retrieval

- **Schema** (`database/schema.sql`): `document_chunks` with `embedding vector(1536)`, `document_id`, `chunk_index`, `content`, `metadata`. IVFFlat index on `embedding` with `vector_cosine_ops`, lists=100.
- **Upsert**: `rag_service.upsert_document()` → chunk text → `generate_embeddings(chunks)` → insert rows with embeddings.
- **Retrieval**: `rag_service.retrieve_context(document_id, query, top_k)` embeds query via `generate_embeddings([query])`, then Supabase RPC `match_document_chunks(query_embedding, match_document_id, match_count)`. RPC returns chunks with `content` and similarity `1 - (embedding <=> query_embedding)`. If RPC missing, fallback: fetch chunks by `document_id` and take first `top_k` contents. Config: `max_retrieval_chunks` (default 5).

### Context to LLM

- **Chat** (`backend/app/api/routes/chat.py`): `retrieve_context(document_id, last_msg.content)`; if empty, context string set to “No relevant context found.” Context injected into system message: “Answer based ONLY on this context… If not in context, say you're not sure.” Responses streamed via SSE.

### Key files

- `backend/app/services/rag_service.py` — upsert and retrieve  
- `backend/app/services/embeddings.py` — embedding generation  
- `backend/app/utils/chunking.py` — chunking logic  
- `database/schema.sql` — tables and `match_document_chunks` RPC  

---

## 4. Flashcard & Quiz Logic 

### Flashcard generation

- **API**: Same LLM pipeline as chat (OpenAI or Gemini via `ai_service.generate_flashcards(content, document_id)`). Content from `get_document_content(document_id)` (full document text).
- **Prompt**: System: “Expert educational content designer”; 10–15 flashcards; concise answers; no duplicates; return only a valid JSON array `[{"question","answer"}, ...]`. User: “Create flashcards from this content: …”
- **Parsing**: `_parse_json_array()` strips markdown code fences and extracts `[...]`. Route normalizes to `FlashcardItem(question, answer)`, strips blanks, caps at 15; empty list → 500 “Could not generate flashcards.”

### Quiz generation

- **API**: `ai_service.generate_quiz(content, document_id)` (OpenAI or Gemini).
- **Prompt**: System: 5–10 MCQs, 4 options, `correctAnswer` exactly A/B/C/D, include brief explanation; return only raw JSON array with `question`, `options`, `correctAnswer`, `explanation`. User: “Create MCQ quiz from this content: …”
- **Parsing**: Robust JSON parsing (strip fences, extract array between first `[` and last `]` for truncated output). Gemini path has one retry on empty parse.
- **Normalization**: `correctAnswer` → `correct_answer`; `.strip().upper()`. In `backend/app/api/routes/quiz.py`: `valid_letters = ("A","B","C","D")`; if `correct_answer` not in that, set to `"A"`; options list normalized; up to 10 items; skip items with no question or &lt;2 options. Returns 200 with empty list when no valid items instead of 500.

### Validation

- Flashcards: only non-empty question/answer kept; cap 15.
- Quiz: Pydantic `QuizItem` with `options` min_length=2, max_length=6; backend enforces A/B/C/D and skips invalid items.

### Key files

- `backend/app/services/ai_service.py` — generation and parsing  
- `backend/app/api/routes/flashcards.py`, `backend/app/api/routes/quiz.py` — request/response and normalization  

---

## 5. UI/UX & Responsiveness 

### Pages and components

- **Pages**: `frontend/app/page.tsx` (single client page), `frontend/app/layout.tsx` (metadata, viewport, fonts, gradient orbs).
- **Tabs**: State `activeTab: "flashcards" | "quiz" | "chat"`; tabs: Flashcards, Quiz, Chat; content: `FlashcardsTab`, `QuizTab`, `ChatTab` in `frontend/components/`. Tabs shown only when `documentId` is set.
- **Input**: `InputPanel` — YouTube URL + “Process” button; PDF drag-and-drop or file picker (accept `.pdf`); “Max 10MB • PDF only” hint.

### Responsive design

- **Breakpoints**: Tailwind (sm/md/lg) for padding, font sizes, spacing, min-heights (e.g. `py-12 sm:py-16 md:py-20`).
- **Safe area**: Main padding uses `env(safe-area-inset-*)` in `page.tsx`; viewport in `layout.tsx`: `viewportFit: "cover"`.
- **Touch**: `min-h-[44px]` on primary buttons/inputs; `touch-manipulation` on buttons; `[font-size:16px]` on key inputs to reduce iOS zoom.
- **Layout**: Tabs full-width on mobile (`w-full`), `sm:w-auto sm:inline-flex` on larger; flex-wrap and min-width for progress and nav.

### Styling

- **Tailwind**: Utility-first; custom theme in `tailwind.config.ts`: `saiv` and `accent` palettes, `fontFamily.display`/`body`, animations `fade-in`, `slide-up`, `shimmer`.
- **Glass cards**: `.glass-card` in `globals.css` — semi-transparent background, `backdrop-filter: blur(12px)`, border, shadow.
- **CSS variables**: `--background`, `--foreground`, `--card`, `--border`, `--saiv-*`, `--shadow-card`; dark green theme. Gradient orbs in layout; `min-height: 100dvh` for mobile.

### Key files

- `frontend/app/page.tsx`, `frontend/app/layout.tsx`, `frontend/app/globals.css`  
- `frontend/components/InputPanel.tsx`, `FlashcardsTab.tsx`, `QuizTab.tsx`, `ChatTab.tsx`  
- `frontend/tailwind.config.ts`  

---

## 6. Error Handling 

### API error responses

- **Status codes**: 400 (invalid URL, empty transcript, invalid/empty PDF, file type/size, no document); 404 (document not found for flashcards/quiz); 500 (server/embedding/LLM failures).
- **Messages**: FastAPI `HTTPException(status_code, detail=...)` with user-facing strings (e.g. “Invalid YouTube URL…”, “Transcript is empty…”, “Please upload a PDF file.”, “File too large. Maximum size is 10MB.”, “Document not found. Please process content first.”, “Could not generate flashcards. Please try again.”). Chat stream errors sent in SSE as `data: [ERROR]<message>\n`.
- **Structure**: Standard JSON from FastAPI for non-streaming; frontend uses `detail` or `error` and maps to `ApiResponse.error`.

### Frontend error states

- **Banner**: `page.tsx` — `error` state; when set, `role="alert"` banner with message; cleared on successful `onProcessed`.
- **Callbacks**: `InputPanel`, `FlashcardsTab`, `QuizTab`, `ChatTab` receive `onError(msg)` and call it on API failure or validation (e.g. invalid URL, non-PDF). Chat: on stream error or `[ERROR]` line, `onError(err)` and placeholder message removed.
- **API client** (`frontend/lib/api.ts`): `!res.ok` → `success: false`, `error: json.detail || json.error || "Request failed"`; PDF upload parses `detail` (string or array); `chatStream` calls `onError` on non-ok or `[ERROR]` payload.
- **Proxy** (`frontend/app/api/backend/[...path]/route.ts`): On fetch failure returns 502 with “Backend unreachable…”.

### Validation and fallbacks

- **File type**: Backend checks `filename.lower().endswith(".pdf")`; frontend `accept=".pdf,application/pdf"` and “Please upload a PDF file” if not PDF.
- **Size**: Backend 10MB limit; frontend “Max 10MB • PDF only”.
- **Embedding**: OpenAI → Gemini → (if `embedding_fallback_to_local`) local fastembed; clear `ValueError` when no provider and fallback disabled. LLM: `_raise_if_quota_error()` suggests GEMINI_API_KEY on OpenAI quota/billing errors.
- **RAG**: Chat system prompt instructs model to say it’s not sure when answer isn’t in context; empty context still sent.

### Key files

- `backend/app/api/routes/*.py` — HTTPException and validation  
- `frontend/app/page.tsx`, `frontend/lib/api.ts` — error state and API handling  
- `frontend/app/api/backend/[...path]/route.ts` — proxy error response  

---




