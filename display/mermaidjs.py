"""
Mermaid Diagram Builder from Rule
"""

from models import Rule, DecisionTable, Update


class MermaidDiagramBuilder:
    def __init__(self, rule: Rule):
        self.rule = rule
        self.node_counter: int = 0
        # Track (entry_node_id, exit_node_id) for every subgraph column
        self.subgraph_bounds: list[tuple[str, str]] = []
        self.lines: list[str] = [
            "graph LR",
            f"    %% Diagram for Rule: {rule.name} (Scope: {getattr(rule, 'scope', 'Rule')})",
            "    classDef inputNode fill:#e1f5fe,stroke:#0288d1,stroke-width:1px;",
            "    classDef appNode fill:#e1f5fe,stroke:#0288d1,stroke-width:1px;",
            "    classDef valNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px;",
            "    classDef reqNode fill:#fff3e0,stroke:#f57c00,stroke-width:1px;",
            "    classDef limNode fill:#fff3e0,stroke:#f57c00,stroke-width:1px;",
            "    classDef ValueUpdateNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;",
            "    classDef RequirementUpdateNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;",
            "    classDef LimitUpdateNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;",
        ]

    def _next_node_id(self) -> str:
        self.node_counter += 1
        return f"N{self.node_counter}"

    def add_decision_table(
        self, table: DecisionTable, node_class: str, action: str = ""
    ) -> tuple[str, str]:
        """Renders any DecisionTable into decision diamonds and action boxes. Returns (first_id, last_id)."""
        if not table.items:
            default_id = self._next_node_id()
            self.lines.append(
                f"""        {default_id}["{action if table.default else ''}{str(table.default)}"]:::{node_class}"""
            )
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
            val_text = item.display_value().replace('"', "'")

            self.lines.append(f'        {cond_id}{{"{cond_text}?"}}')
            self.lines.append(
                f"""        {val_id}["{action if item.value else ''}{val_text}"]:::{node_class}"""
            )
            self.lines.append(f"        {cond_id} -->|Yes| {val_id}")

            if prev_fail_id:
                self.lines.append(f"        {prev_fail_id} -->|No| {cond_id}")

            prev_fail_id = cond_id

        default_id = self._next_node_id()
        self.lines.append(
            f"""        {default_id}["{action if table.default else ''}{str(table.default)}"]:::{node_class}"""
        )
        self.lines.append(f"        {prev_fail_id} -->|No| {default_id}")

        return first_id, default_id

    def add_input_section(self) -> "MermaidDiagramBuilder":
        entity_type = self.rule.scope.replace("_", " ").title().replace(" ", "")
        self.lines.append('\n    subgraph Input ["Input"]')
        self.lines.append("        direction TB")
        node_id = self._next_node_id()
        self.lines.append(f'        {node_id}["{entity_type}"]:::inputNode')
        self.subgraph_bounds.append((node_id, node_id))
        self.lines.append("    end")
        return self

    def add_applicability_section(self) -> "MermaidDiagramBuilder":
        self.lines.append('\n    subgraph Applicability ["Applicability"]')
        self.lines.append("        direction TB")
        entry_id, exit_id = self.add_decision_table(self.rule.applicability, "appNode")
        self.subgraph_bounds.append((entry_id, exit_id))
        self.lines.append("    end")
        return self

    def add_value_section(self) -> "MermaidDiagramBuilder":
        self.lines.append('\n    subgraph SubjectValue ["Initial Value"]')
        self.lines.append("        direction TB")
        entry_id, exit_id = self.add_decision_table(self.rule.value, "valNode")
        self.subgraph_bounds.append((entry_id, exit_id))
        self.lines.append("    end")
        return self

    def add_requirement_section(self) -> "MermaidDiagramBuilder":
        if self.rule.requirement:
            self.lines.append('\n    subgraph Requirement ["Initial Requirement"]')
            self.lines.append("        direction TB")
            entry_id, exit_id = self.add_decision_table(
                self.rule.requirement, "reqNode"
            )
            self.subgraph_bounds.append((entry_id, exit_id))
            self.lines.append("    end")
        return self

    def add_limit_section(self) -> "MermaidDiagramBuilder":
        if self.rule.limit:
            self.lines.append('\n    subgraph Limit ["Initial Limit"]')
            self.lines.append("        direction TB")
            entry_id, exit_id = self.add_decision_table(self.rule.limit, "limNode")
            self.subgraph_bounds.append((entry_id, exit_id))
            self.lines.append("    end")
        return self

    def add_updates_section(
        self, updates: list[Update], name: str
    ) -> "MermaidDiagramBuilder":
        for idx, upd in enumerate(updates, start=1):
            self.lines.append(
                f'\n    subgraph {name}Update_{idx} ["{name} Update: {upd.name}"]'
            )
            self.lines.append("        direction TB")
            upd_entry, upd_exit = self.add_decision_table(
                upd.table,
                f"{name}UpdateNode",
                upd.get_method_action(item=name.lower()),
            )
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


def rule_to_mermaid(rule: Rule) -> str:
    """Convert rule to mermaidjs diagram."""
    diagram = MermaidDiagramBuilder(rule)
    return (
        diagram.add_input_section()
        .add_applicability_section()
        .add_value_section()
        .add_updates_section(diagram.rule.value_updates, "Value")
        .add_requirement_section()
        .add_updates_section(diagram.rule.requirement_updates, "Requirement")
        .add_limit_section()
        .add_updates_section(diagram.rule.limit_updates, "Limit")
        .build()
    )
