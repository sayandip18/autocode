# AI Research Agent Architecture & Roadmap

This document describes the cognitive design, state management, tool specifications, and evolution strategy for the AI Research Assistant backend.

---

## 1. Agent Overview & Persona

- **Objective**: Execute autonomous, deep-dive research across web sources and GitHub repositories to synthesize highly contextual technical answers.
- **Core Paradigm**: Stateful ReAct agent backed by a persistent LangGraph checkpointer and per-user episodic memory via pgvector.

---

## 2. Current Architecture (Phase 2)

The system runs as a **ReAct** agent using LangChain's `create_agent()`. Conversation state is persisted via **`AsyncPostgresSaver`**. Long-term episodic memory is stored in **`AsyncPostgresStore`** (pgvector), scoped per user and retrieved by semantic similarity before each new user turn.

### LLM
`gpt-4o` via `langchain-openai`

### Execution Flow

```
POST /query { q, session_id }
    │
    ├─ get_or_create_session()         → sessions table (public schema)
    │
    ├─ run_agent(q, session_id)
    │       │
    │       ├─ thread_id = str(session_id)
    │       │
    │       ├─ InjectEpisodicMemory.awrap_model_call()
    │       │       ├─ guard: only on HumanMessage turns (skip tool follow-ups)
    │       │       ├─ look up user_id from session_id (DB query)
    │       │       ├─ store.asearch(("memories", user_id), query, limit=5)
    │       │       └─ append retrieved summaries to system prompt
    │       │
    │       ├─ AsyncPostgresSaver restores prior checkpoint (langgraph schema)
    │       ├─ LLM reasons → calls tools as needed
    │       │       ├─ github_fetch       (GitHub repo content)
    │       │       ├─ web_search         (Tavily search)
    │       │       ├─ web_extract        (Tavily page extract)
    │       │       └─ arxiv_tool         (ArXiv paper search)
    │       ├─ LLM synthesizes final answer
    │       │
    │       └─ ArchiveEpisodeHook.aafter_model()
    │               ├─ guard: only on final responses (skip AIMessage with tool_calls)
    │               ├─ gpt-4o-mini judges: SAVE: <summary> or SKIP
    │               ├─ look up user_id from session_id
    │               └─ store.aput(("memories", user_id), uuid, {summary, session_id})
    │
    ├─ save_turn()                     → messages table (audit log)
    │
    └─ { session_id, query, answer }
```

### Persistence — Single Postgres, Two Schemas

| Schema | Port | Purpose |
|---|---|---|
| `public` | 5432 | Application tables: `users`, `sessions`, `messages` (SQLAlchemy / asyncpg) |
| `langgraph` | 5432 | LangGraph tables: checkpoints + episodic memory store with pgvector index (psycopg3 pool) |

The `messages` table is an independent audit log. The checkpointer owns the live in-context message state used by the agent. The store holds long-term episodic summaries across sessions.

### Episodic Memory Design

- **Namespace**: `("memories", str(user_id))` — each user's memories are isolated
- **Embedding model**: `text-embedding-3-small` (1536 dims, via `AsyncPostgresStore` index config)
- **Retrieval**: top-5 by cosine similarity against the current user query
- **Injection point**: system prompt (via `awrap_model_call`) — does not pollute conversation history
- **Write condition**: `gpt-4o-mini` must classify the turn as noteworthy (user preferences, key decisions, domain facts, project context)
- **Write point**: `aafter_model`, after the final natural-language response

### Middleware

| Class | File | Hook | Role |
|---|---|---|---|
| `InjectEpisodicMemory` | `app/core/pre_model_hook.py` | `awrap_model_call` | Fetches and injects memories into system prompt |
| `ArchiveEpisodeHook` | `app/core/post_model_hook.py` | `aafter_model` | Judges and archives noteworthy turns |

### Key Files

| File | Responsibility |
|---|---|
| `app/core/tool.py` | Agent definition; `init_agent(checkpointer, store)` wires persistence and middleware at startup |
| `app/core/pre_model_hook.py` | `InjectEpisodicMemory` — pre-call memory retrieval and system prompt augmentation |
| `app/core/post_model_hook.py` | `ArchiveEpisodeHook` — post-response noteworthiness check and memory write |
| `app/core/session_service.py` | Session lifecycle and audit-log writes |
| `app/api/query.py` | HTTP endpoint; maps `session_id` → `thread_id` |
| `app/main.py` | FastAPI lifespan: creates `vector` extension + `langgraph` schema, opens psycopg3 pool, sets up checkpointer and store, calls `init_agent()` |
| `docker-compose.yml` | Single `pgvector/pgvector:pg16` service on port 5432 |

---

## 3. Roadmap (Phase 3)

- Multi-agent graph: planner → retriever → synthesizer nodes
- Streaming responses via Server-Sent Events
- User authentication (replace anonymous-only session model)
- Source citation in responses
- Memory consolidation: periodic deduplication / summarization of old episodic entries
