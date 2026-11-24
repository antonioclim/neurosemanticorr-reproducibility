"""Load the retained text geometry used to rebuild native figure objects."""
from hashlib import sha256
import json
from pathlib import Path
import fitz

def read_reference_layout(svg_file, pdf_file):
    svg_file, pdf_file = Path(svg_file), Path(pdf_file)
    if pdf_file.is_file():
        with fitz.open(pdf_file) as pdf:
            if len(pdf) != 1:
                raise ValueError("Expected a single-page reference figure")
            page = pdf[0]
            spans = [(tuple(line["dir"]), span)
                     for block in page.get_text("dict")["blocks"] if "lines" in block
                     for line in block["lines"] for span in line["spans"]]
            return page.rect.width, page.rect.height, spans
    layout_file = svg_file.parent / "text_layout" / (svg_file.stem + ".json")
    layout = json.loads(layout_file.read_text(encoding="utf-8"))
    if layout["schema"] != "nsc-figure-reference-layout/1":
        raise ValueError("Unsupported reference-layout schema")
    if sha256(svg_file.read_bytes()).hexdigest() != layout["source_svg_sha256"]:
        raise ValueError("Reference text layout belongs to different SVG bytes")
    spans = [(tuple(item["direction"]), item["span"]) for item in layout["spans"]]
    return layout["page_width_pt"], layout["page_height_pt"], spans

def reference_identity(svg_file, pdf_file):
    pdf_file, svg_file = Path(pdf_file), Path(svg_file)
    source = pdf_file if pdf_file.is_file() else svg_file.parent / "text_layout" / (svg_file.stem + ".json")
    return {"kind": "vector_pdf" if source.suffix == ".pdf" else "retained_text_layout",
            "file": source.name, "sha256": sha256(source.read_bytes()).hexdigest()}
