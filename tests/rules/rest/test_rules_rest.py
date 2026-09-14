from datetime import timedelta

from entities import EmployeeRestTime, Duty
from models import (
    EmployeeRestTimeRule,
    DecisionTable,
    ApplicableValue,
    DurationValue,
    FieldValue,
    AnyRule,
    ConditionValue,
    Condition,
    EqualSetComparison,
    GTNumberComparison,
    TruthComparison,
    Update,
)


def test_rest_01():
    applicability_table = DecisionTable[EmployeeRestTime, ApplicableValue](
        default=ApplicableValue(phrase="Default", applicable=True)
    )
    value_table = DecisionTable[EmployeeRestTime, FieldValue](
        default=FieldValue(phrase="Rest duration", field="duration")
    )
    requirement_table = DecisionTable[EmployeeRestTime, DurationValue](
        default=DurationValue(phrase="Default", duration=timedelta(hours=12))
    )
    rule = EmployeeRestTimeRule(
        name="test",
        applicability=applicability_table,
        value=value_table,
        requirement=requirement_table,
    )

    # Serialize to JSON
    json_data = rule.model_dump_json(indent=4)

    # Parse back using root discriminated union
    parsed_rule = AnyRule.validate_json(json_data)

    assert isinstance(parsed_rule, EmployeeRestTimeRule)
    assert parsed_rule.requirement.default.get_calculated_value(None) == timedelta(
        hours=12
    )


def test_rest_02():
    applicability_table = DecisionTable[EmployeeRestTime, ApplicableValue](
        default=ApplicableValue(phrase="Default", applicable=False),
        items=[
            ConditionValue[EmployeeRestTime, ApplicableValue](
                condition=[
                    Condition[EmployeeRestTime](
                        field="preceding.category",
                        comparison=EqualSetComparison(items={"flying"}),
                    )
                ],
                value=ApplicableValue(phrase="Flight duty", applicable=True),
            )
        ],
    )
    value_table = DecisionTable[EmployeeRestTime, FieldValue](
        default=FieldValue(phrase="Rest duration", field="duration")
    )
    requirement_table = DecisionTable[EmployeeRestTime, DurationValue](
        items=[
            ConditionValue[EmployeeRestTime, DurationValue](
                condition=[
                    Condition[EmployeeRestTime](
                        field="at_home_base",
                        comparison=TruthComparison(),
                        reverse_match=True,
                    )
                ],
                value=DurationValue(phrase="Outstation", duration=timedelta(hours=12)),
            )
        ],
        default=DurationValue(phrase="Default", duration=timedelta(hours=14)),
    )
    requirement_update_table1 = Update[EmployeeRestTime, DurationValue](
        name="Long prior FDP",
        method="increase",
        table=DecisionTable[EmployeeRestTime, DurationValue](
            default=DurationValue(duration=timedelta()),
            items=[
                ConditionValue[EmployeeRestTime, DurationValue](
                    condition=[
                        Condition[EmployeeRestTime](
                            field="preceding.calculated_numbers.fdp_exceedance",
                            comparison=GTNumberComparison(number=0),
                        )
                    ],
                    value=DurationValue(duration=timedelta(hours=1)),
                )
            ],
        ),
    )
    rule = EmployeeRestTimeRule(
        name="test",
        applicability=applicability_table,
        value=value_table,
        requirement=requirement_table,
        requirement_updates=[requirement_update_table1],
    )

    # Serialize to JSON
    json_data = rule.model_dump_json(indent=4)

    # Parse back using root discriminated union
    parsed_rule = AnyRule.validate_json(json_data)

    assert isinstance(parsed_rule, EmployeeRestTimeRule)
    assert parsed_rule.requirement.default.get_calculated_value(None) == timedelta(
        hours=14
    )
