from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from chatbot.ai.model import get_chat_model


Tool = BaseTool | Callable[..., Any] | dict[str, Any]


class AgenticChatbot:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        tools: Sequence[Tool] = (),
        system_prompt: str = "You are a helpful assistant.",
    ) -> None:
        self.agent = create_agent(
            model=model or get_chat_model(),
            tools=tools,
            system_prompt=system_prompt,
        )

    def invoke(self, message: str) -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")

        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]}
        )
        return result["messages"][-1].content

    async def ainvoke(self, message: str) -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")

        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]}
        )
        return result["messages"][-1].content
