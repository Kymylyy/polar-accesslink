from __future__ import annotations

import xml.etree.ElementTree as ET

TCX_NS = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}


def parse_tcx_metadata(xml_text: str) -> dict[str, str | None]:
    root = ET.fromstring(xml_text)
    return {
        "title": _first_text(root, ".//tcx:Training/tcx:Plan/tcx:Name"),
        "notes": _first_text(root, ".//tcx:Notes"),
    }


def _first_text(root: ET.Element, path: str) -> str | None:
    node = root.find(path, TCX_NS)
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None
