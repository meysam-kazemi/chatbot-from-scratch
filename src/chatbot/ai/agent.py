from langchain.agents import create_agent
from chatbot.ai.model import get_chat_model


llm = get_chat_model()

agent = create_agent(
    model=get_chat_model,
    tools=[],
    system_prompt="You are a helpful assistant",
)

