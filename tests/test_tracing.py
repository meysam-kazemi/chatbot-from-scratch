import unittest
import uuid
from contextlib import asynccontextmanager

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.tracing import PostgresTracer


@tool
def echo(text: str) -> str:
    """Return text unchanged."""
    return text


class ToolCallingModel(FakeMessagesListChatModel):
    def bind_tools(self, *args, **kwargs):
        return self


class FakePool:
    def __init__(self):
        self.rows = []

    @asynccontextmanager
    async def connection(self):
        yield self

    async def execute(self, _query, parameters):
        self.rows.append(parameters)


class TracingTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_trace_contains_model_and_tool_runs(self):
        pool = FakePool()
        tracer = PostgresTracer(pool, uuid.uuid4(), uuid.uuid4())
        chatbot = AgenticChatbot(
            model=ToolCallingModel(
                responses=[
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "echo",
                                "args": {"text": "hello"},
                                "id": "call-1",
                                "type": "tool_call",
                            }
                        ],
                    ),
                    AIMessage(content="hello"),
                ]
            ),
            tools=[echo],
        )

        self.assertEqual(
            await chatbot.ainvoke("Echo hello", callbacks=[tracer]),
            "hello",
        )
        await tracer.persist()

        payload = pool.rows[0][-1].obj
        run_types = {
            run["run_type"]
            for run in payload["child_runs"]
            + [child for run in payload["child_runs"] for child in run["child_runs"]]
        }
        self.assertIn("llm", run_types)
        self.assertIn("tool", run_types)
        self.assertEqual(payload["inputs"]["messages"][0]["content"], "Echo hello")


if __name__ == "__main__":
    unittest.main()
