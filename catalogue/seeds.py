"""Five source-linked draft examples used to exercise the catalogue contract."""

from __future__ import annotations

from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from display.mermaidjs.rule import rule_to_mermaid
from models.comparison import FalseComparison, TruthComparison
from models.decision_table.condition import Condition
from models.decision_table.decision_table import ConditionValue, DecisionTable
from models.decision_table.value import ApplicableValue, DurationValue, FieldValue
from models.rule import AnyRule, EmployeeRestTimeRule, EmployeeTimePeriodRule
from models.time_period import TimePeriod

BASE_LIMITATIONS = [
    "Draft interpretation for review; not approved operational policy.",
    "The rule model is a declarative draft; the repository does not yet evaluate it as an operational compliance decision.",
    "A valid result depends on complete, correctly scoped input data and applicable operator approvals.",
]
DOC = "easa-ftl-rev24-2026-03:"


def _table(value):
    return DecisionTable(default=value, items=[])


def _draft(name, seed_id, scope, value, *, requirement=None, limit=None, time_period=None, applicability=None):
    common = dict(
        id=uuid5(NAMESPACE_URL, f"easa-ftl-catalogue:{seed_id}"), name=name,
        applicability=applicability or _table(ApplicableValue(applicable=True)),
        value=_table(value), requirement=requirement, limit=limit,
    )
    rule = EmployeeRestTimeRule(**common) if scope == "employee_rest_time" else EmployeeTimePeriodRule(**common, time_period=time_period)
    return AnyRule.validate_python(rule.model_dump(mode="python"))


def build_seeds() -> tuple[list[dict], list[dict]]:
    definitions = [
        ("home-base-minimum-rest", "Minimum rest at home base", "employee_rest_time", 12, f"{DOC}ERULES-1963177438-12113:p:281BF929", "ORO.FTL.235(a)(1)"),
        ("away-from-base-minimum-rest", "Minimum rest away from home base", "employee_rest_time", 10, f"{DOC}ERULES-1963177438-12113:p:3EDACDB3", "ORO.FTL.235(b)"),
        ("duty-limit-7-days", "Cumulative duty limit over 7 days", "employee_time_period", 60, f"{DOC}ERULES-1963177438-12085:p:7B2FDB84", "ORO.FTL.210(a)(1)"),
        ("duty-limit-14-days", "Cumulative duty limit over 14 days", "employee_time_period", 110, f"{DOC}ERULES-1963177438-12085:p:76054E03", "ORO.FTL.210(a)(2)"),
        ("duty-limit-28-days", "Cumulative duty limit over 28 days", "employee_time_period", 190, f"{DOC}ERULES-1963177438-12085:p:448EBB0E", "ORO.FTL.210(a)(3)"),
    ]
    models, links = [], []
    home_id = away_id = None
    shared_context = [f"{DOC}ERULES-1963177438-12113:p:34826D75"]
    for slug, name, scope, threshold, source_id, clause in definitions:
        if scope == "employee_rest_time":
            at_home = slug == "home-base-minimum-rest"
            app_table = DecisionTable(
                default=ApplicableValue(applicable=False),
                items=[ConditionValue(
                    condition=[Condition(field="at_home_base", comparison=TruthComparison() if at_home else FalseComparison())],
                    value=ApplicableValue(applicable=True),
                )],
            )
            rule = _draft(
                name, slug, scope, FieldValue(field="duration", phrase="Actual rest duration"),
                requirement=_table(FieldValue(
                    field="preceding_duty.duration", clamp_lower=threshold,
                    phrase=f"Greater of preceding duty and {threshold} hours",
                )),
                applicability=app_table,
            )
            interpretation = f"{clause} is represented as a minimum rest duration equal to the greater of the preceding duty and {threshold} hours."
            limitations = BASE_LIMITATIONS + [
                "Adapters must supply actual rest duration, preceding-duty duration, and the home-base classification; these are not computed by the current entity model.",
                "This draft does not model rest reductions, derogations, or their operating conditions.",
            ]
            if not at_home:
                limitations.append("The away-from-base sleep-opportunity and travel-time requirements are not represented by this draft.")
        else:
            days = int(slug.split("-")[-2])
            rule = _draft(
                name, slug, scope, FieldValue(field="duty_hours"),
                limit=_table(DurationValue(duration=timedelta(hours=threshold))),
                time_period=TimePeriod(anchor="day", unit="day", duration=days),
            )
            interpretation = f"{clause} is represented as a maximum of {threshold} duty hours in any {days}-day period."
            limitations = BASE_LIMITATIONS + [
                "An adapter must supply the duty_hours aggregate; the current entity model does not sum duty periods.",
                "Rolling consecutive-day windows and their boundary handling must be supplied by the adapter.",
                "Exceptions and special cases are not represented by this draft.",
            ]
            if days == 28:
                limitations.append("The requirement to spread duty evenly is not represented by this draft.")
        model_id = str(rule.id)
        models.append({
            "id": model_id, "name": name, "status": "draft",
            "interpretation": interpretation, "limitations": limitations,
            "model": rule.model_dump(mode="json"), "mermaid": rule_to_mermaid(rule),
        })
        links.append({
            "id": f"link:{slug}:primary", "source_unit_ids": [source_id],
            "model_id": model_id, "model_path": "", "relation": "models",
            "note": f"Primary source provision for draft {clause} interpretation.",
        })
        if slug == "home-base-minimum-rest": home_id = model_id
        if slug == "away-from-base-minimum-rest": away_id = model_id

    for slug, model_id in (("home-base-minimum-rest", home_id), ("away-from-base-minimum-rest", away_id)):
        links.append({
            "id": f"link:{slug}:reduced-rest-context", "source_unit_ids": shared_context,
            "model_id": model_id, "model_path": "", "relation": "context",
            "note": "Reduced-rest material is shared interpretive context and requires separate applicability and approval review.",
        })
    links.append({
        "id": "link:home-base-minimum-rest:suitable-accommodation-context",
        "source_unit_ids": [f"{DOC}ERULES-1963177438-12113:p:543252B0"],
        "model_id": home_id, "model_path": "", "relation": "context",
        "note": "ORO.FTL.235(a)(2) provides a suitable-accommodation derogation under which the ordinary home-base minimum may be replaced by paragraph (b); operator-specific applicability and approval must be verified.",
    })
    return models, links
