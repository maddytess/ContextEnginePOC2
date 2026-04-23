import os
from contextlib import asynccontextmanager
from surrealdb import AsyncSurreal
from dotenv import load_dotenv

load_dotenv()


@asynccontextmanager
async def get_db():
    url = os.getenv("SURREAL_URL", "ws://localhost:8000/rpc")
    user = os.getenv("SURREAL_USER", "root")
    password = os.getenv("SURREAL_PASS", "root")
    namespace = os.getenv("SURREAL_NS", "escher")
    database = os.getenv("SURREAL_DB", "main")

    async with AsyncSurreal(url) as db:
        await db.signin({"username": user, "password": password})
        await db.use(namespace, database)
        yield db
