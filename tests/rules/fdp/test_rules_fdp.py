from datetime import timedelta
from pathlib import Path
from entities import Duty
from models import (
    DutyRule,
    DecisionTable,
    ApplicableValue,
    ConditionValue,
    Condition,
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
                        field="is_acclimatised",
                        comparison=FalseComparison(),
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

    limit_update_discretion = Update[C, NullableCalculationValue](
        name="Commander's Discretion Extension",
        method="increase",
        table=DecisionTable[C, NullableCalculationValue](
            default=NoneValue(),
            items=[
                ConditionValue[C, DurationValue](
                    condition=[
                        Condition[C](
                            field="discretion.commander",
                            comparison=TruthComparison(),
                        )
                    ],
                    value=DurationValue(
                        phrase="1-hour discretion extension",
                        duration=timedelta(hours=1),
                    ),
                )
            ],
        ),
    )

    # Assemble rule
    rule = DutyRule(
        name="Max FDP 2-Pilot Operations",
        applicability=applicability_table,
        value=value_table,
        limit=limit_table,
        limit_updates=[limit_update_discretion],
    )

    # JSON round-trip validation
    json_data = rule.model_dump_json(indent=4)
    parsed_rule = AnyRule.validate_json(json_data)

    assert isinstance(parsed_rule, DutyRule)
    assert parsed_rule.scope == "duty"
    assert parsed_rule.limit.default.table_name == "MaxFDPTableA"

    # check mermaid diagram
    diagram = rule_to_mermaid(parsed_rule)
    fpath = FILES_DIR / "mermaidjs_max_fdp_01.txt"
    diagram_expected = fpath.read_text()
    assert diagram == diagram_expected
