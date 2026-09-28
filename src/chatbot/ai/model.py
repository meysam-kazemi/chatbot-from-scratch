from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from chatbot.config import settings


def get_chat_model() -> BaseChatModel:
    """Build the configured chat model."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    return init_chat_model(
        model=settings.ai_model,
        api_key=settings.openai_api_key,
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
        timeout=settings.ai_timeout,
        max_retries=settings.ai_max_retries,
    )


def get_title_model() -> BaseChatModel:
    """Build the configured title model."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    return init_chat_model(
        model=settings.ai_title_model,
        api_key=settings.openai_api_key,
        temperature=settings.ai_title_temperature,
        max_tokens=settings.ai_title_max_tokens,
        timeout=settings.ai_title_timeout,
        max_retries=settings.ai_title_max_retries,
    )
