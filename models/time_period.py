from typing import Literal

from utilities.pydantic import CustomBaseModel


class TimePeriod(CustomBaseModel):
    anchor: Literal["day", "duty_end", "duty_start", "week", "month", "year"]
    unit: Literal["minute", "hour", "day", "month", "year"]
    duration: int
