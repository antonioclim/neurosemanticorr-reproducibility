# neuroSEMANTICorr: Verification and Reference Audit

**Version 1.0.0**

neuroSEMANTICorr audits agreement between workflow verifiers against an explicit reference model. It provides exact finite-model sensitivity analysis, controlled transformations of documentary evidence, native P4/P5 checker adapters and finite-population screening calculations.

The software accompanies Antonio Clim's study *When survey workflow verifiers agree and both are wrong*. This distribution contains executable software, examples and retained computational evidence.

Read the [study documentation](docs/README.md), browse the [figure gallery](figures/CAPTIONS.md) or inspect the [retained evidence guide](docs/REPRODUCIBILITY.md). The software and data archives share distribution version **1.0.0**. The [qualification record](docs/QUALIFICATION_1_0_0.md) describes the executed checks and retained-data reconstruction.

## Start

Use **CPython 3.12 on Linux**. The scientific baseline was qualified with CPython 3.12.14. The core verification and analysis procedures use the Python standard library and the packaged inputs, with no package installation, service account or network access. Optional figure reconstruction has its own [dependencies and instructions](figures/README.md#rebuild-in-a-working-copy).

From the directory containing `p5`, `phase2` and `r5_f3`:

```sh
python3 -B tools/check_candidate.py
python3 -B -m r5_f3.integration.run --out ../nsc_verification_01
```

Choose a new output directory outside this software directory. The first command verifies its closed inventory. The second runs the complete qualification workflow and writes commands, raw output, return codes, source identities and a final `SUMMARY.json`. A successful run has `"status": "PASS"`. Failures retain their diagnostic evidence.

The `-B` flag prevents bytecode files from changing the sealed inventory. The included `.gitattributes` preserves raw file bytes during checkout. Native Windows has not been qualified; archive preparation in Windows does not require executing the software.

## Components

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

## Reproduce individual components

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

## Retained evidence

The 192-case study contains 384 original checker invocations and 32 shared errors: 16 false rejections and 16 false acceptances. Its retained screening comparison is 32 versus 19 discoveries at 112 reviews per policy, with a simultaneous upper count of 60.

The packaged replay reconstructs those observations. New checker qualifications use separately identified synthetic cases. [PROVENANCE.json](PROVENANCE.json) distinguishes the scientific source identities from the version 1.0.0 distribution, including the Markdown projection of the retained input capsule.

## Citation and rights

The software and data archives form one version 1.0.0 deposit, identified by DOI [10.5281/zenodo.24509721](https://doi.org/10.5281/zenodo.24509721). The [source repository](https://github.com/antonioclim/neurosemanticorr-reproducibility) contains the software, documentation and figures.

[CITATION.cff](CITATION.cff) records the title, author, version and DOI of the enclosing software-and-data record. Cite the exact version used and the associated study.

Code is licensed under [MIT](LICENSE); documentation, figures and synthetic data are licensed under [CC BY 4.0](LICENSES/CC-BY-4.0.txt). [Licensing and attribution](LICENSING.md) defines the component scope and the authorised terms for retained material.
