# Documentation

This documentation accompanies **neuroSEMANTICorr 1.0.0**, the reproducibility distribution for *When survey workflow verifiers agree and both are wrong*.

## Read the study evidence

| Document | What it establishes |
| --- | --- |
| [Prospective study evidence](supplements/prospective_evidence.md) | The original 192-dossier frame, review allocations, observed errors and finite-population bound. |
| [Historical profile and qualification](supplements/historical_profile.md) | The verification profile, numerical rules, historical P4 outcomes and separate P5 qualification. |
| [Reference audit and diagnostic qualification](supplements/reference_audit.md) | Reference conventions, exact sensitivity analysis, controlled diagnostic transformations and retained-design replay. |
| [Archive projection](ARCHIVE_PROJECTION.md) | The relationship between the retained prospective archive and its distributed projection. |
| [Figures](../figures/README.md) | Captions, browser previews, editable drawing files and the underlying figure data. |

## Distribution and qualification identities

The distribution version is **1.0.0**. The supplements retain the identities of the historical experiments and qualifications they document. In particular, the software qualification described in Supplement T refers to source package **5.0.0-local.3** and its component versions. The current [software provenance](../PROVENANCE.json) records the relationship to that baseline. Renumbering the distribution does not create a new experiment or alter an earlier result.

The prospective study, reference analysis, P5 qualification and later native diagnostic checks have separate populations and execution identities. Their counts are reported in the corresponding supplement.

## Find an evidence record

The evidence indexes use the historical P, S and T identifiers and retain their source hashes:

- [Prospective evidence index](evidence/SUPPLEMENT_P_EVIDENCE_INDEX.json)
- [Historical source index](evidence/SUPPLEMENT_S_SOURCE_INDEX.json)
- [Reference-audit evidence index](evidence/SUPPLEMENT_T_EVIDENCE_INDEX.json)

Copies of the principal records are in `supplement_sources/source_evidence/` within the separately distributed data archive. Paths written inside the indexes retain the source-package convention; paths labelled as data-package locations are interpreted relative to that archive. These historical locators do not rename the files in the current software tree.

For execution, start with the [software guide](../README.md). For retained inputs, outputs and capsule extraction, use the README supplied with the data archive. Read the [rights notices](../RIGHTS_NOTICES.md) for the distribution terms.
