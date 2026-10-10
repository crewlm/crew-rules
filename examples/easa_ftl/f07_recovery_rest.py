"""Documentary rules for recurrent extended recovery rest."""

from datetime import timedelta
from uuid import UUID, uuid5, NAMESPACE_URL

from models.comparison import EqualTextComparison, GENumberComparison
from models.decision_table.condition import Condition
from models.decision_table.decision_table import ConditionValue, DecisionTable
from models.decision_table.value import ApplicableValue, DurationValue, FieldValue, NumberValue
from models.entity import EmployeeRestTime, EmployeeTimePeriod
from models.rule import EmployeeRestTimeRule, EmployeeTimePeriodRule
from models.time_period import TimePeriod

_NAMESPACE = uuid5(NAMESPACE_URL, "https://crew-rules.example/easa-ftl/documentary")


def _id(name: str) -> UUID:
    return uuid5(_NAMESPACE, f"f07:{name}")


def _rest_rule(name: str, title: str, path: str, amount: float, unit: str = "hours", maximum: bool = False):
    c = EmployeeRestTime
    if unit == "hours":
        value = DecisionTable[c, FieldValue](default=FieldValue(field=path, phrase=title))
        threshold = DurationValue(duration=timedelta(hours=amount), phrase=title)
        value_type = DurationValue
    else:
        value = DecisionTable[c, FieldValue](default=FieldValue(field=path, phrase=title))
        threshold = NumberValue(number=amount, phrase=title)
        value_type = NumberValue
    table = DecisionTable[c, value_type](default=threshold)
    return EmployeeRestTimeRule(
        id=_id(name),
        name=title,
        applicability=DecisionTable[c, ApplicableValue](
            default=ApplicableValue(applicable=True, phrase="Candidate recovery rest supplied to evaluator")
        ),
        value=value,
        **({"limit": table} if maximum else {"requirement": table}),
    )


def build() -> dict:
    c = EmployeeRestTime
    monthly = EmployeeTimePeriodRule(
        id=_id("monthly-two-local-days"),
        name="At least two recurrent recovery rests in each calendar month are extended to two local days",
        time_period=TimePeriod(anchor="month", unit="month", duration=1),
        applicability=DecisionTable[EmployeeTimePeriod, ApplicableValue](
            default=ApplicableValue(applicable=True, phrase="One calendar-month period")
        ),
        value=DecisionTable[EmployeeTimePeriod, FieldValue](
            default=FieldValue(
                field="crew.monthly_recovery_rests_with_two_local_days.count",
                phrase="Qualifying rests with two local days in this month",
            )
        ),
        requirement=DecisionTable[EmployeeTimePeriod, NumberValue](
            default=NumberValue(number=2, phrase="Two qualifying rests per month")
        ),
    )
    second_after_disruption = EmployeeRestTimeRule(
        id=_id("disruptive-second"),
        name="Second recovery rest is at least 60 hours after four or more disruptive duties",
        applicability=DecisionTable[c, ApplicableValue](
            default=ApplicableValue(applicable=False, phrase="Not the specified disruptive interval"),
            items=[
                ConditionValue[c, ApplicableValue](
                    condition=[
                        Condition[c](
                            field="rest.disruptive_duties_since_prior_rest.count",
                            comparison=GENumberComparison(number=4),
                        ),
                        Condition[c](
                            field="rest.sequence_position",
                            comparison=EqualTextComparison(text="second"),
                        ),
                    ],
                    value=ApplicableValue(applicable=True, phrase="Second rest after four or more disruptive duties"),
                )
            ],
        ),
        value=DecisionTable[c, FieldValue](default=FieldValue(field="rest.duration")),
        requirement=DecisionTable[c, DurationValue](
            default=DurationValue(duration=timedelta(hours=60), phrase="60 hours")
        ),
    )
    rules = [
        _rest_rule("duration", "Each recurrent extended recovery rest is at least 36 hours", "rest.duration", 36),
        _rest_rule("nights", "Each recurrent extended recovery rest contains two local nights", "rest.local_night_count", 2, "count"),
        _rest_rule("gap", "Gap between qualifying recovery rests is at most 168 hours", "rest.gap_from_prior_qualifying_rest.duration", 168, maximum=True),
        monthly,
        second_after_disruption,
    ]
    return {
        "number": 7,
        "slug": "recovery_rest",
        "title": "Recurrent extended recovery rest",
        "rules": rules,
        "projections": [],
        "concepts": {
            "rest.duration": {"meaning": "Continuous uninterrupted duration of one recurrent extended recovery rest.", "unit": "hours"},
            "rest.local_night_count": {"meaning": "Count of local nights contained in this rest; each local night is 8 hours falling between 22:00 and 08:00 local time.", "unit": "count"},
            "rest.gap_from_prior_qualifying_rest.duration": {"meaning": "Elapsed interval from the preceding qualifying recovery-rest end to this rest start.", "unit": "hours"},
            "crew.monthly_recovery_rests_with_two_local_days.count": {"meaning": "Number of qualifying recovery rests extended to two local days in this calendar month; a local day is 24 hours commencing at 00:00 local time.", "unit": "count"},
            "rest.disruptive_duties_since_prior_rest.count": {"meaning": "Night duties, early starts, or late finishes between the two qualifying recovery rests.", "unit": "count"},
            "rest.sequence_position": {"meaning": "Whether this candidate is the second recovery rest after the disruptive-duty interval."},
            "crew": {"meaning": "Same crew member whose rest events and intervening duties are counted."},
        },
        "represented": [
            "36-hour minimum and two local nights for each recurrent extended recovery rest",
            "168-hour maximum measured from one qualifying rest end to the next qualifying rest start",
            "Two rests extended to two local days in each calendar month, represented by an EmployeeTimePeriod month rule",
            "60-hour minimum applies to the second rest after at least four intervening disruptive duties",
            "Additional rest for time zones, FDP extensions, disruptive schedules, and home-base changes remains a distinct ORO.FTL.235(e) obligation",
            "Event qualification, same-crew correlation, local-calendar construction, and roster history require temporal relationships",
        ],
        "schema_gaps": ["shared-definitions", "rule-relationships", "temporal-collection-definitions", "source-bindings"],
        "sources": [
            "ORO.FTL.235(d)–(e), Revision 24 (March 2026), p. 872.",
            "ORO.FTL.105(15), (16), (21), (8)–(9), Revision 24, pp. 855–856.",
            "CS FTL.1.235(a), Revision 24, p. 885.",
            "GM1 ORO.FTL.230(a), Revision 24, p. 871.",
        ],
    }
