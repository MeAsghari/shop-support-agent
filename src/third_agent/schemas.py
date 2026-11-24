from typing import Literal

from pydantic import BaseModel


class Classification(BaseModel):
    """The result we expect from the classifier model."""

    # Only these three words are allowed
    intent: Literal["docs", "orders", "other"]
    # The customer's email if the question contains one, otherwise None
    email: str | None = None