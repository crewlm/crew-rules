"""Documentary schema for the ordinary EASA home-base rest requirement."""

from datetime import timedelta
from uuid import UUID, uuid5, NAMESPACE_URL

from models.comparison import EqualTextComparison, TruthComparison
from models.decision_table.condition import Condition
from models.decision_table.decision_table import ConditionValue, DecisionTable
from models.decision_table.value import (
    ApplicableValue,
    DurationValue,
    FieldValue,
    NullableCalculationValue,
)
from models.entity import EmployeeRestTime
from models.rule import EmployeeRestTimeRule
from models.update import Update


_RULE_NAMESPACE = uuid5(NAMESPACE_URL, "https://crew-rules.example/easa-ftl")


def _rule_id(name: str) -> UUID:
    return uuid5(_RULE_NAMESPACE, f"f05-home-rest:{name}")


def build() -> dict:
    c = EmployeeRestTime
    rule = EmployeeRestTimeRule(
        id=_rule_id("ordinary-minimum"),
        name="EASA ordinary home-base minimum rest",
        applicability=DecisionTable[c, ApplicableValue](
            default=ApplicableValue(phrase="Outside the declared home-base applicability", applicable=False),
            items=[ConditionValue[c, ApplicableValue](
                condition=[Condition[c](
                    field="succeeding_duty.base_context",
                    comparison=EqualTextComparison(text="home_base"),
                )],
                value=ApplicableValue(phrase="Succeeding FDP starts at home base", applicable=True),
            )],
        ),
        value=DecisionTable[c, FieldValue](
            default=FieldValue(
                phrase="Qualifying rest duration before succeeding FDP",
                field="rest.duration",
            )
        ),
        requirement=DecisionTable[c, DurationValue](
            default=DurationValue(
                phrase="Ordinary home-base floor",
                duration=timedelta(hours=12),
            ),
            items=[ConditionValue[c, DurationValue](
                condition=[Condition[c](
                    field="rest.accommodation_derogation_claimed",
                    comparison=TruthComparison(),
                ), Condition[c](
                    field="rest.suitable_accommodation",
                    comparison=TruthComparison(),
                )],
                value=DurationValue(
                    phrase="Home-base suitable-accommodation derogation floor",
                    duration=timedelta(hours=10),
                ),
            )],
        ),
        requirement_updates=[Update[c, NullableCalculationValue](
            name="Raise the twelve-hour floor to preceding full-duty duration",
            method="max",
            table=DecisionTable[c, NullableCalculationValue](
                default=FieldValue(
                    phrase="Preceding full-duty duration",
                    field="preceding_duty.duration",
                )
            ),
        )],
    )
    return {
        "number": 5,
        "slug": "home_rest",
        "title": "Minimum rest at home base",
        "rules": [rule],
        "projections": [],
        "concepts": {
            "succeeding_duty.base_context": {"meaning": "Whether the FDP following this rest starts at the crew member's home base; the represented rule applies when the value is home_base."},
            "rest.duration": {"meaning": "Duration of the qualifying rest interval before the succeeding home-base FDP.", "unit": "hours"},
            "preceding_duty.duration": {"meaning": "Duration of the full duty preceding the rest interval.", "unit": "hours"},
            "rest.accommodation_derogation_claimed": {"meaning": "Whether the operator claims the home-base suitable-accommodation derogation; this claim alone does not select the shorter rest floor."},
            "rest.suitable_accommodation": {"meaning": "Whether the operator provides the crew member with suitable accommodation at home base under ORO.FTL.105(4): a separate room in a quiet environment, equipped with a bed, sufficient ventilation, temperature and light controls, and access to food and drink."},
            "rest.away_route": {"meaning": "Whether rest occurs during an away-route rotation; away-route rest is outside this home-base rule family."},
        },
        "represented": ["Home-base rest before an FDP", "Ordinary branch requires at least max(preceding full-duty duration, 12 hours)", "When the derogation is claimed and suitable accommodation is provided at home base, the duration floor is 10 hours and remains subject to the preceding-full-duty maximum", "Home-base applicability guard"],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings"],
        "documentation_note": "The 10-hour branch requires both an explicit operator claim and suitable accommodation provided at home base; neither fact alone is sufficient. The relationship graph connecting this branch to the complete F06 sleep/travel group is missing, including the protected-sleep opportunity and travel/physiological allowance concepts. Away-route rest remains outside this family's scope. The schema has no data-input contract or prepared-fact validator; continuity and qualifying-rest derivation require shared temporal definitions.",
        "sources": [
            "ORO.FTL.235(a), EASA Easy Access Rules for Air Operations, Revision 24 (March 2026), PDF p. 871.",
            "GM1 ORO.FTL.235(a)(2), Revision 24, PDF p. 872.",
            "ORO.FTL.105(21), Revision 24, PDF p. 856.",
        ],
    }
