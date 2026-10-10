"""Source and structure checks for the documentary EASA FTL catalog."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path

from examples.easa_ftl.catalog import (
    EASA_FTL_SPECS,
    export_catalog,
    export_gap_issues,
    export_spec,
    get_spec,
    main,
)
from models.comparison import EqualTextComparison, GTNumberComparison, LENumberComparison, RangeNumberComparison
from models.decision_table.value import DurationValue, FieldValue, ProjectedValue
from models.projection import Projection
from models.rule import AnyRule

ROOT = Path(__file__).parents[2]
GAP_IDS = {
    "shared-definitions",
    "rule-relationships",
    "temporal-collection-definitions",
    "source-bindings",
    "qualitative-obligations",
}


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk(child)


def _symbolic_fields(document):
    result = set()
    for node in _walk(document):
        # Condition, field-value, table-lookup, and projected interval paths
        # are schema declarations even if no Python attribute implements them.
        if isinstance(node.get("field"), str):
            result.add(node["field"])
        if node.get("kind") == "field_difference_value" or "start_anchor" in node:
            result.update(path for path in (node.get("start_field"), node.get("end_field")) if path)
    return result


def _projection_refs(document):
    return {
        node["code"]
        for node in _walk(document)
        if node.get("kind") == "projected_value" and isinstance(node.get("code"), str)
    }


def test_catalog_metadata_and_rules_projections_round_trip_as_models():
    assert len(EASA_FTL_SPECS) == 10
    assert [spec["number"] for spec in EASA_FTL_SPECS] == list(range(1, 11))
    assert len({spec["slug"] for spec in EASA_FTL_SPECS}) == 10
    for spec in EASA_FTL_SPECS:
        assert {
            "number", "slug", "title", "rules", "projections", "concepts",
            "represented", "schema_gaps", "sources",
        } <= spec.keys()
        assert spec["represented"]
        assert spec["sources"]
        assert set(spec["schema_gaps"]) <= GAP_IDS
        assert set(spec["schema_gaps"])  # Native missing-definition metadata is explicit.
        assert all("meaning" in concept for concept in spec["concepts"].values())
        for rule in spec["rules"]:
            parsed = AnyRule.validate_python(rule.model_dump(mode="json"))
            assert parsed.scope == rule.scope
        for projection in spec["projections"]:
            parsed = Projection.model_validate(projection.model_dump(mode="json"))
            assert parsed.code == projection.code


def test_json_exports_are_stable_and_have_exactly_ten_family_files(tmp_path):
    output = tmp_path / "catalog"
    baseline = {spec["slug"]: export_spec(spec) for spec in EASA_FTL_SPECS}
    written = export_catalog(output)
    assert len(written) == 10
    assert {path.name for path in written} == {f"{spec['slug']}.json" for spec in EASA_FTL_SPECS}
    assert len(list(output.glob("*.json"))) == 10
    for spec in EASA_FTL_SPECS:
        path = output / f"{spec['slug']}.json"
        assert path.read_text(encoding="utf-8") == baseline[spec["slug"]]
        assert json.loads(path.read_text(encoding="utf-8"))["slug"] == spec["slug"]
    assert get_spec(1)["slug"] == EASA_FTL_SPECS[0]["slug"]
    assert get_spec(EASA_FTL_SPECS[-1]["slug"])["number"] == 10


def test_source_bundle_covers_all_ten_families_and_catalog_citations():
    source_rows = json.loads((ROOT / "references/ftl/easa-issues/sources.json").read_text(encoding="utf-8"))
    by_number = {row["number"]: row for row in source_rows}
    assert set(by_number) == set(range(1, 11))
    code_pattern = re.compile(r"(?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3}|AMC\d* ORO\.FTL\.\d{3}|GM\d* ORO\.FTL\.\d{3})")
    for spec in EASA_FTL_SPECS:
        source = by_number[spec["number"]]
        assert source["title"]
        assert source["source_text"].strip()
        assert source["source_references"]
        catalog_source_text = " ".join(spec["sources"])
        source_codes = {code_pattern.search(reference).group() for reference in source["source_references"]
                        if code_pattern.search(reference)}
        assert source_codes, f"source bundle for {spec['slug']} has no recognizable citations"
        assert source_codes <= set(code_pattern.findall(catalog_source_text)), (
            f"{spec['slug']} does not document source citations {source_codes - set(code_pattern.findall(catalog_source_text))}"
        )


def test_symbolic_field_paths_and_projection_codes_have_local_documentary_references():
    for spec in EASA_FTL_SPECS:
        rule_json = [rule.model_dump(mode="json") for rule in spec["rules"]]
        projection_json = [projection.model_dump(mode="json") for projection in spec["projections"]]
        symbolic = _symbolic_fields([rule_json, projection_json])
        assert symbolic <= set(spec["concepts"]), f"{spec['slug']} has undocumented paths {symbolic - set(spec['concepts'])}"
        projection_codes = {projection.code for projection in spec["projections"]}
        refs = _projection_refs(rule_json)
        assert refs <= projection_codes, f"{spec['slug']} has unresolved projection codes {refs - projection_codes}"


def test_gap_issue_export_uses_prepared_source_backed_drafts_only(tmp_path):
    drafts = [
        {"slug": "shared-definitions", "title": "Define shared FTL concepts", "body": "Source-backed draft."},
        {"slug": "rule-relationships", "title": "Describe rule relationships", "body": "Another draft."},
    ]
    input_path = tmp_path / "gap-drafts.json"
    input_path.write_text(json.dumps(drafts), encoding="utf-8")
    output = tmp_path / "issues"
    written = export_gap_issues(input_path, output)
    assert {path.name for path in written} == {
        "shared-definitions.body.md", "rule-relationships.body.md", "manifest.json"
    }
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert [row["slug"] for row in manifest] == [row["slug"] for row in drafts]
    assert (output / "shared-definitions.body.md").read_text(encoding="utf-8") == "Source-backed draft.\n"


def test_cli_exports_catalog_and_gap_drafts_from_separate_inputs(tmp_path, monkeypatch, capsys):
    gap_drafts = tmp_path / "gap-drafts.json"
    gap_drafts.write_text(json.dumps([
        {"slug": "shared-definitions", "title": "Shared definitions", "body": "Source-backed."}
    ]), encoding="utf-8")
    catalog_dir = tmp_path / "json"
    issues_dir = tmp_path / "issues"
    monkeypatch.setattr("sys.argv", [
        "easa_ftl", "--output", str(catalog_dir), "--manifest",
        "--gap-issues", str(gap_drafts), "--issues-output", str(issues_dir),
    ])

    main()

    assert len(list(catalog_dir.glob("*.json"))) == 11  # Ten family files and manifest.
    assert (issues_dir / "shared-definitions.body.md").read_text(encoding="utf-8") == "Source-backed.\n"
    assert "shared-definitions.body.md" in capsys.readouterr().out


def test_900_hour_calendar_year_is_declared_as_typed_schema_objects():
    spec = get_spec("cumulative-operating-flight-time")
    annual = [
        rule for rule in spec["rules"]
        if getattr(getattr(rule, "time_period", None), "anchor", None) == "year"
        and getattr(getattr(rule, "time_period", None), "duration", None) == 1
    ]
    assert len(annual) == 1
    rule = annual[0]
    assert isinstance(rule.limit.default, DurationValue)
    assert rule.limit.default.duration == timedelta(hours=900)
    assert isinstance(rule.value.default, ProjectedValue)


def test_basic_fdp_table_2_transcription_matches_declared_rows_structurally():
    """Compare every source cell with row declarations; do not evaluate a rule."""
    spec = get_spec("basic-daily-fdp")
    rule = spec["rules"][0]
    # Fourteen chronological rows: the overnight source band is split at
    # midnight. Columns are 1–2 sectors, then 3 through 10 sectors.
    source_rows = [
        ((360, 809), [13, 12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9]),
        ((810, 839), [12.75, 12.25, 11.75, 11.25, 10.75, 10.25, 9.75, 9.25, 9]),
        ((840, 869), [12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 9]),
        ((870, 899), [12.25, 11.75, 11.25, 10.75, 10.25, 9.75, 9.25, 9, 9]),
        ((900, 929), [12, 11.5, 11, 10.5, 10, 9.5, 9, 9, 9]),
        ((930, 959), [11.75, 11.25, 10.75, 10.25, 9.75, 9.25, 9, 9, 9]),
        ((960, 989), [11.5, 11, 10.5, 10, 9.5, 9, 9, 9, 9]),
        ((990, 1019), [11.25, 10.75, 10.25, 9.75, 9.25, 9, 9, 9, 9]),
        ((1020, 1439), [11, 10.5, 10, 9.5, 9, 9, 9, 9, 9]),
        ((0, 299), [11, 10.5, 10, 9.5, 9, 9, 9, 9, 9]),
        ((300, 314), [12, 11.5, 11, 10.5, 10, 9.5, 9, 9, 9]),
        ((315, 329), [12.25, 11.75, 11.25, 10.75, 10.25, 9.75, 9.25, 9, 9]),
        ((330, 344), [12.5, 12, 11.5, 11, 10.5, 10, 9.5, 9, 9]),
        ((345, 359), [12.75, 12.25, 11.75, 11.25, 10.75, 10.25, 9.75, 9.25, 9]),
    ]
    actual = {}
    for item in rule.limit.items:
        conditions = {condition.field: condition.comparison for condition in item.condition}
        if not isinstance(item.value, DurationValue):
            continue
        if conditions.get("acclimatisation.state").text != "acclimatised":
            continue
        time_band = conditions["reference_time.minute_of_day"]
        sector_band = conditions["operating_sector_count"]
        actual[(int(time_band.lower), int(time_band.upper), int(sector_band.lower))] = (
            item.value.duration.total_seconds() / 3600
        )
    expected = {}
    for (lower, upper), cells in source_rows:
        for index, hours in enumerate(cells):
            if index == 0:
                expected[(lower, upper, 1)] = hours
                expected[(lower, upper, 2)] = hours
            else:
                expected[(lower, upper, index + 2)] = hours
    assert actual == expected


def test_split_duty_extension_rows_record_half_of_the_eligible_break():
    extension = next(
        rule for rule in get_spec("split_duty")["rules"]
        if "no more than the basic maximum plus half" in rule.name
    )
    assert len(extension.limit_updates) == 1
    update = extension.limit_updates[0]
    assert update.method == "increase"
    declared = [
        item.value for item in update.table.items
        if isinstance(item.value, FieldValue)
    ]
    assert any(value.field == "split_break.qualified_duration" and value.multiplier == 0.5 for value in declared)
    assert any(
        value.field == "split_break.other_accommodation_extension_eligible.duration"
        and value.multiplier == 0.5
        for value in declared
    )


def test_standby_thresholds_caps_and_procedure_meaning_are_structural():
    spec = get_spec("standby")
    rules = spec["rules"]
    airport_reduction = next(rule for rule in rules if "beyond four hours" in rule.name)
    airport = airport_reduction.limit_updates[0].table.default
    assert isinstance(airport, FieldValue)
    assert (airport.offset, airport.clamp_lower) == (-4, 0)

    other_reduction = next(rule for rule in rules if "six-hour or extended eight-hour" in rule.name)
    reductions = {}
    for update in other_reduction.limit_updates:
        item = update.table.items[0]
        scope = next(condition.comparison.text for condition in item.condition
                     if isinstance(condition.comparison, EqualTextComparison))
        reductions[scope] = item.value
    assert set(reductions) == {"ordinary", "split_or_inflight_extension"}
    assert (reductions["ordinary"].offset, reductions["ordinary"].clamp_lower) == (-6, 0)
    assert (reductions["split_or_inflight_extension"].offset,
            reductions["split_or_inflight_extension"].clamp_lower) == (-8, 0)

    airport_cap = next(rule for rule in rules if "Airport standby plus assigned FDP" in rule.name)
    assert isinstance(airport_cap.limit.default, DurationValue)
    assert airport_cap.limit.default.duration == timedelta(hours=16)
    assert any(
        condition.field == "standby.assigned_fdp_rule_scope"
        and isinstance(condition.comparison, EqualTextComparison)
        and condition.comparison.text == "oro_ftl_205_b_or_d"
        for item in airport_cap.applicability.items for condition in item.condition
    )
    other_cap = next(rule for rule in rules if rule.name == "Other standby is at most 16 hours")
    assert isinstance(other_cap.limit.default, DurationValue)
    assert other_cap.limit.default.duration == timedelta(hours=16)
    assert "standby_and_fdp.awake_duration" in spec["concepts"]
    rule_documents = [rule.model_dump(mode="json") for rule in rules]
    assert "standby_and_fdp.awake_duration" not in json.dumps(rule_documents)


def test_augmentation_caps_strict_extension_guard_and_all_cabin_table_cells():
    spec = get_spec("augmentation")
    cap_rules = [rule for rule in spec["rules"] if rule.name.startswith("Flight-crew maximum total FDP:")]
    assert len(cap_rules) == 6
    caps = {}
    for rule in cap_rules:
        conditions = rule.applicability.items[0].condition
        additional = next(condition.comparison.number for condition in conditions
                          if condition.field == "augmentation.additional_qualified_flight_crew_count")
        facility = next(condition.comparison.text for condition in conditions
                        if condition.field == "augmentation.flight_crew.rest_facility_class")
        assert isinstance(rule.limit.default, DurationValue)
        caps[(additional, facility)] = rule.limit.default.duration.total_seconds() / 3600
        assert len(rule.limit_updates) == 1
        bonus = rule.limit_updates[0]
        assert bonus.method == "increase"
        row = bonus.table.items[0]
        conditions = {condition.field: condition.comparison for condition in row.condition}
        assert isinstance(conditions["augmentation.sector_over_9h.continuous_flight.duration"], GTNumberComparison)
        assert conditions["augmentation.sector_over_9h.continuous_flight.duration"].number == 9
        assert isinstance(conditions["augmentation.sector_count"], LENumberComparison)
        assert conditions["augmentation.sector_count"].number == 2
        assert isinstance(row.value, DurationValue)
        assert row.value.duration == timedelta(hours=1)
    assert caps == {
        (1, "class_3"): 14, (1, "class_2"): 15, (1, "class_1"): 16,
        (2, "class_3"): 15, (2, "class_2"): 16, (2, "class_1"): 17,
    }

    cabin_rules = [
        rule for rule in spec["rules"]
        if rule.name.startswith("Cabin crew minimum total in-flight rest:")
        or rule.name.startswith("Cabin facility ")
    ]
    assert len(cabin_rules) == 24
    actual = {}
    for rule in cabin_rules:
        conditions = rule.applicability.items[0].condition
        band = next(condition.comparison for condition in conditions
                    if condition.field == "augmentation.extended_fdp.duration")
        facility = next(condition.comparison.text for condition in conditions
                        if condition.field == "augmentation.cabin_crew.rest_facility_class")
        assert isinstance(band, RangeNumberComparison)
        key = (band.lower, band.upper, facility)
        if rule.name.startswith("Cabin facility "):
            assert isinstance(rule.limit.default, DurationValue)
            assert rule.limit.default.duration == timedelta(0)
            actual[key] = None
        else:
            assert isinstance(rule.requirement.default, DurationValue)
            actual[key] = rule.requirement.default.duration.total_seconds() / 3600

    bands = [
        ((0, 14.5), (1.5, 1.5, 1.5)),
        ((14 + 31 / 60, 15), (1.75, 2, 2 + 20 / 60)),
        ((15 + 1 / 60, 15.5), (2, 2 + 20 / 60, 2 + 40 / 60)),
        ((15 + 31 / 60, 16), (2.25, 2 + 40 / 60, 3)),
        ((16 + 1 / 60, 16.5), (2 + 35 / 60, 3, None)),
        ((16 + 31 / 60, 17), (3, 3 + 25 / 60, None)),
        ((17 + 1 / 60, 17.5), (3 + 25 / 60, None, None)),
        ((17 + 31 / 60, 18), (3 + 50 / 60, None, None)),
    ]
    expected = {
        (lower, upper, facility): value
        for (lower, upper), values in bands
        for facility, value in zip(("class_1", "class_2", "class_3"), values)
    }
    assert actual == expected
