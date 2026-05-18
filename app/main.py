from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from psycopg_pool import AsyncConnectionPool
from sqlalchemy import select, text
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

from app.api.model.base import Base
from app.api.model.user import User
from app.core.session_service import ANON_USER_EMAIL
from app.core.tool import init_agent
from app.db import AsyncSessionLocal, engine
from app.api.query import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS langgraph"))
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == ANON_USER_EMAIL))
        if result.scalar_one_or_none() is None:
            db.add(User(name="Anonymous", email=ANON_USER_EMAIL, password_hash=""))
            await db.commit()

    langgraph_url = os.environ["CHECKPOINT_DB_URL"]
    async with AsyncConnectionPool(
        conninfo=langgraph_url,
        kwargs={"autocommit": True, "options": "-c search_path=langgraph"},
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        store = AsyncPostgresStore(
            pool,
            index={"dims": 1536, "embed": "openai:text-embedding-3-small"},
        )
        await store.setup()

        init_agent(checkpointer, store)
        yield


app = FastAPI(title="Autocode", lifespan=lifespan)

app.include_router(query_router)
