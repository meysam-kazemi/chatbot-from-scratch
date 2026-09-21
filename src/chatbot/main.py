from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatbot.ai.memory import async_postgres_memory
from chatbot.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_postgres_memory() as memory:
        app.state.memory = memory
        yield


app = FastAPI(
    title="Chatbot API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(
    api_router,
    prefix="/api/v1",
)
