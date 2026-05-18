from __future__ import annotations

from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.typing import ContextT

from app.db import AsyncSessionLocal
from app.api.model.session import Session


async def _get_user_id(session_id: int) -> int | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session.user_id).where(
                Session.id == session_id,
                Session.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


class InjectEpisodicMemory(AgentMiddleware):
    """Retrieves the top-5 episodic memories for the current user and injects
    them into the system prompt before each new human turn."""

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler,
    ) -> ModelResponse:
        # Only inject on new human turns, not on tool-result follow-ups
        last_msg = request.messages[-1] if request.messages else None
        if not isinstance(last_msg, HumanMessage):
            return await handler(request)

        store = request.runtime.store if request.runtime else None
        thread_id = (
            request.runtime.execution_info.thread_id
            if request.runtime and request.runtime.execution_info
            else None
        )
        if store is None or thread_id is None:
            return await handler(request)

        user_id = await _get_user_id(int(thread_id))
        if user_id is None:
            return await handler(request)

        memories = await store.asearch(
            ("memories", str(user_id)),
            query=str(last_msg.content),
            limit=5,
        )
        if not memories:
            return await handler(request)

        lines = [m.value["summary"] for m in memories if m.value.get("summary")]
        if not lines:
            return await handler(request)

        memory_block = "Relevant memories from past conversations with this user:\n" + "\n".join(
            f"- {s}" for s in lines
        )
        base_content = request.system_message.content if request.system_message else ""
        new_system = SystemMessage(content=f"{base_content}\n\n{memory_block}".strip())

        return await handler(request.override(system_message=new_system))
