"""
Mermaid Diagram Builder from Projection
"""

from models.projection import Projection
from models.update import ProjectionUpdate
from models.decision_table.decision_table import ProjectionDecisionTable


class ProjectionMermaidDiagramBuilder:
    def __init__(self, projection: Projection):
        self.projection = projection
        self.node_counter: int = 0
        # Track (entry_node_id, exit_node_id) for every subgraph column
        self.subgraph_bounds: list[tuple[str, str]] = []
        self.lines: list[str] = [
            "graph LR",
            f"    %% Diagram for Projection: {projection.name} ({projection.code})",
            "    classDef inputNode fill:#e1f5fe,stroke:#0288d1,stroke-width:1px;",
            "    classDef projNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;",
        ]

    def _next_node_id(self) -> str:
        self.node_counter += 1
        return f"N{self.node_counter}"

    def add_decision_table(self, table: ProjectionDecisionTable) -> tuple[str, str]:
        """Renders ProjectionDecisionTable into decision diamonds and action boxes."""
        if not table.items:
            default_id = self._next_node_id()
            default_text = str(table.default).replace("\n", "<br/>").replace('"', "'")
            self.lines.append(f"""        {default_id}["{default_text}"]:::projNode""")
            return default_id, default_id

        prev_fail_id = None
        first_id = None

        for item in table.items:
            cond_id = self._next_node_id()
            val_id = self._next_node_id()
            if first_id is None:
                first_id = cond_id

            cond_text = (
                item.display_condition().replace("\n", "<br/>").replace('"', "'")
            )
            val_text = item.display_value().replace("\n", "<br/>").replace('"', "'")

            self.lines.append(f'        {cond_id}{{"{cond_text}?"}}')
            self.lines.append(f"""        {val_id}["{val_text}"]:::projNode""")
            self.lines.append(f"        {cond_id} -->|Yes| {val_id}")

            if prev_fail_id:
                self.lines.append(f"        {prev_fail_id} -->|No| {cond_id}")

            prev_fail_id = cond_id

        default_id = self._next_node_id()
        default_text = str(table.default).replace("\n", "<br/>").replace('"', "'")
        self.lines.append(f"""        {default_id}["{default_text}"]:::projNode""")
        self.lines.append(f"        {prev_fail_id} -->|No| {default_id}")

        return first_id, default_id

    def add_projection_updates(
        self, updates: list[ProjectionUpdate], entity_type: str
    ) -> "ProjectionMermaidDiagramBuilder":
        for idx, upd in enumerate(updates, start=1):
            self.lines.append(
                f'\n    subgraph {entity_type}Proj_{idx} ["{entity_type} Projection: {upd.name}"]'
            )
            self.lines.append("        direction TB")
            upd_entry, upd_exit = self.add_decision_table(upd.table)
            self.subgraph_bounds.append((upd_entry, upd_exit))
            self.lines.append("    end")
        return self

    def build(self) -> str:
        # Link Exit(Subgraph_N) ~~~ Entry(Subgraph_N+1) to force strict horizontal row layout
        if len(self.subgraph_bounds) > 1:
            self.lines.append(
                "\n    %% Force left-to-right column flow across subgraphs"
            )
            for i in range(len(self.subgraph_bounds) - 1):
                prev_exit = self.subgraph_bounds[i][1]
                next_entry = self.subgraph_bounds[i + 1][0]
                self.lines.append(f"    {prev_exit} ~~~ {next_entry}")

        return "\n".join(self.lines)


def projection_to_mermaid(projection: Projection) -> str:
    """Convert projection to mermaidjs diagram."""
    diagram = ProjectionMermaidDiagramBuilder(projection)

    target_groups = [
        (diagram.projection.activity_projections, "Activity"),
        (diagram.projection.employee_ground_time_projections, "Employee Ground Time"),
        (diagram.projection.duty_projections, "Duty"),
        (diagram.projection.employee_rest_time_projections, "Employee Rest Time"),
        (diagram.projection.pairing_projections, "Pairing"),
    ]

    for updates, entity_label in target_groups:
        if updates:
            diagram.add_projection_updates(updates, entity_label)

    return diagram.build()
