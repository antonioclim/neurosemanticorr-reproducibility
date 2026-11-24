#!/usr/bin/env python3
"""Verify the named shape and label inventory on native LibreOffice re-save."""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from lxml import etree as xml

from build_draw_figures import NS, key

SHAPES = {"frame", "rect", "g", "line", "path", "ellipse", "polygon", "polyline", "circle"}


def text_with_spaces(node):
    yield node.text or ""
    for child in node:
        if child.tag == key("text:s"):
            yield " " * int(child.get(key("text:c"), "1"))
        else:
            yield from text_with_spaces(child)
        yield child.tail or ""


def check_shapes(path):
    with ZipFile(path) as package:
        # A generated thumbnail is distinct from an image in a drawing page.
        assert not any(x.startswith("Pictures/") for x in package.namelist())
        tree = xml.fromstring(package.read("content.xml"))
    page, = tree.xpath("//office:drawing/draw:page", namespaces=NS)
    assert not page.xpath(".//draw:image | .//draw:object | .//draw:object-ole", namespaces=NS)
    shapes = [n for n in page.iter() if xml.QName(n).namespace == NS["draw"]
              and xml.QName(n).localname in SHAPES]
    names = {n.get(key("draw:name")) for n in shapes}
    assert len(names) == len(shapes) and None not in names
    counts = Counter(xml.QName(n).localname for n in shapes)
    texts = page.xpath(".//draw:text-box/text:p", namespaces=NS)
    labels = Counter(" ".join("".join(text_with_spaces(p)).split()) for p in texts)
    return names, counts, labels


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    cli.add_argument("--soffice", default="soffice")
    cli.add_argument("--expected", type=int, default=4)
    args = cli.parse_args()
    paths = sorted((args.root / "01_editable_odg").glob("*.odg"))
    assert len(paths) == args.expected
    with TemporaryDirectory(prefix="nsc-draw-verify-") as folder:
        completed = subprocess.run([args.soffice, "--headless", "--convert-to", "odg:draw8",
                                    "--outdir", folder, *(str(p) for p in paths)],
                                   check=True, capture_output=True, text=True)
        assert "using filter : draw8" in completed.stdout
        checks = {}
        for path in paths:
            names, original, labels = check_shapes(path)
            new_names, new_counts, new_labels = check_shapes(Path(folder) / path.name)
            assert names == new_names and labels == new_labels
            assert sum(original.values()) == sum(new_counts.values())
            checks[path.name] = {"labels": sum(labels.values()),
                                "named_shapes_and_groups": sum(original.values()),
                                "reopened_shape_types": new_counts}
    print(json.dumps({"status": "PASS_LIBREOFFICE_DRAW_OPEN_AND_RESAVE", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
