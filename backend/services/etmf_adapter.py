"""
eTMF Storage Adapter
====================
Abstract write interface for signed ETMF PDF routing.

Adapters:
  LocalFilesystemAdapter  — writes to backend/.etmf_local/  (test / dev)
  SharePointAdapter       — STUB: raises NotImplementedError (requires real MS Graph wiring)

Factory:
  get_etmf_adapter()  reads ETMF_ADAPTER env var ('local' | 'sharepoint', default 'local')

Naming convention: {study}/{blinded_subject_id}/FORM_ADJ_15A_{subject_id}_{timestamp_utc}.pdf
Access scope note: the destination path should be restricted to Monitor + Admin roles only;
  adjudicators must never receive a direct path or URL to the eTMF repository.

Outstanding external dependency:
  SharePointAdapter requires:
    - ETMF_SHAREPOINT_SITE_URL  (e.g. https://acrnfoundation.sharepoint.com/sites/PROTECT-eTMF)
    - ETMF_SHAREPOINT_LIBRARY   (document library name, e.g. 'Adjudication Records')
    - AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID  (app registration with Files.ReadWrite)
  Until these are wired, all production eTMF writes MUST use the local adapter and the
  SharePoint upload must be treated as a manual post-process step.
"""

import abc
import os
import hashlib
from datetime import datetime
from pathlib import Path


class ETMFAdapter(abc.ABC):
    """Abstract eTMF write interface."""

    @abc.abstractmethod
    def write(
        self,
        subject_id: str,
        blinded_id: str,
        study: str,
        pdf_bytes: bytes,
        timestamp: datetime | None = None,
    ) -> str:
        """Write a signed adjudication PDF to the eTMF repository."""

    @abc.abstractmethod
    def write_meeting_report(
        self,
        meeting_id: str,
        meeting_title: str,
        study: str,
        report_bytes: bytes,
        timestamp: datetime | None = None,
    ) -> str:
        """Write a signed committee meeting summary report to the eTMF repository."""

    @staticmethod
    def _naming(study: str, blinded_id: str, subject_id: str, ts: datetime) -> str:
        """Deterministic filename per naming convention SOP-ADJ-002 §7."""
        study_safe = study.replace(" ", "_").replace("/", "-")
        ts_str = ts.strftime("%Y%m%dT%H%M%SZ")
        return f"FORM_ADJ_15A_{blinded_id}_{ts_str}.pdf"

    @staticmethod
    def _path_parts(study: str, blinded_id: str) -> tuple[str, str]:
        """Returns (folder_path, study_safe) for use by concrete adapters."""
        study_safe = study.replace(" ", "_").replace("/", "-")
        return study_safe, blinded_id


class LocalFilesystemAdapter(ETMFAdapter):
    """
    Writes signed PDFs to a local filesystem path.

    Root defaults to  <backend_dir>/.etmf_local/
    Override with ETMF_LOCAL_ROOT env var.

    Structure:
      .etmf_local/
        PROTECT-Africa/
          ADJ-E2E-001/
            FORM_ADJ_15A_ADJ-E2E-001_20260818T143000Z.pdf
          MEETINGS/
            MEETING_REPORT_<id>_<ts>.pdf
    """

    def __init__(self, root: str | None = None):
        if root:
            self._root = Path(root)
        else:
            # Resolve relative to this file's parent's parent (backend/)
            here = Path(__file__).parent.parent
            self._root = Path(os.getenv("ETMF_LOCAL_ROOT", str(here / ".etmf_local")))

    def write(
        self,
        subject_id: str,
        blinded_id: str,
        study: str,
        pdf_bytes: bytes,
        timestamp: datetime | None = None,
    ) -> str:
        ts = timestamp or datetime.utcnow()
        study_dir, bid_dir = self._path_parts(study, blinded_id)
        dest_dir = self._root / study_dir / bid_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = self._naming(study, blinded_id, subject_id, ts)
        dest_path = dest_dir / filename

        dest_path.write_bytes(pdf_bytes)

        # Write SHA-256 manifest alongside
        checksum = hashlib.sha256(pdf_bytes).hexdigest()
        (dest_dir / (filename + ".sha256")).write_text(
            f"{checksum}  {filename}\n", encoding="utf-8"
        )
        return str(dest_path)

    def write_meeting_report(
        self,
        meeting_id: str,
        meeting_title: str,
        study: str,
        report_bytes: bytes,
        timestamp: datetime | None = None,
    ) -> str:
        ts = timestamp or datetime.utcnow()
        study_safe = study.replace(" ", "_").replace("/", "-")
        dest_dir = self._root / study_safe / "MEETINGS"
        dest_dir.mkdir(parents=True, exist_ok=True)

        ts_str = ts.strftime("%Y%m%dT%H%M%SZ")
        filename = f"MEETING_REPORT_{meeting_id}_{ts_str}.pdf"
        dest_path = dest_dir / filename

        dest_path.write_bytes(report_bytes)
        checksum = hashlib.sha256(report_bytes).hexdigest()
        (dest_dir / (filename + ".sha256")).write_text(
            f"{checksum}  {filename}\n", encoding="utf-8"
        )
        return str(dest_path)


class SharePointAdapter(ETMFAdapter):
    """
    STUB — SharePoint / MS Graph eTMF adapter.

    NOT IMPLEMENTED. Requires:
      ETMF_SHAREPOINT_SITE_URL, ETMF_SHAREPOINT_LIBRARY,
      AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID

    This class exists so the interface is stable and swappable.
    Raises NotImplementedError at runtime until the dependency is wired.
    """

    def write(self, subject_id, blinded_id, study, pdf_bytes, timestamp=None):
        raise NotImplementedError(
            "SharePointAdapter is not yet configured. "
            "Set ETMF_ADAPTER=local for development/test. "
            "To enable SharePoint, provide ETMF_SHAREPOINT_SITE_URL, "
            "ETMF_SHAREPOINT_LIBRARY, and Azure app credentials. "
            "See backend/services/etmf_adapter.py for full requirements."
        )

    def write_meeting_report(self, meeting_id, meeting_title, study, report_bytes, timestamp=None):
        raise NotImplementedError("SharePointAdapter is not yet configured.")



def get_etmf_adapter() -> ETMFAdapter:
    """
    Factory: returns the correct adapter based on ETMF_ADAPTER env var.
      'local'      -> LocalFilesystemAdapter  (default)
      'sharepoint' -> SharePointAdapter       (stub — not wired)
    """
    adapter_name = os.getenv("ETMF_ADAPTER", "local").strip().lower()
    if adapter_name == "sharepoint":
        return SharePointAdapter()
    return LocalFilesystemAdapter()
