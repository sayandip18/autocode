AUTOCODE

An AI research assistant with GitHub and web retrieval capabilities.

---

## Architecture

```
User Query (with session_id)
        ↓
FastAPI /query endpoint
        ↓
get_or_create_session → sessions table (Postgres)
        ↓
run_agent(query, session_id)
        ↓
LangChain ReAct agent  ←──── AsyncPostgresSaver (thread_id = session_id)
    │                              restores prior messages from checkpoint DB
    ├── github_fetch
    ├── web_search / web_extract
    └── arxiv_tool
        ↓
save_turn → messages table (Postgres, audit log)
        ↓
Response + session_id
```

---

## Setup

### 1. Environment

Copy and fill in `.env`:

```
OPENAI_API_KEY=...
GITHUB_PAT=...
TAVILY_API_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/autocode
CHECKPOINT_DB_URL=postgresql://user:pass@localhost:5433/checkpoints
```

### 2. Start Postgres

```
docker compose up -d
```

Two Postgres instances are started:
- Port `5432` — application DB (sessions, messages, users)
- Port `5433` — LangGraph checkpoint DB (conversation state)

### 3. Run

```
.\venv\Scripts\uvicorn app.main:app --reload
```

On first startup the app creates ORM tables (port 5432) and LangGraph checkpoint tables (port 5433) automatically.

---

## Observability

[Langfuse](https://cloud.langfuse.com) — configure `LANGFUSE_*` keys in `.env`.
