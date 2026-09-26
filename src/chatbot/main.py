from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.memory import async_postgres_memory
from chatbot.ai.tools import assistant_tools
from chatbot.api.router import api_router
from chatbot.db.database import database_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_postgres_memory() as memory, database_pool() as db:
        app.state.memory = memory
        app.state.db = db
        app.state.chatbot = AgenticChatbot(
            checkpointer=memory, tools=assistant_tools
        )
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


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(Path(__file__).with_name("static") / "index.html")


if __name__ == "__main__":
    import uvicorn
    from chatbot.config import settings

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
