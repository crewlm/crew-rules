"""Documentary schema for EASA ORO.FTL.210(a), (c) cumulative duty."""

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
from models.entity import Duty, EmployeeTimePeriod
from models.projection import Projection
from models.rule import EmployeeTimePeriodRule
from models.time_period import TimePeriod
from models.update import ProjectionUpdate


_NAMESPACE = UUID("87b04d04-3536-4e71-bc49-ecb905bfe3ab")


def _projection_update(code: str, category: str, rate: float) -> ProjectionUpdate[Duty]:
    return ProjectionUpdate[Duty](
        name=f"Credit {category} duty time at {rate:g}",
        method="increase",
        table=ProjectionDecisionTable[Duty](
            default=NoneValue(),
            items=[
                ProjectionConditionValue[Duty](
                    condition=[
                        Condition[Duty](
                            field="category",
                            comparison=EqualTextComparison(text=category),
                        )
                    ],
                    value=ProjectionValue(
                        start_anchor="start",
                        end_anchor="end",
                        rate=rate,
                        phrase=f"{category} duty minutes × {rate:g}; credited in hours",
                    ),
                )
            ],
        ),
    )


def _limit_rule(days: int, cap: float) -> EmployeeTimePeriodRule:
    return EmployeeTimePeriodRule(
        id=uuid5(_NAMESPACE, f"easa-orooftl210-duty-{days}-days"),
        name=f"Cumulative duty in any {days} consecutive days ≤ {cap:g} h",
        applicability=DecisionTable[EmployeeTimePeriod, ApplicableValue](
            default=ApplicableValue(applicable=True)
        ),
        value=DecisionTable[EmployeeTimePeriod, ProjectedValue](
            default=ProjectedValue(
                code="cum_duty", element="aggregate",
                phrase=f"Credited duty hours in this supplied {days}-day window",
            )
        ),
        limit=DecisionTable[EmployeeTimePeriod, DurationValue](
            default=DurationValue(duration=timedelta(hours=cap), phrase=f"{cap:g} hours")
        ),
        time_period=TimePeriod(anchor="day", unit="day", duration=days),
    )


def build() -> dict:
    projection = Projection(
        id=uuid5(_NAMESPACE, "easa-cumulative-duty-projection"),
        name="Cumulative duty credit",
        code="cum_duty",
        duty_projections=[
            _projection_update("cum_duty", "flying", 1 / 60),
            _projection_update("cum_duty", "deadhead_only", 1 / 60),
            _projection_update("cum_duty", "airport_standby", 1 / 60),
            _projection_update("cum_duty", "ground", 1 / 60),
            _projection_update("cum_duty", "simulator", 1 / 60),
            _projection_update("cum_duty", "training", 1 / 60),
            _projection_update("cum_duty", "admin", 1 / 60),
            _projection_update("cum_duty", "generic_work", 1 / 60),
            _projection_update("cum_duty", "home_standby", 1 / 240),
        ],
    )
    rules = [
        _limit_rule(7, 60),
        _limit_rule(14, 110),
        _limit_rule(28, 190),
    ]
    return {
        "number": 1,
        "slug": "cumulative-duty",
        "title": "Cumulative duty limits",
        "rules": rules,
        "projections": [projection],
        "concepts": {
            "category": {"meaning": "Duty category used to select cumulative-duty credit: flying, deadhead_only, airport_standby, ground, simulator, training, admin, generic_work, or home_standby."},
            "employee": {"meaning": "Crew member whose duty intervals contribute to the assessed cumulative-duty period."},
            "start": {"meaning": "Start instant of a consecutive-day assessment window."},
            "end": {"meaning": "End instant of a consecutive-day assessment window."},
            "cum_duty": {"meaning": "Duty credit accumulated over the declared assessment window.", "unit": "hours"},
        },
        "represented": ["ORO.FTL.210(a) cumulative limits", "ORO.FTL.210(a) requirement to spread duty as evenly as practicable, retained as a qualitative source obligation without a native qualitative Rule node", "ORO.FTL.210(c) duty credit rates", "Seven-, fourteen- and twenty-eight-day periods", "Duty projection anchors and rates"],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings", "qualitative-obligations"],
        "documentation_note": "The schema declares window anchors, period lengths, credit categories, and rates. It does not define a data-input contract or prepared-fact validator; assignment, history completeness, boundary attribution, overlap interpretation, and the separate 'spread as evenly as practicable' obligation require shared temporal and relationship definitions.",
        "sources": [
            "ORO.FTL.210(a), (c), Easy Access Rules for Air Operations Rev 24 (March 2026), PDF p. 869. Paragraph (a)'s 'spread as evenly as practicable' duty is retained as qualitative source text; the Rule schema has no native qualitative obligation node, and no numeric fairness rule or prepared compliant flag is modeled.",
            "ORO.FTL.105(10)–(11), PDF p. 855; ORO.FTL.225(c), PDF p. 870; CS FTL.1.225(b)(3), PDF p. 883.",
            "CS FTL.1.230(b), PDF p. 884: reserve time does not count as duty period for ORO.FTL.210 and ORO.FTL.235.",
        ],
    }
