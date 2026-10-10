"""Deterministic extraction of EASA's Flat OPC XML export."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

EASA = "http://www.easa.europa.eu/erules-export"
PKG = "http://schemas.microsoft.com/office/2006/xmlPackage"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
NS = {"e": EASA, "pkg": PKG, "w": W, "w14": W14}
SOURCE = Path(__file__).resolve().parents[1] / "references/ftl/easa-air-operations-rev24-2026-03.xml"
DOCUMENT_ID = "easa-ftl-rev24-2026-03"
PUBLISHER_URL = "https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations"
VERSION = "Revision 24, March 2026"


def _part(root: ET.Element, name: str) -> ET.Element:
    for part in root.findall("pkg:part", NS):
        if part.get(f"{{{PKG}}}name") == name:
            data = part.find("pkg:xmlData", NS)
            if data is not None and len(data):
                return data[0]
    raise ValueError(f"Flat OPC part not found: {name}")


def _text(paragraph: ET.Element) -> str:
    pieces: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{{{W}}}t":
            pieces.append(node.text or "")
        elif node.tag == f"{{{W}}}tab":
            pieces.append("\t")
        elif node.tag == f"{{{W}}}br":
            pieces.append("\n")
    return "".join(pieces)


def _paragraphs(container: ET.Element, topic_id: str, path: str, citation: str) -> list[dict[str, Any]]:
    result = []
    paragraphs = [container] if container.tag == f"{{{W}}}p" else container.findall(".//w:p", NS)
    for index, p in enumerate(paragraphs, 1):
        text = _text(p)
        para_id = p.get(f"{{{W14}}}paraId")
        structural_path = path if path.endswith("]") and "/p[" in path else f"{path}/p[{index}]"
        locator = {"para_id": para_id, "structural_path": structural_path}
        result.append({
            "id": f"{DOCUMENT_ID}:{topic_id}:p:{para_id}" if para_id else f"{DOCUMENT_ID}:{topic_id}:p:{structural_path}",
            "kind": "paragraph", "text": text, "citation": _citation(text) or citation, "locator": locator,
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return result


def _citation(text: str) -> str | None:
    match = re.match(r"\s*((?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})(?:\([^)]+\))*)\b", text)
    return match.group(0) if match else None


def _table(table: ET.Element, topic_id: str, ordinal: int, citation: str) -> dict[str, Any]:
    rows = []
    for ri, row in enumerate(table.findall("w:tr", NS), 1):
        cells = []
        for ci, cell in enumerate(row.findall("w:tc", NS), 1):
            tcpr = cell.find("w:tcPr", NS)
            grid_span = tcpr.find("w:gridSpan", NS) if tcpr is not None else None
            vmerge = tcpr.find("w:vMerge", NS) if tcpr is not None else None
            paragraphs = _paragraphs(cell, topic_id, f"{topic_id}/table[{ordinal}]/row[{ri}]/cell[{ci}]", citation)
            cells.append({
                "colspan": int(grid_span.get(f"{{{W}}}val", "1")) if grid_span is not None else 1,
                "rowspan": 1,
                "paragraphs": paragraphs,
                "vertical_merge": (vmerge.get(f"{{{W}}}val", "continue") if vmerge is not None else None),
            })
        rows.append(cells)
    # Word encodes vertical merges as restart/continue. Reflect the effective span on the origin cell.
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            merge = cell.get("vertical_merge")
            if merge != "restart":
                continue
            span = 1
            for later in rows[ri + 1:]:
                if ci < len(later) and later[ci].get("vertical_merge") == "continue":
                    span += 1
                else:
                    break
            cell["rowspan"] = span
    serialized = "\n".join(
        paragraph["text"] for row in rows for cell in row for paragraph in cell["paragraphs"]
    )
    return {
        "id": f"{DOCUMENT_ID}:{topic_id}:table:{ordinal}", "kind": "table", "rows": rows,
        "content_hash": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }


def _walk_units(container: ET.Element, topic_id: str, citation: str) -> list[dict[str, Any]]:
    """Walk wrappers recursively while treating each table as a single ordered unit."""
    units: list[dict[str, Any]] = []
    table_ordinal = 0

    def walk(parent: ET.Element, path: str) -> None:
        nonlocal table_ordinal
        for index, child in enumerate(list(parent), 1):
            tag = child.tag
            if tag == f"{{{W}}}p":
                units.extend(_paragraphs(child, topic_id, f"{path}/p[{index}]", citation))
            elif tag == f"{{{W}}}tbl":
                table_ordinal += 1
                units.append(_table(child, topic_id, table_ordinal, citation))
            else:
                walk(child, f"{path}/{tag.rsplit('}', 1)[-1]}[{index}]")

    walk(container, f"{topic_id}/content")
    return units


def extract(source: Path = SOURCE) -> dict[str, Any]:
    raw = source.read_bytes()
    root = ET.fromstring(raw)
    metadata = next((p.find("pkg:xmlData", NS)[0] for p in root.findall("pkg:part", NS)
                     if p.find("pkg:xmlData", NS) is not None
                     and p.find("pkg:xmlData", NS)[0].tag == f"{{{EASA}}}document"), None)
    if metadata is None:
        raise ValueError("EASA metadata document not found")
    word = _part(root, "/word/document.xml")
    topic_nodes = []
    for topic in metadata.findall(".//e:topic", NS):
        normalized_title = re.sub(r"\s+", " ", topic.get("source-title", ""))
        if "ORO.FTL" in normalized_title or "CS FTL.1" in normalized_title:
            topic_nodes.append(topic)
    sdt_by_id = {}
    for sdt in word.findall(".//w:sdt", NS):
        ident = sdt.find("w:sdtPr/w:id", NS)
        content = sdt.find("w:sdtContent", NS)
        if ident is not None and content is not None:
            sdt_by_id[ident.get(f"{{{W}}}val", "")] = content

    topics = []
    for topic in topic_nodes:
        topic_id = topic.get("ERulesId", "")
        title = topic.get("source-title", "")
        content = sdt_by_id.get(topic.get("sdt-id", ""))
        if content is None:
            raise ValueError(f"EASA topic has no matching content control: {topic_id} ({topic.get('sdt-id')})")
        units = _walk_units(content, topic_id, title)
        topics.append({
            "id": topic_id, "title": title,
            "content_type": topic.get("TypeOfContent", "").strip("; "),
            "units": units,
        })

    return {
        "documents": [{
            "id": DOCUMENT_ID, "title": "EASA FTL", "version": VERSION,
            "publisher_url": PUBLISHER_URL, "sha256": hashlib.sha256(raw).hexdigest(),
            "topics": topics,
        }],
        "models": [], "links": [],
    }
