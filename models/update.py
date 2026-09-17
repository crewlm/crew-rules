from typing import Literal

from utilities.pydantic import CustomBaseModel

from models.decision_table.decision_table import DecisionTable


class Update[C, V](CustomBaseModel):
    name: str
    method: Literal["set", "increase", "decrease", "max", "min", "scale"] = "set"
    table: DecisionTable[C, V]

    def get_method_action(self, item: str):
        match self.method:
            case "set":
                return f"Set {item} to "
            case "increase":
                return f"Increase {item} by "
            case "decrease":
                return f"Decrease {item} by "
            case "max":
                return f"Set {item} to the greater of the current {item} and "
            case "min":
                return f"Set {item} to the lesser of the current {item} and "
            case "scale":
                return f"Multipler {item} by "
        raise ValueError(f"Unsupported method {self.method}")

    def apply(self, current_val: float | None, update_val: float | None) -> float:
        if current_val is None:
            current_val = 0.0
        if update_val is None:
            return current_val
        match self.method:
            case "set":
                return update_val
            case "increase":
                return current_val + update_val
            case "decrease":
                return current_val - update_val
            case "max":
                return max(current_val, update_val)
            case "min":
                return min(current_val, update_val)
            case "scale":
                return current_val * update_val
            case _:
                raise ValueError(f"Unsupported method: {self.method}")
