"""
EDC / eSource Value Resolver
===============================
Implements Dr. Makadzange's source hierarchy rules exactly:

  1. Use EDC value when EDC field is present and non-null.
  2. Use eSource ONLY when EDC is absent AND charter permits.
  3. eSource supplements context but NEVER silently overwrites EDC.
  4. All discrepancies are flagged for adjudicator display.
  5. Clinically material discrepancies are NEVER auto-resolved.

Returns a typed ResolvedValue with full provenance.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class DiscrepancyCategory(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    EQUIVALENT_AFTER_CONVERSION = "EQUIVALENT_AFTER_CONVERSION"
    EDC_POPULATED_ESOURCE_MISSING = "EDC_POPULATED_ESOURCE_MISSING"
    ESOURCE_POPULATED_EDC_MISSING = "ESOURCE_POPULATED_EDC_MISSING"
    VALUE_DISCREPANCY = "VALUE_DISCREPANCY"
    DATE_DISCREPANCY = "DATE_DISCREPANCY"
    CODING_DISCREPANCY = "CODING_DISCREPANCY"
    PARTICIPANT_UNMATCHED = "PARTICIPANT_UNMATCHED"


@dataclass
class ResolvedValue:
    canonical_value: Any
    source: str                               # "EDC", "eSource", or None
    discrepant: bool
    discrepancy_category: Optional[DiscrepancyCategory]
    edc_value: Any
    esource_value: Any
    clinically_meaningful_discrepancy: Optional[bool]
    notes: str = ""


def resolve_value(
    edc_value: Any,
    esource_value: Any,
    tolerance: Optional[float] = None,
    clinically_meaningful_threshold: Optional[float] = None,
) -> ResolvedValue:
    """
    Core EDC/eSource resolution function per Dr. Makadzange's hierarchy:

      - EDC is authoritative.
      - eSource fills gaps only.
      - Discrepancies are always surfaced, never silently resolved.

    Args:
        edc_value:  Raw value from EDC (Oracle Clinical One). None if absent.
        esource_value: Raw value from eSource (Castor/GCP-Sense). None if absent.
        tolerance: For numeric fields, absolute tolerance for "equivalent" match.
        clinically_meaningful_threshold: If discrepancy magnitude exceeds this,
                                         flag as clinically meaningful.

    Returns:
        ResolvedValue with full provenance.
    """
    # ── Both absent ──────────────────────────────────────────────────────────
    if edc_value is None and esource_value is None:
        return ResolvedValue(
            canonical_value=None,
            source=None,
            discrepant=False,
            discrepancy_category=None,
            edc_value=None,
            esource_value=None,
            clinically_meaningful_discrepancy=None,
            notes="Both EDC and eSource are absent.",
        )

    # ── EDC present (authoritative path) ─────────────────────────────────────
    if edc_value is not None:
        # eSource also present — check for discrepancy
        if esource_value is not None:
            discrepant, category, meaningful = _compare(
                edc_value, esource_value, tolerance, clinically_meaningful_threshold
            )
            return ResolvedValue(
                canonical_value=edc_value,   # EDC wins — always
                source="EDC",
                discrepant=discrepant,
                discrepancy_category=category,
                edc_value=edc_value,
                esource_value=esource_value,
                clinically_meaningful_discrepancy=meaningful,
                notes=(
                    f"EDC value used. eSource differs: {esource_value!r} vs {edc_value!r}."
                    if discrepant else "EDC and eSource concordant."
                ),
            )
        else:
            # EDC populated, eSource missing — normal expected case
            return ResolvedValue(
                canonical_value=edc_value,
                source="EDC",
                discrepant=False,
                discrepancy_category=DiscrepancyCategory.EDC_POPULATED_ESOURCE_MISSING,
                edc_value=edc_value,
                esource_value=None,
                clinically_meaningful_discrepancy=None,
                notes="EDC value used. eSource absent (expected for EDC-primary fields).",
            )

    # ── EDC absent, eSource present ───────────────────────────────────────────
    return ResolvedValue(
        canonical_value=esource_value,
        source="eSource",
        discrepant=False,
        discrepancy_category=DiscrepancyCategory.ESOURCE_POPULATED_EDC_MISSING,
        edc_value=None,
        esource_value=esource_value,
        clinically_meaningful_discrepancy=None,
        notes="eSource value used as EDC field is absent. Verify charter permits eSource use for this field.",
    )


def _compare(
    edc_val: Any,
    esource_val: Any,
    tolerance: Optional[float],
    cm_threshold: Optional[float],
) -> tuple[bool, DiscrepancyCategory, Optional[bool]]:
    """
    Compare EDC and eSource values and classify the discrepancy.

    Returns:
        (is_discrepant, discrepancy_category, clinically_meaningful)
    """
    # Numeric comparison with tolerance
    try:
        edc_num = float(edc_val)
        esource_num = float(esource_val)
        diff = abs(edc_num - esource_num)

        if diff == 0:
            return False, DiscrepancyCategory.EXACT_MATCH, False

        if tolerance is not None and diff <= tolerance:
            return False, DiscrepancyCategory.EQUIVALENT_AFTER_CONVERSION, False

        meaningful = None
        if cm_threshold is not None:
            meaningful = diff > cm_threshold

        return True, DiscrepancyCategory.VALUE_DISCREPANCY, meaningful

    except (TypeError, ValueError):
        pass

    # String comparison
    edc_str = str(edc_val).strip().lower()
    esource_str = str(esource_val).strip().lower()

    if edc_str == esource_str:
        return False, DiscrepancyCategory.EXACT_MATCH, False

    # Coding discrepancy (both non-null strings that differ)
    return True, DiscrepancyCategory.VALUE_DISCREPANCY, None
