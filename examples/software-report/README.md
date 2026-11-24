# Checking a claim in a software build report

A release summary reports that seven of eight desktop smoke tests passed. The retained toy result also contains the same fraction for a nightly run. Both fields contain the exact rational 7/8 and carry the same unit and denominator. Their scopes distinguish the release candidate from the nightly run. All values and labels are constructed for this example.

The example uses the existing claim-to-source interface. R15 names the claim and its source. The R15 edge record binds a pointer to scope, unit and denominator. R11 holds the exact result. The evaluator reads only these three records. A direct link to the release measure supports the release claim. Changing only the pointer to the nightly measure violates the scope check even though the number is identical. When the full alias key and suffix key point to different measures, the lookup rule changes which claim can be supported.

| Dossier | Literal only | Suffix only | Either unique | Prefer literal | Prefer suffix |
| --- | --- | --- | --- | --- | --- |
| D1 Direct release scope | S | S | S | S | S |
| D2 Direct nightly pointer, release scope | V | V | V | V | V |
| D3 Alias with release scope | S | V | V | S | V |
| D4 Alias with nightly scope | V | S | V | V | S |

S records a satisfied claim-to-source obligation. V records a violation. `EXPECTED.json` gives the manual prediction for each rule and the corresponding pointer on satisfaction. The expectation and fixture hashes were recorded locally before evaluating the example. The execution receipt includes the resolved pointer or the violation for each comparison.

## Reproduce the 20 comparisons

From the repository root, use the bundled reference modules:

```sh
python3 -B examples/software-report/check_build_report.py --source-dir phase2/02_source
```

The script checks the frozen module hashes and uses the standard library. Expect `PASS_SYNTHETIC_INTERFACE_EXAMPLE` and 20 comparisons. The qualified repository runtime is CPython 3.12.14 on Linux.

The example applies the documentary interface to a constructed software build report. Its 20 comparisons exercise the isolated O15 evaluator. All records belong to this example and remain separate from the retained study observations; evaluation on an external build pipeline would require its own evidence.
