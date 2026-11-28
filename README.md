# neuroSEMANTICorr: Verification, Reference Audit and Reference Stability

**Current reproducibility collection: 1.1.0 — published 28 November 2026**

[Download collection 1.1.0 (GitHub release)](https://github.com/antonioclim/neurosemanticorr-reproducibility/releases/tag/v1.1.0) · [Zenodo record 24629640](https://zenodo.org/records/24629640) · [DOI 10.5281/zenodo.24629640](https://doi.org/10.5281/zenodo.24629640)

This collection accompanies Antonio Clim's study *Minimum adjudication and the stability of shared-error certificates*. The R6 extension examines the stability of certificates when omitted reference conventions are restored. On the archived finite frame, equally small query sets can differ in whether a threshold decision remains decisive after reference-family completion. Grouped departures and a transfer using JSON Schema validators provide additional evidence within their stated domains. The original three-dialect transfer protocol remains `NOT_MET`; exceptions and disagreements are retained.

## Start with collection 1.1.0

Download all seven named assets from the [release](https://github.com/antonioclim/neurosemanticorr-reproducibility/releases/tag/v1.1.0) or [Zenodo](https://zenodo.org/records/24629640) into one directory:

- `neurosemanticorr-software-1.0.0.zip` — unchanged baseline software
- `neurosemanticorr-data-1.0.0.zip` — unchanged baseline data and retained evidence
- [`JSS_Research_Extension_R6.zip`](https://github.com/antonioclim/neurosemanticorr-reproducibility/releases/download/v1.1.0/JSS_Research_Extension_R6.zip) — R6 implementation, inputs, outputs and independent checks
- [`README_COLLECTION_1_1_0.md`](https://github.com/antonioclim/neurosemanticorr-reproducibility/releases/download/v1.1.0/README_COLLECTION_1_1_0.md) — collection instructions
- `LICENSING_COLLECTION_1_1_0.md`
- `COLLECTION_FILES_SHA256.json`
- `VERIFY_COLLECTION.py`

Run `python3 -B VERIFY_COLLECTION.py` to check the collection inventory and integrity. Extract each scientific ZIP into its own new working location. For the extension, read `nsc_r6_research/README_EN_GB.md` and follow its instructions and external output paths.

**Important:** the source tree at tags `v1.0.0` and `v1.1.0` is the original baseline; the complete 1.1.0 collection is the seven named release assets, not GitHub's automatic source archives. This landing-page update on `main` does not alter either tag or any release asset. Because this README differs from the sealed baseline, run the baseline closed-inventory checker in an extracted, unchanged `neurosemanticorr-software-1.0.0.zip` directory (or the exact baseline tag), not in the current `main` checkout. The historical citation and metadata files in the baseline describe version 1.0.0.

## Cite the collection

Clim, A. (2026). *neuroSEMANTICorr: Verification, Reference Audit and Reference Stability* (Version 1.1.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.24629640

The baseline version DOI is [10.5281/zenodo.24509721](https://doi.org/10.5281/zenodo.24509721); the concept DOI is [10.5281/zenodo.24509720](https://doi.org/10.5281/zenodo.24509720). Cite the version actually used. Project code uses MIT; project documentation, figures and synthetic data use CC BY 4.0. Third-party licences and attribution remain intact.

---

## Historical baseline documentation (1.0.0)

The following documentation describes the original software distribution, not the R6 extension. Repository-relative links point to its retained source files.

**Version 1.0.0**

neuroSEMANTICorr audits agreement between workflow verifiers against an explicit reference model. It provides exact finite-model sensitivity analysis, controlled transformations of documentary evidence, native P4/P5 checker adapters and finite-population screening calculations.

The software accompanies Antonio Clim's study *When survey workflow verifiers agree and both are wrong*. This distribution contains executable software, examples and retained computational evidence.

Read the [study documentation](docs/README.md), browse the [figure gallery](figures/CAPTIONS.md) or inspect the [retained evidence guide](docs/REPRODUCIBILITY.md). The software and data archives share distribution version **1.0.0**. The [qualification record](docs/QUALIFICATION_1_0_0.md) describes the executed checks and retained-data reconstruction.

### Start

Use **CPython 3.12 on Linux**. The scientific baseline was qualified with CPython 3.12.14. The core verification and analysis procedures use the Python standard library and the packaged inputs, with no package installation, service account or network access. Optional figure reconstruction has its own [dependencies and instructions](figures/README.md#rebuild-in-a-working-copy).

From the directory containing `p5`, `phase2` and `r5_f3`:

```sh
python3 -B tools/check_candidate.py
python3 -B -m r5_f3.integration.run --out ../nsc_verification_01
```

Choose a new output directory outside this software directory. The first command verifies its closed inventory. The second runs the complete qualification workflow and writes commands, raw output, return codes, source identities and a final `SUMMARY.json`. A successful run has `"status": "PASS"`. Failures retain their diagnostic evidence.

The `-B` flag prevents bytecode files from changing the sealed inventory. The included `.gitattributes` preserves raw file bytes during checkout. Native Windows has not been qualified; archive preparation in Windows does not require executing the software.

### Components

| Component | Operation | Guide |
| --- | --- | --- |
| Reference audit | Exact lower and upper shared-error bounds, independently checked certificates, sensitivity radii and restricted canonical query minima | [Reference audit](r5_f3/reference_audit/README.md) |
| O15 diagnostics | Five documentary conventions, eight controlled transformations and native P4/P5 subprocess adapters | [O15 diagnostics](r5_f3/o15_diagnostics/README.md) |
| Screening | Budgeted review plans, exact finite-population upper bounds and retained-design replay | [Screening](r5_f3/screening/README.md) |
| Integrated qualification | Complete workflow with source inventories before and after execution | [Qualification](r5_f3/integration/README.md) |
| P5 checkers | Two implementations of a fixed finite consistency profile, with synthetic unit review | [P5 checkers](p5/README.md) |
| Retained reference reconstruction | Locked documentary probes and reconstruction of the 192-case frame | `phase2/` |
| Build-report example | Four constructed dossiers and 20 convention comparisons | [Example](examples/software-report/README.md) |

The reference audit distinguishes `AT_OR_BELOW`, `ABOVE`, `UNDETERMINED` and `OUT_OF_MODEL`. Input errors and execution failures have separate statuses. Scores and bounds use exact rational arithmetic.

### Reproduce individual components

Run from this software directory and choose unused output paths:

```sh
python3 -B -m r5_f3.reference_audit.qualify --out ../nsc_math_01
python3 -B -m r5_f3.o15_diagnostics native-suite --generation P4 --out ../nsc_p4_01
python3 -B -m r5_f3.o15_diagnostics native-suite --generation P5 --out ../nsc_p5_01
python3 -B -m r5_f3.o15_diagnostics.qualify_cli --out ../nsc_o15_cli_01
python3 -B -m unittest r5_f3.screening.test_screening -v
python3 -B -m r5_f3.screening.replay_archived --out ../nsc_screening_01
python3 -B -I p5/tools/review.py --mode full --out ../nsc_p5_full_01
python3 -B examples/software-report/check_build_report.py --source-dir phase2/02_source
```

See [reproducibility and scope](docs/REPRODUCIBILITY.md) for the expected checks, retained results and the optional historical bridge.

### Retained evidence

The 192-case study contains 384 original checker invocations and 32 shared errors: 16 false rejections and 16 false acceptances. Its retained screening comparison is 32 versus 19 discoveries at 112 reviews per policy, with a simultaneous upper count of 60.

The packaged replay reconstructs those observations. New checker qualifications use separately identified synthetic cases. [PROVENANCE.json](PROVENANCE.json) distinguishes the scientific source identities from the version 1.0.0 distribution, including the Markdown projection of the retained input capsule.

### Citation and rights

The software and data archives form one version 1.0.0 deposit, identified by DOI [10.5281/zenodo.24509721](https://doi.org/10.5281/zenodo.24509721). The [source repository](https://github.com/antonioclim/neurosemanticorr-reproducibility) contains the software, documentation and figures.

[CITATION.cff](CITATION.cff) records the title, author, version and DOI of the enclosing software-and-data record. Cite the exact version used and the associated study.

Code is licensed under [MIT](LICENSE); documentation, figures and synthetic data are licensed under [CC BY 4.0](LICENSES/CC-BY-4.0.txt). [Licensing and attribution](LICENSING.md) defines the component scope and the authorised terms for retained material.
