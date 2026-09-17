"""
This module defines all the different entities which we might evaluate
a rule on.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar, Literal
from pydantic import Field

from utilities.pydantic import CustomBaseModel
from utilities.builtin_extensions import GettableDict, GettableList, GettableDefaultDict


class Entity(CustomBaseModel):
    """Use this as a general thing where we introspect class"""


class TimedEntity(Entity):
    def start_date(self) -> datetime:
        raise NotImplementedError()

    def end_date(self) -> datetime:
        raise NotImplementedError()


class Port(CustomBaseModel):
    code: str
    code_iata: str = ""
    code_icao: str = ""
    country: str = ""


class Activity(TimedEntity):
    category: Literal["flight", "deadhead", "ground_transport", "other"]


class Duty(TimedEntity):
    activities: GettableList[Activity] = Field(default_factory=GettableList)
    category: Literal[
        "flying",
        "deadhead_only",
        "home_standby",
        "airport_standby",
        "ground",
        "simulator",
        "training",
        "admin",
        "generic_work",
        "generic_rest",
    ] = Field(default="generic_work")
    calculated_numbers: GettableDefaultDict[str, float] = Field(
        default_factory=lambda: GettableDefaultDict(float)
    )

    @property
    def flights(self):
        return [x for x in self.activities if x.category in ("flight", "deadhead")]

    @property
    def operating_flights(self):
        return [x for x in self.activities if x.category == "flight"]


class Pairing(CustomBaseModel):
    pass


class Employee(Entity):
    pass


class Aircraft(Entity):
    pass


class EmployeeTimePeriod(TimedEntity):
    employee: Employee
    start: datetime
    end: datetime


class AircraftTimePeriod(TimedEntity):
    aircraft: Aircraft
    start: datetime
    end: datetime


class PortTimePeriod(TimedEntity):
    port: Port
    start: datetime
    end: datetime


class EmployeeRestTime(TimedEntity):
    preceding_duty: Duty
    succeeding_duty: Duty
    employee: Employee


class EmployeeGroundTime(TimedEntity):
    inbound_activity: Activity
    outbound_activity: Activity
    employee: Employee


class AircraftGroundTime(TimedEntity):
    inbound_activity: Activity
    outbound_activity: Activity
    aircraft: Aircraft
