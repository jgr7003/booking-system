"""DTOs of the notifications module. They are also its public contract (see `public.py`)."""

from pydantic import BaseModel, ConfigDict, Field


class EmailMessage(BaseModel):
    """An email ready to send: who gets it and its content, already rendered by the caller."""

    model_config = ConfigDict(frozen=True)

    to: str = Field(
        description="Recipient address.",
    )

    subject: str = Field(
        description="Subject line.",
    )

    html: str = Field(
        description="HTML body, with inline styles.",
    )

    text: str = Field(
        description="Plain-text body, for clients that don't show HTML.",
    )
