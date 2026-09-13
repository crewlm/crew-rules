"""
Different models.
"""

from dataclasses import dataclass, field
from uuid import uuid4, UUID


@dataclass
class DecisionTable:
    pass


@dataclass
class Rule:
    id: UUID = field(default_factory=uuid4)
    name: str
    rule_type: str
    input: str
    applicability: DecisionTable
    value: DecisionTable
    value_updates: list[DecisionTable] = field(default_factory=list)
    requirement: DecisionTable | None = None
    requirement_updates: list[DecisionTable] = field(default_factory=list)
    limit: DecisionTable | None = None
    limit_updates: list[DecisionTable] = field(default_factory=list)
