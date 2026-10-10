"""Documentary Rule objects for augmented FDP and in-flight rest."""

from datetime import timedelta
from uuid import UUID, uuid5, NAMESPACE_URL

from models.comparison import (
    EqualNumberComparison,
    EqualTextComparison,
    GTNumberComparison,
    LENumberComparison,
    RangeNumberComparison,
    TruthComparison,
)
from models.decision_table.condition import Condition
from models.decision_table.decision_table import ConditionValue, DecisionTable
from models.decision_table.value import (
    ApplicableValue,
    DurationValue,
    FieldValue,
    NoneValue,
    NumberValue,
    NullableCalculationValue,
)
from models.entity import Duty, EmployeeRestTime
from models.rule import DutyRule, EmployeeRestTimeRule
from models.update import Update

_NAMESPACE = uuid5(NAMESPACE_URL, "https://crew-rules.example/easa-ftl/documentary")


def _id(name: str) -> UUID:
    return uuid5(_NAMESPACE, f"f10:{name}")


def _claimed_duty_condition() -> Condition[Duty]:
    return Condition[Duty](
        field="duty.inflight_rest_augmentation_claimed",
        comparison=TruthComparison(),
    )


def _claimed_duty() -> DecisionTable[Duty, ApplicableValue]:
    return DecisionTable[Duty, ApplicableValue](
        default=ApplicableValue(applicable=False, phrase="No in-flight-rest augmentation claimed"),
        items=[
            ConditionValue[Duty, ApplicableValue](
                condition=[_claimed_duty_condition()],
                value=ApplicableValue(applicable=True, phrase="In-flight-rest augmentation claimed"),
            )
        ],
    )


def _text(field: str, value: str) -> Condition[Duty]:
    return Condition[Duty](field=field, comparison=EqualTextComparison(text=value))


def _number(field: str, value: float) -> Condition[Duty]:
    return Condition[Duty](field=field, comparison=EqualNumberComparison(number=value))


def _bonus_conditions() -> list[Condition[Duty]]:
    return [
        _claimed_duty_condition(),
        Condition[Duty](
            field="augmentation.sector_over_9h.continuous_flight.duration",
            comparison=GTNumberComparison(number=9),
        ),
        Condition[Duty](
            field="augmentation.sector_count",
            comparison=LENumberComparison(number=2),
        ),
    ]


def _bonus_limit_update() -> Update[Duty, NullableCalculationValue]:
    return Update[Duty, NullableCalculationValue](
        name="Add one hour when one sector exceeds nine continuous flight hours and the FDP has at most two sectors",
        method="increase",
        table=DecisionTable[Duty, NullableCalculationValue](
            default=NoneValue(),
            items=[
                ConditionValue[Duty, NullableCalculationValue](
                    condition=_bonus_conditions(),
                    value=DurationValue(
                        duration=timedelta(hours=1), phrase="One-hour additional cap"
                    ),
                )
            ],
        ),
    )


def _flight_crew_cap(name: str, additional_crew: int, facility_class: str, cap: int) -> DutyRule:
    return DutyRule(
        id=_id(name),
        name=f"Flight-crew maximum total FDP: {additional_crew} additional crew, {facility_class}",
        applicability=DecisionTable[Duty, ApplicableValue](
            default=ApplicableValue(applicable=False, phrase="Outside this source table cell"),
            items=[
                ConditionValue[Duty, ApplicableValue](
                    condition=[
                        _claimed_duty_condition(),
                        _number("augmentation.additional_qualified_flight_crew_count", additional_crew),
                        _text("augmentation.flight_crew.rest_facility_class", facility_class),
                    ],
                    value=ApplicableValue(applicable=True, phrase="Matching source table cell"),
                )
            ],
        ),
        value=DecisionTable[Duty, FieldValue](
            default=FieldValue(field="augmentation.extended_fdp.duration", phrase="Total extended FDP")
        ),
        limit=DecisionTable[Duty, DurationValue](
            default=DurationValue(duration=timedelta(hours=cap), phrase=f"{cap}-hour total FDP cap")
        ),
        limit_updates=[_bonus_limit_update()],
    )


def _cabin_rest_cell(name: str, low: float, high: float, facility_class: str, minimum: float | None) -> DutyRule:
    cell_conditions = [
        _claimed_duty_condition(),
        Condition[Duty](
            field="augmentation.extended_fdp.duration",
            comparison=RangeNumberComparison(lower=low, upper=high),
        ),
        _text("augmentation.cabin_crew.rest_facility_class", facility_class),
    ]
    applicability = DecisionTable[Duty, ApplicableValue](
        default=ApplicableValue(applicable=False, phrase="Outside this cabin-rest table cell"),
        items=[
            ConditionValue[Duty, ApplicableValue](
                condition=cell_conditions,
                value=ApplicableValue(applicable=True, phrase="Exact source table cell"),
            )
        ],
    )
    if minimum is None:
        return DutyRule(
            id=_id(name),
            name=f"Cabin facility {facility_class} prohibited for FDP band {low:g}–{high:g} hours",
            applicability=applicability,
            value=DecisionTable[Duty, FieldValue](
                default=FieldValue(field="augmentation.extended_fdp.duration")
            ),
            limit=DecisionTable[Duty, DurationValue](
                default=DurationValue(duration=timedelta(0), phrase="Explicitly prohibited source table cell")
            ),
        )
    return DutyRule(
        id=_id(name),
        name=f"Cabin crew minimum total in-flight rest: {facility_class}, FDP {low:g}–{high:g} hours",
        applicability=applicability,
        value=DecisionTable[Duty, FieldValue](
            default=FieldValue(field="augmentation.cabin_crew.allocated_rest.duration")
        ),
        requirement=DecisionTable[Duty, DurationValue](
            default=DurationValue(duration=timedelta(hours=minimum), phrase=f"Source minimum {minimum:g} hours")
        ),
    )


def _zero_count_constraint(name: str, title: str, path: str) -> DutyRule:
    return DutyRule(
        id=_id(name),
        name=title,
        applicability=DecisionTable[Duty, ApplicableValue](
            default=ApplicableValue(applicable=False, phrase="No augmentation claimed"),
            items=[
                ConditionValue[Duty, ApplicableValue](
                    condition=[_claimed_duty_condition()],
                    value=ApplicableValue(applicable=True, phrase="Source prohibition assessed"),
                )
            ],
        ),
        value=DecisionTable[Duty, FieldValue](default=FieldValue(field=path, phrase=title)),
        limit=DecisionTable[Duty, NumberValue](
            default=NumberValue(number=0, phrase="No prohibited occurrences")
        ),
    )


def _destination_rest() -> EmployeeRestTimeRule:
    c = EmployeeRestTime
    return EmployeeRestTimeRule(
        id=_id("destination-rest"),
        name="Destination rest is at least max(previous full duty, 14 hours)",
        applicability=DecisionTable[c, ApplicableValue](
            default=ApplicableValue(applicable=False, phrase="No in-flight-rest augmentation claimed"),
            items=[
                ConditionValue[EmployeeRestTime, ApplicableValue](
                    condition=[Condition[EmployeeRestTime](field="preceding_duty.inflight_rest_augmentation_claimed", comparison=TruthComparison())],
                    value=ApplicableValue(applicable=True, phrase="Augmented FDP destination rest"),
                )
            ]
        ),
        value=DecisionTable[c, FieldValue](default=FieldValue(field="rest.duration")),
        requirement=DecisionTable[c, DurationValue](
            default=DurationValue(duration=timedelta(hours=14), phrase="14-hour destination-rest floor")
        ),
        requirement_updates=[
            Update[c, NullableCalculationValue](
                name="At least preceding full duty",
                method="max",
                table=DecisionTable[c, NullableCalculationValue](
                    default=FieldValue(field="preceding_duty.duration")
                ),
            )
        ],
    )


def build() -> dict:
    rules = [
        _flight_crew_cap("cap-1-class-3", 1, "class_3", 14),
        _flight_crew_cap("cap-1-class-2", 1, "class_2", 15),
        _flight_crew_cap("cap-1-class-1", 1, "class_1", 16),
        _flight_crew_cap("cap-2-class-3", 2, "class_3", 15),
        _flight_crew_cap("cap-2-class-2", 2, "class_2", 16),
        _flight_crew_cap("cap-2-class-1", 2, "class_1", 17),
        DutyRule(
            id=_id("rest-facility-time-in-fdp"),
            name="All in-flight rest-facility time is included in FDP",
            applicability=_claimed_duty(),
            value=DecisionTable[Duty, FieldValue](default=FieldValue(field="fdp.duration")),
            requirement=DecisionTable[Duty, FieldValue](default=FieldValue(field="fdp.duration_without_rest_facility")),
            requirement_updates=[
                Update[Duty, NullableCalculationValue](
                    name="Include all rest-facility time",
                    method="increase",
                    table=DecisionTable[Duty, NullableCalculationValue](
                        default=FieldValue(field="augmentation.rest_facility_time.duration")
                    ),
                )
            ],
        ),
        DutyRule(
            id=_id("sector-cap"),
            name="Augmented FDP is limited to three sectors",
            applicability=_claimed_duty(),
            value=DecisionTable[Duty, FieldValue](default=FieldValue(field="augmentation.sector_count")),
            limit=DecisionTable[Duty, NumberValue](default=NumberValue(number=3)),
        ),
        DutyRule(
            id=_id("each-crew-rest"),
            name="Each crew member receives at least 90 consecutive minutes of in-flight rest",
            applicability=_claimed_duty(),
            value=DecisionTable[Duty, FieldValue](default=FieldValue(field="augmentation.crew_member.minimum_consecutive_rest.duration")),
            requirement=DecisionTable[Duty, DurationValue](default=DurationValue(duration=timedelta(minutes=90))),
        ),
        DutyRule(
            id=_id("landing-crew-rest"),
            name="Flight crew at control during landing receive two consecutive hours of in-flight rest",
            applicability=_claimed_duty(),
            value=DecisionTable[Duty, FieldValue](default=FieldValue(field="augmentation.landing_control_crew.minimum_consecutive_rest.duration")),
            requirement=DecisionTable[Duty, DurationValue](default=DurationValue(duration=timedelta(hours=2))),
        ),
        _zero_count_constraint(
            "same-flight-positioning-prohibition",
            "No crew member starts a positioning sector to become operating crew on the same flight",
            "augmentation.same_flight_positioning_to_operating_crew_occurrences.count",
        ),
        _zero_count_constraint(
            "extension-combination-prohibitions",
            "No prohibited combination of basic daily, in-flight-rest, and split-duty extensions occurs",
            "augmentation.prohibited_extension_combinations.count",
        ),
        _destination_rest(),
    ]

    bands = [
        ((0, 14.5), [1.5, 1.5, 1.5]),
        ((14 + 31 / 60, 15), [1.75, 2, 2 + 20 / 60]),
        ((15 + 1 / 60, 15.5), [2, 2 + 20 / 60, 2 + 40 / 60]),
        ((15 + 31 / 60, 16), [2.25, 2 + 40 / 60, 3]),
        ((16 + 1 / 60, 16.5), [2 + 35 / 60, 3, None]),
        ((16 + 31 / 60, 17), [3, 3 + 25 / 60, None]),
        ((17 + 1 / 60, 17.5), [3 + 25 / 60, None, None]),
        ((17 + 31 / 60, 18), [3 + 50 / 60, None, None]),
    ]
    classes = ["class_1", "class_2", "class_3"]
    for band_index, (band, minimums) in enumerate(bands):
        for facility_class, minimum in zip(classes, minimums):
            rules.append(
                _cabin_rest_cell(
                    f"cabin-{band_index}-{facility_class}",
                    band[0],
                    band[1],
                    facility_class,
                    minimum,
                )
            )

    return {
        "number": 10,
        "slug": "augmentation",
        "title": "Augmentation and in-flight rest",
        "rules": rules,
        "projections": [],
        "concepts": {
            "duty.inflight_rest_augmentation_claimed": {"meaning": "Whether an extension due to in-flight rest is claimed for this duty."},
            "preceding_duty.inflight_rest_augmentation_claimed": {"meaning": "Whether an extension due to in-flight rest was claimed before this destination rest."},
            "augmentation.additional_qualified_flight_crew_count": {"meaning": "Number of additional appropriately qualified flight crew members beyond the minimum crew.", "unit": "count"},
            "augmentation.flight_crew.rest_facility_class": {"meaning": "Flight-crew rest facility class, using the source text labels class_1, class_2, and class_3."},
            "augmentation.flight_crew.maximum_fdp.duration": {"meaning": "Maximum total FDP in the source augmentation table, not an increment to the basic FDP.", "unit": "hours"},
            "augmentation.extended_fdp.duration": {"meaning": "Actual total extended FDP including all in-flight rest-facility time.", "unit": "hours"},
            "fdp.duration": {"meaning": "Full report-to-last-operating-end FDP duration.", "unit": "hours"},
            "fdp.duration_without_rest_facility": {"meaning": "FDP duration with in-flight rest-facility time removed, used to express the source add-back requirement.", "unit": "hours"},
            "augmentation.sector_count": {"meaning": "Number of sectors in the augmented FDP.", "unit": "count"},
            "augmentation.sector_over_9h.continuous_flight.duration": {"meaning": "Continuous flight duration of a qualifying individual sector; aggregate flight time does not qualify.", "unit": "hours"},
            "augmentation.crew_member.minimum_consecutive_rest.duration": {"meaning": "Minimum consecutive in-flight rest allocated to each crew member.", "unit": "hours"},
            "augmentation.landing_control_crew.minimum_consecutive_rest.duration": {"meaning": "Consecutive in-flight rest for flight crew members at control during landing.", "unit": "hours"},
            "augmentation.cabin_crew.rest_facility_class": {"meaning": "Cabin-crew rest-facility class used to select an exact CS table cell."},
            "augmentation.cabin_crew.allocated_rest.duration": {"meaning": "Total cabin-crew in-flight rest required by the literal FDP-band and facility-class table; the source does not separately require all of this amount to be consecutive.", "unit": "hours"},
            "augmentation.same_flight_positioning_to_operating_crew_occurrences.count": {"meaning": "Occurrences of a crew member starting a positioning sector to become operating crew on the same flight.", "unit": "count"},
            "augmentation.prohibited_extension_combinations.count": {"meaning": "Occurrences of prohibited combinations among basic daily, in-flight-rest, and split-duty extensions.", "unit": "count"},
            "augmentation.rest_facility_time.duration": {"meaning": "Time spent in an in-flight rest facility; all of it counts as FDP.", "unit": "hours"},
            "rest.duration": {"meaning": "Destination rest duration after the augmented FDP.", "unit": "hours"},
            "preceding_duty.duration": {"meaning": "Preceding full duty duration used in destination-rest minimum.", "unit": "hours"},
            "augmentation.crew_member": {"meaning": "Crew-member identity for individual rest entitlements, role at landing, and facility allocation."},
            "augmentation.facility_capacity": {"meaning": "Operator/evaluator-provided usable capacity information for allocating per-person rest. This is an inferred planning aid, not a separately quoted requirement in this source excerpt.", "unit": "crew members"},
        },
        "represented": [
            "Six total flight-crew FDP caps: with one additional crew member class 3/2/1 totals are 14/15/16 hours; with two additional crew members totals are 15/16/17 hours",
            "Each of the six caps has a strict greater-than-nine-hours single-sector condition and a no-more-than-two-sector condition that increases its limit by one hour",
            "Augmented FDP sector cap of three",
            "Ninety consecutive minutes for each crew member and two consecutive hours for flight crew at control during landing",
            "Exact minute-labelled cabin-rest table, including explicit prohibited cells; the cabin-table minimum is not stated as fully consecutive",
            "Same-flight positioning and extension-combination prohibitions are explicit zero-occurrence constraints",
            "A lower-bound consistency Rule adds all rest-facility time to an FDP interval with facility time removed; it documents inclusion but does not derive an exact timeline",
            "Destination rest is max(previous full duty, 14 hours)",
            "Subminute FDP band interpretation, individual facility allocation, crew capacity, and crew-role correlation remain external; capacity is an evaluator planning input, not a separately quoted constraint",
        ],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings"],
        "sources": [
            "ORO.FTL.105(5), (19), (17), Revision 24 (March 2026), pp. 855–856.",
            "ORO.FTL.205(e), (d)(4), Revision 24, p. 867.",
            "CS FTL.1.205(c), Revision 24, pp. 876–877.",
            "CS FTL.1.220(f), Revision 24, p. 882.",
            "GM1 ORO.FTL.105(17), Revision 24, p. 858.",
            "GM1–2 CS FTL.1.205(c)(1)(ii), Revision 24, pp. 881–882.",
        ],
    }
