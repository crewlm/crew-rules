from typing import Literal, Any, Hashable, Iterable, Annotated
from pydantic import Field
from datetime import datetime, timedelta, time
import re
from functools import cached_property

from utilities.pydantic import CustomBaseModel


def _timedelta_to_iso8601(td: timedelta) -> str:
    # Extract total seconds and handle negative durations if necessary
    total_seconds = int(td.total_seconds())
    days = td.days

    # Extract hours, minutes, and seconds from the remaining seconds of the day
    remaining_seconds = total_seconds % 86400
    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    seconds = remaining_seconds % 60

    # Build date and time components
    date_part = f"{days}D" if days else ""
    time_part = ""
    if hours or minutes or seconds:
        time_part = "T"
        if hours:
            time_part += f"{hours}H"
        if minutes:
            time_part += f"{minutes}M"
        if seconds:
            time_part += f"{seconds}S"

    return f"P{date_part}{time_part}"


class EqualNumberComparison(CustomBaseModel):
    kind: Literal["equal_number_comparison"] = "equal_number_comparison"
    number: float
    tolerance: float = Field(1e-6, description="Absolute tolerance to use")

    def matches(self, value: float):
        return abs(self.number - value) <= self.tolerance

    def __str__(self):
        return f"is equal to {self.number}"


class GENumberComparison(CustomBaseModel):
    kind: Literal["ge_number_comparison"] = "ge_number_comparison"
    number: float

    def matches(self, value: float):
        return value >= self.number

    def __str__(self):
        return f"is greater than or equal to {self.number}"


class LENumberComparison(CustomBaseModel):
    kind: Literal["le_number_comparison"] = "le_number_comparison"
    number: float

    def matches(self, value: float):
        return value <= self.number

    def __str__(self):
        return f"is less than or equal to {self.number}"


class GTNumberComparison(CustomBaseModel):
    kind: Literal["gt_number_comparison"] = "gt_number_comparison"
    number: float

    def matches(self, value: float):
        return value > self.number

    def __str__(self):
        return f"is greater than {self.number}"


class LTNumberComparison(CustomBaseModel):
    kind: Literal["lt_number_comparison"] = "lt_number_comparison"
    number: float

    def matches(self, value: float):
        return value < self.number

    def __str__(self):
        return f"is less than {self.number}"


class RangeNumberComparison(CustomBaseModel):
    kind: Literal["range_number_comparison"] = "range_number_comparison"
    lower: float
    upper: float

    def matches(self, value: float):
        return self.lower <= value <= self.upper

    def __str__(self):
        return f"is within range {self.lower} to {self.upper}"


class EqualDurationComparison(CustomBaseModel):
    kind: Literal["equal_duration_comparison"] = "equal_duration_comparison"
    duration: timedelta
    tolerance: timedelta = Field(
        timedelta(seconds=1), description="Absolute tolerance to use"
    )

    def matches(self, value: timedelta):
        return abs(self.duration - value) <= self.tolerance

    def __str__(self):
        return f"is equal to {_timedelta_to_iso8601(self.duration)}"


class EqualTextComparison(CustomBaseModel):
    kind: Literal["equal_text_comparison"] = "equal_text_comparison"
    text: str
    case_sensitive: bool = True

    def model_post_init(self, context):
        if not self.case_sensitive:
            self.text = self.text.lower()
        return super().model_post_init(context)

    def matches(self, value: str):
        if not self.case_sensitive:
            return self.text == value.lower()
        return self.text == value

    def __str__(self):
        return f"is equal to '{self.text}' (case-{'' if self.case_sensitive else 'in'}sensitive)"


class RegexTextComparison(CustomBaseModel):
    kind: Literal["regex_text_comparison"] = "regex_text_comparison"
    expression: str

    @cached_property
    def _regex_compiled(self):
        return re.compile(self.expression)

    def matches(self, value: str):
        return self._regex_compiled.search(value) is not None

    def __str__(self):
        return f"matches regular expression '{self.expression}'"


class GEDurationComparison(CustomBaseModel):
    kind: Literal["ge_duration_comparison"] = "ge_duration_comparison"
    duration: timedelta

    def matches(self, value: timedelta):
        return value >= self.duration

    def __str__(self):
        return f"is greater than or equal to {_timedelta_to_iso8601(self.duration)}"


class LEDurationComparison(CustomBaseModel):
    kind: Literal["le_duration_comparison"] = "le_duration_comparison"
    duration: timedelta

    def matches(self, value: timedelta):
        return value <= self.duration

    def __str__(self):
        return f"is less than or equal to {_timedelta_to_iso8601(self.duration)}"


class GTDurationComparison(CustomBaseModel):
    kind: Literal["gt_duration_comparison"] = "gt_duration_comparison"
    duration: timedelta

    def matches(self, value: timedelta):
        return value >= self.duration

    def __str__(self):
        return f"is greater than {_timedelta_to_iso8601(self.duration)}"


class LTDurationComparison(CustomBaseModel):
    kind: Literal["lt_duration_comparison"] = "lt_duration_comparison"
    duration: timedelta

    def matches(self, value: timedelta):
        return value <= self.duration

    def __str__(self):
        return f"is less than {_timedelta_to_iso8601(self.duration)}"


class RangeDurationComparison(CustomBaseModel):
    kind: Literal["range_duration_comparison"] = "range_duration_comparison"
    lower: timedelta
    upper: timedelta

    def matches(self, value: timedelta):
        return self.lower <= value <= self.upper

    def __str__(self):
        return f"is within range {_timedelta_to_iso8601(self.lower)} to {_timedelta_to_iso8601(self.upper)}"


class RangeDatetimeComparison(CustomBaseModel):
    kind: Literal["range_datetime_comparison"] = "range_datetime_comparison"
    lower: datetime
    upper: datetime

    def matches(self, value: datetime):
        return self.lower <= value <= self.upper

    def __str__(self):
        return f"is within range {self.lower.isoformat()} to {self.upper.isoformat()}"


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

    def __str__(self):
        return f"has overlap of {_timedelta_to_iso8601(self.overlap)} or more with {self.start.strftime('%H:%M:%S')} to {self.end.strftime('%H:%M:%S')}"


class TruthComparison(CustomBaseModel):
    kind: Literal["truth_comparison"] = "truth_comparison"

    def matches(self, value: Any):
        return bool(value)

    def __str__(self):
        return f"is true"


class FalseComparison(CustomBaseModel):
    kind: Literal["false_comparison"] = "false_comparison"

    def matches(self, value: Any):
        return not bool(value)

    def __str__(self):
        return f"is false"


class EqualSetComparison(CustomBaseModel):
    kind: Literal["equal_set_comparison"] = "equal_set_comparison"
    items: set[Hashable]

    def matches(self, value: Iterable[Any]):
        return self.items == set(value)

    def __str__(self):
        return f"is equal to {', '.join(map(str, self.items))}"


class WithinSetComparison(CustomBaseModel):
    kind: Literal["within_set_comparison"] = "within_set_comparison"
    items: set[Hashable]

    def matches(self, value: Iterable[Any]):
        return set(value).issubset(self.items)

    def __str__(self):
        return f"is a subset of {', '.join(map(str, self.items))}"


class ContainSetComparison(CustomBaseModel):
    kind: Literal["contain_set_comparison"] = "contain_set_comparison"
    items: set[Hashable]

    def matches(self, value: Iterable[Any]):
        return set(value).issuperset(self.items)

    def __str__(self):
        return f"contains all the following items: {', '.join(map(str, self.items))}"


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
    | LTDurationComparison
    | GTDurationComparison
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
