# O15 documentary diagnostics and native P4/P5 adapters

This component implements the O15 diagnostic extension developed for R5 Phase 3. It reports what a declared transformation changes, the conditions under which that transformation is admissible and the reference verdict before and after the change. It does not implement or validate a CMOP screening policy, causal explanation or a new prospective estimator.

The documentary evaluator has its own identity, `R5-F3-O15-REFERENCE-1`. Native execution is a separate path: the actual, unchanged `T_FULL` and `B_ASSERT` Python entry points receive complete new F3 evidence bundles, the matching frozen profile, new case and invocation identities and a fresh output path. The producer itself is not executed; retained producer/runtime anchors remain synthetic documentary evidence.

## Qualification corpus

Each native branch constructs 21 transformation pairs, two original controls and three deliberately invalid controls. Both arms run on every case.

| Check | P4 | P5 |
| --- | ---: | ---: |
| Actual subprocess invocations | 94 | 94 |
| Valid reports with O01–O16 labels and aggregate | 92 | 92 |
| Specified invalid-arm exits without a semantic report | 2 | 2 |
| Required invocation expectations | 94/94 | 94/94 |
| Documentary before/after pairs under five conventions | 21/21 | 21/21 |
| Required complete-vector invariance comparisons | 12/12 | 12/12 |
| Permitted changes outside O15 in transformed pairs | 0 | 0 |

The 12 complete-vector comparisons per branch cover T01, T02 and T08 across W1 and W2, for both arms. P4's positive T02 cases declare `literal_only` and `either_unique`; P5's declare `suffix_only` and `either_unique`. Other transformations remain contrasts, convention-conditioned changes or repairs.

The component also supplies 23 unit tests, eight CLI checks and a documentary regression comprising ten locked probes plus 192 retained dossiers (1,010 convention comparisons). Documentary regression invokes no original checker. Malformed inputs, stale custody, profile tampering and process faults have explicit negative-test expectations.

The F3 checkpoint retains the original qualification runs, their superseded attempts and their evidence. They are also carried in the historical data kit's `native_o15/native_o15_retained.tar.xz`. This source package omits those duplicate output trees. A fresh run writes its own complete receipts into the requested external output directory. Earlier and current executions must not be pooled as independent observations.

## Reference and failure semantics

The five documentary conventions are `literal_only`, `suffix_only`, `either_unique`, `prefer_literal` and `prefer_suffix`. The reference checks claim and result identities, unique claim identifiers, exact typed values, RFC6901 escape order, canonical ASCII array indices and equality of unit, denominator and scope. A padded object key remains an object key. Integer and rational values are compared exactly; booleans are distinct from integers.

Missing documentary evidence can give U. An explicit semantic contradiction in admitted documentary JSON can give V. Duplicate JSON keys, invalid UTF-8, non-object records and inexact JSON numbers give `INPUT_ERROR` with no semantic label. Operator-domain failures give `PRECONDITION_FAILED`, no transformed dossier and no asserted relation. Unexpected exceptions and process failures remain `EXECUTION_ERROR`; none is converted to V.

Native admission has its own semantics. In the duplicate-key negative control, the actual checkers report O01=V and O15=U. The documentary parser rejects the same ambiguous JSON without assigning O15. These outcomes are deliberately not treated as equivalent execution paths. In the stale-inventory control, the expected native O02=V is recorded separately, while T01 refuses the transformation before an invariance claim can be made.

The strict integer/rational parser applies to evidence and configuration. Reports use ordinary JSON and include measured floating-point durations.

## Operator domains

| Operator | Preconditions and interpretation |
|---|---|
| T01 | Unique JSON keys, explicit object-order independence and current custody. Reorders object members, preserves logical JSON and recommits complete native bundles. |
| T02 | Explicit convention list, injective alias renaming without collisions, coherent claim/key changes, unchanged single-hop targets and metadata. Invariance is asserted only for the named conventions. |
| T03 | Full-token qualification plus declared lexical min/max target selection. Conflicting targets are semantic contrasts. Preservation mode additionally requires one distinct target and compatibility with every declared convention. |
| T04 | Converts used mappings to bare keys without distinct-target collisions. Reports all five before/after references; a legitimate convention-dependent flip is retained. |
| T05 | Finite, acyclic, unambiguous alias-chain repair with a declared depth bound and existing final target metadata. Multi-hop invariance is unsupported under the frozen single-hop profile. |
| T06 | An explicit claim and direct pointer probe. Native qualification covers padded and out-of-range array indices; the broader escape, Unicode, huge-index and padded-object cases are documentary tests. |
| T07 | Original satisfaction under an explicit convention, a different existing target, exactly equal value and different valid metadata. This is a metadata contrast. |
| T08 | Exact frozen P4/P5 profile, the declared Appendix A row-local eligibility model, bijective co-permutation of data/state/output rows, correct stable-ID maps and order-independent `/values/` claim targets. It makes no initial-pairing or producer-authentication claim. |

Complete-bundle transformations verify the input inventory and canonical semantic commitment, then recalculate raw-byte inventories and the commitment for the new bundle. Inventory comparison preserves JSON types, so a boolean cannot impersonate an integer byte count. Frozen profile content is pinned by its canonical hash. Alias chains are not silently admitted as a sixth reference convention.

## Native sources and interpretation

P5 uses the retained repository files in `p5/checkers` and `p5/profiles`. P4 uses four exact extracted files under `native_sources/P4`: the two checkers, fixed profile and frozen arms manifest. `PROVENANCE.json` gives their archive member paths and byte hashes. The source archive hash is:

`01d39c2da1515e5870d6e356ac24000e89fbe0d4fad77188bd83dc2a6b31625a`

The complete historical ZIP is unnecessary for a rerun. Historical absolute paths inside the byte-preserved frozen manifest are archival text; execution uses component-relative locations. Both source branches and profiles are hash-checked before execution. Every invocation records its real command, exit code, raw stdout/stderr, input binding, profile/checker hashes, full native report and whether inputs and instruments stayed unchanged.

P5's native alias grammar is exact nonempty suffix lookup with one hop. P4's full-token lookup corresponds to the `literal_only` known answers on this particular corpus. This is not a universal equivalence claim: the historical parsers and the documentary evaluator need not agree on every malformed or unusual pointer token.

`NATIVE_RELATIONS.json` retains both complete vectors, aggregates and all changed obligations. `SHARED_REFERENCE_DISAGREEMENTS.json` compares native agreement with each named documentary convention. For example, the fresh P4 full-token-correct conflict cases produce native S/S while `either_unique` gives V; `literal_only` gives S. The reverse conflict orientation exposes the analogous suffix-dependent agreement under P5. Agreement alone selects no reference convention and establishes no field error rate.

All native dossiers are new synthetic F3 fixtures. No historical dossier, oracle, report, checker or profile is overwritten. The historical FAIL_CLOSED outcomes 771/772 remain outside this new qualification and remain unchanged. No new statistical coverage, external validity, causal effect or prospective panel result is claimed.

## Reproduce from the software repository

Use CPython 3.12 on Linux and run these commands from the repository directory containing `p5`, `phase2` and `r5_f3`. The qualified patch version is 3.12.14. The component uses the Python standard library. Unit-test temporary files use `NSC_O15_TEST_TMP` when set, or the system temporary directory; they are not written into the component. Use new output directories and filenames; existing outputs are never overwritten.

```bash
python3 -B -m unittest r5_f3.o15_diagnostics.test_diagnostics -v
python3 -B -m r5_f3.o15_diagnostics.qualify_cli --out ../o15_cli_rerun
python3 -B -m r5_f3.o15_diagnostics native-suite --generation P4 --out ../o15_native_p4_rerun
python3 -B -m r5_f3.o15_diagnostics native-suite --generation P5 --out ../o15_native_p5_rerun
python3 -B -m r5_f3.o15_diagnostics regression --output ../o15_regression_10.json
```

The last command checks the ten repository probes without an external archive. To repeat the complete 202-dossier documentary regression, append `--archive /path/to/extracted/NSC_PROS_v1`. This argument is read-only and must contain exactly the 192 retained dossier paths. It is not required for either native branch.

A direct example and an explicitly labelled repair are:

```bash
python3 -B -m r5_f3.o15_diagnostics reference --input r5_f3/o15_diagnostics/examples/dockets/conflicting_alias --case-id F3-EXAMPLE-CONFLICT --output ../o15_reference.json
python3 -B -m r5_f3.o15_diagnostics transform --input r5_f3/o15_diagnostics/examples/dockets/chain --case-id F3-EXAMPLE-CHAIN --operator T05 --parameters r5_f3/o15_diagnostics/examples/parameters/T05_repair.json --output-dir ../o15_repaired_dossier --output ../o15_repair_report.json
```

For a complete native input, `transform` also requires `--profile` pointing to the matching frozen profile. Its result is a prepared evidence bundle and documentary report; this command does not itself invoke a checker. `native-suite` performs the actual subprocess executions with the unchanged checkers. Run IDs, timestamps and durations vary on rerun; the predeclared verdict vectors and relation checks are the reproducibility targets.
