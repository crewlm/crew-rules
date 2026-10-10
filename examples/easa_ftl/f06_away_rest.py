"""Documentary rules for away-base rest and the suitable-accommodation branch."""

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

_NAMESPACE = uuid5(NAMESPACE_URL, "https://crew-rules.example/easa-ftl/documentary")


def _id(name: str) -> UUID:
    return uuid5(_NAMESPACE, f"f06:{name}")


def _rest_applicability() -> DecisionTable[EmployeeRestTime, ApplicableValue]:
    c = EmployeeRestTime
    return DecisionTable[c, ApplicableValue](
        default=ApplicableValue(
            applicable=False,
            phrase="Outside away-base or claimed suitable-accommodation derogation scope",
        ),
        items=[
            ConditionValue[c, ApplicableValue](
                condition=[
                    Condition[c](
                        field="succeeding_duty.base_context",
                        comparison=EqualTextComparison(text="away_base"),
                    )
                ],
                value=ApplicableValue(applicable=True, phrase="FDP starts away from home base"),
            ),
            ConditionValue[c, ApplicableValue](
                condition=[
                    Condition[c](
                        field="succeeding_duty.base_context",
                        comparison=EqualTextComparison(text="home_base"),
                    ),
                    Condition[c](
                        field="rest.accommodation_derogation_claimed",
                        comparison=TruthComparison(),
                    ),
                    Condition[c](
                        field="rest.suitable_accommodation",
                        comparison=TruthComparison(),
                    ),
                ],
                value=ApplicableValue(
                    applicable=True,
                    phrase="Home-base suitable-accommodation derogation claimed",
                ),
            ),
        ],
    )


def build() -> dict:
    c = EmployeeRestTime
    applicability = _rest_applicability()
    minimum = EmployeeRestTimeRule(
        id=_id("minimum-rest"),
        name="Away-base or suitable-accommodation-derogation rest is at least max(10 hours, preceding full duty)",
        applicability=applicability,
        value=DecisionTable[c, FieldValue](
            default=FieldValue(field="rest.duration", phrase="Qualifying rest duration")
        ),
        requirement=DecisionTable[c, DurationValue](
            default=DurationValue(
                duration=timedelta(hours=10), phrase="10-hour minimum rest duration"
            )
        ),
        requirement_updates=[
            Update[c, NullableCalculationValue](
                name="At least preceding full duty",
                method="max",
                table=DecisionTable[c, NullableCalculationValue](
                    default=FieldValue(
                        field="preceding_duty.duration",
                        phrase="Preceding full duty duration",
                    )
                ),
            )
        ],
    )
    sleep = EmployeeRestTimeRule(
        id=_id("protected-sleep"),
        name="Qualifying rest includes an eight-hour protected sleep opportunity",
        applicability=applicability,
        value=DecisionTable[c, FieldValue](
            default=FieldValue(
                field="rest.protected_sleep_opportunity.duration",
                phrase="Protected sleep opportunity",
            )
        ),
        requirement=DecisionTable[c, DurationValue](
            default=DurationValue(
                duration=timedelta(hours=8), phrase="Eight-hour sleep opportunity"
            )
        ),
    )
    return {
        "number": 6,
        "slug": "away_rest",
        "title": "Minimum rest away from home base",
        "rules": [minimum, sleep],
        "projections": [],
        "concepts": {
            "succeeding_duty.base_context": {
                "meaning": "Whether the FDP after this rest starts at home_base or away_base."
            },
            "rest.duration": {
                "meaning": "Continuous, uninterrupted qualifying rest duration.",
                "unit": "hours",
            },
            "preceding_duty.duration": {
                "meaning": "Duration of the preceding full duty, including post-flight duty.",
                "unit": "hours",
            },
            "rest.protected_sleep_opportunity.duration": {
                "meaning": "Protected sleep opportunity contained within qualifying rest; this is independent of total rest duration.",
                "unit": "hours",
            },
            "rest.accommodation_derogation_claimed": {
                "meaning": "Whether the home-base suitable-accommodation derogation is claimed; the ordinary home-base rule is outside this family."
            },
            "rest.suitable_accommodation": {
                "meaning": "Whether suitable accommodation as defined by ORO.FTL.105 is provided."
            },
            "rest.travel_to_suitable_accommodation.duration": {
                "meaning": "Travel time to suitable accommodation used by AMC1 ORO.FTL.235(b).",
                "unit": "hours",
            },
            "rest.travel_and_physiological_allowance.duration": {
                "meaning": "Source AMC expression: 1 hour + 2 × max(travel time to suitable accommodation − 0.5 hours, 0). This family records the symbolic expression but does not select its calculation order relative to the preceding-duty maximum.",
                "unit": "hours",
            },
        },
        "represented": [
            "10-hour rest floor raised to preceding full-duty duration",
            "Separate eight-hour protected sleep opportunity",
            "Applicability covers an away-base FDP and a home-base suitable-accommodation derogation when claimed and suitable accommodation is recorded",
            "The AMC travel allowance formula is retained as a source expression; its calculation order is unresolved in the cited wording and is not a schema expressiveness gap",
            "Travel allowance application and crew/rest/FDP temporal links remain external documentary interpretation and relationship work",
        ],
        "schema_gaps": [
            "shared-definitions",
            "rule-relationships",
            "temporal-collection-definitions",
            "source-bindings",
        ],
        "sources": [
            "ORO.FTL.235(a)–(b), EASA Easy Access Rules for Air Operations, Revision 24 (March 2026), p. 871.",
            "ORO.FTL.105(21), (11), (4), Revision 24, pp. 855–856.",
            "AMC1 ORO.FTL.235(b), Revision 24, p. 872.",
        ],
    }
