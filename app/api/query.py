from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session_service import get_or_create_session, load_history, save_turn
from app.core.tool import run_agent
from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    q: str
    session_id: int | None = None


@router.post("/query")
async def query(body: QueryRequest, db: AsyncSession = Depends(get_db)):
    try:
        session = await get_or_create_session(db, body.session_id)
        history = await load_history(db, session.id)
        answer = await run_agent(body.q, history)
        await save_turn(db, session.id, body.q, answer)
    except Exception as exc:
        logger.exception("Agent failed")
        raise HTTPException(status_code=502, detail=str(exc))

    return {"session_id": session.id, "query": body.q, "answer": answer}
