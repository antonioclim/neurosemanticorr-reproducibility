# Screening and finite-frame sampling

This module implements a review plan whose flags are declared independently of
adjudicated labels. It reviews every flagged case, then fills the available slots
from a supplied whole-frame permutation. All frame members must be comparable
agreements between the two checkers. A case is one review unit.

The retained design is replayed from its original permutation, selection lists
and adjudications. This replay produces no new sample or checker outcome.

## Run

Use CPython 3.12 on Linux, from the repository root. The component uses the standard library:

```sh
python3 -B r5_f3/screening/test_screening.py
python3 -B r5_f3/screening/replay_archived.py --out ../fresh_screening_replay
python3 -B r5_f3/screening/cli.py ../fresh_screening_replay/community-library__screen_and_uniform.request.json
```

The qualified patch version is CPython 3.12.14. Native Windows execution has not
been qualified.

The replay checks the identity of each historical source before constructing
requests. All counts, selected IDs and intervals are recalculated. The archived
primary comparison remains 32 versus 19 discoveries at 112 reviews per policy,
with 64 flagged cases, 48 residual draws and the original simultaneous upper
count of 60. The module does not substitute a post hoc bound or a different
screening function for that result.

## Input and output contract

`request.schema.json` documents the request. Runtime validation also rejects
duplicate JSON keys, repeated IDs, invalid labels, incomplete output pairs,
out-of-frame flags, malformed permutations, booleans used as integers and
observations that do not match the selected IDs exactly. `U` is a reference
label; it is distinct from a missing observation or an execution error.

`plan_input` contains unique `case_ids`, `flagged_ids`, an integer `budget`, a
permutation of the complete frame and a `design_id`. `checker_outputs` maps each
case to `[T_FULL, B_ASSERT]`. `observations` contains only the selected labels.
`alpha` is an exact rational string and `sampling_basis` states the source of the
random-sampling design. A digest binds the JSON inputs; it does not authenticate
the author or establish that a permutation was drawn independently.

The three boundary cases have explicit meanings:

| Condition | Behaviour |
| --- | --- |
| No flags | Sample from the whole frame. Flag precision is null with `UNDEFINED_EMPTY_FLAG_PANEL`. |
| Flags exhaust the budget | Review the flags and draw zero residual cases. The residual upper count is its whole population. |
| Flags exceed the budget | Return `INVALID_DESIGN`, a null selection and no scientific interval. The declared overflow rule is `REJECT_DESIGN`. |

Malformed inputs raise `INPUT_ERROR`; an unreadable file or output collision
raises `EXECUTION_ERROR`. The CLI exits 0 for a conditional score, 2 for an
invalid input/design and 3 for an I/O execution failure. Reports written with
`--out` require a new path. `--expect-sha256` optionally enforces the raw request
identity before parsing.

## Meaning of the bounds

The deterministic interval uses the observed errors and every unreviewed case.
The conditional upper count inverts the exact hypergeometric lower tail under
sampling without replacement. A count is retained when `P(X <= x) > alpha`.
All arithmetic is integer or rational. The implementation accepts positive
sample hits through the general formula. `zero_hit_upper` explicitly rejects
any positive hit.

Coverage requires a fixed residual frame, a simple random sample independent
of its reference labels, accurate adjudications and the declared analysis look.
The API records this condition; arbitrary user-supplied permutations do not
establish it. No independence between contexts is needed to sum the retained
per-context bounds using Bonferroni at their declared levels. These sampling
bounds differ from the deterministic convention/departure intervals implemented
in `../reference_audit/`.

The tests enumerate every sample for populations from zero through nine and
compare the implementation with the resulting empirical finite distributions.
They also check invalid plans, positive hits, exact equality at alpha and the
CLI error paths. The executed test receipt specifies the actual counts.

## Files and provenance

`inputs/` contains unchanged historical records, with their source paths and
digests in `INPUT_LOCK.json`. Version 1.0.0 distributes the code under MIT and
the records and documentation under CC BY 4.0; see [the licensing scope](../../LICENSING.md).
Each replay writes eight complete requests, eight reports and a consolidated
result. Historical source identities and observations remain unchanged.
