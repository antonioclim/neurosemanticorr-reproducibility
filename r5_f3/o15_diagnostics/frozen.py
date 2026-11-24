"""Identify unchanged native source bytes; never alter a checker or its profile."""
from pathlib import Path

from .evidence import InputError, parse, sha256

P4_ARCHIVE_SHA256 = "01d39c2da1515e5870d6e356ac24000e89fbe0d4fad77188bd83dc2a6b31625a"
P4_FILES = {
    "t_full/checker.py": ("02_implementations/t_full/checker.py", "9d8153640e47fb74d154af547d7119ff92bb67be53f9b395f5a559700e5e2d10"),
    "b_assert/checker.py": ("02_implementations/b_assert/checker.py", "3266ca109c7cea6f5fe9a1aeb0bdf9a8e46d808787708b36551a5e4ff03fc59e"),
    "FIXED_PROFILE.json": ("01_protocol/FIXED_PROFILE.json", "e71c7435494dcf5e27163cdbf10bbb63baa57390465d1695ec9597f3a9dc448d"),
    "FROZEN_ARMS_MANIFEST.json": ("01_protocol/FROZEN_ARMS_MANIFEST.json", "4c010aef347b745c19157bd1dd45299f8d463cbccd5beb091df5cf39d0fb78ce"),
}
P5_FILES = {
    "checkers/t_full/checker.py": "5deb8b064d17b0729d8fea77a88b24f21bf98327a24e40a316c79c91e6d7666a",
    "checkers/b_assert/checker.py": "0606b623c0261795bcc7dbe42210e92698dbb694533ba2da87632e61a45386af",
    "profiles/FIXED_PROFILE.json": "dcbd63f5bc49b32f43b9cdf3e2fc2fa4fd29a9878d8af9809d57041e21b32b8f",
}


def native_context(repository, generation):
    repository = Path(repository).resolve()
    if generation == "P5":
        root = repository / "p5"
        for relative, expected in P5_FILES.items():
            member = root / relative
            if not member.is_file() or member.is_symlink() or sha256(member.read_bytes()) != expected:
                raise InputError("P5_RETAINED_SOURCE_MISMATCH:" + relative)
        checkers = {"T_FULL": root / "checkers/t_full/checker.py", "B_ASSERT": root / "checkers/b_assert/checker.py"}
        profile = root / "profiles/FIXED_PROFILE.json"
        convention = "suffix_only"
        qualification = "P5 exact-nonempty-suffix alias grammar, maximum one hop."
    elif generation == "P4":
        root = Path(__file__).resolve().parent / "native_sources/P4"
        for relative, (_, expected) in P4_FILES.items():
            member = root / relative
            if not member.is_file() or member.is_symlink() or sha256(member.read_bytes()) != expected:
                raise InputError("P4_FROZEN_SOURCE_MISMATCH:" + relative)
        manifest = parse((root / "FROZEN_ARMS_MANIFEST.json").read_bytes())
        if manifest["profile_sha256"] != P4_FILES["FIXED_PROFILE.json"][1]:
            raise InputError("P4_FROZEN_PROFILE_MANIFEST_MISMATCH")
        for arm, sub in (("T_FULL", "t_full"), ("B_ASSERT", "b_assert")):
            item = next(a for a in manifest["arms"] if a["arm_id"] == arm)
            if item["sha256"] != P4_FILES[sub + "/checker.py"][1]:
                raise InputError("P4_FROZEN_ARM_MANIFEST_MISMATCH:" + arm)
        checkers = {"T_FULL": root / "t_full/checker.py", "B_ASSERT": root / "b_assert/checker.py"}
        profile = root / "FIXED_PROFILE.json"
        convention = "literal_only"
        qualification = ("P4 full-token alias lookup on this declared corpus. The literal_only documentary labels are "
                         "known-answer expectations for these cases, not a claim of universal equivalence of parsers.")
    else:
        raise InputError("NATIVE_GENERATION_MUST_BE_P4_OR_P5")
    return {"generation": generation, "profile_path": profile, "checker_paths": checkers,
            "profile_sha256": sha256(profile.read_bytes()),
            "checker_hashes": {a: sha256(p.read_bytes()) for a, p in checkers.items()},
            "comparison_convention": convention, "comparison_scope": qualification}
