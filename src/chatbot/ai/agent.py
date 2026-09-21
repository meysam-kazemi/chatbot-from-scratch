import asyncio
from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from chatbot.ai.model import get_chat_model


Tool = BaseTool | Callable[..., Any] | dict[str, Any]


class AgenticChatbot:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        tools: Sequence[Tool] = (),
        system_prompt: str = "You are a helpful assistant.",
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self.agent = create_agent(
            model=model or get_chat_model(),
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer or InMemorySaver(),
        )

    def invoke(self, message: str, conversation_id: str = "default") -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")

        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": conversation_id}},
        )
        return result["messages"][-1].content

    async def ainvoke(self, message: str, conversation_id: str = "default") -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")

        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": conversation_id}},
        )
        return result["messages"][-1].content


async def demo() -> None:
    from chatbot.ai.memory import async_postgres_memory

    async with async_postgres_memory() as memory:
        chatbot = AgenticChatbot(checkpointer=memory)
        response = await chatbot.ainvoke(
            "what is my past message?",
            conversation_id="test",
        )
        print(response)


if __name__ == "__main__":
    asyncio.run(demo())