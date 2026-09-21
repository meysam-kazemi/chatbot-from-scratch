from fastapi import Request

from chatbot.ai.agent import AgenticChatbot


def get_chatbot(request: Request) -> AgenticChatbot:
    return AgenticChatbot(checkpointer=request.app.state.memory)
