# Phase 2 fixture criteria

These ten fixtures isolate the O15 claim-to-source obligation. They contain the R15 claim record, the R15 edge and metadata record and the R11 result record. The missing-evidence control intentionally omits R11. The fixtures carry new case identifiers and have no P4 admission inventory. The cases do not establish end-to-end checker performance across O01–O16.

The expected labels were derived manually from the declared policies, the O15 value and metadata contract and RFC 6901 before running the Phase 2 evaluator. The fixture generator serialises those inputs and labels. It has no evaluator dependency. The out-of-model labels come from two **synthetically declared local policies** on the same bytes. They do not represent human, field or organisational adjudications.

## Alias policies

For claim token `alias:claim`, the literal key is `alias:claim` and the suffix key is `claim`. Each target must resolve as a direct pointer. The selected result value and its field metadata must match the claim, and the result identities in the edge and result records must match. A complete violation is `V`. A record missing without a demonstrated violation is `U`. A matched complete claim is `S`.

| Policy | Target selection |
| --- | --- |
| `literal_only` | Requires the literal key and selects its pointer. |
| `suffix_only` | Requires the suffix key and selects its pointer. |
| `either_unique` | Accepts either spelling if the pointers supplied define a single target string. Rejects conflicting strings. |
| `prefer_literal` | Selects the literal pointer if its key exists. Otherwise tries the suffix key. |
| `prefer_suffix` | Selects the suffix pointer if its key exists. Otherwise tries the literal key. |

A policy's fallback concerns key absence. A mismatch after lookup does not cause another lookup.

`F2-MIRROR-LITERAL` and `F2-MIRROR-SUFFIX` bind the same mapping to `/values/mean_staff` and `/values/turnover_ratio/row01`. They adapt the two quantities from archived case `R1PROS-1175F475261EE917E0E06A6A` and use a fresh synthetic result with just the two relevant values. The literal case claims 26 staff with supporting denominator 5. The mirror claims 142/205 as a ratio with supporting denominator 1. The edge and retained result records are byte-identical between the two cases. The claim identifier is constant. The claim payload changes only in its number and associated unit and denominator. The mirror separates `either_unique` with `V` from `prefer_suffix` with `S`. The literal control has `V` for both. The pair still leaves `suffix_only` and `prefer_suffix` with the same signature.

## Direct pointer controls

RFC 6901 defines the normative direct pointer syntax and evaluation. Its Section 4 specifies the escape order, exact object key matching and the grammar of an array index. The O15 contract additionally compares metadata and value. [Bryan, Zyp and Nottingham, 2013](https://doi.org/10.17487/RFC6901)

- `F2-RFC-ESCAPE-ORDER` resolves `~01` to object member `~1`, which contains 73. Reversing the escape substitutions would lead to `/`, which contains 97. Edge field metadata are provided for both paths.
- `F2-IDENTITY-CORRECT` and `F2-IDENTITY-WRONG-TARGET` share a result whose two targets both contain 73. Only the claim pointer changes. The metadata assign the targets to different cohorts, so the second pointer fails the O15 metadata criterion even though a value-only comparison agrees.
- `F2-RFC-ARRAY-INDEX` and `F2-RFC-ARRAY-PADDED` share a result with a two-element array and both potential metadata entries. `/1` selects its second value. `/01` fails RFC array index syntax before value comparison. `F2-RFC-OBJECT-PADDED` uses the same token against an object with a literal `01` member and resolves successfully.
- `F2-MISSING-RESULT` copies the valid direct array claim and its edge record while withholding R11. It establishes the `U` control for missing evidence.

## Transcript checks

`F2-CONTEXT-SUFFIX` has a different docket identifier and identical raw records to `F2-MIRROR-LITERAL`. In a controlled negative transcript, the first context's literal policy accepts the claim and the second context's suffix policy rejects it. Their labels form a valid transcript under the declared context-specific rules and a contradiction under **every** listed single global policy. The correct result is an empty compatible set. The test does not choose between the local rules or supply normative authority for one of them.

The direct-only transcript retains all five policies. The mirror's `S` transcript retains both suffix-selecting policies. These controls test the continuing ability to report an underdetermined hypothesis set after observing valid evidence.

`EXPECTED.json` states the accepted labels and the three transcripts. `FIXTURE_LOCK.json` records SHA-256 and lengths for the fixture files, the generator, expectation and design documents. Regenerating with `python3 -B 01_fixtures/build_fixtures.py` from the phase root should reproduce the test and expectation bytes. A directory without R11 is intentional in the missing-evidence case. The experiment validator can check the lock before evaluating the fixture set.
