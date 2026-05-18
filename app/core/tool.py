from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

from app.arxiv import arxiv_tool
from app.github import github_fetch
from app.web_search import make_web_extract_tool, make_web_search_tool
from app.core.pre_model_hook import InjectEpisodicMemory
from app.core.post_model_hook import ArchiveEpisodeHook

inject_episodic_memory = InjectEpisodicMemory()
archive_episode_hook = ArchiveEpisodeHook()

_agent = None


def init_agent(checkpointer: AsyncPostgresSaver, store: AsyncPostgresStore) -> None:
    global _agent
    _agent = create_agent(
        model="openai:gpt-4o",
        tools=[github_fetch, make_web_search_tool(), make_web_extract_tool(), arxiv_tool],
        system_prompt="You are a helpful assistant.",
        checkpointer=checkpointer,
        store=store,
        middleware=[inject_episodic_memory, archive_episode_hook],
    )


def _get_agent():
    if _agent is None:
        raise RuntimeError("Agent not initialized — call init_agent() at startup")
    return _agent


async def run_agent(user_query: str, session_id: int) -> str:
    config = {"configurable": {"thread_id": str(session_id)}}
    result = await _get_agent().ainvoke(
        {"messages": [HumanMessage(content=user_query)]},
        config=config,  # type: ignore[arg-type]
    )
    return result["messages"][-1].content
