#!/usr/bin/env python3
"""Verify plotted positions against retained counts and matched intervals."""

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
from statistics import median

import fitz
from lxml import etree as xml
from svgpathtools import parse_path

from build_draw_figures import NAMES, digest
from reference_layout import read_reference_layout

PLOT_GROUPS = ("B_ASSERT", "T_FULL", "A0_SYNTAX", "A1_STRUCTURE", "A2_LOCAL", "A3_PROVENANCE")


def rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def svg_tree(path):
    return xml.parse(str(path), xml.XMLParser(load_dtd=False, resolve_entities=False, no_network=True))


def contained_objects(tree, identity, tag):
    item = tree.xpath("//*[@id=$identity]", identity=identity)
    assert len(item) == 1
    return item[0].xpath(".//*[local-name()=$name]", name=tag)


def match_number(a, b):
    assert math.isclose(a, b, rel_tol=0, abs_tol=2e-6), (a, b)


def check_outcomes(src, source_counts):
    for j, metric in enumerate(("D_strict_localisation", "M_vector_match", "full_conformance", "valid_rejected")):
        for i, arm in enumerate(PLOT_GROUPS[:2]):
            patch = 3 + 4*j + i
            path, = contained_objects(src, f"patch_{patch}", "path")
            clip, = contained_objects(src, path.get("clip-path")[5:-1], "rect")
            x0, x1, _, _ = parse_path(path.get("d")).bbox()
            width = (x1-x0) / float(clip.get("width"))
            n, d = source_counts[arm, metric]
            match_number(width, (100*n/d) / 112)
    for i, arm in enumerate(PLOT_GROUPS[2:]):
        path, = contained_objects(src, f"patch_{19+i}", "path")
        clip, = contained_objects(src, path.get("clip-path")[5:-1], "rect")
        _, _, y0, y1 = parse_path(path.get("d")).bbox()
        n, d = source_counts[arm, "D_rejected"]
        assert d == 32
        match_number((y1-y0) / float(clip.get("height")), n / 36)
        n, d = source_counts[arm, "complete_obligations"]
        expected = f"{n}/{d} complete obligations"
        assert any(t.text == expected for t in src.xpath("//*[local-name()='text']"))


def check_timing_sources(plot_data):
    raw = rows(plot_data / "raw_matched_pairs.csv")
    cases = rows(plot_data / "case_paired_timing.csv")
    blocks = rows(plot_data / "block_timing.csv")
    assert len(raw) == 400 and len(cases) == len({x["case_id"] for x in cases}) == 100 and len(blocks) == 8
    by_case, by_block = defaultdict(list), defaultdict(list)
    for row in raw:
        t, b = float(row["T_seconds"]), float(row["B_seconds"])
        diff = t-b
        assert diff == float(row["T_minus_B_seconds"]) and t/b == float(row["T_over_B"])
        by_case[row["case_id"]].append((row["block"], diff, t/b))
        for arm, elapsed in (("B_ASSERT", b), ("T_FULL", t)):
            by_block[row["block"], arm].append(elapsed)
    for row in cases:
        values = by_case[row["case_id"]]
        assert len(values) == len({v[0] for v in values}) == int(row["paired_blocks"]) == 4
        assert median(v[1] for v in values) == float(row["median_T_minus_B_seconds"])
        assert median(v[2] for v in values) == float(row["median_T_over_B"])
    for row in blocks:
        values = by_block[row["block"], row["arm"]]
        assert len(values) == int(row["observations"]) == 100
        assert median(values) == float(row["median_seconds"])
        assert min(values) == float(row["minimum_seconds"]) and max(values) == float(row["maximum_seconds"])
    return cases, blocks


def svg_markers(src, group):
    return [(float(u.get("x")), float(u.get("y"))) for u in contained_objects(src, group, "use")]


def check_timing_geometry(src, cases, blocks):
    a = 61.228346
    w = 433.700788
    # The retained first SVG panel maps x=0..101 and y=-25..25.
    top, height = 42.718110, 125.669292
    for ind, workflow in enumerate(("W1", "W2"), 1):
        source = svg_markers(src, f"PathCollection_{ind}")
        expected = [(a + (index+1)*w/101,
                     top + (25-1000*float(row["median_T_minus_B_seconds"]))*height/50)
                    for index, row in enumerate(cases) if row["workflow"] == workflow]
        assert len(source) == len(expected) == 50
        for (x, y), (sx, sy) in zip(source, expected, strict=True):
            match_number(x, sx)
            match_number(y, sy)
    # The retained second SVG panel maps x=.8..4.2 and y=120..155.
    top, height = 248.097638, 89.763780
    for arm, group in (("B_ASSERT", "line2d_32"), ("T_FULL", "line2d_33")):
        expected = [(a + (int(row["block"][-1])-.8) * w/3.4,
                     top + (155-1000*float(row["median_seconds"]))*height/35)
                    for row in blocks if row["arm"] == arm]
        source = svg_markers(src, group)
        assert len(source) == len(expected) == 4
        for (x, y), (sx, sy) in zip(source, expected, strict=True):
            match_number(x, sx)
            match_number(y, sy)


def geometry_distance(a, b):
    return max(abs(x-y) for x, y in zip(a, b, strict=True))


def pdf_markers(pdf, panel):
    # Filter by matching marker dimensions and colour so legend keys stay out.
    area = (42.7, 168.4, 4., 4.04) if panel == "A" else (260., 331., 3.95, 4.06)
    low, high, thin, thick = area
    with fitz.open(pdf) as source:
        paths = source[0].get_drawings()
    colours = ((0, 114, 178), (213, 94, 0))
    groups = []
    for target in colours:
        markers = []
        for row in paths:
            r, fill = row["rect"], row.get("fill")
            if fill and tuple(round(v*255) for v in fill) == target and low <= r.y0 and r.y1 <= high:
                if thin <= r.width <= thick and thin <= r.height <= thick:
                    markers.append(((r.x0+r.x1)/2, (r.y0+r.y1)/2))
        groups.append(markers)
    return groups


def check_geometry_in_export(src, result_pdf):
    max_displacement = 0.
    for panel, names, expected_length in [
        ("A", ("PathCollection_1", "PathCollection_2"), 50),
        ("B", ("line2d_32", "line2d_33"), 4),
    ]:
        groups = pdf_markers(result_pdf, panel)
        for group, points in zip(names, groups, strict=True):
            expected = svg_markers(src, group)
            assert len(points) == len(expected) == expected_length, (group, len(points), len(expected))
            for a, b in zip(sorted(points), sorted(expected), strict=True):
                max_displacement = max(max_displacement, geometry_distance(a, b))
    assert max_displacement <= .04, max_displacement
    return max_displacement


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    cli.add_argument("--data-only", action="store_true", help="Check retained data and source SVG geometry without generating or reading PDF exports.")
    args = cli.parse_args()
    out = args.root
    sources = out / "04_sources"
    plotted = sources / "plot_data"
    source_counts = {
        (row["arm"], row["metric"]): (int(row["numerator"]), int(row["denominator"]))
        for row in rows(plotted / "outcome_counts.csv")
    }
    assert len(source_counts) == 42
    check_outcomes(svg_tree(sources / "P6_F02_FROZEN_P4_OUTCOMES.svg"), source_counts)
    cases, blocks = check_timing_sources(plotted)
    timing = svg_tree(sources / "P6_F03_FROZEN_P4_TIMING.svg")
    check_timing_geometry(timing, cases, blocks)
    displacement = (None if args.data_only else check_geometry_in_export(timing, out / "02_publication_pdf/JSS_Figure_3_Supervisor_Timing.pdf"))
    graph = json.loads((sources / "ARCHITECTURE_GRAPH.json").read_text())
    assert len(graph["nodes"]) == 7 and len(graph["edges"]) == 6
    pdfs = out / "02_publication_pdf"
    all_bounds = {}
    if not args.data_only:
        for name, stem in NAMES.items():
            width, height, reference_spans = read_reference_layout(
                sources / f"{stem}.svg", sources / f"{stem}.pdf")
            with fitz.open(pdfs / f"{name}.pdf") as checked:
                assert abs(width - checked[0].rect.width) < .06
                assert abs(height - checked[0].rect.height) < .06
                assert not checked[0].get_images()
                checked_labels = checked[0].get_text("dict")["blocks"]
                x = [span for _, span in reference_spans]
                y = [s for b in checked_labels if "lines" in b
                     for l in b["lines"] for s in l["spans"]]
                new = defaultdict(list)
                for item in y:
                    new[" ".join(item["text"].split())].append(item["origin"])
                bounds = []
                for span in x:
                    same = new[" ".join(span["text"].split())]
                    shortest = min(same, key=lambda pos: geometry_distance(pos, span["origin"]))
                    bounds.append(geometry_distance(shortest, span["origin"]))
                    same.remove(shortest)
                all_bounds[name] = round(max(bounds), 5)
                assert max(bounds) < .55, (name, max(bounds))
    proof = {
        "status": ("PASS_RETAINED_DATA_AND_SOURCE_GEOMETRY" if args.data_only else "PASS_RETAINED_DATA_AND_RENDERED_GEOMETRY"),
        "rendered_export_checked": not args.data_only,
        "figure_1_conceptual_nodes": 7,
        "figure_1_source_relations": 6,
        "figure_2_data_bars_compared": 12,
        "figure_3_pairs_read": 400,
        "figure_3_case_marker_values": 100,
        "figure_3_block_marker_values": 8,
        "figure_3_max_rendered_marker_displacement_points": displacement,
        "figure_max_rendered_label_origin_displacement_points": all_bounds,
        "source_data_sha256": {p.name: digest(p) for p in sorted(plotted.iterdir()) if p.is_file()},
    }
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
