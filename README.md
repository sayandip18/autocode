AUTOCODE

An AI research assistant with GitHub and web retrieval capabilities, and per-user episodic memory.

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
InjectEpisodicMemory middleware          ← retrieves top-5 similar memories
        ↓                                   (pgvector similarity search, scoped to user_id)
LangChain ReAct agent  ←──── AsyncPostgresSaver (thread_id = session_id)
    │                              restores prior messages from langgraph schema
    ├── github_fetch
    ├── web_search / web_extract
    └── arxiv_tool
        ↓
ArchiveEpisodeHook middleware             ← judges turn with gpt-4o-mini
        ↓                                   stores summary in pgvector if noteworthy
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
CHECKPOINT_DB_URL=postgresql://user:pass@localhost:5432/autocode
```

### 2. Start Postgres

```
docker compose up -d
```

A single Postgres instance (port `5432`, image `pgvector/pgvector:pg16`) hosts everything:

| Schema | Purpose |
|---|---|
| `public` | Application tables: `users`, `sessions`, `messages` |
| `langgraph` | LangGraph tables: checkpoints, store (episodic memories with pgvector index) |

### 3. Run

```
.\venv\Scripts\uvicorn app.main:app --reload
```

On first startup the app creates the `vector` extension, the `langgraph` schema, ORM tables, and LangGraph checkpoint/store tables automatically.

---

## Observability

[Langfuse](https://cloud.langfuse.com) — configure `LANGFUSE_*` keys in `.env`.
