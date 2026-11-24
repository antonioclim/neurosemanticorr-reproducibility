# Figure qualification records

## Current distribution

[F2_FIGURE_QUALIFICATION.json](F2_FIGURE_QUALIFICATION.json) records the executed qualification of neuroSEMANTICorr 1.0.0: reconstruction of all four figures, eighteen certificate replays, data and geometry checks, native Draw object persistence, font checks and visual inspection. It binds the delivered ODG, SVG, PNG and tool files by their SHA-256 hashes.

The object test modified names, text, positions, fills, stroke colours and line widths in disposable ODF XML copies, then loaded, saved and reloaded them through LibreOffice Draw. It covered 861 primitives and ten groups. Restoring the original properties recovered the original geometry, labels and rendered pixels. This execution used Draw's native import/export filters; it did not include a graphical editing session.

The delivered ODG files also contain a minimal view-metadata correction. Their `VisibleAreaTop` and `VisibleAreaLeft` values are zero; width and height match the page in hundredths of a millimetre. Every other ODF member is byte-identical to the retained drawing. Direct native exports of the original, corrected and temporarily resaved versions had identical text, vector paths and pixels at 300 dpi. This is a metadata normalisation; no graphical-interface defect was demonstrated.

The unit follows LibreOffice's [document-shell map-unit initialisation](https://docs.libreoffice.org/sfx2/html/objxtor_8cxx_source.html), [visible-area property implementation](https://docs.libreoffice.org/sd/html/unomodel_8cxx_source.html) and [view-settings import](https://docs.libreoffice.org/xmloff/html/sdxmlimp_8cxx_source.html). These sources establish the property semantics; the native export comparisons establish the observed result for these four files.

## Retained records

The other JSON records retain their original run labels and hashes. They identify the earlier evidence from which the drawing geometry, sources and previews were selected. The current qualification supplements those records without rewriting their history.

Some retained records refer to PDF and TIFF exports used during qualification. Those names identify historical evidence. The public figure tree supplies ODG, SVG and PNG; reconstruction creates fresh local PDF and TIFF exports in a working copy.

[FIGURE_KIT_MANIFEST.json](../FIGURE_KIT_MANIFEST.json) binds the complete delivered file set. A future reconstruction should be assessed from its own execution records and visual output.
