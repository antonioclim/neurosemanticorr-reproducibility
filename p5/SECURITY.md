# Security and execution scope

This local candidate evaluates synthetic retained evidence. It is not a sandbox for arbitrary hostile programs or a security certification of the host operating system.

The reviewer route verifies the sealed kit inventory, uses explicit paths and fresh output directories, runs serial subprocesses and retains failures. POSIX process groups support child cleanup. The Windows fallback does not establish process-tree containment. The checkers also use POSIX output flags, so native Windows remains outside the current supported and executed profile. Do not elevate privileges to run this kit.

Case inputs must remain ordinary local files. Symlinks, path traversal, duplicate JSON keys, nonfinite tokens, Boolean/integer confusion and undefined values are handled within the declared profile and its qualified test scope. An absence of findings in those tests is not proof that all hostile inputs are safe. Resource sampling is not a hard operating-system memory quota.

No external network access is needed for the intended reviewer path. The source audit records imports and sensitive operations. It distinguishes a reviewed file operation or subprocess launch from arbitrary code execution. No source scanner can prove the absence of secrets or personal data. Synthetic markers used in adversarial fixtures must be distinguished from actual credentials.

Preserve the complete output when reporting a problem. Identify the source/profile hashes, Python version, command, expected check and actual receipt path. Do not attach credentials or unrelated personal data. No dedicated reporting channel or response-time commitment is specified by this version.

The [licensing scope](../LICENSING.md) records the authorised MIT and CC BY 4.0 terms for this distribution. The original internal licence remains a historical source record.

Deadlines are cooperative monotonic checks with child-reap and evidence-write allowances. Output ceilings are sampled. Complete descendant cleanup after a normally exited owner and host-death survival are not certified. The sealed, inspected checkers do not launch producers or child programs; this driver is not a replacement for the stronger historical P4 supervisor.
