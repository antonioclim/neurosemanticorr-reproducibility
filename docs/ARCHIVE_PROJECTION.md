# Retained archive projection

## Distribution and source identities

The version 1.0.0 software supplies this input capsule:

```text
r5_f3/integration/inputs/neurosemanticorr_prospective_evidence_1.0.0.tar.xz
```

Its SHA-256 is:

```text
55dc0a8bfd7a9aec272bf259b81b15a57e9fc41be9f3b38b75d3e1b20c0054d1
```

The original archive from which it was derived has SHA-256:

```text
c2ecc59137d0f7f9912fac73486f5ddc03ffdbdeca27d4e0f71b5fb586222767
```

The original hash continues to identify the source of the historical screening records in `r5_f3/screening/inputs/INPUT_LOCK.json`. The integration runner verifies the hash of the current capsule. [PROVENANCE.json](../PROVENANCE.json) records both identities.

## Content preservation

The original capsule contains 7,141 files. The distribution capsule contains 7,139 files: 7,136 retain identical bytes, while its navigation document, Markdown research-report packaging and current manifest are revised.

All members under `00_plan/`, `dockets/`, `evaluation/`, `execution/`, `frame_design/`, `implementation_receipt/` and `reference/` remain byte-identical. This preserves the pre-execution commitment, original source and input identities, 192 dossiers, 384 original invocations, policy selections and numerical results.

The printed research report is represented by its matching Markdown source, preserving the prose and both tables. Its editorial insertion reference and the separate manuscript insertion are outside this distribution. The current capsule manifest describes the supplied files and retains the original archive and manifest hashes.

## Reproduction

The capsule extracts under `NSC_PROS_v1/`. The integrated workflow uses that directory to reconstruct retained reference results. Its procedures and expected outputs are described in [the qualification guide](../r5_f3/integration/README.md).

Historical run labels and locks describe their original observations. The version 1.0.0 inventory describes the present software distribution. Their roles remain separate.
