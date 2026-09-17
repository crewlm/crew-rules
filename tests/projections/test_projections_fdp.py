from pathlib import Path
from datetime import datetime, timedelta

from models.projection import Projection
from models.update import ProjectionUpdate
from models.decision_table.condition import Condition
from models.decision_table.value import NoneValue, ProjectionValue
from models.decision_table.decision_table import (
    ProjectionDecisionTable,
    ProjectionConditionValue,
)
from models.entity import Activity, Duty
from models.comparison import EqualTextComparison, TruthComparison

from display.mermaidjs.projection import projection_to_mermaid

FILES_DIR = Path(__file__).resolve().parent / ".files"


def test_fdp_01():
    split_duty_reduction = ProjectionUpdate[Activity](
        name="Split duty reduction",
        method="decrease",
        table=ProjectionDecisionTable[Activity](
            default=NoneValue(),
            items=[
                ProjectionConditionValue[Activity](
                    condition=[
                        Condition[Activity](
                            field="type",
                            comparison=EqualTextComparison(text="mid_duty_rest"),
                        )
                    ],
                    value=ProjectionValue(rate=0.5),
                )
            ],
        ),
    )
    basic = ProjectionUpdate[Duty](
        name="Basic",
        method="increase",
        table=ProjectionDecisionTable[Duty](
            default=ProjectionValue(start_anchor="start", end_anchor="start"),
            items=[
                ProjectionConditionValue[Duty](
                    condition=[
                        Condition[Duty](
                            field="type", comparison=EqualTextComparison(text="flying")
                        )
                    ],
                    value=ProjectionValue(
                        start_anchor="start",
                        end_anchor="field",
                        end_field="operating_flights.last.blocks_on",
                    ),
                )
            ],
        ),
    )
    standby_callout = ProjectionUpdate[Duty](
        name="Standby callout",
        method="increase",
        table=ProjectionDecisionTable[Duty](
            default=NoneValue(),
            items=[
                ProjectionConditionValue[Duty](
                    condition=[
                        Condition[Duty](
                            field="called_out_standby",
                            comparison=TruthComparison(),
                        )
                    ],
                    value=ProjectionValue(
                        start_anchor="field",
                        start_field="called_out_standby.report",
                        end_anchor="start",
                        rate=0.5,
                        clamp_upper=timedelta(hours=2),
                    ),
                )
            ],
        ),
    )
    projection = Projection(
        id="1e6268b2-f487-42db-b769-125ca11a46dd",
        name="FDP Projection",
        code="FDP",
        activity_projections=[split_duty_reduction],
        duty_projections=[basic, standby_callout],
    )

    # JSON round-trip validation
    json_data = projection.model_dump_json(indent=4)
    fpath_json = FILES_DIR / "fdp_01.json"
    fpath_json.write_text(json_data)
    parsed_projection = Projection.model_validate_json(json_data)

    assert isinstance(parsed_projection, Projection)

    # check mermaid diagram
    diagram = projection_to_mermaid(parsed_projection)
    fpath = FILES_DIR / "mermaidjs_fdp_01.txt"
    fpath.write_text(diagram)
    diagram_expected = fpath.read_text()
    assert diagram == diagram_expected
