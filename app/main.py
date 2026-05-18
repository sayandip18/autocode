from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from psycopg_pool import AsyncConnectionPool
from sqlalchemy import select
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.model.base import Base
from app.api.model.user import User
from app.core.session_service import ANON_USER_EMAIL
from app.core.tool import init_agent
from app.db import AsyncSessionLocal, engine
from app.api.query import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == ANON_USER_EMAIL))
        if result.scalar_one_or_none() is None:
            db.add(User(name="Anonymous", email=ANON_USER_EMAIL, password_hash=""))
            await db.commit()

    checkpoint_url = os.environ["CHECKPOINT_DB_URL"]
    async with AsyncConnectionPool(
        conninfo=checkpoint_url,
        kwargs={"autocommit": True},
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        init_agent(checkpointer)
        yield


app = FastAPI(title="Autocode", lifespan=lifespan)

app.include_router(query_router)
