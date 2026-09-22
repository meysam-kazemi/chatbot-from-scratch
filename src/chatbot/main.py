from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatbot.ai.memory import async_postgres_memory
from chatbot.api.router import api_router
from chatbot.db.database import database_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_postgres_memory() as memory, database_pool() as db:
        app.state.memory = memory
        app.state.db = db
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



if __name__ == "__main__":
    import uvicorn
    from chatbot.config import settings

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")