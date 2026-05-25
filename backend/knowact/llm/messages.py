from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class ModelMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["system", "developer", "user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

