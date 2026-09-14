"""
This module defines all the different entities which we might evaluate
a rule on.

Some notes:
- We
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from utilites.pydantic import CustomBaseModel, Field


class Port(CustomBaseModel):
    code: str
    code_iata: str = ""
    code_icao: str = ""
    country: str = ""


class Activity(CustomBaseModel):
    pass


class Duty(CustomBaseModel):
    pass


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
