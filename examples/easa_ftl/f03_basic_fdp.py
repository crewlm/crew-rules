"""Documentary schema for EASA ORO.FTL.205(b), Tables 2–4."""

from datetime import timedelta
from uuid import UUID, uuid5

from models.comparison import EqualTextComparison, RangeNumberComparison, TruthComparison
from models.decision_table.condition import Condition
from models.decision_table.decision_table import ConditionValue, DecisionTable
from models.decision_table.value import ApplicableValue, DurationValue, FieldValue
from models.entity import Duty
from models.rule import DutyRule
from models.update import Update
from models.decision_table.value import NullableCalculationValue


_NAMESPACE = UUID("87b04d04-3536-4e71-bc49-ecb905bfe3ab")

# EASA Table 2 start-time rows. The overnight 17:00–04:59 band is split at
# midnight while retaining its single source limit.
_TABLE_2_BANDS = [
    ((360, 809), 13.0), ((810, 839), 12.75), ((840, 869), 12.5),
    ((870, 899), 12.25), ((900, 929), 12.0), ((930, 959), 11.75),
    ((960, 989), 11.5), ((990, 1019), 11.25), ((1020, 1439), 11.0),
    ((0, 299), 11.0), ((300, 314), 12.0), ((315, 329), 12.25),
    ((330, 344), 12.5), ((345, 359), 12.75),
]


def _condition(field: str, comparison) -> Condition[Duty]:
    return Condition[Duty](field=field, comparison=comparison)


def _rows() -> list[ConditionValue[Duty, DurationValue]]:
    state = "acclimatisation.state"
    start = "reference_time.minute_of_day"
    frm = "frm_eligibility.safety_performance_maintained"
    sectors = "operating_sector_count"
    rows: list[ConditionValue[Duty, DurationValue]] = []

    for (lower, upper), base_hours in _TABLE_2_BANDS:
        for sector_count in range(1, 11):
            rows.append(ConditionValue[Duty, DurationValue](
                condition=[
                    _condition(state, EqualTextComparison(text="acclimatised")),
                    _condition(start, RangeNumberComparison(lower=lower, upper=upper)),
                    _condition(sectors, RangeNumberComparison(lower=sector_count, upper=sector_count)),
                ],
                value=DurationValue(
                    duration=timedelta(hours=max(9.0, base_hours - 0.5 * max(0, sector_count - 2))),
                    phrase=f"Table 2: {max(9.0, base_hours - 0.5 * max(0, sector_count - 2)):g} hours for {sector_count} operating sector(s)",
                ),
            ))

    # Tables 3 and 4 apply to unknown acclimatisation state. Table 4's
    # additional hour is represented only when the FRM qualification holds.
    for state_value, frm_eligible, base in (("unknown", False, 11.0), ("unknown", True, 12.0)):
        for sector_count in range(1, 9):
            limit = max(9.0, base - 0.5 * max(0, sector_count - 2))
            rows.append(ConditionValue[Duty, DurationValue](
                condition=[
                    _condition(state, EqualTextComparison(text=state_value)),
                    _condition(start, RangeNumberComparison(lower=0, upper=1439)),
                    _condition(sectors, RangeNumberComparison(lower=sector_count, upper=sector_count)),
                    _condition(frm, TruthComparison() if frm_eligible else _false_truth()),
                ],
                value=DurationValue(
                    duration=timedelta(hours=limit),
                    phrase=f"Table {4 if frm_eligible else 3}: {limit:g} hours for {sector_count} operating sector(s)",
                ),
            ))
    return rows


def _false_truth():
    from models.comparison import FalseComparison
    return FalseComparison()


def build() -> dict:
    cap_rule = DutyRule(
        id=uuid5(_NAMESPACE, "easa-orooftl205-basic-daily-fdp"),
        name="Basic maximum daily FDP (Tables 2, 3 and 4)",
        applicability=DecisionTable[Duty, ApplicableValue](
            default=ApplicableValue(applicable=True, phrase="Basic-FDP table rule"),
        ),
        value=DecisionTable[Duty, FieldValue](
            default=FieldValue(field="fdp.duration", phrase="Report-to-end-of-last-operating-sector FDP"),
        ),
        limit=DecisionTable[Duty, DurationValue](
            # Each declared table row is a complete source cell, including
            # sector reduction and the nine-hour floor.
            default=DurationValue(duration=timedelta(hours=9), phrase="Nine-hour floor appearing in Tables 2–4"),
            items=_rows(),
        ),
    )
    return {
        "number": 3,
        "slug": "basic-daily-fdp",
        "title": "Basic maximum daily flight duty period",
        "rules": [cap_rule],
        "projections": [],
        "concepts": {
            "fdp.duration": {"meaning": "Flight duty period from crew report to the end of the last operating sector, including qualifying pre-operating positioning.", "unit": "hours"},
            "acclimatisation.state": {"meaning": "Crew acclimatisation state used to select the basic maximum FDP table; the represented states are acclimatised and unknown."},
            "reference_time.minute_of_day": {"meaning": "FDP start expressed as minute of day at the crew member's reference time; time-zone conversion and reference-time history are not derived here.", "unit": "minute_of_day"},
            "operating_sector_count": {"meaning": "Count of operating sectors for the FDP; positioning sectors are excluded.", "unit": "sectors"},
            "frm_eligibility.safety_performance_maintained": {"meaning": "Whether the Table 4 FRM criterion is met: an implemented FRM continuously monitors whether required safety performance is maintained."},
        },
        "represented": ["Table 2 start-time bands for acclimatised crew, including all sector counts 1–10", "Table 3 limits for unknown acclimatisation state", "Table 4 limits for unknown state when FRM safety performance is maintained", "Thirty-minute reduction per operating sector above two, subject to the nine-hour floor"],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings"],
        "documentation_note": "Table values and guards are represented directly. The concepts describe symbolic facts; this module establishes no data-input contract or prepared-fact validator. Derivation and provenance of acclimatisation, reference time, FRM status, and person-specific FDP remain shared-domain concerns. The default limit records the source's nine-hour floor; the represented table guards identify the source-supported combinations.",
        "sources": [
            "ORO.FTL.205(b)(1)–(3), Easy Access Rules for Air Operations Rev 24 (March 2026), PDF pp. 865–866.",
            "ORO.FTL.105(1), (2), (12), PDF pp. 854–855; GM1–3 ORO.FTL.105(1) and GM1 ORO.FTL.105(2), PDF pp. 856–857.",
        ],
    }
