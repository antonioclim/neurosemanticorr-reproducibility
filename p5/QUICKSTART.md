# Reviewer quick start

## Smoke check

1. Extract the complete software distribution to a new directory. Keep its `p5`, `phase2` and `r5_f3` directories together. Directory names may contain spaces.
2. Use CPython 3.12 on Linux and open a terminal in the distribution's `p5` directory. The check uses the Python standard library.
3. Choose a new output directory outside the software distribution and run:

   ```sh
   python3 -B -I tools/review.py --mode smoke --out ../../p5_smoke
   ```

4. Open `../../p5_smoke/SUMMARY.json`. A successful smoke check reports `PASS_UNIT_REVIEW` with 45 completed checks. `ENVIRONMENT.json` and `COMMAND.json` identify the runtime and command. Per-attempt receipts and raw checker reports are in `attempts/`; generated inputs are in `fixtures/`.
5. Preserve the complete output of each attempt, including failures. Use a fresh directory for a separately identified rerun.

## Full qualification

From the same `p5` directory, choose another new output directory outside the software distribution:

```sh
python3 -B -I tools/review.py --mode full --out ../../p5_full
```

The full path covers deterministic UNIT, alias, metamorphic and ablation controls. A successful result reports `PASS_UNIT_REVIEW` with 183 completed checks across 158 checker invocations. Inspect the executed and missing counts, source/profile bindings and raw receipts. Semantic verdicts such as `REJECT` are evaluated against each fixture's declared expectation.

## Deadlines and execution evidence

The pipeline runs serially with a five-second deadline per child. Its cooperative monotonic deadlines are 300 seconds for smoke and 1,800 seconds for full qualification. Child cleanup can add up to two seconds; final evidence writing adds overhead. Actual durations are recorded in the receipts. A timeout or incomplete check set remains a failed or incomplete attempt.

## Reproduction scope

These commands execute new synthetic P5 UNIT cases. The retained P4 and M06DR observations keep their original identities and adverse scores. P4 summary arithmetic can be recomputed from stored outputs without launching the historical candidates.

The qualified full-pipeline environment is CPython 3.12.14 on Linux. Native Windows has not been qualified. Environment files identify the host and interpreter used for each run; an isolated virtual environment on one host does not establish reproduction on a clean operating system or in another laboratory. See [verification scope](docs/VERIFICATION_SCOPE.md) and [failure handling](docs/TROUBLESHOOTING.md).
