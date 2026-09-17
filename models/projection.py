from uuid import uuid4, UUID
from typing import Literal, Any
from datetime import timedelta

from pydantic import Field

from utilities.pydantic import CustomBaseModel


class Component(CustomBaseModel):
    start: Any
    end: Any
    rate: float = Field(1.0, description="Per-minute accumulation")
    clamp_lower: timedelta | None = Field(
        None, description="Minimum duration of component"
    )
    clamp_upper: timedelta | None = Field(
        None, description="Maximum duration of component"
    )


class Projection(CustomBaseModel):
    id: UUID = Field(default_factory=uuid4, description="UUID for projection")
    name: str
    scope: Literal["entity"] = "entity"
