# Verification scope

The P5 pipeline performs source custody checks, deterministic synthetic unit checks and serial execution of the included checker sources. Its receipts identify each command, source/profile hash, input, expected result and observed result. These checks qualify the declared finite cases and transformations.

The frozen P4 result remains 98/100 conformance and 2/36 gold-valid false rejections for each primary arm, with MAIN semantic `FAIL_CLOSED`. The earlier P1 custody result remains `FAIL_CLOSED 771/772`. P5's explicit alias grammar and new synthetic cases do not replace or rescore that original experiment.

The qualified full repository runtime is Linux CPython 3.12.14. Source syntax inspection is distinct from execution on another interpreter. A fresh virtual environment on one host does not establish reproduction on a clean operating system or in another laboratory. The checker output path uses POSIX flags including `O_NOFOLLOW`, and the driver uses POSIX process groups. Native Windows is outside the qualified full-pipeline profile.

The test fixtures exercise finite properties under their stated preconditions. They do not estimate field prevalence, authenticate the original producer or provide natural-language entailment. No original scientific fit, refit or prospective sampling operation is performed by these commands.

The root `codemeta.json` uses a minimal Schema.org SoftwareSourceCode JSON-LD representation; it is not a remotely registered record. The closed package inventories and provenance files use their explicit project-local schemas. The root citation file is separate from computational receipts.

Historical phase records retain their original environment descriptions and validation scope. Current package qualification and historical study outcomes should be reported with their own identities.
