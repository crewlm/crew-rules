"""
Mermaid Diagram Builder from Rule
"""

from models import Rule, DecisionTable


class MermaidDiagramBuilder:
    def __init__(self, rule: Rule):
        self.rule = rule
        self.node_counter: int = 0
        self.lines: list[str] = [
            "graph TD",
            f"    %% Diagram for Rule: {rule.name} (Scope: {getattr(rule, 'scope', 'Rule')})",
            "    classDef appNode fill:#e1f5fe,stroke:#0288d1,stroke-width:1px;",
            "    classDef valNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px;",
            "    classDef reqNode fill:#fff3e0,stroke:#f57c00,stroke-width:1px;",
            "    classDef limNode fill:#fff3e0,stroke:#f57c00,stroke-width:1px;",
            "    classDef valUpdNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;",
            "    classDef reqUpdNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;",
            "    classDef limUpdNode fill:#e8f5e9,stroke:#388e3c,stroke-width:1px;",
        ]

    def _next_node_id(self) -> str:
        self.node_counter += 1
        return f"N{self.node_counter}"

    def add_decision_table(self, table: DecisionTable, node_class: str) -> str:
        """Renders any DecisionTable into decision diamonds and action boxes."""
        if not table.items:
            default_id = self._next_node_id()
            self.lines.append(
                f'        {default_id}["Default: {str(table.default)}"]:::{node_class}'
            )
            return default_id

        prev_fail_id = None
        first_id = None

        for item in table.items:
            cond_id = self._next_node_id()
            val_id = self._next_node_id()
            if first_id is None:
                first_id = cond_id

            # Clean HTML line-breaks for Mermaid decision nodes
            cond_text = item.display_condition().replace("\n", "<br/>")
            val_text = item.display_value()

            self.lines.append(f'        {cond_id}{{"{cond_text}?"}}')
            self.lines.append(f'        {val_id}["{val_text}"]:::{node_class}')
            self.lines.append(f"        {cond_id} -->|Match| {val_id}")

            if prev_fail_id:
                self.lines.append(f"        {prev_fail_id} -->|No Match| {cond_id}")

            prev_fail_id = cond_id

        default_id = self._next_node_id()
        self.lines.append(
            f'        {default_id}["Default: {str(table.default)}"]:::{node_class}'
        )
        self.lines.append(f"        {prev_fail_id} -->|No Match| {default_id}")

        return first_id

    def add_applicability_section(self) -> "MermaidDiagramBuilder":
        self.lines.append('\n    subgraph Applicability ["Applicability"]')
        self.add_decision_table(self.rule.applicability, "appNode")
        self.lines.append("    end")
        return self

    def add_subject_value_section(self) -> "MermaidDiagramBuilder":
        self.lines.append('\n    subgraph SubjectValue ["Initial Value"]')
        self.add_decision_table(self.rule.value, "valNode")
        self.lines.append("    end")
        if self.rule.value_updates:
            self.lines.append('\n    subgraph ValueUpdates ["Value Updates"]')
            for upd in self.rule.value_updates:
                u_header_id = self._next_node_id()
                self.lines.append(
                    f'        {u_header_id}[["Value Update: {upd.name} ({upd.method.title()})"]]:::valUpdNode'
                )
                upd_entry = self.add_decision_table(upd.table, "valUpdNode")
                self.lines.append(f"        {u_header_id} --> {upd_entry}")
            self.lines.append("    end")
        return self

    def add_threshold_sections(self) -> "MermaidDiagramBuilder":
        if self.rule.requirement:
            self.lines.append('\n    subgraph Requirement ["Initial Requirement"]')
            self.add_decision_table(self.rule.requirement, "reqNode")
            self.lines.append("    end")

        if self.rule.requirement_updates:
            self.lines.append(
                '\n    subgraph RequirementUpdates ["Requirement Updates"]'
            )
            for upd in self.rule.requirement_updates:
                u_header_id = self._next_node_id()
                self.lines.append(
                    f'        {u_header_id}[["Requirement Update: {upd.name} ({upd.method.title()})"]]:::reqUpdNode'
                )
                upd_entry = self.add_decision_table(upd.table, "reqUpdNode")
                self.lines.append(f"        {u_header_id} --> {upd_entry}")
            self.lines.append("    end")

        if self.rule.limit:
            self.lines.append('\n    subgraph Limit ["Initial Limit"]')
            self.add_decision_table(self.rule.limit, "limNode")
            self.lines.append("    end")

        if self.rule.limit_updates:
            self.lines.append('\n    subgraph LimitUpdates ["Limit Updates"]')
            for upd in self.rule.limit_updates:
                u_header_id = self._next_node_id()
                self.lines.append(
                    f'        {u_header_id}[["Limit Update: {upd.name} ({upd.method.title()})"]]:::limUpdNode'
                )
                upd_entry = self.add_decision_table(upd.table, "limUpdNode")
                self.lines.append(f"        {u_header_id} --> {upd_entry}")
            self.lines.append("    end")
        return self

    def build(self) -> str:
        return "\n".join(self.lines)


def rule_to_mermaid(rule: Rule) -> str:
    """Convenience wrapper for rule diagram generation."""
    return (
        MermaidDiagramBuilder(rule)
        .add_applicability_section()
        .add_subject_value_section()
        .add_threshold_sections()
        .build()
    )
