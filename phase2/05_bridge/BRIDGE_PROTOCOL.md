# Local pre-execution protocol for the retained Study Contract bridge

**23 November 2026 · local engineering demonstration · protocol frozen before bridge execution**

## Question and source

Can a standard-library reader reconstruct which original rows a retained Study Contract runtime report admits under its own documented eligibility rule? Does the reconstruction detect altered records even when a reported population has the correct length and its own updated digest?

Read the 53,468,001-byte `neuroSEMANTICorr v12.zip` with SHA-256 `6f758773b489cea9bc17fc36cd30013e24543256631eb2cb9ea53aaf64cd24c5`. Take the first retained qualification pair identified in Phase 1, `M05E-EQUIV:C24:Q0941`. Within `neuroSEMANTICorr v12/01_CURRENT_M06DR/04_CURRENT_EVIDENCE/SUCCESSOR_CHAIN/M05E_Q0941_RAW/PAIRS/001_C24_Q0941/CANDIDATE/`, use `DATA_MANIFEST.json` and the following files under `DATA/`:

- `data.json`, original ordered row records
- `pair_admission/contract.json`, declared identifier and eligible states
- `pair_admission/states.csv`, ordered response-state rows
- `pair_admission/alignment.json`, archived co-export receipt and ordered row tokens
- `pair_admission/admission/study_contract_validation.json`, runtime report to check
- `pair_binding.json` and `RESULT.json`, downstream comparison records

C24/Q0941 is an archived synthetic engineering qualification, not a new dataset. The runtime advertises 200 input rows and 156 members of P. These numbers are discovery observations to check, not independently estimated quantities. The runtime report, downstream binding and alignment evidence share producer lineage.

## Rules fixed before execution

1. Reject a different archive hash, duplicated archive names or mismatched document bytes against the documented retained data manifest. Parse JSON with duplicate keys rejected and parse CSV as strings in archive order.
2. Independently reconstruct the documented canonical digest (UTF-8 JSON, keys sorted, Unicode retained, no spaces in separators, nonfinite numbers inadmissible). Check the report's frame hashes and seal against contract, data and state receipts. Reconstruct the ordered row tokens from the declared integer `id` and check their uniqueness, order, and canonical binding to the alignment receipt. The selected archive exposes a positional sidecar and the receipt explicitly denies producer authentication and initial pairing verification.
3. Independently reconstruct P by scanning all 200 CSV rows in order. A position is included if every required variable has an allowed state in the corresponding row. This contract lists V00 through V09 and permits only `observed` for each. Check position bounds, uniqueness, order, row count, exact membership and canonical positions digest against the runtime. Check `/population_row_positions`, `/retained_source_positions`, `/excluded_by_population` and `/retained` in the retained downstream files for the current pair and exact state scope. Report source paths and document digests, without exporting rows or their individual identifiers.
4. Interpret the result solely as reconstruction of the retained contract and bytes. A match creates an inspectable association between population eligibility and documented positions. It does not certify the initial data–state pairing, authenticate a producer, run the archived producer, measure scientific validity or execute any P4/P5 obligation. The bridge uses a different document shape from the new O15 decision evaluator.

## Predeclared test outcomes

| Trial | Construction in memory | Expected detection |
| --- | --- | --- |
| Original | Exact retained records | No diagnostic. Input and selected row counts match 200 and 156, respectively. |
| Position substitution | Replace the smallest selected position with the smallest excluded position and sort. Update the runtime's own canonical position hash. | Membership mismatch despite the correct position count, unique ordered positions and matching runtime position hash. |
| Row-identifier replacement | Replace the first data identifier with a fresh integer one greater than the largest original identifier. Preserve row count and the same states. | Ordered identity-token mismatch and data-frame digest/seal mismatch. |
| Reported length change | Increase only `analytic_populations.P.row_count` by one. | Population count mismatch with unchanged positions and positions digest. |

Unexpected diagnostics are preserved in the receipt. Archival files are opened only for reading. Deliberate alterations are temporary Python copies and do not modify the retained evidence or become new archive members.
