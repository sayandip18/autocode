# AI Research Agent Architecture & Roadmap

This document describes the cognitive design, state management, tool specifications, and evolution strategy for the AI Research Assistant backend.

---

## 1. Agent Overview & Persona

- **Objective**: Execute autonomous, deep-dive research across web sources and GitHub repositories to synthesize highly contextual technical answers.
- **Core Paradigm**: Stateful ReAct agent backed by a persistent LangGraph checkpointer.

---

## 2. Current Architecture (Phase 1)

The system runs as a **ReAct (Reasoning + Acting)** agent using LangChain's `create_agent()`. Conversation state is persisted across turns via a **LangGraph `AsyncPostgresSaver` checkpointer** — the agent resumes from the exact last state on every request without manually loading or replaying message history.

### LLM
`gpt-4o` via `langchain-openai`

### Execution Flow

```
POST /query { q, session_id }
    │
    ├─ get_or_create_session()   → sessions table
    │
    ├─ run_agent(q, session_id)
    │       │
    │       ├─ thread_id = str(session_id)
    │       ├─ AsyncPostgresSaver restores prior checkpoint
    │       ├─ LLM reasons → calls tools as needed
    │       │       ├─ github_fetch       (GitHub repo content)
    │       │       ├─ web_search         (Tavily search)
    │       │       ├─ web_extract        (Tavily page extract)
    │       │       └─ arxiv_tool         (ArXiv paper search)
    │       └─ LLM synthesizes final answer
    │
    ├─ save_turn()               → messages table (audit log)
    │
    └─ { session_id, query, answer }
```

### Persistence — Two Postgres Databases

| Database | Port | Purpose |
|---|---|---|
| `autocode` | 5432 | Application tables: `users`, `sessions`, `messages` (audit log) |
| `checkpoints` | 5433 | LangGraph tables: `checkpoints`, `checkpoint_writes`, `checkpoint_blobs` |

The `messages` table is an independent audit log. The checkpointer owns the live in-context message state used by the agent.

### Key Files

| File | Responsibility |
|---|---|
| `app/core/tool.py` | Agent definition; `init_agent(checkpointer)` wires the saver at startup |
| `app/core/session_service.py` | Session lifecycle and audit-log writes |
| `app/api/query.py` | HTTP endpoint; maps `session_id` → `thread_id` |
| `app/main.py` | FastAPI lifespan: opens psycopg3 pool, calls `checkpointer.setup()`, calls `init_agent()` |
| `docker-compose.yml` | Two Postgres 16 services |

---

## 3. Roadmap (Phase 2)

- Multi-agent graph: planner → retriever → synthesizer nodes
- Streaming responses via Server-Sent Events
- User authentication (replace anonymous-only session model)
- Source citation in responses
