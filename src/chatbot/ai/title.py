from importlib.resources import files
from pydantic import BaseModel, Field, field_validator

from langchain_core.callbacks.manager import Callbacks
from langchain_core.language_models import BaseChatModel

from chatbot.ai.model import get_title_model


SYSTEM_PROMPT = (
    files("chatbot.ai.prompts")
    .joinpath("change_title_prompt.md")
    .read_text(encoding="utf-8")
)

class ConversationTitle(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="Concise conversation title in the user's language")

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class TitleGenerator:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        system_prompt: str = SYSTEM_PROMPT,
    ):
        self.model = (model or get_title_model()).with_structured_output(
            ConversationTitle, method="json_schema", strict=True
        )
        self.system_prompt = system_prompt
    
    def invoke(self, message: str) -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")
        response = self.model.invoke(
            [
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": message[:4000],
                },
            ]
        )
        return response.title
    
    async def ainvoke(self, message: str, callbacks: Callbacks = None) -> str:
        if not message.strip():
            raise ValueError("message cannot be empty")
        config = {"callbacks": callbacks} if callbacks else None
        response = await self.model.ainvoke(
            [
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": message[:4000],
                },
            ],
            config=config,
        )

        return response.title

        
if __name__=="__main__":
    title = TitleGenerator()
    res = title.invoke("hi my name is meysam kjazemi")
    print(res)
