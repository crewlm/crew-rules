"""Documentary schema for EASA ORO.FTL.210(b) operating flight time."""

from datetime import timedelta
from uuid import UUID, uuid5

from models.comparison import EqualTextComparison
from models.decision_table.condition import Condition
from models.decision_table.decision_table import (
    DecisionTable,
    ProjectionDecisionTable,
    ProjectionConditionValue,
)
from models.decision_table.value import (
    ApplicableValue,
    DurationValue,
    NoneValue,
    ProjectedValue,
    ProjectionValue,
)
from models.entity import Activity, EmployeeTimePeriod
from models.projection import Projection
from models.rule import EmployeeTimePeriodRule
from models.time_period import TimePeriod
from models.update import ProjectionUpdate


_NAMESPACE = UUID("87b04d04-3536-4e71-bc49-ecb905bfe3ab")


def _operating_flight_projection() -> Projection:
    return Projection(
        id=uuid5(_NAMESPACE, "easa-operating-flight-time-projection"),
        name="Operating flight time",
        code="op_flight",
        activity_projections=[
            ProjectionUpdate[Activity](
                name="Credit operating flight block time",
                method="increase",
                table=ProjectionDecisionTable[Activity](
                    default=NoneValue(),
                    items=[
                        ProjectionConditionValue[Activity](
                            condition=[
                                Condition[Activity](
                                    field="category",
                                    comparison=EqualTextComparison(text="flight"),
                                )
                            ],
                            value=ProjectionValue(
                                start_anchor="start",
                                end_anchor="end",
                                rate=1 / 60,
                                phrase="Operating block minutes × 1/60; credited in hours",
                            ),
                        )
                    ],
                ),
            )
        ],
    )


def _limit_rule(name: str, anchor: str, unit: str, duration: int, cap: float) -> EmployeeTimePeriodRule:
    return EmployeeTimePeriodRule(
        id=uuid5(_NAMESPACE, f"easa-orooftl210-operating-flight-{anchor}-{duration}"),
        name=name,
        applicability=DecisionTable[EmployeeTimePeriod, ApplicableValue](
            default=ApplicableValue(applicable=True)
        ),
        value=DecisionTable[EmployeeTimePeriod, ProjectedValue](
            default=ProjectedValue(
                code="op_flight",
                element="aggregate",
                phrase=f"Operating flight hours in this supplied {name.lower()} window",
            )
        ),
        limit=DecisionTable[EmployeeTimePeriod, DurationValue](
            default=DurationValue(duration=timedelta(hours=cap), phrase=f"{cap:g} hours")
        ),
        time_period=TimePeriod(anchor=anchor, unit=unit, duration=duration),
    )


def build() -> dict:
    projection = _operating_flight_projection()
    rules = [
        _limit_rule("100 hours in any 28 consecutive days", "day", "day", 28, 100),
        _limit_rule("900 hours in a calendar year", "year", "year", 1, 900),
        _limit_rule("1,000 hours in any 12 consecutive calendar months", "month", "month", 12, 1000),
    ]
    return {
        "number": 2,
        "slug": "cumulative-operating-flight-time",
        "title": "Cumulative operating flight-time limits",
        "rules": rules,
        "projections": [projection],
        "concepts": {
            "category": {"meaning": "Activity category; only flight activities contribute operating flight time, while deadhead positioning is excluded."},
            "employee": {"meaning": "Crew member whose operating-sector history contributes to the assessed period."},
            "start": {"meaning": "Start instant or calendar boundary of an assessment window, according to its declared TimePeriod."},
            "end": {"meaning": "End instant or calendar boundary of an assessment window, according to its declared TimePeriod."},
            "op_flight": {"meaning": "Operating block time accumulated for the crew member over the declared assessment window.", "unit": "hours"},
        },
        "represented": ["ORO.FTL.210(b) limits of 100 hours in 28 consecutive days, 900 hours in a calendar year, and 1,000 hours in 12 consecutive calendar months", "Operating flight block-time projection at 1/60 per minute", "Rule windows retain their distinct calendar and consecutive-day anchors"],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings"],
        "documentation_note": "The 900-hour calendar-year rule is directly represented by a one-year TimePeriod and a 900-hour limit. This schema defines no data-input contract or prepared-fact validator. Crew-to-sector attribution, reserve/in-flight-rest classification, complete history, calendar boundaries, and window aggregation require shared relationship and temporal collection definitions.",
        "sources": [
            "ORO.FTL.210(b), Easy Access Rules for Air Operations Rev 24 (March 2026), PDF p. 869.",
            "ORO.FTL.105(13), (17), PDF pp. 855–856; GM1 ORO.FTL.105(17), PDF p. 858.",
        ],
    }
