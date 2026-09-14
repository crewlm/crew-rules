"""
This module defines all the different entities which we might evaluate
a rule on.

Some notes:
- We
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from utilites.pydantic import CustomBaseModel, Field, GetCoreSchemaHandler, core_schema

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def _to_std_type(source_type: Any, std_base: type) -> Any:
    """
    Replaces GettableList/GettableDict with standard list/dict while preserving generic args.
    - GettableList[T] -> list[T]
    - GettableDict[K, V] -> dict[K, V]
    """
    args = getattr(source_type, "__args__", ())
    if args:
        return std_base[args]
    return std_base


class GettableList(list[T], Generic[T]):
    """
    List subclass enabling dot-notation field access for attrgetter.
    Supports index access (.0, .1) and property access (.first, .last, .max, .min).
    """

    @property
    def first(self):
        return self[0]

    @property
    def last(self):
        return self[-1]

    @property
    def largest(self):
        return max(self)

    @property
    def smallest(self):
        return min(self)

    @property
    def arg_largest(self):
        return max(range(len(self)), key=lambda i: self[i])

    @property
    def arg_smallest(self):
        return min(range(len(self)), key=lambda i: self[i])

    @property
    def count_items(self):
        return len(self)

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
        std_type = _to_std_type(source_type, list)
        return core_schema.no_info_after_validator_function(
            cls,
            handler.generate_schema(std_type),
        )


class GettableDict(dict[K, V], Generic[K, V]):
    """
    Dict subclass enabling dot-notation field access for attrgetter.
    E.g., calculated_numbers.frms_score
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
        std_type = _to_std_type(source_type, dict)
        return core_schema.no_info_after_validator_function(
            cls,
            handler.generate_schema(std_type),
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
