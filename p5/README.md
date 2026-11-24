# P5 finite consistency checkers

The P5 component contains two separately implemented checkers, a fixed finite consistency profile, an explicit alias interface and deterministic synthetic unit checks. The scientific author is Antonio Clim. The component sources, profiles and fixtures retain their qualified bytes within neuroSEMANTICorr software 1.0.0.

## Start

Use an installed CPython 3.12 interpreter on Linux. From this directory:

```sh
python3 -B -I tools/review.py --mode smoke --out ../../p5_smoke
python3 -B -I tools/review.py --mode full --out ../../p5_full
```

Each output directory must be new and outside the enclosing repository. The smoke and full reviewer paths use cooperative monotonic deadlines of 300 and 1,800 seconds, with up to two seconds for child reaping and final evidence-write overhead. They are not suspend-inclusive production time-budget certificates or promises of completion. The pipeline runs serially and uses a five-second child limit. Do not rerun into an existing directory. See [QUICKSTART.md](QUICKSTART.md) for the smoke and full qualification paths and [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for evidence-preserving failure handling.

A sealed distribution contains `KIT_MANIFEST.json`. The pipeline checks its closed inventory before launching checkers. `--unsealed-development` is for retained internal pre-seal qualification only; it is not the reviewer route. No dependency installation is required by the kit. Python itself remains an external runtime dependency.

## What is tested

The active profile has 16 three-valued obligations and four diagnostic ablations. `S`, `V` and `U` mean satisfied, violated and undecidable from the available evidence. An active `V` yields `REJECT`; otherwise a `U` yields `INDETERMINATE`; otherwise the full scope yields `ALLOW_WITHIN_SCOPE`. A partial ablation cannot claim full acceptance.

The P5 fixtures use new `P5UNIT-...` identities. They are semantic, regression and metamorphic checks, not a fresh main benchmark or independent incidents. Source/profile hashes, exact commands, per-attempt outputs and the environment are retained under the selected output directory. `SUMMARY.json` states the executed scope and failures. Tests do not authenticate the historical producer or establish natural-language entailment, causal diagnosis or measured adoption value.

The alias contract is in `profiles/ALIAS_GRAMMAR_V1.json`. A direct source pointer begins with `/`. An alias is `alias:NAME` and is resolved exactly once through the `NAME` key in `aliases`; the resulting value must be a direct pointer. The contract also defines invalid forms and metadata checks. The two checkers implement this convention separately. Their report schema retains its earlier identifier for compatibility; the distribution provenance identifies the new source version.

## Preserve the earlier experiment

The P4 v2 comparison remains immutable. Each primary checker matched its frozen gold on 98/100 cases and rejected 2/36 cases designated valid. Those common alias discrepancies exposed an underspecified interface; P5 repair does not relabel or replace those observations. P4 MAIN semantic conformance remains `FAIL_CLOSED`, with 20 affected reports including timing repeats. Its 1,400 completed invocations are distinct from P5 UNIT checks.

P4 DEV also retains its initial failed diagnostic gate and a separately qualified rescore of identical reports. The raw P4 v1 evidence was not recovered after the earlier temporary-environment reset. None of these limitations is removed by new P5 tests.

## Runtime and verification boundaries

Actual available runtimes are recorded in the phase evidence. Linux CPython 3.12.3 and 3.12.14 are distinct patch runtimes. Other minor Python versions, native Windows and native R must not be described as executed without their own receipts. An isolated virtual environment on this host is not a clean operating-system reproduction or external replication.

The POSIX pipeline uses process groups for child cleanup. Checker output creation also uses POSIX flags such as O_NOFOLLOW. The Windows direct-child fallback is not sufficient to establish native Windows compatibility; that platform is outside the executed profile. Read [SECURITY.md](SECURITY.md) and [docs/VERIFICATION_SCOPE.md](docs/VERIFICATION_SCOPE.md). Static inspection and syntax compilation do not substitute for execution or a formal type-checker result.

## Provenance and rights

The earlier P1 custody result remains `FAIL_CLOSED 771/772`. P5 qualification uses new synthetic identities and does not replace the historical scientific evidence. The root repository provenance and inventory identify the packaged version. Historical P5 qualification records are in `p5/` within the accompanying data archive.

P5 code is licensed under [MIT](../LICENSE); its documentation and synthetic data are licensed under [CC BY 4.0](../LICENSES/CC-BY-4.0.txt). The [licensing scope](../LICENSING.md) includes the public grant for retained material. The [original internal licence](INHERITED_RESTRICTED_INTERNAL_LICENCE.txt) remains unchanged as historical provenance. [Citation metadata](../CITATION.cff) identifies the distribution.
