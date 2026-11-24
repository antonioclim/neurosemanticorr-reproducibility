# Integrated qualification

Run from the software repository directory with CPython 3.12 on Linux. The qualified patch version is 3.12.14:

```sh
python3 -B -m r5_f3.integration.run --out ../nsc_f3_verification_01
```

Choose a new output directory outside the repository. The runner checks the closed software inventory, verifies and extracts the retained 192-case archive, then runs the mathematical qualification, O15 unit/CLI/documentary/native checks, screening tests and frozen-design replay, retained phase2 calculations, the software-report example and the complete P5 synthetic unit review. Its final source inventory must equal the initial inventory.

The expected corpus is explicit: 27 mathematical test methods and 17 examples; 23 O15 unit tests and eight CLI checks; 202 documentary dossiers with 1,010 convention comparisons; 94 P4 and 94 P5 diagnostic invocations; 12 screening tests; four retained decision tests; 20 software-example comparisons; and 183 P5 review checks across 158 candidate invocations. The layers overlap and must not be summed as independent research observations.

`SUMMARY.json` contains the final status and all command receipts. Each command also has raw `stdout.bin`, `stderr.bin` and `RECEIPT.json`, including controlled timeout, launch failure and nonzero-exit records when they occur. `TRACEBACK.txt` is written on an unsuccessful acceptance run. A zero exit code alone is insufficient: known corpus sizes, named results and retained exact result hashes are checked.

New native diagnostic inputs and outputs appear in `native_p4` and `native_p5`. The historical data are extracted read-only in `retained_archive`; the historical prospective checker identities are never executed. The `p5_full` directory contains fresh synthetic unit inputs and raw reports. No new sampling design, human adjudication or publication is performed.

The current input capsule has SHA-256 `55dc0a8bfd7a9aec272bf259b81b15a57e9fc41be9f3b38b75d3e1b20c0054d1`. Its scientific members retain their original bytes; its documentation is the Markdown projection described in `PROVENANCE.json`. The runner rejects links and unsafe paths during extraction.
