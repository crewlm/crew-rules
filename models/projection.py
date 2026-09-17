from uuid import uuid4, UUID
from typing import Literal, Any
from datetime import timedelta

from pydantic import Field

from utilities.pydantic import CustomBaseModel


class Projection(CustomBaseModel):
    id: UUID = Field(default_factory=uuid4, description="UUID for projection")
    name: str
    scope: Literal["entity"] = "entity"
