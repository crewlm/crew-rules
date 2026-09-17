from typing import TypeVar, Annotated, Literal, Any, Iterable, Callable
from datetime import datetime, timedelta, time
from functools import cached_property
from operator import attrgetter
from pydantic import Field

from models.entity import TimedEntity
from utilities.pydantic import CustomBaseModel
from utilities.formatters import timedelta_to_iso8601, format_field


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


class ProjectionValue(Value):
    kind: Literal["projection_value"] = "projection_value"
    start_anchor: Literal["start", "end", "field"] = "start"
    start_offset: timedelta = timedelta()
    start_field: str | None = None
    end_anchor: Literal["start", "end", "field"] = "end"
    end_offset: timedelta = timedelta()
    end_field: str | None = None
    rate: float = Field(1.0, description="Per-minute aggregation rate")
    clamp_lower: timedelta | None = Field(
        None,
        description="If provided and window from start to end is shorter than this, sets the window duration to this",
    )
    clamp_upper: timedelta | None = Field(
        None,
        description="If provided and window from start to end is longer than this, sets the window duration to this",
    )
    clamp_direction: Literal["forwards", "backwards"] = Field(
        "forwards",
        description="Clamping forwards constrains end, while clamping backwards constrains start",
    )

    @cached_property
    def _start_field_getter(self) -> Callable[[Any], datetime]:
        if self.start_field is None:
            raise ValueError("start_field cannot be null")
        return attrgetter(self.start_field)

    @cached_property
    def _end_field_getter(self) -> Callable[[Any], datetime]:
        if self.end_field is None:
            raise ValueError("end_field cannot be null")
        return attrgetter(self.end_field)

    def get_calculated_duration(self, obj: TimedEntity):
        match self.start_anchor:
            case "start":
                start = obj.get_start()
            case "end":
                start = obj.get_end()
            case "field":
                start = self._start_field_getter(obj)
            case _:
                raise NotImplementedError(
                    f"Unsupported start anchor: {self.start_anchor}"
                )

        match self.end_anchor:
            case "start":
                end = obj.get_start()
            case "end":
                end = obj.get_end()
            case "field":
                end = self._end_field_getter(obj)
            case _:
                raise NotImplementedError(f"Unsupported end anchor: {self.end_anchor}")

        start += self.start_offset
        end += self.end_offset

        match self.clamp_direction:
            case "forwards":
                if self.clamp_lower is not None:
                    end = max(end, start + self.clamp_lower)
                if self.clamp_upper is not None:
                    end = min(end, start + self.clamp_upper)
            case "backwards":
                if self.clamp_lower is not None:
                    start = min(end - self.clamp_lower, start)
                if self.clamp_upper is not None:
                    start = max(end - self.clamp_upper, start)
            case _:
                raise NotImplementedError(
                    f"Unsupported clamp direction {self.clamp_direction}"
                )

        duration = ((end - start).total_seconds() / 60.0) * self.rate
        return start, end, duration

    def get_calculated_value(self, obj: TimedEntity) -> float:
        """Returns duration from start to end"""
        _, _, duration = self.get_calculated_duration(obj)
        return duration

    def __str__(self):
        start_field = (
            f"{format_field("entity", self.start_field)}"
            if self.start_anchor == "field"
            else f"entity {self.start_anchor}"
        )
        start_def = f"Start is {start_field}"
        if self.start_offset:
            pm = "plus" if self.start_offset > timedelta() else "minus"
            start_def += f" {pm} {timedelta_to_iso8601(abs(self.start_offset))}"
        if self.clamp_direction == "backwards":
            if self.clamp_lower:
                start_def += f"; if end minus {timedelta_to_iso8601(self.clamp_lower)} is before start, set start to end minus {timedelta_to_iso8601(self.clamp_lower)}"
            if self.clamp_upper:
                start_def += f"; if end minus {timedelta_to_iso8601(self.clamp_upper)} is after start, set start to end minus {timedelta_to_iso8601(self.clamp_upper)}"

        end_field = (
            f"{format_field("entity", self.end_field)}"
            if self.end_anchor == "field"
            else f"entity {self.end_anchor}"
        )
        end_def = f"End is {end_field}"
        if self.end_offset:
            pm = "plus" if self.end_offset > timedelta() else "minus"
            end_def += f" {pm} {timedelta_to_iso8601(abs(self.end_offset))}"
        if self.clamp_direction == "forwards":
            if self.clamp_lower:
                end_def += f"; if start plus {timedelta_to_iso8601(self.clamp_lower)} is after end, set end to start plus {timedelta_to_iso8601(self.clamp_lower)}"
            if self.clamp_upper:
                end_def += f"; if start plus {timedelta_to_iso8601(self.clamp_upper)} is before end, set end to start plus {timedelta_to_iso8601(self.clamp_upper)}"

        text = f"Accumulate at a rate of {self.rate} per minute from start to end, where:\n-{start_def}\n-{end_def}"
        return text


CalculationValue = Annotated[
    NumberValue
    | DurationValue
    | FieldValue
    | FieldDifferenceValue
    | NumberRangeValue
    | DurationRangeValue
    | TableLookupValue
    | ProjectionValue,
    Field(discriminator="kind"),
]
NullableCalculationValue = Annotated[
    CalculationValue | NoneValue, Field(discriminator="kind")
]

V = TypeVar("V", bound=NullableCalculationValue)
