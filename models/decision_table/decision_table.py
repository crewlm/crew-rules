from pydantic import Field

from utilities.pydantic import CustomBaseModel
from models.decision_table.condition import Condition
from models.decision_table.value import ProjectionValue


class ConditionValue[C, V](CustomBaseModel):
    condition: list[Condition[C]] = Field(
        description="All conditions must be met together (AND)."
    )
    value: V

    def matches(self, obj):
        return all(c.matches(obj) for c in self.condition)

    def display_condition(self):
        return ",\n<u>and</u> ".join(str(c) for c in self.condition)

    def display_value(self):
        return str(self.value)


class ProjectionConditionValue[C](CustomBaseModel):
    condition: list[Condition[C]] = Field(
        description="All conditions must be met together (AND)."
    )
    value: ProjectionValue

    def matches(self, obj):
        return all(c.matches(obj) for c in self.condition)

    def display_condition(self):
        return ",\n<u>and</u> ".join(str(c) for c in self.condition)

    def display_value(self):
        return str(self.value)


class ProjectionDecisionTable[C](CustomBaseModel):
    default: ProjectionValue
    items: list[ProjectionConditionValue[C]] = Field(default_factory=list)

    def get_matching_value(self, obj):
        for item in self.items:
            if item.matches(obj):
                return item.value
        return self.default


class DecisionTable[C, V](CustomBaseModel):
    default: V
    items: list[ConditionValue[C, V]] = Field(default_factory=list)

    def get_matching_value(self, obj):
        for item in self.items:
            if item.matches(obj):
                return item.value
        return self.default
