# Qualification of version 1.0.0

The distribution was qualified with **CPython 3.12.14 on Linux x86_64**. The integrated workflow executes the supplied components, checks their declared corpus sizes and results and verifies that the source inventory remains unchanged.

## Executed checks

| Component | Qualified coverage |
| --- | --- |
| Reference audit | 27 unit tests and 17 examples |
| O15 unit and command-line interfaces | 23 unit tests and eight CLI checks |
| Documentary regression | 202 dossiers and 1,010 convention comparisons |
| Native P4 diagnostics | 94 invocations |
| Native P5 diagnostics | 94 invocations |
| Screening | 12 tests, eight replay reports and 72 field comparisons |
| Retained decision calculations | Four tests |
| Software-report example | 20 convention comparisons |
| Full P5 review | 183 checks across 158 invocations |

Each integrated qualification therefore contains **346 new checker invocations on synthetic qualification inputs**. The four native invalid-arm CLI cases have their expected exit code and diagnostic. The qualified layers overlap; their counts describe test coverage.

The new reference-audit results and screening replay match the retained results byte for byte. Native reports preserve the same outcomes after explicitly separating variable run identifiers and timing fields. Retained study observations keep their original execution identities.

Run the complete workflow from the software root, using a new output directory:

```sh
python3 -B tools/check_candidate.py
python3 -B -m r5_f3.integration.run --out ../nsc_qualification_01
```

The result is `PASS` when the named checks, expected corpus sizes and source-inventory comparison succeed. [Integrated qualification](../r5_f3/integration/README.md) describes the output records. The accompanying data archive contains the qualification outputs in `qualification_1_0_0/`.

## Retained-data reconstruction

The independent prospective audit reads 384 retained checker reports, checks 5,568 dossier members and reconstructs the 192 reference labels. Its output matches the retained audit byte for byte. The screening comparison remains 32 versus 19 discoveries at 112 reviews per policy, with simultaneous upper count 60.

The data archive also supplies the eight exact original documents for the Study Contract bridge. Their portable replay reproduces the original 200-row/156-position trial and its three controlled alterations. The historical protocol, evaluator and receipt retain their original identities. The data README gives both replay commands and the source bindings.

## Figures

All four figures were rebuilt from their supplied data and text-layout JSON. The 18 Figure 4 certificates were recalculated. The reconstructed PNGs match the supplied previews byte for byte, and the numerical and geometric checks pass their declared tolerances.

The editable ODG set contains 861 drawing primitives, ten groups and 167 text paragraphs. Qualification applies controlled object changes to temporary ODF copies, loads and saves them through native LibreOffice Draw filters, checks persistence and then restores the drawings. This is a native headless round-trip test; the qualification record identifies the exact method and environment.

The distributed ODG files have normalised view settings. Their drawing content, styles, authorship metadata and all other ODF entries retain their original bytes. Native exports preserve the original text, vectors and pixels.

See the [figure guide](../figures/README.md), [gallery](../figures/CAPTIONS.md) and [figure qualification record](../figures/05_validation/F2_FIGURE_QUALIFICATION.json). Figure reconstruction has separate pinned dependencies from the standard-library core.

## Evidence identities

[Software provenance](../PROVENANCE.json) identifies the source baseline and packaging changes. The data manifests bind the retained records, recovered bridge inputs and current qualification outputs. Historical software labels in the supplements identify the versions used for those earlier runs; **1.0.0** identifies this standalone distribution.
