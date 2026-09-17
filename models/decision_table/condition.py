from typing import TypeVar, Annotated, Literal, Any, Iterable
from datetime import datetime, timedelta, time
from functools import cached_property
from operator import attrgetter

from utilities.pydantic import CustomBaseModel, Field
from utilities.formatters import timedelta_to_iso8601, format_field
from models.comparison import Comparison


class Condition[C](CustomBaseModel):
    """TODO: C constrains the fields allowed (scoping to the object's available fields)"""

    field: str = Field(
        description="Dot-separated field, accessing object's field using dot notation."
    )
    comparison: Comparison = Field(description="Comparison to make")
    reverse_match: bool = Field(False, description="TRUE inverts the match")

    @cached_property
    def _field_getter(self):
        return attrgetter(self.field)

    def matches(self, obj):
        value = self._field_getter(obj)
        comparison_match = self.comparison.matches(value)
        return (not comparison_match) if self.reverse_match else comparison_match

    def __str__(self):
        entity_name = ""
        op = "is not" if self.reverse_match else "is"
        return f"{format_field(entity_name, self.field)} {op} {str(self.comparison)}"
