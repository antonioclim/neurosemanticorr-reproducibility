# Supplement P: prospective study evidence

[Documentation](../README.md) · [Software overview](../../README.md)

Companion to When survey workflow verifiers agree and both are wrong

This guide identifies the original frozen experiment on 192 synthetic dossiers and the evidence supporting its counts, selection policies and sampling bound. It is a retrospective guide to that experiment, not a new protocol or execution. The later reference-model analysis and software qualification are described in [Supplement T](reference_audit.md).

## P1 Frame and frozen reference

Four simulated collection contexts each contain 48 dossiers. Two use the existing W1 profile and two use W2; they are four contexts within two workflow profiles. Twelve prespecified representation strata contribute four dossiers per context. Each case has new data, claim representation and identity. Stratum frequencies are fixed by design and do not estimate field prevalence.

The experimental reference treats direct and one-level alias forms symmetrically: either a literal full token or its suffix may resolve the claim, but conflicting targets are rejected. O15 checks the resolved value and its required unit, denominator and scope. The primary outcome is a shared O15 judgement that differs from this fixed reference. Full obligation vectors and aggregates provide scope checks. Reference construction, input materialisation and candidate execution are separately identified in the original records.

The experiment used byte-identical P4 checker and profile versions on the new dossiers. The frozen plan, frame, reference receipt, input manifests, sources and permutations precede the candidate results. The selection commitment precedes reference-based scoring. The retrospective guide preserves this chronology and the original receipt identities (P01–P14).

## P2 Prespecified review allocations

Each policy has a ceiling of 28 adjudications per context, or 112 across the frame. A dossier costs one adjudication by design; no human review-time saving is measured. Every policy first considers comparable checker disagreements as certainty cases. The disagreement-only policy stops there. Uniform completion fills the remaining budget from comparable agreements. Screening followed by uniform completion first selects agreements flagged by the representation rule, then draws from the unflagged agreements.

The screen flags a used alias when its suffix exists without the literal token, when both keys have different raw targets or when the selected target is another alias. A flag is a reason for review, not an error label. Screening does not inspect the adjudication labels. A uniform permutation is drawn once per context with SystemRandom before candidate execution; restricting that retained order to each eligible residual frame couples the comparisons without another draw.

All 192 pairs agreed on O15, so the disagreement panel was empty. The screened allocation reviewed 16 flagged dossiers and 12 of the 32 unflagged dossiers per context. Across the frame this is 64 flagged reviews and 48 residual reviews, including 30 dossiers that used no alias. P16 reconstructs that last count directly from the selected claim records and records their hashes.

## P3 Original outcomes

P-T01. Original review-policy outcomes on the fixed 192-dossier frame.

| **Policy**                       | **Reviews** | **Shared errors found** | **Errors missed** |
|----------------------------------|-------------|-------------------------|-------------------|
| Disagreement only                | 0           | 0                       | 32                |
| Uniform completion               | 112         | 19                      | 13                |
| Screening and uniform completion | 112         | 32                      | 0                 |
| Exploratory alias-only review    | 112         | 32                      | 0                 |

All 384 original checker invocations produced valid reports. The two arms agreed on the full obligation vector and aggregate for all 192 dossiers, and reported S for every obligation outside O15. The fixed O15 reference identified 32 shared errors: 16 false rejections of valid suffix-only aliases and 16 false acceptances of conflicting mappings whose full-token target matched the claim. Both the reference and each checker had totals of 80 S and 112 V; opposite errors cancelled in those totals.

Uniform review found 5, 5, 5 and 4 errors across the contexts, while screening found eight in each, a realised gain of 13. Of the 64 flagged dossiers, 32 conformed to the reference, including all 16 alias chains and 16 suffix-only claims with the wrong value. No error appeared in the sampled unflagged cases.

The alias-only allocation is an exploratory comparator from the later sensitivity analysis (P15). Its equal discovery count does not distinguish it from the prespecified screened policy. The screened allocation additionally retained a random residual sample outside its panel, which supports the bound described next.

## P4 Residual uncertainty and the illustrative ceiling

Each residual sample was assessed once using the exact hypergeometric upper bound at level 0.0125 per context. With zero observed errors among 12 sampled unflagged dossiers out of 32, the upper residual count was seven. Adding the eight confirmed screened errors gave 15 per context. Summing the four simultaneous bounds yields the conservative 95% upper bound of 60 for the total shared-error count under the fixed experimental reference.

The corresponding deterministic interval is 8–28 in each context, or 32–112 when summed. The exploratory alias-only allocation supports that deterministic interval but supplies no random sample outside its allocation. The eight confirmed errors in each context exceed the illustrative ceiling of six; the realised uniform allocation leaves that ceiling undecided in every context.

The exhaustive reference count of eight per context is used to score each policy after selection. It is not substituted for the evidence available within the policy’s 28-review allocation. The probability bound addresses sampling uncertainty under the frozen reference and design. Convention-conditioned bounds in [Supplement T](reference_audit.md) address different modelling assumptions and carry no sampling-coverage claim.

## P5 Reproduction and version boundaries

The distribution includes `r5_f3/integration/inputs/neurosemanticorr_prospective_evidence_1.0.0.tar.xz`, a documented projection of the original prospective archive. The plan, frame, dossiers, candidate outputs, reference labels, selections and receipts retain their original bytes. [Archive projection](../ARCHIVE_PROJECTION.md) records the original and distributed identities. The [prospective evidence index](../evidence/SUPPLEMENT_P_EVIDENCE_INDEX.json) preserves the historical source hashes; principal documentary records are available in `supplement_sources/source_evidence/P/` in the data archive.

The F3 replay reconstructs the frozen selections and scores from the original identifiers, flags, permutations and labels. It matches eight context–policy reports across 72 field comparisons, reproducing 32 errors under screening, 19 under uniform review and the upper bound of 60. It makes no new random draw or human adjudication. [Supplement T](reference_audit.md), Sections T10–T11, identifies that implementation and its integrated qualification.

The experiment, retrospective convention analysis, mathematical certificates and native diagnostic probes have different input and execution identities. Their repeated software checks are not added to the 192-dossier empirical denominator. Historical P1 and P4 FAIL_CLOSED outcomes and the later P5 qualification keep their original scope in [Supplement S](historical_profile.md).

## P6 Evidence navigation

[SUPPLEMENT_P_EVIDENCE_INDEX.json](../evidence/SUPPLEMENT_P_EVIDENCE_INDEX.json) lists the historical path, size and SHA-256 of each record: P01–P04 cover the plan, freeze, reference and permutations; P05–P08 the selection, results, commitment and original execution receipt; P09–P14 the frame, construction and reference checks; P15 the exploratory sensitivity analysis; and P16 the additional documentary count of selected non-alias cases. The distribution terms are recorded in the [rights notices](../../RIGHTS_NOTICES.md).
