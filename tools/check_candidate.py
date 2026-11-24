"""Check the software distribution against its closed SHA-256 inventory."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "SOFTWARE_CONTENTS.json"


def main():
    declared = json.loads(MANIFEST.read_bytes())["files"]
    files = {}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts or path == MANIFEST:
            continue
        if path.is_symlink():
            raise ValueError(f"Unexpected symlink: {relative}")
        if path.is_file():
            files[relative.as_posix()] = path
    if set(declared) != set(files):
        raise ValueError(f"Inventory mismatch. Missing: {sorted(set(declared) - set(files))}. "
                         f"Unexpected: {sorted(set(files) - set(declared))}.")
    for name, path in files.items():
        data = path.read_bytes()
        if {"nbytes": len(data), "sha256": sha256(data).hexdigest()} != declared[name]:
            raise ValueError(f"Candidate bytes differ: {name}")
    print(json.dumps({
        "status": "PASS_SOFTWARE_CUSTODY",
        "version": json.loads(MANIFEST.read_bytes())["version"],
        "files_verified": len(files),
        "software_manifest_sha256": sha256(MANIFEST.read_bytes()).hexdigest(),
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
