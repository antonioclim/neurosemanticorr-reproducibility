# Supplement S: historical profile and qualification

[Documentation](../README.md) · [Software overview](../../README.md)

Companion to When survey workflow verifiers agree and both are wrong. This supplement documents the finite verification profile, the historical P4 v2 experiment and the separate P5 toolkit qualification. Section S10 identifies their retained source records. [Supplement T](reference_audit.md) reports the later reference-audit implementation and F3 diagnostic qualification.

## S1. Scope and formal interpretation

The scientific question is whether named retained artefacts satisfy named cross-stage relations under fixed types, evidence requirements and trust assumptions. A study contract records variables, response states, policies, populations, estimands, design, configuration, applicability and assurance limits. An evidence graph has immutable typed nodes and labelled dependent-to-prerequisite edges. Reachability alone does not prove a relation; the edge predicate must be evaluated.

### S1.1 Evidence judgements and completion

For an active obligation, S means all required admitted subclauses hold; V requires a decisive finite contradiction with an exact locator; U records unavailable, ambiguous or deliberately unevaluated premises. NA requires a proven false applicability predicate fixed before observing outcomes. All 16 fresh-core obligations are active, so their operational vectors use S, V and U. These evidence judgements do not assert a named four-valued truth calculus.

S-T01. Aggregate policy after completed evaluation. Execution status is a separate axis.

| **Condition**                                 | **Aggregate**                         |
|-----------------------------------------------|---------------------------------------|
| At least one applicable V                     | REJECT                                |
| No V and at least one required U              | INDETERMINATE                         |
| Nonempty active set, all active obligations S | ALLOW_WITHIN_SCOPE                    |
| Empty or all-inapplicable set                 | INDETERMINATE; NO_APPLICABLE_COVERAGE |

NOT_RUN, CRASH, TIMEOUT, RESOURCE_LIMIT and UNSUPPORTED_ENVIRONMENT are execution outcomes. A crash is never credited as a correct rejection. A readable closed inventory may establish O02=V for a missing required file while its dependent semantic relation remains U. Missing inventory itself cannot establish closure. Dependencies are local prerequisites, rather than a rule that every earlier obligation must pass.

### S1.2 Conditional equivalence and assurance

If T_FULL and B_ASSERT receive the same evidence and correctly evaluate the same obligations, applicability, numerical rules and aggregation, their vectors and aggregate verdicts are identical component by component (P07). The organisational form of a contract cannot create an intrinsic detection advantage over an equally informed correct assertion baseline. Runtime, effort and diagnostic usefulness remain separate outcomes. Internal consistency does not establish authenticity, initial pairing, construct validity, causal truth or calibrated uncertainty.

Evidence: S01 §§2–5, 12; S13 P01–P07 and X01–X09; S17 aggregation_order and dependency_policy.

## S2. Obligation registry: representation to state

Tables S-T02 and S-T03 summarise the exact fresh-core relation instances. Their broader historical names are retained for continuity. The complete normative clauses and witnesses remain in S03; these summaries do not broaden the exercised predicates. All 16 obligations are active, with 27 clauses in total.

S-T02. Concrete obligations O01–O08 and their interpretative boundaries.

| **ID / family** | **Relation evaluated in the fresh core**                                                        | **Boundary or required distinction**                                                                                                               |
|-----------------|-------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| O01 / F01       | Strict JSON/typed admission; registered R01 canonical semantic commitment.                      | Duplicate keys, nonfinite values and malformed present types violate admission. Missing unrelated files are not malformed bytes.                   |
| O02 / F01       | Closed raw-byte inventory: exact membership, sizes and SHA-256, excluding inventory itself.     | Readable absence of a mandatory member is V; unavailable inventory is U. Custody is distinct from semantic linkage.                                |
| O03 / F02       | Declared defaults resolve to effective settings; executed settings equal effective settings.    | Documented default expansion may be valid. A display-only or non-executing option is not an executed setting.                                      |
| O04 / F02       | Recorded source/runtime agree with frozen anchors; source text has the expected raw digest.     | Synthetic producer records are documentary inputs. Actual checker/interpreter bindings are separately recorded by the supervisor.                  |
| O05 / F03       | Stable IDs are unique; data/state physical ID order equals the receipt sequences.               | This instance does not test the broader historical content-linked co-export digest. Neither O02 nor matching ID order proves initial pairing.      |
| O06 / F03       | Population IDs/supports equal declared eligible membership; local positions map to source rows. | Enumeration may vary only with correct maps. Unknown states or ambiguous IDs can leave the membership relation U.                                  |
| O07 / F04       | Workflow-specific state vocabulary and value/change-kind coherence.                             | W1 observed values differ from non-observed states. W2 original availability is separate from imputed or edited output; arithmetic belongs to O11. |
| O08 / F04       | Ordinal category identity/order and stage-specific policy authority.                            | W1 increasing display codes do not authorise an arithmetic mean. W2 imputation requires the declared policy and separate input/change states.      |

### S2.1 Historical methodological rationale

The retained Study Contract distinguishes a physical missing value from response semantics. Refusal, explicit “do not know”, structural skip and non-applicability cannot be collapsed solely because each is stored as null. Ordinal identity includes ordered labels, score map, construct and direction; equal category counts do not permit substituting likelihood labels for readiness labels. The demonstrator readiness index remains unvalidated. These historical safeguards motivate the profile without implying that every historical implementation path was exercised here.

Evidence: S02 obligations O01–O08; S03 clauses and predicate_instances; S05 Scope of exercised relations; S14 paragraphs 1–3.

## S3. Obligation registry: estimand to assurance

S-T03. Concrete obligations O09–O16.

| **ID / family** | **Relation evaluated in the fresh core**                                                                             | **Boundary or required distinction**                                                                                                                  |
|-----------------|----------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| O09 / F05       | Declared target method equals the actual supported method; population names bind to materialisation.                 | This scoped relation does not repeat population eligibility or position arithmetic, and has no blanket upstream-pass dependency.                      |
| O10 / F05       | Requested operation belongs to the fixed supported set; generalisation and causal flags are false.                   | A consistent supported declaration does not test the scientific assumptions behind it.                                                                |
| O11 / F06       | Exact retained arithmetic, optional displays and formula/method binding.                                             | Self-contained result operands support recomputation. They do not authenticate the producer or add an undeclared relation to every original data row. |
| O12 / F06       | Consumer result ID, status, values and optional displays equal the authoritative retained result.                    | Consistent propagation of a wrong result may satisfy this relation; arithmetic correctness is a different predicate.                                  |
| O13 / F07       | Unique task IDs, terminal counts and frozen universe partition agree; failures and unattempted tasks remain visible. | Replays are not new independent evidence. Conditional rates retain the unconditional requested denominator.                                           |
| O14 / F07       | Task, wait, result-presence and closure records agree under the fixed lifecycle.                                     | Missing output is not proof of no in-memory computation. A truthful failure record is not successful science.                                         |
| O15 / F08       | A bounded structured claim resolves to a retained value with matching unit, denominator and scope.                   | The P5 grammar specifies one alias hop. This finite relation is not natural-language entailment or producer authentication.                           |
| O16 / F08       | Pre-existing assurance flags and limitations remain within declared scope, retaining P1 FAIL_CLOSED.                 | The future checker report is not its own evidential input. Consistency cannot be relabelled as complete programme certification.                      |

### S3.1 Coverage and direct witnesses

A finite witness names the obligation, admitted evidence node or edge and exact field/position locator, with observed and expected relations. Direct violation localisation is distinct from a missing-premise explanation and from a human causal diagnosis. A rejection for stale custody bytes does not by itself demonstrate detection of an estimand error.

Every ablation retains all 16 vector slots and a separate frozen coverage mask. An omitted active clause is U with NOT_EVALUATED_BY_ABLATION, never S or NA. With any required omission, a completed ablation can reject a witnessed contradiction but cannot grant full-profile ALLOW_WITHIN_SCOPE. A satisfied named subset must be labelled as that subset.

Evidence: S02 O09–O16; S03 clauses O09.local through O16.scope; S13 X08; S17 ablation_reporting and localisation_unit.

## S4. Numerical semantics and workflow anchors

C00–C03 govern the fresh finite core. Historical N00–N11 document heterogeneous original-source tolerances and remain unchanged; they do not require NumPy, SciPy, covariance or network calculations in this standard-library benchmark. No result-dependent tolerance widening is permitted.

S-T04. Active numerical policies.

| **Policy**                   | **Rule**                                                                                                                                                                                                          |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C00: exact discrete types    | IDs, order, counts, booleans, task partitions, statuses, domains and hashes compare exactly. Boolean is not an integer count; no floating coercion.                                                               |
| C01: exact rationals         | Retained numerator and denominator are integers excluding bool; \|n\| ≤ 10^9 and 1 ≤ d ≤ 10^9. Non-reduced fractions are admitted. Derived exact reference intermediates may exceed the retained component bound. |
| C02: presentation            | Optional decimal strings use exactly six fractional digits and HALF_EVEN rounding, with canonical 0.000000. The rational is authoritative; rounding is not a statistical tolerance.                               |
| C03: missing/state semantics | Null differs from zero. Empty support, zero denominator and missing inputs retain typed undefined reasons. No NaN/Infinity or silent ordinal-to-interval coercion.                                                |

$$
\frac{n_1}{d_1}=\frac{n_2}{d_2}\quad\Longleftrightarrow\quad n_1d_2=n_2d_1,\qquad d_1,d_2>0
$$

### S4.1 W1: ordinal distribution

The main anchor has three observed eligible rows in the first three of five declared categories. Counts are (1, 1, 1, 0, 0), the eligible denominator is 3 and each represented category proportion is 1/3, displayed optionally as 0.333333. The excluded refusal contributes neither a count nor the denominator. Category identity and order remain part of the contract.

### S4.2 W2: separate available-case supports

The literal cleaning adaptation computes staff and turnover means on their own available supports. It does not replace the ratio of these means with the mean of complete-case row ratios. Fractional imputed staff is permitted by this descriptive toy adapter.

$$
\begin{aligned}\mathrm{mean\_staff}&=\frac{10+30+20}{3}=20,\\\mathrm{mean\_turnover}&=\frac{100+200+400}{3}=\frac{700}{3}.\end{aligned}
$$

$$
\begin{aligned}\mathrm{ratio}&=\frac{20}{700/3}=\frac{3}{35},\\\mathrm{imputed\_staff}&=200\times\frac{3}{35}=\frac{120}{7}.\end{aligned}
$$

The alternative complete-case mean of staff/turnover is 3/40, a different declared method. The teaching rule for other.rev fills missing with zero and then takes absolute value, yielding (0, 5, 10, 0); it is not total revenue minus turnover. Retained turnover/total.rev anchors are 5/6, 20/21 and 1. Missing turnover remains typed undefined unless a separately declared rule supplies it.

Response-state labels do not identify MCAR, MAR or MNAR; imputability does not prove a missing-data mechanism. Internal coherence and a synthetic fixture cannot establish substantive measurement validity (Rubin, 1976; Seaman et al., 2013).

Evidence: S04 numeric_policies and analytically_derived_literal_anchors; S03 W1_arithmetic/W2_arithmetic; S18 N00–N11; retained references in S10.

## S5. Corpus, protocol and scoring

P4 v2 is a new reconstruction under the retained P3 design, rather than a byte-identical recovery of lost v1 work. The earlier 96 v1 development observations remain chat-only historical statements, without the raw evidence required for reuse; their identities are retired and they are excluded from every v2 estimate. The visible main corpus is purposeful coverage of a taxonomy, not a random sample or externally blinded hold-out.

S-T05. P4 v2 accounting; execution units do not enlarge the case denominator.

| **Evidence stratum** | **Design and unit**                        | **Completed / planned**   |
|----------------------|--------------------------------------------|---------------------------|
| Separate DEV         | 16 cases × 6 arms                          | 96 / 96 invocations       |
| Main functional      | 100 cases × 6 arms                         | 600 / 600 invocations     |
| Main timing          | 100 cases × 2 primaries × 4 blocks         | 800 / 800 invocations     |
| MAIN total           | Functional plus timing                     | 1,400 / 1,400 invocations |
| v2 total             | DEV plus MAIN                              | 1,496 / 1,496 invocations |
| Main case strata     | D=32; valid=32 alternatives +4 clean; M=32 | 100 / 100 fixed cases     |

### S5.1 Primary and diagnostic contrasts

T_FULL and B_ASSERT receive the same profile and admissible evidence. A0_SYNTAX, A1_STRUCTURE, A2_LOCAL and A3_PROVENANCE intentionally cover fewer clauses. W1 and W2 are source-distinct synthetic adaptations sharing programme components. W2 source logic has an external origin, while its literal toy rows, wrapper, translated implementation and oracle recipes are programme-authored. Native R execution and external laboratory replication are not claimed.

Gross D detection requires a completed valid REJECT. Target attribution requires the designated obligation. Strict registered localisation additionally requires the exact registered six-field witness without unsupported allegations; duplicate witnesses collapse. Conditional localisation divides by gross detections, while unconditional localisation retains 32. Valid-control rejection uses all 36 gold-valid cases. M vectors, aggregates and target-U behaviour are assessed separately; closure rejection is not proof of a missing semantic relation.

### S5.2 Qualification, gates and immutable evidence

Case-level full vectors and accepted witness sets are frozen before candidate outcomes. Qualification fixtures, scheduled DEV and MAIN remain distinct. DEV originally failed on 12 truthful optional-U diagnostics. A reviewed narrow expectation correction qualified on the same 96 reports, with 192 report/receipt hashes unchanged. Fourteen optional permissions were added, twelve emitted; required vectors, masks, aggregates and direct witnesses did not change. Both the failed gate and adjudication remain in the record.

The historical results in Sections S5–S9 retain their original scientific identities, budgets, admission rules and denominators. The later F3 implementation and native diagnostic runs are documented separately in [Supplement T](reference_audit.md); they do not replace or rescore these results.

Evidence: S05 Reconstruction and accounting, Measurement and scoring; S06 main/development; S07 T01; P4 08_reviewer/DEV01_OPTIONAL_U_ADJUDICATION_R001.json.

## S6. Retained P4 results and shared failure

P4 MAIN completed operationally, but semantic conformance remains FAIL_CLOSED. Both primaries agree on every main vector and aggregate, including their two shared disagreements with gold. Agreement therefore establishes neither correctness nor equivalence to the oracle.

S-T06. Primary finite-corpus outcomes. Denominators are cases, not timing repeats.

| **Outcome**                                   | **T_FULL**     | **B_ASSERT**   |
|-----------------------------------------------|----------------|----------------|
| D gross rejection / eligible D                | 32 / 32        | 32 / 32        |
| D target attribution / eligible D             | 32 / 32        | 32 / 32        |
| D strict registered localisation / eligible D | 32 / 32        | 32 / 32        |
| Gold-valid false REJECT / valid cases         | 2 / 36 (5.56%) | 2 / 36 (5.56%) |
| M exact vector and aggregate / M cases        | 32 / 32        | 32 / 32        |
| M wrongly decisive target-U assertions        | 0 / 32         | 0 / 32         |
| Full functional conformance / all main cases  | 98 / 100       | 98 / 100       |

D paired tables have n11=32 and n10=n01=n00=0. The valid false-rejection table has n11=2, n00=34 and n10=n01=0. Every exact paired primary contrast is zero. For M, 30 cases per primary reject the readable missing-member inventory while retaining unknown dependent semantics; two missing-inventory cases are INDETERMINATE.

### S6.1 The two O15 alias alternatives

P3BENCH-v2-W1-C044 and P3BENCH-v2-W2-C044 use source_pointer="alias:primary" and aliases\["primary"\]. Intended targets are /values/denominator and /values/mean_staff. Materialisation removes the prefix, while both checkers looked up the complete token. The neutral P4 interface did not specify the lexical prefix convention or its removal, and its positive examples used direct pointers. The defensible diagnosis is a shared representation/interface gap; exclusive attribution to a candidate defect is unsupported.

The term false rejection reports frozen gold scoring. All source, gold and scores remain unchanged. There are four canonical functional case-arm discrepancies plus sixteen timing repetitions: 20 affected reports, two distinct cases. P5 does not rescore them.

### S6.2 Ablation interpretation

D detection and strict localisation are 0/32, 0/32, 11/32 and 23/32 for A0–A3; complete-obligation coverage is respectively 0, 0, 3 and 10 of 16. All ablations reject 0/36 valid controls but leave every valid case INDETERMINATE. A3 matches all M aggregates, yet no ablation has a complete M-vector match or full-profile conformance. These are coverage contrasts and cannot establish an intrinsic advantage over the strong same-obligation baseline.

Evidence: S06 primary, paired_primary, alias_finding and ablations; S07 T02–T05. Original P4 MAIN and P1 FAIL_CLOSED are retained.

## S7. Timing, dependence and sensitivity

All 800 timing reports are valid, with four complete matched blocks per case and no semantic drift. Timing repetitions describe the same finite cases; they are neither new detection cases nor independent incidents. DEV elapsed time is 16.373668117 s; MAIN elapsed time is 315.328694407 s. The phase clock is distinct from individual invocation intervals.

S-T07. Timing summaries use explicitly different units and aggregation orders.

| **Quantity**                                     | **Observed descriptive value**     |
|--------------------------------------------------|------------------------------------|
| Median of 100 within-case median T−B differences | +0.00021549925 s                   |
| Range of the 100 within-case median differences  | −0.0202032675 to +0.021616316 s    |
| Median of 100 within-case median T/B ratios      | 1.0056296502                       |
| Range of within-case median ratios               | 0.8752973862 to 1.1751346589       |
| Pooled median invocation interval, T; B          | 0.1343833915 s; 0.135321253 s      |
| Pooled mean invocation interval, T; B            | 0.139726156125 s; 0.139295781460 s |

Invocation intervals include supervisor preparation, process work, report validation/publication and cleanup. Final receipt writing is outside that interval but within phase elapsed time. Child parsing and predicate-only durations are unmeasured. Alternating matched execution order, persistent filesystem cache and one host limit interpretation. Differing summary orderings preclude selecting one favourable number as a general speed claim. Sampled process memory is not certified complete process-tree peak RSS.

### S7.1 Finite analysis and missing-outcome policy

No binomial confidence interval, bootstrap, McNemar test, randomisation test or other IID inference is applied. Exact counts describe the constructed corpus. A zero contrast does not establish statistical equivalence or general non-inferiority. Every leave-family-out, leave-workflow-out and alternative-weight paired contrast stays zero because primary actions coincide.

MAIN has no genuinely missing outcomes. The frozen protocol nevertheless retains missing slots in the planned denominator: D contrast bounds are (kT−kB−mB)/32 and (kT+mT−kB)/32, with observed rejections k and genuinely missing outcomes m. These are completion bounds, not confidence intervals; the valid-case denominator is 36.

### S7.2 Duplicate sensitivity does not replace primary weights

Raw-byte grouping gives 92 groups and no within-group oracle/output conflict. Canonical representation similarity gives 86 groups after omitting inventory commitments, including two oracle-vector conflicts and six arm-group semantic differences; splitting within D, valid and M yields 88 representatives. The valid-domain representative rejection scores are 2/28 for raw grouping and 2/24 for canonical grouping. Neither replaces 2/36. Canonical similarity is not full-input identity or semantic equivalence.

Evidence: S05 finite descriptions, timing definitions and completion bounds; S06 timing/duplicate_sensitivity_summary; S07 T06 and deterministic sensitivity.

## S8. Prospective P5 repair and reproducibility

NSC-P5-CORE-1 and grammar NSC-O15-ALIAS-1 resolve the lexical gap prospectively. Repaired T_FULL and B_ASSERT copies have new versioned identities. The payload/report shape is retained, while profile identity and semantic specification advance. P5 checks are development/regression qualification on fresh P5UNIT identities, not a new 100-case blinded benchmark.

### S8.1 One exact reference grammar

A direct reference is a nonempty JSON pointer beginning with /. An alias is the literal case-sensitive prefix alias: followed by an exact nonempty Unicode NAME. Remove the prefix once, look up NAME without trimming or Unicode normalisation and require the selected value to be a direct pointer. Chains and cycles are rejected. Decode only ~0 and ~1 once; array indices match ASCII 0\|\[1-9\]\[0-9\]\*, with no leading zeros, sign, append token or out-of-range value. The resolved pointer selects field metadata for value, unit, denominator and scope.

Typed malformed or unresolved references yield O15=V. Empty or ill-typed source_pointer or selected strings retain admission O01=V and dependent O15=U unless another admitted local contradiction is decisive. The complete relational grammar remains O15.claim_source, level 4; it is not promoted into a local ablation clause.

S-T08. Distinct P5 qualification units must not be summed as an incident sample.

| **Component**                          | **Retained qualification**                                                       |
|----------------------------------------|----------------------------------------------------------------------------------|
| Own implementation checks              | T: 62 UNIT methods +4 CLI; B: 54 UNIT methods +14 CLI                            |
| Independent alias suite                | 21 literal +112 CLI +4 metamorphic checks                                        |
| Fixture preflight; wrapper             | 56/56 with zero candidate calls; 24/24 with zero candidate calls                 |
| Sealed smoke, CPython 3.12.14          | 45/45 checks; 20 CLI; 2.142737617 s                                              |
| Sealed full, CPython 3.12.14           | 183/183 checks; 158 CLI; 25.056876207 s                                          |
| Sealed full, CPython 3.12.3            | 183/183 checks; 158 CLI; 26.971679581 s                                          |
| Official source/provenance cross-check | 43/43; 336 unique invocations, 328 reports +8 expected exit-2 no-report controls |

Two fresh virtual environments used the same Linux host and the same 78-file kit manifest. This is neither a clean OS/container reproduction nor external laboratory, Windows, native R or Python 3.10/3.11 qualification. The cooperative monotonic smoke/full limits are 300/1,800 s, with 5 s per child, up to 2 s cleanup and final-write overhead. Sampled bytes and deadlines do not constitute a global hostile-code sandbox, suspend-inclusive budget or production resume guarantee.

From the `p5` directory of the software package, choose a new output directory outside the package and run:

```sh
python3 -B -I tools/review.py --mode smoke --out ../../p5_smoke
```

For full qualification, use `--mode full` and a different new output directory. Inspect `SUMMARY.json`, `ENVIRONMENT.json`, `COMMAND.json` and the raw attempts. The historical P6 consolidation did not execute candidates; the subsequent F3 integrated run executed the full P5 synthetic unit review as recorded in [Supplement T](reference_audit.md). CF15 closure remains confined to the qualified P5 profile, with the frozen P4 failure retained.

Evidence: S08 grammar; S09–S10 official isolated evidence; S11 reviewer paths; S19–S23 own, alias, fixture and wrapper qualification. Exact bindings are in the source manifest.

## S9. Economics, threat model and unresolved limits

The economic analysis uses three P3-locked hypothetical analyst-minute scenarios and missing-evidence prevalence q in {0, 1/20, 1/5}. Outcome rates are finite-corpus inputs, not estimates of deployment prevalence. Because primary outcomes coincide, their outcome-loss terms coincide. Measured machine intervals and operational bytes contribute small differences; setup and operational deltas are assumptions.

S-T09. All nine locked illustrative net benefits: T relative to B, analyst-minute equivalents per dossier.

| **Locked scenario**          | **q = 0**    | **q = 1/20** | **q = 1/5**  |
|------------------------------|--------------|--------------|--------------|
| Low volume / low consequence | −0.609999619 | −0.609999667 | −0.609999812 |
| Routine analytic             | −0.289996396 | −0.289997574 | −0.290001107 |
| Higher consequence           | −1.059970974 | −1.059982399 | −1.060016676 |

Every row conditionally favours B under those assumptions; this is not an adoption recommendation. Both conformance guards are false. Measured human setup, maintenance, integration, adaptation, diagnosis and review effort, and measured net adoption benefit, remain null. Exact prevalence/horizon/setup switching expressions and assumptions are retained in the machine-readable analysis; no favourable scenario is selected.

### S9.1 What an internally coherent package cannot establish

An actor able to replace both evidence and every untrusted anchor can construct a coherent false history. Unkeyed hashes do not authenticate authorship. A newly generated receipt may bind an already mispaired data/state pair without recovering original participant correspondence. Equal summaries can conceal different raw histories. Missing output can arise before or after in-memory computation. Each example limits what retained observations can decide.

Co-permutation can preserve identified population membership with correct maps, but does not automatically preserve seeded folds or an order-sensitive method. Numerical identities do not establish estimator assumptions, convergence, construct validity, causal interpretation or calibrated uncertainty. A supported declaration is not proof that its scientific premise holds. Localisation to a registered witness is not measured human diagnosis.

### S9.2 Historical and editorial boundaries

P1 remains FAIL_CLOSED 771/772: the raw-byte/canonical-object confusion was diagnosed, not repaired or rerun. P4 remains 98/100 conformance per primary and MAIN semantic FAIL_CLOSED. P5 closes its explicit repair/qualification scope only. Historical M06DR evidence, adverse results, undefined values, replay dependence and analytical admissions are not rescored by this supplement.

The retained material supports review of the finite consistency relations and the local software candidate. General transfer, external empirical validation and measured human or economic benefits remain open research questions. Exact-build distribution rights are recorded separately from computational qualification. This supplement preserves the original experimental record; later software checks are identified in [Supplement T](reference_audit.md).

Evidence: S12 locked scenario grid; S06 economics/conformance_guard/human_effort; S07 T07–T08; S13 counterexamples X01–X09. Distribution terms are recorded in the [rights notices](../../RIGHTS_NOTICES.md).

## S10. Evidence index and retained references

The source IDs below identify the historical records used to construct this supplement. “P4 ZIP” paths are relative to NSC_P4_RECOVERY_v2/continuity/P3 in the retained P4 archive; “P4” and “P5” paths are relative to their phase roots. The accompanying [SUPPLEMENT_S_SOURCE_INDEX.json](../evidence/SUPPLEMENT_S_SOURCE_INDEX.json) records the original SHA-256, byte length and section locator. Recovered documentary copies are available in `supplement_sources/source_evidence/S/` in the data archive; the data package retains the complete scientific capsules. The index preserves the original locators separately from the paths of the distributed copies.

S01–S02 — P4 ZIP formal/FORMAL_SPECIFICATION_EN_GB.txt; OBLIGATION_PROFILE_v1.json — definitions and registry.

S03–S04 — P4 01_protocol/PAYLOAD_INTERFACE.json; P4 ZIP formal/ACTIVE_CORE_NUMERICAL_MAP.json — 27 clauses and active C00–C03.

S05–S07 — P4 08_reviewer/P4_METHODS_AND_LIMITATIONS_EN_GB.txt; 07_analysis/RESULTS_REPORTING_SUMMARY.json; 08_reviewer/P4_RESULTS_AND_CLAIM_DISPOSITION_EN_GB.txt.

S08–S10 — P5 01_protocol/ALIAS_GRAMMAR_V1.json; 05_evidence/P5_RESULTS_AND_CLAIMS_MANIFEST.json; 03_tests/OFFICIAL_ISOLATED_CROSSCHECK.json.

S11–S13 — P5 kit/QUICKSTART.md; P4 ZIP economics/COST_SCENARIOS_LOCK.json; formal/PROPOSITIONS_AND_COUNTEREXAMPLES.json.

S14–S16 — Original S3_SUPPLEMENT/EXTENDED_STUDY_CONTRACT_METHODS.md; REFERENCES_APA7_WITH_DOI.csv; CURRENT/ASSEMBLY_MAP_CURRENT.md.

S17–S18 — P4 ZIP formal/VERDICT_AND_DEPENDENCY_POLICY.json; NUMERICAL_POLICY.json — aggregation/dependencies and unchanged historical tolerance inventory.

S19–S23 — P5 02_sources/{t_full,b_assert}/QUALIFICATION.json; 03_tests/ALIAS_CONTRACT_QUALIFICATION_DEV_A001.json; 03_tests/ALIAS_FIXTURE_QUALIFICATION_A001/QUALIFICATION.json; 04_tools/PIPELINE_FREEZE.json — own, alias, fixture and wrapper qualification.

### S10.1 Retained methodological references

The following records are retained from the S3 reference baseline (S15), for the missingness distinction in S4. They are not sources of the new P4/P5 empirical counts.

Rubin, D. B. (1976). Inference and missing data. Biometrika, 63(3), 581–592. <https://doi.org/10.1093/biomet/63.3.581>

Seaman, S., Galati, J., Jackson, D., & Carlin, J. (2013). What is meant by “missing at random”? Statistical Science, 28(2), 257–268. <https://doi.org/10.1214/13-STS415>

### S10.2 Reviewer navigation and integration

Read S1–S4 for semantics and numerical rules, S5–S7 for design, immutable outcomes and sensitivity, S8 for the versioned repair and runtime limits, and S9 for economic and assurance limits. The source index identifies the retained sources by evidence ID, locator, byte count and hash. The historical reports retain their original dates, totals and scope; [Supplement T](reference_audit.md) identifies subsequent checks.

The supplement presents the historical results without adding experimental observations. Case-level interpretation follows the frozen raw evidence. Document compilation and rendering are editorial checks; the separate software qualification is reported in [Supplement T](reference_audit.md).
