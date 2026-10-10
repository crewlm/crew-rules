"""Documentary catalog and deterministic JSON export for EASA FTL examples.

The catalog preserves source-oriented schema declarations. It does not resolve
the declarations into runtime facts or calculate regulatory outcomes.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from models.projection import Projection
from models.rule import AnyRule

_MODULES = (
    "f01_cumulative_duty",
    "f02_cumulative_flight",
    "f03_basic_fdp",
    "f04_positioning",
    "f05_home_rest",
    "f06_away_rest",
    "f07_recovery_rest",
    "f08_split_duty",
    "f09_standby",
    "f10_augmentation",
)

_REQUIRED = {
    "number", "slug", "title", "rules", "projections", "concepts",
    "represented", "schema_gaps", "sources",
}
SCHEMA_GAPS = {
    "shared-definitions",
    "rule-relationships",
    "temporal-collection-definitions",
    "source-bindings",
    "qualitative-obligations",
}


@lru_cache(maxsize=1)
def _load_specs() -> tuple[dict[str, Any], ...]:
    """Import family examples only when the catalog is first used."""
    from importlib import import_module

    specs = []
    for module_name in _MODULES:
        module = import_module(f"examples.easa_ftl.{module_name}")
        spec = module.build()
        _validate_spec(spec)
        specs.append(spec)
    return tuple(specs)


def _validate_spec(spec: dict[str, Any]) -> None:
    """Check documentary metadata and model references, never runtime fields."""
    absent = _REQUIRED - spec.keys()
    if absent:
        raise ValueError(f"Spec is missing required metadata: {', '.join(sorted(absent))}")
    if not isinstance(spec["number"], int) or isinstance(spec["number"], bool):
        raise TypeError("Family number must be an integer")
    if not isinstance(spec["slug"], str) or not spec["slug"]:
        raise TypeError("Family slug must be a non-empty string")
    if not isinstance(spec["title"], str) or not spec["title"]:
        raise TypeError("Family title must be a non-empty string")
    if not isinstance(spec["rules"], list):
        raise TypeError(f"{spec['slug']} rules must be a list of Rule objects")
    for rule in spec["rules"]:
        if not hasattr(rule, "model_dump"):
            raise TypeError(f"{spec['slug']} contains a non-Rule value: {type(rule).__name__}")
        try:
            AnyRule.validate_python(rule.model_dump(mode="json"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise TypeError(f"{spec['slug']} contains an invalid Rule value") from exc
    if not isinstance(spec["projections"], list):
        raise TypeError(f"{spec['slug']} projections must be a list of Projection objects")
    for projection in spec["projections"]:
        if not isinstance(projection, Projection):
            raise TypeError(f"{spec['slug']} contains a non-Projection value: {type(projection).__name__}")
        Projection.model_validate(projection.model_dump(mode="json"))
    if not isinstance(spec["concepts"], Mapping):
        raise TypeError(f"{spec['slug']} concepts must map symbolic field paths to meanings")
    for path, definition in spec["concepts"].items():
        if not isinstance(path, str) or not path:
            raise TypeError(f"{spec['slug']} concept field paths must be non-empty strings")
        if not isinstance(definition, Mapping) or not isinstance(definition.get("meaning"), str):
            raise TypeError(f"{spec['slug']} concept {path!r} must include a meaning")
    for key in ("represented", "schema_gaps", "sources"):
        if not isinstance(spec[key], list) or not all(isinstance(item, str) for item in spec[key]):
            raise TypeError(f"{spec['slug']} {key} must be a list of strings")
    unknown_gaps = set(spec["schema_gaps"]) - SCHEMA_GAPS
    if unknown_gaps:
        raise ValueError(f"{spec['slug']} has unknown schema gap IDs: {', '.join(sorted(unknown_gaps))}")


class _LazySpecs(Sequence[dict[str, Any]]):
    """Load family modules when the catalog is accessed, not at package import."""

    def __len__(self) -> int:
        return len(_MODULES)

    def __getitem__(self, index):
        return _load_specs()[index]

    def __iter__(self):
        return iter(_load_specs())


EASA_FTL_SPECS: Sequence[dict[str, Any]] = _LazySpecs()


def get_spec(slug_or_number: str | int) -> dict[str, Any]:
    """Return the documented family matching a slug or number."""
    for spec in EASA_FTL_SPECS:
        if spec["slug"] == slug_or_number or spec["number"] == slug_or_number:
            return spec
    raise KeyError(f"Unknown EASA FTL family: {slug_or_number}")


def _jsonable_spec(spec: dict[str, Any]) -> dict[str, Any]:
    _validate_spec(spec)
    result = {key: value for key, value in spec.items() if key not in {"rules", "projections"}}
    result["rules"] = [rule.model_dump(mode="json") for rule in spec["rules"]]
    result["projections"] = [projection.model_dump(mode="json") for projection in spec["projections"]]
    return result


def export_spec(spec: dict[str, Any], path: str | Path | None = None) -> str:
    """Encode a family as stable JSON and optionally write it to ``path``."""
    encoded = json.dumps(_jsonable_spec(spec), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path is not None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(encoded, encoding="utf-8")
    return encoded


def export_catalog(output_dir: str | Path, *, manifest: bool = False) -> list[Path]:
    """Write ten deterministic family JSON files and optionally a manifest."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for spec in EASA_FTL_SPECS:
        path = destination / f"{spec['slug']}.json"
        export_spec(spec, path)
        written.append(path)
    if manifest:
        path = destination / "manifest.json"
        path.write_text(
            json.dumps(
                [{"number": spec["number"], "slug": spec["slug"], "title": spec["title"]}
                 for spec in EASA_FTL_SPECS],
                indent=2, sort_keys=True, ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def export_gap_issues(gap_issues_path: str | Path, output_dir: str | Path) -> list[Path]:
    """Export externally prepared, source-backed schema-gap issue drafts.

    Input is a JSON list of ``{slug, title, body}`` records. This function does
    not regenerate issues from family rule fragments or source quotations.
    """
    rows = json.loads(Path(gap_issues_path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Gap issue drafts must be a non-empty JSON list")
    if not all(isinstance(row, Mapping) and all(isinstance(row.get(key), str) and row[key]
                                                for key in ("slug", "title", "body")) for row in rows):
        raise ValueError("Each gap issue draft must contain non-empty slug, title, and body strings")
    slugs = [row["slug"] for row in rows]
    if any(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) is None for slug in slugs):
        raise ValueError("Gap issue draft slugs must use lowercase letters, digits, and hyphens")
    if len(set(slugs)) != len(slugs):
        raise ValueError("Gap issue draft slugs must be unique")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = []
    written = []
    for row in rows:
        body_path = destination / f"{row['slug']}.body.md"
        body_path.write_text(row["body"].rstrip() + "\n", encoding="utf-8")
        written.append(body_path)
        manifest.append({"slug": row["slug"], "title": row["title"], "file": body_path.name})
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    written.append(manifest_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the documentary EASA FTL schema catalog")
    parser.add_argument("--output", required=True, help="directory to receive ten family JSON specs")
    parser.add_argument("--manifest", action="store_true", help="also write manifest.json")
    parser.add_argument("--gap-issues", help="JSON list of source-backed schema-gap drafts")
    parser.add_argument("--issues-output", help="directory to receive schema-gap issue drafts")
    args = parser.parse_args()
    if bool(args.gap_issues) != bool(args.issues_output):
        parser.error("--gap-issues and --issues-output must be used together")
    for path in export_catalog(args.output, manifest=args.manifest):
        print(path)
    if args.gap_issues:
        for path in export_gap_issues(args.gap_issues, args.issues_output):
            print(path)


if __name__ == "__main__":
    main()
