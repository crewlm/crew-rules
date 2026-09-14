from datetime import timedelta

from entities import EmployeeRestTime
from models import (
    EmployeeRestTimeRule,
    DecisionTable,
    ApplicableValue,
    DurationValue,
    FieldValue,
    AnyRule,
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
    assert parsed_rule.requirement.default.duration == timedelta(hours=12)
