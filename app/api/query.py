from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.tool import run_agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/query")
async def query(q: str = Query(..., description="Question or GitHub repository URL")):
    try:
        answer = await run_agent(q)
    except Exception as exc:
        logger.exception("Agent failed")
        raise HTTPException(status_code=502, detail=str(exc))

    return {"query": q, "answer": answer}
