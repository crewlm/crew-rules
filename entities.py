"""
This module defines all the different entities which we might evaluate
a rule on.

Some notes:
- We
"""

from functools import cached_property
from datetime import datetime
from typing import Any

from utilites.pydantic import CustomBaseModel, Field, GetCoreSchemaHandler, core_schema


class GettableList(list):
    """
    List subclass enabling dot-notation field access for attrgetter.
    Supports index access (.0, .1) and property access (.first, .last, .max, .min).
    """

    # Necessary for @cached_property to store instance attributes on a list subclass
    __slots__ = ("__dict__",)

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

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Preserve item validation when typed like GettableList[MyModel]
        instance_schema = (
            handler(source_type) if source_type != cls else core_schema.list_schema()
        )
        return core_schema.no_info_after_validator_function(
            cls,
            instance_schema,
        )


class GettableDict(dict):
    """
    Dict subclass enabling dot-notation field access for attrgetter.
    E.g., calculated_numbers.max_fdp_hours
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no key '{name}'")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = (
            handler(source_type) if source_type != cls else core_schema.dict_schema()
        )
        return core_schema.no_info_after_validator_function(
            cls,
            instance_schema,
        )


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
