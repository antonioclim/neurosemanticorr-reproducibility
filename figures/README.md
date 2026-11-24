# Figures

The four figures combine the Study Contract workflow, retained verifier outcomes, supervisor timing and exact reference-model results. This directory accompanies neuroSEMANTICorr **1.0.0**.

## Browse and edit

| Figure | Subject | Editable drawing | Vector source | Preview |
| --- | --- | --- | --- | --- |
| 1 | Study Contract workflow | [ODG](01_editable_odg/JSS_Figure_1_Study_Contract.odg) | [SVG](04_sources/P6_F01_STUDY_CONTRACT_WORKFLOW.svg) | [PNG](06_preview_png/JSS_Figure_1_Study_Contract.png) |
| 2 | Functional outcomes | [ODG](01_editable_odg/JSS_Figure_2_Functional_Outcomes.odg) | [SVG](04_sources/P6_F02_FROZEN_P4_OUTCOMES.svg) | [PNG](06_preview_png/JSS_Figure_2_Functional_Outcomes.png) |
| 3 | Supervisor timing | [ODG](01_editable_odg/JSS_Figure_3_Supervisor_Timing.odg) | [SVG](04_sources/P6_F03_FROZEN_P4_TIMING.svg) | [PNG](06_preview_png/JSS_Figure_3_Supervisor_Timing.png) |
| 4 | Reference bounds and query minima | [ODG](01_editable_odg/JSS_Figure_4_Reference_Audit.odg) | [SVG](04_sources/F4_REFERENCE_AUDIT.svg) | [PNG](06_preview_png/JSS_Figure_4_Reference_Audit.png) |

Browse the [figure gallery and captions](CAPTIONS.md) for inline previews of all four figures. Their canonical text is stored in [CAPTIONS_EN_GB.json](04_sources/CAPTIONS_EN_GB.json).

The ODG files contain 861 native drawing primitives, 10 groups and 167 text paragraphs. Text, lines, markers, outlines, fills and hatches can be selected and edited in LibreOffice Draw. Figure 2 contains ten groups; enter a group to edit its components. Embedded images or OLE objects do not replace the drawings.

The drawings and SVG sources use **DejaVu Sans**. Font files are not embedded in the ODG drawings, so install this family before editing or rebuilding. Other font names retained in LibreOffice's default style declarations do not imply that the figure labels use those fonts.

## Data and geometry

| Material | Location | Purpose |
| --- | --- | --- |
| Workflow graph | [ARCHITECTURE_GRAPH.json](04_sources/ARCHITECTURE_GRAPH.json) | Seven nodes and six declared conceptual relations for Figure 1. |
| Outcome and timing data | [plot_data](04_sources/plot_data/) | Counts, 400 matched timing pairs, 100 case summaries and eight block summaries. |
| Reference-model figure data | [FIGURE4_DATA.json](04_sources/FIGURE4_DATA.json) | Conditional intervals and nine fixed-query minima used by Figure 4. |
| Retained reports and certificates | [reference_audit](04_sources/reference_audit/) | Source bindings, base requests and eighteen query certificates. |
| Reference text layout | [text_layout](04_sources/text_layout/) | Original text coordinates, bounds, directions, sizes and colours, bound to the corresponding SVG and original vector-reference hashes. |
| Qualification records | [05_validation](05_validation/README.md) | Current reconstruction, numerical, geometric and native-object checks alongside the retained records. |

The SVG files retain the drawing geometry. The text-layout JSON files allow the native-object builder to recover the original reference text geometry without shipping source PDF files. Source labels and coordinates are preserved at their extracted numerical precision.

The SVG sources and PNG previews retain the exact bytes of the retained figure set. Each ODG preserves its drawing content, styles, authorship and thumbnail; only its four visible-area settings have been set to the page dimensions. Native Draw exports before and after that adjustment have identical text, vector paths and pixels at 300 dpi. The presentation formats in this directory are ODG, SVG and PNG; captions and instructions are Markdown. Licensing terms follow the distribution's licence and attribution files.

## Check the delivered files

Use Python 3.12. The integrity check uses the standard library:

```sh
python3 -B 09_tools/figure_manifest.py --root .
python3 -B 09_tools/normalise_draw_view.py --root . --check
```

The source-data and SVG-geometry check requires the Python dependencies below. It reads the retained data without requiring PDF exports:

```sh
python3 -B 09_tools/verify_figure_data.py --root . --data-only
```

An integrity result verifies file identity. The data-only mode checks counts, paired intervals and source geometry; it does not claim to inspect a new rendered export.

## Rebuild in a working copy

Work in a separate copy of this directory because the builders replace generated files. Install the pinned Python packages:

```sh
python3 -m pip install -r 09_tools/requirements_figures.txt
```

The complete reconstruction also needs LibreOffice with the `soffice` command, Poppler's `pdffonts` utility and DejaVu Sans. The current qualification used Python 3.12.14, the exact pinned Python dependencies, LibreOfficeDev 26.8.0.0.alpha0 and Poppler 25.03.0 on Linux.

From the copied figures directory:

```sh
python3 -B 09_tools/build_draw_figures.py --root .
python3 -B 09_tools/build_figure4.py --root .
python3 -B 09_tools/build_and_verify_f4.py --root . --evidence ../figure_rebuild_evidence
python3 -B 09_tools/verify_figure_data.py --root .
python3 -B 09_tools/verify_figure4_geometry.py --root .
python3 -B 09_tools/verify_draw_round_trip.py --root . --expected 4
python3 -B 09_tools/normalise_draw_view.py --root . --check
python3 -B 09_tools/figure_manifest.py --root . --seal
```

The first builder reads the retained SVG geometry and text-layout JSON for Figures 1–3. The second reads Figure 4's numerical bindings and certificates, then rebuilds its source graphic and native objects. The native Draw checks normalise the generated ODG visible-area settings, then use disposable copies to test object edits, saved geometry and rendered output. The normaliser changes only the four view settings; it can also be run separately with `python3 -B 09_tools/normalise_draw_view.py --root .`.

**PDF and TIFF are local reconstruction outputs.** The full reconstruction creates them for rendering, geometry and font checks inside the working copy. They are not included in this distributed figure tree. Using these optional export formats does not require adding them to the public repository.

The [1.0.0 qualification record](05_validation/F2_FIGURE_QUALIFICATION.json) records successful reconstruction of all four figures, replay of all eighteen Figure 4 certificates, native Draw persistence checks, numerical and rendered-geometry checks, embedded fonts and visual inspection. All four regenerated previews were byte-identical to the delivered previews. The object-edit test changed ODF XML in disposable copies and loaded, saved and reloaded them through LibreOffice Draw; a graphical editing session was not part of this test.

## Replay the Figure 4 certificates

The data needed to redraw Figure 4 are already present. To recalculate its query certificates, point the driver to the extracted software distribution containing `r5_f3/reference_audit`.

If this directory is located at `software/figures/`, run:

```sh
python3 -B 09_tools/derive_figure4_data.py --root . --software ..
```

For another arrangement, set `--software` to that software root. The driver reads the retained scope report and mathematical comparison report in this directory, calls the reference-audit implementation and checks that its runtime sources remain unchanged. It does not create new prospective observations.

## Editing a figure

Open its ODG in LibreOffice Draw. Double-click text to edit it; select shapes or group members to change their properties. Keep a working copy and retain the original file. If a numerical value changes, update the linked data and rebuild the figure so that labels, geometry and captions remain consistent.
