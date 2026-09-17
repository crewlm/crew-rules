from datetime import timedelta
from pathlib import Path

from models.entity import EmployeeRestTime, Duty

from models.rule import (
    EmployeeRestTimeRule,
    AnyRule,
)
from models.decision_table.value import (
    ApplicableValue,
    FieldValue,
    NoneValue,
    DurationValue,
    NullableCalculationValue,
)
from models.decision_table.condition import Condition
from models.decision_table.decision_table import ConditionValue, DecisionTable
from models.update import Update
from models.comparison import (
    EqualTextComparison,
    FalseComparison,
    GTNumberComparison,
)
from models.comparison import (
    EqualTextComparison,
    GTNumberComparison,
    FalseComparison,
)
from display.mermaidjs import rule_to_mermaid

FILES_DIR = Path(__file__).resolve().parent / ".files"


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
        id="1e6268b2-f487-42db-b769-125ca11a46dd",
        name="test",
        applicability=applicability_table,
        value=value_table,
        requirement=requirement_table,
        requirement_updates=[requirement_update_table1, requirement_update_table2],
    )

    # JSON round-trip validation
    json_data = rule.model_dump_json(indent=4)
    fpath_json = FILES_DIR / "min_rest_02.json"
    fpath_json.write_text(json_data)
    parsed_rule = AnyRule.validate_json(json_data)

    assert isinstance(parsed_rule, EmployeeRestTimeRule)
    assert parsed_rule.requirement.default.get_calculated_value(None) == 14.0

    # check mermaid diagram
    diagram = rule_to_mermaid(parsed_rule)
    fpath = FILES_DIR / "mermaidjs_min_rest_02.txt"
    # fpath.write_text(diagram)
    diagram_expected = fpath.read_text()
    assert diagram == diagram_expected
