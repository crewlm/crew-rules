"""Documentary Rule and Projection objects for standby accounting."""

from datetime import timedelta
from uuid import UUID, uuid5, NAMESPACE_URL

from models.comparison import EqualTextComparison, TruthComparison
from models.decision_table.condition import Condition
from models.decision_table.decision_table import (
    ConditionValue,
    DecisionTable,
    ProjectionConditionValue,
    ProjectionDecisionTable,
)
from models.decision_table.value import (
    ApplicableValue,
    FieldValue,
    NoneValue,
    DurationValue,
    NumberValue,
    NullableCalculationValue,
    ProjectionValue,
)
from models.entity import Activity, Duty
from models.projection import Projection
from models.rule import DutyRule
from models.update import ProjectionUpdate, Update

_NAMESPACE = uuid5(NAMESPACE_URL, "https://crew-rules.example/easa-ftl/documentary")


def _id(name: str) -> UUID:
    return uuid5(_NAMESPACE, f"f09:{name}")


def _text_condition(field: str, text: str) -> Condition[Duty]:
    return Condition[Duty](field=field, comparison=EqualTextComparison(text=text))


def _applicability(*conditions: Condition[Duty]) -> DecisionTable[Duty, ApplicableValue]:
    return DecisionTable[Duty, ApplicableValue](
        default=ApplicableValue(applicable=False, phrase="Outside this standby rule's scope"),
        items=[
            ConditionValue[Duty, ApplicableValue](
                condition=list(conditions),
                value=ApplicableValue(applicable=True, phrase="Declared standby rule scope"),
            )
        ],
    )


def _duration_projection(name: str, category: str, rate: float, phrase: str) -> Projection:
    return Projection(
        id=_id(name),
        name=phrase,
        code=name.replace("f09.", ""),
        activity_projections=[
            ProjectionUpdate[Activity](
                name=phrase,
                method="increase",
                table=ProjectionDecisionTable[Activity](
                    default=NoneValue(),
                    items=[
                        ProjectionConditionValue[Activity](
                            condition=[
                                Condition[Activity](
                                    field="category",
                                    comparison=EqualTextComparison(text=category),
                                )
                            ],
                            value=ProjectionValue(rate=rate, phrase=phrase),
                        )
                    ],
                ),
            )
        ],
    )


def _reduction_update(name: str, standby_path: str, threshold: float, scope: str) -> Update[Duty, NullableCalculationValue]:
    return Update[Duty, NullableCalculationValue](
        name=name,
        method="decrease",
        table=DecisionTable[Duty, NullableCalculationValue](
            default=NoneValue(),
            items=[
                ConditionValue[Duty, NullableCalculationValue](
                    condition=[_text_condition("standby.extension_scope", scope)],
                    value=FieldValue(
                        field=standby_path,
                        offset=-threshold,
                        clamp_lower=0,
                        phrase=f"max(effective standby time − {threshold:g} hours, 0)",
                    ),
                )
            ],
        ),
    )


def build() -> dict:
    airport = _duration_projection(
        "f09.airportDuty", "airport_standby", 1 / 60, "Airport standby counts fully as duty"
    )
    other = _duration_projection(
        "f09.otherDuty", "other_standby", 1 / 240, "Other standby counts at 25 percent as duty"
    )

    airport_fdp = DutyRule(
        id=_id("airport-fdp-reduction"),
        name="Airport standby beyond four hours reduces the maximum assigned FDP",
        applicability=_applicability(
            _text_condition("standby.type", "airport_standby"),
            Condition[Duty](field="standby.assigned_fdp_started_during_standby", comparison=TruthComparison()),
        ),
        value=DecisionTable[Duty, FieldValue](default=FieldValue(field="standby.assigned_fdp.duration")),
        limit=DecisionTable[Duty, FieldValue](default=FieldValue(field="fdp.base_maximum.duration")),
        limit_updates=[
            Update[Duty, NullableCalculationValue](
                name="Subtract max(airport standby duration − 4 hours, 0)",
                method="decrease",
                table=DecisionTable[Duty, NullableCalculationValue](
                    default=FieldValue(
                        field="standby.airport.duration",
                        offset=-4,
                        clamp_lower=0,
                        phrase="max(airport standby duration − 4 hours, 0)",
                    )
                ),
            )
        ],
    )
    airport_combined = DutyRule(
        id=_id("airport-combined-cap"),
        name="Airport standby plus assigned FDP is at most 16 hours within ORO.FTL.205(b)/(d) scope",
        applicability=_applicability(
            _text_condition("standby.type", "airport_standby"),
            _text_condition("standby.assigned_fdp_rule_scope", "oro_ftl_205_b_or_d"),
        ),
        value=DecisionTable[Duty, FieldValue](default=FieldValue(field="standby.airport_plus_assigned_fdp.duration")),
        limit=DecisionTable[Duty, DurationValue](default=DurationValue(duration=timedelta(hours=16), phrase="16 hours")),
    )
    other_fdp = DutyRule(
        id=_id("other-fdp-reduction"),
        name="Other-standby FDP reduction uses the six-hour or extended eight-hour threshold",
        applicability=_applicability(_text_condition("standby.type", "other_standby")),
        value=DecisionTable[Duty, FieldValue](default=FieldValue(field="standby.assigned_fdp.duration")),
        limit=DecisionTable[Duty, FieldValue](default=FieldValue(field="fdp.base_maximum.duration")),
        limit_updates=[
            _reduction_update(
                "Subtract max(effective other standby − 6 hours, 0)",
                "standby.other.effective_duration",
                6,
                "ordinary",
            ),
            _reduction_update(
                "Subtract max(effective other standby − 8 hours, 0) for split-duty or in-flight-rest extension",
                "standby.other.effective_duration",
                8,
                "split_or_inflight_extension",
            ),
        ],
    )
    other_cap = DutyRule(
        id=_id("other-duration-cap"),
        name="Other standby is at most 16 hours",
        applicability=_applicability(_text_condition("standby.type", "other_standby")),
        value=DecisionTable[Duty, FieldValue](default=FieldValue(field="standby.other.duration")),
        limit=DecisionTable[Duty, DurationValue](default=DurationValue(duration=timedelta(hours=16), phrase="16 hours")),
    )

    return {
        "number": 9,
        "slug": "standby",
        "title": "Standby accounting and FDP impact",
        "rules": [airport_fdp, airport_combined, other_fdp, other_cap],
        "projections": [airport, other],
        "concepts": {
            "category": {"meaning": "Activity category used by standby accounting projections; relevant values are airport_standby and other_standby."},
            "standby.type": {"meaning": "Standby category: airport_standby or other_standby."},
            "standby.extension_scope": {"meaning": "Whether other standby precedes ordinary FDP or an FDP extended for split duty or in-flight rest."},
            "standby.airport.duration": {"meaning": "Airport standby interval from reporting point to the end of the notified standby period.", "unit": "hours"},
            "standby.other.duration": {"meaning": "Non-airport standby interval at home or suitable accommodation.", "unit": "hours"},
            "standby.other.effective_duration": {"meaning": "Other-standby duration after excluding the applicable 23:00–07:00 interval until first operator contact.", "unit": "hours"},
            "standby.assigned_fdp_rule_scope": {"meaning": "Whether the airport standby/FDP combination is in the cited ORO.FTL.205(b)/(d) scope."},
            "standby.assigned_fdp_started_during_standby": {"meaning": "Whether assigned FDP starts before the notified airport-standby period ends."},
            "standby.airport_plus_assigned_fdp.duration": {"meaning": "Airport standby duration plus the assigned FDP.", "unit": "hours"},
            "standby.assigned_fdp.duration": {"meaning": "Assigned FDP duration; exact start depends on airport versus other standby rules.", "unit": "hours"},
            "fdp.base_maximum.duration": {"meaning": "Applicable maximum FDP before standby reductions.", "unit": "hours"},
            "standby.first_operator_contact": {"meaning": "Time of first operator contact during other standby; controls the overnight reduction exclusion."},
            "standby.accommodation": {"meaning": "Accommodation provided to a crew member assigned airport standby."},
            "standby.operator_response_time": {"meaning": "Operator-established time from call to reporting point, allowing reasonable arrival from place of rest.", "unit": "minutes"},
            "standby_and_fdp.awake_duration": {"meaning": "Awake duration relevant to standby procedure design; this numeric duration is not checked by an individual roster Rule." , "unit": "hours"},
        },
        "represented": [
            "Airport standby receives full duty projection credit",
            "Other standby receives 25 percent duty projection credit",
            "Airport standby reduction is explicitly computed as max(airport standby duration − 4 hours, 0)",
            "Other standby reductions are explicitly computed as max(effective duration − 6 hours, 0), or max(effective duration − 8 hours, 0) for split-duty or in-flight-rest extension",
            "Airport standby plus assigned FDP has a 16-hour limit only under ORO.FTL.205(b)/(d) scope",
            "Other standby has a 16-hour maximum duration",
            "Advance notification, accommodation, follow-on rest, contact event, and reasonable response-time clauses are retained as named documentary obligations",
            "The 18-hour awake-time provision governs operator procedure design and is retained as text; no individual numeric Rule asserts that roster arithmetic proves awake time",
        ],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings", "qualitative-obligations"],
        "sources": [
            "ORO.FTL.225, Revision 24 (March 2026), pp. 870–871.",
            "CS FTL.1.225, Revision 24, pp. 882–883.",
            "ORO.FTL.105(25)–(27), (3), (4), Revision 24, pp. 854–856.",
            "GM1 CS FTL.1.225 and GM1 CS FTL.1.225(b), Revision 24, pp. 883–884.",
        ],
    }
