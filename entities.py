"""
This module defines all the different entities which we might evaluate
a rule on.

Some notes:
- We
"""

from functools import cached_property
from datetime import datetime

from utilites.pydantic import CustomBaseModel, Field


class GettableList(list):
    """
    Use this for all lists, so that field access can
    do things like items.0, or items.first, etc.

    Can later add properties like max / min.
    """

    @cached_property
    def first(self):
        return self[0]

    @cached_property
    def last(self):
        return self[-1]

    @cached_property
    def max(self):
        return max(self)

    @cached_property
    def min(self):
        return min(self)

    @cached_property
    def argmax(self):
        return max(range(len(self)), key=lambda i: self[i])

    @cached_property
    def argmin(self):
        return min(range(len(self)), key=lambda i: self[i])

    def __getattr__(self, name: str):
        try:
            idx = int(name)
        except ValueError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        try:
            return self[idx]
        except IndexError:
            raise AttributeError(
                f"'{type(self).__name__}' list doesn't have an element at index '{idx}'"
            )


class GettableDict(dict):
    """
    Use this for all dicts to allow field
    access instead of dict key access.
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no key '{name}'")


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
