from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage

from app.arxiv import arxiv_tool
from app.github import github_fetch
from app.web_search import make_web_extract_tool, make_web_search_tool

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent(
            model="openai:gpt-4o",
            tools=[github_fetch, make_web_search_tool(), make_web_extract_tool(), arxiv_tool],
            system_prompt="You are a helpful assistant.",
        )
    return _agent


async def run_agent(user_query: str, history: list[BaseMessage] | None = None) -> str:
    messages = (history or []) + [HumanMessage(content=user_query)]
    result = await _get_agent().ainvoke({"messages": messages})  # type: ignore[arg-type]
    return result["messages"][-1].content
