from datetime import timedelta

from entities import EmployeeRestTime, Duty
from models import (
    EmployeeRestTimeRule,
    CalculationValue,
    NullableCalculationValue,
    NoneValue,
    DecisionTable,
    ApplicableValue,
    DurationValue,
    FieldValue,
    AnyRule,
    ConditionValue,
    Condition,
    Update,
)
from comparisons import (
    EqualTextComparison,
    GTNumberComparison,
    FalseComparison,
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
    assert parsed_rule.requirement.default.get_calculated_value(None) == 12.0


def test_rest_02():
    C = EmployeeRestTime
    applicability_table = DecisionTable[C, ApplicableValue](
        default=ApplicableValue(phrase="Default", applicable=False),
        items=[
            ConditionValue[C, ApplicableValue](
                condition=[
                    Condition[C](
                        field="preceding_duty.category",
                        comparison=EqualTextComparison(text="flying"),
                    )
                ],
                value=ApplicableValue(phrase="Flight duty", applicable=True),
            )
        ],
    )
    value_table = DecisionTable[C, FieldValue](
        default=FieldValue(phrase="Rest duration", field="duration")
    )
    requirement_table = DecisionTable[C, DurationValue](
        items=[
            ConditionValue[C, DurationValue](
                condition=[
                    Condition[C](
                        field="at_home_base",
                        comparison=FalseComparison(),
                    )
                ],
                value=DurationValue(phrase="Outstation", duration=timedelta(hours=12)),
            )
        ],
        default=DurationValue(phrase="Default", duration=timedelta(hours=14)),
    )
    requirement_update_table1 = Update[C, NullableCalculationValue](
        name="Long prior FDP",
        method="increase",
        table=DecisionTable[C, NullableCalculationValue](
            default=NoneValue(),
            items=[
                ConditionValue[C, DurationValue](
                    condition=[
                        Condition[C](
                            field="preceding_duty.calculated_numbers.fdp_exceedance",
                            comparison=GTNumberComparison(number=0),
                        )
                    ],
                    value=DurationValue(duration=timedelta(hours=1)),
                )
            ],
        ),
    )
    requirement_update_table2 = Update[C, NullableCalculationValue](
        name="Crossed multiple time zones",
        method="increase",
        table=DecisionTable[C, NullableCalculationValue](
            default=NoneValue(),
            items=[
                ConditionValue[C, FieldValue](
                    condition=[
                        Condition[C](
                            field="preceding_duty.calculated_numbers.time_zones_crossed",
                            comparison=GTNumberComparison(number=2),
                        )
                    ],
                    value=FieldValue(
                        field="preceding_duty.calculated_numbers.time_zones_crossed",
                        offset=-2,
                    ),
                )
            ],
        ),
    )
    rule = EmployeeRestTimeRule(
        name="test",
        applicability=applicability_table,
        value=value_table,
        requirement=requirement_table,
        requirement_updates=[requirement_update_table1, requirement_update_table2],
    )

    # Serialize to JSON
    json_data = rule.model_dump_json(indent=4)

    # Parse back using root discriminated union
    parsed_rule = AnyRule.validate_json(json_data)

    assert isinstance(parsed_rule, EmployeeRestTimeRule)
    assert parsed_rule.requirement.default.get_calculated_value(None) == 14.0
