from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.api.model.message import Message
from app.api.model.session import Session
from app.api.model.user import User

ANON_USER_EMAIL = "anon@system"

_ROLE_TO_MSG: dict[str, type[BaseMessage]] = {
    "human": HumanMessage,
    "ai": AIMessage,
}


async def get_or_create_session(db: AsyncSession, session_id: int | None) -> Session:
    if session_id is not None:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        return session

    result = await db.execute(select(User).where(User.email == ANON_USER_EMAIL))
    anon_user = result.scalar_one()
    session = Session(user_id=anon_user.id)
    db.add(session)
    await db.flush()
    return session


async def load_history(db: AsyncSession, session_id: int) -> list[BaseMessage]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    return [
        _ROLE_TO_MSG[msg.role](content=msg.content)
        for msg in result.scalars()
        if msg.role in _ROLE_TO_MSG
    ]


async def save_turn(
    db: AsyncSession, session_id: int, user_content: str, assistant_content: str
) -> None:
    db.add(Message(session_id=session_id, role="human", content=user_content))
    db.add(Message(session_id=session_id, role="ai", content=assistant_content))
    await db.commit()
