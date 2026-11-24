# Supplement T: reference audit and diagnostic qualification

[Documentation](../README.md) · [Software overview](../../README.md)

Companion to When survey workflow verifiers agree and both are wrong

This supplement identifies the documentary inputs, decision assumptions and receipts for the O15 convention analysis, then documents the implemented reference audit, native diagnostic transformations and screening replay. Sections T1–T5 preserve the earlier convention analysis; T6–T11 report the F3 software qualification. [Supplement S](historical_profile.md) retains the historical P4 evaluation and the separate P5 qualification.

## T1 Documentary scope

The archived frame contains 192 O15 agreements. Each reference evaluation reads the claim record, the claim-to-source edge record and the retained result. The replay first verifies the three recorded hashes for each dossier. It reproduces all 192 labels under the fixed experimental grammar and holds the two historical reports fixed. The replay method evaluates O15 on the retained documents. The linked historical receipts give the separate execution evidence for the two checkers.

## T2 Conventions and discrepancy counts

T-T01. Reference conventions on the retained 192-agreement frame.

| **Convention** | **Lookup rule for an alias**                                 | **Count** |
|----------------|--------------------------------------------------------------|-----------|
| literal_only   | Require the complete alias token as the key.                 | 0         |
| suffix_only    | Require the suffix following the prefix.                     | 48        |
| either_unique  | Accept either key. When both exist, require the same target. | 32        |
| prefer_literal | Prefer a literal key. Use the suffix on literal key absence. | 16        |
| prefer_suffix  | Prefer a suffix key. Use the literal on suffix key absence.  | 32        |

Direct pointers and the value and required metadata predicates are common to all five rules. A missing documentary premise can yield U. A dossier awaiting adjudication is omitted from the query transcript. The counts apply solely to the retained 192 agreements.

## T3 Ten convention-analysis probes

The local pre-evaluation commitment binds the protocol, evaluator, new inputs and expected labels. The ten new dossiers and five conventions give 50 comparisons. All matched the fixed expectations. The probes test a literal-direction conflict and its suffix-direction mirror, equal values attached to different metadata, pointer escaping, a valid array index, a disallowed padded array index, a valid padded object key and a missing result. One dossier repeats the document bytes of the literal-direction conflict for the incompatible-context transcript.

Suffix preference and the fixed unique-target convention coincide on all 192 archived labels. They differ on the new suffix-direction mirror. The preferred suffix points to the claim's matching evidence under suffix preference, while the two valid key spellings in the map point to different targets under the unique-target rule. The expected verdicts are S and V, respectively.

## T4 Interpreting the threshold

At the illustrative ceiling 24, there are six pairs of conventions on opposite sides. Each of 16 archived dossiers separates all six pairs. The selected example is the first such identifier in lexical order.

R1PROS-1175F475261EE917E0E06A6A

T-T02. Conditional counts at the illustrative ceiling of 24.

| **Adjudication** | **Common convention**            | **Independent choices by dossier** |
|------------------|----------------------------------|------------------------------------|
| S                | 0 or 16, at or below the ceiling | 0–47, undecided                    |
| V                | 32 or 48, above the ceiling      | 1–48, undecided                    |

The common-convention column gives attainable counts. The independent-choice column gives the sharp interval when each dossier may follow a separate choice from the same five rules. The two verdicts are possible authoritative responses and are analysed conditionally.

A stipulated S for the new mirror leaves two compatible conventions with 32 or 48 discrepancies on the archived frame. Another synthetic transcript gives different labels to byte-identical documents under different local rules. Every global candidate fails at least one of the observations, so the reference reports OUT_OF_MODEL and no numerical interval. The new probes do not enter the historical denominator.

## T5 Earlier reproducibility records

The archived prospective package supplies the paired O15 outputs, original reference labels and 576 documentary records. The convention-analysis results give the discrepancy counts for all five conventions, the ten-probe signatures and traces, and the transcript outcomes. The earlier local reproduction receipt records a byte-identical repeat from a fresh extraction of the archived dossier and rejection of a modified threshold commitment before evaluation. The current software package retains these records under phase2; the F3 regression and integrated qualification identify their additional executions separately.

**Convention-analysis result**

`259e8bd285373048e53fc5fedcfae0a221ffa310eb9e5b159843e7693363dbbb`

**Pre-evaluation commitment**

`db1b10464f1a619ae29edd1941216d34814c00f293e1b4f49dd5bf5edfd3d71a`

The sampling limit under the fixed experimental reference addresses uncertainty under the original inspection design. The convention-conditioned counts arise from a different finite-model analysis and carry no sampling coverage.

## T6 Executable reference model and certificates

The reference_audit component, version 1.0.0 in software package 5.0.0-local.3, implements a finite union of explicitly supplied joint centres. A request records case identities, the paired checker outputs, local admissibility sets, fixed observations, nonnegative exact weights, protected coordinates and one shared budget of eligible local departures. Exact rational arithmetic preserves the requested score and threshold. The interface evaluates the supplied centres; their completeness is a modelling responsibility.

The optimiser separates mandatory departures from optional gains and returns sharp lower and upper scores with complete assignments attaining them. A separate exact-cost dynamic programme verifies the endpoint scores and the first budgets permitting either threshold region. Direct certificate checks also verify request identity, local admissibility, hard observations, protection, total Hamming cost and score. A valid hash binds a certificate to its request; it does not establish the authority or truth of an external adjudication.

The four semantic states distinguish a resolved decision at or below the threshold, a resolved decision above it, an interval spanning both sides and an empty feasible family. Input, execution and verification errors remain separate from those semantic states. Malformed input therefore cannot be converted into a semantic violation merely because a process returned an error.

An external query can have zero score weight while consuming the shared departure budget. A protected query must retain its centre prediction. Adjudicated labels remain fixed in both cases. The budget counts distinct local reference outcomes; it does not count independent adjudicators, causes, templates or contexts.

## T7 Convention scope and local departures

T-T03. Sharp intervals under the same stipulated conflict query at k = 0. Counts concern the 192 archived paired agreements.

| **Convention scope**        | **S branch** | **V branch** |
|-----------------------------|--------------|--------------|
| One global convention       | \[0, 16\]    | \[32, 48\]   |
| One convention per context  | \[0, 40\]    | \[8, 48\]    |
| Casewise prediction product | \[0, 47\]    | \[1, 48\]    |

The global model supplies five centres. The contextwise model supplies all 5⁴ = 625 assignments across the four contexts and was checked against direct raw-row enumeration. The complete casewise prediction product uses a separate coordinate-extrema calculation at k = 0; the explicit-centre engine did not enumerate 5¹⁹² centres. Both relaxations leave the ceiling of 24 unresolved for either stipulated branch.

With one eligible local departure, the stipulated S branch has interval \[0, 47\] under either verified admissibility choice. The V branch has \[1, 48\] under the restricted local prediction sets and \[1, 49\] when S, V and U are all admissible. In each branch the first opposite-side completion appears at one departure. Because the feasible families are nested, this makes the original decision undetermined; it does not produce an opposite unanimous decision.

For the mirror-S transcript, the original compatible global counts are 32 and 48. A completion at or below 24 first becomes feasible at budget 1 when the external probe can depart and consume the shared budget. If that probe is protected and departures are restricted to the scored frame, the first such completion requires eight. The probe contributes zero to the discrepancy count in both calculations.

## T8 Fixed-query certificates and mathematical qualification

The canonical query routine applies only to the unit-weight 192-case frame, its five exact versioned conventions, ceiling 24, budgets zero through eight, no prior observations, all frame positions eligible for departures and one of the two verified admissibility choices. It returns NOT_APPLICABLE for requests outside this domain. The article gives the necessity and sufficiency proofs; the implementation checks their stated finite instance.

T-T04. Exact minimum size of a preselected adjudication set in the canonical instance.

| **Departure budget k** | **0** | **1** | **2** | **3** | **4** | **5** | **6** | **7** | **8** |
|------------------------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| Minimum query size     | 1     | 3     | 5     | 7     | 9     | 11    | 13    | 15    | 33    |

At budget seven, the certificate identifies a 15-query set and lower-bound witnesses. At eight, it identifies all 32 indispensable frame positions plus one control, with constructive necessity witnesses. These finite results do not extend the expression 2k + 1 beyond seven or provide a general query-selection theorem for other matrices or grouped departures.

Qualification passed 27 test methods. Within them, 5,198 input-and-budget comparisons checked endpoint and radius results against direct assignment enumeration: 5,184 binary configurations and 14 additional ternary, multicentre, weighted or external-query cases. Each of 17 packaged examples produced a report and a separate verification receipt. Regression executed the retained convention evaluator on all ten original probe dockets and reproduced the original transcripts at k = 0. These are different verification units and are not independent experiments.

The reference-audit component itself made no native checker invocation. Its execution environment was CPython 3.12.14 on Linux. The declared Python 3.10 language baseline is separate from the environment actually executed.

## T9 Native O15 diagnostic transformations

The diagnostic component separates documentary reference evaluation from native checker execution. Each new synthetic dossier has a fresh identity, regenerated raw-byte inventory and recalculated semantic commitment under the matching frozen profile. The unchanged P4 and P5 checker entry points are executed as separate processes. Commands, exit codes, output streams and the complete O01–O16 vector are retained. Synthetic producer records remain documentary inputs; the producer itself is not run.

T-T05. Transformation families and the relation tested.

| **Family** | **Transformation**                             | **Interpretation**                                  |
|------------|------------------------------------------------|-----------------------------------------------------|
| T01        | Reorder unique JSON members                    | Whole-vector invariance with regenerated custody    |
| T02        | Coherent bijection of alias names              | Whole-vector invariance under each named convention |
| T03        | Change the target chosen by competing keys     | Convention-conditioned contrast                     |
| T04        | Change the legitimate lookup convention        | Reference sensitivity                               |
| T05        | Repair an alias chain to a direct target       | Repair, not an added multihop convention            |
| T06        | Exercise pointer syntax and indices            | Valid and invalid reference controls                |
| T07        | Equal value with wrong target metadata         | Metadata-sensitive contradiction                    |
| T08        | Co-permute rows with correct local/source maps | Profile-scoped whole-vector invariance              |

Each native branch met 94 predeclared invocation expectations across 21 transformation pairs and the accompanying controls. The 94 outcomes consist of 92 complete semantic reports and two expected invalid-arm command-line errors without semantic reports. All 12 declared whole-vector invariance comparisons per branch passed, and the transformation pairs showed no changes outside O15.

In full-token-correct conflict cases, the P4 checkers return S/S, while either_unique returns V and literal_only returns S. The opposite conflict orientation exposes the corresponding suffix-sensitive agreement under P5. These cases locate the reference convention on which the correctness judgement depends. They do not assign an unobserved universal ground truth or a field error prevalence.

The final component evidence comprises 23 unit methods, eight CLI checks and a documentary regression of 202 dossiers under five conventions, giving 1,010 convention comparisons. The regression contains the retained 192 dossiers plus the ten earlier probes; it does not rerun their historical checker identities. Definitive native component runs are native_p4_003 and native_p5_003. Earlier attempts remain retained under their own source bindings and are not pooled.

T08 covers the frozen profiles’ row-local eligibility and order-independent targets. Co-permutation does not authenticate initial pairing or establish invariance for order-sensitive allocation, seeded folds or a different method.

## T10 Screening implementation and retained-design replay

Selection is separated from scoring. A zero-flag panel gives whole-frame simple random sampling and undefined precision; when flags exhaust the budget, the residual draw is empty. A flag count exceeding the review budget is rejected as an invalid design. Typed plans are reconstructed strictly, with malformed JSON, duplicate members and nonfinite values reported as input errors.

The residual upper bound uses exact hypergeometric calculations for the observed number of hits. Its zero-hit helper rejects a positive hit count rather than silently applying an inappropriate formula. Qualification passed 12 tests, including 660 direct subset-bound comparisons and 1,155 exact conditional-coverage checks.

The frozen replay preserves case identifiers, flags, permutations and adjudication labels. Across eight context–policy reports, 72 field comparisons matched the retained records. Screening reviewed 64 flagged dossiers and 48 residual dossiers, finding 32 errors in the flagged panel and zero in the residual sample. Uniform review found 19 errors. Both policies used 112 reviews. The original conservative familywise upper bound remains 60; the replay made no new draws or human adjudications.

The exploratory alias-only rule and other post hoc policies are distinct from the original prospective design. They do not replace its upper bound or provide a newly prospectively validated selection rule.

## T11 Reproduction sequence and evidence identities

Run the complete software qualification from the extracted software root with CPython 3.12 on Linux, using a new output directory outside that root:

```sh
python3 -B -m r5_f3.integration.run --out ../nsc_f3_verification_01
```

The retained successful integrated run used CPython 3.12.14 on Linux and passed all 15 command groups. It included 346 native checker invocations: 94 P4 diagnostics, 94 P5 diagnostics and 158 P5 full-review invocations. The latter satisfied 183 checks. These are new synthetic runs with their own identities; repeated qualification does not enlarge the archived empirical denominator.

The integrated run also repeated the reference tests, documentary regression, screening checks, retained decision tests and software example. The before/after inventory contained 10,456 identical entries. Its raw command receipts and output files are retained with the summary. A first integrated attempt failed because of screening module imports; the corrected import paths passed the full rerun. The failed attempt and its source snapshot remain in the audit record.

[SUPPLEMENT_T_EVIDENCE_INDEX.json](../evidence/SUPPLEMENT_T_EVIDENCE_INDEX.json) maps every added result to its component path, exact SHA-256 and byte count. Recovered documentary copies are available in `supplement_sources/source_evidence/T/` in the data archive. Paths beginning software/ are relative to the software package, paths beginning checkpoint/ to the retained F3 checkpoint. The machine-readable index also records the historical reference-analysis result and commitment shown in Section T5. These historical locators are distinct from the current distribution paths described in the [documentation guide](../README.md).

[Supplement P](prospective_evidence.md) provides the prospective-study evidence guide cited in the article. It separates the original fixed-reference sampling design from retrospective convention analysis, native diagnostics and subsequent regression checks. Distribution terms are recorded in the [rights notices](../../RIGHTS_NOTICES.md).
