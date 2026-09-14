"""
This module defines all the different entities which we might evaluate
a rule on.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar, Literal
from pydantic import Field

from utilities.pydantic import CustomBaseModel
from utilities.builtin_extensions import GettableDict, GettableList, GettableDefaultDict


class Port(CustomBaseModel):
    code: str
    code_iata: str = ""
    code_icao: str = ""
    country: str = ""


class Activity(CustomBaseModel):
    pass


class Duty(CustomBaseModel):
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
    calculated_numbers: GettableDefaultDict[float] = Field(
        default_factory=lambda: GettableDefaultDict(float)
    )


class Pairing(CustomBaseModel):
    pass


class Employee(CustomBaseModel):
    pass


class Aircraft(CustomBaseModel):
    pass


class EmployeeTimePeriod(CustomBaseModel):
    employee: Employee
    start: datetime
    end: datetime


class AircraftTimePeriod(CustomBaseModel):
    aircraft: Aircraft
    start: datetime
    end: datetime


class PortTimePeriod(CustomBaseModel):
    port: Port
    start: datetime
    end: datetime


class EmployeeRestTime(CustomBaseModel):
    preceding: Duty
    succeeding: Duty
    employee: Employee


class EmployeeGroundTime(CustomBaseModel):
    inbound: Activity
    outbound: Activity
    employee: Employee


class AircraftGroundTime(CustomBaseModel):
    inbound: Activity
    outbound: Activity
    aircraft: Aircraft
