# Reference-model audit

`reference_audit` computes exact sensitivity results for a declared finite family of reference conventions. It reports the smallest and largest weighted shared-error score compatible with local admissibility, fixed observations, protected coordinates and a shared exception budget. Every finite endpoint and first-region radius has a complete label assignment that can be checked independently.

This is the R5/F3 research implementation. The component does not invoke either original checker or create new prospective experimental results.

## Run the component

Use CPython 3.12 on Linux; the qualified patch version is 3.12.14. The component has a declared Python 3.10 language baseline, while qualification records the interpreter actually executed. It uses the standard library. Run these commands from the software repository directory, which contains `r5_f3/`:

```bash
python3 -B -m r5_f3.reference_audit audit r5_f3/reference_audit/examples/single_conflict_V_broad_k1.json
python3 -B -m r5_f3.reference_audit q-min r5_f3/reference_audit/examples/canonical_broad_k8.json
python3 -B -m unittest discover -s r5_f3/reference_audit/tests -t . -v
python3 -B -m r5_f3.reference_audit.qualify --out ../reference-audit-run-01
```

The first command returns `UNDETERMINED` with the exact envelope `[1,49]`. The second returns the 33 canonical case identifiers required at budget eight, together with the constructive necessity certificate. The qualification command runs the tests, verifies every packaged example, executes the retained phase2 documentary evaluator and writes reproducible evidence to the requested new directory. `--out` is required; an existing path or a path inside the component is refused. A later run must use a new output directory. Temporary test files are confined to that output and removed afterwards. The source component and the retained qualification are not overwritten. Direct unittest execution uses the operating system's temporary directory unless `NSC_REFERENCE_AUDIT_TEST_TMP` selects another existing directory.

To save and verify a report:

```bash
python3 -B -m r5_f3.reference_audit audit r5_f3/reference_audit/examples/weighted_protected_third_outcome.json > ../reference-audit-report.json
python3 -B -m r5_f3.reference_audit verify r5_f3/reference_audit/examples/weighted_protected_third_outcome.json ../reference-audit-report.json
```

`audit`, `q-min` and `digest` accept `-` in place of the input filename to read standard input. The CLI writes one JSON result to standard output. It never overwrites its inputs. The commands above use `-B` to avoid Python bytecode files; this flag does not change the mathematics.

## Mathematical domain

A case is one local reference outcome. Its identifier, context, paired checker labels, admissible reference labels, weight and exception eligibility are explicit. The label alphabet is `S`, `V`, `U`. An observed `U` is an outcome; the absence of an observation is represented by omitting the observation record.

A convention supplies one predicted label for every case in the declared domain. A joint centre selects one versioned convention at each case. The scope controls that selection:

| Scope | Required property of each supplied centre |
| --- | --- |
| `global` | One convention is used throughout the whole declared domain. |
| `contextwise` | One convention is used within each context; different contexts may use different conventions. |
| `casewise` | A convention may be selected separately at each case. |

All three scopes use **only the explicit list of joint centres supplied in the request**. Validation does not certify that a caller has enumerated the full product. Reports therefore set `complete_cartesian_product_certified` to `false`, even when a separate construction has deliberately supplied every centre. The contextwise and casewise toy examples are declared subsets.

For a centre `g`, a completion `y` must satisfy every admissibility set and every fixed observation. A protected case, with `exception_eligible: false`, must retain `g`'s predicted label. Every eligible case at which `y` differs from `g` spends one unit from the **shared total budget**. Cost is counted per local outcome, including eligible external queries. It is not counted per family, causal mechanism, context or adjudicator. The implementation has no per-context budget mode.

Only frame cases contribute to the score. A frame case contributes its nonnegative weight when the two checker labels are identical and that common label differs from the reference completion. Disagreement between the checkers contributes zero to this particular shared-error score. An external query has weight zero; it may still consume exception budget or rule out a centre. The model does not describe erroneous adjudication labels: supplied observations remain fixed.

The mathematical family grows as the budget increases while the same observations, centres and constraints are held fixed. A unanimous decision can become undetermined when an opposite completion becomes feasible. It cannot jump directly to the opposite unanimous decision, because the previous assignments remain feasible.

## Request contract

`request.schema.json` documents the JSON shape. `model.py` performs the authoritative runtime validation, including cross-field identity, coverage and hash checks that JSON Schema cannot establish. The runtime does not import a schema-validation library. Unknown fields and missing fields are errors; all identifiers and observations must be unique in their respective domains.

The required top-level fields are:

| Field | Meaning |
| --- | --- |
| `schema` | Exactly `nsc.reference-audit.request/1`. |
| `frame_id` | Stable identifier for the scored frame. |
| `matrix` | Explicit payload containing `cases`, versioned `conventions` and joint `centres`, plus its verified SHA-256 and canonicalisation identifier. |
| `model_scope` | `kind`, `enumeration: "explicit"` and `budget_scope: "shared_total"`. |
| `observations` | Possibly empty list of exact labels, each bound to a case and evidence record. |
| `budget` | Nonnegative JSON integer. A boolean is rejected. |
| `threshold` | Nonnegative exact rational string. The lower decision region includes equality. |

A case must include `case_id`, `context_id`, `role`, `checker_labels`, `allowed_labels`, `weight` and `exception_eligible`. At least one frame case is required. Both checker labels must be observed `S`, `V` or `U` for frame cases. For `external_query` cases, both checker labels may instead be `null`, but an incomplete pair is rejected and the weight must explicitly equal zero. Every local admissibility set must initially be nonempty and contain no duplicates.

Each convention must have `convention_id`, a nonempty `version` and predictions over exactly the complete case domain. Each centre must have `centre_id` and `convention_by_case` over the same complete domain. References to unknown conventions, duplicate joint assignments and assignments inconsistent with the declared scope are rejected. Different convention assignments may legitimately predict the same vector.

An observation has `case_id`, `label` and `evidence`. Its evidence record contains a unique `evidence_id`, canonicalisation, SHA-256 and a payload with exactly `case_id`, `label` and a nonempty `basis`. The evidence payload must bind the same case and label as the observation. Its digest is recalculated from the supplied payload. The basis may describe an adjudication or identify its source. These checks establish the identity of the supplied evidence record; they do not authenticate an external source or establish the truth or independence of an adjudication. The packaged query branches are explicitly stipulated or retained transcripts.

Duplicate observations are input errors even if their labels agree. One well-formed observation outside its case's declared admissibility set instead yields a valid empty reference family and `OUT_OF_MODEL`. A protected-coordinate conflict or mandatory departures exceeding the budget can also produce `OUT_OF_MODEL`.

### Exact rational values

Weights and the threshold are strings such as `"0"`, `"2"`, `"1/2"` or `"9007199254740993/7"`. Negative values, decimal notation, whitespace, zero denominators and JSON floating-point values are rejected. Input fractions need not be reduced. Output fractions are reduced and an integer denominator is omitted. Arithmetic uses `fractions.Fraction` throughout; no floating-point tolerance is used.

### Canonical payload identity

The canonicalisation identifier is `nsc-json-utf8-sort-keys-v1`. The admitted JSON domain consists of objects with string keys, arrays, strings, integers, booleans and null. Duplicate keys, floating-point numbers and non-finite numbers are rejected on loading.

Canonical bytes are precisely the UTF-8 encoding of Python's:

```python
json.dumps(value, sort_keys=True, ensure_ascii=False,
           separators=(",", ":"), allow_nan=False)
```

Object keys are sorted, array order is retained, Unicode is not normalised and there is no trailing newline. Strings must be UTF-8 encodable. SHA-256 is taken over those bytes. `matrix.sha256` commits to the actual `matrix.payload`; each evidence SHA commits to its actual evidence payload. The computed `request_sha256` commits to the entire request, including observations, budget and threshold. The general audit accepts this explicit payload commitment; it does not infer that an arbitrary caller's payload came from a particular external CSV.

The canonical query calculation has an additional restriction: it verifies the packaged CSV's raw SHA-256 and checks the request against the corresponding 192-case geometry, metadata, conventions and predictions. `inputs/SOURCE_IDENTITIES.json` records the raw identities and documentary origins of the packaged retained inputs. No runtime path points to an external phase directory.

## Results and certificates

The four semantic statuses are:

| Status | Exact meaning |
| --- | --- |
| `AT_OR_BELOW` | Every feasible completion has score at or below the threshold. |
| `ABOVE` | Every feasible completion has score strictly above the threshold. |
| `UNDETERMINED` | At least one feasible completion exists on each side. |
| `OUT_OF_MODEL` | No completion satisfies the supplied constraints at the requested budget. |

An interval is an exact endpoint envelope. It does not assert that every interior score is attainable. The report identifies feasible centres, mandatory departure case IDs, centre-specific bounds and incompatibilities. A `null` minimum required budget means that a centre cannot be made feasible at any budget while its local and protected constraints remain fixed.

Endpoint certificates provide all case labels, the supporting centre, the exact score, changed case IDs, distance and the **request's budget**. `verify_witness` checks both feasibility and sharpness at that budget; an internally consistent witness at a larger budget is rejected as an endpoint of the original request.

The report also computes the first budget permitting any completion at or below the threshold and the first budget permitting any completion above it. Their certificates are allowed to use a budget different from the request budget, but only the first feasible budget of their stated region. `verify_witness` returns `certificate_domain: "first_region_budget"` for these and `"requested_budget_endpoint"` for endpoint certificates. `null` encodes an unattainable region. `first_opposite_completion` is relative to the current request's unanimous decision; it is undefined when the current result is `UNDETERMINED` or `OUT_OF_MODEL`.

These radii are model-sensitivity results. They do not estimate label-error probabilities or provide sampling confidence bounds. External queries remain outside the scored frame, and zero weight never means that an eligible departure is free of budget cost.

The optimiser computes mandatory departures and sorts useful optional score changes. `verification.py` uses a separate exact-cost dynamic programme and directly validates every witness. It does not call the optimiser or its profile and gain helpers. Reports bind the request, matrix and installed runtime source hashes. A verifier rejects reports from a different runtime identity; retain the matching software version alongside a report. Hashes establish identity and accidental or deliberate alteration can be detected, but they are not signatures.

## Canonical fixed-query minimum

`q-min` implements only the verified 192-case O15 problem with the five specified versioned global centres, unit weights, all coordinates eligible, no prior observations, threshold 24 and budgets zero through eight. Admissibility must be uniformly either the local union of the five predictions or the full `S,V,U` alphabet. No other geometry is extrapolated.

For budgets zero through seven, it returns `2k+1` distinct `dual_alias_conflict` cases. The certificate records all cross-region distances and the closest opposing pair. At budget eight, it returns every one of the 32 `suffix_alias_clean` and `dual_alias_conflict` cases plus one `exact_alias_clean` case. Each of the 32 necessary cases has a constructive pair of opposite-side completions differing only at that case. The extra case separates the remaining 24-versus-40 obstruction. Compatibility with the declared family must be checked before the threshold-specific sufficiency rule is applied, including when `U` is observed.

This result concerns a fixed set of exact local adjudications and a shared budget of local departures. It is not an adaptive cost, a claim about human effort or a general query optimiser. A valid request outside the verified domain receives `NOT_APPLICABLE` with a null minimum and explicit reasons. Its metadata preserves the actual request threshold and budget.

## Python API

```python
from r5_f3.reference_audit import audit, verify_report, verify_witness
from r5_f3.reference_audit.canonical import load_file

request = load_file("r5_f3/reference_audit/examples/canonical_broad_k8.json")
report = audit(request)
receipt = verify_report(request, report)
witness_receipt = verify_witness(request, report["endpoint_certificates"]["upper"])
```

`validate_request` exposes the validated model representation. `canonical_query_minimum` exposes the canonical query certificate. The public functions do not mutate the supplied request or report.

| CLI exit code | Meaning |
| --- | --- |
| `0` | A valid calculation, including `OUT_OF_MODEL` or canonical `NOT_APPLICABLE`. |
| `2` | `INPUT_ERROR`, or a conventional command-line usage error. |
| `3` | `VERIFICATION_FAILED`; a report or witness claim fails verification. |
| `4` | `EXECUTION_ERROR`; a runtime failure is not recoded as a reference label or semantic verdict. |

## Verification evidence and limits

The test suite covers malformed identities and hashes, exact arithmetic, mandatory changes, protected cases, zero-weight external probes, observed `U`, checker disagreement, finite model unions, nesting and all original phase2 transcripts. Exhaustive binary two-coordinate configurations vary the centre, common checker labels, nonempty admissibility sets, eligibility masks, rational/zero weights and budgets. A raw assignment enumerator serves as an oracle independent of both computational methods. Adversarial tests change certificate budgets, labels, distances and scores together, and rehash deliberately altered reports.

`regression_phase2.py` executes exact local copies of the retained documentary evaluator on the ten original probe dockets and compares all original transcripts at budget zero. This is a regression of that evaluator, not a new run of `T_FULL` or `B_ASSERT`.

`integration_scope_comparison.py` reproduces the real frame's global and contextwise scope comparison after the canonical S/V conflict query. It supplies all 625 contextwise joint centres to the engine and independently enumerates their scores at budget zero. The complete casewise product is calculated by a separate coordinate-extrema comparator; the engine is not claimed to have materialised or run on `5**192` centres.

In the selected output directory, `RESULT.json` records the executed checks and limitations. `COMMAND_LOG.json` records the actual invocation, working directory and generated operations; `FILE_MANIFEST.json` binds the component files and generated evidence in separately named sections. Example reports and their independent verification receipts are in `example_reports/`. The accompanying data archive supplies retained mathematical qualification records in `reference_analysis/f3/qualification/` and integrated-run records in `f3_qualification/`. Historical locators in those records identify their original executions.

Results establish correctness for the declared finite models and tested contracts. They do not establish external adjudication truth, undocumented model completeness, generic optimal query selection or new native-checker performance.
