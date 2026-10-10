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
PARITY_CASES = json.loads(Path(__file__).with_name("airspec_parity_cases.json").read_text())
BASE_RULE = CATALOGUE["models"][0]["model"]


def test_python_anyrule_accepts_every_catalogue_model():
    for model in CATALOGUE["models"]:
        assert AnyRule.validate_python(model["model"])


@pytest.mark.parametrize("duration", [12, 12.0, "12", "1.0", "1_0", " 1 "])
def test_python_anyrule_accepts_integer_time_period_coercions(duration):
    rule = deepcopy(BASE_RULE)
    rule["scope"] = "employee_time_period"
    rule["time_period"] = {"anchor": "day", "unit": "hour", "duration": duration}
    assert AnyRule.validate_python(rule)


@pytest.mark.parametrize("duration", [1.5, "0x10", "1e3", None])
def test_python_anyrule_rejects_invalid_integer_time_period_values(duration):
    rule = deepcopy(BASE_RULE)
    rule["scope"] = "employee_time_period"
    rule["time_period"] = {"anchor": "day", "unit": "hour", "duration": duration}
    with pytest.raises(ValidationError):
        AnyRule.validate_python(rule)


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


def parity_rule(case):
    rule = deepcopy(BASE_RULE)
    if case["kind"] == "number":
        rule["value"]["default"] = {"kind": "number_value", "number": case["value"]}
    elif case["kind"] == "duration":
        rule["value"]["default"] = {
            "kind": "duration_value",
            "duration": case["value"],
        }
    else:
        comparison = (
            {"kind": "time_window_overlap_comparison", "start": "09:00", "end": "10:00"}
            if case["kind"] == "time"
            else {"kind": "range_datetime_comparison", "lower": "2026-01-01T00:00:00Z", "upper": "2026-01-02T00:00:00Z"}
            if case["kind"] == "datetime"
            else {"kind": case["comparisonKind"], "items": []}
        )
        field = case.get("field", "lower" if case["kind"] == "datetime" else "items")
        comparison[field] = case["value"]
        rule["value"]["items"] = [
            {
                "condition": [{"field": "duration", "comparison": comparison}],
                "value": rule["value"]["default"],
            }
        ]
    return rule


@pytest.mark.parametrize("case", PARITY_CASES, ids=lambda case: case["name"])
def test_python_anyrule_acceptance_matches_each_fixture_expectation(case):
    try:
        AnyRule.validate_python(parity_rule(case))
        python_accepts = True
    except ValidationError:
        python_accepts = False
    assert python_accepts is case.get("pythonValid", case["valid"])


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
