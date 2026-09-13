"""
Different models.
"""

from typing import Literal, Iterable, Any
from uuid import uuid4, UUID
from utilites.pydantic import CustomBaseModel, Field


class EqualNumberComparison(CustomBaseModel):
    kind: Literal["equal_number_comparison"] = "equal_number_comparison"
    number: float
    tolerance: float = Field(1e-6, description="Absolute tolerance to use")

    def matches(self, value: float):
        return (self.number - value) <= self.tolerance


class EqualSetComparison(CustomBaseModel):
    kind: Literal["equal_set_comparison"] = "equal_set_comparison"
    items: set[Any]

    def matches(self, value: Iterable[Any]):
        return self.items == set(value)


class WithinSetComparison(CustomBaseModel):
    kind: Literal["within_set_comparison"] = "within_set_comparison"
    items: set[Any]

    def matches(self, value: Iterable[Any]):
        return set(value).issubset(self.items)


class ContainSetComparison(CustomBaseModel):
    kind: Literal["within_set_comparison"] = "within_set_comparison"
    items: set[Any]

    def matches(self, value: Iterable[Any]):
        return set(value).issuperset(self.items)


Comparison = (
    EqualNumberComparison
    | EqualSetComparison
    | WithinSetComparison
    | ContainSetComparison
)


class Condition(CustomBaseModel):
    field: str = Field(
        description="Dot-separated field, accessing object's field using dot notation."
    )
    comparison: Comparison = Field(description="Comparison to make")
    reverse_match: bool = Field(False, description="TRUE inverts the match")


class Value(CustomBaseModel):
    pass


class ConditionValue(CustomBaseModel):
    condition: list[Condition] = Field(
        description="All conditions must be met together (AND)."
    )
    value: Value


class DecisionTable(CustomBaseModel):
    default: Value
    items: list[ConditionValue] = Field(default_factory=list)


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
