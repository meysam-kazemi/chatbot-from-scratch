import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any
from importlib.resources import files

from langchain.agents import create_agent
from langchain_core.callbacks.manager import Callbacks
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from chatbot.ai.long_term_memory import LongTermMemoryMiddleware
from chatbot.ai.model import get_chat_model
from chatbot.ai.tools import ToolContext


Tool = BaseTool | Callable[..., Any] | dict[str, Any]
SYSTEM_PROMPT = (
    files("chatbot.ai.prompts")
    .joinpath("agent_prompt.md")
    .read_text(encoding="utf-8")
)

DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT


class AgenticChatbot:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        tools: Sequence[Tool] = (),
        system_prompt: str = SYSTEM_PROMPT,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self.checkpointer = checkpointer or InMemorySaver()
        self.agent = create_agent(
            model=model or get_chat_model(),
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=self.checkpointer,
            context_schema=ToolContext,
            middleware=[LongTermMemoryMiddleware()],
        )

    def invoke(
        self, message: str,
        conversation_id: str = "default",
        context: ToolContext | None = None,
        callbacks: Callbacks = None,
        ) -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")

        config = {"configurable": {"thread_id": conversation_id}}
        if callbacks:
            config["callbacks"] = callbacks
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            context=context,
        )
        return result["messages"][-1].content

    async def aget_messages(self, conversation_id: str) -> list[BaseMessage]:
        state = await self.agent.aget_state(
            {"configurable": {"thread_id": conversation_id}}
        )
        return [
            message
            for message in state.values.get("messages", [])
            if isinstance(message, HumanMessage)
            or (isinstance(message, AIMessage) and not message.tool_calls)
        ]

    async def adelete_conversation(self, conversation_id: str) -> None:
        await self.checkpointer.adelete_thread(conversation_id)

    async def ainvoke(
        self,
        message: str,
        conversation_id: str = "default",
        context: ToolContext | None = None,
        callbacks: Callbacks = None,
    ) -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")

        config = {"configurable": {"thread_id": conversation_id}}
        if callbacks:
            config["callbacks"] = callbacks
        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            context=context,
        )
        return result["messages"][-1].content


    async def astream(
        self,
        message: str,
        conversation_id: str = "default",
        context: ToolContext | None = None,
        callbacks: Callbacks = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream text and tool lifecycle events, without exposing tool payloads."""
        if not message.strip():
            raise ValueError("message cannot be empty")
        config = {"configurable": {"thread_id": conversation_id}}
        if callbacks:
            config["callbacks"] = callbacks
        async for event in self.agent.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config=config, context=context, version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_start":
                yield {"event": "message_start"}
            elif kind == "on_chat_model_stream":
                text = event["data"]["chunk"].text
                if text:
                    yield {"event": "delta", "text": text}
            elif kind in {"on_tool_start", "on_tool_end"}:
                output = event["data"].get("output")
                yield {
                    "event": "tool_start" if kind == "on_tool_start" else "tool_end",
                    "id": str(event["run_id"]),
                    "name": event["name"],
                    "status": "error" if getattr(output, "status", None) == "error" else "ok",
                }
            elif kind == "on_chain_end" and not event.get("parent_ids"):
                output = event["data"]["output"]
                yield {"event": "answer", "content": output["messages"][-1].text}


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
