"""
Different models.
"""

from typing import Literal, Iterable, Any, Hashable, Annotated, TypeVar
from functools import cached_property
from operator import attrgetter
from uuid import uuid4, UUID
from datetime import datetime, timedelta, time
from pydantic import Field, TypeAdapter
import re

from utilities.pydantic import CustomBaseModel
from entities import (
    Activity,
    Duty,
    Pairing,
    EmployeeTimePeriod,
    EmployeeRestTime,
    EmployeeGroundTime,
    AircraftTimePeriod,
    AircraftGroundTime,
    PortTimePeriod,
)


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


class GTNumberComparison(CustomBaseModel):
    kind: Literal["gt_number_comparison"] = "gt_number_comparison"
    number: float

    def matches(self, value: float):
        return value > self.number


class LTNumberComparison(CustomBaseModel):
    kind: Literal["lt_number_comparison"] = "lt_number_comparison"
    number: float

    def matches(self, value: float):
        return value < self.number


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


class EqualTextComparison(CustomBaseModel):
    kind: Literal["equal_text_comparison"] = "equal_text_comparison"
    text: str
    case_sensitive: bool = True

    def matches(self, value: str):
        if not self.case_sensitive:
            return self.text.lower() == value.lower()
        return self.text == value


class RegexTextComparison(CustomBaseModel):
    kind: Literal["regex_text_comparison"] = "regex_text_comparison"
    expression: str

    @cached_property
    def _regex_compiled(self):
        return re.compile(self.expression)

    def matches(self, value: str):
        return self._regex_compiled.search(value) is not None


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


class TruthComparison(CustomBaseModel):
    kind: Literal["truth_comparison"] = "truth_comparison"

    def matches(self, value: Any):
        return bool(value)


class FalseComparison(CustomBaseModel):
    kind: Literal["false_comparison"] = "false_comparison"

    def matches(self, value: Any):
        return not bool(value)


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
    | EqualTextComparison
    | RegexTextComparison
    | LENumberComparison
    | GENumberComparison
    | LTNumberComparison
    | GTNumberComparison
    | RangeNumberComparison
    | EqualDurationComparison
    | LEDurationComparison
    | GEDurationComparison
    | RangeDurationComparison
    | RangeDatetimeComparison
    | TimeWindowOverlapComparison
    | EqualSetComparison
    | TruthComparison
    | FalseComparison
    | WithinSetComparison
    | ContainSetComparison,
    Field(discriminator="kind"),
]


class Condition[C](CustomBaseModel):
    """TODO: C constraints the fields allowed (scoping to the object's available fields)"""

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

    def get_calculated_value(self, obj: Any):
        """Sub classes should implement this interface"""
        raise NotImplementedError


class NumberValue(Value):
    kind: Literal["number_value"] = "number_value"
    number: float

    def get_calculated_value(self, obj):
        return self.number


class DurationValue(Value):
    kind: Literal["duration_value"] = "duration_value"
    duration: timedelta

    def get_calculated_value(self, obj):
        return self.duration


class NumberRangeValue(Value):
    kind: Literal["number_range_value"] = "number_range_value"
    lower: float
    upper: float

    def get_calculated_value(self, obj):
        return (self.lower, self.upper)


class DurationRangeValue(Value):
    kind: Literal["duration_range_value"] = "duration_range_value"
    lower: timedelta
    upper: timedelta

    def get_calculated_value(self, obj):
        return (self.lower, self.upper)


class ApplicableValue(Value):
    kind: Literal["applicable_value"] = "applicable_value"
    applicable: bool

    def get_calculated_value(self, obj):
        return self.applicable


class FieldValue(Value):
    kind: Literal["field_value"] = "field_value"
    field: str

    @cached_property
    def _field_getter(self):
        return attrgetter(self.field)

    def get_calculated_value(self, obj):
        return self._field_getter(obj)


CalculationValue = Annotated[
    NumberValue
    | DurationValue
    | FieldValue
    | NumberRangeValue
    | DurationRangeValue
    | ApplicableValue,
    Field(discriminator="kind"),
]

V = TypeVar("V", bound=CalculationValue)


class ConditionValue[C, V](CustomBaseModel):
    condition: list[Condition[C]] = Field(
        description="All conditions must be met together (AND)."
    )
    value: V

    def matches(self, obj):
        return all(c.matches(obj) for c in self.condition)


class DecisionTable[C, V](CustomBaseModel):
    default: V
    items: list[ConditionValue[C, V]] = Field(default_factory=list)

    def get_matching_value(self, obj):
        for item in self.items:
            if item.matches(obj):
                return item.value
        return self.default


N = TypeVar("N")


class Update[C, V](CustomBaseModel):
    name: str
    method: Literal["set", "increase", "decrease", "max", "min", "scale"] = "set"
    table: DecisionTable[C, V]

    def apply(self, current_val: N, update_val: N) -> N:
        match self.method:
            case "set":
                return update_val
            case "increase":
                return current_val + update_val
            case "decrease":
                return current_val - update_val
            case "max":
                return max(current_val, update_val)
            case "min":
                return min(current_val, update_val)
            case "scale":
                if isinstance(current_val, timedelta):
                    return current_val * update_val
                return current_val * update_val
            case _:
                raise ValueError(f"Unsupported method: {self.method}")


class TimePeriod(CustomBaseModel):
    anchor: Literal["day", "duty_end", "duty_start", "week", "month", "year"]
    unit: Literal["minute", "hour", "day", "month", "year"]
    duration: int


class RuleResult(CustomBaseModel):
    result: Literal["pass", "fail", "not_applicable"]
    messages: list[str]
    slack: float
    surplus: float
    base_value: float

    @property
    def slack_percent(self):
        """derive from slack and base_value"""
        raise NotImplementedError

    @property
    def surplus_percent(self):
        """derive from surplus and base_value"""
        raise NotImplementedError


class Rule[C](CustomBaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    applicability: DecisionTable[C, ApplicableValue]
    value: DecisionTable[C, CalculationValue]
    value_updates: list[Update[C, CalculationValue]] = Field(default_factory=list)
    requirement: DecisionTable[C, CalculationValue] | None = None
    requirement_updates: list[Update[C, CalculationValue]] = Field(default_factory=list)
    limit: DecisionTable[C, CalculationValue] | None = None
    limit_updates: list[Update[C, CalculationValue]] = Field(default_factory=list)

    def model_post_init(self, context):
        if self.requirement is None and len(self.requirement_updates) > 0:
            raise ValueError(
                "Must set base requirement if there are any requirement updates"
            )
        if self.limit is None and len(self.limit_updates) > 0:
            raise ValueError("Must set base limit if there are any limit updates")
        if self.limit is None and self.requirement is None:
            raise ValueError("Must have at least one of limit or requirement set")
        return super().model_post_init(context)

    def evaluate(self, obj: Any) -> RuleResult:
        """TODO: Returns a ruleresult object"""


class ActivityRule(Rule[Activity]):
    scope: Literal["activity"] = "activity"


class DutyRule(Rule[Duty]):
    scope: Literal["duty"] = "duty"


class PairingRule(Rule[Pairing]):
    scope: Literal["pairing"] = "pairing"


class EmployeeTimePeriodRule(Rule[EmployeeTimePeriod]):
    scope: Literal["employee_time_period"] = "employee_time_period"
    time_period: TimePeriod


class AircraftTimePeriodRule(Rule[AircraftTimePeriod]):
    scope: Literal["aircraft_time_period"] = "aircraft_time_period"
    time_period: TimePeriod


class EmployeeRestTimeRule(Rule[EmployeeRestTime]):
    scope: Literal["employee_rest_time_rule"] = "employee_rest_time_rule"


class EmployeeGroundTimeRule(Rule[EmployeeGroundTime]):
    scope: Literal["employee_ground_time"] = "employee_ground_time"


class AircraftGroundTimeRule(Rule[AircraftGroundTime]):
    scope: Literal["aircraft_ground_time"] = "aircraft_ground_time"


class PortTimePeriodRule(Rule[PortTimePeriod]):
    scope: Literal["port_time_period"] = "port_time_period"
    time_period: TimePeriod


_AnyRuleType = (
    ActivityRule
    | DutyRule
    | PairingRule
    | EmployeeTimePeriodRule
    | AircraftTimePeriodRule
    | EmployeeRestTimeRule
    | EmployeeGroundTimeRule
    | AircraftGroundTimeRule
    | PortTimePeriodRule
)
AnyRule: TypeAdapter[_AnyRuleType] = TypeAdapter(
    Annotated[_AnyRuleType, Field(discriminator="scope")]
)
