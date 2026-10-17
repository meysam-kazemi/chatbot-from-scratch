import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage
from pydantic import BaseModel, ValidationError

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.title import ConversationTitle, TitleGenerator
from test_tools import ToolCallingFakeModel


class Answer(BaseModel):
    answer: str


class StructuredOutputTest(unittest.IsolatedAsyncioTestCase):
    async def test_title_uses_schema_and_preserves_callbacks(self):
        model = Mock()
        structured = model.with_structured_output.return_value
        structured.invoke.return_value = ConversationTitle(title=" Greeting ")
        structured.ainvoke = AsyncMock(return_value=ConversationTitle(title="Greeting"))
        generator = TitleGenerator(model=model)
        self.assertEqual(generator.invoke("Hi"), "Greeting")
        callbacks = [Mock()]
        self.assertEqual(await generator.ainvoke("Hi", callbacks=callbacks), "Greeting")
        model.with_structured_output.assert_called_once_with(
            ConversationTitle, method="json_schema", strict=True
        )
        self.assertEqual(structured.ainvoke.call_args.kwargs['config'], {'callbacks': callbacks})
        for value in (" ", "x" * 101):
            with self.assertRaises(ValidationError):
                ConversationTitle(title=value)
        with self.assertRaises(ValueError):
            await generator.ainvoke(" ")

    def make_chatbot(self):
        return AgenticChatbot(
            model=ToolCallingFakeModel(responses=[AIMessage(content="", tool_calls=[{
                "name": "Answer", "args": {"answer": "Hello"},
                "id": "answer-1", "type": "tool_call",
            }])]), response_format=Answer,
        )

    async def test_typed_agent_sync_async_and_stream(self):
        self.assertEqual(await asyncio.to_thread(self.make_chatbot().invoke, "Hi"), Answer(answer="Hello"))
        self.assertEqual(await self.make_chatbot().ainvoke("Hi"), Answer(answer="Hello"))
        events = [e async for e in self.make_chatbot().astream("Hi")]
        self.assertEqual(events[-1], {'event': 'answer', 'content': '{"answer":"Hello"}'})
        self.assertEqual(''.join(e['text'] for e in events if e['event'] == 'delta'), '{"answer":"Hello"}')
