"""
Different models.
"""

from utilites.pydantic import CustomBaseModel, Field
from uuid import uuid4, UUID


class DecisionTable(CustomBaseModel):
    pass


class Rule(CustomBaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    rule_type: str
    input: str
    applicability: DecisionTable
    value: DecisionTable
    value_updates: list[DecisionTable] = Field(default_factory=list)
    requirement: DecisionTable | None = None
    requirement_updates: list[DecisionTable] = Field(default_factory=list)
    limit: DecisionTable | None = None
    limit_updates: list[DecisionTable] = Field(default_factory=list)
