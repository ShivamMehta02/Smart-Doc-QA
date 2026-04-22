# Smart Document Q&A System — TheHireHub.AI Assignment

## 🚀 Overview
A production-grade, asynchronous RAG (Retrieval-Augmented Generation) pipeline built with FastAPI, PostgreSQL, and Celery. This system allows users to upload documents (PDF/DOCX) and ask complex, conversational questions grounded in the document content.

---

## 🏗️ Architecture & Design Decisions

### 1. Asynchronous Document Processing (Celery + Redis)
**Decision:** Document ingestion (parsing, chunking, embedding) is offloaded to a background Celery worker.
**Why?** Large PDFs can take seconds to process. Blocking the API during this time is poor UX. Our system returns a `job_id` immediately, allowing the UI to show a progress bar while the backend handles the heavy lifting.

### 2. Recursive Chunking with Semantic Overlap
**Decision:** We use a recursive character splitter with a chunk size of 600 tokens and 120 tokens overlap.
**Why?** Fixed-size chunking often splits sentences in the middle. Recursive splitting respects paragraph and sentence boundaries. Overlap ensures that context spanning across two chunks is not lost during retrieval.

### 3. Hybrid Re-ranking (Precision Layer)
**Decision:** We retrieve `top-10` candidates via FAISS but re-rank them using a Cross-Encoder before sending the `top-5` to the LLM.
**Why?** Vector similarity (bi-encoders) is fast but can be imprecise. Cross-encoders are much more accurate as they jointly process the query and document text. This "Two-Stage Retrieval" is industry standard for high-quality RAG.

### 4. Hallucination Guard & Confidence Scoring
**Decision:** Every LLM response is validated for word overlap with the source context.
**Why?** LLMs are prone to hallucination. If the overlap is too low or the retrieval similarity score is below `0.45`, the system gracefully returns a "Not found in document" fallback rather than a confident lie.

### 5. Database Choice: PostgreSQL + JSONB
**Decision:** We used PostgreSQL for metadata and conversation history.
**Why?** PostgreSQL offers true async support via `asyncpg` and its JSONB columns are perfect for storing flexible document metadata and chat history without complex join logic.

---

## 🛠️ Setup & Installation

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key

### One-Command Start
1. Clone the repo.
2. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.
3. Run:
   ```bash
   docker-compose up --build
   ```
4. Access the API at: `http://localhost:8000/api/v1`
5. View Interactive Docs: `http://localhost:8000/docs` (if DEBUG=True)

---

## 📡 API Usage (Quick Examples)

### 1. Upload a Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@sample.pdf"
```

### 2. Check Processing Status
```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}/status"
```

### 3. Ask a Question (One-shot)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{doc_id}/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the company policy on remote work?"}'
```

### 4. Conversational Chat
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{doc_id}/chat" \
     -H "Content-Type: application/json" \
     -d '{"question": "Tell me more about the benefits.", "conversation_id": "optional-id"}'
```

---

## 🛡️ Failure Handling
- **OpenAI Down?** The system uses `tenacity` for exponential backoff retries.
- **Corrupt File?** Custom `CorruptFileError` exception returns a clean 422 error to the user.
- **No Answer Found?** The `validation_service` detects low-confidence hits and prevents hallucination.
