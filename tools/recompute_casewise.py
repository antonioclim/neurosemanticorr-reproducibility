"""Reconstruct the common and casewise threshold implications from retained records."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2 / "02_source"))

from run_phase2 import reconstruct_frame, verify_local_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frozen_root", type=Path, help="unpacked NSC_PROS_v1")
    archive = parser.parse_args().frozen_root
    verify_local_lock(PHASE2 / "00_protocol/PREEXECUTION_LOCK.json")
    labels, _, frame = reconstruct_frame(archive)
    frozen_selection = archive / "evaluation/BLIND_SELECTION.json"
    agreed = {case: row["O15"][0] for case, row in
              json.loads(frozen_selection.read_bytes())["case_outputs"].items()}
    possible_errors = {
        case: {int(verdicts[case] != prior) for verdicts in labels.values()}
        for case, prior in agreed.items()
    }
    witness = frame["minimum_witness"]["case_ids"][0]
    branches = {}
    for verdict, common in frame["possible_decisions_after_witness"].items():
        admissible = possible_errors | {witness: {int(agreed[witness] != verdict)}}
        lower = sum(map(min, admissible.values()))
        upper = sum(map(max, admissible.values()))
        branches[verdict] = {
            "common_rule_attainable_counts": common["attainable_counts"],
            "casewise_interval": [lower, upper],
        }
    print(json.dumps({
        "scope": "derived comparison on 192 retained agreements, no historical checker execution",
        "selection_sha256": sha256(frozen_selection.read_bytes()).hexdigest(),
        "ceiling": frame["ceiling"],
        "illustrative_witness": witness,
        "casewise_ambiguous_dossiers": sum(len(options) == 2 for options in possible_errors.values()),
        "casewise_always_correct_dossiers": sum(options == {0} for options in possible_errors.values()),
        "branches": branches,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
