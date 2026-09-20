from fastapi import FastAPI

from chatbot.api.router import api_router


app = FastAPI(
    title="Chatbot API",
    version="0.1.0",
)

app.include_router(
    api_router,
    prefix="/api/v1",
)