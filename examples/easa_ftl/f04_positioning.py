"""Documentary schema for EASA ORO.FTL.215 positioning accounting."""

from datetime import timedelta
from uuid import UUID, uuid5

from models.comparison import EqualTextComparison, TruthComparison
from models.decision_table.condition import Condition
from models.decision_table.decision_table import (
    DecisionTable,
    ProjectionConditionValue,
    ProjectionDecisionTable,
)
from models.decision_table.value import (
    ApplicableValue,
    FieldValue,
    NoneValue,
    NumberValue,
    ProjectionValue,
)
from models.entity import Activity, Duty
from models.projection import Projection
from models.rule import DutyRule
from models.update import ProjectionUpdate


_NAMESPACE = UUID("87b04d04-3536-4e71-bc49-ecb905bfe3ab")


def _positioning_projection() -> Projection:
    return Projection(
        id=uuid5(_NAMESPACE, "easa-positioning-duty-projection"),
        name="Positioning duty credit",
        code="pos_duty",
        activity_projections=[
            ProjectionUpdate[Activity](
                name="Count positioning as duty",
                method="increase",
                table=ProjectionDecisionTable[Activity](
                    default=NoneValue(),
                    items=[ProjectionConditionValue[Activity](
                        condition=[Condition[Activity](
                            field="category",
                            comparison=EqualTextComparison(text="deadhead"),
                        )],
                        value=ProjectionValue(
                            start_anchor="start",
                            end_anchor="end",
                            rate=1 / 60,
                            phrase="Positioning interval credited as duty at full duration, in hours",
                        ),
                    )],
                ),
            )
        ],
    )


def _preoperating_fdp_projection() -> Projection:
    return Projection(
        id=uuid5(_NAMESPACE, "easa-preoperating-positioning-fdp-projection"),
        name="Pre-operating positioning in FDP",
        code="pos_fdp",
        activity_projections=[
            ProjectionUpdate[Activity](
                name="Include positioning after report and before operating begins in FDP",
                method="increase",
                table=ProjectionDecisionTable[Activity](
                    default=NoneValue(),
                    items=[ProjectionConditionValue[Activity](
                        condition=[
                            Condition[Activity](field="category", comparison=EqualTextComparison(text="deadhead")),
                            Condition[Activity](field="after_required_report", comparison=TruthComparison()),
                            Condition[Activity](field="before_first_operating_sector", comparison=TruthComparison()),
                        ],
                        value=ProjectionValue(
                            start_anchor="start",
                            end_anchor="end",
                            rate=1 / 60,
                            phrase="Pre-operating positioning interval included in FDP, in hours",
                        ),
                    )],
                ),
            )
        ],
    )


def build() -> dict:
    zero_sector_credit = DutyRule(
        id=uuid5(_NAMESPACE, "easa-positioning-zero-operating-sector-credit"),
        name="Positioning contributes zero operating sectors",
        applicability=DecisionTable[Duty, ApplicableValue](
            default=ApplicableValue(applicable=True),
        ),
        value=DecisionTable[Duty, FieldValue](
            default=FieldValue(
                field="positioning.operating_sector_credit",
                phrase="Operating-sector credit attributable to positioning",
            ),
        ),
        limit=DecisionTable[Duty, NumberValue](
            default=NumberValue(number=0, phrase="Zero operating sectors"),
        ),
    )
    return {
        "number": 4,
        "slug": "positioning-accounting",
        "title": "Positioning accounting",
        "rules": [zero_sector_credit],
        "projections": [_positioning_projection(), _preoperating_fdp_projection()],
        "concepts": {
            "category": {"meaning": "Activity category; deadhead identifies a positioning activity."},
            "start": {"meaning": "Start instant of a positioning activity interval."},
            "end": {"meaning": "End instant of a positioning activity interval."},
            "after_required_report": {"meaning": "Whether the positioning interval occurs after the crew member's required report."},
            "before_first_operating_sector": {"meaning": "Whether the positioning interval occurs before the crew member begins operating."},
            "positioning.operating_sector_credit": {"meaning": "Operating-sector count attributable to positioning; ORO.FTL.215 gives positioning no operating-sector credit.", "unit": "sectors"},
            "pos_duty": {"meaning": "Duty duration credited for positioning activity intervals.", "unit": "hours"},
            "pos_fdp": {"meaning": "FDP duration credited for positioning intervals after required report and before operating begins.", "unit": "hours"},
        },
        "represented": ["Positioning counts as duty", "Positioning before operating begins and after report is included in FDP", "Positioning contributes zero operating sectors"],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings"],
        "documentation_note": "The projections declare interval anchors, full-duration rates, and the symbolic ordering guards for pre-operating FDP credit. This schema defines no data-input contract or prepared-fact validator. Timeline ordering, positioning purpose versus other transport, person-to-activity links, and the relationship to the containing FDP require shared definitions. Post-operating positioning remains duty time and does not satisfy the pre-operating FDP guards.",
        "sources": [
            "ORO.FTL.215, Easy Access Rules for Air Operations Rev 24 (March 2026), PDF p. 870.",
            "ORO.FTL.105(18), PDF p. 856.",
        ],
    }
