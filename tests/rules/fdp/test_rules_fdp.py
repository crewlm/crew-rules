from datetime import timedelta
from pathlib import Path
from entities import Duty
from models import (
    DutyRule,
    DecisionTable,
    ApplicableValue,
    ConditionValue,
    Condition,
    FieldValue,
    FieldDifferenceValue,
    TableLookupValue,
    LookupParameter,
    Update,
    CalculationValue,
    NoneValue,
    DurationValue,
    NullableCalculationValue,
    AnyRule,
)
from comparisons import (
    EqualTextComparison,
    EqualNumberComparison,
    TruthComparison,
    FalseComparison,
    GTNumberComparison,
)
from display.mermaidjs import rule_to_mermaid

FILES_DIR = Path(__file__).resolve().parent / ".files"


def test_max_fdp_01():
    C = Duty

    applicability_table = DecisionTable[C, ApplicableValue](
        default=ApplicableValue(phrase="Default", applicable=False),
        items=[
            ConditionValue[C, ApplicableValue](
                condition=[
                    Condition[C](
                        field="category",
                        comparison=EqualTextComparison(text="flying"),
                    ),
                    Condition[C](
                        field="operating_pilot_count",
                        comparison=EqualNumberComparison(number=2),
                    ),
                ],
                value=ApplicableValue(phrase="2-Pilot Flying Duty", applicable=True),
            )
        ],
    )

    value_table = DecisionTable[C, CalculationValue](
        default=FieldDifferenceValue(
            phrase="Actual Duty FDP Duration",
            start_field="calculated_datetime.fdp_start_timestamp",
            end_field="operating_flights.-1.on_blocks",
        )
    )

    limit_table = DecisionTable[C, CalculationValue](
        items=[
            ConditionValue[C, TableLookupValue](
                condition=[
                    Condition[C](
                        field="acclimatised_state",
                        comparison=EqualTextComparison(text="acclimatised"),
                    )
                ],
                value=TableLookupValue(
                    phrase="Unacclimatised Max FDP Limit (Table B)",
                    table_name="MaxFDPTableB",
                    lookup_map=[
                        LookupParameter(
                            name="sectors", field="calculated_numbers.fdp_sectors"
                        ),
                        LookupParameter(
                            name="preceding_rest", field="preceding_rest.duration"
                        ),
                    ],
                ),
            )
        ],
        default=TableLookupValue(
            phrase="Standard Max FDP Limit (Table A)",
            table_name="MaxFDPTableA",
            lookup_map=[
                LookupParameter(name="sectors", field="calculated_numbers.fdp_sectors"),
                LookupParameter(
                    name="start_time_of_day", field="duty.report_time_of_day_local"
                ),
            ],
        ),
    )

    limit_update_reduced_rest = Update[C, NullableCalculationValue](
        name="Short Rest Reduction",
        method="decrease",
        table=DecisionTable[C, NullableCalculationValue](
            default=NoneValue(),
            items=[
                ConditionValue[C, NullableCalculationValue](
                    condition=[
                        Condition[C](
                            field="calculated_number.preceding_rest_infringement",
                            comparison=GTNumberComparison(number=0.0),
                        )
                    ],
                    value=FieldValue(
                        phrase="Short preceding rest",
                        field="calculated_number.preceding_rest_infringement",
                    ),
                )
            ],
        ),
    )

    limit_update_discretion = Update[C, NullableCalculationValue](
        name="Commander's Discretion Extension",
        method="increase",
        table=DecisionTable[C, NullableCalculationValue](
            default=NoneValue(),
            items=[
                ConditionValue[C, NullableCalculationValue](
                    condition=[
                        Condition[C](
                            field="commander_discretion",
                            comparison=TruthComparison(),
                        )
                    ],
                    value=DurationValue(
                        phrase="Commander's discretion given",
                        duration=timedelta(hours=1),
                    ),
                ),
                ConditionValue[C, NullableCalculationValue](
                    condition=[
                        Condition[C](
                            field="class_1_override",
                            comparison=TruthComparison(),
                        )
                    ],
                    value=DurationValue(
                        phrase="Class 1 override given",
                        duration=timedelta(minutes=30),
                    ),
                ),
            ],
        ),
    )

    # Assemble rule
    rule = DutyRule(
        id="1e6268b2-f487-42db-b769-125ca11a46dd",
        name="Max FDP 2-Pilot Operations",
        applicability=applicability_table,
        value=value_table,
        limit=limit_table,
        limit_updates=[limit_update_reduced_rest, limit_update_discretion],
    )

    # JSON round-trip validation
    json_data = rule.model_dump_json(indent=4)
    fpath_json = FILES_DIR / "max_fdp_01.json"
    fpath_json.write_text(json_data)
    parsed_rule = AnyRule.validate_json(json_data)

    assert isinstance(parsed_rule, DutyRule)
    assert parsed_rule.scope == "duty"
    assert parsed_rule.limit.default.table_name == "MaxFDPTableA"

    # check mermaid diagram
    diagram = rule_to_mermaid(parsed_rule)
    fpath = FILES_DIR / "mermaidjs_max_fdp_01.txt"
    # fpath.write_text(diagram)
    diagram_expected = fpath.read_text()
    assert diagram == diagram_expected
