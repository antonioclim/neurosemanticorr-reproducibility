"""Identities of the installed component, independent of the working directory."""

from pathlib import Path
from .canonical import file_digest

VERSION = "1.0.0"
HERE = Path(__file__).resolve().parent
RUNTIME_FILES = ("__init__.py", "__main__.py", "canonical.py", "model.py", "engine.py",
                 "verification.py", "canonical_query.py", "provenance.py", "cli.py", "request.schema.json")


def code_identity():
    return {"component": "neuroSEMANTICorr.reference_audit", "version": VERSION,
            "files_sha256": {name: file_digest(HERE / name) for name in RUNTIME_FILES}}
