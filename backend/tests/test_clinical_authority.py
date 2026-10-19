from pathlib import Path

import pytest

from services.clinical_derivation import ClinicalDerivationError, RULE_VERSION, derive_clinical_bundle


def test_authoritative_bundle_has_one_version_and_required_gates():
    bundle = derive_clinical_bundle({"bp_readings": []})
    assert bundle["engine_version"] == RULE_VERSION
    assert {"DV-03", "DV-26", "DV-27", "DV-30"}.issubset(bundle["dv_results"])
    assert {result["rule_version"] for result in bundle["dv_results"].values()} == {RULE_VERSION}


def test_reviewer_workbench_does_not_execute_browser_clinical_engine():
    source = (Path(__file__).parents[2] / "src" / "components" / "AdjudicatorWorkbench.jsx").read_text(encoding="utf-8")
    assert "runDvEngine" not in source
    assert "Authoritative server derivation unavailable" in source

