from __future__ import annotations

import logging
import os

import openai
from fastapi import APIRouter, HTTPException, Query

from app.github import fetch_repo_info

logger = logging.getLogger(__name__)

router = APIRouter()

_SUMMARIZE_PROMPT = (
    "You are a senior software engineer. Given the README and file tree of a GitHub "
    "repository, write a concise summary covering: what the project does, its main "
    "components, and the overall architecture. Be specific and technical.\n\n"
    "README:\n{readme}\n\nFile tree:\n{file_tree}"
)


@router.get("/query")
async def query(q: str = Query(..., description="GitHub repository URL")):
    try:
        repo_info = await fetch_repo_info(q)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to fetch repo info")
        raise HTTPException(status_code=502, detail=f"GitHub fetch failed: {exc}")

    prompt = _SUMMARIZE_PROMPT.format(
        readme=repo_info["readme"][:8000],
        file_tree=repo_info["file_tree"][:4000],
    )

    try:
        client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        summary = response.choices[0].message.content
    except Exception as exc:
        logger.exception("OpenAI call failed")
        raise HTTPException(status_code=502, detail=f"OpenAI call failed: {exc}")

    return {
        "repo": q,
        "summary": summary,
        "readme_length": len(repo_info["readme"]),
        "file_count": repo_info["file_tree"].count("\n") + 1,
    }
