from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


MessageRole = Literal["system", "developer", "user", "assistant"]


class ModelMessageProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    high_priority_instruction_role: Literal["system", "developer"]

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


OPENAI_MESSAGE_PROFILE = ModelMessageProfile(
    name="openai",
    high_priority_instruction_role="developer",
)
DEEPSEEK_MESSAGE_PROFILE = ModelMessageProfile(
    name="deepseek",
    high_priority_instruction_role="system",
)


class ModelMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: MessageRole
    content: str

    @field_validator("content")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def render_messages_for_profile(
    messages: Sequence[ModelMessage],
    profile: ModelMessageProfile,
) -> list[dict[str, str]]:
    rendered_messages = []
    for message in messages:
        role = message.role
        if role == "developer":
            role = profile.high_priority_instruction_role
        rendered_messages.append({"role": role, "content": message.content})
    return rendered_messages
