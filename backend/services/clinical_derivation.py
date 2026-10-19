"""Authoritative clinical derivation boundary.

All application workflows must call this module rather than executing a second
implementation of the clinical rules.  The boundary validates the engine
contract before results can be persisted or shown to an adjudicator.
"""
from typing import Any, Dict

from services.dv_engine import RULE_VERSION, run_dv_engine


class ClinicalDerivationError(RuntimeError):
    """Raised when the rule engine returns a bundle that cannot be trusted."""


def derive_clinical_bundle(case_data: Dict[str, Any]) -> Dict[str, Any]:
    bundle = run_dv_engine(case_data)
    if bundle.get("engine_version") != RULE_VERSION:
        raise ClinicalDerivationError("Clinical rule engine returned an unexpected version")

    results = bundle.get("dv_results")
    required = {"DV-03", "DV-07", "DV-08", "DV-10", "DV-11", "DV-14", "DV-26", "DV-27", "DV-30"}
    if not isinstance(results, dict) or not required.issubset(results):
        raise ClinicalDerivationError("Clinical rule engine returned an incomplete result bundle")
    if any(result.get("rule_version") != RULE_VERSION for result in results.values()):
        raise ClinicalDerivationError("Clinical result bundle contains mixed rule versions")
    return bundle

