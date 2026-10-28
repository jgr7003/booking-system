"""Base of every flights DTO."""

from pydantic import BaseModel, ConfigDict


class DTO(BaseModel):
    """Base of every flights DTO: immutable."""

    model_config = ConfigDict(frozen=True)
