"""Documentary Rule objects for split-duty requirements and constraints."""

from datetime import timedelta
from uuid import UUID, uuid5, NAMESPACE_URL

from models.comparison import (
    EqualTextComparison,
    FalseComparison,
    GENumberComparison,
    LTNumberComparison,
    TruthComparison,
)
from models.decision_table.condition import Condition
from models.decision_table.decision_table import ConditionValue, DecisionTable
from models.decision_table.value import (
    ApplicableValue,
    DurationValue,
    FieldValue,
    NumberValue,
    NoneValue,
    NullableCalculationValue,
)
from models.entity import Duty
from models.rule import DutyRule
from models.update import Update

_NAMESPACE = uuid5(NAMESPACE_URL, "https://crew-rules.example/easa-ftl/documentary")


def _id(name: str) -> UUID:
    return uuid5(_NAMESPACE, f"f08:{name}")


def _claimed_condition() -> Condition[Duty]:
    return Condition[Duty](
        field="duty.split_duty_extension_claimed",
        comparison=TruthComparison(),
    )


def _claimed() -> DecisionTable[Duty, ApplicableValue]:
    return DecisionTable[Duty, ApplicableValue](
        default=ApplicableValue(applicable=False, phrase="No split-duty extension claimed"),
        items=[
            ConditionValue[Duty, ApplicableValue](
                condition=[_claimed_condition()],
                value=ApplicableValue(applicable=True, phrase="Split-duty extension claimed"),
            )
        ],
    )


def _conditional_applicability(
    conditions: list[Condition[Duty]], phrase: str
) -> DecisionTable[Duty, ApplicableValue]:
    return DecisionTable[Duty, ApplicableValue](
        default=ApplicableValue(applicable=False, phrase="Condition does not apply"),
        items=[
            ConditionValue[Duty, ApplicableValue](
                condition=[_claimed_condition(), *conditions],
                value=ApplicableValue(applicable=True, phrase=phrase),
            )
        ],
    )


def _zero_count_rule(name: str, title: str, path: str) -> DutyRule:
    return DutyRule(
        id=_id(name),
        name=title,
        applicability=_claimed(),
        value=DecisionTable[Duty, FieldValue](default=FieldValue(field=path, phrase=title)),
        limit=DecisionTable[Duty, NumberValue](default=NumberValue(number=0, phrase="No prohibited occurrences")),
    )


def build() -> dict:
    c = Duty
    full_fdp = DutyRule(
        id=_id("full-fdp-includes-break"),
        name="Full FDP is at least the interval without the break plus the complete split-duty break",
        applicability=_claimed(),
        value=DecisionTable[c, FieldValue](default=FieldValue(field="fdp.duration")),
        requirement=DecisionTable[c, FieldValue](default=FieldValue(field="fdp.duration_without_split_break")),
        requirement_updates=[
            Update[c, NullableCalculationValue](
                name="Include the complete break duration",
                method="increase",
                table=DecisionTable[c, NullableCalculationValue](
                    default=FieldValue(field="split_break.duration")
                ),
            )
        ],
    )
    extension_credit_table = DecisionTable[c, NullableCalculationValue](
        default=NoneValue(),
        items=[
            ConditionValue[c, NullableCalculationValue](
                condition=[
                    Condition[c](
                        field="split_break.suitable_accommodation",
                        comparison=TruthComparison(),
                    )
                ],
                value=FieldValue(
                    field="split_break.qualified_duration",
                    multiplier=0.5,
                    phrase="Half of qualified break when suitable accommodation is provided",
                ),
            ),
            ConditionValue[c, NullableCalculationValue](
                condition=[
                    Condition[c](
                        field="split_break.suitable_accommodation",
                        comparison=FalseComparison(),
                    )
                ],
                value=FieldValue(
                    field="split_break.other_accommodation_extension_eligible.duration",
                    multiplier=0.5,
                    phrase="Half of eligible break in other cases after CS FTL.1.220(e) exclusions",
                ),
            ),
        ],
    )
    extension = DutyRule(
        id=_id("extension-credit"),
        name="FDP with split duty is no more than the basic maximum plus half the eligible break",
        applicability=_claimed(),
        value=DecisionTable[c, FieldValue](
            default=FieldValue(field="fdp.duration")
        ),
        limit=DecisionTable[c, FieldValue](
            default=FieldValue(field="fdp.basic_maximum.duration")
        ),
        limit_updates=[
            Update[c, NullableCalculationValue](
                name="Add up to 50 percent of the extension-eligible break",
                method="increase",
                table=extension_credit_table,
            )
        ],
    )
    suitable_trigger = DecisionTable[c, ApplicableValue](
        default=ApplicableValue(applicable=False, phrase="No suitable-accommodation trigger"),
        items=[
            ConditionValue[c, ApplicableValue](
                condition=[_claimed_condition(), Condition[c](field="split_break.duration", comparison=GENumberComparison(number=6))],
                value=ApplicableValue(applicable=True, phrase="Break is at least six hours"),
            ),
            ConditionValue[c, ApplicableValue](
                condition=[_claimed_condition(), Condition[c](field="split_break.encroaches_wocl", comparison=TruthComparison())],
                value=ApplicableValue(applicable=True, phrase="Break encroaches WOCL"),
            ),
        ],
    )
    suitable_accommodation = DutyRule(
        id=_id("suitable-accommodation-trigger"),
        name="Suitable accommodation is provided for a break of at least six hours or any break encroaching WOCL",
        applicability=suitable_trigger,
        value=DecisionTable[c, FieldValue](
            default=FieldValue(field="split_break.suitable_accommodation_missing.count", phrase="Crew members without required suitable accommodation")
        ),
        limit=DecisionTable[c, NumberValue](default=NumberValue(number=0, phrase="None")),
    )
    other_accommodation = DutyRule(
        id=_id("other-accommodation"),
        name="Accommodation is provided for other split-duty breaks",
        applicability=_conditional_applicability(
            [
                Condition[c](field="split_break.duration", comparison=LTNumberComparison(number=6)),
                Condition[c](field="split_break.encroaches_wocl", comparison=FalseComparison()),
            ],
            "Break is under six hours and does not encroach WOCL",
        ),
        value=DecisionTable[c, FieldValue](
            default=FieldValue(field="split_break.accommodation_missing.count", phrase="Crew members without accommodation")
        ),
        limit=DecisionTable[c, NumberValue](default=NumberValue(number=0, phrase="None")),
    )
    qualified_break_minimum = DutyRule(
        id=_id("qualified-break-minimum"),
        name="Split-duty break contains at least three consecutive qualified hours",
        applicability=_claimed(),
        value=DecisionTable[c, FieldValue](
            default=FieldValue(field="split_break.qualified_duration")
        ),
        requirement=DecisionTable[c, DurationValue](
            default=DurationValue(duration=timedelta(hours=3), phrase="Three consecutive hours")
        ),
    )
    excluded_minimum = DutyRule(
        id=_id("excluded-time-minimum"),
        name="Operator-specified pre-flight, post-flight, and travel exclusions total at least 30 minutes",
        applicability=_claimed(),
        value=DecisionTable[c, FieldValue](default=FieldValue(field="split_break.excluded_duty_and_travel.duration")),
        requirement=DecisionTable[c, DurationValue](default=DurationValue(duration=timedelta(minutes=30))),
    )
    rest_constraint = _zero_count_rule(
        "no-reduced-rest-before-split",
        "No split-duty occurrence follows reduced rest",
        "split_duty.following_reduced_rest_occurrences.count",
    )
    extension_constraint = _zero_count_rule(
        "extension-combination-prohibitions",
        "No prohibited split-duty and in-flight-rest or basic-extension combination occurs",
        "duty.prohibited_split_or_inflight_extension_combinations.count",
    )
    basic_combination = _zero_count_rule(
        "basic-extension-combination-prohibition",
        "No basic daily extension is combined with split duty or in-flight-rest extension",
        "duty.basic_extension_with_split_or_inflight_extension_occurrences.count",
    )
    rules = [
        full_fdp,
        extension,
        suitable_accommodation,
        other_accommodation,
        excluded_minimum,
        qualified_break_minimum,
        rest_constraint,
        extension_constraint,
        basic_combination,
    ]
    return {
        "number": 8,
        "slug": "split_duty",
        "title": "Split duty",
        "rules": rules,
        "projections": [],
        "concepts": {
            "fdp.duration": {"meaning": "Full FDP duration including every split-duty break.", "unit": "hours"},
            "fdp.duration_without_split_break": {"meaning": "FDP duration excluding the full break interval, used to express break inclusion.", "unit": "hours"},
            "fdp.basic_maximum.duration": {"meaning": "Applicable basic daily maximum FDP before the split-duty extension.", "unit": "hours"},
            "split_break.duration": {"meaning": "Full break interval within the FDP; it remains counted in full as FDP.", "unit": "hours"},
            "split_break.qualified_duration": {"meaning": "Consecutive task-free break after operator-specified pre-flight, post-flight, and travel exclusions; at least three hours.", "unit": "hours"},
            "split_break.excluded_duty_and_travel.duration": {"meaning": "Combined operator-specified time excluded from the break for pre-flight duties, post-flight duties, and travel; minimum 30 minutes.", "unit": "hours"},
            "split_break.other_accommodation_extension_eligible.duration": {
                "meaning": "For CS FTL.1.220(e) cases only, creditable actual break duration after excluding time beyond six hours and time overlapping WOCL.",
                "unit": "hours",
            },
            "split_break.encroaches_wocl": {"meaning": "Whether the break overlaps WOCL, 02:00–05:59 in the crew member's acclimatised time zone."},
            "duty.split_duty_extension_claimed": {"meaning": "Whether an extension due to split duty is claimed for this duty."},
            "split_break.suitable_accommodation": {"meaning": "Whether suitable accommodation is provided for this break."},
            "split_break.suitable_accommodation_missing.count": {"meaning": "Crew members lacking required suitable accommodation for a triggered break.", "unit": "crew members"},
            "split_break.accommodation_missing.count": {"meaning": "Crew members lacking accommodation in other split-duty cases.", "unit": "crew members"},
            "split_duty.following_reduced_rest_occurrences.count": {"meaning": "Occurrences of split duty immediately following reduced rest.", "unit": "count"},
            "duty.prohibited_split_or_inflight_extension_combinations.count": {"meaning": "Occurrences combining split duty with in-flight rest.", "unit": "count"},
            "duty.basic_extension_with_split_or_inflight_extension_occurrences.count": {"meaning": "Occurrences combining a basic daily extension with split-duty or in-flight-rest extension.", "unit": "count"},
        },
        "represented": [
            "Minimum three consecutive net break hours",
            "Lower-bound FDP consistency constraint adds the full break to the interval without it; it does not derive exact FDP from the timeline",
            "Maximum extension is half of the eligible break added to the applicable basic FDP maximum",
            "Operator-specified exclusions total at least 30 minutes",
            "Suitable accommodation is required at six hours or more or on any WOCL overlap; accommodation is required otherwise",
            "In CS FTL.1.220(e) other-break cases only, time beyond six hours or overlapping WOCL is excluded from extension-credit duration; the suitable-accommodation branch uses qualified break duration",
            "Reduced-rest and extension-combination prohibitions are represented as zero-occurrence constraints",
        ],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings"],
        "sources": [
            "ORO.FTL.220, Revision 24 (March 2026), p. 870.",
            "CS FTL.1.220, Revision 24, p. 882.",
            "ORO.FTL.105(6), (4), (3), (28), Revision 24, pp. 854–856.",
            "ORO.FTL.205(d)(4), Revision 24, p. 867.",
            "GM1 CS FTL.1.220(b), Revision 24, p. 882.",
        ],
    }
