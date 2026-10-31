"""Base of the identity DTOs."""

from pydantic import BaseModel, ConfigDict


class DTO(BaseModel):
    """Base of every identity DTO: immutable."""

    model_config = ConfigDict(frozen=True)
