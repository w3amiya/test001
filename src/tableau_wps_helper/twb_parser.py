from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorksheetInfo:
    name: str


class TwbParseError(RuntimeError):
    pass


def list_worksheets(twb_path: str | Path) -> list[WorksheetInfo]:
    path = Path(twb_path).expanduser()
    if not path.exists():
        raise TwbParseError(f"TWB file not found: {path}")
    if path.suffix.lower() != ".twb":
        raise TwbParseError(f"Only .twb is supported in phase 1: {path}")

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise TwbParseError(f"Invalid Tableau workbook XML: {path}") from exc

    root = tree.getroot()
    names: list[str] = []
    for worksheet in root.findall(".//worksheets/worksheet"):
        name = worksheet.attrib.get("name", "").strip()
        if name and name not in names:
            names.append(name)

    if not names:
        # Some Tableau files may use a flatter shape.
        for worksheet in root.findall(".//worksheet"):
            name = worksheet.attrib.get("name", "").strip()
            if name and name not in names:
                names.append(name)

    return [WorksheetInfo(name=name) for name in names]
