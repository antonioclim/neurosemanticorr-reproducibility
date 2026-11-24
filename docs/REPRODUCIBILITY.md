# Reproducibility and scope

## Runtime and evidence

The retained scientific baseline was qualified on Linux with CPython 3.12.14. The core qualification pipeline uses Python's standard library. Optional [figure reconstruction](../figures/README.md#rebuild-in-a-working-copy) has separate dependencies. Native execution relies on POSIX process groups and file flags; native Windows is outside that qualification.

Every complete run writes its own environment, commands, source hashes, input identities, return codes and raw streams. Output paths must be new and outside the software directory. Timings and run identifiers can vary; declared outcomes, exact values and source/input identities provide the comparison targets.

## Complete qualification

The integrated workflow expects the following checks:

| Layer | Expected scope |
| --- | --- |
| Reference audit | 27 test methods and 17 examples with verified certificates |
| O15 unit and CLI | 23 unit tests and eight CLI checks |
| Documentary regression | 202 dossiers and 1,010 convention comparisons |
| Native P4 diagnostics | 94 invocations |
| Native P5 diagnostics | 94 invocations |
| Screening | 12 unit tests and retained-design replay |
| Retained decision audit | Four unit tests and byte-identical result reconstructions |
| Build-report example | 20 convention comparisons |
| P5 full review | 183 checks across 158 invocations |

These layers overlap. They are computational checks rather than independent study observations.

## Finite-model interpretation

The reference audit evaluates the joint centres explicitly supplied by a request, with its observations, admissibility sets, protected coordinates and shared departure budget. Certificates cover that declared finite family.

The canonical query-minimum calculation is restricted to the retained 192-case frame, the five versioned global conventions, threshold 24, no prior observations, all coordinates eligible and the specified admissibility choices. For departure budgets zero through eight, its minima are **1, 3, 5, 7, 9, 11, 13, 15 and 33**. Requests outside this domain return `NOT_APPLICABLE`.

Screening confidence bounds require the declared fixed frame, sampling design and reference labels. They differ from the deterministic convention/departure bounds of the reference-audit component.

## Historical outcomes

The original 192-case study and its 384 invocations retain their input, reference and output identities. The P4 results of 98/100 conformance and 2/36 false rejections, its failed semantic gate and the earlier P1 custody result `FAIL_CLOSED 771/772` remain part of the history. Later P5 and O15 qualifications use new synthetic identities.

The input capsule in this distribution retains the scientific members byte for byte. Its current manifest describes the Markdown documentation projection; its provenance also records the original archive identity. A historical source lock describes the source from which evidence was obtained, while the current distribution inventory describes the bytes now supplied.

## Study Contract reconstruction

The accompanying data archive includes the eight original documents for one retained synthetic Study Contract record, exact source bindings and a portable replay adapter. From the root of that data archive, run:

```sh
python3 -B study_contract_bridge/replay_bridge.py
```

The adapter checks the source identities and repeats the original four protocol trials. The retained original selects 156 of 200 rows; the three controlled discrepancy trials test membership, row identity and reported length. `study_contract_bridge/SOURCE_BINDINGS.json` identifies the delivered documents, and `REPLAY_RECEIPT.json` records the portable replay separately from the historical receipt.

The original software-side reader, `phase2/05_bridge/study_contract_bridge.py`, is also retained unchanged. Its original route requires the exact `neuroSEMANTICorr v12.zip`: **53,468,001 bytes**, SHA-256:

```text
6f758773b489cea9bc17fc36cd30013e24543256631eb2cb9ea53aaf64cd24c5
```

The portable data-side route above uses the delivered source documents. To repeat the original archive-based route, the utility verifies the entire source archive and then its retained member identities:

```sh
python3 -B phase2/05_bridge/study_contract_bridge.py /path/to/neuroSEMANTICorr_v12.zip > ../nsc_bridge_reconstruction.json
```

The historical protocol and receipt retain their original identities. The bridge is a documentary consistency trial; it is separate from the native P4/P5 qualification and performs no producer authentication or initial-pairing verification.
