from __future__ import annotations

import hashlib
import copy
import re
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from catalogue.export import build_catalogue, validate_catalogue
from catalogue.extractor import EASA, NS, PKG, SOURCE, W, W14
from models.rule import AnyRule


def _paragraphs(document):
    for topic in document["topics"]:
        for unit in topic["units"]:
            if unit["kind"] == "paragraph":
                yield unit
            elif unit["kind"] == "table":
                for row in unit["rows"]:
                    for cell in row:
                        yield from cell["paragraphs"]


def test_export_has_expected_source_coverage_and_stable_hashes():
    data = build_catalogue()
    document = data["documents"][0]
    paragraphs = list(_paragraphs(document))
    tables = [
        unit for topic in document["topics"] for unit in topic["units"]
        if unit["kind"] == "table"
    ]

    assert document["id"] == "easa-ftl-rev24-2026-03"
    assert len(document["topics"]) == 74
    assert len(paragraphs) == 1137
    assert len(tables) == 9
    assert all(p["id"].startswith(document["id"] + ":") for p in paragraphs)
    assert all(p["content_hash"] == hashlib.sha256(p["text"].encode()).hexdigest() for p in paragraphs)
    assert all("colspan" in c and "rowspan" in c for t in tables for row in t["rows"] for c in row)


def test_seed_models_are_valid_and_traces_resolve_to_real_units():
    data = build_catalogue()
    validate_catalogue(data)
    document = data["documents"][0]
    paragraphs = {p["id"]: p for p in _paragraphs(document)}
    models = {model["id"]: model for model in data["models"]}

    assert len(models) == 5
    assert all(model["status"] == "draft" for model in models.values())
    for model in models.values():
        assert AnyRule.validate_python(model["model"])
        assert model["limitations"]
    assert sum(link["relation"] == "context" for link in data["links"]) == 3
    assert all(link["model_id"] in models for link in data["links"])
    assert all(source_id in paragraphs for link in data["links"] for source_id in link["source_unit_ids"])
    assert paragraphs["easa-ftl-rev24-2026-03:ERULES-1963177438-12113:p:281BF929"]["citation"] == "ORO.FTL.235(a)(1)"


def test_duty_seed_windows_and_28_day_limitation_are_explicit():
    data = build_catalogue()
    limits = [m for m in data["models"] if m["model"]["scope"] == "employee_time_period"]
    assert [m["model"]["time_period"]["duration"] for m in limits] == [7, 14, 28]
    assert all(m["model"]["limit"]["default"]["kind"] == "duration_value" for m in limits)
    assert any("evenly" in item for item in limits[-1]["limitations"])


def test_rest_applicability_and_minimums_cover_short_and_long_preceding_duty():
    data = build_catalogue()
    models = {model["name"]: AnyRule.validate_python(model["model"]) for model in data["models"]}
    home = models["Minimum rest at home base"]
    away = models["Minimum rest away from home base"]

    assert home.applicability.get_matching_value(SimpleNamespace(at_home_base=True)).applicable
    assert not home.applicability.get_matching_value(SimpleNamespace(at_home_base=False)).applicable
    assert away.applicability.get_matching_value(SimpleNamespace(at_home_base=False)).applicable
    assert not away.applicability.get_matching_value(SimpleNamespace(at_home_base=True)).applicable
    assert home.requirement.default.get_calculated_value(SimpleNamespace(preceding_duty=SimpleNamespace(duration=11))) == 12
    assert home.requirement.default.get_calculated_value(SimpleNamespace(preceding_duty=SimpleNamespace(duration=13))) == 13
    assert away.requirement.default.get_calculated_value(SimpleNamespace(preceding_duty=SimpleNamespace(duration=8))) == 10
    assert away.requirement.default.get_calculated_value(SimpleNamespace(preceding_duty=SimpleNamespace(duration=14))) == 14


def test_source_paragraph_ids_and_text_match_flat_opc_xml():
    root = ET.fromstring(SOURCE.read_bytes())
    metadata = next(
        part.find("pkg:xmlData", NS)[0]
        for part in root.findall("pkg:part", NS)
        if part.find("pkg:xmlData", NS) is not None
        and part.find("pkg:xmlData", NS)[0].tag == f"{{{EASA}}}document"
    )
    word = next(
        part.find("pkg:xmlData", NS)[0]
        for part in root.findall("pkg:part", NS)
        if part.get(f"{{{PKG}}}name") == "/word/document.xml"
    )
    controls = {
        sdt.find("w:sdtPr/w:id", NS).get(f"{{{W}}}val"): sdt.find("w:sdtContent", NS)
        for sdt in word.findall(".//w:sdt", NS)
        if sdt.find("w:sdtPr/w:id", NS) is not None and sdt.find("w:sdtContent", NS) is not None
    }
    source_text = {}
    for topic in metadata.findall(".//e:topic", NS):
        title = re.sub(r"\s+", " ", topic.get("source-title", ""))
        if "ORO.FTL" not in title and "CS FTL.1" not in title:
            continue
        control = controls[topic.get("sdt-id")]
        for paragraph in control.findall(".//w:p", NS):
            para_id = paragraph.get(f"{{{W14}}}paraId")
            if para_id:
                source_text[para_id] = "".join(
                    node.text or "" if node.tag == f"{{{W}}}t" else
                    "\t" if node.tag == f"{{{W}}}tab" else
                    "\n" if node.tag == f"{{{W}}}br" else ""
                    for node in paragraph.iter()
                )
    extracted = {p["locator"]["para_id"]: p["text"] for p in _paragraphs(build_catalogue()["documents"][0]) if p["locator"]["para_id"]}
    assert extracted == source_text


def test_fallback_ids_are_unique_and_dangling_source_links_are_rejected():
    data = build_catalogue()
    paragraphs = list(_paragraphs(data["documents"][0]))
    fallback = [p for p in paragraphs if p["locator"]["para_id"] is None]
    assert fallback
    assert len({p["id"] for p in fallback}) == len(fallback)
    invalid = copy.deepcopy(data)
    invalid["links"][0]["source_unit_ids"] = ["unknown-source-unit"]
    try:
        validate_catalogue(invalid)
    except ValueError as error:
        assert "unknown source unit" in str(error)
    else:
        raise AssertionError("Dangling source links must fail validation")
