"""
Different models.
"""

from typing import Literal, Iterable, Any, Hashable, Annotated
from functools import cached_property
from operator import attrgetter
from uuid import uuid4, UUID
from datetime import datetime, timedelta, time

from utilites.pydantic import CustomBaseModel, Field, PrivateAttr


class EqualNumberComparison(CustomBaseModel):
    kind: Literal["equal_number_comparison"] = "equal_number_comparison"
    number: float
    tolerance: float = Field(1e-6, description="Absolute tolerance to use")

    def matches(self, value: float):
        return abs(self.number - value) <= self.tolerance


class GENumberComparison(CustomBaseModel):
    kind: Literal["ge_number_comparison"] = "ge_number_comparison"
    number: float

    def matches(self, value: float):
        return value >= self.number


class LENumberComparison(CustomBaseModel):
    kind: Literal["le_number_comparison"] = "le_number_comparison"
    number: float

    def matches(self, value: float):
        return value <= self.number


class RangeNumberComparison(CustomBaseModel):
    kind: Literal["range_number_comparison"] = "range_number_comparison"
    lower: float
    upper: float

    def matches(self, value: float):
        return self.lower <= value <= self.upper


class EqualDurationComparison(CustomBaseModel):
    kind: Literal["equal_duration_comparison"] = "equal_duration_comparison"
    duration: timedelta
    tolerance: timedelta = Field(
        timedelta(seconds=1), description="Absolute tolerance to use"
    )

    def matches(self, value: timedelta):
        return abs(self.duration - value) <= self.tolerance


class GEDurationComparison(CustomBaseModel):
    kind: Literal["ge_duration_comparison"] = "ge_duration_comparison"
    number: timedelta

    def matches(self, value: timedelta):
        return value >= self.number


class LEDurationComparison(CustomBaseModel):
    kind: Literal["le_duration_comparison"] = "le_duration_comparison"
    number: timedelta

    def matches(self, value: timedelta):
        return value <= self.number


class RangeDurationComparison(CustomBaseModel):
    kind: Literal["range_duration_comparison"] = "range_duration_comparison"
    lower: timedelta
    upper: timedelta

    def matches(self, value: timedelta):
        return self.lower <= value <= self.upper


class RangeDatetimeComparison(CustomBaseModel):
    kind: Literal["range_datetime_comparison"] = "range_datetime_comparison"
    lower: datetime
    upper: datetime

    def matches(self, value: datetime):
        return self.lower <= value <= self.upper


class TimeWindowOverlapComparison(CustomBaseModel):
    kind: Literal["time_window_overlap_comparison"] = "time_window_overlap_comparison"
    start: time
    end: time
    overlap: timedelta = Field(
        timedelta(seconds=1), description="Minimum amount of overlap to check for."
    )

    def matches(self, value: tuple[datetime, datetime]) -> bool:
        interval_start, interval_end = value
        if interval_end <= interval_start:
            return False

        total_overlap = timedelta(seconds=0)

        # Iterate day-by-day over the interval duration
        current_date = interval_start.date()
        end_date = interval_end.date() + timedelta(days=1)

        while current_date <= end_date:
            # Construct window for current day (handling overnight windows like 22:00 - 06:00)
            window_start = datetime.combine(current_date, self.start)
            window_end = datetime.combine(current_date, self.end)

            if window_end <= window_start:
                window_end += timedelta(days=1)

            # Intersection of [interval_start, interval_end] and [window_start, window_end]
            overlap_start = max(interval_start, window_start)
            overlap_end = min(interval_end, window_end)

            if overlap_end > overlap_start:
                total_overlap += overlap_end - overlap_start
                if total_overlap >= self.overlap:
                    return True

            current_date += timedelta(days=1)

        return False


class EqualSetComparison(CustomBaseModel):
    kind: Literal["equal_set_comparison"] = "equal_set_comparison"
    items: set[Hashable]

    def matches(self, value: Iterable[Any]):
        return self.items == set(value)


class WithinSetComparison(CustomBaseModel):
    kind: Literal["within_set_comparison"] = "within_set_comparison"
    items: set[Hashable]

    def matches(self, value: Iterable[Any]):
        return set(value).issubset(self.items)


class ContainSetComparison(CustomBaseModel):
    kind: Literal["contain_set_comparison"] = "contain_set_comparison"
    items: set[Hashable]

    def matches(self, value: Iterable[Any]):
        return set(value).issuperset(self.items)


Comparison = Annotated[
    EqualNumberComparison
    | LENumberComparison
    | GENumberComparison
    | RangeNumberComparison
    | EqualDurationComparison
    | LEDurationComparison
    | GEDurationComparison
    | RangeDurationComparison
    | RangeDatetimeComparison
    | TimeWindowOverlapComparison
    | EqualSetComparison
    | WithinSetComparison
    | ContainSetComparison,
    Field(discriminator="kind"),
]


class Condition[C](CustomBaseModel):
    """C constraints the fields allowed (scoping to the object's available fields)"""

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


class Value(CustomBaseModel):
    phrase: str = "Matched"


class NumberValue(Value):
    number: float


class DurationValue(Value):
    duration: timedelta


class NumberRangeValue(Value):
    lower: float
    upper: float


class DurationRangeValue(Value):
    lower: timedelta
    upper: timedelta


class ApplicableValue(Value):
    applicable: bool


class FieldValue(Value):
    field: str


CalculationValue = (
    NumberValue
    | DurationValue
    | FieldValue
    | NumberRangeValue
    | DurationRangeValue
    | ApplicableValue
)


class ConditionValue[C, V](CustomBaseModel):
    condition: list[Condition[C]] = Field(
        description="All conditions must be met together (AND)."
    )
    value: Value[V]

    def matches(self, obj):
        return all(c.matches(obj) for c in self.condition)


class DecisionTable[C, V](CustomBaseModel):
    default: Value
    items: list[ConditionValue[C, V]] = Field(default_factory=list)

    def get_matching_value(self, obj):
        for item in self.items:
            if item.matches(obj):
                return item.value
        return self.default


class Update[C, V](CustomBaseModel):
    name: str
    method: Literal["set", "add", "max", "min"] = "set"
    table: DecisionTable[C, V]


class Rule[C](CustomBaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    rule_type: str
    input: str
    applicability: DecisionTable[C, ApplicableValue]
    value: DecisionTable[C, CalculationValue]
    value_updates: list[Update[C, CalculationValue]] = Field(default_factory=list)
    requirement: DecisionTable[C, CalculationValue] | None = None
    requirement_updates: list[Update[C, CalculationValue]] = Field(default_factory=list)
    limit: DecisionTable[C, CalculationValue] | None = None
    limit_updates: list[Update[C, CalculationValue]] = Field(default_factory=list)
