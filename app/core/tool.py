from __future__ import annotations

import json
import os
from typing import Any, cast

import openai
from openai.types.chat import ChatCompletionMessageParam

from app.github import fetch_repo_info
from app.web_search import web_search

_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "github_fetch",
            "description": "Fetch README, file tree, and recent commits from a GitHub repo URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string"}
                },
                "required": ["repo_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for recent articles, docs, or discussions",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
            },
        },
    },
]


async def github_fetch(repo_url: str) -> dict[str, Any]:
    return await fetch_repo_info(repo_url)


async def run_agent(user_query: str) -> str:
    client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages: list[ChatCompletionMessageParam] = [
        {"role": "user", "content": user_query}
    ]

    while True:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=cast(Any, _TOOLS),
            tool_choice="auto",
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or ""

        messages.append(cast(ChatCompletionMessageParam, msg))
        for tool_call in msg.tool_calls:
            if tool_call.type != "function":
                continue
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if name == "github_fetch":
                result = await github_fetch(**args)
            elif name == "web_search":
                result = await web_search(**args)
            else:
                result = {"error": f"unknown tool: {name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })
