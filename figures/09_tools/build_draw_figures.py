#!/usr/bin/env python3
"""Translate retained artwork to editable ODF Draw objects and export it."""

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

import fitz
from lxml import etree as xml
from PIL import Image
from svgpathtools import CubicBezier, Line, parse_path
from reference_layout import read_reference_layout, reference_identity

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}
MIMETYPE = "application/vnd.oasis.opendocument.graphics"
PT_TO_MM = 25.4 / 72
PT_TO_ODF = PT_TO_MM * 100
NAMES = {
    "JSS_Figure_1_Study_Contract": "P6_F01_STUDY_CONTRACT_WORKFLOW",
    "JSS_Figure_2_Functional_Outcomes": "P6_F02_FROZEN_P4_OUTCOMES",
    "JSS_Figure_3_Supervisor_Timing": "P6_F03_FROZEN_P4_TIMING",
}


def key(name):
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def write_element(parent, tag, attributes=None):
    return xml.SubElement(parent, key(tag), {key(k): str(v) for k, v in (attributes or {}).items()})


def root_element(tag):
    return xml.Element(key(tag), {key("office:version"): "1.3"}, nsmap=NS)


def serial(element):
    return xml.tostring(element, encoding="UTF-8", xml_declaration=True)


def mm(value):
    return f"{value * PT_TO_MM:.5f}mm"


def point(value):
    return f"{value:.5f}pt"


def colour(value):
    return "#ffffff" if value == "white" else value


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def cut_line(a, b, rect):
    x0, x1, y0, y1 = rect
    low, high = 0.0, 1.0
    v = b - a
    for p, q in ((-v.real, a.real - x0), (v.real, x1 - a.real),
                 (-v.imag, a.imag - y0), (v.imag, y1 - a.imag)):
        if abs(p) < 1e-12:
            if q < -1e-7:
                return None
            continue
        candidate = q / p
        if p < 0:
            low = max(low, candidate)
        else:
            high = min(high, candidate)
        if low >= high:
            return None
    return a + v * low, a + v * high


def circle_clip(center, radius, rect):
    """Vector approximation is used only for a dot cut by a bar edge."""
    points = [center + radius * complex(math.cos(k * math.tau / 64), math.sin(k * math.tau / 64))
              for k in range(64)]
    for coordinate, boundary, sense in (("real", rect[0], 1), ("real", rect[1], -1),
                                        ("imag", rect[2], 1), ("imag", rect[3], -1)):
        clipped = []
        for a, b in zip(points[-1:] + points[:-1], points):
            av, bv = getattr(a, coordinate), getattr(b, coordinate)
            a_in, b_in = (av - boundary) * sense >= 0, (bv - boundary) * sense >= 0
            if a_in != b_in:
                clipped.append(a + (b - a) * ((boundary - av) / (bv - av)))
            if b_in:
                clipped.append(b)
        points = clipped
    return points


def style_values(node, prior):
    result = prior.copy()
    for name in ("fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
                 "stroke-dasharray", "marker-end", "clip-path"):
        if name in node.attrib:
            result[name] = node.get(name)
    for clause in node.get("style", "").split(";"):
        if ":" in clause:
            name, value = clause.split(":", 1)
            result[name.strip()] = value.strip()
    return result


class Drawing:
    def __init__(self, width, height, title):
        self.width, self.height, self.title = width, height, title
        self.document = root_element("office:document-content")
        fonts = write_element(self.document, "office:font-face-decls")
        write_element(fonts, "style:font-face", {
            "style:name": "DejaVuSans", "svg:font-family": "DejaVu Sans", "style:font-family-generic": "swiss",
        })
        self.styles = write_element(self.document, "office:automatic-styles")
        doc = write_element(write_element(self.document, "office:body"), "office:drawing")
        self.page = write_element(doc, "draw:page", {
            "draw:name": title, "draw:master-page-name": "Default", "draw:style-name": "dp",
        })
        self.objects = Counter()
        self.graphics_cache = {}
        self.text_cache = {}
        st = write_element(self.styles, "style:style", {"style:name": "dp", "style:family": "drawing-page"})
        write_element(st, "style:drawing-page-properties", {"draw:fill": "none"})

    def graphics_style(self, fill="none", stroke="none", width=1, cap="butt", join="round", dash=""):
        index = (fill, stroke, width, cap, join, dash)
        if index not in self.graphics_cache:
            name = f"gr{len(self.graphics_cache) + 1}"
            data = {
                "draw:fill": "none" if fill == "none" else "solid",
                "draw:stroke": "none" if stroke == "none" else "solid",
            }
            if fill != "none":
                data["draw:fill-color"] = colour(fill)
            if stroke != "none":
                data.update({
                    "svg:stroke-color": colour(stroke), "svg:stroke-width": mm(width),
                    "svg:stroke-linecap": cap, "draw:stroke-linejoin": join,
                })
            if dash and stroke != "none":
                on, off = (float(k) for k in dash.split(","))
                dash_name = f"dash{len(self.graphics_cache) + 1}"
                write_element(self.styles, "draw:stroke-dash", {
                    "draw:name": dash_name, "draw:style": "rect", "draw:dots1": "1",
                    "draw:dots1-length": mm(on), "draw:distance": mm(off),
                })
                data.update({"draw:stroke": "dash", "draw:stroke-dash": dash_name})
            st = write_element(self.styles, "style:style", {"style:name": name, "style:family": "graphic"})
            write_element(st, "style:graphic-properties", data)
            self.graphics_cache[index] = name
        return self.graphics_cache[index]

    def shape(self, parent, kind, name, style, coordinates):
        self.objects[kind] += 1
        return write_element(parent, f"draw:{kind}", {
            "draw:name": name, "draw:style-name": style, **coordinates,
        })

    def rect(self, parent, name, x, y, width, height, style, radius=0, kind="rect"):
        coordinates = {"svg:x": mm(x), "svg:y": mm(y), "svg:width": mm(width), "svg:height": mm(height)}
        if radius:
            coordinates["draw:corner-radius"] = mm(radius)
        return self.shape(parent, kind, name, style, coordinates)

    def line(self, parent, name, a, b, style):
        return self.shape(parent, "line", name, style, {
            "svg:x1": mm(a.real), "svg:y1": mm(a.imag), "svg:x2": mm(b.real), "svg:y2": mm(b.imag),
        })

    def path(self, parent, name, parts, style):
        all_xy = [p for commands in parts for _, vals in commands for p in vals]
        if len(all_xy) < 2:
            return
        x0 = min(x.real for x in all_xy)
        y0 = min(x.imag for x in all_xy)
        width = max(max(x.real for x in all_xy) - x0, .01)
        height = max(max(x.imag for x in all_xy) - y0, .01)
        view_width, view_height = max(1, round(width * PT_TO_ODF)), max(1, round(height * PT_TO_ODF))
        d = " ".join(" ".join([cmd] + [f"{round((v.real-x0) * PT_TO_ODF)} {round((v.imag-y0) * PT_TO_ODF)}"
                                     for v in vals])
                     for commands in parts for cmd, vals in commands)
        self.shape(parent, "path", name, style, {
            "svg:x": mm(x0), "svg:y": mm(y0), "svg:width": mm(width), "svg:height": mm(height),
            "svg:viewBox": f"0 0 {view_width} {view_height}", "svg:d": d,
        })

    def poly(self, parent, name, points, style):
        if len(points) >= 3:
            self.path(parent, name, [[("M", points[:1]), ("L", points[1:]), ("Z", [])]], style)

    def text(self, parent, name, label, origin, bounds, size, fill="#000000", bold=False, angle=0):
        if not label:
            return
        index = (round(size, 5), fill, bold)
        if index not in self.text_cache:
            name_id = f"P{len(self.text_cache) + 1}"
            st = write_element(self.styles, "style:style", {"style:name": name_id, "style:family": "paragraph"})
            write_element(st, "style:paragraph-properties", {
                "fo:margin": "0mm", "fo:text-align": "left", "fo:line-height": "100%",
            })
            write_element(st, "style:text-properties", {
                "style:font-name": "DejaVuSans", "fo:font-family": "DejaVu Sans",
                "fo:font-size": point(size), "fo:color": fill,
                "fo:font-weight": "bold" if bold else "normal",
            })
            self.text_cache[index] = name_id
        style_name = "textBox"
        if not self.styles.xpath(".//*[@style:name='textBox']", namespaces=NS):
            st = write_element(self.styles, "style:style", {"style:name": style_name, "style:family": "graphic"})
            write_element(st, "style:graphic-properties", {
                "draw:fill": "none", "draw:stroke": "none", "draw:auto-grow-height": "false",
                "draw:auto-grow-width": "false", "draw:textarea-horizontal-align": "left",
                "draw:textarea-vertical-align": "top", "fo:padding-left": "0mm",
                "fo:padding-right": "0mm", "fo:padding-top": "0mm", "fo:padding-bottom": "0mm",
            })
        if angle == 0:
            coordinates = {"svg:x": mm(origin[0]), "svg:y": mm(origin[1] - .925 * size)}
            width = bounds[2] - bounds[0]
        else:
            coordinates = {
                "draw:transform": f"rotate(1.57079632679) translate({mm(origin[0] - .925*size)} {mm(origin[1])})",
            }
            width = bounds[3] - bounds[1]
        coordinates.update({"svg:width": mm(max(1, width) + 5), "svg:height": mm(1.7 * size)})
        frame = self.shape(parent, "frame", name, style_name, coordinates)
        box = write_element(frame, "draw:text-box")
        p = write_element(box, "text:p", {"text:style-name": self.text_cache[index]})
        # Preserve internal groups of spaces that ODF otherwise collapses.
        pieces = re.split(r"( {2,})", label)
        p.text = pieces[0]
        for run, tail in zip(pieces[1::2], pieces[2::2]):
            spacer = write_element(p, "text:s", {"text:c": len(run)})
            spacer.tail = tail

    def save(self, path):
        style_document = root_element("office:document-styles")
        write_element(style_document, "office:styles")
        auto = write_element(style_document, "office:automatic-styles")
        layout = write_element(auto, "style:page-layout", {"style:name": "Layout"})
        write_element(layout, "style:page-layout-properties", {
            "fo:page-width": mm(self.width), "fo:page-height": mm(self.height),
            "fo:margin-top": "0mm", "fo:margin-bottom": "0mm",
            "fo:margin-left": "0mm", "fo:margin-right": "0mm",
            "style:print-orientation": "landscape",
        })
        master = write_element(style_document, "office:master-styles")
        write_element(master, "style:master-page", {
            "style:name": "Default", "style:page-layout-name": "Layout",
        })
        metadata = root_element("office:document-meta")
        meta = write_element(metadata, "office:meta")
        write_element(meta, "dc:title").text = self.title
        write_element(meta, "dc:language").text = "en-GB"
        manifest = xml.Element(key("manifest:manifest"), {key("manifest:version"): "1.3"}, nsmap=NS)
        write_element(manifest, "manifest:file-entry", {"manifest:full-path": "/", "manifest:version": "1.3",
                                                       "manifest:media-type": MIMETYPE})
        members = {"content.xml": self.document, "styles.xml": style_document, "meta.xml": metadata}
        for name in members:
            write_element(manifest, "manifest:file-entry", {"manifest:full-path": name,
                                                            "manifest:media-type": "text/xml"})
        with ZipFile(path, "w", ZIP_DEFLATED) as z:
            z.writestr("mimetype", MIMETYPE, ZIP_STORED)
            for name, data in members.items():
                z.writestr(name, serial(data))
            z.writestr("META-INF/manifest.xml", serial(manifest))


def pattern_rect(drawing, parent, name, bounds, fill, border):
    x0, x1, y0, y1 = bounds
    if x1 <= x0 or y1 <= y0:
        drawing.line(parent, name, complex(x0, y0), complex(x1, y1), border)
        return
    background, spacing = {
        "url(#ha602a9d19d)": ("#0072b2", 8),
        "url(#h9d129bb638)": ("#d55e00", None),
        "url(#hf8d0d75958)": ("#72777d", 12),
    }[fill]
    layer = write_element(parent, "draw:g", {"draw:name": name})
    drawing.rect(layer, f"{name} fill", x0, y0, x1 - x0, y1 - y0, drawing.graphics_style(background))
    ink = drawing.graphics_style("#222222")
    if spacing:
        ink_line = drawing.graphics_style("none", "#222222", 1)
        for k in range(math.floor((x0+y0)/spacing), math.ceil((x1+y1)/spacing)+1):
            offset = k * spacing
            if ends := cut_line(complex(x0, offset-x0), complex(x1, offset-x1), bounds):
                drawing.line(layer, f"{name} hatch {k}", *ends, ink_line)
    else:
        radius = .9
        for j in range(math.floor((y0-radius)/4), math.ceil((y1+radius)/4)+1):
            y = 4*j
            shift = 2*(j % 2)
            for k in range(math.floor((x0-shift-radius)/4), math.ceil((x1-shift+radius)/4)+1):
                x = 4*k + shift
                if x0 <= x-radius and x+radius <= x1 and y0 <= y-radius and y+radius <= y1:
                    drawing.rect(layer, f"{name} dot {j}.{k}", x-radius, y-radius, 2*radius, 2*radius,
                                 ink, kind="ellipse")
                elif x+radius > x0 and x-radius < x1 and y+radius > y0 and y-radius < y1:
                    points = circle_clip(complex(x, y), radius, bounds)
                    drawing.poly(layer, f"{name} boundary dot {j}.{k}", points, ink)
    drawing.rect(layer, f"{name} outline", x0, y0, x1 - x0, y1 - y0, border)


def path_commands(path, scale, offset, clip, dashed):
    result = []
    for subpath in path.continuous_subpaths():
        series = []
        if len(subpath) == 1 and isinstance(subpath[0], Line) and clip is not None and not dashed:
            ends = cut_line(subpath.start * scale + offset, subpath.end * scale + offset, clip)
            if ends:
                result.append([("M", [ends[0]]), ("L", [ends[1]])])
            continue
        for i, seg in enumerate(subpath):
            if i == 0:
                series.append(("M", [seg.start * scale + offset]))
            if isinstance(seg, Line):
                series.append(("L", [seg.end * scale + offset]))
            elif isinstance(seg, CubicBezier):
                series.append(("C", [p*scale + offset for p in (seg.control1, seg.control2, seg.end)]))
            else:
                raise ValueError(f"Unexpected SVG curve {type(seg)}")
        if subpath.isclosed():
            series.append(("Z", []))
        result.append(series)
    return result


def build_native(svg_file, pdf_file, out, title):
    svg = xml.parse(str(svg_file), xml.XMLParser(load_dtd=False, resolve_entities=False, no_network=True))
    labels_svg = Counter("".join(x.itertext()) for x in svg.xpath("//*[local-name()='text']"))
    width, height, spans = read_reference_layout(svg_file, pdf_file)
    labels_reference = Counter(s["text"] for _, s in spans)
    normalize = lambda labels: Counter({" ".join(k.split()): v for k, v in labels.items()})
    if normalize(labels_svg) != normalize(labels_reference):
        raise ValueError(f"SVG and retained reference labels differ: {labels_svg-labels_reference}, "
                         f"{labels_reference-labels_svg}")
    drawing = Drawing(width, height, title)
    viewbox = tuple(float(s) for s in svg.getroot().get("viewBox").split())
    scale = drawing.width / viewbox[2]
    if not math.isclose(scale * viewbox[3], drawing.height, abs_tol=.003):
        raise ValueError("SVG view box and reference PDF have different aspect ratios")
    lookup = {n.get("id"): n for n in svg.xpath("//*[@id]")}
    node_count = Counter()

    def walk(node, parent, style, offset=0j, caption="Object"):
        tag = xml.QName(node).localname
        if tag in {"metadata", "defs", "text", "title", "desc"}:
            return
        style = style_values(node, style)
        group = caption if tag == "use" else (node.get("id") or caption)
        if tag == "use":
            reference = node.get("{http://www.w3.org/1999/xlink}href")
            shift = complex(float(node.get("x", 0)), float(node.get("y", 0))) * scale
            walk(lookup[reference[1:]], parent, style, offset+shift, group)
            return
        if tag in {"g", "svg"}:
            for item in node:
                walk(item, parent, style, offset, group)
            return
        if tag not in {"path", "rect"}:
            raise ValueError(f"Unexpected SVG element {tag}")
        node_count[group] += 1
        name = f"{group} / {node_count[group]}"
        fill = style.get("fill", "#000000")
        stroke = style.get("stroke", "none")
        width = float(style.get("stroke-width", 1)) * scale
        dash = ",".join(str(float(n)*scale) for n in style["stroke-dasharray"].split(",")) if (
            "stroke-dasharray" in style) else ""
        cap, join = style.get("stroke-linecap", "butt"), style.get("stroke-linejoin", "round")
        if tag == "rect":
            drawing.rect(parent, name, float(node.get("x", 0))*scale+offset.real,
                         float(node.get("y", 0))*scale+offset.imag, float(node.get("width"))*scale,
                         float(node.get("height"))*scale, drawing.graphics_style(fill, stroke, width, cap, join),
                         float(node.get("rx", 0))*scale)
            return
        data = parse_path(node.get("d"))
        if not len(data):
            return
        if fill.startswith("url("):
            bounds = tuple(v*scale for v in data.bbox())
            pattern_rect(drawing, parent, name, bounds, fill,
                         drawing.graphics_style("none", stroke, width, cap, join))
            return
        clip = None
        if style.get("clip-path"):
            clip_node = lookup[style["clip-path"][5:-1]][0]
            x, y, w, h = (float(clip_node.get(n)) * scale for n in ("x", "y", "width", "height"))
            clip = (x, x+w, y, y+h)
        props = drawing.graphics_style(fill, stroke, width, cap, join, dash)
        commands = path_commands(data, scale, offset, clip, dash)
        if len(commands) == 1 and [item[0] for item in commands[0]] == ["M", "L"]:
            drawing.line(parent, name, commands[0][0][1][0], commands[0][1][1][0], props)
        else:
            drawing.path(parent, name, commands, props)
        if style.get("marker-end"):
            head = lookup[style["marker-end"][5:-1]]
            ref = complex(float(head.get("refX")), float(head.get("refY")))
            direction = (data[-1].end - data[-1].start)
            end = data.end * scale + offset
            points = [end + (seg.start-ref) * scale * direction / abs(direction)
                      for seg in parse_path(head[0].get("d"))]
            drawing.poly(parent, name + " arrowhead", points,
                         drawing.graphics_style(head[0].get("fill")))
    walk(svg.getroot(), drawing.page, {})
    for i, (angle, s) in enumerate(spans, 1):
        if angle not in {(1., 0.), (0., -1.)}:
            raise ValueError(f"Unexpected text angle {angle}")
        drawing.text(drawing.page, f"Label {i:02d} / {s['text']}", s["text"], s["origin"], s["bbox"], s["size"],
                     f"#{s['color']:06x}", bool(s["flags"] & 16), 0 if angle == (1., 0.) else 90)
    drawing.save(out)
    return drawing.objects, [s["text"] for _, s in spans]


def read_native_labels(path):
    with ZipFile(path) as z:
        t = xml.fromstring(z.read("content.xml"))
        pages = t.xpath("//office:drawing/draw:page", namespaces=NS)
        assert len(pages) == 1 and z.testzip() is None
        assert z.read("mimetype").decode() == MIMETYPE
        assert not t.xpath("//draw:image | //draw:object | //draw:object-ole", namespaces=NS)
        assert not any(n.startswith(("Pictures/", "Object ")) for n in z.namelist())
    labels = []
    for p in t.xpath("//draw:text-box/text:p", namespaces=NS):
        full = p.text or ""
        for kid in p:
            assert kid.tag == key("text:s")
            full += " " * int(kid.get(key("text:c"), 1)) + (kid.tail or "")
        labels.append(full)
    counts = Counter(xml.QName(n).localname for n in t.xpath("//draw:page//draw:*", namespaces=NS))
    return labels, counts


def inspect_and_raster(odg, pdf, tiff, expected, dpi):
    labels, counts = read_native_labels(odg)
    assert labels == expected
    with fitz.open(pdf) as d:
        assert len(d) == 1 and not d[0].get_images(full=True)
        page = d[0]
        native = Counter(" ".join(s["text"].split()) for b in page.get_text("dict")["blocks"] if "lines" in b
                         for l in b["lines"] for s in l["spans"])
        expected_counts = Counter(" ".join(s.split()) for s in expected)
        if native != expected_counts:
            raise AssertionError(f"{odg.name} output text mismatch: missing={expected_counts-native}, "
                                 f"surplus={native-expected_counts}")
        text_bounds = [fitz.Rect(s["bbox"]) for b in page.get_text("dict")["blocks"] if "lines" in b
                       for l in b["lines"] for s in l["spans"]]
        assert all(page.rect.contains(bounds) for bounds in text_bounds)
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
        raster = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        raster.save(tiff, dpi=(dpi, dpi), compression="tiff_lzw")
        dimensions = [round(page.rect.width*PT_TO_MM, 2), round(page.rect.height*PT_TO_MM, 2)]
        return {"editable_native_objects": counts, "matching_editable_labels": len(labels),
                "pdf_labels_in_bounds": len(text_bounds), "embedded_payload_images": 0,
                "draw_page_size_mm": dimensions, "tiff_size_px": [raster.width, raster.height], "dpi": dpi}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--soffice", default="soffice")
    args = p.parse_args()
    dest = args.root
    for name in ("01_editable_odg", "02_publication_pdf", "03_publication_tiff", "05_validation"):
        (dest / name).mkdir(parents=True, exist_ok=True)
    files = {}
    for index, (name, stem) in enumerate(NAMES.items(), 1):
        svg = dest / f"04_sources/{stem}.svg"
        pdf = dest / f"04_sources/{stem}.pdf"
        odg = dest / f"01_editable_odg/{name}.odg"
        counts, labels = build_native(svg, pdf, odg, name.replace("_", " "))
        files[odg] = (index, stem, labels, counts)
    pdf_dir = dest / "02_publication_pdf"
    subprocess.run([args.soffice, "--headless", "--convert-to", "pdf:draw_pdf_Export",
                    "--outdir", str(pdf_dir), *(str(p) for p in files)], check=True)
    audit = {}
    for path, (index, stem, labels, counts) in files.items():
        pdf = pdf_dir / path.with_suffix(".pdf").name
        tiff = dest / "03_publication_tiff" / path.with_suffix(".tiff").name
        dpi = 1000 if index == 1 else 500
        status = inspect_and_raster(path, pdf, tiff, labels, dpi)
        audit[str(index)] = {
            "source_svg_sha256": digest(dest / f"04_sources/{stem}.svg"),
            "source_text_reference": reference_identity(dest / f"04_sources/{stem}.svg", dest / f"04_sources/{stem}.pdf"),
            "odg_sha256": digest(path), "pdf_sha256": digest(pdf), "tiff_sha256": digest(tiff),
            **status,
        }
    report = {"status": "PASS_NATIVE_ODG_AND_DRAW_EXPORTS", "figure_checks": audit}
    (dest / "05_validation/FIGURE_CONVERSION_QA.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
