from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from app.api.query import router as query_router

app = FastAPI(title="Autocode")

app.include_router(query_router)
