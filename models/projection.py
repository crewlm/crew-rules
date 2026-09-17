from uuid import uuid4, UUID
from typing import Literal, Any
from datetime import timedelta

from pydantic import Field

from models.update import ProjectionUpdate
from models.entity import Activity, EmployeeGroundTime, Duty, Pairing, EmployeeRestTime
from utilities.pydantic import CustomBaseModel


class Projection(CustomBaseModel):
    id: UUID = Field(default_factory=uuid4, description="UUID for projection")
    name: str
    activity_projections: list[ProjectionUpdate[Activity]] = Field(default_factory=list)
    employee_ground_time_projections: list[ProjectionUpdate[EmployeeGroundTime]] = (
        Field(default_factory=list)
    )
    duty_projections: list[ProjectionUpdate[Duty]] = Field(default_factory=list)
    employee_rest_time_projections: list[ProjectionUpdate[EmployeeRestTime]] = Field(
        default_factory=list
    )
    pairing_projections: list[ProjectionUpdate[Pairing]] = Field(default_factory=list)
