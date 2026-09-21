from langchain.chat_models import init_chat_model
from functools import lru_cache
from chatbot.config import settings


@lru_cache
def get_chat_model():
    return init_chat_model(
        settings.ai_model,
        temperature=settings.ai_temperature,
        timeout=30,
        max_retries=3,
    )
    