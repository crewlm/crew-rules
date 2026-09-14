from typing import TypeVar, Any, Generic, get_args
from collections import defaultdict
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def _to_std_type(source_type: Any, std_base: type):
    """
    Replaces GettableList/GettableDict with standard list/dict while preserving generic args.
    - GettableList[T] -> list[T]
    - GettableDict[K, V] -> dict[K, V]
    """
    args = getattr(source_type, "__args__", ())
    if args:
        return std_base[args]
    return std_base


class GettableList(list[T], Generic[T]):
    """
    List subclass enabling dot-notation field access for attrgetter.
    Supports index access (.0, .1) and property access (.first, .last, .max, .min).
    """

    @property
    def first(self):
        return self[0]

    @property
    def last(self):
        return self[-1]

    @property
    def largest(self):
        return max(self)

    @property
    def smallest(self):
        return min(self)

    @property
    def arg_largest(self):
        return max(range(len(self)), key=lambda i: self[i])

    @property
    def arg_smallest(self):
        return min(range(len(self)), key=lambda i: self[i])

    @property
    def count_items(self):
        return len(self)

    def __getattr__(self, name: str):
        try:
            idx = int(name)
        except ValueError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        try:
            return self[idx]
        except IndexError:
            raise AttributeError(
                f"'{type(self).__name__}' list doesn't have an element at index '{idx}'"
            )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        std_type = _to_std_type(source_type, list)
        return core_schema.no_info_after_validator_function(
            cls,
            handler.generate_schema(std_type),
        )


class GettableDict(dict[K, V], Generic[K, V]):
    """
    Dict subclass enabling dot-notation field access for attrgetter.
    E.g., calculated_numbers.frms_score
    """

    # Computed once at class definition time
    _RESERVED_NAMES = frozenset(dir(dict))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._check_key_collisions()

    def _check_key_collisions(self):
        colliding = self._RESERVED_NAMES & self.keys()
        if colliding:
            raise ValueError(
                f"{type(self).__name__} keys collide with dict attributes/methods "
                f"and won't be reachable via dot access: {sorted(colliding)}"
            )

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no key '{name}'")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        std_type = _to_std_type(source_type, dict)
        return core_schema.no_info_after_validator_function(
            cls,
            handler.generate_schema(std_type),
        )


class GettableDefaultDict(defaultdict[K, V], Generic[K, V]):
    """
    defaultdict subclass enabling dot-notation field access for attrgetter.
    E.g., calculated_numbers.frms_score

    Since this is a defaultdict, dot access to a missing key will trigger
    default_factory and create the entry, just like `d[key]` would.
    """

    # Computed once at class definition time
    _RESERVED_NAMES = frozenset(dir(defaultdict))

    def __init__(self, default_factory=None, *args, **kwargs):
        super().__init__(default_factory, *args, **kwargs)
        self._check_key_collisions()

    def _check_key_collisions(self):
        colliding = self._RESERVED_NAMES & self.keys()
        if colliding:
            raise ValueError(
                f"{type(self).__name__} keys collide with dict/defaultdict attributes/methods "
                f"and won't be reachable via dot access: {sorted(colliding)}"
            )

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no key '{name}'")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        std_type = _to_std_type(source_type, dict)
        type_args = get_args(source_type)
        value_type = type_args[-1] if type_args else None

        def _build(value: dict) -> "GettableDefaultDict":
            return cls(value_type, value)

        return core_schema.no_info_after_validator_function(
            _build,
            handler.generate_schema(std_type),
        )


def test_classes():
    """Runs tests in same file. TODO: Move into pytest module."""
    from pydantic import BaseModel
    from operator import attrgetter

    class Model(BaseModel):
        items: GettableList[int]
        data: GettableDict[str, int]

    m = Model(items=[3, 1, 2], data={"a": 1, "b": 2})
    assert m.items.largest == 3
    assert m.items.first == 3
    assert m.data.a == 1
    assert isinstance(m.items, GettableList)
    assert isinstance(m.data, GettableDict)
    print("[PASS] basic validation + dot access")

    # collision check fires
    try:
        Model(items=[1], data={"items": 1})  # "items" collides with dict.items
        assert False, "should have raised"
    except ValueError:
        pass
    print("[PASS] collision check raises on reserved key")

    # nested case
    class Nested(BaseModel):
        groups: GettableList[GettableDict[str, int]]

    n = Nested(groups=[{"x": 1}, {"y": 2}])
    assert n.groups.first.x == 1
    assert isinstance(n.groups.first, GettableDict)
    print("[PASS] nested GettableList[GettableDict] dot access")

    # serialization round-trip
    dumped = m.model_dump()
    assert dumped == {"items": [3, 1, 2], "data": {"a": 1, "b": 2}}
    assert type(dumped["items"]) is list
    assert type(dumped["data"]) is dict
    print("[PASS] model_dump() returns plain list/dict")

    dumped_json = m.model_dump_json()
    m2 = Model.model_validate_json(dumped_json)
    assert m2.items.largest == 3
    assert m2.data.a == 1
    assert isinstance(m2.items, GettableList)
    assert isinstance(m2.data, GettableDict)
    print("[PASS] model_dump_json() + model_validate_json() round-trip")

    # index access via attrgetter
    assert attrgetter("1")(m.items) == 1
    print("[PASS] integer-string index access via attrgetter")

    # unknown attribute raises AttributeError, not KeyError/IndexError
    try:
        m.items.not_a_real_attr
        assert False, "should have raised"
    except AttributeError:
        pass
    try:
        m.data.not_a_real_key
        assert False, "should have raised"
    except AttributeError:
        pass
    print("[PASS] unknown attribute access raises AttributeError")

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    test_classes()
