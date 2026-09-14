"""
Different models.
"""

from typing import Literal, Any, Annotated, TypeVar, Iterable
from functools import cached_property
from operator import attrgetter
from uuid import uuid4, UUID
from datetime import datetime, timedelta, time
from pydantic import Field, TypeAdapter

from utilities.pydantic import CustomBaseModel
from utilities.formatters import timedelta_to_iso8601, format_field
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
from comparisons import Comparison


def _convert_to_float(val: Any, null_replacement: float | None = None) -> float | None:
    if val is None:
        return null_replacement
    elif isinstance(val, float):
        return val
    elif isinstance(val, (str, bytes, bytearray)):
        return ord(val)
    elif isinstance(val, Iterable):
        return len(val)
    elif isinstance(val, int):
        return float(val)
    elif isinstance(val, datetime):
        return val.timestamp()
    elif isinstance(val, timedelta):
        return val.total_seconds() / 3600.0
    elif isinstance(val, time):
        return val.hour + val.minute / 60.0 + val.second / 3600.0
    return None


class Condition[C](CustomBaseModel):
    """TODO: C constrains the fields allowed (scoping to the object's available fields)"""

    field: str = Field(
        description="Dot-separated field, accessing object's field using dot notation."
    )
    comparison: Comparison = Field(description="Comparison to make")
    reverse_match: bool = Field(False, description="TRUE inverts the match")

    def get_generic_param_name(self) -> str:
        # TODO: This returns C not the actual class name
        # Loop through the class MRO to find who defined the [C] parameter
        for cls in self.__class__.__mro__:
            if hasattr(cls, "__type_params__") and cls.__type_params__:
                return cls.__type_params__[0].__name__
        return "Entity"

    @cached_property
    def _field_getter(self):
        return attrgetter(self.field)

    def matches(self, obj):
        value = self._field_getter(obj)
        comparison_match = self.comparison.matches(value)
        return (not comparison_match) if self.reverse_match else comparison_match

    def __str__(self):
        entity_name = self.get_generic_param_name()
        op = "is not" if self.reverse_match else "is"
        return f"{format_field(entity_name, self.field)} {op} {str(self.comparison)}"


class Value(CustomBaseModel):
    phrase: str = "Matched"

    def get_calculated_value(self, obj: Any):
        """Subclasses should implement this interface"""
        raise NotImplementedError

    def __str__(self):
        """Subclasses implement this for displaying to user"""
        raise NotImplementedError


class NumberValue(Value):
    kind: Literal["number_value"] = "number_value"
    number: float

    def get_calculated_value(self, obj):
        return self.number

    def __str__(self):
        return f"{self.number:g}"


class DurationValue(Value):
    kind: Literal["duration_value"] = "duration_value"
    duration: timedelta

    def get_calculated_value(self, obj):
        return self.duration.total_seconds() / 3600.0

    def __str__(self):
        return timedelta_to_iso8601(self.duration)


class NumberRangeValue(Value):
    kind: Literal["number_range_value"] = "number_range_value"
    lower: float
    upper: float

    def get_calculated_value(self, obj):
        return (self.lower, self.upper)

    def __str__(self):
        return f"{self.lower:g} to {self.upper:g}"


class DurationRangeValue(Value):
    kind: Literal["duration_range_value"] = "duration_range_value"
    lower: timedelta
    upper: timedelta

    def get_calculated_value(self, obj):
        return (
            self.lower.total_seconds() / 3600.0,
            self.upper.total_seconds() / 3600.0,
        )

    def __str__(self):
        return (
            f"{timedelta_to_iso8601(self.lower)} to {timedelta_to_iso8601(self.upper)}"
        )


class ApplicableValue(Value):
    kind: Literal["applicable_value"] = "applicable_value"
    applicable: bool

    def get_calculated_value(self, obj):
        return self.applicable

    def __str__(self):
        return "Applicable" if self.applicable else "Not applicable"


class NoneValue(Value):
    kind: Literal["none_value"] = "none_value"
    phrase: str = "No modification"

    def get_calculated_value(self, obj: Any):
        return None

    def __str__(self):
        return "Do nothing"

    def __bool__(self):
        return False


class FieldDifferenceValue(Value):
    kind: Literal["field_difference_value"] = "field_difference_value"
    start_field: str
    end_field: str
    multiplier: float = 1.0
    offset: float = 0.0
    clamp_lower: float | None = None
    clamp_upper: float | None = None

    @cached_property
    def _start_field_getter(self):
        if self.start_field is None:
            return lambda x: 0.0
        return attrgetter(self.start_field)

    @cached_property
    def _end_field_getter(self):
        if self.end_field is None:
            return lambda x: 0.0
        return attrgetter(self.end_field)

    def get_calculated_value(self, obj):
        val_start = self._start_field_getter(obj)
        val_end = self._end_field_getter(obj)
        # convert from everything else to float
        val_start = _convert_to_float(val_start)
        if val_start is None:
            raise ValueError(
                f"Cannot convert start field to number: {self.start_field}"
            )
        val_end = _convert_to_float(val_end)
        if val_end is None:
            raise ValueError(f"Cannot convert end field to number: {self.end_field}")
        #
        val = self.multiplier * (val_end - val_start) + self.offset
        if self.clamp_lower is not None and self.clamp_lower > val:
            val = self.clamp_lower
        if self.clamp_upper is not None and self.clamp_upper < val:
            val = self.clamp_upper
        return val

    def __str__(self):
        text = f"From {format_field("", self.start_field)} to {format_field("", self.end_field)}"

        if abs(self.multiplier - 1) > 1e-6:
            text += f", multiplied by {self.multiplier}"

        if self.offset > 1e-6:
            text += f", plus {self.offset}"
        elif self.offset < -1e-6:
            text += f", minus {-self.offset}"

        if self.clamp_lower is not None:
            text += f", clamped below at {self.clamp_lower:g}"

        if self.clamp_upper is not None:
            text += f", clamped above at {self.clamp_upper:g}"
        return text


class FieldValue(Value):
    kind: Literal["field_value"] = "field_value"
    field: str
    multiplier: float = 1.0
    offset: float = 0.0
    clamp_lower: float | None = None
    clamp_upper: float | None = None

    @cached_property
    def _field_getter(self):
        if self.field is None:
            return lambda x: 0.0
        return attrgetter(self.field)

    def get_calculated_value(self, obj):
        val = self._field_getter(obj)
        # convert from everything else to float
        val = _convert_to_float(val)
        if val is None:
            raise ValueError(f"Cannot convert field to number: {self.field}")
        #
        val = self.multiplier * val + self.offset
        if self.clamp_lower is not None and self.clamp_lower > val:
            val = self.clamp_lower
        if self.clamp_upper is not None and self.clamp_upper < val:
            val = self.clamp_upper
        return val

    def __str__(self):
        text = f"{format_field("", self.field)}"

        if abs(self.multiplier - 1) > 1e-6:
            text += f", multiplied by {self.multiplier}"

        if self.offset > 1e-6:
            text += f", plus {self.offset}"
        elif self.offset < -1e-6:
            text += f", minus {-self.offset}"

        if self.clamp_lower is not None:
            text += f", clamped below at {self.clamp_lower:g}"

        if self.clamp_upper is not None:
            text += f", clamped above at {self.clamp_upper:g}"
        return text


class LookupParameter(CustomBaseModel):
    name: str = Field(description="Name of parameter in table definition")
    field: str = Field(description="Name of entity field to use for lookup")


class TableLookupValue(Value):
    kind: Literal["table_lookup_number_value"] = "table_lookup_number_value"
    table_name: str
    lookup_map: list[LookupParameter]

    def get_calculated_value(self, obj) -> float:
        """TODO: Lookup value from table based on object properties"""
        raise NotImplementedError

    def __str__(self):
        text = f"Look up the value in {self.table_name}"
        lookups = ", ".join(
            f"{format_field("", x.field)} as {x.name}" for x in self.lookup_map
        )
        if lookups:
            text += f" using {lookups}"
        return text


CalculationValue = Annotated[
    NumberValue
    | DurationValue
    | FieldValue
    | FieldDifferenceValue
    | NumberRangeValue
    | DurationRangeValue
    | TableLookupValue,
    Field(discriminator="kind"),
]
NullableCalculationValue = Annotated[
    CalculationValue | NoneValue, Field(discriminator="kind")
]

V = TypeVar("V", bound=NullableCalculationValue)


class ConditionValue[C, V](CustomBaseModel):
    condition: list[Condition[C]] = Field(
        description="All conditions must be met together (AND)."
    )
    value: V

    def matches(self, obj):
        return all(c.matches(obj) for c in self.condition)

    def display_condition(self):
        return ",\nand ".join(str(c) for c in self.condition)

    def display_value(self):
        return str(self.value)


class DecisionTable[C, V](CustomBaseModel):
    default: V
    items: list[ConditionValue[C, V]] = Field(default_factory=list)

    def get_matching_value(self, obj):
        for item in self.items:
            if item.matches(obj):
                return item.value
        return self.default


class Update[C, V](CustomBaseModel):
    name: str
    method: Literal["set", "increase", "decrease", "max", "min", "scale"] = "set"
    table: DecisionTable[C, V]

    def apply(self, current_val: float | None, update_val: float | None) -> float:
        if current_val is None:
            current_val = 0.0
        if update_val is None:
            return current_val
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
    value_updates: list[Update[C, NullableCalculationValue]] = Field(
        default_factory=list
    )
    requirement: DecisionTable[C, CalculationValue] | None = None
    requirement_updates: list[Update[C, NullableCalculationValue]] = Field(
        default_factory=list
    )
    limit: DecisionTable[C, CalculationValue] | None = None
    limit_updates: list[Update[C, NullableCalculationValue]] = Field(
        default_factory=list
    )

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
