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
from models.entity import (
    Entity,
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
from models.comparison import Comparison
from models.decision_table.value import (
    NullableCalculationValue,
    CalculationValue,
    ApplicableValue,
)
from models.decision_table.decision_table import DecisionTable
from models.update import Update
from models.time_period import TimePeriod


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
    id: UUID = Field(default_factory=uuid4, description="UUID for rule")
    name: str = Field(description="Rule name")
    scope: Literal["entity"] = "entity"
    applicability: DecisionTable[C, ApplicableValue] = Field(title="Applicability")
    value: DecisionTable[C, CalculationValue]
    value_updates: list[Update[C, NullableCalculationValue]] = Field(
        default_factory=list
    )
    requirement: DecisionTable[C, CalculationValue] | None = Field(
        None, title="Requirement"
    )
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
