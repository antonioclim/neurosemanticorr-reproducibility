#!/usr/bin/env python3
"""Set the ODG visible-area rectangle to its page without changing drawing data.

LibreOffice Draw stores this rectangle in hundredths of a millimetre. Only
the four VisibleArea values in settings.xml are replaced; every other ODF
member, including styles, geometry, authorship and thumbnails, is preserved.
"""
from __future__ import annotations

import argparse
from copy import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}


def hundredths_mm(value):
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(cm|mm|in|pt)", value)
    if not match:
        raise ValueError(f"Unsupported page dimension: {value!r}")
    scale = {"cm": Decimal(1000), "mm": Decimal(100),
             "in": Decimal(2540), "pt": Decimal(2540) / Decimal(72)}
    result = Decimal(match[1]) * scale[match[2]]
    if not 0 < result <= 2147483647 or result != result.to_integral_value():
        raise ValueError(f"Page dimension is not an exact positive 1/100 mm integer: {value!r}")
    return int(result)


def normalise(path, *, check=False):
    path = Path(path)
    before_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    with ZipFile(path) as package:
        infos = package.infolist()
        members = {item.filename: package.read(item) for item in infos}
        if len(members) != len(infos):
            raise ValueError("Duplicate ODF package members")
        comment = package.comment
    pages = ET.fromstring(members["styles.xml"]).findall(".//style:page-layout-properties", NS)
    if len(pages) != 1:
        raise ValueError("Exactly one page layout is required")
    width = hundredths_mm(pages[0].get(f"{{{NS['fo']}}}page-width", ""))
    height = hundredths_mm(pages[0].get(f"{{{NS['fo']}}}page-height", ""))
    expected = {"VisibleAreaTop": 0, "VisibleAreaLeft": 0,
                "VisibleAreaWidth": width, "VisibleAreaHeight": height}
    original = {}
    settings = members["settings.xml"]
    for name, value in expected.items():
        pattern = (rb'(<config:config-item\b[^>]*\bconfig:name="' + name.encode("ascii")
                   + rb'"[^>]*>)(-?\d+)(</config:config-item>)')
        matches = list(re.finditer(pattern, settings))
        if len(matches) != 1:
            raise ValueError(f"Exactly one integer setting is required for {name}")
        original[name] = int(matches[0][2])
        settings = re.sub(pattern, lambda m: m[1] + str(value).encode("ascii") + m[3], settings)
    changed = settings != members["settings.xml"]
    if check and changed:
        raise ValueError(f"Visible-area rectangle differs from the page: {path.name}")
    if changed:
        mode = path.stat().st_mode
        with NamedTemporaryFile(prefix=".nsc-view-", suffix=".odg", dir=path.parent, delete=False) as tmp:
            temporary = Path(tmp.name)
        try:
            with ZipFile(temporary, "w") as package:
                package.comment = comment
                for info in infos:
                    data = settings if info.filename == "settings.xml" else members[info.filename]
                    package.writestr(copy(info), data)
            with ZipFile(temporary) as package:
                assert package.namelist() == [item.filename for item in infos]
                assert all(package.read(name) == data for name, data in members.items()
                           if name != "settings.xml")
                ET.fromstring(package.read("settings.xml"))
            os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"file": path.name, "changed": changed, "unit": "1/100 mm",
            "before": original, "after": expected,
            "only_changed_member": "settings.xml" if changed else None,
            "before_sha256": before_hash,
            "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    cli.add_argument("--check", action="store_true", help="Validate without changing files")
    args = cli.parse_args()
    paths = sorted((args.root / "01_editable_odg").glob("*.odg"))
    if len(paths) != 4:
        raise ValueError("Exactly four figure ODG files are required")
    checks = [normalise(path, check=args.check) for path in paths]
    print(json.dumps({"status": "PASS_DRAW_VISIBLE_AREA", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
