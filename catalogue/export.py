"""Export the checked EASA FTL catalogue to the frontend's static JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from catalogue.extractor import extract
from catalogue.seeds import build_seeds
from models.rule import AnyRule

OUTPUT = Path(__file__).resolve().parents[1] / "web/public/catalogue.json"


def build_catalogue() -> dict:
    data = extract()
    models, links = build_seeds()
    data["models"] = models
    data["links"] = links
    citation_overrides = {
        "ERULES-1963177438-12113:p:281BF929": "ORO.FTL.235(a)(1)",
        "ERULES-1963177438-12113:p:3EDACDB3": "ORO.FTL.235(b)",
        "ERULES-1963177438-12085:p:7B2FDB84": "ORO.FTL.210(a)(1)",
        "ERULES-1963177438-12085:p:76054E03": "ORO.FTL.210(a)(2)",
        "ERULES-1963177438-12085:p:448EBB0E": "ORO.FTL.210(a)(3)",
        "ERULES-1963177438-12113:p:543252B0": "ORO.FTL.235(a)(2)",
        "ERULES-1963177438-12113:p:34826D75": "ORO.FTL.235(c)",
    }
    for topic in data["documents"][0]["topics"]:
        for unit in topic["units"]:
            paragraphs = [unit] if unit["kind"] == "paragraph" else [
                paragraph for row in unit["rows"] for cell in row for paragraph in cell["paragraphs"]
            ]
            for paragraph in paragraphs:
                for source_id, citation in citation_overrides.items():
                    if paragraph["id"].endswith(source_id):
                        paragraph["citation"] = citation
    validate_catalogue(data)
    return data


def validate_catalogue(data: dict) -> None:
    """Fail closed on broken IDs, links, or rule model payloads."""
    if len(data.get("documents", [])) != 1:
        raise ValueError("Catalogue must contain exactly one source document")
    source_ids: list[str] = []
    for topic in data["documents"][0]["topics"]:
        for unit in topic["units"]:
            source_ids.append(unit["id"])
            if unit["kind"] == "table":
                for row in unit["rows"]:
                    for cell in row:
                        source_ids.extend(p["id"] for p in cell["paragraphs"])
    model_ids = [model["id"] for model in data["models"]]
    link_ids = [link["id"] for link in data["links"]]
    for label, ids in (("source unit", source_ids), ("model", model_ids), ("link", link_ids)):
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {label} ID")
    known_sources = set(source_ids)
    known_models = set(model_ids)
    for model in data["models"]:
        parsed = AnyRule.validate_python(model["model"])
        if str(parsed.id) != model["id"]:
            raise ValueError(f"Model ID does not match rule payload: {model['id']}")
    for link in data["links"]:
        if link["model_id"] not in known_models:
            raise ValueError(f"Link references unknown model: {link['id']}")
        if any(source_id not in known_sources for source_id in link["source_unit_ids"]):
            raise ValueError(f"Link references unknown source unit: {link['id']}")


def main() -> None:
    output = OUTPUT
    data = build_catalogue()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} ({len(data['documents'][0]['topics'])} topics)")


if __name__ == "__main__":
    main()
