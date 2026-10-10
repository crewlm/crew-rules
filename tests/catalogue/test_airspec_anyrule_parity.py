"""Regression cases shared with the browser AirSpec structural validator."""

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.rule import AnyRule


CATALOGUE = json.loads(
    (Path(__file__).parents[2] / "web/public/catalogue.json").read_text()
)
BASE_RULE = CATALOGUE["models"][0]["model"]


def test_python_anyrule_accepts_every_catalogue_model():
    for model in CATALOGUE["models"]:
        assert AnyRule.validate_python(model["model"])


def test_python_anyrule_defaults_allow_omitted_table_items_and_updates():
    rule = deepcopy(BASE_RULE)
    for field in ("applicability", "value", "requirement"):
        if rule.get(field) is not None:
            rule[field].pop("items", None)
    rule["value_updates"] = [{"name": "x", "table": {"default": {"kind": "none_value"}}}]
    for field in ("requirement_updates", "limit_updates"):
        rule.pop(field, None)
    assert AnyRule.validate_python(rule)


def invalid_rule(mutator):
    rule = deepcopy(BASE_RULE)
    mutator(rule)
    return rule


@pytest.mark.parametrize(
    "rule",
    [
        invalid_rule(lambda rule: rule["value"]["default"].pop("field")),
        invalid_rule(
            lambda rule: rule["value"].update(
                items=[
                    {
                        "condition": [
                            {
                                "field": "duration",
                                "comparison": {"kind": "unknown_comparison"},
                            }
                        ],
                        "value": rule["value"]["default"],
                    }
                ]
            )
        ),
        invalid_rule(
            lambda rule: rule["value"].update(
                items=[
                    {
                        "condition": [
                            {
                                "field": "duration",
                                "comparison": {
                                    "kind": "ge_number_comparison",
                                    "number": "not a number",
                                },
                            }
                        ],
                        "value": rule["value"]["default"],
                    }
                ]
            )
        ),
        invalid_rule(lambda rule: rule["value"].update(default=7)),
        invalid_rule(
            lambda rule: rule["value"].update(
                default={"kind": "number_value", "number": "not a number"}
            )
        ),
        invalid_rule(
            lambda rule: rule.update(
                value_updates=[{"name": "x", "table": {"items": []}}]
            )
        ),
    ],
    ids=[
        "missing-calculation-value-field",
        "unknown-comparison-kind",
        "invalid-comparison-field-type",
        "scalar-calculation-default",
        "invalid-calculation-field-type",
        "missing-update-table-default",
    ],
)
def test_python_anyrule_rejects_invalid_structural_fixtures(rule):
    with pytest.raises(ValidationError):
        AnyRule.validate_python(rule)


@pytest.mark.parametrize(
    "rule",
    [
        invalid_rule(
            lambda rule: (
                rule.update(limit=deepcopy(rule["requirement"]), requirement=None),
                rule.update(
                    requirement_updates=[
                        {"name": "x", "table": {"default": {"kind": "none_value"}}}
                    ]
                ),
            )
        ),
        invalid_rule(
            lambda rule: rule.update(
                limit_updates=[
                    {"name": "x", "table": {"default": {"kind": "none_value"}}}
                ]
            )
        ),
    ],
    ids=["requirement-update-needs-base", "limit-update-needs-base"],
)
def test_python_anyrule_requires_base_values_for_requirement_and_limit_updates(rule):
    with pytest.raises(ValidationError):
        AnyRule.validate_python(rule)
