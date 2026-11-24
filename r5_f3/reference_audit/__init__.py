"""Finite reference-audit software with exact rational scoring."""

from .canonical import InputError, VerificationError
from .engine import audit
from .model import validate_request
from .canonical_query import canonical_query_minimum
from .provenance import VERSION
from .verification import verify_report, verify_witness

__all__ = ["VERSION", "InputError", "VerificationError", "validate_request", "audit",
           "verify_report", "verify_witness", "canonical_query_minimum"]
