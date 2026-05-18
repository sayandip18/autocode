from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langgraph.runtime import Runtime
from langgraph.typing import ContextT

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.api.model.session import Session

_judge = ChatOpenAI(model="gpt-4o-mini", temperature=0)

_JUDGE_PROMPT = """\
Does this conversation turn contain information worth remembering long-term \
(e.g. user preferences, key decisions, domain facts, or project context)?

User: {query}
Assistant: {response}

If yes: SAVE: <1-2 sentence summary>
If no: SKIP"""


async def _get_user_id(session_id: int) -> int | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session.user_id).where(
                Session.id == session_id,
                Session.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


async def _judge_turn(query: str, response: str) -> tuple[bool, str]:
    result = await _judge.ainvoke(_JUDGE_PROMPT.format(query=query, response=response))
    content = str(result.content).strip()
    if content.upper().startswith("SAVE:"):
        return True, content[5:].strip()
    return False, ""


class ArchiveEpisodeHook(AgentMiddleware):
    """After each final model response, judges whether the turn is noteworthy
    and stores a summary in the episodic memory store scoped to the user."""

    async def aafter_model(
        self, state: AgentState, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        messages = state["messages"]

        # Only archive final responses, not intermediate tool-dispatch steps
        last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        if last_ai is None or last_ai.tool_calls:
            return None

        last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        if last_human is None:
            return None

        thread_id = (
            runtime.execution_info.thread_id
            if runtime and runtime.execution_info
            else None
        )
        store = runtime.store if runtime else None
        if thread_id is None or store is None:
            return None

        noteworthy, summary = await _judge_turn(
            str(last_human.content), str(last_ai.content)
        )
        if not noteworthy:
            return None

        user_id = await _get_user_id(int(thread_id))
        if user_id is None:
            return None

        await store.aput(
            ("memories", str(user_id)),
            str(uuid.uuid4()),
            {"summary": summary, "session_id": thread_id},
        )
        return None
